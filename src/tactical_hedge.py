"""Tactical inverse-ETF hedge slot.

When macro turns risk-off AND the bot's top theme is in the lagging sector
set, open up to ``tactical_hedge.max_pct`` in ``tactical_hedge.symbol``
(default SH = 1x inverse S&P). Closes when macro recovers.

Week-1 default is ``shadow_mode: true`` — the module logs decisions and
emits an audit but never actually submits orders. Flip the config flag
when comfortable.
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
        "tactical_hedge", "state_file",
        default="data/state/tactical_hedge.json",
    )
    p = Path(str(raw))
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load(cfg: Config) -> dict[str, Any]:
    p = _state_path(cfg)
    if not p.exists():
        return {"open": False, "history": []}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"open": False, "history": []}


def _save(cfg: Config, state: dict[str, Any]) -> None:
    try:
        _state_path(cfg).write_text(json.dumps(state, indent=2, default=str))
    except Exception as e:
        log.warning("tactical_hedge save failed: %s", e)


def decide(
    cfg: Config,
    *,
    macro_score: float,
    sector_regime: dict[str, Any] | None,
    held_themes: set[str] | None,
    equity: float,
) -> dict[str, Any]:
    """Decide whether to open / hold / close the hedge slot. Returns an
    audit dict with action ∈ {open, hold_open, close, none} and the
    proposed notional. ``shadow_mode`` is enforced by the caller — this
    function returns the same dict regardless.
    """
    if not bool(cfg.get("tactical_hedge", "enabled", default=False)):
        return {"action": "none", "reason": "disabled"}
    symbol = str(cfg.get("tactical_hedge", "symbol", default="SH") or "SH")
    max_pct = float(cfg.get("tactical_hedge", "max_pct", default=0.05) or 0.05)
    open_th = float(cfg.get("tactical_hedge", "open_macro_score_threshold", default=-0.20) or -0.20)
    close_th = float(cfg.get("tactical_hedge", "close_macro_score_threshold", default=0.0) or 0.0)
    shadow = bool(cfg.get("tactical_hedge", "shadow_mode", default=True))
    state = _load(cfg)
    currently_open = bool(state.get("open"))

    # Identify lagging sectors as a set of GICS sector names for theme match.
    lagging_sector_names: set[str] = set()
    if sector_regime:
        snaps = sector_regime.get("snapshots") or []
        lagging_etfs = set(sector_regime.get("lagging") or [])
        for s in snaps:
            if s.get("symbol") in lagging_etfs:
                lagging_sector_names.add(str(s.get("sector_name", "")).strip())
    top_theme_in_lagging = bool(held_themes and (held_themes & lagging_sector_names))

    audit: dict[str, Any] = {
        "symbol": symbol,
        "macro_score": float(macro_score or 0.0),
        "open_threshold": open_th,
        "close_threshold": close_th,
        "currently_open": currently_open,
        "lagging_sectors": list(lagging_sector_names),
        "held_themes": list(held_themes or []),
        "top_theme_in_lagging": top_theme_in_lagging,
        "shadow_mode": shadow,
    }
    if currently_open:
        if macro_score >= close_th:
            audit["action"] = "close"
            audit["reason"] = "macro_recovered"
            state["open"] = False
        else:
            audit["action"] = "hold_open"
            audit["reason"] = "macro_still_risk_off"
    else:
        if macro_score <= open_th and top_theme_in_lagging:
            audit["action"] = "open"
            audit["proposed_notional"] = round(float(equity or 0.0) * max_pct, 2)
            audit["reason"] = "risk_off_with_top_theme_lagging"
            state["open"] = True
        else:
            audit["action"] = "none"
            audit["reason"] = "no_trigger"
    state.setdefault("history", []).append({"ts": time.time(), **audit})
    # Keep last 200 entries
    state["history"] = state["history"][-200:]
    _save(cfg, state)
    return audit
