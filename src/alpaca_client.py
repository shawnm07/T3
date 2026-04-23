"""Thin wrapper around alpaca-py: account, market data, news, orders."""
from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable

from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import (
    CryptoBarsRequest,
    CryptoLatestQuoteRequest,
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


class AlpacaClient:
    def __init__(self, config: Config):
        paper = config.alpaca.mode == "paper"
        creds = dict(api_key=config.alpaca.api_key, secret_key=config.alpaca.api_secret)
        self.trading = TradingClient(paper=paper, **creds)
        self.stock_data = StockHistoricalDataClient(**creds)
        self.crypto_data = CryptoHistoricalDataClient(**creds)
        self.news_client = NewsClient(**creds)

    # ---------- account ----------
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_account(self):
        return self.trading.get_account()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_positions(self):
        return self.trading.get_all_positions()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_clock(self):
        return self.trading.get_clock()

    # ---------- stock data ----------
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

    def get_stock_quote(self, symbol: str):
        req = StockLatestQuoteRequest(symbol_or_symbols=[symbol])
        return self.stock_data.get_stock_latest_quote(req)[symbol]

    # ---------- crypto ----------
    def get_crypto_bars(self, symbols: Iterable[str], timeframe=TimeFrame.Hour, lookback_hours: int = 24 * 30):
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=lookback_hours)
        req = CryptoBarsRequest(
            symbol_or_symbols=list(symbols), timeframe=timeframe, start=start, end=end,
        )
        return self.crypto_data.get_crypto_bars(req).df

    def get_crypto_quote(self, symbol: str):
        req = CryptoLatestQuoteRequest(symbol_or_symbols=[symbol])
        return self.crypto_data.get_crypto_latest_quote(req)[symbol]

    # ---------- news ----------
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
    ):
        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif_enum = {"day": TimeInForce.DAY, "gtc": TimeInForce.GTC, "ioc": TimeInForce.IOC}[tif.lower()]
        kwargs: dict = dict(symbol=symbol, qty=qty, side=side_enum, time_in_force=tif_enum)
        if stop_loss or take_profit:
            kwargs["order_class"] = OrderClass.BRACKET
            if stop_loss:
                kwargs["stop_loss"] = StopLossRequest(stop_price=round(stop_loss, 2))
            if take_profit:
                kwargs["take_profit"] = TakeProfitRequest(limit_price=round(take_profit, 2))
        if limit_price is not None:
            kwargs["limit_price"] = round(limit_price, 2)
            req = LimitOrderRequest(**kwargs)
        else:
            req = MarketOrderRequest(**kwargs)
        order = self.trading.submit_order(req)
        log.info("Submitted %s %s %s qty=%s order_id=%s", side, symbol, req.order_class or "simple", qty, order.id)
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
        return order

    def close_position(self, symbol: str, qty: float | None = None, percentage: float | None = None):
        from alpaca.trading.requests import ClosePositionRequest
        req = ClosePositionRequest(qty=str(qty) if qty else None, percentage=str(percentage) if percentage else None)
        return self.trading.close_position(symbol, req)

    def cancel_all_orders(self):
        return self.trading.cancel_orders()

    def get_open_orders(self):
        return self.trading.get_orders(GetOrdersRequest(status="open"))

    def get_portfolio_history(self, period: str = "1M", timeframe: str = "1D"):
        from alpaca.trading.requests import GetPortfolioHistoryRequest
        req = GetPortfolioHistoryRequest(period=period, timeframe=timeframe)
        return self.trading.get_portfolio_history(req)
