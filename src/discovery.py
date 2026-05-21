"""Unified candidate-pool discovery for the portfolio selector.

At each scan, builds a single deduped pool of {held positions} ∪ {newly
discovered candidates} for the portfolio-selector to rank. Sources:

  - Held positions (always included)
  - Alpha Vantage TOP_GAINERS_LOSERS (gainers + losers + most-active)
  - Alpha Vantage NEWS_SENTIMENT outliers (topic-driven discovery)
  - tradingview-screener volume-breakout + bollinger-squeeze scans
  - Seed watchlist + auto-maintained dynamic watchlist (eligibility only)

After dedup + screener-floor filtering + sector cap, the pool is capped at
``discovery.pool_size_max`` symbols.

Output is a list of ``Candidate`` dataclasses each carrying the ``sources``
that surfaced the symbol so downstream logging can show source breakdown.
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from src.candidate_scoring import discovery_priority_score
from src.config import Config
from src.dynamic_watchlist import load_dynamic_watchlist
from src.market_data import MarketDataService
from src.universe import sp500_sectors

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Candidate                                                                   #
# --------------------------------------------------------------------------- #


@dataclass
class Candidate:
    symbol: str
    sources: list[str] = field(default_factory=list)
    sector: str = ""
    price: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    market_cap_usd: float = 0.0
    is_held: bool = False
    discovery_priority_score: float = 0.0
    discovery_priority_reasons: list[str] = field(default_factory=list)

    def add_source(self, src: str) -> None:
        if src not in self.sources:
            self.sources.append(src)


# --------------------------------------------------------------------------- #
#  Discovery entry point                                                       #
# --------------------------------------------------------------------------- #


def discover_candidates(
    cfg: Config,
    mds: MarketDataService,
    held_symbols: Iterable[str] | None = None,
    exclude_symbols: Iterable[str] | None = None,
) -> tuple[list[Candidate], dict[str, int]]:
    """Build the unified candidate pool.

    Returns ``(candidates, sources_breakdown)`` where ``sources_breakdown`` is
    a dict like ``{"held": 4, "av_movers": 25, "tv_breakout": 9, ...}`` for
    logging.
    """
    held = {s.upper() for s in (held_symbols or [])}
    excluded = {s.upper() for s in (exclude_symbols or [])}
    excluded |= {s.upper() for s in cfg.get("universe", "exclude_tickers", default=[]) or []}

    pool: dict[str, Candidate] = {}
    breakdown: Counter[str] = Counter()
    sectors = sp500_sectors() if _need_sector_lookup(cfg) else {}

    # 1. Held positions (highest priority — always included, never excluded)
    if cfg.get("discovery", "always_include_held", default=True):
        for sym in held:
            if "/" in sym:
                continue
            _upsert(pool, sym, "held", sectors, is_held=True)
            breakdown["held"] += 1

    # 2. Seed + dynamic watchlists (eligibility only; no score bonus)
    if cfg.get("discovery", "always_include_watchlist", default=True):
        seed_watchlist = cfg.get("universe", "seed_watchlist", default=None)
        if seed_watchlist is None:
            seed_watchlist = cfg.get("universe", "custom_watchlist", default=[]) or []
        for sym in seed_watchlist or []:
            sym = str(sym).upper()
            if sym in excluded:
                continue
            _upsert(pool, sym, "seed_watchlist", sectors)
            breakdown["seed_watchlist"] += 1
        # Backward-compatible legacy custom_watchlist support. If both are
        # present, duplicates are naturally deduped by _upsert.
        for sym in (cfg.get("universe", "custom_watchlist", default=[]) or []):
            sym = str(sym).upper()
            if sym in excluded:
                continue
            _upsert(pool, sym, "legacy_watchlist", sectors)
            breakdown["legacy_watchlist"] += 1

    for sym in load_dynamic_watchlist(cfg):
        if sym in excluded:
            continue
        _upsert(pool, sym, "dynamic_watchlist", sectors)
        breakdown["dynamic_watchlist"] += 1

    # 2026-05-11 overhaul: carry-forward roster. Symbols that scored above
    # discovery.carry_forward_min_score on a recent scan but weren't selected
    # are re-introduced into today's pool so rank truncation doesn't make
    # tomorrow's leader invisible.
    try:
        from src.carry_forward import get_carry_forward_symbols
        for row in get_carry_forward_symbols(cfg):
            sym = str(row.get("symbol", "")).upper()
            if not sym or sym in excluded:
                continue
            _upsert(pool, sym, "carry_forward", sectors)
            breakdown["carry_forward"] += 1
    except Exception:
        pass

    # 2b. Peer-group expansion. This prevents a single familiar ticker from
    # crowding out obvious substitutes in the same trade (AMD vs INTC, MU vs
    # SNDK/WDC, data-center power names such as BE/VRT/GEV).
    if cfg.get("discovery", "include_peer_groups", default=True):
        peer_groups = cfg.get("universe", "peer_groups", default={}) or {}
        active_symbols = set(pool.keys()) | held
        for _group_name, members in peer_groups.items():
            normalized = [str(s).upper() for s in (members or []) if str(s).strip()]
            if not active_symbols.intersection(normalized):
                continue
            for sym in normalized:
                if sym in excluded:
                    continue
                _upsert(pool, sym, "peer_group", sectors)
                breakdown["peer_group"] += 1

    # 3. AV top movers
    movers_top_n = int(cfg.get("discovery", "movers_top_n", default=15) or 15)
    most_active_top_n = int(cfg.get("discovery", "most_active_top_n", default=10) or 10)
    try:
        movers = mds.get_top_movers()
    except Exception as e:
        log.warning("[discovery] get_top_movers failed: %s", e)
        movers = None
    if movers is not None:
        for row in (movers.gainers or [])[:movers_top_n]:
            sym = (row.get("symbol") or "").upper()
            if not sym or sym in excluded:
                continue
            _upsert(pool, sym, "av_gainers", sectors,
                    price=row.get("price", 0.0),
                    change_pct=row.get("change_pct", 0.0),
                    volume=row.get("volume", 0),
                    market_cap_usd=row.get("market_cap_usd", 0.0),
                    sector_hint=row.get("sector", ""))
            breakdown["av_gainers"] += 1
        for row in (movers.losers or [])[:movers_top_n]:
            sym = (row.get("symbol") or "").upper()
            if not sym or sym in excluded:
                continue
            _upsert(pool, sym, "av_losers", sectors,
                    price=row.get("price", 0.0),
                    change_pct=row.get("change_pct", 0.0),
                    volume=row.get("volume", 0),
                    market_cap_usd=row.get("market_cap_usd", 0.0),
                    sector_hint=row.get("sector", ""))
            breakdown["av_losers"] += 1
        for row in (movers.most_active or [])[:most_active_top_n]:
            sym = (row.get("symbol") or "").upper()
            if not sym or sym in excluded:
                continue
            _upsert(pool, sym, "av_most_active", sectors,
                    price=row.get("price", 0.0),
                    change_pct=row.get("change_pct", 0.0),
                    volume=row.get("volume", 0),
                    market_cap_usd=row.get("market_cap_usd", 0.0),
                    sector_hint=row.get("sector", ""))
            breakdown["av_most_active"] += 1

    # 4. AV news-sentiment outliers (topic-wide scan, no ticker filter)
    news_top_n = int(cfg.get("discovery", "news_sentiment_top_n", default=10) or 10)
    relevance_threshold = float(cfg.get("discovery", "news_relevance_threshold", default=0.6) or 0.6)
    if news_top_n > 0:
        try:
            feed = mds.get_news_sentiment(
                tickers=None,
                topics="earnings,ipo,mergers_and_acquisitions,financial_markets",
                limit=50,
            )
        except Exception as e:
            log.warning("[discovery] news_sentiment failed: %s", e)
            feed = []
        outliers = _extract_news_outliers(feed, relevance_threshold)
        for sym in outliers[:news_top_n]:
            sym = sym.upper()
            if sym in excluded:
                continue
            _upsert(pool, sym, "av_news", sectors)
            breakdown["av_news"] += 1

    # 5. TV-screener volume breakouts + bollinger squeeze
    tv_breakout_top_n = int(cfg.get("discovery", "tv_breakout_top_n", default=10) or 10)
    tv_squeeze_top_n = int(cfg.get("discovery", "tv_squeeze_top_n", default=5) or 5)
    if tv_breakout_top_n > 0:
        for row in _tv_volume_breakouts(tv_breakout_top_n)[:tv_breakout_top_n]:
            sym = (row.get("symbol") or "").upper()
            if not sym or sym in excluded:
                continue
            _upsert(pool, sym, "tv_breakout", sectors,
                    price=row.get("price", 0.0),
                    change_pct=row.get("change_pct", 0.0),
                    volume=row.get("volume", 0),
                    market_cap_usd=row.get("market_cap_usd", 0.0),
                    sector_hint=row.get("sector", ""))
            breakdown["tv_breakout"] += 1
    if tv_squeeze_top_n > 0:
        for row in _tv_bollinger_squeezes(tv_squeeze_top_n)[:tv_squeeze_top_n]:
            sym = (row.get("symbol") or "").upper()
            if not sym or sym in excluded:
                continue
            _upsert(pool, sym, "tv_squeeze", sectors,
                    price=row.get("price", 0.0),
                    change_pct=row.get("change_pct", 0.0),
                    volume=row.get("volume", 0),
                    market_cap_usd=row.get("market_cap_usd", 0.0),
                    sector_hint=row.get("sector", ""))
            breakdown["tv_squeeze"] += 1

    # 5b. Phase 7b (2026-05-07): earnings calendar source. Picks up names
    # reporting today AMC + next window_days BMO/AMC that may not appear
    # in normal momentum scanners but have a strong pre-earnings setup.
    # Filtered by min_research_score so only credible plays reach the pool.
    earnings_calendar_cfg = (
        (cfg.get("discovery", "sources", default={}) or {}).get("earnings_calendar")
        if isinstance(cfg.get("discovery", "sources", default={}) or {}, dict)
        else None
    )
    if earnings_calendar_cfg and earnings_calendar_cfg.get("enabled", True):
        try:
            from src.earnings import fetch_upcoming_earnings_calendar, compute_earnings_research_score
            window_days = int(earnings_calendar_cfg.get("window_days", 2) or 2)
            horizon = str(earnings_calendar_cfg.get("horizon", "3month") or "3month")
            max_cands = int(earnings_calendar_cfg.get("max_candidates", 10) or 10)
            min_score = float(earnings_calendar_cfg.get("min_research_score", 0.30) or 0.30)
            picks = fetch_upcoming_earnings_calendar(window_days=window_days, horizon=horizon)
            added = 0
            for entry in picks:
                if added >= max_cands:
                    break
                sym = (entry.get("symbol") or "").upper()
                if not sym or sym in excluded:
                    continue
                research = compute_earnings_research_score(sym)
                if float(research.get("score") or 0.0) < min_score:
                    continue
                _upsert(pool, sym, "earnings_calendar", sectors)
                breakdown["earnings_calendar"] += 1
                added += 1
        except Exception as e:
            log.warning("[discovery] earnings_calendar source failed: %s", e)

    # 6. Apply screener floors (skip held — they bypass floors)
    pool = _apply_screener_floors(pool, cfg, held)

    # 7. Rank the raw pool by active market evidence, not by list membership.
    _annotate_discovery_priorities(pool)

    # 7b. Phase 7b (2026-05-07): boost earnings_calendar candidates so they
    # compete with momentum movers despite no intraday flow. Boost is
    # research_score * priority_score_boost (default 10), so a 0.30 score
    # adds +3 points; 0.60 score adds +6 points.
    if earnings_calendar_cfg and earnings_calendar_cfg.get("enabled", True):
        try:
            from src.earnings import compute_earnings_research_score
            boost_mult = float(earnings_calendar_cfg.get("priority_score_boost", 10) or 10)
            for cand in pool.values():
                if "earnings_calendar" not in (cand.sources or []):
                    continue
                research = compute_earnings_research_score(cand.symbol)
                bonus = float(research.get("score") or 0.0) * boost_mult
                if bonus > 0:
                    cand.discovery_priority_score = float(cand.discovery_priority_score or 0.0) + bonus
                    cand.discovery_priority_reasons = list(cand.discovery_priority_reasons or []) + [
                        f"earnings_calendar_research_score={research.get('score')}"
                    ]
        except Exception as e:
            log.debug("[discovery] earnings_calendar boost failed: %s", e)

    # 7c. 2026-05-12 overhaul: sector-relative score adjustment.
    # Penalize candidates whose sector ETF is underperforming SPY today;
    # boost candidates whose sector is leading. Driven by macro.sector_regime
    # if available. This is the per-sector counterpart to the SPY-only
    # intraday tape filter.
    try:
        from src.sector_etfs import (
            SectorRegime, SectorSnapshot,
            sector_relative_score_adjustment,
        )
        sr_dict = None
        try:
            cached_path = Path(__file__).resolve().parents[1] / "data" / "cache" / "sector_etfs" / "snapshot.json"
            if cached_path.exists():
                cached = json.loads(cached_path.read_text())
                snaps = [SectorSnapshot(**s) for s in cached.get("snapshots", [])]
                sr_dict = {"snapshots": [s.to_dict() for s in snaps], "leading": [], "lagging": []}
        except Exception:
            sr_dict = None
        if sr_dict and bool(cfg.get("sector_rotation", "enabled", default=False)):
            # Build a regime from the cached snapshots so leading/lagging are
            # computed against the same data the adjustment uses.
            from src.sector_etfs import compute_sector_regime
            regime = compute_sector_regime(cfg, [SectorSnapshot(**s) for s in cached.get("snapshots", [])])
            for cand in pool.values():
                sector_name = (sp500_sectors().get(cand.symbol) if sectors else cand.sector) or cand.sector
                if not sector_name:
                    continue
                adj, _audit = sector_relative_score_adjustment(cfg, sector_name, regime)
                if abs(adj) > 0.01:
                    cand.discovery_priority_score = float(cand.discovery_priority_score or 0.0) + adj
                    cand.discovery_priority_reasons = list(cand.discovery_priority_reasons or []) + [
                        f"sector_rs_adj={adj:+.1f}"
                    ]
    except Exception as _e:
        log.debug("sector-relative score adjustment skipped: %s", _e)

    # 7d. 2026-05-12 overhaul: defensive lane injection. When sector_rotation
    # signals a rotation day with defensives leading, the lane appends a
    # required-evaluation set of defensive ETFs to the pool.
    try:
        from src.defensive_lane import build_defensive_candidates
        if 'regime' in locals() and regime is not None:
            for d in build_defensive_candidates(cfg, regime.to_dict()):
                sym = d["symbol"]
                if sym in excluded:
                    continue
                _upsert(pool, sym, "defensive_lane", sectors)
                breakdown["defensive_lane"] += 1
                if sym in pool:
                    pool[sym].discovery_priority_score = max(
                        float(pool[sym].discovery_priority_score or 0.0),
                        float(d.get("discovery_priority_score") or 0.0),
                    )
    except Exception as _e:
        log.debug("defensive_lane injection skipped: %s", _e)

    # 8. Sector cap on the pool (held retained for exit decisions)
    pool = _apply_sector_cap(pool, cfg, held)

    # 9. Hard cap pool_size_max (held always retained)
    pool_max = int(cfg.get("discovery", "pool_size_max", default=50) or 50)
    candidates = _truncate_pool(list(pool.values()), pool_max, held)

    log.info(
        "[discovery] pool=%d held=%d sources=%s",
        len(candidates),
        sum(1 for c in candidates if c.is_held),
        dict(breakdown),
    )
    return candidates, dict(breakdown)


# --------------------------------------------------------------------------- #
#  Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _need_sector_lookup(cfg: Config) -> bool:
    return float(cfg.get("discovery", "max_pool_per_sector", default=0.40) or 0) > 0


def _upsert(
    pool: dict[str, Candidate],
    symbol: str,
    source: str,
    sectors: dict[str, str],
    *,
    price: float = 0.0,
    change_pct: float = 0.0,
    volume: int = 0,
    market_cap_usd: float = 0.0,
    is_held: bool = False,
    sector_hint: str = "",
) -> None:
    sym = symbol.upper().strip()
    if not sym:
        return
    cand = pool.get(sym)
    if cand is None:
        sector = sectors.get(sym, "") or sector_hint or "Other"
        cand = Candidate(
            symbol=sym,
            sector=sector,
            price=float(price or 0.0),
            change_pct=float(change_pct or 0.0),
            volume=int(volume or 0),
            market_cap_usd=float(market_cap_usd or 0.0),
            is_held=is_held,
        )
        pool[sym] = cand
    cand.add_source(source)
    if is_held:
        cand.is_held = True
    # Prefer non-zero metadata over zeros from later sources
    if not cand.price and price:
        cand.price = float(price)
    if not cand.change_pct and change_pct:
        cand.change_pct = float(change_pct)
    if not cand.volume and volume:
        cand.volume = int(volume)
    if not cand.market_cap_usd and market_cap_usd:
        cand.market_cap_usd = float(market_cap_usd)
    if cand.sector in ("", "Other") and sector_hint:
        cand.sector = sector_hint


def _extract_news_outliers(feed: list[dict], relevance_threshold: float) -> list[str]:
    """Pick symbols with high relevance + extreme sentiment from AV news feed.

    Each feed item has ``ticker_sentiment`` = list of {ticker, relevance_score,
    ticker_sentiment_score}. We rank symbols by max(|score|) where relevance
    exceeds threshold, then return top symbols sorted by intensity.
    """
    intensity: dict[str, float] = {}
    for item in feed or []:
        for ts in item.get("ticker_sentiment", []) or []:
            try:
                rel = float(ts.get("relevance_score", 0) or 0)
                score = float(ts.get("ticker_sentiment_score", 0) or 0)
            except (TypeError, ValueError):
                continue
            if rel < relevance_threshold:
                continue
            sym = (ts.get("ticker") or "").upper()
            if not sym or "_" in sym:
                continue
            mag = abs(score) * rel
            if mag > intensity.get(sym, 0.0):
                intensity[sym] = mag
    return [s for s, _ in sorted(intensity.items(), key=lambda kv: kv[1], reverse=True)]


def _tv_volume_breakouts(limit: int) -> list[dict]:
    """Volume + price breakout scan via tradingview-screener."""
    try:
        from tradingview_screener import Query, Column
    except ImportError:
        return []
    try:
        result = (
            Query()
            .select("name", "close", "change", "volume", "relative_volume_10d_calc",
                    "market_cap_basic", "sector")
            .where(
                Column("type").isin(["stock"]),
                Column("exchange").isin(["NASDAQ", "NYSE"]),
                Column("close") > 5,
                Column("relative_volume_10d_calc") > 1.5,
                Column("change") > 2,
            )
            .order_by("relative_volume_10d_calc", ascending=False)
            .limit(max(limit * 2, 20))
            .get_scanner_data()
        )
    except Exception as e:
        log.warning("[discovery] TV volume-breakout scan failed: %s", e)
        return []
    return _tv_rows_to_dicts(result)


def _tv_bollinger_squeezes(limit: int) -> list[dict]:
    """Bollinger-Band squeeze scan via tradingview-screener."""
    try:
        from tradingview_screener import Query, Column
    except ImportError:
        return []
    try:
        result = (
            Query()
            .select("name", "close", "change", "volume", "BB.upper", "BB.lower",
                    "market_cap_basic", "sector")
            .where(
                Column("type").isin(["stock"]),
                Column("exchange").isin(["NASDAQ", "NYSE"]),
                Column("close") > 5,
                Column("volume") > 500_000,
            )
            .order_by("volume", ascending=False)
            .limit(max(limit * 2, 10))
            .get_scanner_data()
        )
    except Exception as e:
        log.warning("[discovery] TV bollinger-squeeze scan failed: %s", e)
        return []
    return _tv_rows_to_dicts(result)


def _tv_rows_to_dicts(scan_result) -> list[dict]:
    if scan_result is None:
        return []
    try:
        _count, df = scan_result
    except (TypeError, ValueError):
        df = scan_result
    if df is None or len(df) == 0:
        return []
    out: list[dict] = []
    for _, row in df.iterrows():
        try:
            out.append({
                "symbol": str(row.get("name", "") or row.get("ticker", "")).upper(),
                "price": float(row.get("close", 0) or 0),
                "change_pct": float(row.get("change", 0) or 0) / 100.0,
                "volume": int(float(row.get("volume", 0) or 0)),
                "sector": str(row.get("sector", "") or ""),
                "market_cap_usd": float(row.get("market_cap_basic", 0) or 0),
            })
        except (TypeError, ValueError):
            continue
    return out


def _apply_screener_floors(
    pool: dict[str, Candidate], cfg: Config, held: set[str]
) -> dict[str, Candidate]:
    min_price = float(cfg.get("screener", "min_price", default=0) or 0)
    min_volume = int(cfg.get("screener", "min_avg_volume", default=0) or 0)
    min_mcap = float(cfg.get("screener", "min_market_cap_usd", default=0) or 0)
    min_dollar_volume = float(
        cfg.get("screener", "min_dollar_volume_usd", default=0) or 0
    )
    out: dict[str, Candidate] = {}
    dropped = 0
    dropped_dollar_volume = 0
    for sym, cand in pool.items():
        if cand.is_held:
            out[sym] = cand
            continue
        if cand.price > 0 and cand.price < min_price:
            dropped += 1
            continue
        if cand.volume > 0 and cand.volume < min_volume:
            dropped += 1
            continue
        if cand.market_cap_usd > 0 and cand.market_cap_usd < min_mcap:
            dropped += 1
            continue
        # Dollar-volume floor: drops thin/choppy names where price * volume
        # is too small for our position sizes. Only enforced when both price
        # and volume are populated; held positions are exempted above.
        if (
            min_dollar_volume > 0
            and cand.price > 0
            and cand.volume > 0
            and (cand.price * cand.volume) < min_dollar_volume
        ):
            dropped += 1
            dropped_dollar_volume += 1
            continue
        out[sym] = cand
    if dropped:
        log.info(
            "[discovery] screener floors dropped %d symbols (%d below dollar-volume floor)",
            dropped, dropped_dollar_volume,
        )
    return out


def _annotate_discovery_priorities(pool: dict[str, Candidate]) -> None:
    for cand in pool.values():
        score, reasons = discovery_priority_score(
            cand.sources,
            change_pct=cand.change_pct,
            volume=cand.volume,
        )
        cand.discovery_priority_score = score
        cand.discovery_priority_reasons = reasons


def _apply_sector_cap(
    pool: dict[str, Candidate], cfg: Config, held: set[str]
) -> dict[str, Candidate]:
    pct_cap = float(cfg.get("discovery", "max_pool_per_sector", default=0.40) or 0.40)
    if pct_cap >= 1.0 or pct_cap <= 0:
        return pool
    total = len(pool)
    if total == 0:
        return pool
    max_per_sector = max(1, int(total * pct_cap))
    by_sector: dict[str, list[Candidate]] = defaultdict(list)
    for cand in pool.values():
        by_sector[cand.sector].append(cand)
    keep: dict[str, Candidate] = {}
    dropped = 0
    for sector, members in by_sector.items():
        # Held equities are required in the selector input so the AI can exit
        # them, but they do not consume the non-held discovery quota. Non-held
        # names compete on active discovery priority, not source count or
        # watchlist membership.
        held_members = [c for c in members if c.is_held]
        rest = [c for c in members if not c.is_held]
        rest.sort(
            key=lambda c: (
                -float(c.discovery_priority_score or 0.0),
                -abs(float(c.change_pct or 0.0)),
                c.symbol,
            )
        )
        kept = held_members + rest[:max_per_sector]
        dropped += len(members) - len(kept)
        for c in kept:
            keep[c.symbol] = c
    if dropped:
        log.info("[discovery] sector cap (%.0f%%) dropped %d symbols", pct_cap * 100, dropped)
    return keep


def _truncate_pool(
    candidates: list[Candidate], pool_max: int, held: set[str]
) -> list[Candidate]:
    def _sort_key(c: Candidate) -> tuple[float, float, str]:
        return (
            -float(c.discovery_priority_score or 0.0),
            -abs(float(c.change_pct or 0.0)),
            c.symbol,
        )

    if len(candidates) <= pool_max:
        return sorted(candidates, key=_sort_key)
    held_candidates = [c for c in candidates if c.is_held]
    rest = [c for c in candidates if not c.is_held]
    # Rank by active discovery priority. Seed/dynamic watchlist membership is
    # eligibility-only and receives no priority bonus.
    rest.sort(
        key=lambda c: (
            -float(c.discovery_priority_score or 0.0),
            -abs(float(c.change_pct or 0.0)),
            c.symbol,
        )
    )
    keep_count = max(0, pool_max - len(held_candidates))
    truncated = sorted(held_candidates + rest[:keep_count], key=_sort_key)
    log.info("[discovery] truncated pool from %d to %d (held=%d kept all)",
             len(candidates), len(truncated), len(held_candidates))
    return truncated
