from __future__ import annotations

import json
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


def _install_alpaca_stubs() -> None:
    class _Enum:
        DAY = "day"
        STOP = "stop"
        BUY = "buy"
        SELL = "sell"
        BRACKET = "bracket"
        OTO = "oto"

    class _Request:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    sys.modules.setdefault("alpaca", types.ModuleType("alpaca"))
    sys.modules.setdefault("alpaca.data", types.ModuleType("alpaca.data"))
    historical = types.ModuleType("alpaca.data.historical")
    historical.StockHistoricalDataClient = object
    sys.modules["alpaca.data.historical"] = historical
    news = types.ModuleType("alpaca.data.historical.news")
    news.NewsClient = object
    sys.modules["alpaca.data.historical.news"] = news
    requests_mod = types.ModuleType("alpaca.data.requests")
    requests_mod.NewsRequest = _Request
    requests_mod.StockBarsRequest = _Request
    requests_mod.StockLatestQuoteRequest = _Request
    sys.modules["alpaca.data.requests"] = requests_mod
    timeframe = types.ModuleType("alpaca.data.timeframe")
    timeframe.TimeFrame = SimpleNamespace(Day="day")
    sys.modules["alpaca.data.timeframe"] = timeframe
    sys.modules.setdefault("alpaca.trading", types.ModuleType("alpaca.trading"))
    trading_client = types.ModuleType("alpaca.trading.client")
    trading_client.TradingClient = object
    sys.modules["alpaca.trading.client"] = trading_client
    enums = types.ModuleType("alpaca.trading.enums")
    enums.OrderClass = _Enum
    enums.OrderSide = _Enum
    enums.OrderType = _Enum
    enums.TimeInForce = _Enum
    sys.modules["alpaca.trading.enums"] = enums
    trading_requests = types.ModuleType("alpaca.trading.requests")
    trading_requests.GetOrdersRequest = _Request
    trading_requests.LimitOrderRequest = _Request
    trading_requests.MarketOrderRequest = _Request
    trading_requests.StopOrderRequest = _Request
    trading_requests.StopLossRequest = _Request
    trading_requests.TakeProfitRequest = _Request
    sys.modules["alpaca.trading.requests"] = trading_requests


try:
    import alpaca  # noqa: F401
except ModuleNotFoundError:
    _install_alpaca_stubs()

try:
    import tenacity  # noqa: F401
except ModuleNotFoundError:
    tenacity_stub = types.ModuleType("tenacity")
    tenacity_stub.retry = lambda *args, **kwargs: (lambda fn: fn)
    tenacity_stub.stop_after_attempt = lambda *args, **kwargs: None
    tenacity_stub.wait_exponential = lambda *args, **kwargs: None
    sys.modules["tenacity"] = tenacity_stub

try:
    import yaml  # noqa: F401
except ModuleNotFoundError:
    sys.modules["yaml"] = types.SimpleNamespace(safe_load=lambda *_args, **_kwargs: {})

try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda *_args, **_kwargs: None)

from src.discovery import Candidate
from src.dynamic_watchlist import load_dynamic_watchlist, remove_dynamic_watchlist_symbols
from src.orchestrator import TradingOrchestrator


FIXTURE_NOW = datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc)


class DummyConfig:
    def __init__(self, state_file: str):
        self.raw = {
            "dynamic_watchlist": {
                "enabled": True,
                "state_file": state_file,
                "ttl_days": 7,
            },
        }

    def get(self, *keys: str, default=None):
        node = self.raw
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node


class FakeClient:
    def __init__(self):
        self.assets = {
            "AKAN": {
                "symbol": "AKAN",
                "status": "active",
                "tradable": False,
                "fractionable": True,
            },
            "MSFT": {
                "symbol": "MSFT",
                "status": "active",
                "tradable": True,
                "fractionable": True,
            },
        }

    def get_asset_info(self, symbol: str) -> dict:
        return dict(self.assets[str(symbol).upper()])


def _write_state(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "symbols": {
                "AKAN": {
                    "score": 80,
                    "last_seen": "2026-05-01T15:00:00+00:00",
                },
                "MSFT": {
                    "score": 70,
                    "last_seen": "2026-05-01T15:00:00+00:00",
                },
            }
        }),
        encoding="utf-8",
    )


def test_remove_dynamic_watchlist_symbols_persists_prune():
    with tempfile.TemporaryDirectory() as tmp:
        state_file = Path(tmp) / "dynamic_watchlist.json"
        _write_state(state_file)
        cfg = DummyConfig(str(state_file))

        update = remove_dynamic_watchlist_symbols(
            cfg,
            ["AKAN"],
            reason="alpaca_asset_not_ai_eligible",
            now=FIXTURE_NOW,
        )

        assert update["removed"] == [{
            "symbol": "AKAN",
            "reason": "alpaca_asset_not_ai_eligible",
        }]
        assert load_dynamic_watchlist(cfg, now=FIXTURE_NOW) == ["MSFT"]


def test_selector_asset_prune_removes_non_tradable_before_ai(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        state_file = Path(tmp) / "dynamic_watchlist.json"
        _write_state(state_file)
        cfg = DummyConfig(str(state_file))

        import src.orchestrator as orchestrator_module

        monkeypatch.setattr(orchestrator_module, "log_decision", lambda _payload: None)

        orch = TradingOrchestrator.__new__(TradingOrchestrator)
        orch.cfg = cfg
        orch.client = FakeClient()
        orch.cash_proxy_enabled = False
        orch.cash_proxy_symbol = "SPY"

        kept, removed = orch._prune_untradable_candidates(
            [
                Candidate("AKAN", sources=["dynamic_watchlist"]),
                Candidate("MSFT", sources=["seed_watchlist"]),
            ],
            held_symbols=set(),
        )

        assert [cand.symbol for cand in kept] == ["MSFT"]
        assert removed[0]["symbol"] == "AKAN"
        assert removed[0]["reason"] == "asset_not_tradable"
        assert load_dynamic_watchlist(cfg, now=FIXTURE_NOW) == ["MSFT"]


def test_asset_lookup_404_is_treated_as_terminal_not_found():
    assert (
        TradingOrchestrator._asset_lookup_failure_reason(Exception("404 Not Found"))
        == "asset_not_found"
    )
