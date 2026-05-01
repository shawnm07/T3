import sys
import types
from pathlib import Path

try:
    import yaml  # noqa: F401
except ModuleNotFoundError:
    sys.modules["yaml"] = types.SimpleNamespace(safe_load=lambda *_args, **_kwargs: {})

try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda *_args, **_kwargs: None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.sector_guard import Violation, force_compliance


def test_theme_weight_force_compliance_scales_qty_and_delta():
    target_weights = {"A": 0.3, "B": 0.3}
    per_symbol = {
        "A": {
            "target_pct": 0.3,
            "qty": 30,
            "target_qty": 30,
            "delta_qty": 10,
            "action": "INCREASE",
        },
        "B": {
            "target_pct": 0.3,
            "qty": 60,
            "target_qty": 60,
            "delta_qty": 60,
            "action": "BUY",
        },
    }

    force_compliance(
        target_weights,
        per_symbol,
        [Violation("theme_weight", "ai_data_center", ["A", "B"], 0.6, 0.5)],
        cash_proxy_symbol="SPY",
    )

    assert target_weights["A"] == 0.25
    assert target_weights["B"] == 0.25
    assert per_symbol["A"]["qty"] == 25
    assert per_symbol["A"]["delta_qty"] == 5
    assert per_symbol["B"]["qty"] == 50
    assert per_symbol["B"]["delta_qty"] == 50
    assert target_weights["SPY"] == 0.1


def test_count_force_compliance_exits_with_current_qty_delta():
    target_weights = {"A": 0.2, "B": 0.2}
    per_symbol = {
        "A": {
            "target_pct": 0.2,
            "qty": 20,
            "target_qty": 20,
            "delta_qty": -5,
            "action": "REDUCE",
            "opportunity_score": 10,
        },
        "B": {
            "target_pct": 0.2,
            "qty": 40,
            "target_qty": 40,
            "delta_qty": 40,
            "action": "BUY",
            "opportunity_score": 90,
        },
    }

    forced = force_compliance(
        target_weights,
        per_symbol,
        [Violation("theme_count", "ai_data_center", ["A", "B"], 0.4, 1)],
        cash_proxy_symbol=None,
    )

    assert forced == ["A"]
    assert target_weights["A"] == 0
    assert per_symbol["A"]["qty"] == 0
    assert per_symbol["A"]["target_qty"] == 0
    assert per_symbol["A"]["delta_qty"] == -25


if __name__ == "__main__":
    test_theme_weight_force_compliance_scales_qty_and_delta()
    test_count_force_compliance_exits_with_current_qty_delta()
    print("sector guard tests passed")
