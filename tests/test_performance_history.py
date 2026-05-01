from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.performance_history import (
    PriceResult,
    record_scan_datapoint,
    should_record_scan_datapoint,
)


class DummyConfig:
    def __init__(self, raw):
        self.raw = raw

    def get(self, *keys, default=None):
        node = self.raw
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node


class FakePriceClient:
    def __init__(self, prices):
        self.prices = prices
        self.calls = []

    def get_price(self, symbol):
        symbol = symbol.upper()
        self.calls.append(symbol)
        if symbol not in self.prices:
            return PriceResult(symbol=symbol, price=None, error="missing_test_price")
        return PriceResult(symbol=symbol, price=float(self.prices[symbol]))


def _cfg(path: Path | None = None):
    raw = {
        "benchmark": "SPY",
        "scheduling": {
            "timezone": "America/New_York",
            "intraday_times": ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00"],
        },
        "performance_history": {
            "enabled": True,
            "benchmark": "SPY",
            "schedule_start_grace_minutes": 2,
            "schedule_finish_grace_minutes": 20,
        },
    }
    if path is not None:
        raw["performance_history"]["path"] = str(path)
    return DummyConfig(raw)


def test_should_record_requires_scheduled_marker():
    started = datetime(2026, 5, 1, 14, 5, tzinfo=timezone.utc)  # 10:05 ET
    ok, reason = should_record_scan_datapoint(
        _cfg(),
        scheduled_run=False,
        dry_run=False,
        force=False,
        started_at=started,
    )
    assert ok is False
    assert reason == "manual_run"

    ok, reason = should_record_scan_datapoint(
        _cfg(),
        scheduled_run=True,
        dry_run=False,
        force=False,
        started_at=started,
    )
    assert ok is True
    assert reason == "scheduled_window:10:00"


def test_should_record_blocks_force_dry_run_and_outside_window():
    cfg = _cfg()
    scheduled_start = datetime(2026, 5, 1, 14, 5, tzinfo=timezone.utc)  # 10:05 ET
    outside = datetime(2026, 5, 1, 14, 25, tzinfo=timezone.utc)  # 10:25 ET

    assert should_record_scan_datapoint(
        cfg,
        scheduled_run=True,
        dry_run=True,
        force=False,
        started_at=scheduled_start,
    ) == (False, "dry_run")
    assert should_record_scan_datapoint(
        cfg,
        scheduled_run=True,
        dry_run=False,
        force=True,
        started_at=scheduled_start,
    ) == (False, "force_run")
    assert should_record_scan_datapoint(
        cfg,
        scheduled_run=True,
        dry_run=False,
        force=False,
        started_at=outside,
    ) == (False, "outside_intraday_schedule")


def test_should_record_new_11am_et_scan_window():
    started = datetime(2026, 5, 1, 15, 8, tzinfo=timezone.utc)  # 11:08 ET / 08:08 Phoenix
    ok, reason = should_record_scan_datapoint(
        _cfg(),
        scheduled_run=True,
        dry_run=False,
        force=False,
        started_at=started,
    )
    assert ok is True
    assert reason == "scheduled_window:11:00"


def test_record_scan_datapoint_writes_chart_friendly_json(tmp_path):
    path = tmp_path / "portfolio_vs_spy.json"
    account = SimpleNamespace(cash=1000.0)
    positions = [
        SimpleNamespace(symbol="AAPL", qty=2, side="long"),
        SimpleNamespace(symbol="MSFT", qty=3, side="long"),
    ]
    prices = FakePriceClient({"SPY": 400, "AAPL": 10, "MSFT": 20})

    point, written_path = record_scan_datapoint(
        _cfg(path),
        account=account,
        positions=positions,
        dry_run=False,
        scheduled_run=True,
        scan_started_at=datetime(2026, 5, 1, 14, 5, tzinfo=timezone.utc),
        price_client=prices,
    )

    assert written_path == path
    assert point["complete"] is True
    assert point["spy_price"] == 400
    assert point["portfolio_value"] == 1080
    assert point["positions_value"] == 80

    data = json.loads(path.read_text())
    assert data["chart_fields"] == ["timestamp_utc", "portfolio_value", "spy_price"]
    assert len(data["points"]) == 1
    assert data["points"][0]["portfolio_value"] == 1080
    assert data["points"][0]["positions"][0]["price_source"] == "twelve_data"


def test_record_scan_datapoint_marks_missing_twelve_data_prices(tmp_path):
    path = tmp_path / "portfolio_vs_spy.json"
    account = SimpleNamespace(cash=1000.0)
    positions = [
        SimpleNamespace(symbol="AAPL", qty=2, side="long"),
        SimpleNamespace(symbol="MSFT", qty=3, side="long"),
    ]
    prices = FakePriceClient({"SPY": 400, "AAPL": 10})

    point, _ = record_scan_datapoint(
        _cfg(path),
        account=account,
        positions=positions,
        dry_run=False,
        scheduled_run=True,
        scan_started_at=datetime(2026, 5, 1, 14, 5, tzinfo=timezone.utc),
        price_client=prices,
    )

    assert point["complete"] is False
    assert point["portfolio_complete"] is False
    assert point["benchmark_complete"] is True
    assert point["portfolio_value"] is None
    assert point["priced_positions_value"] == 20
    assert point["missing_symbols"] == ["MSFT"]

    data = json.loads(path.read_text())
    assert len(data["points"]) == 1
    assert data["points"][0]["errors"] == [{"symbol": "MSFT", "error": "missing_test_price"}]
