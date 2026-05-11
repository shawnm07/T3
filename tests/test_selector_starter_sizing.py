from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

try:
    import yaml  # noqa: F401
except ModuleNotFoundError:
    sys.modules["yaml"] = types.SimpleNamespace(safe_load=lambda *_args, **_kwargs: {})

try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda *_args, **_kwargs: None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.orchestrator import TradingOrchestrator


class _Cfg:
    def get(self, *keys, default=None):
        values = {
            ("selector", "new_entry_initial_fraction"): 0.70,
            ("selector", "new_entry_strong_initial_fraction"): 0.85,
            ("selector", "new_entry_max_initial_fraction"): 0.90,
            ("selector", "new_entry_strong_min_opportunity_score"): 85,
            ("selector", "new_entry_strong_min_confidence"): 0.75,
        }
        return values.get(tuple(keys), default)


def _orch():
    orch = TradingOrchestrator.__new__(TradingOrchestrator)
    orch.cfg = _Cfg()
    orch.cash_proxy_enabled = True
    orch.cash_proxy_symbol = "SPY"
    orch.risk = SimpleNamespace()
    return orch


def _selector_result(*, opportunity_score=90, confidence=0.80, severity="favorable"):
    return {
        "_tape_state": {"severity_label": severity},
        "selected_positions": ["AVGO"],
        "target_weights": {"AVGO": 0.20},
        "cash_target_pct": 0.0,
        "per_symbol": {
            "AVGO": {
                "target_pct": 0.20,
                "qty": 20,
                "delta_qty": 20,
                "entry_price": 100,
                "action": "BUY",
                "confidence": confidence,
                "opportunity_score": opportunity_score,
                "one_sentence_reason": "Strong continuation setup.",
            }
        },
    }


def test_strong_new_entry_stages_at_85_percent():
    orch = _orch()

    target_weights, per_symbol, cash_target_pct, adjustments = orch._stage_new_entry_targets(
        _selector_result(),
        held_symbols=set(),
        equity=10_000,
    )

    assert target_weights["AVGO"] == 0.17
    assert per_symbol["AVGO"]["qty"] == 17
    assert cash_target_pct == 0.03
    assert adjustments[0]["staged_fraction"] == 0.85
    assert adjustments[0]["staged_fraction_reason"] == "strong_opportunity"


def test_risk_off_new_entry_keeps_base_starter_size():
    orch = _orch()

    target_weights, per_symbol, cash_target_pct, adjustments = orch._stage_new_entry_targets(
        _selector_result(severity="mild_risk_off"),
        held_symbols=set(),
        equity=10_000,
    )

    assert target_weights["AVGO"] == 0.14
    assert per_symbol["AVGO"]["qty"] == 14
    assert cash_target_pct == 0.06
    assert adjustments[0]["staged_fraction"] == 0.70
    assert adjustments[0]["staged_fraction_reason"] == "base"
