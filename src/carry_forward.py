"""Discovery carry-forward.

Every scan ranks the candidate pool and selects ~5–6 names. Today's #51 may
have been tomorrow's #3 if it had been visible — but the pool was hard-capped
at 50 and the scanner is stateless. This module persists "almost made it"
symbols (score >= carry_forward_min_score) for ``carry_forward_ttl_scans``
subsequent scans so they get a second look even when the next scan's raw
ranking would have dropped them off.
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
        "discovery", "carry_forward_state_file",
        default="data/state/carry_forward.json",
    )
    p = Path(str(raw))
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load(cfg: Config) -> dict[str, Any]:
    p = _state_path(cfg)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _save(cfg: Config, state: dict[str, Any]) -> None:
    try:
        _state_path(cfg).write_text(json.dumps(state, indent=2, sort_keys=True))
    except Exception as e:
        log.warning("carry_forward: save failed: %s", e)


def record_unpicked(
    cfg: Config,
    ranked_candidates: list[tuple[str, float]],
    selected: set[str],
    now: float | None = None,
) -> None:
    """Persist symbols that scored above the carry-forward floor but
    weren't selected this scan."""
    if not bool(cfg.get("discovery", "carry_forward_enabled", default=True)):
        return
    floor = float(cfg.get("discovery", "carry_forward_min_score", default=0.30) or 0.30)
    ttl = int(cfg.get("discovery", "carry_forward_ttl_scans", default=3) or 3)
    sel = {str(s).upper() for s in (selected or set())}
    state = _load(cfg)
    ts = float(now or time.time())
    for sym, score in (ranked_candidates or []):
        s = str(sym).upper()
        if s in sel:
            continue
        try:
            sc = float(score)
        except Exception:
            continue
        if sc < floor:
            continue
        prev = state.get(s, {})
        state[s] = {
            "best_score": max(float(prev.get("best_score", 0.0)), sc),
            "last_seen_score": sc,
            "ttl": ttl,
            "ts": ts,
        }
    # Decrement TTL for symbols not seen this scan
    seen = {str(sym).upper() for sym, _ in (ranked_candidates or [])}
    for s in list(state.keys()):
        if s not in seen and s not in sel:
            state[s]["ttl"] = int(state[s].get("ttl", 0)) - 1
        if state[s].get("ttl", 0) <= 0:
            state.pop(s, None)
    _save(cfg, state)


def get_carry_forward_symbols(cfg: Config) -> list[dict[str, Any]]:
    """Return the active carry-forward roster. Each entry contains symbol,
    best_score, last_seen_score, and ttl. Caller can append these to the
    discovery pool before ranking."""
    if not bool(cfg.get("discovery", "carry_forward_enabled", default=True)):
        return []
    state = _load(cfg)
    return [
        {"symbol": s, **rec}
        for s, rec in state.items()
        if int(rec.get("ttl", 0)) > 0
    ]


def clear_symbol(cfg: Config, symbol: str) -> None:
    state = _load(cfg)
    if state.pop(str(symbol).upper(), None) is not None:
        _save(cfg, state)
