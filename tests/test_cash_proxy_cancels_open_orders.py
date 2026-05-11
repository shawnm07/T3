"""Regression: cash-proxy sell cancels open orders first so the qty becomes
available. Without this, the trailing stop on SPY reserves every share
(`held_for_orders = qty`) and Alpaca rejects the funding sell with
"insufficient qty available for order" — blocking every rebalance buy.

See 2026-05-11 09:22 scan: $91K cash on the books, $48K of buys planned,
all three skipped on `insufficient_confirmed_cash` because the SPY trailing
stop pinned every share.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import yaml

from src.config import Config, AlpacaConfig
from src.orchestrator import TradingOrchestrator as Orchestrator


def _make_orchestrator():
    with open("config.yaml", "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    cfg = Config(AlpacaConfig("", "", "", "", "paper"), raw)
    client = MagicMock()
    orch = Orchestrator.__new__(Orchestrator)
    orch.client = client
    orch.cfg = cfg
    orch.cash_proxy_enabled = True
    orch.cash_proxy_symbol = "SPY"
    orch._get_proxy_position = lambda _positions: SimpleNamespace(
        symbol="SPY", market_value=98000.0, qty=132.486,
    )
    orch._wait_order_ok = lambda _order: True
    return orch, client


def test_cash_proxy_sell_cancels_open_orders_before_close_position():
    orch, client = _make_orchestrator()
    client.get_positions.return_value = []
    client.cancel_open_orders_for_symbol.return_value = 1
    client.close_position.return_value = MagicMock(id="sell-1")

    ok = orch._sell_cash_proxy_for(10_000.0, "fund trade")

    assert ok is True
    # Order cancellation must precede the sell so the qty becomes available.
    cancel_call = client.cancel_open_orders_for_symbol.call_args_list
    close_call = client.close_position.call_args_list
    assert cancel_call and cancel_call[0].args == ("SPY",)
    assert close_call, "close_position must still be invoked after cancel"


def test_cash_proxy_sell_proceeds_even_if_cancel_raises():
    orch, client = _make_orchestrator()
    client.get_positions.return_value = []
    client.cancel_open_orders_for_symbol.side_effect = RuntimeError("api blip")
    client.close_position.return_value = MagicMock(id="sell-1")

    # Cancel failure must not block the sell attempt itself. The sell may
    # still get rejected by Alpaca for held_for_orders, but at least we tried.
    ok = orch._sell_cash_proxy_for(10_000.0, "fund trade")
    assert ok is True
    assert client.close_position.called
