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
    def __init__(self, *, filled_qty: float, filled_avg_price: float):
        self.filled_qty = filled_qty
        self.filled_avg_price = filled_avg_price
        self.qty_orders = []
        self.stop_orders = []

    def submit_qty(self, **kwargs):
        self.qty_orders.append(kwargs)
        return SimpleNamespace(id="entry-1")

    def submit_stop_loss(self, **kwargs):
        self.stop_orders.append(kwargs)
        return SimpleNamespace(id="stop-1")

    def wait_for_order_fill(self, order_id, timeout_s, poll_s):
        return (
            SimpleNamespace(
                status="filled",
                filled_qty=str(self.filled_qty),
                filled_avg_price=str(self.filled_avg_price),
            ),
            True,
        )


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
