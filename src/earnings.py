"""Earnings calendar lookups with a disk cache.

Fetches next earnings date via yfinance and caches per-symbol on disk so we
don't hammer the network on every scan. Cache entry TTL is configurable
(default 24h). Failures degrade gracefully to None — the bot should never
block on an earnings lookup.
"""
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    yf = None

log = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "state"
CACHE_FILE = CACHE_DIR / "earnings_cache.json"


@dataclass(frozen=True)
class EarningsInfo:
    symbol: str
    next_date: str | None          # ISO yyyy-mm-dd
    days_until: int | None         # calendar days, negative = past

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "next_earnings_date": self.next_date,
            "days_until_earnings": self.days_until,
        }


def _load_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except OSError as e:
        log.warning("earnings cache save failed: %s", e)


def _extract_next_date(ticker) -> str | None:
    """Pull the next upcoming earnings date from a yfinance Ticker.

    Prefers `earnings_dates` (future rows) and falls back to `calendar`.
    Returns ISO yyyy-mm-dd or None.
    """
    today = date.today()

    try:
        ed = ticker.earnings_dates
        if ed is not None and not ed.empty:
            idx = ed.index
            future = [d for d in idx if d.date() >= today]
            if future:
                return min(future).date().isoformat()
    except Exception:
        pass

    try:
        cal = ticker.calendar
        if cal is not None:
            if hasattr(cal, "get"):
                val = cal.get("Earnings Date") or cal.get("earnings_date")
                if isinstance(val, list) and val:
                    d = val[0]
                    if hasattr(d, "isoformat"):
                        return d.isoformat() if d >= today else None
                elif hasattr(val, "isoformat"):
                    return val.isoformat() if val >= today else None
            elif hasattr(cal, "loc"):
                row = cal.loc["Earnings Date"] if "Earnings Date" in cal.index else None
                if row is not None:
                    d = row.iloc[0] if hasattr(row, "iloc") else row
                    if hasattr(d, "date"):
                        d = d.date()
                    if hasattr(d, "isoformat") and d >= today:
                        return d.isoformat()
    except Exception:
        pass

    return None


def fetch_earnings(symbol: str, ttl_hours: float = 24) -> EarningsInfo:
    """Return EarningsInfo for symbol, using disk cache. Never raises."""
    if not symbol or "/" in symbol:  # crypto never reports earnings
        return EarningsInfo(symbol=symbol, next_date=None, days_until=None)

    cache = _load_cache()
    entry = cache.get(symbol)
    now = time.time()
    if entry and (now - entry.get("fetched_at", 0)) < ttl_hours * 3600:
        return _build_info(symbol, entry.get("next_date"))

    next_date: str | None = None
    if yf is not None:
        try:
            t = yf.Ticker(symbol.replace(".", "-"))
            next_date = _extract_next_date(t)
        except Exception as e:
            log.debug("yfinance earnings lookup for %s failed: %s", symbol, e)

    cache[symbol] = {"next_date": next_date, "fetched_at": now}
    _save_cache(cache)
    return _build_info(symbol, next_date)


def _build_info(symbol: str, next_date: str | None) -> EarningsInfo:
    if not next_date:
        return EarningsInfo(symbol=symbol, next_date=None, days_until=None)
    try:
        d = datetime.fromisoformat(next_date).date()
    except ValueError:
        return EarningsInfo(symbol=symbol, next_date=None, days_until=None)
    delta = (d - date.today()).days
    return EarningsInfo(symbol=symbol, next_date=next_date, days_until=delta)


def batch_earnings(symbols: list[str], ttl_hours: float = 24) -> dict[str, EarningsInfo]:
    return {s: fetch_earnings(s, ttl_hours=ttl_hours) for s in symbols}


def within_window(info: EarningsInfo, days: int) -> bool:
    """True if earnings is within `days` calendar days in the future (inclusive)."""
    if info.days_until is None:
        return False
    return 0 <= info.days_until <= days
