"""Regression tests for Telegram message rendering.

These tests cover the bugs the user reported in the screenshots:
* `Equity: $0` (now `Account: $X`)
* Empty DECISIONS block
* `SHORT ?` / `? ?` placeholders for rebalance-shape executions
* `RSI N/A` when signal_details is missing
* Rebalance items rendered twice (DECISIONS + AI REBALANCE)
"""
from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.telegram_notifier import TelegramNotifier, _is_rebalance_shape, _normalize_execution


def _capture_message():
    """Patch _send to capture the rendered message instead of POSTing."""
    captured = {}

    def fake_send(self, message: str, parse_mode: str = "HTML") -> bool:
        captured["msg"] = message
        return True

    patcher = patch.object(TelegramNotifier, "_send", fake_send)
    return captured, patcher


# --------------------------------------------------------------------------- #
#  _is_rebalance_shape                                                        #
# --------------------------------------------------------------------------- #


def test_rebalance_shape_detected_by_ai_action():
    ex = {"symbol": "AAPL", "side": "buy", "ai_action": "ADD", "delta_notional": 1000}
    assert _is_rebalance_shape(ex) is True


def test_rebalance_shape_false_for_nested_sizing():
    ex = {"sizing": {"qty": 10, "entry": 150.0}, "decision": {"symbol": "AAPL", "action": "buy"}}
    assert _is_rebalance_shape(ex) is False


def test_skipped_with_reason_not_treated_as_rebalance():
    ex = {"symbol": "AAPL", "side": "buy", "skipped": "missing_risk_inputs"}
    # Has neither ai_action nor delta_notional → should NOT be rebalance.
    assert _is_rebalance_shape(ex) is False


# --------------------------------------------------------------------------- #
#  _normalize_execution                                                       #
# --------------------------------------------------------------------------- #


def test_normalize_falls_back_to_top_level_symbol():
    ex = {"symbol": "AAPL", "side": "buy", "skipped": "earnings_blackout"}
    norm = _normalize_execution(ex)
    assert norm["symbol"] == "AAPL"
    assert norm["side_label"] == "BUY"
    assert norm["kind"] == "skipped"
    assert norm["skipped"] == "earnings_blackout"


def test_normalize_looks_up_decision_by_symbol():
    ex = {"sizing": {"qty": 10, "entry": 150.0}, "decision": {"symbol": "AAPL"}}
    decisions_by_sym = {
        "AAPL": {
            "symbol": "AAPL",
            "action": "buy",
            "signal_scores": {"technical": 0.5},
            "signal_details": {"technical": {"rsi": 45.2}},
        }
    }
    norm = _normalize_execution(ex, decisions_by_sym)
    # Even though `decision` was minimal, the lookup wasn't triggered (decision
    # was non-empty). Confirm: when decision is empty, lookup fires.
    ex2 = {"sizing": {"qty": 10, "entry": 150.0}, "symbol": "AAPL"}
    norm2 = _normalize_execution(ex2, decisions_by_sym)
    assert norm2["signal_scores"].get("technical") == 0.5
    assert norm2["signal_details"]["technical"]["rsi"] == 45.2


def test_normalize_position_pct_uses_equity():
    ex = {"sizing": {"notional": 5000.0}}
    norm = _normalize_execution(ex, equity=100_000.0)
    assert abs(norm["position_pct"] - 0.05) < 1e-9


# --------------------------------------------------------------------------- #
#  notify_scan_execution rendering                                            #
# --------------------------------------------------------------------------- #


def test_account_label_replaces_equity():
    """User wants 'Account' (total balance) not 'Equity' (read as positions-only)."""
    captured, patcher = _capture_message()
    with patcher:
        n = TelegramNotifier(token="x", chat_id="y")
        n.notify_scan_execution(
            scan_name="@ TEST",
            macro={},
            decisions=[],
            executions=[],
            exits=[],
            equity=99_281.0,
            positions_count=7,
            daily_pnl=-685.0,
            daily_pnl_pct=-0.0068,
            spy_daily_pct=-0.0043,
        )
    msg = captured["msg"]
    assert "Account: $99,281" in msg
    assert "Equity:" not in msg


def test_no_action_when_executions_empty():
    captured, patcher = _capture_message()
    with patcher:
        n = TelegramNotifier(token="x", chat_id="y")
        n.notify_scan_execution(
            scan_name="@ T",
            macro={},
            decisions=[],
            executions=[],
            exits=[],
            equity=99_000.0,
            positions_count=0,
        )
    msg = captured["msg"]
    assert "DECISIONS" in msg
    assert "No action taken (holding)" in msg


def test_rebalance_executions_excluded_from_decisions_block():
    """Selector rebalance items used to render as 'SHORT ?' garbage in DECISIONS.

    Now they should appear ONLY in the AI REBALANCE block, never in DECISIONS.
    """
    captured, patcher = _capture_message()
    with patcher:
        n = TelegramNotifier(token="x", chat_id="y")
        n.notify_scan_execution(
            scan_name="@ T",
            macro={},
            decisions=[],
            executions=[
                # Eight rebalance-shape items (mirrors the SCAN @ 12:36 bug).
                {"symbol": f"SYM{i}", "side": "sell", "ai_action": "TRIM",
                 "delta_notional": 500, "execution": {}}
                for i in range(8)
            ],
            exits=[],
            equity=96_647.0,
            positions_count=7,
            rebalance=[
                {"symbol": f"SYM{i}", "side": "sell", "ai_action": "TRIM",
                 "delta_notional": 500, "target_pct": 0.05,
                 "opportunity_score": 30, "one_sentence_reason": "trim"}
                for i in range(8)
            ],
        )
    msg = captured["msg"]
    # No "?" placeholder garbage in the DECISIONS section.
    assert "Entry: $? | Stop: $?" not in msg
    assert "RSI N/A" not in msg
    # Rebalance items appear in AI REBALANCE.
    assert "AI REBALANCE" in msg
    # Since DECISIONS got filtered to empty, it should fall back to "holding".
    assert "No action taken (holding)" in msg


def test_skipped_execution_renders_as_skip_line():
    captured, patcher = _capture_message()
    with patcher:
        n = TelegramNotifier(token="x", chat_id="y")
        n.notify_scan_execution(
            scan_name="@ T",
            macro={},
            decisions=[],
            executions=[
                {"symbol": "MSFT", "side": "buy",
                 "skipped": "earnings_blackout", "is_new_entry": True},
            ],
            exits=[],
            equity=99_000.0,
            positions_count=3,
        )
    msg = captured["msg"]
    assert "⊘ SKIP MSFT" in msg
    assert "earnings_blackout" in msg
    # Must NOT show the entry/stop/target placeholder line.
    assert "Entry: $?" not in msg


def test_rsi_recovered_from_decisions_lookup():
    """When execution has nested decision but signal_details was missing,
    notifier should still surface RSI from the orchestrator's decisions list."""
    captured, patcher = _capture_message()
    with patcher:
        n = TelegramNotifier(token="x", chat_id="y")
        n.notify_scan_execution(
            scan_name="@ T",
            macro={},
            decisions=[{
                "symbol": "AAPL", "action": "buy",
                "signal_scores": {"technical": 0.42},
                "signal_details": {"technical": {"rsi": 55.7}},
            }],
            executions=[{
                "sizing": {"qty": 10, "entry": 150.0, "stop_loss": 145.0,
                           "take_profit": 160.0, "notional": 1500.0},
                # Decision with only symbol — should look up the rest.
                "symbol": "AAPL",
            }],
            exits=[],
            equity=100_000.0,
            positions_count=1,
        )
    msg = captured["msg"]
    assert "BUY AAPL" in msg
    assert "RSI 55.7" in msg
    assert "Technical: +0.42" in msg
    assert "Size: 1.5%" in msg
