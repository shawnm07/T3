"""Scanning-failure streak detector + alert.

On 2026-05-11 the preclose evaluated 3 candidates and rejected all 3
(conf 0.42 / 0.38 / 0.22 < threshold 0.45). One day of that is fine —
the tape may genuinely be uninvestable. But 3 straight days of 100%
rejection signals a mis-calibrated gate or a vendor data outage that
needs a human eye. This module tracks the streak and pings Telegram
when it crosses ``scanning_failure_alert.consecutive_days``.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import Config

log = logging.getLogger(__name__)


def _state_path(cfg: Config) -> Path:
    raw = cfg.get(
        "scanning_failure_alert", "state_file",
        default="data/state/scanning_failure_streak.json",
    )
    p = Path(str(raw))
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load(cfg: Config) -> dict[str, Any]:
    p = _state_path(cfg)
    if not p.exists():
        return {"streak": 0, "last_day": None}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"streak": 0, "last_day": None}


def _save(cfg: Config, state: dict[str, Any]) -> None:
    try:
        _state_path(cfg).write_text(json.dumps(state, indent=2, sort_keys=True))
    except Exception as e:
        log.warning("scanning_failure_alert: save failed: %s", e)


def _today_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def record_scan_outcome(
    cfg: Config,
    *,
    candidates_evaluated: int,
    candidates_accepted: int,
) -> dict[str, Any]:
    """Update the streak counter and return current state + alert flag.

    A "failure" day is: candidates_evaluated > 0 AND candidates_accepted == 0.
    Days with no candidates evaluated (e.g. macro halt) are ignored.
    """
    if not bool(cfg.get("scanning_failure_alert", "enabled", default=False)):
        return {"status": "disabled"}
    state = _load(cfg)
    today = _today_key()
    if state.get("last_day") == today:
        # Idempotent within a day — first call wins for the streak increment.
        return {**state, "should_alert": False, "status": "already_recorded_today"}
    failure = candidates_evaluated > 0 and candidates_accepted == 0
    if failure:
        state["streak"] = int(state.get("streak", 0)) + 1
    elif candidates_evaluated > 0:
        state["streak"] = 0
    state["last_day"] = today
    state["last_evaluated"] = int(candidates_evaluated)
    state["last_accepted"] = int(candidates_accepted)
    state["last_ts"] = time.time()
    threshold = int(cfg.get("scanning_failure_alert", "consecutive_days", default=3) or 3)
    should_alert = bool(failure and state["streak"] >= threshold)
    state["should_alert"] = should_alert
    _save(cfg, state)
    if should_alert:
        log.warning(
            "[scanning_failure_alert] streak=%d crossing threshold=%d",
            state["streak"], threshold,
        )
    return state
