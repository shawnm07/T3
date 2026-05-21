"""Daily trade-count circuit breaker.

The bot is a swing strategy. >8 fills/day signals churn, not edge. This
module counts non-stop fills against ``risk.max_daily_fills`` and forces
the rest of the day to HOLD-only when exceeded.

Stop-loss fills do NOT count — risk discipline still operates.
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

_STATE_FILE = "data/state/daily_fill_cap.json"


def _state_path() -> Path:
    p = Path(__file__).resolve().parents[1] / _STATE_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _today_key(now: float | None = None) -> str:
    ts = now or time.time()
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def _load() -> dict[str, Any]:
    p = _state_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _save(state: dict[str, Any]) -> None:
    try:
        _state_path().write_text(json.dumps(state, indent=2, sort_keys=True))
    except Exception as e:
        log.warning("daily_fill_cap: save failed: %s", e)


def record_fill(
    symbol: str,
    is_stop_loss: bool = False,
    now: float | None = None,
) -> int:
    """Append a fill to today's counter. Stop fills are recorded separately
    and do NOT advance the cap counter. Returns the post-increment counted
    fill total for today (0 for stop fills).
    """
    state = _load()
    key = _today_key(now)
    day = state.setdefault(key, {"counted_fills": 0, "stop_fills": 0, "log": []})
    if is_stop_loss:
        day["stop_fills"] = int(day.get("stop_fills", 0)) + 1
    else:
        day["counted_fills"] = int(day.get("counted_fills", 0)) + 1
    day["log"].append({
        "ts": float(now or time.time()),
        "symbol": str(symbol).upper(),
        "is_stop": bool(is_stop_loss),
    })
    # Trim history
    state = {k: v for k, v in state.items() if k >= _today_key(time.time() - 7 * 86400)}
    state[key] = day
    _save(state)
    return int(day["counted_fills"])


def fills_today(now: float | None = None) -> int:
    return int(_load().get(_today_key(now), {}).get("counted_fills", 0))


def is_capped(cfg: Config, now: float | None = None) -> tuple[bool, dict[str, Any]]:
    cap = int(cfg.get("risk", "max_daily_fills", default=0) or 0)
    if cap <= 0:
        return False, {"reason": "disabled"}
    cur = fills_today(now)
    if cur >= cap:
        return True, {
            "reason": "daily_fill_cap_reached",
            "fills_today": cur,
            "cap": cap,
        }
    return False, {"reason": "under_cap", "fills_today": cur, "cap": cap}
