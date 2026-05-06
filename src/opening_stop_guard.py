"""Opening-stop guard.

Protective stop-market orders can get picked off in the opening auction/noise.
The guard cancels live sell stops before the open and re-arms them after the
configured delay, closing instead when the position has already crossed a
catastrophic gap threshold.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def _state_path(cfg) -> Path:
    rel = cfg.get(
        "opening_stop_guard", "state_file",
        default="data/state/opening_stop_guard.json",
    )
    return Path(__file__).resolve().parents[1] / rel


def _load_state(cfg) -> dict[str, Any]:
    path = _state_path(cfg)
    if not path.exists():
        return {"orders": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"orders": []}
    if not isinstance(data, dict):
        return {"orders": []}
    data.setdefault("orders", [])
    return data


def _save_state(cfg, state: dict[str, Any]) -> None:
    path = _state_path(cfg)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    except OSError as exc:
        log.warning("opening-stop state save failed: %s", exc)


def _enum_text(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").lower().rsplit(".", 1)[-1]


def _snapshot(order: Any) -> dict[str, Any]:
    return {
        "id": str(getattr(order, "id", "") or ""),
        "symbol": str(getattr(order, "symbol", "") or "").upper(),
        "side": _enum_text(getattr(order, "side", "")),
        "type": _enum_text(getattr(order, "type", "")),
        "time_in_force": _enum_text(getattr(order, "time_in_force", "")),
        "qty": float(getattr(order, "qty", 0) or 0),
        "stop_price": (
            float(getattr(order, "stop_price", 0) or 0)
            if getattr(order, "stop_price", None) not in (None, "")
            else None
        ),
        "status": _enum_text(getattr(order, "status", "")),
    }


def _is_protective_stop(order: Any, held_symbols: set[str]) -> bool:
    snap = _snapshot(order)
    guards_live_position = (not held_symbols) or snap["symbol"] in held_symbols
    return (
        guards_live_position
        and snap["side"] == "sell"
        and snap["type"] in {"stop", "stop_limit", "trailing_stop"}
        and snap["qty"] > 0
        and snap["status"] not in {"filled", "canceled", "cancelled", "expired", "rejected"}
        and snap["stop_price"] is not None
    )


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def capture_opening_guard_orders(
    cfg,
    client,
    *,
    held_symbols: set[str] | None = None,
    open_orders: list[Any] | None = None,
) -> dict[str, Any]:
    """Cancel protective sell stops before the open and persist re-arm data."""
    if not bool(cfg.get("opening_stop_guard", "enabled", default=False)):
        return {"enabled": False, "cancelled": []}
    held = {str(s or "").upper() for s in (held_symbols or set())}
    if open_orders is None:
        open_orders = client.get_open_orders()
    state = _load_state(cfg)
    existing = {
        str(row.get("order_id") or "")
        for row in state.get("orders", [])
        if row.get("status") in {"cancelled_for_opening_guard", "pending_rearm"}
    }
    cancelled: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    for order in open_orders or []:
        snap = _snapshot(order)
        if not _is_protective_stop(order, held):
            continue
        if snap["id"] in existing:
            continue
        try:
            client.cancel_order(snap["id"])
        except Exception as exc:
            log.warning("[%s] opening-stop guard cancel failed for %s: %s",
                        snap["symbol"], snap["id"], exc)
            cancelled.append({**snap, "status": "cancel_failed", "error": str(exc)})
            continue
        row = {
            "order_id": snap["id"],
            "symbol": snap["symbol"],
            "qty": snap["qty"],
            "stop_price": snap["stop_price"],
            "time_in_force": snap["time_in_force"] or "day",
            "captured_at": now,
            "status": "pending_rearm",
        }
        state["orders"].append(row)
        cancelled.append(row)
    cutoff = datetime.now(timezone.utc) - timedelta(days=5)
    state["orders"] = [
        row for row in state.get("orders", [])
        if (_parse_ts(row.get("captured_at")) or datetime.now(timezone.utc)) >= cutoff
    ]
    if cancelled:
        _save_state(cfg, state)
    return {"enabled": True, "cancelled": cancelled}


def _quote_price(client, symbol: str) -> float | None:
    try:
        quote = client.get_stock_quote(symbol)
    except Exception as exc:
        log.warning("[%s] opening-stop quote failed: %s", symbol, exc)
        return None
    vals = []
    for name in ("bid_price", "ask_price", "price", "last_price"):
        raw = getattr(quote, name, None)
        if raw in (None, "") and isinstance(quote, dict):
            raw = quote.get(name)
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue
        if val > 0:
            vals.append(val)
    if len(vals) >= 2:
        return sum(vals[:2]) / 2.0
    return vals[0] if vals else None


def _position_by_symbol(client) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        positions = client.get_positions_raw()
    except Exception:
        positions = client.get_positions()
    for p in positions or []:
        sym = str(getattr(p, "symbol", "") or "").upper()
        if sym:
            out[sym] = p
    return out


def rearm_opening_guard_orders(cfg, client, executor=None) -> dict[str, Any]:
    """Re-arm previously cancelled opening stops after the opening delay."""
    if not bool(cfg.get("opening_stop_guard", "enabled", default=False)):
        return {"enabled": False, "actions": []}
    state = _load_state(cfg)
    positions = _position_by_symbol(client)
    actions: list[dict[str, Any]] = []
    catastrophic_gap = float(cfg.get(
        "opening_stop_guard", "catastrophic_gap_pct", default=0.03,
    ) or 0.03)
    buffer_pct = float(cfg.get(
        "opening_stop_guard", "rearm_below_market_buffer_pct", default=0.003,
    ) or 0.003)
    for row in state.get("orders", []):
        if row.get("status") != "pending_rearm":
            continue
        sym = str(row.get("symbol") or "").upper()
        qty = float(row.get("qty") or 0)
        stop_price = float(row.get("stop_price") or 0)
        p = positions.get(sym)
        if p is None:
            row["status"] = "position_absent"
            actions.append({"symbol": sym, "status": "position_absent"})
            continue
        try:
            held_qty = abs(float(getattr(p, "qty", 0) or 0))
        except (TypeError, ValueError):
            held_qty = 0.0
        rearm_qty = min(qty, held_qty)
        if rearm_qty <= 0 or stop_price <= 0:
            row["status"] = "invalid_rearm_qty_or_stop"
            actions.append({"symbol": sym, "status": row["status"]})
            continue
        current = _quote_price(client, sym)
        if current is None:
            row["status"] = "quote_unavailable"
            actions.append({"symbol": sym, "status": "quote_unavailable"})
            continue
        if current <= stop_price * (1.0 - catastrophic_gap):
            reason = (
                f"opening stop guard catastrophic gap: current ${current:.2f} "
                f"below original stop ${stop_price:.2f}"
            )
            try:
                if executor is not None:
                    res = executor.close_position(sym, reason=reason)
                    action = res.to_dict()
                else:
                    order = client.close_position(sym)
                    action = {"order_id": str(getattr(order, "id", "") or "")}
                row["status"] = "closed_catastrophic_gap"
                row["rearmed_at"] = datetime.now(timezone.utc).isoformat()
                actions.append({"symbol": sym, "status": row["status"], **action})
            except Exception as exc:
                row["status"] = "close_failed"
                row["error"] = str(exc)
                actions.append({"symbol": sym, "status": "close_failed", "error": str(exc)})
            continue
        adjusted_stop = stop_price
        if current <= stop_price:
            adjusted_stop = round(max(0.01, current * (1.0 - buffer_pct)), 2)
        try:
            order = client.submit_stop_loss(
                symbol=sym,
                qty=rearm_qty,
                stop_price=adjusted_stop,
                side="sell",
                tif=row.get("time_in_force") or "day",
            )
            row["status"] = "rearmed"
            row["rearmed_at"] = datetime.now(timezone.utc).isoformat()
            row["new_order_id"] = str(getattr(order, "id", "") or "")
            row["new_stop_price"] = adjusted_stop
            actions.append({
                "symbol": sym,
                "status": "rearmed",
                "qty": rearm_qty,
                "stop_price": adjusted_stop,
                "order_id": row["new_order_id"],
            })
        except Exception as exc:
            row["status"] = "rearm_failed"
            row["error"] = str(exc)
            actions.append({"symbol": sym, "status": "rearm_failed", "error": str(exc)})
    _save_state(cfg, state)
    return {"enabled": True, "actions": actions}
