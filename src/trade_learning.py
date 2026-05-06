"""Post-exit learning metrics from actual broker fills.

This module intentionally reads Alpaca orders directly instead of consuming the
end-of-day report. Each filled sell is compared with the symbol price 30m, 60m,
and at the trading-day close so exits can be reviewed against what happened
after the bot acted.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.journal import log_trade

log = logging.getLogger(__name__)


def _state_path(cfg) -> Path:
    rel = cfg.get(
        "trade_learning", "state_file",
        default="data/state/exit_learning_pending.json",
    )
    return Path(__file__).resolve().parents[1] / rel


def _load_state(cfg) -> dict[str, Any]:
    path = _state_path(cfg)
    if not path.exists():
        return {"pending": {}, "completed_order_ids": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"pending": {}, "completed_order_ids": []}
    if not isinstance(data, dict):
        return {"pending": {}, "completed_order_ids": []}
    data.setdefault("pending", {})
    data.setdefault("completed_order_ids", [])
    return data


def _save_state(cfg, state: dict[str, Any]) -> None:
    path = _state_path(cfg)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    except OSError as exc:
        log.warning("trade-learning state save failed: %s", exc)


def _enum_text(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").lower().rsplit(".", 1)[-1]


def _as_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _float_attr(obj: Any, name: str, default: float = 0.0) -> float:
    raw = getattr(obj, name, None)
    if raw in (None, "") and isinstance(obj, dict):
        raw = obj.get(name)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _str_attr(obj: Any, name: str, default: str = "") -> str:
    raw = getattr(obj, name, None)
    if raw in (None, "") and isinstance(obj, dict):
        raw = obj.get(name)
    return str(raw or default)


def _order_dt(order: Any) -> datetime:
    for name in ("filled_at", "updated_at", "submitted_at", "created_at"):
        dt = _as_dt(getattr(order, name, None) if not isinstance(order, dict) else order.get(name))
        if dt is not None:
            return dt
    return datetime.now(timezone.utc)


def _slice_symbol(df, symbol: str):
    if df is None or getattr(df, "empty", True):
        return None
    try:
        if "symbol" in df.index.names:
            return df.xs(symbol, level="symbol")
        return df
    except Exception:
        return None


def _close_from_df(df) -> float | None:
    if df is None or getattr(df, "empty", True):
        return None
    try:
        close = df["close"].dropna()
        if close.empty:
            return None
        return float(close.iloc[-1])
    except Exception:
        return None


def _minute_price_at(client: Any, symbol: str, target: datetime) -> float | None:
    try:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
    except Exception as exc:
        log.debug("trade-learning minute import failed: %s", exc)
        return None
    start = target.astimezone(timezone.utc) - timedelta(minutes=10)
    end = target.astimezone(timezone.utc) + timedelta(minutes=10)
    try:
        req = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Minute,
            start=start,
            end=end,
            adjustment="split",
        )
        bars = client.stock_data.get_stock_bars(req).df
    except Exception as exc:
        log.debug("[%s] trade-learning minute bars failed: %s", symbol, exc)
        return None
    return _close_from_df(_slice_symbol(bars, symbol))


def _daily_close_price(client: Any, symbol: str, exit_time: datetime) -> float | None:
    try:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
    except Exception as exc:
        log.debug("trade-learning daily import failed: %s", exc)
        return None
    day = exit_time.astimezone(timezone.utc).date()
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    try:
        req = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            adjustment="split",
        )
        bars = client.stock_data.get_stock_bars(req).df
    except Exception as exc:
        log.debug("[%s] trade-learning daily bars failed: %s", symbol, exc)
        return None
    return _close_from_df(_slice_symbol(bars, symbol))


def _missed_pnl(qty: float, exit_price: float, later_price: float | None) -> float | None:
    if later_price is None:
        return None
    return round(float(qty) * (float(later_price) - float(exit_price)), 2)


def _sync_recent_exits(cfg, client, state: dict[str, Any], cash_proxy_symbol: str | None) -> bool:
    pending = state.setdefault("pending", {})
    completed = set(str(x) for x in state.setdefault("completed_order_ids", []))
    lookback_hours = float(cfg.get("trade_learning", "sync_lookback_hours", default=36) or 36)
    after = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    try:
        getter = getattr(client, "get_orders", None)
        if getter is not None:
            orders = getter(status="all", limit=500, after=after, side="sell")
        else:
            from alpaca.trading.requests import GetOrdersRequest
            orders = client.trading.get_orders(GetOrdersRequest(
                status="all", limit=500, after=after,
            ))
    except Exception as exc:
        log.debug("trade-learning order sync failed: %s", exc)
        return False
    changed = False
    proxy = str(cash_proxy_symbol or "").upper()
    for order in orders or []:
        order_id = _str_attr(order, "id")
        symbol = _str_attr(order, "symbol").upper()
        if not order_id or not symbol or "/" in symbol or symbol == proxy:
            continue
        if order_id in pending or order_id in completed:
            continue
        if _enum_text(getattr(order, "side", "")) != "sell":
            continue
        if _enum_text(getattr(order, "status", "")) != "filled":
            continue
        qty = _float_attr(order, "filled_qty")
        exit_price = _float_attr(order, "filled_avg_price")
        if qty <= 0 or exit_price <= 0:
            continue
        exit_time = _order_dt(order)
        pending[order_id] = {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "exit_price": exit_price,
            "exit_time": exit_time.isoformat(),
            "metrics": {},
        }
        changed = True
    return changed


def resolve_exit_learning_metrics(cfg, client, cash_proxy_symbol: str | None = None) -> dict[str, Any]:
    """Sync actual filled exits and resolve 30m/60m/close post-exit prices."""
    if not bool(cfg.get("trade_learning", "enabled", default=False)):
        return {"enabled": False}
    state = _load_state(cfg)
    changed = _sync_recent_exits(cfg, client, state, cash_proxy_symbol)
    now = datetime.now(timezone.utc)
    resolved: list[dict[str, Any]] = []
    pending = state.setdefault("pending", {})
    completed = list(state.setdefault("completed_order_ids", []))
    for order_id, row in list(pending.items()):
        exit_time = _as_dt(row.get("exit_time"))
        if exit_time is None:
            pending.pop(order_id, None)
            changed = True
            continue
        symbol = str(row.get("symbol") or "").upper()
        qty = float(row.get("qty") or 0)
        exit_price = float(row.get("exit_price") or 0)
        metrics = row.setdefault("metrics", {})
        metric_changed = False
        if "price_30m" not in metrics and now >= exit_time + timedelta(minutes=30):
            price = _minute_price_at(client, symbol, exit_time + timedelta(minutes=30))
            if price is not None:
                metrics["price_30m"] = price
                metrics["missed_pnl_30m"] = _missed_pnl(qty, exit_price, price)
                metric_changed = True
        if "price_60m" not in metrics and now >= exit_time + timedelta(minutes=60):
            price = _minute_price_at(client, symbol, exit_time + timedelta(minutes=60))
            if price is not None:
                metrics["price_60m"] = price
                metrics["missed_pnl_60m"] = _missed_pnl(qty, exit_price, price)
                metric_changed = True
        if "close_price" not in metrics and (
            now.date() > exit_time.date() or now >= exit_time + timedelta(hours=7)
        ):
            price = _daily_close_price(client, symbol, exit_time)
            if price is not None:
                metrics["close_price"] = price
                metrics["missed_pnl_close"] = _missed_pnl(qty, exit_price, price)
                metric_changed = True
        if metric_changed:
            changed = True
            payload = {
                "event": "exit_learning_metrics",
                "symbol": symbol,
                "order_id": order_id,
                "qty": qty,
                "exit_price": exit_price,
                "exit_time": row.get("exit_time"),
                **metrics,
            }
            log_trade(payload)
            resolved.append(payload)
        if all(k in metrics for k in ("price_30m", "price_60m", "close_price")):
            pending.pop(order_id, None)
            completed.append(order_id)
            changed = True
    state["completed_order_ids"] = completed[-1000:]
    if changed:
        _save_state(cfg, state)
    return {
        "enabled": True,
        "pending": len(pending),
        "resolved": resolved,
    }
