from __future__ import annotations

import json
from types import SimpleNamespace

from src.config import AlpacaConfig, Config
from src.executor import TradeExecutor


def _config() -> Config:
    return Config(
        alpaca=AlpacaConfig(
            api_key="test",
            api_secret="test",
            base_url="",
            data_url="",
            mode="paper",
        ),
        raw={
            "execution": {"fill_timeout_s": 0, "fill_poll_s": 0},
            "risk": {"hard_stop_loss_pct": 0.01},
        },
    )


class _FakeClient:
    def __init__(
        self,
        *,
        filled_qty: float,
        filled_avg_price: float,
        normalizer=None,
        submit_failures=None,
        existing_order=None,
        position_qty: float | None = None,
    ):
        self.filled_qty = filled_qty
        self.filled_avg_price = filled_avg_price
        self.normalizer = normalizer
        self.submit_failures = list(submit_failures or [])
        self.existing_order = existing_order
        self.position_qty = position_qty
        self.qty_orders = []
        self.stop_orders = []
        self.cancelled_orders = []

    def submit_qty(self, **kwargs):
        self.qty_orders.append(kwargs)
        if self.submit_failures:
            raise self.submit_failures.pop(0)
        return SimpleNamespace(id="entry-1")

    def submit_stop_loss(self, **kwargs):
        self.stop_orders.append(kwargs)
        return SimpleNamespace(id="stop-1")

    def normalize_buy_qty_for_asset(self, symbol, qty):
        if self.normalizer is not None:
            return self.normalizer(symbol, qty)
        return qty, {"symbol": symbol, "requested_qty": qty, "submitted_qty": qty}, None

    def wait_for_order_fill(self, order_id, timeout_s, poll_s):
        return (
            SimpleNamespace(
                status="filled",
                filled_qty=str(self.filled_qty),
                filled_avg_price=str(self.filled_avg_price),
            ),
            True,
        )

    def get_order(self, order_id):
        if self.existing_order is not None and str(self.existing_order.id) == str(order_id):
            return self.existing_order
        return SimpleNamespace(id=order_id, status="filled", filled_qty=str(self.filled_qty))

    def cancel_order(self, order_id):
        self.cancelled_orders.append(str(order_id))
        if self.existing_order is not None and str(self.existing_order.id) == str(order_id):
            self.existing_order.status = "canceled"
        return None

    def get_positions_raw(self):
        if self.position_qty is None:
            return []
        return [SimpleNamespace(symbol="AMD", qty=str(self.position_qty))]


def test_ai_buy_uses_simple_fractional_entry_then_standalone_stop(monkeypatch):
    logs = []
    monkeypatch.setattr("src.executor.log_trade", lambda payload: logs.append(payload))
    client = _FakeClient(filled_qty=43.0201, filled_avg_price=386.0)
    executor = TradeExecutor(client, _config())

    result = executor.execute_ai_bracket(
        symbol="TSLA",
        qty=43.0201,
        entry_price=388.355,
        stop_loss=384.48,
        reason="rebalance",
    )

    assert result.ok
    assert result.order_id == "entry-1"
    assert result.stop_order_id == "stop-1"
    assert client.qty_orders == [{
        "symbol": "TSLA",
        "qty": 43.0201,
        "side": "buy",
        "tif": "day",
        "client_order_id": client.qty_orders[0]["client_order_id"],
    }]
    assert client.stop_orders == [{
        "symbol": "TSLA",
        "qty": 43.0201,
        "stop_price": 384.48,
        "side": "sell",
        "tif": "day",
        "client_order_id": client.stop_orders[0]["client_order_id"],
    }]
    assert logs[0]["protective_stop"]["placement"] == "standalone_after_entry_fill"


def test_stale_ai_stop_above_actual_fill_recomputes_from_fill(monkeypatch):
    monkeypatch.setattr("src.executor.log_trade", lambda _payload: None)
    client = _FakeClient(filled_qty=33.9989, filled_avg_price=418.56)
    executor = TradeExecutor(client, _config())

    result = executor.execute_ai_bracket(
        symbol="WDC",
        qty=33.9989,
        entry_price=429.975,
        stop_loss=425.68,
        reason="rebalance",
    )

    assert result.ok
    assert client.qty_orders[0]["qty"] == 33.9989
    assert client.stop_orders[0]["qty"] == 33.9989
    assert client.stop_orders[0]["stop_price"] == 414.38
    assert result.stop_price == 414.38


def test_non_fractionable_ai_buy_rounds_entry_and_stop_to_whole_qty(monkeypatch):
    monkeypatch.setattr("src.executor.log_trade", lambda _payload: None)
    client = _FakeClient(
        filled_qty=49.0,
        filled_avg_price=28.86,
        normalizer=lambda _symbol, qty: (
            49.0,
            {
                "symbol": "AVLN",
                "requested_qty": qty,
                "submitted_qty": 49.0,
                "asset": {"tradable": True, "fractionable": False},
                "qty_adjustment": "rounded_down_to_whole_share_for_non_fractionable_asset",
            },
            None,
        ),
    )
    executor = TradeExecutor(client, _config())

    result = executor.execute_ai_bracket(
        symbol="AVLN",
        qty=49.9494,
        entry_price=28.86,
        stop_loss=28.58,
        reason="rebalance",
    )

    assert result.ok
    assert client.qty_orders[0]["qty"] == 49.0
    assert client.stop_orders[0]["qty"] == 49.0


def test_not_tradable_ai_buy_rejects_before_entry_order(monkeypatch):
    logs = []
    monkeypatch.setattr("src.executor.log_trade", lambda payload: logs.append(payload))
    client = _FakeClient(
        filled_qty=0.0,
        filled_avg_price=0.0,
        normalizer=lambda _symbol, qty: (
            qty,
            {
                "symbol": "AKAN",
                "requested_qty": qty,
                "asset": {"tradable": False, "fractionable": True},
            },
            "asset_not_tradable",
        ),
    )
    executor = TradeExecutor(client, _config())

    result = executor.execute_ai_bracket(
        symbol="AKAN",
        qty=170.8276,
        entry_price=77.402,
        stop_loss=76.63,
        reason="rebalance",
    )

    assert not result.ok
    assert result.status == "rejected"
    assert result.message == "asset_not_tradable"
    assert client.qty_orders == []
    assert logs[0]["ai_audit"]["asset_check"]["asset"]["tradable"] is False


def test_wash_trade_buy_retry_cancels_old_stop_and_replaces_consolidated_stop(monkeypatch):
    logs = []
    monkeypatch.setattr("src.executor.log_trade", lambda payload: logs.append(payload))
    blocker_id = "5859a8ea-4400-4592-9c66-5c0f9795c681"
    wash_error = Exception(json.dumps({
        "code": 40310000,
        "existing_order_id": blocker_id,
        "message": "potential wash trade detected. use complex orders",
        "reject_reason": "opposite side market/stop order exists",
    }))
    client = _FakeClient(
        filled_qty=9.055,
        filled_avg_price=361.49,
        submit_failures=[wash_error],
        existing_order=SimpleNamespace(
            id=blocker_id,
            symbol="AMD",
            side="sell",
            type="stop",
            qty="43.697",
            stop_price="355.22",
            status="new",
            order_class="simple",
            client_order_id="tb-stop-AMD-old",
        ),
        position_qty=52.752,
    )
    executor = TradeExecutor(client, _config())

    result = executor.execute_ai_bracket(
        symbol="AMD",
        qty=9.055,
        entry_price=362.03,
        stop_loss=358.41,
        reason="rebalance add",
    )

    assert result.ok
    assert len(client.qty_orders) == 2
    assert client.cancelled_orders == [blocker_id]
    assert client.stop_orders[0]["qty"] == 52.752
    assert client.stop_orders[0]["stop_price"] == 358.41
    recovery_logs = [row for row in logs if row["event"] == "wash_trade_recovery"]
    assert recovery_logs
    assert recovery_logs[0]["recovery"]["existing_order_id"] == blocker_id


def test_wash_trade_retry_failure_restores_cancelled_stop(monkeypatch):
    logs = []
    monkeypatch.setattr("src.executor.log_trade", lambda payload: logs.append(payload))
    blocker_id = "5859a8ea-4400-4592-9c66-5c0f9795c681"
    wash_error = Exception(json.dumps({
        "code": 40310000,
        "existing_order_id": blocker_id,
        "message": "potential wash trade detected. use complex orders",
        "reject_reason": "opposite side market/stop order exists",
    }))
    client = _FakeClient(
        filled_qty=0,
        filled_avg_price=0,
        submit_failures=[wash_error, Exception("retry still rejected")],
        existing_order=SimpleNamespace(
            id=blocker_id,
            symbol="AMD",
            side="sell",
            type="stop",
            qty="43.697",
            stop_price="355.22",
            status="new",
            order_class="simple",
            client_order_id="tb-stop-AMD-old",
        ),
    )
    executor = TradeExecutor(client, _config())

    result = executor.execute_ai_bracket(
        symbol="AMD",
        qty=9.055,
        entry_price=362.03,
        stop_loss=358.41,
        reason="rebalance add",
    )

    assert not result.ok
    assert result.status == "rejected"
    assert client.cancelled_orders == [blocker_id]
    assert client.stop_orders[0]["qty"] == 43.697
    assert client.stop_orders[0]["stop_price"] == 355.22
    failed = [row for row in logs if row["event"] == "wash_trade_recovery_failed"]
    assert failed
    assert failed[0]["recovery"]["restored_stop"]["status"] == "submitted"
