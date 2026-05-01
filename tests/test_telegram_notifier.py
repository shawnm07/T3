"""Regression tests for the rebuilt Telegram renderer."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.telegram_notifier import TelegramNotifier, _split_message


def _capture_message():
    captured: dict[str, str] = {}

    def fake_send(self, message: str, parse_mode: str | None = None) -> bool:
        captured["msg"] = message
        return True

    patcher = patch.object(TelegramNotifier, "_send", fake_send)
    return captured, patcher


def _pos(symbol: str, qty: float, price: float, source: str = "twelve_data"):
    return SimpleNamespace(
        symbol=symbol,
        qty=qty,
        avg_entry_price=190,
        current_price=price,
        market_value=qty * price,
        unrealized_pl=(price - 190) * qty,
        unrealized_plpc=(price / 190) - 1,
        price_source=source,
    )


def test_scan_summary_contains_account_spy_delta_and_position_sizes():
    captured, patcher = _capture_message()
    with patcher:
        n = TelegramNotifier(token="x", chat_id="y")
        n.notify_scan_execution(
            scan_name="@ TEST",
            macro={"regime": "neutral", "score": 0.2, "vix_regime": "normal"},
            decisions=[],
            executions=[],
            exits=[],
            equity=100_000.0,
            cash=10_000.0,
            positions=[_pos("AAPL", 10, 200)],
            positions_count=1,
            daily_pnl=1_000.0,
            daily_pnl_pct=0.01,
            spy_daily_pct=0.005,
        )
    msg = captured["msg"]
    assert "Total account balance: $100,000" in msg
    assert "SPY +0.50%" in msg
    assert "alpha/delta +0.50%" in msg
    assert "AAPL: 10 sh | avg $190.00 -> now $200.00 = $2,000" in msg
    assert "P/L +$100 (+5.26%)" in msg
    assert "average entry from Alpaca" in msg
    assert "Equity:" not in msg


def test_selector_scan_renders_buys_sells_targets_and_interested():
    captured, patcher = _capture_message()
    plan = {
        "portfolio_thesis": "Rotate into stronger continuation names.",
        "final_portfolio": {
            "positions": [
                {
                    "symbol": "GOOGL",
                    "target_pct": 0.18,
                    "target_notional_usd": 18_000,
                    "target_qty": 45,
                    "opportunity_score": 83,
                    "reason": "Post-gap continuation.",
                }
            ],
            "cash_target_pct": 0.22,
            "cash_target_usd": 22_000,
            "spy_target_pct": 0.05,
        },
        "all_symbol_decisions": [
            {
                "symbol": "DELL",
                "final_action": "EXIT",
                "selector_action": "EXIT",
                "target_pct": 0,
                "opportunity_score": 32,
                "reason": "Fading near day high.",
            },
            {
                "symbol": "QCOM",
                "final_action": "PASS",
                "selector_action": "PASS",
                "opportunity_score": 70,
                "candidate_priority_score": 75,
                "momentum_grade": "strong_continuation",
                "reason": "Strong, but bucket capped.",
            },
        ],
    }
    with patcher:
        n = TelegramNotifier(token="x", chat_id="y")
        n.notify_scan_execution(
            scan_name="@ TEST",
            macro={},
            decisions=[],
            executions=[
                {
                    "symbol": "DELL",
                    "side": "sell",
                    "delta_notional": 8_000,
                    "current_notional": 8_000,
                    "target_notional": 0,
                    "target_pct": 0,
                    "ai_action": "EXIT",
                    "ai_confidence": 0.78,
                    "opportunity_score": 32,
                    "one_sentence_reason": "Fading near day high.",
                    "dry_run": True,
                },
                {
                    "symbol": "GOOGL",
                    "side": "buy",
                    "delta_notional": 18_000,
                    "target_pct": 0.18,
                    "target_qty": 45,
                    "ai_action": "BUY",
                    "ai_confidence": 0.8,
                    "opportunity_score": 83,
                    "one_sentence_reason": "Post-gap continuation.",
                    "dry_run": True,
                },
            ],
            exits=[],
            equity=100_000,
            cash=20_000,
            positions=[],
            positions_count=0,
            selector={
                "pool_size": 40,
                "selected_positions": ["GOOGL"],
                "execution_cash_target_pct": 0.22,
                "spy_target_pct": 0.05,
            },
            unified_portfolio_plan=plan,
        )
    msg = captured["msg"]
    assert "FINAL TARGET PORTFOLIO" in msg
    assert "GOOGL: target 18.00%" in msg
    assert "BOUGHT / INCREASED" in msg
    assert "GOOGL: dry-run | add $18,000" in msg
    assert "SELL / TRIM / EXIT DECISIONS" in msg
    assert "DELL: dry-run | reduce $8,000 from $8,000 to $0" in msg
    assert "INTERESTED BUT NOT BOUGHT" in msg
    assert "QCOM: action PASS" in msg


def test_long_messages_are_split_with_part_headers():
    chunks = _split_message("\n".join([f"line {i} " + ("x" * 200) for i in range(60)]), max_len=1000)
    assert len(chunks) > 1
    assert chunks[0].startswith("[1/")
