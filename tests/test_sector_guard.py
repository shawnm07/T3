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

from src.sector_guard import Violation, force_compliance, validate


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


def test_theme_weight_rounding_stays_inside_cap():
    target_weights = {"MU": 0.38, "AVGO": 0.25, "SNDK": 0.15}
    per_symbol = {
        "MU": {"target_pct": 0.38, "qty": 52, "delta_qty": 52, "action": "BUY"},
        "AVGO": {"target_pct": 0.25, "qty": 59, "delta_qty": 59, "action": "BUY"},
        "SNDK": {"target_pct": 0.15, "qty": 10, "delta_qty": 10, "action": "BUY"},
    }

    force_compliance(
        target_weights,
        per_symbol,
        [Violation("theme_weight", "ai_data_center", ["MU", "AVGO", "SNDK"], 0.78, 0.5)],
        cash_proxy_symbol="SPY",
    )

    assert round(target_weights["MU"] + target_weights["AVGO"] + target_weights["SNDK"], 4) <= 0.5
    assert per_symbol["MU"]["action"] == "BUY"
    assert per_symbol["AVGO"]["action"] == "BUY"
    assert per_symbol["SNDK"]["action"] == "BUY"


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


def test_count_force_compliance_marks_unheld_target_as_pass():
    target_weights = {"A": 0.2, "B": 0.2}
    per_symbol = {
        "A": {
            "target_pct": 0.2,
            "qty": 20,
            "target_qty": 20,
            "delta_qty": 20,
            "action": "BUY",
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
    assert per_symbol["A"]["delta_qty"] == 0
    assert per_symbol["A"]["action"] == "PASS"
    assert per_symbol["A"]["reason_code"] == "sector_capped"


class _Cfg:
    def get(self, *keys, default=None):
        values = {
            ("diversification", "max_per_gics_sector"): 1,
            ("diversification", "max_per_theme"): 3,
            ("diversification", "max_theme_weight_pct"): 0.50,
            ("diversification", "themes"): {},
            ("diversification", "symbol_overrides"): {},
        }
        return values.get(tuple(keys), default)


def test_validate_audit_distinguishes_live_and_same_scan_members():
    result = validate(
        {"A": 0.20, "B": 0.20},
        {},
        {
            "A": {"sector": "Information Technology", "currently_held": True},
            "B": {"sector": "Information Technology", "currently_held": False},
            "C": {"sector": "Information Technology", "currently_held": False},
        },
        _Cfg(),
        cash_proxy_symbol="SPY",
    )

    assert not result.ok
    sector = result.audit["sectors"]["Information Technology"]
    assert sector["live_holdings"] == ["A"]
    assert sector["accepted_same_scan_candidates"] == ["B"]
    assert "C" not in sector["members"]


if __name__ == "__main__":
    test_theme_weight_force_compliance_scales_qty_and_delta()
    test_count_force_compliance_exits_with_current_qty_delta()
    test_validate_audit_distinguishes_live_and_same_scan_members()
    print("sector guard tests passed")
