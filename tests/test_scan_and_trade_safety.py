from __future__ import annotations

import sys
from types import SimpleNamespace

import scripts.scan_and_trade as scan_and_trade


class _Log:
    def info(self, *_args, **_kwargs):
        pass

    def warning(self, *_args, **_kwargs):
        pass

    def exception(self, *_args, **_kwargs):
        pass


class _Config:
    pass


class _Orchestrator:
    def __init__(self, _cfg):
        self.client = SimpleNamespace(
            get_clock=lambda: SimpleNamespace(is_open=True, next_open=None)
        )

    def run_scan(self, *_args, **_kwargs):
        raise RuntimeError("core scan exploded")


class _AlpacaClient:
    def __init__(self, _cfg):
        pass

    def get_snapshot(self):
        return SimpleNamespace(equity=100000.0, cash=12000.0), [
            SimpleNamespace(symbol="AMD"),
        ]


def test_scan_entrypoint_converts_core_exception_to_fatal_noop(monkeypatch):
    alerts: list[dict] = []
    notifications: list[dict] = []

    monkeypatch.setattr(sys, "argv", ["scan_and_trade.py", "--force"])
    monkeypatch.setattr(scan_and_trade, "setup_logging", lambda _name: _Log())
    monkeypatch.setattr(scan_and_trade.Config, "load", lambda: _Config())
    monkeypatch.setattr(scan_and_trade, "TradingOrchestrator", _Orchestrator)
    monkeypatch.setattr(scan_and_trade, "AlpacaClient", _AlpacaClient)
    monkeypatch.setattr(
        scan_and_trade,
        "send_alert",
        lambda alert_type, task_name, message, **kwargs: alerts.append({
            "alert_type": alert_type,
            "task_name": task_name,
            "message": message,
            **kwargs,
        }) or True,
    )
    monkeypatch.setattr(
        scan_and_trade,
        "should_record_scan_datapoint",
        lambda *_args, **_kwargs: (False, "test"),
    )
    monkeypatch.setattr(
        scan_and_trade,
        "get_daily_pnl",
        lambda _equity: SimpleNamespace(
            pnl_dollars=0.0,
            pnl_pct=0.0,
            baseline_equity=100000.0,
            baseline_date="2026-05-08",
            source="test",
        ),
    )
    monkeypatch.setattr(
        scan_and_trade,
        "get_spy_daily_pct",
        lambda alpaca_client=None: (0.0, "test"),
    )

    def _notify(scan_name, macro, decisions, executions, exits, **kwargs):
        notifications.append({
            "scan_name": scan_name,
            "macro": macro,
            "decisions": decisions,
            "executions": executions,
            "exits": exits,
            **kwargs,
        })
        return True

    monkeypatch.setattr(scan_and_trade, "notify_scan_execution", _notify)

    assert scan_and_trade.main() == 0
    assert alerts
    assert alerts[0]["alert_type"] == "ERROR"
    assert notifications
    assert notifications[0]["selector"]["safety_noop"] is True
    assert notifications[0]["executions"] == []
    assert notifications[0]["exits"] == []

