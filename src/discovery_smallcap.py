"""Small-cap momentum discovery lane.

The main ``discovery.py`` filters at min_market_cap_usd=$2B / min_price=$5 —
which is correct for the bulk of swing entries but blinds the bot to the
dispersion-day winners (AKAN +44.5%, KFRC +43.3%, EDSA +27.7% on 2026-05-11).
This lane runs in parallel with stricter scoring gates and a hard candidate
cap so the AI cost stays roughly flat.

Eligibility (config ``discovery.smallcap_lane``):
- market_cap >= min_market_cap_usd (default $300M, vs $2B on main lane)
- price >= min_price (default $3)
- 20d avg dollar volume >= min_dollar_volume_usd (default $25M)

Scoring gate (applied AFTER fundamentals/technicals/sentiment):
- technical_score >= min_technical_score (default 0.50)
- sentiment_score >= min_sentiment_score (default 0.30)

Returns at most ``max_candidates`` symbols that pass all gates.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable

from src.config import Config

log = logging.getLogger(__name__)


@dataclass
class SmallcapCandidate:
    symbol: str
    market_cap: float
    price: float
    avg_dollar_volume_20d: float
    pct_change: float
    source: str
    sector: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "market_cap": float(self.market_cap),
            "price": float(self.price),
            "avg_dollar_volume_20d": float(self.avg_dollar_volume_20d),
            "pct_change": float(self.pct_change),
            "source": self.source,
            "sector": self.sector,
            "lane": "smallcap",
        }


def is_lane_enabled(cfg: Config) -> bool:
    return bool(cfg.get("discovery", "smallcap_lane", "enabled", default=False))


def eligible(cfg: Config, raw: dict[str, Any]) -> bool:
    """Universe-level eligibility check (no scoring required)."""
    if not is_lane_enabled(cfg):
        return False
    min_cap = float(cfg.get("discovery", "smallcap_lane", "min_market_cap_usd", default=300_000_000) or 0)
    min_price = float(cfg.get("discovery", "smallcap_lane", "min_price", default=3.0) or 0)
    min_dv = float(cfg.get("discovery", "smallcap_lane", "min_dollar_volume_usd", default=25_000_000) or 0)
    try:
        mc = float(raw.get("market_cap", 0) or 0)
        px = float(raw.get("price", 0) or 0)
        dv = float(raw.get("avg_dollar_volume_20d", raw.get("dollar_volume", 0)) or 0)
    except (TypeError, ValueError):
        return False
    if mc < min_cap:
        return False
    if px < min_price:
        return False
    if dv < min_dv:
        return False
    return True


def filter_universe(
    cfg: Config,
    raw_candidates: Iterable[dict[str, Any]],
) -> list[SmallcapCandidate]:
    out: list[SmallcapCandidate] = []
    for raw in raw_candidates:
        if not eligible(cfg, raw):
            continue
        sym = str(raw.get("symbol", "")).upper().strip()
        if not sym:
            continue
        try:
            out.append(SmallcapCandidate(
                symbol=sym,
                market_cap=float(raw.get("market_cap", 0) or 0),
                price=float(raw.get("price", 0) or 0),
                avg_dollar_volume_20d=float(raw.get(
                    "avg_dollar_volume_20d", raw.get("dollar_volume", 0)) or 0),
                pct_change=float(raw.get("pct_change", 0) or 0),
                source=str(raw.get("source", "unknown")),
                sector=raw.get("sector"),
            ))
        except (TypeError, ValueError):
            continue
    return out


def score_and_select(
    cfg: Config,
    candidates: Iterable[SmallcapCandidate],
    technical_scores: dict[str, float],
    sentiment_scores: dict[str, float] | None = None,
    dilution_flags: dict[str, bool] | None = None,
) -> list[dict[str, Any]]:
    """Apply scoring gates and return up to max_candidates as dicts."""
    if not is_lane_enabled(cfg):
        return []
    min_tech = float(cfg.get("discovery", "smallcap_lane", "min_technical_score", default=0.50) or 0)
    min_sent = float(cfg.get("discovery", "smallcap_lane", "min_sentiment_score", default=0.30) or 0)
    cap = int(cfg.get("discovery", "smallcap_lane", "max_candidates", default=10) or 10)
    sent = sentiment_scores or {}
    dil = dilution_flags or {}

    selected: list[tuple[SmallcapCandidate, float]] = []
    for cand in candidates:
        ts = float(technical_scores.get(cand.symbol, 0.0) or 0.0)
        if ts < min_tech:
            continue
        ss = float(sent.get(cand.symbol, 0.0) or 0.0)
        if ss < min_sent:
            continue
        if dil.get(cand.symbol):
            log.info("[smallcap_lane] %s rejected: dilution flag", cand.symbol)
            continue
        # Rank by blended momentum signal
        rank = 0.6 * ts + 0.25 * ss + 0.15 * min(1.0, max(0.0, cand.pct_change / 10.0))
        selected.append((cand, rank))

    selected.sort(key=lambda row: row[1], reverse=True)
    selected = selected[:cap]
    out = []
    for cand, rank in selected:
        d = cand.to_dict()
        d["smallcap_rank_score"] = round(float(rank), 4)
        out.append(d)
    if out:
        log.info("[smallcap_lane] %d candidates selected: %s",
                 len(out), [d["symbol"] for d in out])
    return out
