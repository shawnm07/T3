"""Sector-ETF watcher + rotation detector.

The bot's macro signal historically only looked at SPY/VIX/breadth — a market-
direction signal. On 2026-05-12 tech sold off hard while defensives held, and
the bot read "neutral" because SPY was only -0.4%. This module fetches the
GICS sector ETF complex (XLK/XLF/XLE/XLV/XLP/XLY/XLU/XLI/XLB/XLRE/XLC) and
produces:

- per-sector daily / 5-day / 20-day returns
- intraday relative strength vs SPY (since open)
- leading / lagging sector lists
- rotation_score: how much today's ranking differs from the 5-day ranking
- rotation_regime: "stable" | "rotating" | "panic_rotation"

Output is consumed by:
- macro.py (adds sector_regime to the macro signal)
- intraday_tape.py (per-sector tape_badness)
- candidate_scoring.py (sector-relative penalty)
- premarket_brief.py (heatmap)
- orchestrator open-of-day audit
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config import Config

log = logging.getLogger(__name__)


@dataclass
class SectorSnapshot:
    symbol: str
    sector_name: str
    price: float
    ret_1d: float
    ret_5d: float
    ret_20d: float
    intraday_change_pct: float
    intraday_rs_vs_spy: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "sector_name": self.sector_name,
            "price": round(float(self.price), 4),
            "ret_1d": round(float(self.ret_1d), 4),
            "ret_5d": round(float(self.ret_5d), 4),
            "ret_20d": round(float(self.ret_20d), 4),
            "intraday_change_pct": round(float(self.intraday_change_pct), 4),
            "intraday_rs_vs_spy": round(float(self.intraday_rs_vs_spy), 4),
        }


@dataclass
class SectorRegime:
    leading: list[str]           # top-3 sectors by today's intraday RS vs SPY
    lagging: list[str]           # bottom-3 sectors
    rotation_score: float        # 0..1 — how shuffled today's ranking is vs 5-day
    rotation_regime: str         # "stable" | "rotating" | "panic_rotation"
    defensives_leading: bool     # XLV/XLP/XLU all in leading set
    cyclicals_lagging: bool      # XLK/XLY/XLC all in lagging set
    snapshots: list[SectorSnapshot] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "leading": list(self.leading),
            "lagging": list(self.lagging),
            "rotation_score": round(float(self.rotation_score), 4),
            "rotation_regime": self.rotation_regime,
            "defensives_leading": bool(self.defensives_leading),
            "cyclicals_lagging": bool(self.cyclicals_lagging),
            "snapshots": [s.to_dict() for s in self.snapshots],
        }


# ----- cache helpers -----

def _cache_dir(cfg: Config) -> Path:
    raw = cfg.get("sector_rotation", "cache_dir", default="data/cache/sector_etfs")
    p = Path(str(raw))
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cache_path(cfg: Config) -> Path:
    return _cache_dir(cfg) / "snapshot.json"


def _load_cached(cfg: Config) -> dict[str, Any] | None:
    p = _cache_path(cfg)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except Exception:
        return None
    ttl = float(cfg.get("sector_rotation", "cache_ttl_minutes", default=15) or 15) * 60
    if time.time() - float(data.get("_ts", 0)) > ttl:
        return None
    return data


def _save_cached(cfg: Config, data: dict[str, Any]) -> None:
    try:
        d = dict(data, _ts=time.time())
        _cache_path(cfg).write_text(json.dumps(d, indent=2, default=str))
    except Exception as e:
        log.warning("sector_etfs cache save failed: %s", e)


# ----- public computation -----

def _rank(values: dict[str, float]) -> list[str]:
    return [s for s, _ in sorted(values.items(), key=lambda kv: kv[1], reverse=True)]


def _rotation_score(today_rank: list[str], five_day_rank: list[str]) -> float:
    """Spearman-style displacement, normalized to [0..1]."""
    if not today_rank or not five_day_rank:
        return 0.0
    five_day_index = {s: i for i, s in enumerate(five_day_rank)}
    n = max(len(today_rank), 1)
    displacement = 0.0
    for i, s in enumerate(today_rank):
        if s in five_day_index:
            displacement += abs(i - five_day_index[s])
    # Max displacement: reversed ranking → n*(n-1)/2 * 2 = n^2/2 approximately
    max_disp = (n * n) / 2.0 if n > 1 else 1.0
    return max(0.0, min(1.0, displacement / max_disp))


def compute_sector_regime(
    cfg: Config,
    snapshots: list[SectorSnapshot] | None = None,
    spy_today_change_pct: float = 0.0,
) -> SectorRegime:
    """Build the SectorRegime from per-ETF snapshots. If ``snapshots`` is
    None, returns an empty/neutral regime — caller is responsible for
    fetching via ``fetch_snapshots()``.
    """
    snaps = list(snapshots or [])
    if not snaps:
        return SectorRegime(
            leading=[], lagging=[], rotation_score=0.0,
            rotation_regime="stable", defensives_leading=False,
            cyclicals_lagging=False, snapshots=[],
        )
    # Rank by intraday RS vs SPY (live today's signal)
    intraday_rs = {s.symbol: float(s.intraday_rs_vs_spy) for s in snaps}
    # 5-day return rank
    five_d = {s.symbol: float(s.ret_5d) for s in snaps}
    today_rank = _rank(intraday_rs)
    five_rank = _rank(five_d)
    rscore = _rotation_score(today_rank, five_rank)
    alert = float(cfg.get("sector_rotation", "rotation_alert_score", default=0.50) or 0.50)
    if rscore < alert:
        regime = "stable"
    elif rscore < alert + 0.20:
        regime = "rotating"
    else:
        regime = "panic_rotation"
    leading = today_rank[:3]
    lagging = today_rank[-3:][::-1]  # worst first
    defensives = {"XLV", "XLP", "XLU"}
    cyclicals = {"XLK", "XLY", "XLC"}
    defensives_leading = len(defensives & set(leading)) >= 2
    cyclicals_lagging = len(cyclicals & set(lagging)) >= 2
    return SectorRegime(
        leading=leading,
        lagging=lagging,
        rotation_score=rscore,
        rotation_regime=regime,
        defensives_leading=defensives_leading,
        cyclicals_lagging=cyclicals_lagging,
        snapshots=snaps,
    )


def fetch_snapshots(cfg: Config, market_data: Any = None) -> list[SectorSnapshot]:
    """Pull current bars for each sector ETF and build snapshots.

    ``market_data`` is the project's existing data accessor (e.g. the object
    returned by ``src.market_data.get_market_data()``). If None or if any
    fetch fails, falls back to whatever is cached. Returns empty list on
    complete failure so callers degrade gracefully.
    """
    cached = _load_cached(cfg)
    if cached and not market_data:
        try:
            return [SectorSnapshot(**s) for s in cached.get("snapshots", [])]
        except Exception:
            pass
    etfs_map = cfg.get("sector_rotation", "etfs", default={}) or {}
    if not etfs_map or not market_data:
        return []
    snaps: list[SectorSnapshot] = []
    try:
        # Compute SPY's intraday change once for relative-strength baseline.
        spy_intraday = _get_intraday_change(market_data, "SPY")
    except Exception:
        spy_intraday = 0.0
    for symbol, sector_name in etfs_map.items():
        try:
            ret_1d = _get_period_return(market_data, symbol, days=1)
            ret_5d = _get_period_return(market_data, symbol, days=5)
            ret_20d = _get_period_return(market_data, symbol, days=20)
            intra = _get_intraday_change(market_data, symbol)
            price = _get_last_price(market_data, symbol)
        except Exception as e:
            log.info("[sector_etfs] %s fetch failed: %s", symbol, e)
            continue
        snaps.append(SectorSnapshot(
            symbol=symbol,
            sector_name=str(sector_name),
            price=float(price or 0.0),
            ret_1d=float(ret_1d or 0.0),
            ret_5d=float(ret_5d or 0.0),
            ret_20d=float(ret_20d or 0.0),
            intraday_change_pct=float(intra or 0.0),
            intraday_rs_vs_spy=float(intra or 0.0) - float(spy_intraday or 0.0),
        ))
    if snaps:
        _save_cached(cfg, {"snapshots": [s.to_dict() for s in snaps]})
    return snaps


# ----- adapter helpers (graceful w/ different market_data shapes) -----

def _get_last_price(market_data: Any, symbol: str) -> float:
    try:
        if hasattr(market_data, "last_price"):
            return float(market_data.last_price(symbol))
        if hasattr(market_data, "get_last_price"):
            return float(market_data.get_last_price(symbol))
        if hasattr(market_data, "intraday_bars"):
            df = market_data.intraday_bars(symbol, minutes=5)
            if df is not None and len(df):
                return float(df["close"].iloc[-1])
    except Exception:
        return 0.0
    return 0.0


def _get_intraday_change(market_data: Any, symbol: str) -> float:
    try:
        if hasattr(market_data, "intraday_change_pct"):
            return float(market_data.intraday_change_pct(symbol))
        if hasattr(market_data, "intraday_bars"):
            df = market_data.intraday_bars(symbol, minutes=5)
            if df is not None and len(df) >= 2:
                first = float(df["open"].iloc[0])
                last = float(df["close"].iloc[-1])
                return (last / first - 1.0) if first else 0.0
    except Exception:
        return 0.0
    return 0.0


def _get_period_return(market_data: Any, symbol: str, days: int) -> float:
    try:
        if hasattr(market_data, "period_return_pct"):
            return float(market_data.period_return_pct(symbol, days=days))
        if hasattr(market_data, "daily_bars"):
            df = market_data.daily_bars(symbol, lookback_days=max(days + 5, 25))
            if df is not None and len(df) >= days + 1:
                first = float(df["close"].iloc[-(days + 1)])
                last = float(df["close"].iloc[-1])
                return (last / first - 1.0) if first else 0.0
    except Exception:
        return 0.0
    return 0.0


# ----- candidate-scoring helper -----

def sector_relative_score_adjustment(
    cfg: Config,
    candidate_sector: str | None,
    regime: SectorRegime,
) -> tuple[float, dict[str, Any]]:
    """Return (score_adjustment_points, audit). Positive = sector is leading
    (boost candidate), negative = lagging (penalize).
    """
    if not candidate_sector or not regime or not regime.snapshots:
        return 0.0, {"reason": "no_data"}
    pts_per_pct = float(
        cfg.get("sector_rotation", "sector_relative_score_pct_to_points", default=50.0) or 50.0
    )
    # Find matching snapshot
    target = None
    for snap in regime.snapshots:
        if snap.sector_name.strip().lower() == str(candidate_sector).strip().lower():
            target = snap
            break
    if target is None:
        return 0.0, {"reason": "sector_etf_not_found", "candidate_sector": candidate_sector}
    adj = target.intraday_rs_vs_spy * pts_per_pct
    # Hard clamp so a 5% sector divergence doesn't dominate the entire score
    adj = max(-30.0, min(30.0, adj))
    return round(adj, 2), {
        "sector": target.sector_name,
        "sector_etf": target.symbol,
        "sector_rs_vs_spy_pct": round(target.intraday_rs_vs_spy, 4),
        "points": round(adj, 2),
    }


def lagging_sector_etfs(regime: SectorRegime) -> set[str]:
    """ETF symbols that map to the lagging sectors (caller can use to flag
    held positions for pro-active trim)."""
    return set(regime.lagging or [])


def held_position_in_lagging(
    cfg: Config,
    held_sectors: dict[str, str],
    regime: SectorRegime,
) -> list[dict[str, Any]]:
    """Return per-symbol audit rows for held positions whose sector is in
    the lagging set with RS worse than the proactive-trim threshold.
    ``held_sectors`` is symbol -> GICS sector string.
    """
    threshold = float(
        cfg.get("sector_rotation", "proactive_trim_rs_threshold", default=-0.010) or -0.010
    )
    trim_pct = float(cfg.get("sector_rotation", "proactive_trim_pct", default=0.25) or 0.25)
    sector_to_rs = {
        s.sector_name.strip().lower(): s.intraday_rs_vs_spy
        for s in (regime.snapshots or [])
    }
    flagged: list[dict[str, Any]] = []
    lagging_names = set()
    for etf in regime.lagging or []:
        for snap in regime.snapshots:
            if snap.symbol == etf:
                lagging_names.add(snap.sector_name.strip().lower())
    for sym, sector in (held_sectors or {}).items():
        key = str(sector or "").strip().lower()
        if key not in lagging_names:
            continue
        rs = float(sector_to_rs.get(key, 0.0))
        if rs > threshold:
            continue
        flagged.append({
            "symbol": sym,
            "sector": sector,
            "sector_rs_vs_spy": round(rs, 4),
            "proposed_trim_pct": trim_pct,
            "reason": "held_position_in_lagging_sector",
        })
    return flagged
