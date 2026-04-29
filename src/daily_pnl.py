"""Daily portfolio P&L vs yesterday's close + SPY benchmark.

Two responsibilities:

1. **Portfolio daily %.** Cache the first equity reading per trading day
   (NY-time date) as the baseline. Subsequent calls return
   ``(equity_now - baseline, pct, source)`` — independent of any
   external market-data API.
2. **SPY daily %.** Fetch via Twelve Data (primary) → yfinance →
   Alpha Vantage. Each provider's quota is managed by its own
   :class:`~src.api_keys.KeyPool` so no single provider becomes a
   blocker.

The portfolio P&L number is what the user sees as the "Daily" line in
Telegram messages. It does **not** depend on Alpha Vantage being up.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests

from src.api_keys import KeyPool

log = logging.getLogger(__name__)

_STATE_DIR = Path(__file__).resolve().parents[1] / "data" / "state"
_BASELINE_FILE = _STATE_DIR / "daily_baseline.json"


# --------------------------------------------------------------------------- #
#  Trading-day helpers                                                        #
# --------------------------------------------------------------------------- #


def _ny_date_str(now: Optional[datetime] = None) -> str:
    """Return today's date in NY (Eastern) as YYYY-MM-DD.

    The bot operates on US market hours; we anchor "today" to the NY date
    so the baseline rolls over at midnight ET, not UTC.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    # ET is UTC-5 (EST) or UTC-4 (EDT). Approximate with -5 — the only
    # consequence of being off by an hour at midnight is the baseline
    # rolling over at 00:00 ET ± 1h, which is hours before any scan runs.
    et = now.astimezone(timezone(timedelta(hours=-5)))
    return et.strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
#  Portfolio daily P&L                                                        #
# --------------------------------------------------------------------------- #


@dataclass
class DailyPnL:
    pnl_dollars: float
    pnl_pct: float
    baseline_equity: float
    baseline_date: str
    source: str          # "baseline_cache" | "first_read_today"


def get_or_set_baseline(equity_now: float, date_str: Optional[str] = None) -> tuple[float, str]:
    """Return (baseline_equity, baseline_date_str).

    On the first call of a NY trading day, writes ``equity_now`` as the
    baseline and returns ``(equity_now, today)``. On subsequent calls
    the same day, returns the cached value.
    """
    today = date_str or _ny_date_str()
    _STATE_DIR.mkdir(parents=True, exist_ok=True)

    data: dict = {}
    if _BASELINE_FILE.exists():
        try:
            data = json.loads(_BASELINE_FILE.read_text())
        except Exception as e:
            log.warning("[daily_pnl] baseline read failed: %s — re-creating", e)
            data = {}

    if data.get("date") == today and data.get("equity") is not None:
        return float(data["equity"]), today

    # New trading day — write a fresh baseline.
    data = {"date": today, "equity": float(equity_now), "set_at": time.time()}
    try:
        _BASELINE_FILE.write_text(json.dumps(data, indent=2))
        log.info("[daily_pnl] new baseline for %s: equity=$%.2f", today, equity_now)
    except Exception as e:
        log.warning("[daily_pnl] baseline write failed: %s", e)
    return float(equity_now), today


def get_daily_pnl(equity_now: float) -> DailyPnL:
    """Compute daily P&L vs the cached open-of-day equity baseline."""
    baseline, baseline_date = get_or_set_baseline(equity_now)
    pnl_dollars = equity_now - baseline
    pnl_pct = (pnl_dollars / baseline) if baseline > 0 else 0.0
    today = _ny_date_str()
    source = "baseline_cache" if baseline_date == today and abs(pnl_dollars) > 0.01 else "first_read_today"
    return DailyPnL(
        pnl_dollars=pnl_dollars,
        pnl_pct=pnl_pct,
        baseline_equity=baseline,
        baseline_date=baseline_date,
        source=source,
    )


# --------------------------------------------------------------------------- #
#  SPY daily % (Twelve Data → yfinance → Alpha Vantage)                       #
# --------------------------------------------------------------------------- #


_TWELVE_URL = "https://api.twelvedata.com/time_series"
_AV_URL = "https://www.alphavantage.co/query"


def _spy_via_twelve_data(pool: KeyPool) -> Optional[float]:
    key = pool.acquire()
    if not key:
        return None
    try:
        resp = requests.get(
            _TWELVE_URL,
            params={"symbol": "SPY", "interval": "1day", "outputsize": 2, "apikey": key},
            timeout=10,
        )
        data = resp.json() or {}
    except Exception as e:
        log.warning("[daily_pnl] Twelve Data fetch failed: %s", e)
        return None
    status = data.get("status")
    if status == "error":
        msg = (data.get("message") or "").lower()
        # 401/403/invalid-key style → mark dead. Quota → throttle.
        if "limit" in msg or "credit" in msg or "rate" in msg:
            pool.mark_throttled(key)
        elif "key" in msg or "auth" in msg or "invalid" in msg:
            pool.mark_dead(key)
        log.warning("[daily_pnl] Twelve Data error: %s", data.get("message"))
        return None
    values = data.get("values") or []
    if len(values) < 2:
        return None
    try:
        curr = float(values[0]["close"])
        prev = float(values[1]["close"])
        if prev <= 0:
            return None
        return (curr / prev) - 1
    except (KeyError, TypeError, ValueError) as e:
        log.warning("[daily_pnl] Twelve Data parse failed: %s", e)
        return None


def _spy_via_yfinance() -> Optional[float]:
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        return None
    try:
        hist = yf.Ticker("SPY").history(period="5d", interval="1d")
        if hist is None or len(hist) < 2:
            return None
        prev = float(hist["Close"].iloc[-2])
        curr = float(hist["Close"].iloc[-1])
        if prev <= 0:
            return None
        return (curr / prev) - 1
    except Exception as e:
        log.warning("[daily_pnl] yfinance SPY fetch failed: %s", e)
        return None


def _spy_via_alpha_vantage(pool: KeyPool) -> Optional[float]:
    key = pool.acquire()
    if not key:
        return None
    try:
        resp = requests.get(
            _AV_URL,
            params={"function": "TIME_SERIES_DAILY", "symbol": "SPY", "apikey": key},
            timeout=10,
        )
        data = resp.json() or {}
    except Exception as e:
        log.warning("[daily_pnl] Alpha Vantage SPY fetch failed: %s", e)
        return None
    note = data.get("Note") or data.get("Information")
    if note:
        pool.mark_throttled(key)
        log.warning("[daily_pnl] Alpha Vantage throttled SPY: %s", str(note)[:120])
        return None
    series = data.get("Time Series (Daily)") or {}
    if len(series) < 2:
        return None
    sorted_dates = sorted(series.keys(), reverse=True)
    try:
        curr = float(series[sorted_dates[0]]["4. close"])
        prev = float(series[sorted_dates[1]]["4. close"])
        if prev <= 0:
            return None
        return (curr / prev) - 1
    except (KeyError, TypeError, ValueError) as e:
        log.warning("[daily_pnl] Alpha Vantage SPY parse failed: %s", e)
        return None


def get_spy_daily_pct(
    twelve_pool: Optional[KeyPool] = None,
    av_pool: Optional[KeyPool] = None,
    alpaca_client=None,
) -> tuple[float, str]:
    """Return (spy_daily_pct, source).

    Provider order: Twelve Data → yfinance → Alpha Vantage → Alpaca bars
    (last-resort, only if ``alpaca_client`` is provided).
    """
    if twelve_pool is None:
        twelve_pool = KeyPool.from_env("twelve_data", "TWELVEDATA_API_KEYS")
    if av_pool is None:
        av_pool = KeyPool.from_env(
            "alpha_vantage", "ALPHA_VANTAGE_API_KEYS",
            singular_env="ALPHA_VANTAGE_API_KEY",
        )

    if twelve_pool.has_keys():
        v = _spy_via_twelve_data(twelve_pool)
        if v is not None:
            return v, "twelve_data"

    v = _spy_via_yfinance()
    if v is not None:
        return v, "yfinance"

    if av_pool.has_keys():
        v = _spy_via_alpha_vantage(av_pool)
        if v is not None:
            return v, "alpha_vantage"

    if alpaca_client is not None:
        try:
            bars = alpaca_client.get_stock_bars(["SPY"], lookback_days=10)
            spy = bars.xs("SPY", level="symbol") if "symbol" in bars.index.names else bars
            if len(spy) >= 2:
                prev = float(spy["close"].iloc[-2])
                curr = float(spy["close"].iloc[-1])
                if prev > 0:
                    return (curr / prev) - 1, "alpaca_fallback"
        except Exception as e:
            log.warning("[daily_pnl] Alpaca SPY fallback failed: %s", e)

    log.warning("[daily_pnl] All SPY providers exhausted; returning 0.0")
    return 0.0, "unavailable"
