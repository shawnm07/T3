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

from src.rebalance import compute_rebalance_plan


class DummyConfig:
    raw = {
        "rebalance": {"enabled": True, "min_delta_pct": 0.0, "min_delta_usd": 1},
        "risk": {"max_position_pct": 0.50},
        "selector": {"enabled": True},
    }

    def get(self, *keys: str, default=None):
        node = self.raw
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node


def _position(symbol: str, value: float, qty: float):
    return SimpleNamespace(
        symbol=symbol,
        market_value=value,
        qty=qty,
        unrealized_plpc=0.0,
    )


def test_unified_plan_rotates_holds_and_new_entries_together():
    cfg = DummyConfig()
    positions = [
        _position("NVDA", 1000.0, 10.0),
        _position("AAPL", 500.0, 5.0),
    ]
    per_symbol = {
        "NVDA": {
            "action": "REDUCE",
            "target_pct": 0.05,
            "qty": 5,
            "delta_qty": -5,
            "entry_price": 100,
            "opportunity_score": 45,
            "one_sentence_reason": "Momentum is fading, so trim to fund stronger upside.",
        },
        "AAPL": {
            "action": "EXIT",
            "target_pct": 0,
            "qty": 0,
            "delta_qty": -5,
            "entry_price": 100,
            "opportunity_score": 20,
            "one_sentence_reason": "Capital is better recycled into higher-upside names.",
        },
        "MSFT": {
            "action": "BUY",
            "target_pct": 0.20,
            "qty": 20,
            "delta_qty": 20,
            "entry_price": 100,
            "opportunity_score": 90,
            "one_sentence_reason": "Best fresh remaining upside deserves new capital.",
        },
    }

    plan = compute_rebalance_plan(
        positions=positions,
        tech_map={},
        sent_map={},
        numeric_decisions={},
        ai_verdicts={},
        equity=10000.0,
        config=cfg,
        ai_target_weights={"NVDA": 0.05, "MSFT": 0.20},
        ai_per_symbol=per_symbol,
    )

    actual = [(a.symbol, a.side, round(a.delta_notional, 2), a.is_new_entry) for a in plan]
    assert actual == [
        ("AAPL", "sell", 500.0, False),
        ("NVDA", "sell", 500.0, False),
        ("MSFT", "buy", 2000.0, True),
    ]


def test_explicit_zero_target_exits_current_book_in_selector_floor_breach_mode():
    cfg = DummyConfig()
    positions = [
        _position("NVDA", 1000.0, 10.0),
        _position("AAPL", 500.0, 5.0),
    ]

    plan = compute_rebalance_plan(
        positions=positions,
        tech_map={},
        sent_map={},
        numeric_decisions={},
        ai_verdicts={},
        equity=10000.0,
        config=cfg,
        ai_target_weights={},
        ai_per_symbol={
            "NVDA": {
                "action": "EXIT",
                "target_pct": 0,
                "qty": 0,
                "delta_qty": -10,
                "opportunity_score": 10,
                "one_sentence_reason": "No current edge.",
            },
            "AAPL": {
                "action": "EXIT",
                "target_pct": 0,
                "qty": 0,
                "delta_qty": -5,
                "opportunity_score": 10,
                "one_sentence_reason": "No current edge.",
            },
        },
    )

    actual = [(a.symbol, a.side, round(a.delta_notional, 2), a.ai_action) for a in plan]
    assert actual == [
        ("AAPL", "sell", 500.0, "EXIT"),
        ("NVDA", "sell", 1000.0, "EXIT"),
    ]


if __name__ == "__main__":
    test_unified_plan_rotates_holds_and_new_entries_together()
    test_explicit_zero_target_exits_current_book_in_selector_floor_breach_mode()
    print("unified rebalance plan tests passed")
