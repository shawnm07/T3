"""Defensive ETF lane.

When ``sector_rotation`` detects a rotation day AND defensives are leading,
this lane injects ``defensive_lane.etfs`` (XLV/XLP/XLU/SHV/BIL/TLT) into the
candidate pool with a priority bump so the selector is forced to evaluate
them.

Output is a list of synthetic candidates that look like ordinary discovery
rows so they slot into the existing selector input format.
"""
from __future__ import annotations

import logging
from typing import Any

from src.config import Config

log = logging.getLogger(__name__)


def is_lane_active(cfg: Config, sector_regime: dict[str, Any] | None) -> bool:
    if not bool(cfg.get("defensive_lane", "enabled", default=False)):
        return False
    if not sector_regime:
        return False
    if not bool(sector_regime.get("defensives_leading")):
        return False
    rotation_alert = float(
        cfg.get("sector_rotation", "rotation_alert_score", default=0.50) or 0.50
    )
    return float(sector_regime.get("rotation_score", 0.0) or 0.0) >= rotation_alert


def build_defensive_candidates(
    cfg: Config,
    sector_regime: dict[str, Any] | None,
    market_data: Any = None,
) -> list[dict[str, Any]]:
    """Return synthetic candidate dicts for each eligible defensive ETF.
    Caller appends these to the discovery pool before AI ranking.
    """
    if not is_lane_active(cfg, sector_regime):
        return []
    etfs = cfg.get("defensive_lane", "etfs", default=[]) or []
    out: list[dict[str, Any]] = []
    snapshots_by_sym = {s.get("symbol"): s for s in (sector_regime.get("snapshots") or [])}
    for sym in etfs:
        snap = snapshots_by_sym.get(sym, {})
        intra = float(snap.get("intraday_change_pct", 0.0) or 0.0)
        out.append({
            "symbol": str(sym).upper(),
            "source": "defensive_lane",
            "lane": "defensive",
            "intraday_change_pct": intra,
            "discovery_priority_score": 70 + max(0.0, intra * 100.0),
            "reason": "rotation_day_defensives_leading",
        })
    if out:
        log.info("[defensive_lane] injecting %d defensive ETFs: %s",
                 len(out), [c["symbol"] for c in out])
    return out


def required_evaluation_set(cfg: Config) -> set[str]:
    """Symbols the selector MUST evaluate at minimum when the lane is
    active. Used by the orchestrator to surface a warning if any are
    missing from selector output.
    """
    min_eval = int(cfg.get("defensive_lane", "require_min_evaluated", default=2) or 2)
    etfs = list(cfg.get("defensive_lane", "etfs", default=[]) or [])
    return set(etfs[:min_eval])
