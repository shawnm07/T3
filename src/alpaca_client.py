"""Thin wrapper around alpaca-py: account, market data, news, orders."""
from __future__ import annotations
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Iterable

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import (
    NewsRequest,
    StockBarsRequest,
    StockLatestQuoteRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
from alpaca.trading.requests import (
    GetOrdersRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
)
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import Config

log = logging.getLogger(__name__)

# Snapshot cache TTL — keeps the (account, positions) view consistent for a
# scan cycle without re-hitting Alpha Vantage dozens of times.
_SNAPSHOT_TTL_SEC = 15.0


class AlpacaClient:
    def __init__(self, config: Config):
        paper = config.alpaca.mode == "paper"
        creds = dict(api_key=config.alpaca.api_key, secret_key=config.alpaca.api_secret)
        self.trading = TradingClient(paper=paper, **creds)
        self.stock_data = StockHistoricalDataClient(**creds)
        self.news_client = NewsClient(**creds)
        self._data_timeout = 30
        # Lazy-initialised pricing service (imported here to avoid a circular
        # import at module load — valuation.py only needs the instance).
        self._pricing = None
        self._snapshot_cache: tuple[float, object, list] | None = None

    def _get_pricing(self):
        if self._pricing is None:
            from src.valuation import PricingService
            self._pricing = PricingService(alpaca_client=self)
        return self._pricing

    # ---------- account (INDEPENDENT VALUATION) ----------
    # NOTE: Alpaca paper's reported equity, market_value, unrealized_pl/plpc,
    # and current_price are unreliable. get_account() / get_positions() below
    # return recomputed views built from independently fetched prices. The
    # *_raw variants return the unmodified Alpaca objects (rarely needed).

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_account_raw(self):
        return self.trading.get_account()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_positions_raw(self):
        return self.trading.get_all_positions()

    def get_snapshot(self, *, force_refresh: bool = False, log_detail: bool = True):
        """Return (ValuedAccount, list[ValuedPosition]) with independent pricing.

        Cached for ``_SNAPSHOT_TTL_SEC`` so multiple callers within one scan
        share a single valuation pass.
        """
        import time as _time
        from src.valuation import build_snapshot
        now = _time.monotonic()
        if (not force_refresh and self._snapshot_cache
                and (now - self._snapshot_cache[0]) < _SNAPSHOT_TTL_SEC):
            _, acct, pos = self._snapshot_cache
            return acct, pos
        acct, pos = build_snapshot(self, pricing=self._get_pricing(), log_detail=log_detail)
        self._snapshot_cache = (now, acct, pos)
        return acct, pos

    def invalidate_snapshot(self) -> None:
        self._snapshot_cache = None

    def get_account(self):
        acct, _ = self.get_snapshot(log_detail=False)
        return acct

    def get_positions(self):
        _, pos = self.get_snapshot(log_detail=False)
        return pos

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_clock(self):
        return self.trading.get_clock()

    # ---------- stock data ----------
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def get_stock_bars(self, symbols: Iterable[str], timeframe=TimeFrame.Day, lookback_days: int = 252):
        end = datetime.now(timezone.utc) - timedelta(minutes=20)
        start = end - timedelta(days=lookback_days * 2)
        req = StockBarsRequest(
            symbol_or_symbols=list(symbols),
            timeframe=timeframe,
            start=start,
            end=end,
            adjustment="split",
        )
        return self.stock_data.get_stock_bars(req).df

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def get_stock_quote(self, symbol: str):
        req = StockLatestQuoteRequest(symbol_or_symbols=[symbol])
        return self.stock_data.get_stock_latest_quote(req)[symbol]

    # ---------- news ----------
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def get_news(self, symbols: Iterable[str] | None = None, limit: int = 50, days_back: int = 3):
        sym = ",".join(symbols) if symbols else None
        req = NewsRequest(
            symbols=sym,
            limit=limit,
            start=datetime.now(timezone.utc) - timedelta(days=days_back),
        )
        resp = self.news_client.get_news(req)
        data = getattr(resp, "data", None) or {}
        items: list = []
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    items.extend(v)
        elif isinstance(data, list):
            items = data
        return items

    # ---------- orders ----------
    def submit_bracket(
        self,
        symbol: str,
        qty: float,
        side: str,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        tif: str = "day",
        limit_price: float | None = None,
        stop_loss_limit_price: float | None = None,
        client_order_id: str | None = None,
    ):
        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif_enum = {"day": TimeInForce.DAY, "gtc": TimeInForce.GTC, "ioc": TimeInForce.IOC}[tif.lower()]
        kwargs: dict = dict(symbol=symbol, qty=qty, side=side_enum, time_in_force=tif_enum)
        if client_order_id:
            kwargs["client_order_id"] = client_order_id
        if stop_loss or take_profit:
            kwargs["order_class"] = OrderClass.BRACKET if (stop_loss and take_profit) else OrderClass.OTO
            if stop_loss:
                stop_kwargs: dict = {"stop_price": round(stop_loss, 2)}
                if stop_loss_limit_price is not None:
                    stop_kwargs["limit_price"] = round(stop_loss_limit_price, 2)
                kwargs["stop_loss"] = StopLossRequest(**stop_kwargs)
            if take_profit:
                kwargs["take_profit"] = TakeProfitRequest(limit_price=round(take_profit, 2))
        if limit_price is not None:
            kwargs["limit_price"] = round(limit_price, 2)
            req = LimitOrderRequest(**kwargs)
        else:
            req = MarketOrderRequest(**kwargs)
        order = self.trading.submit_order(req)
        log.info("Submitted %s %s %s qty=%s order_id=%s", side, symbol, req.order_class or "simple", qty, order.id)
        self.invalidate_snapshot()
        return order

    def submit_qty(self, symbol: str, qty: float, side: str, tif: str = "day"):
        """Submit a plain market order sized by exact share count (no bracket)."""
        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif_enum = {"day": TimeInForce.DAY, "gtc": TimeInForce.GTC, "ioc": TimeInForce.IOC}[tif.lower()]
        req = MarketOrderRequest(
            symbol=symbol, qty=qty,
            side=side_enum, time_in_force=tif_enum,
        )
        order = self.trading.submit_order(req)
        log.info("Submitted qty %s %s %s order_id=%s", side, symbol, qty, order.id)
        self.invalidate_snapshot()
        return order

    def submit_notional(self, symbol: str, notional: float, side: str, tif: str = "day"):
        """Submit a plain market order sized by dollar notional (fractional-share)."""
        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif_enum = {"day": TimeInForce.DAY, "gtc": TimeInForce.GTC, "ioc": TimeInForce.IOC}[tif.lower()]
        req = MarketOrderRequest(
            symbol=symbol, notional=round(notional, 2),
            side=side_enum, time_in_force=tif_enum,
        )
        order = self.trading.submit_order(req)
        log.info("Submitted notional %s %s $%.2f order_id=%s", side, symbol, notional, order.id)
        self.invalidate_snapshot()
        return order

    def close_position(self, symbol: str, qty: float | None = None, percentage: float | None = None):
        from alpaca.trading.requests import ClosePositionRequest
        # alpaca-py requires one of qty/percentage. Default to a full close (100%)
        # when the caller specifies neither.
        if qty is None and percentage is None:
            percentage = 100
        req = ClosePositionRequest(
            qty=str(qty) if qty is not None else None,
            percentage=str(percentage) if percentage is not None else None,
        )
        res = self.trading.close_position(symbol, req)
        self.invalidate_snapshot()
        return res

    def get_order(self, order_id: str):
        return self.trading.get_order_by_id(order_id)

    def wait_for_order_fill(self, order_id: str, timeout_s: float = 30.0, poll_s: float = 1.0):
        """Poll until the order reaches a terminal state or timeout.

        Returns (order, ok) where ok=True means the order filled (possibly
        partially with filled_qty > 0). Terminal non-fill states (rejected,
        canceled, expired, suspended) return ok=False.
        On timeout: returns ok=True if filled_qty > 0 else False.
        Never raises — any API error is logged and returns (None, False).
        """
        terminal_ok = {"filled"}
        terminal_fail = {"rejected", "canceled", "cancelled", "expired", "suspended", "replaced"}
        deadline = time.monotonic() + timeout_s
        last = None
        while True:
            try:
                order = self.trading.get_order_by_id(order_id)
            except Exception as e:
                log.warning("get_order(%s) failed: %s", order_id, e)
                return (last, False)
            last = order
            status = str(getattr(order, "status", "") or "").lower().replace("orderstatus.", "")
            if status in terminal_ok:
                return (order, True)
            if status in terminal_fail:
                filled_qty = float(getattr(order, "filled_qty", 0) or 0)
                return (order, filled_qty > 0)
            if time.monotonic() >= deadline:
                filled_qty = float(getattr(order, "filled_qty", 0) or 0)
                log.warning("Order %s not terminal after %.1fs (status=%s, filled_qty=%.4f)",
                            order_id, timeout_s, status, filled_qty)
                return (order, filled_qty > 0)
            time.sleep(poll_s)

    def cancel_all_orders(self):
        return self.trading.cancel_orders()

    def cancel_order(self, order_id: str):
        return self.trading.cancel_order_by_id(order_id)

    def get_open_orders(self):
        return self.trading.get_orders(GetOrdersRequest(status="open"))

    def get_portfolio_history(self, period: str = "1M", timeframe: str = "1D"):
        from alpaca.trading.requests import GetPortfolioHistoryRequest
        req = GetPortfolioHistoryRequest(period=period, timeframe=timeframe)
        return self.trading.get_portfolio_history(req)
