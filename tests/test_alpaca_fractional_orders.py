import sys
import types
from pathlib import Path
from types import SimpleNamespace


def _install_alpaca_stubs() -> None:
    class _OrderClass:
        BRACKET = "bracket"
        OTO = "oto"

    class _OrderSide:
        BUY = "buy"
        SELL = "sell"

    class _OrderType:
        STOP = "stop"

    class _TimeInForce:
        DAY = "day"
        GTC = "gtc"

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

    data_requests = types.ModuleType("alpaca.data.requests")
    data_requests.NewsRequest = _Request
    data_requests.StockBarsRequest = _Request
    data_requests.StockLatestQuoteRequest = _Request
    sys.modules["alpaca.data.requests"] = data_requests

    timeframe = types.ModuleType("alpaca.data.timeframe")
    timeframe.TimeFrame = SimpleNamespace(Day="day")
    sys.modules["alpaca.data.timeframe"] = timeframe

    sys.modules.setdefault("alpaca.trading", types.ModuleType("alpaca.trading"))
    trading_client = types.ModuleType("alpaca.trading.client")
    trading_client.TradingClient = object
    sys.modules["alpaca.trading.client"] = trading_client

    enums = types.ModuleType("alpaca.trading.enums")
    enums.OrderClass = _OrderClass
    enums.OrderSide = _OrderSide
    enums.OrderType = _OrderType
    enums.TimeInForce = _TimeInForce
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.alpaca_client import AlpacaClient, TimeInForce


class _FakeTrading:
    def __init__(self):
        self.last_request = None
        self.positions = [SimpleNamespace(symbol="TSLA", qty="12.3456")]
        self.assets = {
            "TSLA": SimpleNamespace(
                symbol="TSLA",
                name="Tesla",
                asset_class="us_equity",
                exchange="NASDAQ",
                status="active",
                tradable=True,
                fractionable=True,
            )
        }

    def submit_order(self, req):
        self.last_request = req
        return SimpleNamespace(id="order-1")

    def get_all_positions(self):
        return self.positions

    def get_asset(self, symbol):
        return self.assets[str(symbol).upper()]


def _client():
    client = AlpacaClient.__new__(AlpacaClient)
    client.trading = _FakeTrading()
    client.invalidate_snapshot = lambda: None
    return client


def test_bracket_orders_are_day_tif_even_when_requested_otherwise():
    client = _client()

    client.submit_bracket(
        symbol="TSLA",
        qty=12.3456,
        side="buy",
        stop_loss=99,
        tif="not_day",
    )

    assert client.trading.last_request.time_in_force == TimeInForce.DAY
    assert client.trading.last_request.qty == 12


def test_whole_share_bracket_orders_are_day_tif():
    client = _client()

    client.submit_bracket(
        symbol="TSLA",
        qty=12,
        side="buy",
        stop_loss=99,
        tif="day",
    )

    assert client.trading.last_request.time_in_force == TimeInForce.DAY
    assert client.trading.last_request.qty == 12


def test_fractional_bracket_below_one_share_is_rejected_before_broker():
    client = _client()

    try:
        client.submit_bracket(
            symbol="TSLA",
            qty=0.75,
            side="buy",
            stop_loss=99,
            tif="day",
        )
    except ValueError as exc:
        assert "rounds below 1 whole share" in str(exc)
    else:
        raise AssertionError("expected protected fractional qty below one share to be rejected")


def test_qty_orders_are_day_tif_even_when_requested_otherwise():
    client = _client()

    client.submit_qty(
        symbol="TSLA",
        qty=12,
        side="sell",
        tif="immediate",
    )

    assert client.trading.last_request.time_in_force == TimeInForce.DAY


def test_notional_orders_are_day_tif_even_when_requested_otherwise():
    client = _client()

    client.submit_notional(
        symbol="TSLA",
        notional=500,
        side="buy",
        tif="not_day",
    )

    assert client.trading.last_request.time_in_force == TimeInForce.DAY


def test_standalone_stop_loss_keeps_fractional_qty_and_simple_order():
    client = _client()

    client.submit_stop_loss(
        symbol="TSLA",
        qty=12.345678,
        stop_price=384.481,
        tif="not_day",
        client_order_id="stop-1",
    )

    req = client.trading.last_request
    assert req.time_in_force == TimeInForce.DAY
    assert req.qty == 12.345678
    assert req.side == "sell"
    assert req.type == "stop"
    assert req.order_class is None
    assert getattr(req, "stop_loss", None) is None
    assert req.stop_price == 384.48
    assert req.client_order_id == "stop-1"


def test_whole_share_standalone_stop_loss_can_use_gtc():
    client = _client()

    client.submit_stop_loss(
        symbol="TSLA",
        qty=12,
        stop_price=384.481,
        tif="gtc",
        client_order_id="stop-gtc",
    )

    req = client.trading.last_request
    assert req.time_in_force == TimeInForce.GTC
    assert req.qty == 12


def test_precision_tail_standalone_stop_loss_uses_day_tif():
    client = _client()

    client.submit_stop_loss(
        symbol="TSLA",
        qty=180.999999999,
        stop_price=384.481,
        tif="gtc",
    )

    req = client.trading.last_request
    assert req.time_in_force == TimeInForce.DAY
    assert req.qty == 180.999999999


def test_asset_preflight_rejects_not_tradable():
    client = _client()
    client.trading.assets["AKAN"] = SimpleNamespace(
        symbol="AKAN",
        name="Akan",
        asset_class="us_equity",
        exchange="NASDAQ",
        status="active",
        tradable=False,
        fractionable=True,
    )

    submitted_qty, audit, reject = client.normalize_buy_qty_for_asset("AKAN", 170.8276)

    assert submitted_qty == 170.8276
    assert reject == "asset_not_tradable"
    assert audit["asset"]["tradable"] is False


def test_asset_preflight_rounds_non_fractionable_buy_to_whole_share():
    client = _client()
    client.trading.assets["AVLN"] = SimpleNamespace(
        symbol="AVLN",
        name="Avalon",
        asset_class="us_equity",
        exchange="NYSE",
        status="active",
        tradable=True,
        fractionable=False,
    )

    submitted_qty, audit, reject = client.normalize_buy_qty_for_asset("AVLN", 49.9494)

    assert reject is None
    assert submitted_qty == 49.0
    assert audit["qty_adjustment"] == "rounded_down_to_whole_share_for_non_fractionable_asset"
    assert audit["asset"]["fractionable"] is False


def test_close_position_uses_day_qty_order():
    client = _client()

    client.close_position("TSLA", percentage=50)

    assert client.trading.last_request.time_in_force == TimeInForce.DAY
    assert client.trading.last_request.side == "sell"
    assert round(float(client.trading.last_request.qty), 4) == 6.1728


if __name__ == "__main__":
    test_bracket_orders_are_day_tif_even_when_requested_otherwise()
    test_whole_share_bracket_orders_are_day_tif()
    test_fractional_bracket_below_one_share_is_rejected_before_broker()
    test_qty_orders_are_day_tif_even_when_requested_otherwise()
    test_notional_orders_are_day_tif_even_when_requested_otherwise()
    test_standalone_stop_loss_keeps_fractional_qty_and_simple_order()
    test_whole_share_standalone_stop_loss_can_use_gtc()
    test_precision_tail_standalone_stop_loss_uses_day_tif()
    test_asset_preflight_rejects_not_tradable()
    test_asset_preflight_rounds_non_fractionable_buy_to_whole_share()
    test_close_position_uses_day_qty_order()
    print("alpaca day order tests passed")
