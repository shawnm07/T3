"""Scheduled-scan portfolio/SPY history.

This module writes one append-only data point per automatic intraday scan so
the bot's account value can be charted against SPY later. Alpaca is used only
for cash and share quantities supplied by the caller; every market price in the
saved point must come from Twelve Data.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # Python 3.8 compatibility in the local test runner.
    from dateutil import tz

    class ZoneInfoNotFoundError(Exception):
        pass

    def ZoneInfo(name: str):
        zone = tz.gettz(name)
        if zone is None:
            raise ZoneInfoNotFoundError(name)
        return zone

import requests

from src.api_keys import KeyPool

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY_PATH = ROOT / "data" / "performance" / "portfolio_vs_spy.json"
TWELVE_PRICE_URL = "https://api.twelvedata.com/price"


@dataclass(frozen=True)
class PriceResult:
    symbol: str
    price: float | None
    source: str = "twelve_data"
    error: str | None = None


class TwelveDataPriceClient:
    """Small Twelve Data price client with shared KeyPool semantics."""

    def __init__(
        self,
        pool: KeyPool | None = None,
        session: requests.Session | None = None,
        timeout: float = 10.0,
    ):
        self._pool = pool or KeyPool.from_env(
            "twelve_data",
            "TWELVEDATA_API_KEYS",
            singular_env="TWELVEDATA_API_KEY",
        )
        self._session = session or requests.Session()
        self._timeout = timeout

    def get_price(self, symbol: str) -> PriceResult:
        sym = _clean_symbol(symbol)
        if not sym:
            return PriceResult(symbol=sym, price=None, error="empty_symbol")
        if not self._pool.has_keys():
            return PriceResult(symbol=sym, price=None, error="no_healthy_twelve_data_key")

        max_attempts = max(1, len(getattr(self._pool, "_keys", [])) or 1)
        last_error = "no_healthy_twelve_data_key"
        for _ in range(max_attempts):
            key = self._pool.acquire()
            if not key:
                break
            try:
                resp = self._session.get(
                    TWELVE_PRICE_URL,
                    params={"symbol": sym, "apikey": key},
                    timeout=self._timeout,
                )
                data = resp.json() or {}
            except Exception as e:
                msg = f"request_failed:{type(e).__name__}"
                log.warning("[performance_history] Twelve Data price failed for %s: %s", sym, e)
                return PriceResult(symbol=sym, price=None, error=msg)

            if data.get("status") == "error":
                msg = str(data.get("message") or data.get("code") or "twelve_data_error")
                msg_l = msg.lower()
                last_error = msg
                if any(token in msg_l for token in ("limit", "credit", "rate")):
                    self._pool.mark_throttled(key)
                    continue
                if any(token in msg_l for token in ("key", "auth", "invalid")):
                    self._pool.mark_dead(key)
                    continue
                log.warning("[performance_history] Twelve Data error for %s: %s", sym, msg[:120])
                return PriceResult(symbol=sym, price=None, error=msg)

            try:
                price = float(data.get("price", 0) or 0)
            except (TypeError, ValueError):
                return PriceResult(symbol=sym, price=None, error="unparseable_price")
            if price <= 0:
                return PriceResult(symbol=sym, price=None, error="missing_price")
            return PriceResult(symbol=sym, price=price)

        return PriceResult(symbol=sym, price=None, error=last_error)


def should_record_scan_datapoint(
    cfg,
    *,
    scheduled_run: bool,
    dry_run: bool,
    force: bool,
    started_at: datetime | None = None,
) -> tuple[bool, str]:
    """Return whether this scan should append a performance data point.

    A run must be explicitly marked as scheduler-owned and must have started
    near one of the configured intraday scan times. The decision uses the scan
    start time, not finish time, because AI scans commonly complete 5-10
    minutes after the scheduled trigger.
    """
    if not bool(_cfg_get(cfg, "performance_history", "enabled", default=True)):
        return False, "performance_history_disabled"
    if dry_run:
        return False, "dry_run"
    if force:
        return False, "force_run"
    if not scheduled_run:
        return False, "manual_run"

    now_utc = _as_aware_utc(started_at or datetime.now(timezone.utc))
    tz_name = str(_cfg_get(cfg, "scheduling", "timezone", default="America/New_York"))
    try:
        local = now_utc.astimezone(ZoneInfo(tz_name))
    except ZoneInfoNotFoundError:
        local = now_utc.astimezone(ZoneInfo("America/New_York"))

    if local.weekday() >= 5:
        return False, "outside_weekday_schedule"

    intraday_times = _cfg_get(cfg, "scheduling", "intraday_times", default=[]) or []
    before_minutes = float(
        _cfg_get(cfg, "performance_history", "schedule_start_grace_minutes", default=2)
    )
    after_minutes = float(
        _cfg_get(cfg, "performance_history", "schedule_finish_grace_minutes", default=20)
    )

    for time_text in intraday_times:
        parsed = _parse_hhmm(str(time_text))
        if parsed is None:
            continue
        hour, minute = parsed
        scheduled_at = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        delta_minutes = (local - scheduled_at).total_seconds() / 60.0
        if -before_minutes <= delta_minutes <= after_minutes:
            return True, f"scheduled_window:{time_text}"

    return False, "outside_intraday_schedule"


def build_scan_datapoint(
    cfg,
    *,
    account: Any,
    positions: Iterable[Any],
    dry_run: bool,
    scheduled_run: bool,
    scan_started_at: datetime | None = None,
    recorded_at: datetime | None = None,
    price_client: Any | None = None,
) -> dict[str, Any]:
    """Build a chart-friendly point using Twelve Data prices only."""
    started = _as_aware_utc(scan_started_at or datetime.now(timezone.utc))
    recorded = _as_aware_utc(recorded_at or datetime.now(timezone.utc))
    benchmark = _clean_symbol(_cfg_get(cfg, "performance_history", "benchmark", default=None)
                              or _cfg_get(cfg, "benchmark", default="SPY"))
    price_client = price_client or TwelveDataPriceClient()

    cash = _safe_float(getattr(account, "cash", account if isinstance(account, (int, float)) else 0.0))
    position_list = list(positions or [])
    symbols = [_clean_symbol(getattr(p, "symbol", "")) for p in position_list]
    symbols = [s for s in symbols if s and "/" not in s]
    lookup_symbols = list(dict.fromkeys([benchmark] + symbols))

    prices: dict[str, PriceResult] = {}
    for sym in lookup_symbols:
        prices[sym] = price_client.get_price(sym)

    position_rows: list[dict[str, Any]] = []
    missing_symbols: list[str] = []
    errors: list[dict[str, str]] = []
    priced_positions_value = 0.0
    portfolio_complete = True

    for p in position_list:
        sym = _clean_symbol(getattr(p, "symbol", ""))
        if not sym or "/" in sym:
            portfolio_complete = False
            missing_symbols.append(sym or "unknown")
            errors.append({"symbol": sym or "unknown", "error": "unsupported_symbol"})
            continue
        qty = _safe_float(getattr(p, "qty", 0.0))
        side = _side_str(getattr(p, "side", "long"))
        result = prices.get(sym) or PriceResult(symbol=sym, price=None, error="price_not_fetched")
        row = {
            "symbol": sym,
            "side": side,
            "qty": qty,
            "price": _round(result.price, 4) if result.price is not None else None,
            "price_source": result.source if result.price is not None else None,
            "market_value": None,
        }
        if result.price is None:
            portfolio_complete = False
            missing_symbols.append(sym)
            errors.append({"symbol": sym, "error": result.error or "missing_price"})
        else:
            market_value = _position_market_value(qty=qty, price=result.price, side=side)
            priced_positions_value += market_value
            row["market_value"] = _round(market_value, 2)
        position_rows.append(row)

    spy_result = prices.get(benchmark) or PriceResult(symbol=benchmark, price=None, error="price_not_fetched")
    benchmark_complete = spy_result.price is not None
    if not benchmark_complete:
        missing_symbols.append(benchmark)
        errors.append({"symbol": benchmark, "error": spy_result.error or "missing_price"})

    portfolio_value = cash + priced_positions_value if portfolio_complete else None
    return {
        "timestamp_utc": _iso_z(recorded),
        "timestamp_et": _iso_local(recorded, "America/New_York"),
        "scan_started_at_utc": _iso_z(started),
        "scan_type": "intraday",
        "scheduled_run": bool(scheduled_run),
        "dry_run": bool(dry_run),
        "pricing_source": "twelve_data",
        "complete": bool(portfolio_complete and benchmark_complete),
        "portfolio_complete": bool(portfolio_complete),
        "benchmark_complete": bool(benchmark_complete),
        "benchmark_symbol": benchmark,
        "spy_price": _round(spy_result.price, 4) if spy_result.price is not None else None,
        "cash": _round(cash, 2),
        "positions_value": _round(priced_positions_value, 2) if portfolio_complete else None,
        "priced_positions_value": _round(priced_positions_value, 2),
        "portfolio_value": _round(portfolio_value, 2) if portfolio_value is not None else None,
        "positions": position_rows,
        "missing_symbols": sorted(set(missing_symbols)),
        "errors": errors,
    }


def record_scan_datapoint(
    cfg,
    *,
    account: Any,
    positions: Iterable[Any],
    dry_run: bool,
    scheduled_run: bool,
    scan_started_at: datetime | None = None,
    price_client: Any | None = None,
    path: Path | str | None = None,
) -> tuple[dict[str, Any], Path]:
    """Build and append a scheduled-scan data point."""
    point = build_scan_datapoint(
        cfg,
        account=account,
        positions=positions,
        dry_run=dry_run,
        scheduled_run=scheduled_run,
        scan_started_at=scan_started_at,
        price_client=price_client,
    )
    history_path = Path(path) if path is not None else _history_path(cfg)
    _append_point(history_path, point)
    return point, history_path


def _append_point(path: Path, point: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    else:
        existing = {}

    if isinstance(existing, list):
        data = _new_history_document()
        data["points"] = existing
    elif isinstance(existing, dict):
        data = {**_new_history_document(), **existing}
        if not isinstance(data.get("points"), list):
            data["points"] = []
    else:
        data = _new_history_document()

    data["updated_at_utc"] = point["timestamp_utc"]
    data["points"].append(point)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _new_history_document() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "description": (
            "Scheduled intraday scan history. Chart points[].timestamp_utc, "
            "points[].portfolio_value, and points[].spy_price. Market prices "
            "are Twelve Data only; Alpaca is only used upstream for cash and quantities."
        ),
        "chart_fields": ["timestamp_utc", "portfolio_value", "spy_price"],
        "points": [],
    }


def _history_path(cfg) -> Path:
    raw = _cfg_get(
        cfg,
        "performance_history",
        "path",
        default="data/performance/portfolio_vs_spy.json",
    )
    path = Path(str(raw))
    if not path.is_absolute():
        path = ROOT / path
    return path


def _cfg_get(cfg, *keys: str, default: Any = None) -> Any:
    getter = getattr(cfg, "get", None)
    if callable(getter):
        return getter(*keys, default=default)
    node = getattr(cfg, "raw", cfg)
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def _clean_symbol(symbol: Any) -> str:
    return str(symbol or "").strip().upper()


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _round(value: float | None, places: int) -> float | None:
    if value is None:
        return None
    return round(float(value), places)


def _side_str(side: Any) -> str:
    value = getattr(side, "value", side)
    text = str(value or "long").split(".")[-1].lower()
    return "short" if text == "short" else "long"


def _position_market_value(*, qty: float, price: float, side: str) -> float:
    value = abs(qty) * price
    return -value if side == "short" else value


def _as_aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso_z(dt: datetime) -> str:
    return _as_aware_utc(dt).isoformat().replace("+00:00", "Z")


def _iso_local(dt: datetime, tz_name: str) -> str:
    return _as_aware_utc(dt).astimezone(ZoneInfo(tz_name)).isoformat()


def _parse_hhmm(value: str) -> tuple[int, int] | None:
    try:
        hour_text, minute_text = value.strip().split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute
