"""Phase 0: Selector hits max_tokens -> no retry, Telegram alert, return None."""
from __future__ import annotations

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
    monkeypatch.setattr(
        ai_pipeline,
        "_run_with_ai_cleanup",
        lambda ai, coro: {
            "_stop_reason": "max_tokens",
            "_input_tokens": 54000,
            "_output_tokens": 32000,
        },
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


class _FakeConfig:
    """Minimal cfg shim that returns sensible defaults."""

    def get(self, *path, default=None):
        if path == ("selector", "retry_validation_failures"):
            return 1
        if path == ("selector", "min_positions"):
            return 3
        if path == ("selector", "max_positions"):
            return 6
        return default
