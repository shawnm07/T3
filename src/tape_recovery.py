"""Tape-recovery detector — the "comeback" signal.

Watches consecutive tape_badness readings. When badness peaks then falls
for ``tape_recovery.consecutive_falling_bars`` scans, ``is_recovering()``
flips True and the selector receives a small opportunity-score boost so it
deploys *as* the tape clears, not after.

This codifies what saved 2026-05-12: bot waited for tape to clear then
chased; with this signal, it would deploy 1-2 scans earlier and capture
more of the comeback move.
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
    raw = cfg.get(
        "tape_recovery", "state_file",
        default="data/state/tape_recovery.json",
    )
    p = Path(str(raw))
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load(cfg: Config) -> dict[str, Any]:
    p = _state_path(cfg)
    if not p.exists():
        return {"history": [], "recovering": False}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"history": [], "recovering": False}


def _save(cfg: Config, state: dict[str, Any]) -> None:
    try:
        _state_path(cfg).write_text(json.dumps(state, indent=2))
    except Exception as e:
        log.warning("tape_recovery save failed: %s", e)


def record_and_detect(
    cfg: Config,
    tape_badness: float,
    now: float | None = None,
) -> dict[str, Any]:
    """Append the latest badness reading, prune history older than today,
    and return current detector state including ``recovering`` flag and
    ``opportunity_score_boost``.
    """
    if not bool(cfg.get("tape_recovery", "enabled", default=False)):
        return {"enabled": False, "recovering": False, "opportunity_score_boost": 0}
    state = _load(cfg)
    ts = float(now or time.time())
    history: list[dict[str, Any]] = list(state.get("history") or [])
    history.append({"ts": ts, "badness": float(tape_badness or 0.0)})
    # Keep last 24h
    cutoff = ts - 24 * 3600
    history = [h for h in history if float(h.get("ts", 0)) >= cutoff]
    state["history"] = history
    consecutive = int(cfg.get("tape_recovery", "consecutive_falling_bars", default=2) or 2)
    recovering = False
    if len(history) >= consecutive + 1:
        peak_idx = max(range(len(history)), key=lambda i: history[i]["badness"])
        if peak_idx <= len(history) - consecutive - 1:
            # peak older than `consecutive` bars; check falling streak
            tail = history[-(consecutive + 1):]
            falling = all(
                tail[i + 1]["badness"] < tail[i]["badness"] - 1e-6
                for i in range(consecutive)
            )
            peak_badness = float(history[peak_idx]["badness"])
            # Require the peak to have been at least mildly elevated, otherwise
            # tape was favorable all along.
            if falling and peak_badness >= 0.20:
                recovering = True
    state["recovering"] = recovering
    boost = int(cfg.get("tape_recovery", "opportunity_score_boost", default=5) or 5) if recovering else 0
    state["opportunity_score_boost"] = boost
    state["last_ts"] = ts
    _save(cfg, state)
    return {
        "enabled": True,
        "recovering": recovering,
        "opportunity_score_boost": boost,
        "history_len": len(history),
    }


def current_boost(cfg: Config) -> int:
    if not bool(cfg.get("tape_recovery", "enabled", default=False)):
        return 0
    return int(_load(cfg).get("opportunity_score_boost", 0) or 0)
