"""Regression: BUY-gate violations auto-downgrade instead of failing validation.

Before 2026-05-11 these gates appended hard problems, forcing the selector to
retry up to 5x; in a rallying tape every retry picked the next-best names that
failed the same distance-from-high gate, ending in a safety no-op. The
validator now downgrades offending selections to PASS, redistributes their
weight to cash, and lets the scan ship.
"""
from __future__ import annotations

import yaml

from src.ai_pipeline import validate_selector_response
from src.config import Config, AlpacaConfig


def _make_cfg() -> Config:
    with open("config.yaml", "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Config(AlpacaConfig("", "", "", "", "paper"), raw)


def _per_sym_buy(qty: float, entry: float, *, action: str = "BUY", opp: float = 75):
    return {
        "action": action,
        "target_pct": 0.15,
        "qty": qty,
        "entry_price": entry,
        "delta_qty": qty,
        "opportunity_score": opp,
        "one_sentence_reason": "test",
        "stop_loss": entry * 0.99,
    }


def test_distance_from_high_violations_auto_downgrade_to_pass():
    cfg = _make_cfg()
    pool_symbols = ["BE", "VRT", "NVDA", "AMD"]
    pool_meta = {
        "BE":   {"intraday_chart": {"distance_from_high_pct": -0.004, "volume_trend": "fading"}, "currently_held": False},
        "VRT":  {"intraday_chart": {"distance_from_high_pct": -0.001, "volume_trend": "fading"}, "currently_held": False},
        "NVDA": {"intraday_chart": {"distance_from_high_pct": -0.007, "volume_trend": "fading"}, "currently_held": False},
        "AMD":  {"intraday_chart": {"distance_from_high_pct":  0.50,  "volume_trend": "rising"}, "currently_held": True, "current_qty": 50},
    }
    result = {
        "selected_positions": ["BE", "VRT", "NVDA", "AMD"],
        "target_weights": {"BE": 0.15, "VRT": 0.15, "NVDA": 0.15, "AMD": 0.15},
        "per_symbol": {
            "BE": _per_sym_buy(150, 100),
            "VRT": _per_sym_buy(15, 1000),
            "NVDA": _per_sym_buy(75, 200),
            "AMD": {**_per_sym_buy(50, 400, action="HOLD"), "delta_qty": 0},
        },
        "spy_target_pct": 0.20,
        "cash_target_pct": 0.20,
        "spy_decision": {"target_pct": 0.20, "action": "HOLD",
                         "opportunity_score": 0, "one_sentence_reason": "park"},
        "rotation_plan": {"exited": [], "entered": [], "held": []},
    }
    ok, problems = validate_selector_response(
        result, held_symbols=["AMD"], pool_symbols=pool_symbols,
        pool_meta=pool_meta, cfg=cfg, allow_floor_breach=True,
        equity=100_000,
        system_state={
            "buy_max_distance_from_high_pct": 0.04,
            "tape_state": {"severity_label": "favorable"},
        },
    )
    assert ok, f"validator should pass after auto-repair, got problems={problems}"
    assert problems == []
    downgraded = result.get("_auto_repaired", {}).get("buy_gate_downgrade", {})
    assert set(downgraded.keys()) == {"BE", "VRT", "NVDA"}
    # Held AMD stays; the three ineligible BUYs are stripped.
    assert result["selected_positions"] == ["AMD"]
    assert result["target_weights"] == {"AMD": 0.15}
    # Freed 0.45 of weight migrates into cash (0.20 + 0.45 = 0.65).
    assert abs(result["cash_target_pct"] - 0.65) < 1e-6
    # Per-symbol metadata reflects the downgrade.
    for sym in ("BE", "VRT", "NVDA"):
        assert result["per_symbol"][sym]["action"] == "PASS"
        assert result["per_symbol"][sym]["target_pct"] == 0.0
        assert result["per_symbol"][sym]["_gate_downgrade_reason"]


def test_auto_downgrade_can_be_disabled_via_config():
    cfg = _make_cfg()
    cfg.raw.setdefault("selector", {})["auto_downgrade_buy_gate_violations"] = False
    pool_symbols = ["BE", "AMD"]
    pool_meta = {
        "BE":  {"intraday_chart": {"distance_from_high_pct": -0.004, "volume_trend": "fading"}, "currently_held": False},
        "AMD": {"intraday_chart": {"distance_from_high_pct":  0.50,  "volume_trend": "rising"}, "currently_held": True, "current_qty": 50},
    }
    result = {
        "selected_positions": ["BE", "AMD"],
        "target_weights": {"BE": 0.30, "AMD": 0.30},
        "per_symbol": {
            "BE": _per_sym_buy(150, 100),
            "AMD": {**_per_sym_buy(50, 400, action="HOLD"), "delta_qty": 0},
        },
        "spy_target_pct": 0.20,
        "cash_target_pct": 0.20,
        "spy_decision": {"target_pct": 0.20, "action": "HOLD",
                         "opportunity_score": 0, "one_sentence_reason": "park"},
        "rotation_plan": {"exited": [], "entered": [], "held": []},
    }
    ok, problems = validate_selector_response(
        result, held_symbols=["AMD"], pool_symbols=pool_symbols,
        pool_meta=pool_meta, cfg=cfg, allow_floor_breach=True,
        equity=100_000,
        system_state={
            "buy_max_distance_from_high_pct": 0.04,
            "tape_state": {"severity_label": "favorable"},
        },
    )
    # With auto-repair off, the legacy hard-problem path surfaces.
    assert not ok
    assert any("BE" in p and "BUY blocked" in p for p in problems)
