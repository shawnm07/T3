"""Market-data layer for the trading bot.

Single entry point for price/bar/news/movers data in the discovery + scoring
path.

Per user instruction (see memory/data_source_preferences.md): Alpha Vantage
is the primary data source; ``tradingview-screener`` and ``yfinance`` are
fallbacks. Alpaca is NEVER used here for charts/bars/news. Alpaca is
retained only for positions, account, and order submission.

Endpoint coverage:
  - daily bars (TIME_SERIES_DAILY_ADJUSTED)
  - intraday bars (TIME_SERIES_INTRADAY)
  - latest quote (GLOBAL_QUOTE)
  - top movers / gainers / losers / most-active (TOP_GAINERS_LOSERS)
  - news + sentiment (NEWS_SENTIMENT)

Caching: in-memory + on-disk JSON under ``data/cache/av/<endpoint>/<key>.json``
with per-endpoint TTLs. Persistent within a trading day.

Rate limiting: per-minute rolling window + concurrency semaphore. On AV
"Note"/"Information" throttle responses or HTTP 429, falls through to the
configured fallback chain.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests

log = logging.getLogger(__name__)

_AV_URL = "https://www.alphavantage.co/query"

# Default TTLs (seconds). Overridable via config.
_DEFAULT_TTL = {
    "daily_bars": 4 * 3600,
    "intraday_bars": 5 * 60,
    "quote": 60,
    "top_movers": 5 * 60,
    "news_sentiment": 10 * 60,
}


# --------------------------------------------------------------------------- #
#  Rate limiting                                                              #
# --------------------------------------------------------------------------- #


class _RateLimiter:
    """Thread-safe per-minute rolling-window limiter + concurrency cap."""

    def __init__(self, per_minute: int, max_concurrency: int):
        self._per_minute = per_minute
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()
        self._sem = threading.Semaphore(max_concurrency)

    def acquire(self) -> None:
        """Block until a call slot is available (window + concurrency)."""
        self._sem.acquire()
        with self._lock:
            now = time.monotonic()
            # Drop calls older than 60s.
            while self._calls and (now - self._calls[0]) > 60.0:
                self._calls.popleft()
            if len(self._calls) >= self._per_minute:
                wait_until = self._calls[0] + 60.0
                sleep_for = max(0.0, wait_until - now)
            else:
                sleep_for = 0.0
            self._calls.append(now + sleep_for)
        if sleep_for > 0:
            log.info("[market_data] rate-limit wait %.2fs", sleep_for)
            time.sleep(sleep_for)

    def release(self) -> None:
        self._sem.release()


# --------------------------------------------------------------------------- #
#  Disk cache                                                                 #
# --------------------------------------------------------------------------- #


class _DiskCache:
    """Tiny JSON-on-disk + in-memory cache with per-key TTL.

    Cache values must be JSON-serializable. Bars are stored as dict-of-lists
    (open/high/low/close/volume) and rebuilt into a DataFrame on read.
    """

    def __init__(self, root: Path):
        self._root = Path(root)
        self._mem: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.warning("[market_data] cache dir %s unwritable: %s", self._root, e)

    def _path(self, namespace: str, key: str) -> Path:
        safe = key.replace("/", "_").replace(":", "_")
        return self._root / namespace / f"{safe}.json"

    def get(self, namespace: str, key: str, ttl: float) -> Any | None:
        full_key = f"{namespace}::{key}"
        now = time.time()
        with self._lock:
            cached = self._mem.get(full_key)
            if cached and (now - cached[0]) < ttl:
                return cached[1]
        # Disk fall-through.
        path = self._path(namespace, key)
        if not path.exists():
            return None
        try:
            mtime = path.stat().st_mtime
            if (now - mtime) >= ttl:
                return None
            with path.open("r", encoding="utf-8") as f:
                value = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            log.debug("[market_data] disk-cache read failed for %s: %s", full_key, e)
            return None
        with self._lock:
            self._mem[full_key] = (now, value)
        return value

    def set(self, namespace: str, key: str, value: Any) -> None:
        full_key = f"{namespace}::{key}"
        now = time.time()
        with self._lock:
            self._mem[full_key] = (now, value)
        path = self._path(namespace, key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(value, f)
            os.replace(tmp, path)
        except OSError as e:
            log.debug("[market_data] disk-cache write failed for %s: %s", full_key, e)


# --------------------------------------------------------------------------- #
#  DataFrame helpers                                                          #
# --------------------------------------------------------------------------- #


def _bars_records_from_df(df: pd.DataFrame) -> dict[str, list]:
    """Serialize an OHLCV DataFrame for JSON caching."""
    if df.empty:
        return {"index": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
    return {
        "index": [t.isoformat() for t in df.index],
        "open": df["open"].tolist(),
        "high": df["high"].tolist(),
        "low": df["low"].tolist(),
        "close": df["close"].tolist(),
        "volume": df["volume"].tolist(),
    }


def _df_from_bars_records(rec: dict[str, list]) -> pd.DataFrame:
    if not rec or not rec.get("index"):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame({
        "open": rec["open"],
        "high": rec["high"],
        "low": rec["low"],
        "close": rec["close"],
        "volume": rec["volume"],
    }, index=pd.to_datetime(rec["index"]))
    df.sort_index(inplace=True)
    return df


# --------------------------------------------------------------------------- #
#  MarketDataService                                                          #
# --------------------------------------------------------------------------- #


@dataclass
class TopMovers:
    gainers: list[dict[str, Any]]
    losers: list[dict[str, Any]]
    most_active: list[dict[str, Any]]
    last_updated: str = ""


class MarketDataService:
    """Alpha Vantage primary + TV-screener + yfinance fallbacks.

    Initialize once per process; share across orchestrator components. All
    methods are thread-safe.
    """

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: str | Path = "data/cache/av",
        per_minute: int = 75,
        max_concurrency: int = 5,
        ttl_overrides: dict[str, float] | None = None,
        fallback_to_tv_screener: bool = True,
        fallback_to_yfinance: bool = True,
        request_timeout: float = 15.0,
    ):
        self._api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY", "")
        if not self._api_key:
            log.warning("[market_data] ALPHA_VANTAGE_API_KEY is empty — AV calls will fail")
        self._cache = _DiskCache(Path(cache_dir))
        self._limiter = _RateLimiter(per_minute=per_minute, max_concurrency=max_concurrency)
        self._ttl = {**_DEFAULT_TTL, **(ttl_overrides or {})}
        self._tv_enabled = fallback_to_tv_screener
        self._yf_enabled = fallback_to_yfinance
        self._timeout = request_timeout
        self._session = requests.Session()

    # ---------- public ----------

    def get_daily_bars(self, symbol: str, days: int = 252) -> pd.DataFrame:
        """Adjusted daily bars. Falls back to yfinance on AV failure."""
        cache_key = f"{symbol}_{days}"
        cached = self._cache.get("daily_bars", cache_key, self._ttl["daily_bars"])
        if cached is not None:
            return _df_from_bars_records(cached)

        df = self._av_daily_bars(symbol, days)
        if df is None or df.empty:
            if self._yf_enabled:
                df = self._yf_daily_bars(symbol, days)
        if df is None:
            df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        self._cache.set("daily_bars", cache_key, _bars_records_from_df(df))
        return df

    def get_avg_dollar_volume(self, symbol: str, days: int = 20) -> float | None:
        """Phase 6 (2026-05-07): 20-day average dollar volume for liquidity gating.

        Returns the mean of (close * volume) over the last ``days`` daily bars,
        or None when bars are unavailable. Reuses ``get_daily_bars`` so the
        existing daily-bars cache is shared (no separate cache needed).
        """
        try:
            df = self.get_daily_bars(symbol, days=max(days * 2, 40))
        except Exception:
            return None
        if df is None or df.empty:
            return None
        try:
            tail = df.tail(days)
            if tail.empty:
                return None
            dv = (tail["close"].astype(float) * tail["volume"].astype(float)).mean()
            return float(dv)
        except Exception:
            return None

    def get_intraday_bars(
        self, symbol: str, interval: str = "5min", outputsize: str = "compact"
    ) -> pd.DataFrame:
        """Intraday bars. Returns up to ~100 bars (compact) or full month (full)."""
        cache_key = f"{symbol}_{interval}_{outputsize}"
        cached = self._cache.get("intraday_bars", cache_key, self._ttl["intraday_bars"])
        if cached is not None:
            return _df_from_bars_records(cached)
        df = self._av_intraday_bars(symbol, interval, outputsize)
        if df is None:
            df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        self._cache.set("intraday_bars", cache_key, _bars_records_from_df(df))
        return df

    def get_quote(self, symbol: str) -> dict[str, Any] | None:
        """Latest GLOBAL_QUOTE — last trade + change pct + volume."""
        cached = self._cache.get("quote", symbol, self._ttl["quote"])
        if cached is not None:
            return cached
        data = self._av_call("GLOBAL_QUOTE", {"symbol": symbol})
        if not data:
            return None
        gq = data.get("Global Quote") or {}
        if not gq:
            return None
        try:
            quote = {
                "symbol": symbol,
                "price": float(gq.get("05. price", 0) or 0),
                "open": float(gq.get("02. open", 0) or 0),
                "high": float(gq.get("03. high", 0) or 0),
                "low": float(gq.get("04. low", 0) or 0),
                "volume": int(float(gq.get("06. volume", 0) or 0)),
                "prev_close": float(gq.get("08. previous close", 0) or 0),
                "change_pct": float(str(gq.get("10. change percent", "0%")).rstrip("%") or 0) / 100.0,
                "latest_day": gq.get("07. latest trading day", ""),
            }
        except (TypeError, ValueError) as e:
            log.warning("[market_data] AV quote parse failed for %s: %s", symbol, e)
            return None
        if quote["price"] <= 0:
            return None
        self._cache.set("quote", symbol, quote)
        return quote

    def get_top_movers(self) -> TopMovers:
        """Single AV call returns gainers + losers + most-active."""
        cached = self._cache.get("top_movers", "us", self._ttl["top_movers"])
        if cached is not None:
            return TopMovers(**cached)
        data = self._av_call("TOP_GAINERS_LOSERS", {})
        if not data or "top_gainers" not in data:
            if self._tv_enabled:
                tv = self._tv_screener_movers()
                if tv:
                    self._cache.set("top_movers", "us", tv)
                    return TopMovers(**tv)
            return TopMovers(gainers=[], losers=[], most_active=[])
        result = {
            "gainers": _av_movers_clean(data.get("top_gainers") or []),
            "losers": _av_movers_clean(data.get("top_losers") or []),
            "most_active": _av_movers_clean(data.get("most_actively_traded") or []),
            "last_updated": data.get("last_updated", ""),
        }
        self._cache.set("top_movers", "us", result)
        return TopMovers(**result)

    def get_news_sentiment(
        self,
        tickers: Iterable[str] | None = None,
        topics: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """News + sentiment feed. Empty tickers = topic-wide scan."""
        tickers_str = ",".join(sorted(tickers)) if tickers else ""
        cache_key = f"{tickers_str or 'all'}__{topics or 'all'}__{limit}"
        cached = self._cache.get("news_sentiment", cache_key, self._ttl["news_sentiment"])
        if cached is not None:
            return cached
        params: dict[str, Any] = {"limit": limit, "sort": "LATEST"}
        if tickers_str:
            params["tickers"] = tickers_str
        if topics:
            params["topics"] = topics
        data = self._av_call("NEWS_SENTIMENT", params)
        feed = data.get("feed", []) if data else []
        self._cache.set("news_sentiment", cache_key, feed)
        return feed

    # ---------- AV core ----------

    def _av_call(self, function: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Single AV HTTP call with rate-limit + throttle handling."""
        if not self._api_key:
            return None
        full_params = {"function": function, "apikey": self._api_key, **params}
        self._limiter.acquire()
        try:
            resp = self._session.get(_AV_URL, params=full_params, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json() or {}
        except Exception as e:
            log.warning("[market_data] AV %s failed: %s", function, e)
            return None
        finally:
            self._limiter.release()
        note = data.get("Note") or data.get("Information")
        if note and "Thank you" in str(note):
            log.warning("[market_data] AV throttled on %s: %s", function, str(note)[:140])
            return None
        if "Error Message" in data:
            log.warning("[market_data] AV error on %s: %s", function, data["Error Message"])
            return None
        return data

    def _av_daily_bars(self, symbol: str, days: int) -> pd.DataFrame | None:
        outputsize = "full" if days > 100 else "compact"
        data = self._av_call(
            "TIME_SERIES_DAILY_ADJUSTED", {"symbol": symbol, "outputsize": outputsize}
        )
        if not data:
            return None
        series = data.get("Time Series (Daily)") or {}
        if not series:
            return None
        rows: list[tuple[str, dict]] = sorted(series.items())  # ascending by date
        if not rows:
            return None
        try:
            df = pd.DataFrame({
                "open": [float(r[1].get("1. open", 0) or 0) for r in rows],
                "high": [float(r[1].get("2. high", 0) or 0) for r in rows],
                "low": [float(r[1].get("3. low", 0) or 0) for r in rows],
                "close": [float(r[1].get("4. close", 0) or 0) for r in rows],
                "volume": [int(float(r[1].get("6. volume", 0) or 0)) for r in rows],
            }, index=pd.to_datetime([r[0] for r in rows]))
        except (TypeError, ValueError) as e:
            log.warning("[market_data] AV daily-bars parse failed for %s: %s", symbol, e)
            return None
        if days and len(df) > days:
            df = df.tail(days)
        return df

    def _av_intraday_bars(
        self, symbol: str, interval: str, outputsize: str
    ) -> pd.DataFrame | None:
        data = self._av_call(
            "TIME_SERIES_INTRADAY",
            {"symbol": symbol, "interval": interval, "outputsize": outputsize, "extended_hours": "false"},
        )
        return _parse_av_intraday(data) if data else None

    # ---------- fallbacks ----------

    def _yf_daily_bars(self, symbol: str, days: int) -> pd.DataFrame | None:
        if not self._yf_enabled:
            return None
        try:
            import yfinance as yf
        except ImportError:
            return None
        period_days = max(days + 5, 60)
        try:
            yf_sym = symbol.replace(".", "-")  # BRK.B -> BRK-B
            data = yf.download(yf_sym, period=f"{period_days}d", interval="1d",
                               progress=False, auto_adjust=False)
        except Exception as e:
            log.warning("[market_data] yfinance fallback failed for %s: %s", symbol, e)
            return None
        if data is None or data.empty:
            return None
        # yfinance returns multi-index columns when given a single ticker in some
        # versions; flatten to lowercase names.
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume",
        })
        keep = [c for c in ("open", "high", "low", "close", "volume") if c in data.columns]
        data = data[keep].copy()
        data.index = pd.to_datetime(data.index)
        return data.tail(days) if days else data

    def _tv_screener_movers(self) -> dict[str, Any] | None:
        """TV-screener fallback for top movers when AV is throttled."""
        if not self._tv_enabled:
            return None
        try:
            from tradingview_screener import Query, Column
        except ImportError:
            return None
        try:
            base = (
                Query()
                .select("name", "close", "change", "volume", "market_cap_basic", "sector")
                .where(
                    Column("type").isin(["stock"]),
                    Column("exchange").isin(["NASDAQ", "NYSE", "AMEX"]),
                    Column("close") > 5,
                )
            )
            gainers = (
                base.copy()
                .order_by("change", ascending=False)
                .limit(20)
                .get_scanner_data()
            )
            losers = (
                base.copy()
                .order_by("change", ascending=True)
                .limit(20)
                .get_scanner_data()
            )
            most_active = (
                base.copy()
                .order_by("volume", ascending=False)
                .limit(20)
                .get_scanner_data()
            )
        except Exception as e:
            log.warning("[market_data] TV-screener movers fallback failed: %s", e)
            return None
        return {
            "gainers": _tv_rows_to_movers(gainers),
            "losers": _tv_rows_to_movers(losers),
            "most_active": _tv_rows_to_movers(most_active),
            "last_updated": "",
        }


# --------------------------------------------------------------------------- #
#  Module-level singleton                                                     #
# --------------------------------------------------------------------------- #


_DEFAULT_INSTANCE: MarketDataService | None = None
_DEFAULT_LOCK = threading.Lock()


def get_market_data(cfg=None) -> MarketDataService:
    """Return a shared MarketDataService configured from ``cfg``.

    Accepts a Config object (with ``.get(*keys, default=...)``) or None.
    Caches the instance on the module so callers don't re-init on every scan.
    """
    global _DEFAULT_INSTANCE
    with _DEFAULT_LOCK:
        if _DEFAULT_INSTANCE is not None:
            return _DEFAULT_INSTANCE
        api_key_env = "ALPHA_VANTAGE_API_KEY"
        cache_dir = "data/cache/av"
        per_minute = 75
        max_conc = 5
        tv = True
        yfb = True
        if cfg is not None and hasattr(cfg, "get"):
            api_key_env = cfg.get("data", "alpha_vantage_api_key_env", default=api_key_env)
            cache_dir = cfg.get("data", "cache_dir", default=cache_dir)
            per_minute = int(cfg.get("data", "alpha_vantage_rate_limit_per_min", default=per_minute) or per_minute)
            max_conc = int(cfg.get("data", "alpha_vantage_max_concurrency", default=max_conc) or max_conc)
            tv = bool(cfg.get("data", "fallback_to_tv_screener", default=tv))
            yfb = bool(cfg.get("data", "fallback_to_yfinance", default=yfb))
        _DEFAULT_INSTANCE = MarketDataService(
            api_key=os.getenv(api_key_env, ""),
            cache_dir=cache_dir,
            per_minute=per_minute,
            max_concurrency=max_conc,
            fallback_to_tv_screener=tv,
            fallback_to_yfinance=yfb,
        )
        return _DEFAULT_INSTANCE


# --------------------------------------------------------------------------- #
#  Helpers                                                                    #
# --------------------------------------------------------------------------- #


def _av_movers_clean(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows or []:
        try:
            out.append({
                "symbol": str(r.get("ticker", "")).upper(),
                "price": float(r.get("price", 0) or 0),
                "change_pct": float(str(r.get("change_percentage", "0%")).rstrip("%") or 0) / 100.0,
                "volume": int(float(r.get("volume", 0) or 0)),
            })
        except (TypeError, ValueError):
            continue
    return [r for r in out if r["symbol"]]


def _tv_rows_to_movers(scan_result) -> list[dict[str, Any]]:
    """tradingview-screener returns (count, DataFrame). Extract rows."""
    if scan_result is None:
        return []
    try:
        _count, df = scan_result
    except (TypeError, ValueError):
        df = scan_result
    if df is None or len(df) == 0:
        return []
    out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        try:
            out.append({
                "symbol": str(row.get("name", "") or row.get("ticker", "")).upper(),
                "price": float(row.get("close", 0) or 0),
                "change_pct": float(row.get("change", 0) or 0) / 100.0,
                "volume": int(float(row.get("volume", 0) or 0)),
                "sector": row.get("sector", "") or "",
                "market_cap_usd": float(row.get("market_cap_basic", 0) or 0),
            })
        except (TypeError, ValueError):
            continue
    return [r for r in out if r["symbol"]]


def _parse_av_intraday(data: dict[str, Any]) -> pd.DataFrame | None:
    """AV intraday returns 'Time Series (5min)' (or similar) — find the right key."""
    series_key = next((k for k in data.keys() if k.startswith("Time Series")), None)
    if not series_key:
        return None
    series = data.get(series_key) or {}
    if not series:
        return None
    rows: list[tuple[str, dict]] = sorted(series.items())
    try:
        df = pd.DataFrame({
            "open": [float(r[1].get("1. open", 0) or 0) for r in rows],
            "high": [float(r[1].get("2. high", 0) or 0) for r in rows],
            "low": [float(r[1].get("3. low", 0) or 0) for r in rows],
            "close": [float(r[1].get("4. close", 0) or 0) for r in rows],
            "volume": [int(float(r[1].get("5. volume", 0) or 0)) for r in rows],
        }, index=pd.to_datetime([r[0] for r in rows]))
    except (TypeError, ValueError) as e:
        log.warning("[market_data] AV intraday parse failed: %s", e)
        return None
    return df

