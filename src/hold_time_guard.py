"""Minimum-hold-time guard.

A freshly opened position cannot be discretionary-exited within
``risk.min_hold_minutes`` of its entry unless AI confidence is at least
``risk.min_hold_override_confidence``. Stop-losses are exempt — they fire
regardless. The point is to block the 1-hour round-trip churn pattern
(WDC 10:00→11:00) without removing risk discipline.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from src.config import Config

log = logging.getLogger(__name__)


def _parse_entry_ts(entry_time: Any) -> float | None:
    if entry_time is None:
        return None
    if isinstance(entry_time, (int, float)):
        return float(entry_time)
    if isinstance(entry_time, datetime):
        if entry_time.tzinfo is None:
            return entry_time.replace(tzinfo=timezone.utc).timestamp()
        return entry_time.timestamp()
    try:
        s = str(entry_time).rstrip("Z")
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def should_block_discretionary_exit(
    cfg: Config,
    *,
    entry_time: Any,
    confidence: float,
    is_stop_loss: bool = False,
    now: float | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Return (blocked, audit).

    Block when (now - entry_time) < min_hold_minutes AND confidence is below
    the override threshold AND this is not a stop-loss exit.
    """
    minutes = float(cfg.get("risk", "min_hold_minutes", default=0) or 0)
    if minutes <= 0:
        return False, {"reason": "disabled"}
    if is_stop_loss:
        return False, {"reason": "stop_loss_exempt"}
    entry_ts = _parse_entry_ts(entry_time)
    if entry_ts is None:
        return False, {"reason": "no_entry_time"}
    age_min = ((now or time.time()) - entry_ts) / 60.0
    if age_min >= minutes:
        return False, {"reason": "hold_window_elapsed", "age_minutes": age_min}
    override = float(cfg.get("risk", "min_hold_override_confidence", default=0.80) or 0.80)
    if float(confidence or 0.0) >= override:
        return False, {
            "reason": "high_confidence_override",
            "age_minutes": age_min,
            "confidence": float(confidence),
            "override_threshold": override,
        }
    return True, {
        "reason": "min_hold_active",
        "age_minutes": age_min,
        "min_hold_minutes": minutes,
        "confidence": float(confidence or 0.0),
        "override_threshold": override,
    }
