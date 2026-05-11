"""Phase 0: Selector hits max_tokens -> no retry, Telegram alert, return None."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.ai_pipeline as ai_pipeline


class _FakeAI:
    enabled = True
    api_key = "stub"

    def available(self) -> bool:
        return True


class _FakePipeline:
    """Records how many times portfolio_selector is called."""

    def __init__(self):
        self.calls = 0

    def portfolio_selector(self, ctx):
        self.calls += 1

        async def _runner():
            return {
                "_stop_reason": "max_tokens",
                "_input_tokens": 54000,
                "_output_tokens": 32000,
            }

        return _runner()


def _return_and_close(coro, result):
    coro.close()
    return result


class _SequencePipeline:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def portfolio_selector(self, ctx):
        self.calls += 1
        result = self.results[min(self.calls - 1, len(self.results) - 1)]

        async def _runner():
            return result

        return _runner()


def _valid_selector_result(stop_reason="end_turn"):
    return {
        "_stop_reason": stop_reason,
        "_input_tokens": 100,
        "_output_tokens": 200,
        "portfolio_thesis": "Test",
        "spy_target_pct": 0.0,
        "cash_target_pct": 0.5,
        "spy_decision": {
            "target_pct": 0.0,
            "action": "HOLD",
            "opportunity_score": 0,
            "one_sentence_reason": "No SPY target.",
        },
        "spy_vs_cash_reasoning": "Test.",
        "selected_positions": ["AMD"],
        "target_weights": {"AMD": 0.5},
        "per_symbol": {
            "AMD": {
                "target_pct": 0.5,
                "qty": 10,
                "delta_qty": 10,
                "entry_price": 100,
                "stop_loss": None,
                "take_profit": None,
                "action": "BUY",
                "confidence": 0.8,
                "opportunity_score": 80,
                "one_sentence_reason": "AMD has the best remaining upside.",
            },
        },
        "exhaustion_penalty_applied": [],
        "rotation_plan": {"entered": [], "exited": [], "held": []},
    }


def test_selector_max_tokens_does_not_retry(monkeypatch):
    fake_pipeline = _FakePipeline()
    captured_alert: dict = {}

    class _FakeNotifier:
        def send_alert(self, alert_type, task_name, message, error_details=""):
            captured_alert["alert_type"] = alert_type
            captured_alert["task_name"] = task_name
            captured_alert["message"] = message
            return True

    monkeypatch.setattr(ai_pipeline, "AIResearcher", lambda cfg: _FakeAI())
    monkeypatch.setattr(ai_pipeline, "AIPipeline", lambda cfg, ai: fake_pipeline)
    monkeypatch.setattr(ai_pipeline, "_dump_selector_validation_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.journal.log_decision", lambda _payload: None)
    monkeypatch.setattr(
        ai_pipeline,
        "_run_with_ai_cleanup",
        lambda ai, coro: _return_and_close(coro, {
            "_stop_reason": "max_tokens",
            "_input_tokens": 54000,
            "_output_tokens": 32000,
        }),
    )

    with patch("src.telegram_notifier.get_notifier", lambda: _FakeNotifier()):
        result = ai_pipeline.run_portfolio_selector(
            config=_FakeConfig(),
            context={"equity": 100_000},
            pool_symbols=["AMZN", "INTC"],
            pool_meta={},
            held_symbols=[],
            allow_floor_breach=False,
            max_attempts=3,
        )

    assert result is None, "max_tokens must skip the scan, not return a partial dict"
    assert fake_pipeline.calls <= 1, (
        f"expected exactly one selector call on max_tokens, got {fake_pipeline.calls}"
    )
    assert captured_alert.get("alert_type") == "MAX_TOKENS", (
        f"expected MAX_TOKENS Telegram alert, got {captured_alert!r}"
    )
    assert "portfolio-selector" in captured_alert.get("task_name", "")


def test_selector_accepts_valid_json_despite_max_tokens(monkeypatch):
    fake_pipeline = _SequencePipeline([_valid_selector_result(stop_reason="max_tokens")])
    rebuild_calls: list[int] = []

    monkeypatch.setattr(ai_pipeline, "AIResearcher", lambda cfg: _FakeAI())
    monkeypatch.setattr(ai_pipeline, "AIPipeline", lambda cfg, ai: fake_pipeline)
    monkeypatch.setattr(ai_pipeline, "_dump_selector_validation_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.journal.log_decision", lambda _payload: None)
    monkeypatch.setattr(
        ai_pipeline,
        "_run_with_ai_cleanup",
        lambda ai, coro: asyncio.run(coro),
    )

    result = ai_pipeline.run_portfolio_selector(
        config=_FakeConfig(),
        context={"equity": 100_000, "system_state": {}},
        pool_symbols=["AMD", "INTC"],
        pool_meta={"AMD": {"current_qty": 0}, "INTC": {"current_qty": 0}},
        held_symbols=[],
        allow_floor_breach=True,
        max_attempts=3,
        rebuild_with_pool_size=lambda n: rebuild_calls.append(n),
    )

    assert result is not None
    assert result["_accepted_with_stop_reason"] == "max_tokens"
    assert fake_pipeline.calls == 1
    assert rebuild_calls == []


def test_selector_retries_max_tokens_with_smaller_pool(monkeypatch):
    fake_pipeline = _SequencePipeline([
        {"_stop_reason": "max_tokens", "_input_tokens": 50_000, "_output_tokens": 30_000},
        _valid_selector_result(),
    ])
    rebuild_calls: list[int] = []

    def rebuild(n):
        rebuild_calls.append(n)
        return (
            {"equity": 100_000, "system_state": {}},
            ["AMD", "INTC"],
            {"AMD": {"current_qty": 0}, "INTC": {"current_qty": 0}},
        )

    monkeypatch.setattr(ai_pipeline, "AIResearcher", lambda cfg: _FakeAI())
    monkeypatch.setattr(ai_pipeline, "AIPipeline", lambda cfg, ai: fake_pipeline)
    monkeypatch.setattr(ai_pipeline, "_dump_selector_validation_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.journal.log_decision", lambda _payload: None)
    monkeypatch.setattr(
        ai_pipeline,
        "_run_with_ai_cleanup",
        lambda ai, coro: asyncio.run(coro),
    )

    result = ai_pipeline.run_portfolio_selector(
        config=_FakeConfig(),
        context={"equity": 100_000, "system_state": {}},
        pool_symbols=["AMD", "INTC", "NVDA"],
        pool_meta={"AMD": {"current_qty": 0}, "INTC": {"current_qty": 0}, "NVDA": {"current_qty": 0}},
        held_symbols=[],
        allow_floor_breach=True,
        max_attempts=3,
        rebuild_with_pool_size=rebuild,
    )

    assert result is not None
    assert fake_pipeline.calls == 2
    assert rebuild_calls == [30]


class _FakeConfig:
    """Minimal cfg shim that returns sensible defaults."""

    def get(self, *path, default=None):
        if path == ("selector", "retry_validation_failures"):
            return 1
        if path == ("selector", "min_positions"):
            return 3
        if path == ("selector", "max_positions"):
            return 6
        if path == ("selector", "max_tokens_fallback_pool_size"):
            return 30
        if path == ("selector", "max_tokens_fallback_min_pool_size"):
            return 12
        if path == ("selector", "max_tokens_max_attempts"):
            return 2
        if path == ("risk", "max_position_pct"):
            return 1.0
        if path == ("risk", "hard_stop_loss_pct"):
            return 0.01
        if path == ("risk", "max_risk_per_trade_pct"):
            return 0.005
        return default
