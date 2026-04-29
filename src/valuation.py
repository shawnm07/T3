"""Independent account/position valuation.

Alpaca paper's ``equity``, ``market_value``, ``unrealized_pl``,
``unrealized_plpc``, and ``current_price`` fields are unreliable for live
decisions. This module recomputes them from:

* share quantity + average entry price (from Alpaca — reliable)
* cash balance (from Alpaca — reliable)
* **independently fetched** current market prices (Alpha Vantage for stocks)

Every call site in the bot that needs equity / P/L / market value should go
through :func:`build_snapshot` (or use the wrapper methods on
:class:`AlpacaClient`) rather than reading Alpaca's fields directly.

Extended-hours pricing: Alpha Vantage's ``GLOBAL_QUOTE`` returns the latest
regular-market trade. If an extended-hours (pre/post-market) price is
available, we log that it is being used; otherwise we log that we are
falling back to the regular-market last trade.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

import requests

from src.api_keys import KeyPool

log = logging.getLogger(__name__)

# Backwards-compat: the old single-key constant is still consulted as a
# fallback by KeyPool.from_env when only ALPHA_VANTAGE_API_KEY (singular)
# is set. New deployments should use ALPHA_VANTAGE_API_KEYS (plural).
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
_AV_URL = "https://www.alphavantage.co/query"

# Price cache TTL (seconds). Keeps scan hot loops under Alpha Vantage
# rate limits while still being fresh enough for sizing decisions.
_PRICE_TTL = 20.0


@dataclass
class PricedQuote:
    symbol: str
    price: float
    source: str              # "alpha_vantage" | "alpha_vantage_extended" | "alpaca_stock_fallback"
    extended_hours: bool = False


class PricingService:
    """Fetch live prices for stocks from Alpha Vantage.

    Falls back to Alpaca's latest stock quote if Alpha Vantage is unreachable
    or rate-limited. Caches prices for ``_PRICE_TTL`` seconds.
    """

    def __init__(self, alpaca_client=None, av_key: str | None = None,
                 av_pool: KeyPool | None = None, ttl: float = _PRICE_TTL):
        self._alpaca = alpaca_client
        # Prefer pool; fall back to single key if explicitly passed.
        self._av_pool = av_pool or KeyPool.from_env(
            "alpha_vantage", "ALPHA_VANTAGE_API_KEYS",
            singular_env="ALPHA_VANTAGE_API_KEY",
        )
        self._av_key = av_key  # legacy override; only used if pool empty
        self._ttl = ttl
        self._cache: dict[str, tuple[float, PricedQuote]] = {}
        self._session = requests.Session()

    # ---------- public ----------
    def get_price(self, symbol: str) -> PricedQuote | None:
        now = time.monotonic()
        cached = self._cache.get(symbol)
        if cached and (now - cached[0]) < self._ttl:
            return cached[1]
        quote = self._fetch(symbol)
        if quote is not None:
            self._cache[symbol] = (now, quote)
        return quote

    def get_prices(self, symbols: Iterable[str]) -> dict[str, PricedQuote]:
        out: dict[str, PricedQuote] = {}
        for s in symbols:
            q = self.get_price(s)
            if q is not None:
                out[s] = q
        return out

    # ---------- fetchers ----------
    def _fetch(self, symbol: str) -> PricedQuote | None:
        q = self._fetch_alpha_vantage(symbol)
        if q is not None:
            return q
        return self._fetch_alpaca_stock(symbol)

    def _fetch_alpha_vantage(self, symbol: str) -> PricedQuote | None:
        # Try keys in rotation; on throttle, mark and try next.
        max_attempts = max(1, len(getattr(self._av_pool, "_keys", [])) or 1)
        for _ in range(max_attempts):
            key = self._av_pool.acquire() if self._av_pool.has_keys() else self._av_key
            if not key:
                return None
            try:
                resp = self._session.get(
                    _AV_URL,
                    params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": key},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json() or {}
            except Exception as e:
                log.warning("[valuation] Alpha Vantage fetch failed for %s: %s", symbol, e)
                return None
            note = data.get("Note") or data.get("Information")
            if note:
                log.warning("[valuation] Alpha Vantage throttled/limited for %s: %s", symbol, str(note)[:120])
                if self._av_pool.has_keys():
                    self._av_pool.mark_throttled(key)
                    continue  # try next key
                return None
            break
        else:
            return None
        gq = data.get("Global Quote") or data.get("globalQuote") or {}
        price_str = gq.get("05. price") or gq.get("price")
        if not price_str:
            log.warning("[valuation] Alpha Vantage returned no price for %s (keys=%s)",
                        symbol, list(gq.keys()) if gq else list(data.keys()))
            return None
        try:
            price = float(price_str)
        except (TypeError, ValueError):
            log.warning("[valuation] Alpha Vantage unparseable price for %s: %r", symbol, price_str)
            return None
        if price <= 0:
            return None
        # AV's GLOBAL_QUOTE is regular-market last trade only — log so the user
        # knows extended-hours pricing is not in use even when the market is
        # pre/post-market.
        log.debug("[valuation] %s priced via Alpha Vantage GLOBAL_QUOTE = $%.4f "
                  "(regular-market last trade; extended-hours not available)",
                  symbol, price)
        return PricedQuote(symbol=symbol, price=price, source="alpha_vantage", extended_hours=False)

    def _fetch_alpaca_stock(self, symbol: str) -> PricedQuote | None:
        if self._alpaca is None:
            return None
        try:
            q = self._alpaca.get_stock_quote(symbol)
        except Exception as e:
            log.warning("[valuation] Alpaca stock quote fallback failed for %s: %s", symbol, e)
            return None
        # Prefer mid; fall back to ask/bid/last.
        bid = float(getattr(q, "bid_price", 0) or 0)
        ask = float(getattr(q, "ask_price", 0) or 0)
        if bid > 0 and ask > 0:
            price = (bid + ask) / 2
        elif ask > 0:
            price = ask
        elif bid > 0:
            price = bid
        else:
            return None
        log.info("[valuation] %s using Alpaca stock-quote fallback = $%.4f "
                 "(Alpha Vantage unavailable; regular-market last trade)", symbol, price)
        return PricedQuote(symbol=symbol, price=price, source="alpaca_stock_fallback", extended_hours=False)

# --------------------------------------------------------------------------- #
#  Valued wrappers — attribute-compatible with alpaca-py Position / Account   #
# --------------------------------------------------------------------------- #


@dataclass
class ValuedPosition:
    """Drop-in replacement for an alpaca-py Position with recomputed values.

    Preserves the attribute surface the rest of the codebase already uses:
    ``symbol``, ``qty``, ``side``, ``avg_entry_price``, ``market_value``,
    ``unrealized_pl``, ``unrealized_plpc``, ``current_price``, ``asset_class``.

    ``market_value``, ``unrealized_pl``, ``unrealized_plpc`` and
    ``current_price`` are recomputed from an independently fetched price;
    the rest come straight from Alpaca.
    """
    symbol: str
    qty: float
    side: Any                       # original Alpaca PositionSide or str
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pl: float
    unrealized_plpc: float
    asset_class: Any = None
    price_source: str = ""
    price_extended_hours: bool = False
    # Keep a reference to the raw Alpaca position so callers that need other
    # fields (e.g. ``cost_basis``) can still reach them.
    raw: Any = field(default=None, repr=False)


@dataclass
class ValuedAccount:
    """Drop-in replacement for an alpaca-py Account with recomputed equity.

    ``cash``, ``buying_power``, ``last_equity``, ``status``, etc. come from
    Alpaca. ``equity`` and ``portfolio_value`` are recomputed as
    ``cash + sum(signed position market_value)``.
    """
    cash: float
    equity: float
    portfolio_value: float
    buying_power: float
    last_equity: float
    status: Any = None
    raw: Any = field(default=None, repr=False)

    # Support `float(account.equity)` — alpaca-py returns strings for these
    # numeric fields, and the codebase wraps in float() defensively. We can
    # keep them as floats; float(float) is a no-op.


# --------------------------------------------------------------------------- #
#  Snapshot builder                                                            #
# --------------------------------------------------------------------------- #


def _side_is_long(raw_position) -> bool:
    return True


def value_position(raw_position, quote: PricedQuote | None) -> ValuedPosition:
    """Recompute market value and P/L for one Alpaca position."""
    sym = str(raw_position.symbol)
    qty = float(raw_position.qty)
    avg_entry = float(getattr(raw_position, "avg_entry_price", 0) or 0)
    is_long = _side_is_long(raw_position)

    if quote is None:
        # Fall back to avg_entry so we don't crash — but log loudly.
        log.warning("[valuation] No independent price for %s — falling back to avg_entry ($%.4f). "
                    "Position P/L will read as zero.", sym, avg_entry)
        current = avg_entry
        price_source = "fallback_avg_entry"
        extended = False
    else:
        current = quote.price
        price_source = quote.source
        extended = quote.extended_hours

    abs_qty = abs(qty)
    signed_market_value = abs_qty * current
    # P/L: (current - avg_entry) * qty * direction
    if avg_entry > 0:
        pnl_per_share = current - avg_entry
        unrealized_pl = pnl_per_share * abs_qty
        unrealized_plpc = pnl_per_share / avg_entry
    else:
        unrealized_pl = 0.0
        unrealized_plpc = 0.0

    return ValuedPosition(
        symbol=sym,
        qty=qty,
        side=getattr(raw_position, "side", "long"),
        avg_entry_price=avg_entry,
        current_price=current,
        market_value=signed_market_value,
        unrealized_pl=unrealized_pl,
        unrealized_plpc=unrealized_plpc,
        asset_class=getattr(raw_position, "asset_class", None),
        price_source=price_source,
        price_extended_hours=extended,
        raw=raw_position,
    )


def build_snapshot(alpaca_client, pricing: PricingService | None = None,
                   log_detail: bool = True) -> tuple[ValuedAccount, list[ValuedPosition]]:
    """Fetch cash + positions + independent prices and return corrected views.

    Returns ``(account, positions)`` where both are attribute-compatible with
    their Alpaca counterparts but with recomputed equity / market-value / P/L.
    """
    if pricing is None:
        pricing = PricingService(alpaca_client=alpaca_client)

    raw_account = alpaca_client.get_account_raw()
    raw_positions = list(alpaca_client.get_positions_raw())
    symbols = [str(p.symbol) for p in raw_positions]
    quotes = pricing.get_prices(symbols)

    valued: list[ValuedPosition] = []
    for rp in raw_positions:
        q = quotes.get(str(rp.symbol))
        valued.append(value_position(rp, q))

    cash = float(getattr(raw_account, "cash", 0) or 0)
    total_position_value = sum(p.market_value for p in valued)
    equity = cash + total_position_value

    account = ValuedAccount(
        cash=cash,
        equity=equity,
        portfolio_value=equity,
        buying_power=float(getattr(raw_account, "buying_power", 0) or 0),
        last_equity=float(getattr(raw_account, "last_equity", 0) or 0),
        status=getattr(raw_account, "status", None),
        raw=raw_account,
    )

    if log_detail:
        _log_snapshot(account, valued)

    return account, valued


def _log_snapshot(account: ValuedAccount, positions: list[ValuedPosition]) -> None:
    log.info("[valuation] --- independent account valuation ---")
    log.info("[valuation] cash=$%.2f | positions=%d | computed_equity=$%.2f",
             account.cash, len(positions), account.equity)
    for p in positions:
        log.info(
            "[valuation]   %s qty=%s avg_entry=$%.4f price=$%.4f (src=%s%s) "
            "mkt_val=$%+.2f unrealized_pl=$%+.2f (%+.2f%%)",
            p.symbol, p.qty, p.avg_entry_price, p.current_price,
            p.price_source, ",ext" if p.price_extended_hours else "",
            p.market_value, p.unrealized_pl, p.unrealized_plpc * 100,
        )
    log.info("[valuation] total_account_value=$%.2f (cash + sum(position_values))",
             account.equity)
