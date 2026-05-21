"""Theme-replacement cooldown.

After the bot exits symbol X in theme T (e.g. AMD in ai_data_center), the
selector cannot enter any other symbol in theme T within
``diversification.theme_cooldown_minutes`` unless the new candidate's
opportunity_score beats the exit score by at least
``diversification.theme_cooldown_score_delta`` points.

This stops same-day theme-churn — paying the spread to swap one semiconductor
for another is exactly the failure we saw on 2026-05-11 (AMD → MU rebalance).
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from src.config import Config
from src.sector_guard import (
    _build_sector_to_theme,
    _symbol_overrides,
    theme_bucket_for,
)

log = logging.getLogger(__name__)


def _state_path(cfg: Config) -> Path:
    raw = cfg.get(
        "diversification", "theme_cooldown_state_file",
        default="data/state/theme_cooldown.json",
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
    p = _state_path(cfg)
    try:
        p.write_text(json.dumps(state, indent=2, sort_keys=True))
    except Exception as e:
        log.warning("theme_cooldown: failed to save state: %s", e)


def record_exit(
    cfg: Config,
    symbol: str,
    sector: str | None,
    exit_score: float,
    timestamp: float | None = None,
) -> None:
    """Mark the theme of ``symbol`` as on cooldown."""
    sector_to_theme = _build_sector_to_theme(cfg)
    overrides = _symbol_overrides(cfg)
    theme = theme_bucket_for(sector or "", sector_to_theme, symbol, overrides)
    if not theme or theme == "other":
        return
    state = _load(cfg)
    state[theme] = {
        "exited_symbol": str(symbol).upper(),
        "exit_score": float(exit_score or 0.0),
        "ts": float(timestamp or time.time()),
    }
    _save(cfg, state)
    log.info("[theme_cooldown] %s on cooldown (theme=%s exit_score=%.1f)",
             symbol, theme, exit_score or 0.0)


def is_blocked(
    cfg: Config,
    symbol: str,
    sector: str | None,
    candidate_score: float,
    now: float | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Return (blocked, audit_info) for a candidate BUY/INCREASE.

    Block if the candidate's theme is on cooldown AND its opportunity_score
    does not exceed the previously-exited symbol's score by the required
    delta.
    """
    minutes = float(cfg.get("diversification", "theme_cooldown_minutes", default=0) or 0)
    if minutes <= 0:
        return False, {"reason": "disabled"}
    delta = float(cfg.get("diversification", "theme_cooldown_score_delta", default=0) or 0)
    sector_to_theme = _build_sector_to_theme(cfg)
    overrides = _symbol_overrides(cfg)
    theme = theme_bucket_for(sector or "", sector_to_theme, symbol, overrides)
    if not theme or theme == "other":
        return False, {"reason": "no_theme"}
    state = _load(cfg)
    rec = state.get(theme)
    if not rec:
        return False, {"reason": "no_cooldown_for_theme", "theme": theme}
    age_s = float(now or time.time()) - float(rec.get("ts", 0))
    if age_s > minutes * 60:
        return False, {"reason": "cooldown_expired", "theme": theme, "age_minutes": age_s / 60.0}
    needed = float(rec.get("exit_score", 0.0)) + delta
    if float(candidate_score or 0.0) >= needed:
        return False, {
            "reason": "cooldown_overridden_by_higher_score",
            "theme": theme,
            "candidate_score": float(candidate_score),
            "exit_score": float(rec.get("exit_score", 0.0)),
            "delta_required": delta,
        }
    return True, {
        "reason": "theme_cooldown_active",
        "theme": theme,
        "exited_symbol": rec.get("exited_symbol"),
        "exit_score": float(rec.get("exit_score", 0.0)),
        "candidate_score": float(candidate_score),
        "delta_required": delta,
        "age_minutes": age_s / 60.0,
        "cooldown_minutes": minutes,
    }


def prune_expired(cfg: Config) -> None:
    minutes = float(cfg.get("diversification", "theme_cooldown_minutes", default=0) or 0)
    if minutes <= 0:
        return
    state = _load(cfg)
    cutoff = time.time() - minutes * 60
    pruned = {k: v for k, v in state.items() if float(v.get("ts", 0)) >= cutoff}
    if len(pruned) != len(state):
        _save(cfg, pruned)
