"""Open-of-day position audit.

First scan of the day: examine every held position. If its sector is in
today's bottom-2 (per sector_etfs) and the sector is materially weaker than
SPY, propose a pre-emptive trim. The orchestrator can either feed these
into the selector context (preferred) or short-circuit the rebalance to
trim before any new entries.

This is the fix for 2026-05-12's 07:03 UTC self-inflicted hole: bot held
VRT in ai_data_center, sold it after the morning damage, then re-bought
AMD in the same theme on the same scan. Open-of-day audit would have
flagged "ai_data_center is in today's bottom-2 sectors" BEFORE any new
entry decision.
"""
from __future__ import annotations

import logging
from typing import Any

from src.config import Config
from src.sector_etfs import held_position_in_lagging

log = logging.getLogger(__name__)


def is_first_scan_of_day(scan_type: str) -> bool:
    return str(scan_type or "").strip().upper() in ("FIRST", "FIRST_OF_DAY", "PREMARKET")


def audit(
    cfg: Config,
    scan_type: str,
    held_sectors: dict[str, str],
    sector_regime: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return an audit dict. Always safe to call (empty result when disabled
    or not first scan)."""
    if not bool(cfg.get("open_of_day_audit", "enabled", default=False)):
        return {"status": "disabled"}
    if not is_first_scan_of_day(scan_type):
        return {"status": "skipped_not_first_scan"}
    if not sector_regime:
        return {"status": "no_sector_regime"}
    # Lift sector_regime dict back into the dataclass-like structure expected
    # by held_position_in_lagging. We reuse the dict accessor since
    # SectorRegime.to_dict() is what's likely passed in.
    from src.sector_etfs import SectorRegime, SectorSnapshot
    try:
        snaps = [
            SectorSnapshot(
                symbol=s.get("symbol"),
                sector_name=s.get("sector_name", ""),
                price=float(s.get("price", 0) or 0),
                ret_1d=float(s.get("ret_1d", 0) or 0),
                ret_5d=float(s.get("ret_5d", 0) or 0),
                ret_20d=float(s.get("ret_20d", 0) or 0),
                intraday_change_pct=float(s.get("intraday_change_pct", 0) or 0),
                intraday_rs_vs_spy=float(s.get("intraday_rs_vs_spy", 0) or 0),
            )
            for s in (sector_regime.get("snapshots") or [])
        ]
        regime = SectorRegime(
            leading=sector_regime.get("leading") or [],
            lagging=sector_regime.get("lagging") or [],
            rotation_score=float(sector_regime.get("rotation_score", 0) or 0),
            rotation_regime=str(sector_regime.get("rotation_regime", "stable")),
            defensives_leading=bool(sector_regime.get("defensives_leading")),
            cyclicals_lagging=bool(sector_regime.get("cyclicals_lagging")),
            snapshots=snaps,
        )
    except Exception as e:
        return {"status": "error", "error": str(e)}
    flagged = held_position_in_lagging(cfg, held_sectors, regime)
    return {
        "status": "ok",
        "flagged_count": len(flagged),
        "flagged": flagged,
        "rotation_regime": regime.rotation_regime,
        "leading": regime.leading,
        "lagging": regime.lagging,
    }
