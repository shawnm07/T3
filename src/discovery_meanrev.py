"""Mean-reversion / dip-buy discovery lane.

The bot's primary discovery path is momentum-continuation (gainers, breakouts,
EMA-above). On 2026-05-12 the comeback was driven by the bot waiting for
tape recovery and then chasing names that had already bounced. A dip-buy
path would have caught NVDA/UNH near the trough.

Eligibility (config ``mean_reversion_lane``):
- High-quality only: ``min_market_cap_usd`` AND optionally ``require_sp500``.
- Down ≥ ``min_intraday_drop_pct`` AND ≥ ``min_drop_vs_5d_high_pct``.
- RSI(14) intraday < ``max_rsi`` (oversold).
- Reversal pattern: ``require_higher_low_30m`` AND
  ``min_intraday_rs_vs_sector`` (positive RS vs candidate's own sector).

Output is up to ``max_candidates`` entries, intended to run in parallel with
the momentum lane. A separate confidence floor (``buy_threshold_confidence``)
applies — typically lower than the momentum gate because the holding period
is expected to be short.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable

from src.config import Config

log = logging.getLogger(__name__)


@dataclass
class MeanRevCandidate:
    symbol: str
    sector: str | None
    market_cap: float
    last_price: float
    intraday_change_pct: float
    drop_vs_5d_high_pct: float
    rsi_14: float
    higher_low_30m: bool
    intraday_rs_vs_sector_pct: float
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "sector": self.sector,
            "market_cap": float(self.market_cap),
            "last_price": float(self.last_price),
            "intraday_change_pct": float(self.intraday_change_pct),
            "drop_vs_5d_high_pct": float(self.drop_vs_5d_high_pct),
            "rsi_14": float(self.rsi_14),
            "higher_low_30m": bool(self.higher_low_30m),
            "intraday_rs_vs_sector_pct": float(self.intraday_rs_vs_sector_pct),
            "reasons": list(self.reasons),
            "lane": "mean_reversion",
        }


def is_lane_enabled(cfg: Config) -> bool:
    return bool(cfg.get("mean_reversion_lane", "enabled", default=False))


def _passes(cfg: Config, raw: dict[str, Any], sp500_set: set[str] | None) -> tuple[bool, list[str]]:
    """Return (eligible, reasons_or_rejects)."""
    reasons: list[str] = []
    symbol = str(raw.get("symbol", "")).upper()
    if not symbol:
        return False, ["no_symbol"]
    if bool(cfg.get("mean_reversion_lane", "require_sp500", default=True)):
        if sp500_set and symbol not in sp500_set:
            return False, ["not_sp500"]
    try:
        mc = float(raw.get("market_cap", 0) or 0)
        intra = float(raw.get("intraday_change_pct", 0) or 0)
        drop = float(raw.get("drop_vs_5d_high_pct", 0) or 0)
        rsi = float(raw.get("rsi_14", 50) or 50)
        hl30 = bool(raw.get("higher_low_30m", False))
        rs_sec = float(raw.get("intraday_rs_vs_sector_pct", 0) or 0)
    except (TypeError, ValueError):
        return False, ["malformed_input"]
    min_cap = float(cfg.get("mean_reversion_lane", "min_market_cap_usd", default=20e9) or 0)
    if mc < min_cap:
        return False, ["below_market_cap_floor"]
    min_drop = float(cfg.get("mean_reversion_lane", "min_intraday_drop_pct", default=0.03) or 0.03)
    min_drop_5d = float(cfg.get("mean_reversion_lane", "min_drop_vs_5d_high_pct", default=0.05) or 0.05)
    if -intra < min_drop:
        return False, [f"intraday_drop_only_{intra:+.3f}"]
    if -drop < min_drop_5d:
        return False, [f"drop_vs_5d_high_only_{drop:+.3f}"]
    max_rsi = float(cfg.get("mean_reversion_lane", "max_rsi", default=35) or 35)
    if rsi > max_rsi:
        return False, [f"rsi_too_high_{rsi:.1f}"]
    if bool(cfg.get("mean_reversion_lane", "require_higher_low_30m", default=True)) and not hl30:
        return False, ["no_higher_low_30m"]
    min_rs = float(cfg.get("mean_reversion_lane", "min_intraday_rs_vs_sector", default=0.0) or 0.0)
    if rs_sec < min_rs:
        return False, [f"weak_vs_sector_{rs_sec:+.3f}"]
    reasons.append("oversold")
    if hl30:
        reasons.append("higher_low_30m")
    if rs_sec > 0:
        reasons.append("outperforming_sector_intraday")
    return True, reasons


def discover_dipbuys(
    cfg: Config,
    raw_candidates: Iterable[dict[str, Any]],
    sp500_set: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not is_lane_enabled(cfg):
        return []
    cap = int(cfg.get("mean_reversion_lane", "max_candidates", default=3) or 3)
    accepted: list[MeanRevCandidate] = []
    for raw in raw_candidates:
        ok, reasons = _passes(cfg, raw, sp500_set)
        if not ok:
            continue
        try:
            accepted.append(MeanRevCandidate(
                symbol=str(raw["symbol"]).upper(),
                sector=raw.get("sector"),
                market_cap=float(raw.get("market_cap", 0) or 0),
                last_price=float(raw.get("last_price", 0) or 0),
                intraday_change_pct=float(raw.get("intraday_change_pct", 0) or 0),
                drop_vs_5d_high_pct=float(raw.get("drop_vs_5d_high_pct", 0) or 0),
                rsi_14=float(raw.get("rsi_14", 0) or 0),
                higher_low_30m=bool(raw.get("higher_low_30m", False)),
                intraday_rs_vs_sector_pct=float(raw.get("intraday_rs_vs_sector_pct", 0) or 0),
                reasons=reasons,
            ))
        except Exception:
            continue
    # Rank: stronger sector RS + cleaner higher-low + bigger drop = bigger bounce
    def _rank(c: MeanRevCandidate) -> float:
        return (
            (-c.intraday_change_pct) * 0.40
            + max(0.0, c.intraday_rs_vs_sector_pct) * 0.30
            + (1.0 if c.higher_low_30m else 0.0) * 0.20
            + max(0.0, (40.0 - c.rsi_14) / 40.0) * 0.10
        )
    accepted.sort(key=_rank, reverse=True)
    accepted = accepted[:cap]
    if accepted:
        log.info(
            "[meanrev_lane] %d dip-buy candidates: %s",
            len(accepted), [c.symbol for c in accepted],
        )
    return [c.to_dict() for c in accepted]
