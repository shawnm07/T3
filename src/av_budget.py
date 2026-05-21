"""Alpha Vantage budget tracker.

AV plan = 75 req/min, 5 concurrent. Today (2026-05-11) the bot silently hit
throttling on NEWS_SENTIMENT and TIME_SERIES_DAILY because four scans/day
× 50 symbols × multiple endpoints is bursty. This module tracks request
counts in a rolling window and exposes ``remaining_pct()`` so non-critical
fetches (news sentiment) can be deferred when the budget is low.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from src.config import Config

log = logging.getLogger(__name__)


def _state_path(cfg: Config) -> Path:
    raw = cfg.get("av_budget", "state_file", default="data/state/av_budget.json")
    p = Path(str(raw))
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load(cfg: Config) -> dict[str, Any]:
    p = _state_path(cfg)
    if not p.exists():
        return {"requests": []}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"requests": []}


def _save(cfg: Config, state: dict[str, Any]) -> None:
    try:
        _state_path(cfg).write_text(json.dumps(state, indent=2))
    except Exception as e:
        log.warning("av_budget: save failed: %s", e)


def record_request(cfg: Config, endpoint: str = "unknown", now: float | None = None) -> None:
    if not bool(cfg.get("av_budget", "enabled", default=False)):
        return
    state = _load(cfg)
    ts = float(now or time.time())
    state.setdefault("requests", []).append({"ts": ts, "endpoint": endpoint})
    # Trim anything older than 5 min — only need the rolling 60s for budget,
    # the rest is kept for diagnostics.
    cutoff = ts - 300
    state["requests"] = [r for r in state["requests"] if float(r.get("ts", 0)) >= cutoff]
    _save(cfg, state)


def used_last_minute(cfg: Config, now: float | None = None) -> int:
    state = _load(cfg)
    cutoff = float(now or time.time()) - 60.0
    return sum(1 for r in state.get("requests", []) if float(r.get("ts", 0)) >= cutoff)


def remaining_pct(cfg: Config, now: float | None = None) -> float:
    limit = float(cfg.get("av_budget", "rate_limit_per_min", default=75) or 75)
    used = used_last_minute(cfg, now=now)
    return max(0.0, 1.0 - (used / limit)) if limit > 0 else 1.0


def should_defer_non_critical(cfg: Config, now: float | None = None) -> bool:
    if not bool(cfg.get("av_budget", "enabled", default=False)):
        return False
    floor = float(cfg.get("av_budget", "defer_below_pct", default=0.20) or 0.20)
    return remaining_pct(cfg, now=now) < floor
