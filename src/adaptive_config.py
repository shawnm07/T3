"""Adaptive threshold overrides.

The weekly retrospective inspects post-mortem data and proposes parameter
adjustments. Adjustments are written to ``data/state/config_overrides.yaml``
(never overwriting ``config.yaml``). At app start, ``apply_overrides()``
deep-merges the override file into the in-memory Config so the bot picks up
the auto-tuned values without losing human-tuned defaults.

Current adjustment rules:

- Exit-arbiter min_confidence: if accuracy < ``exit_arbiter_min_accuracy``
  on ≥ ``exit_arbiter_min_samples`` recent closes, raise the floor by
  ``exit_arbiter_step_up`` (capped at ``exit_arbiter_max_floor``).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from src.config import Config
from src.postmortem import exit_arbiter_accuracy, read_recent

log = logging.getLogger(__name__)


def _overrides_path(cfg: Config) -> Path:
    raw = cfg.get(
        "adaptive_config", "overrides_file",
        default="data/state/config_overrides.yaml",
    )
    p = Path(str(raw))
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load(cfg: Config) -> dict[str, Any]:
    p = _overrides_path(cfg)
    if not p.exists():
        return {}
    try:
        return yaml.safe_load(p.read_text()) or {}
    except Exception:
        return {}


def _save(cfg: Config, overrides: dict[str, Any]) -> None:
    try:
        _overrides_path(cfg).write_text(yaml.safe_dump(overrides, sort_keys=True))
    except Exception as e:
        log.warning("adaptive_config: save failed: %s", e)


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def apply_overrides(cfg: Config) -> None:
    """Mutate ``cfg`` in-place to merge override values. No-op when disabled."""
    if not bool(cfg.get("adaptive_config", "enabled", default=False)):
        return
    overrides = _load(cfg)
    if not overrides:
        return
    raw = getattr(cfg, "raw", None) or getattr(cfg, "_raw", None) or getattr(cfg, "data", None)
    if isinstance(raw, dict):
        merged = _deep_merge(raw, overrides)
        # Config is a frozen dataclass with a mutable .raw dict. We mutate the
        # existing dict in place so the frozen constraint still holds.
        raw.clear()
        raw.update(merged)
        log.info("[adaptive_config] applied overrides: %s", list(overrides.keys()))


def evaluate_and_update(cfg: Config) -> dict[str, Any]:
    """Run the weekly evaluation. Reads recent postmortems, computes
    diagnostics, and updates the override file when calibration drifts.

    Returns a summary dict suitable for the weekly review report.
    """
    summary: dict[str, Any] = {"adjustments": []}
    if not bool(cfg.get("adaptive_config", "enabled", default=False)):
        summary["status"] = "disabled"
        return summary
    records = read_recent(cfg, days=28)
    summary["records_examined"] = len(records)
    diag = exit_arbiter_accuracy(records)
    summary["exit_arbiter"] = diag

    min_accuracy = float(cfg.get("adaptive_config", "exit_arbiter_min_accuracy", default=0.55) or 0.55)
    min_samples = int(cfg.get("adaptive_config", "exit_arbiter_min_samples", default=20) or 20)
    step = float(cfg.get("adaptive_config", "exit_arbiter_step_up", default=0.05) or 0.05)
    max_floor = float(cfg.get("adaptive_config", "exit_arbiter_max_floor", default=0.85) or 0.85)

    if diag.get("sample", 0) >= min_samples and (diag.get("accuracy") or 1.0) < min_accuracy:
        overrides = _load(cfg)
        current_floor = float(
            overrides.get("exit_arbiter", {}).get("min_confidence")
            or cfg.get("exit_arbiter", "min_confidence", default=0.55)
        )
        new_floor = min(max_floor, current_floor + step)
        if new_floor > current_floor + 1e-6:
            overrides.setdefault("exit_arbiter", {})["min_confidence"] = round(new_floor, 3)
            _save(cfg, overrides)
            summary["adjustments"].append({
                "key": "exit_arbiter.min_confidence",
                "old": current_floor,
                "new": new_floor,
                "reason": (
                    f"accuracy {diag.get('accuracy')} < {min_accuracy} "
                    f"over {diag.get('sample')} samples"
                ),
            })
            log.info(
                "[adaptive_config] raised exit_arbiter.min_confidence %.2f → %.2f",
                current_floor, new_floor,
            )
    return summary
