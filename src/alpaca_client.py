"""Thin wrapper around alpaca-py: account, market data, news, orders."""
from __future__ import annotations
import logging
import math
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
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
from alpaca.trading.enums import OrderClass, OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import (
    GetOrdersRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    StopOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
)
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import Config

log = logging.getLogger(__name__)

# Snapshot cache TTL — keeps the (account, positions) view consistent for a
# scan cycle without re-hitting Alpha Vantage dozens of times.
_SNAPSHOT_TTL_SEC = 15.0


def _round_cents(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


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
        self._asset_info_cache: dict[str, dict] = {}

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

    # ---------- assets ----------
    @staticmethod
    def _enum_value(value):
        return getattr(value, "value", value)

    def get_asset_info(self, symbol: str) -> dict:
        """Return cached Alpaca asset metadata needed for order preflight."""
        sym = str(symbol or "").strip().upper()
        if not sym:
            raise ValueError("empty symbol")
        cache = getattr(self, "_asset_info_cache", None)
        if cache is None:
            cache = {}
            self._asset_info_cache = cache
        if sym in cache:
            return dict(cache[sym])
        asset = self.trading.get_asset(sym)

        def _get(name: str):
            if isinstance(asset, dict):
                return asset.get(name)
            return getattr(asset, name, None)

        info = {
            "symbol": str(_get("symbol") or sym).upper(),
            "name": _get("name"),
            "asset_class": self._enum_value(_get("asset_class")),
            "exchange": self._enum_value(_get("exchange")),
            "status": self._enum_value(_get("status")),
            "tradable": _get("tradable"),
            "fractionable": _get("fractionable"),
        }
        cache[sym] = info
        return dict(info)

    def normalize_buy_qty_for_asset(
        self,
        symbol: str,
        qty: float,
    ) -> tuple[float, dict, str | None]:
        """Validate tradability and convert non-fractionable buys to whole qty.

        Returns ``(submitted_qty, audit, reject_reason)``. ``reject_reason`` is
        ``None`` when the order can proceed.
        """
        try:
            qty_f = float(qty)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"qty not numeric for {symbol}: {qty!r}") from exc
        audit: dict = {
            "symbol": str(symbol or "").upper(),
            "requested_qty": qty_f,
        }
        if qty_f <= 0:
            return qty_f, audit, "non_positive_qty"
        try:
            info = self.get_asset_info(symbol)
        except Exception as exc:
            audit["lookup_error"] = str(exc)
            return qty_f, audit, f"asset_lookup_failed: {exc}"
        audit["asset"] = info
        status = str(info.get("status") or "").lower()
        if status and status != "active":
            return qty_f, audit, f"asset_not_active: {status}"
        if info.get("tradable") is False:
            return qty_f, audit, "asset_not_tradable"
        submitted_qty = qty_f
        if info.get("fractionable") is False:
            whole_qty = math.floor(qty_f)
            audit["fractionable"] = False
            if whole_qty < 1:
                return qty_f, audit, "asset_not_fractionable_qty_below_one_share"
            if abs(qty_f - whole_qty) > 1e-9:
                submitted_qty = float(whole_qty)
                audit["qty_adjustment"] = "rounded_down_to_whole_share_for_non_fractionable_asset"
                audit["submitted_qty"] = submitted_qty
                log.warning(
                    "Rounded non-fractionable %s buy qty %.6f down to %.0f whole shares",
                    symbol, qty_f, submitted_qty,
                )
        audit.setdefault("submitted_qty", submitted_qty)
        return submitted_qty, audit, None

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
    @staticmethod
    def _day_time_in_force(tif: str | None, *, symbol: str, side: str) -> TimeInForce:
        requested = str(tif or "day").lower()
        if requested != "day":
            log.warning(
                "Forcing %s %s time_in_force %s -> day",
                side.lower(), symbol, requested,
            )
        return TimeInForce.DAY

    @staticmethod
    def _is_whole_qty(qty: float) -> bool:
        try:
            qty_f = float(qty)
        except (TypeError, ValueError):
            return False
        return qty_f > 0 and abs(qty_f - round(qty_f)) < 1e-9

    @classmethod
    def _standalone_stop_time_in_force(
        cls,
        tif: str | None,
        *,
        symbol: str,
        side: str,
        qty: float,
    ) -> TimeInForce:
        requested = str(tif or "day").lower()
        if requested == "gtc":
            if cls._is_whole_qty(qty):
                gtc = getattr(TimeInForce, "GTC", None)
                if gtc is not None:
                    return gtc
                log.warning("TimeInForce.GTC unavailable; forcing %s %s stop to day", side, symbol)
            else:
                log.warning(
                    "Forcing fractional %s %s stop time_in_force gtc -> day (qty=%s)",
                    side.lower(), symbol, qty,
                )
            return TimeInForce.DAY
        return cls._day_time_in_force(tif, symbol=symbol, side=side)

    @staticmethod
    def _protected_order_qty(symbol: str, qty: float) -> int:
        """Alpaca bracket/OTO orders must be whole-share orders."""
        try:
            qty_f = float(qty)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"qty not numeric for protected {symbol} order: {qty!r}") from exc
        if qty_f <= 0:
            raise ValueError(f"protected {symbol} order qty must be > 0, got {qty!r}")
        whole_qty = math.floor(qty_f)
        if whole_qty < 1:
            raise ValueError(
                f"protected {symbol} order qty rounds below 1 whole share "
                f"(requested {qty_f:.6f})"
            )
        if abs(qty_f - whole_qty) > 1e-9:
            log.warning(
                "Rounded protected %s order qty %.6f down to %d whole shares",
                symbol, qty_f, whole_qty,
            )
        return whole_qty

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
        tif_enum = self._day_time_in_force(tif, symbol=symbol, side=side)
        has_stop = stop_loss not in (None, "")
        has_take_profit = take_profit not in (None, "")
        protected = has_stop or has_take_profit
        submitted_qty = self._protected_order_qty(symbol, qty) if protected else qty
        kwargs: dict = dict(symbol=symbol, qty=submitted_qty, side=side_enum, time_in_force=tif_enum)
        if client_order_id:
            kwargs["client_order_id"] = client_order_id
        if protected:
            kwargs["order_class"] = OrderClass.BRACKET if (has_stop and has_take_profit) else OrderClass.OTO
            if has_stop:
                stop_kwargs: dict = {"stop_price": _round_cents(stop_loss)}
                if stop_loss_limit_price is not None:
                    stop_kwargs["limit_price"] = _round_cents(stop_loss_limit_price)
                kwargs["stop_loss"] = StopLossRequest(**stop_kwargs)
            if has_take_profit:
                kwargs["take_profit"] = TakeProfitRequest(limit_price=_round_cents(take_profit))
        if limit_price is not None:
            kwargs["limit_price"] = _round_cents(limit_price)
            req = LimitOrderRequest(**kwargs)
        else:
            req = MarketOrderRequest(**kwargs)
        order = self.trading.submit_order(req)
        log.info("Submitted %s %s %s qty=%s order_id=%s", side, symbol, req.order_class or "simple", submitted_qty, order.id)
        self.invalidate_snapshot()
        return order

    def submit_qty(
        self,
        symbol: str,
        qty: float,
        side: str,
        tif: str = "day",
        client_order_id: str | None = None,
    ):
        """Submit a plain market order sized by exact share count (no bracket)."""
        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif_enum = self._day_time_in_force(tif, symbol=symbol, side=side)
        kwargs: dict = dict(
            symbol=symbol, qty=qty,
            side=side_enum, time_in_force=tif_enum,
        )
        if client_order_id:
            kwargs["client_order_id"] = client_order_id
        req = MarketOrderRequest(**kwargs)
        order = self.trading.submit_order(req)
        log.info("Submitted qty %s %s %s order_id=%s", side, symbol, qty, order.id)
        self.invalidate_snapshot()
        return order

    def submit_notional(self, symbol: str, notional: float, side: str, tif: str = "day"):
        """Submit a plain market order sized by dollar notional (fractional-share)."""
        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif_enum = self._day_time_in_force(tif, symbol=symbol, side=side)
        req = MarketOrderRequest(
            symbol=symbol, notional=round(notional, 2),
            side=side_enum, time_in_force=tif_enum,
        )
        order = self.trading.submit_order(req)
        log.info("Submitted notional %s %s $%.2f order_id=%s", side, symbol, notional, order.id)
        self.invalidate_snapshot()
        return order

    def submit_stop_loss(
        self,
        symbol: str,
        qty: float,
        stop_price: float,
        side: str = "sell",
        tif: str = "day",
        client_order_id: str | None = None,
    ):
        """Submit a standalone stop order.

        This intentionally uses Alpaca's simple ``type=stop`` order shape
        instead of an OTO/bracket ``stop_loss`` leg so fractional entries can
        be protected after their actual fill quantity is known.
        """
        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif_enum = self._standalone_stop_time_in_force(
            tif, symbol=symbol, side=side, qty=qty,
        )
        kwargs: dict = dict(
            symbol=symbol,
            qty=qty,
            side=side_enum,
            type=OrderType.STOP,
            time_in_force=tif_enum,
            stop_price=_round_cents(stop_price),
        )
        if client_order_id:
            kwargs["client_order_id"] = client_order_id
        req = StopOrderRequest(**kwargs)
        order = self.trading.submit_order(req)
        log.info(
            "Submitted standalone stop %s %s qty=%s stop=%.2f order_id=%s",
            side, symbol, qty, _round_cents(stop_price), order.id,
        )
        self.invalidate_snapshot()
        return order

    def close_position(self, symbol: str, qty: float | None = None, percentage: float | None = None):
        sym = str(symbol or "").upper()
        raw_qty = 0.0
        for pos in self.get_positions_raw() or []:
            if str(getattr(pos, "symbol", "") or "").upper() == sym:
                raw_qty = float(getattr(pos, "qty", 0) or 0)
                break
        if raw_qty == 0:
            raise ValueError(f"no open position for {symbol}")
        if qty is None:
            pct = 100.0 if percentage is None else max(0.0, min(100.0, float(percentage)))
            close_qty = abs(raw_qty) * (pct / 100.0)
        else:
            close_qty = min(abs(float(qty)), abs(raw_qty))
        if close_qty <= 0:
            raise ValueError(f"close quantity must be > 0 for {symbol}")
        side = "sell" if raw_qty > 0 else "buy"
        return self.submit_qty(sym, close_qty, side=side, tif="day")

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

    def get_orders(
        self,
        status: str = "open",
        *,
        limit: int | None = None,
        after: datetime | None = None,
        until: datetime | None = None,
        side: str | None = None,
        symbols: list[str] | None = None,
    ):
        side_enum = None
        if side:
            side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        return self.trading.get_orders(GetOrdersRequest(
            status=status,
            limit=limit,
            after=after,
            until=until,
            side=side_enum,
            symbols=symbols,
        ))

    def cancel_open_orders_for_symbol(self, symbol: str) -> int:
        """Cancel open parent/child orders for a symbol before a trim/exit."""
        sym = str(symbol or "").upper()
        if not sym:
            return 0
        cancelled = 0
        for order in self.get_open_orders() or []:
            order_sym = str(getattr(order, "symbol", "") or "").upper()
            if order_sym != sym:
                continue
            order_id = str(getattr(order, "id", "") or "")
            if not order_id:
                continue
            self.cancel_order(order_id)
            cancelled += 1
        if cancelled:
            log.info("Cancelled %d open order(s) for %s", cancelled, sym)
            self.invalidate_snapshot()
        return cancelled

    def get_portfolio_history(self, period: str = "1M", timeframe: str = "1D"):
        from alpaca.trading.requests import GetPortfolioHistoryRequest
        req = GetPortfolioHistoryRequest(period=period, timeframe=timeframe)
        return self.trading.get_portfolio_history(req)
