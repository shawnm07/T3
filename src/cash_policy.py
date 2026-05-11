"""Shared cash-vs-SPY policy for scan and trailing-stop processes.

The selector is the primary authority immediately after a scan, but the
5-minute trailing-stop task runs in a separate process. Persisting the latest
decision here keeps those processes from fighting each other.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.intraday_tape import compute_tape_signal

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_FILE = "data/state/cash_policy.json"
RISK_OFF_LABELS = {"mild_risk_off", "strong_risk_off"}


def _cfg_get(cfg: Any, *keys: str, default: Any = None) -> Any:
    try:
        return cfg.get(*keys, default=default)
    except Exception:
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat()


def parse_ts(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        ts = datetime.fromisoformat(text)
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def state_path(cfg: Any, override: str | Path | None = None) -> Path:
    rel = override or _cfg_get(
        cfg, "cash_policy", "state_file", default=DEFAULT_STATE_FILE
    )
    path = Path(rel)
    if path.is_absolute():
        return path
    return ROOT / path


def load_cash_policy(
    cfg: Any,
    *,
    path: str | Path | None = None,
) -> dict[str, Any] | None:
    p = state_path(cfg, path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("cash policy load failed: %s", exc)
        return None
    if not isinstance(data, dict):
        return None
    mode = str(data.get("mode") or "").lower()
    if mode not in {"cash", "spy"}:
        return None
    return data


def save_cash_policy(
    cfg: Any,
    decision: dict[str, Any],
    *,
    path: str | Path | None = None,
) -> Path:
    p = state_path(cfg, path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(decision, indent=2, sort_keys=True), encoding="utf-8")
    return p


def is_locked(decision: dict[str, Any] | None, *, now: datetime | None = None) -> bool:
    if not decision:
        return False
    lock_until = parse_ts(decision.get("lock_until"))
    if lock_until is None:
        return False
    now = now or utc_now()
    return now.astimezone(timezone.utc) < lock_until.astimezone(timezone.utc)


def _text_mentions_bearish_spy(selector_result: dict[str, Any]) -> bool:
    parts: list[str] = []
    for key in ("spy_vs_cash_reasoning", "portfolio_thesis"):
        value = selector_result.get(key)
        if value:
            parts.append(str(value))
    spy_decision = selector_result.get("spy_decision") or {}
    if isinstance(spy_decision, dict):
        for key in ("action", "one_sentence_reason"):
            value = spy_decision.get(key)
            if value:
                parts.append(str(value))
    text = " ".join(parts).lower()
    bearish_terms = (
        "bearish", "risk-off", "risk off", "downtrend", "below vwap",
        "macro halt", "preserve cash", "hold cash",
        "avoid spy", "cash over spy", "prefer cash", "cash is safer",
        "true cash is safer", "safer than spy",
    )
    return any(term in text for term in bearish_terms)


def build_selector_cash_policy_decision(
    cfg: Any,
    selector_result: dict[str, Any],
    *,
    tape_state: dict[str, Any] | None = None,
    spy_target_pct: float | None = None,
    cash_target_pct: float | None = None,
    scan_ts: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Convert selector SPY/cash targets into a locked policy decision."""
    now = now or utc_now()
    tape_state = dict(tape_state or {})
    reserve_pct = _to_float(_cfg_get(cfg, "risk", "cash_reserve_pct", default=0.05), 0.05)
    margin_pct = _to_float(
        _cfg_get(cfg, "cash_policy", "cash_preference_margin_pct", default=0.03),
        0.03,
    )
    badness_threshold = _to_float(
        _cfg_get(cfg, "cash_policy", "cash_badness_threshold", default=0.20),
        0.20,
    )
    lock_minutes = _to_int(
        _cfg_get(cfg, "cash_policy", "selector_lock_minutes", default=55),
        55,
    )

    spy_target = max(
        0.0,
        _to_float(selector_result.get("spy_target_pct") if spy_target_pct is None else spy_target_pct),
    )
    cash_target = max(
        0.0,
        _to_float(selector_result.get("cash_target_pct") if cash_target_pct is None else cash_target_pct),
    )
    idle_allocation = max(0.0, spy_target + cash_target)
    explicit_cash_size = (
        cash_target >= reserve_pct + margin_pct
        and cash_target >= max(spy_target, idle_allocation * 0.5)
    )

    severity = str(tape_state.get("severity_label") or "").lower()
    badness = _to_float(tape_state.get("tape_badness"), 0.0)
    has_data = bool(tape_state.get("has_data", True))
    bearish_tape = severity in RISK_OFF_LABELS or badness >= badness_threshold
    bearish_reason = _text_mentions_bearish_spy(selector_result)

    if explicit_cash_size and (bearish_tape or bearish_reason or not has_data):
        mode = "cash"
        reason = (
            selector_result.get("spy_vs_cash_reasoning")
            or f"Selector assigned {cash_target:.1%} to cash while SPY tape was defensive."
        )
    else:
        mode = "spy"
        if explicit_cash_size and not bearish_tape and not bearish_reason:
            reason = (
                "Selector left excess cash, but SPY tape was not bearish; "
                "policy parks excess cash in SPY."
            )
        else:
            reason = (
                selector_result.get("spy_vs_cash_reasoning")
                or f"Selector assigned {spy_target:.1%} to SPY versus {cash_target:.1%} cash."
            )

    return {
        "updated_at": _iso(now),
        "source": "selector",
        "mode": mode,
        "lock_until": _iso(now + timedelta(minutes=max(1, lock_minutes))),
        "spy_target_pct": round(spy_target, 6),
        "cash_target_pct": round(cash_target, 6),
        "tape": tape_state,
        "reason": str(reason)[:500],
        "selector_scan_ts": scan_ts or _iso(now),
        "confidence": "explicit",
    }


def fallback_cash_policy_decision(
    cfg: Any,
    tape_state: dict[str, Any] | None,
    *,
    previous: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Use deterministic SPY tape with hysteresis when no selector lock exists."""
    now = now or utc_now()
    tape_state = dict(tape_state or {})
    previous = previous if isinstance(previous, dict) else None
    min_hold_minutes = _to_int(
        _cfg_get(cfg, "cash_policy", "fallback_min_hold_minutes", default=30),
        30,
    )
    spy_threshold = _to_float(
        _cfg_get(cfg, "cash_policy", "spy_badness_threshold", default=0.08),
        0.08,
    )
    cash_threshold = _to_float(
        _cfg_get(cfg, "cash_policy", "cash_badness_threshold", default=0.20),
        0.20,
    )

    prev_mode = str((previous or {}).get("mode") or "").lower()
    prev_updated = parse_ts((previous or {}).get("updated_at"))
    if (
        prev_mode in {"cash", "spy"}
        and prev_updated is not None
        and now - prev_updated < timedelta(minutes=max(1, min_hold_minutes))
    ):
        out = dict(previous or {})
        out["active_hold_reason"] = f"minimum {min_hold_minutes} minute cash-policy hold"
        return out

    severity = str(tape_state.get("severity_label") or "favorable").lower()
    badness = _to_float(tape_state.get("tape_badness"), 0.0)
    spy_change = _to_float(tape_state.get("spy_intraday_change_pct"), 0.0)
    spy_vwap = _to_float(tape_state.get("spy_vs_vwap_pct"), 0.0)
    has_data = bool(tape_state.get("has_data", False))

    if not has_data:
        mode = prev_mode if prev_mode in {"cash", "spy"} else "cash"
        reason = "SPY intraday tape unavailable; preserving prior mode or holding cash."
    elif severity in RISK_OFF_LABELS or badness >= cash_threshold:
        mode = "cash"
        reason = (
            f"SPY tape is defensive ({severity}, badness={badness:.2f}); "
            "hold excess cash."
        )
    else:
        favorable_enough = (
            severity in {"favorable", "neutral"}
            and badness <= spy_threshold
            and spy_change >= 0
            and spy_vwap >= 0
        )
        if prev_mode == "cash" and not favorable_enough:
            mode = "cash"
            reason = (
                "Prior cash mode remains until SPY tape is clearly favorable "
                f"(badness={badness:.2f}, change={spy_change:+.2%}, "
                f"vs_vwap={spy_vwap:+.2%})."
            )
        else:
            mode = "spy"
            reason = (
                f"SPY tape is constructive enough for proxy parking "
                f"({severity}, badness={badness:.2f})."
            )

    return {
        "updated_at": _iso(now),
        "source": "tape_fallback",
        "mode": mode,
        "lock_until": None,
        "spy_target_pct": None,
        "cash_target_pct": None,
        "tape": tape_state,
        "reason": reason,
        "selector_scan_ts": (previous or {}).get("selector_scan_ts"),
        "confidence": "deterministic",
    }


def fetch_spy_tape_state(client: Any, cfg: Any) -> dict[str, Any]:
    symbol = str(_cfg_get(cfg, "cash_proxy", "symbol", default="SPY") or "SPY").upper()
    tape_cfg = _cfg_get(cfg, "macro", "intraday_tape_filter", default={}) or {}
    try:
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

        bars = client.get_stock_bars(
            [symbol],
            timeframe=TimeFrame(5, TimeFrameUnit.Minute),
            lookback_days=2,
        )
    except Exception as exc:
        log.warning("cash policy SPY tape fetch failed: %s", exc)
        bars = None
    return compute_tape_signal(bars, tape_cfg).to_dict()


def resolve_active_cash_policy(
    cfg: Any,
    client: Any | None = None,
    *,
    tape_state: dict[str, Any] | None = None,
    now: datetime | None = None,
    persist_fallback: bool = True,
) -> dict[str, Any]:
    now = now or utc_now()
    current = load_cash_policy(cfg)
    if is_locked(current, now=now):
        out = dict(current or {})
        out["active_lock_reason"] = "selector_lock"
        return out
    if tape_state is None and client is not None:
        tape_state = fetch_spy_tape_state(client, cfg)
    decision = fallback_cash_policy_decision(cfg, tape_state or {}, previous=current, now=now)
    if persist_fallback:
        try:
            save_cash_policy(cfg, decision)
        except Exception as exc:
            log.warning("cash policy fallback save failed: %s", exc)
    return decision


def _enum_text(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").lower().rsplit(".", 1)[-1]


def _order_id(order: Any) -> str:
    return str(getattr(order, "id", "") or "")


def _order_symbol(order: Any) -> str:
    return str(getattr(order, "symbol", "") or "").upper()


def _is_open_buy_order(order: Any, symbol: str) -> bool:
    return _order_symbol(order) == symbol.upper() and _enum_text(getattr(order, "side", "")) == "buy"


def _is_protective_stop(order: Any, symbol: str) -> bool:
    if _order_symbol(order) != symbol.upper():
        return False
    return (
        _enum_text(getattr(order, "side", "")) == "sell"
        and _enum_text(getattr(order, "type", "")) in {"stop", "stop_limit", "trailing_stop"}
    )


def _market_open(client: Any) -> bool:
    try:
        clock = client.get_clock()
        return bool(getattr(clock, "is_open", False))
    except Exception as exc:
        log.warning("cash policy clock lookup failed: %s", exc)
        return False


def _find_position(positions: list[Any], symbol: str) -> Any | None:
    sym = symbol.upper()
    for pos in positions or []:
        if str(getattr(pos, "symbol", "") or "").upper() == sym:
            return pos
    return None


def rearm_cash_proxy_stop(
    client: Any,
    cfg: Any,
    symbol: str,
    *,
    dry_run: bool = False,
    min_qty: float | None = None,
) -> dict[str, Any] | None:
    """Immediately restore a trailing-stop style protective stop for SPY."""
    try:
        positions = client.get_positions_raw() or []
    except Exception:
        try:
            positions = client.get_positions() or []
        except Exception as exc:
            return {"action": "stop_rearm_failed", "error": f"positions:{exc}"}
    pos = _find_position(positions, symbol)
    if pos is None:
        return {"action": "stop_rearm_skipped", "reason": "no_position"}
    qty = _to_float(getattr(pos, "qty", 0), 0.0)
    if min_qty is not None:
        qty = max(qty, _to_float(min_qty, 0.0))
    avg_entry = _to_float(getattr(pos, "avg_entry_price", 0), 0.0)
    current_price = _to_float(getattr(pos, "current_price", 0), 0.0)
    if qty <= 0 or avg_entry <= 0:
        return {"action": "stop_rearm_skipped", "reason": "invalid_position"}
    if current_price <= 0:
        current_price = avg_entry

    try:
        from Trailing_Stop.trailing_stops import desired_stop_price, _submit_native_stop
    except Exception as exc:
        return {"action": "stop_rearm_failed", "error": f"import:{exc}"}

    floor_pct = _to_float(_cfg_get(cfg, "trailing_stops", "floor_pct", default=2.0), 2.0)
    converged_pct = _to_float(
        _cfg_get(cfg, "trailing_stops", "converged_pct", default=0.5), 0.5
    )
    converge_gain_pct = _to_float(
        _cfg_get(cfg, "trailing_stops", "converge_gain_pct", default=10.0), 10.0
    )
    tif = str(_cfg_get(cfg, "trailing_stops", "extended_hours", "tif", default="gtc") or "gtc")
    desired = desired_stop_price(
        avg_entry,
        max(avg_entry, current_price),
        floor_pct=floor_pct,
        converged_pct=converged_pct,
        converge_gain_pct=converge_gain_pct,
    )
    order_id = _submit_native_stop(
        client,
        symbol,
        qty,
        desired,
        tif=tif,
        dry_run=dry_run,
    )
    if not order_id:
        return {"action": "stop_rearm_failed", "stop_price": desired}
    return {
        "action": "stop_rearmed",
        "symbol": symbol.upper(),
        "qty": round(qty, 6),
        "stop_price": desired,
        "order_id": order_id,
    }


def submit_cash_proxy_buy(
    client: Any,
    cfg: Any,
    symbol: str,
    notional: float,
    *,
    dry_run: bool = False,
    reason: str = "cash_proxy_buy",
) -> dict[str, Any]:
    symbol = str(symbol or "SPY").upper()
    amount = round(max(0.0, float(notional or 0.0)), 2)
    if amount <= 0:
        return {"action": "buy_skipped", "symbol": symbol, "skipped": "non_positive_notional"}

    before_qty = 0.0
    try:
        before_pos = _find_position(list(client.get_positions_raw() or []), symbol)
        if before_pos is not None:
            before_qty = _to_float(getattr(before_pos, "qty", 0), 0.0)
    except Exception:
        before_qty = 0.0

    try:
        open_orders = list(client.get_open_orders() or [])
    except Exception as exc:
        log.warning("cash proxy buy: open order lookup failed: %s", exc)
        open_orders = []
    duplicate_buy = [_order_id(o) for o in open_orders if _is_open_buy_order(o, symbol)]
    if duplicate_buy:
        return {
            "action": "buy_skipped",
            "symbol": symbol,
            "skipped": "open_proxy_buy_order",
            "open_buy_order_ids": duplicate_buy,
        }

    cancelled_stops: list[str] = []
    for order in open_orders:
        if not _is_protective_stop(order, symbol):
            continue
        oid = _order_id(order)
        if not oid:
            continue
        if dry_run:
            cancelled_stops.append(oid)
            continue
        try:
            client.cancel_order(oid)
            cancelled_stops.append(oid)
        except Exception as exc:
            log.warning("cash proxy buy: cancel %s stop %s failed: %s", symbol, oid, exc)

    if cancelled_stops and not dry_run:
        time.sleep(0.5)

    order_id = None
    final_status = "dry_run"
    ok = True
    filled_qty = 0.0
    if dry_run:
        log.info("[DRY] would buy %s notional $%.2f for %s", symbol, amount, reason)
    else:
        try:
            order = client.submit_notional(symbol, amount, side="buy", tif="day")
            order_id = _order_id(order)
            final_status = "submitted"
            filled_qty = _to_float(getattr(order, "filled_qty", 0), 0.0)
            if order_id and hasattr(client, "wait_for_order_fill"):
                filled_order, ok = client.wait_for_order_fill(order_id)
                if filled_order is not None:
                    final_status = _enum_text(getattr(filled_order, "status", "")) or final_status
                    filled_qty = max(
                        filled_qty,
                        _to_float(getattr(filled_order, "filled_qty", 0), 0.0),
                    )
            if hasattr(client, "invalidate_snapshot"):
                client.invalidate_snapshot()
        except Exception as exc:
            ok = False
            final_status = "error"
            log.warning("cash proxy buy failed for %s: %s", symbol, exc)
            rearm = rearm_cash_proxy_stop(client, cfg, symbol, dry_run=dry_run)
            return {
                "action": "buy_failed",
                "symbol": symbol,
                "notional": amount,
                "error": str(exc),
                "cancelled_stop_order_ids": cancelled_stops,
                "protective_stop": rearm,
            }

    min_rearm_qty = before_qty + filled_qty if filled_qty > 0 else None
    rearm = rearm_cash_proxy_stop(
        client,
        cfg,
        symbol,
        dry_run=dry_run,
        min_qty=min_rearm_qty,
    )
    return {
        "action": "buy_proxy",
        "symbol": symbol,
        "notional": amount,
        "order_id": order_id,
        "final_status": final_status,
        "filled_qty": round(filled_qty, 6),
        "ok": bool(ok),
        "cancelled_stop_order_ids": cancelled_stops,
        "protective_stop": rearm,
    }


def sweep_cash_to_proxy_if_allowed(
    client: Any,
    cfg: Any,
    equity: float,
    *,
    policy: dict[str, Any] | None = None,
    dry_run: bool = False,
    reason: str = "idle_cash_sweep",
) -> dict[str, Any] | None:
    if not bool(_cfg_get(cfg, "cash_proxy", "enabled", default=False)):
        return None
    symbol = str(_cfg_get(cfg, "cash_proxy", "symbol", default="SPY") or "SPY").upper()
    policy = policy or resolve_active_cash_policy(cfg, client, persist_fallback=True)
    mode = str((policy or {}).get("mode") or "").lower()
    if mode != "spy":
        return {
            "action": "hold_cash",
            "symbol": symbol,
            "skipped": "cash_policy_cash",
            "cash_policy": policy,
        }
    if not _market_open(client):
        return {
            "action": "buy_skipped",
            "symbol": symbol,
            "skipped": "market_closed",
            "cash_policy": policy,
        }
    try:
        account = client.get_account()
        cash = _to_float(getattr(account, "cash", 0), 0.0)
    except Exception as exc:
        log.warning("cash sweep account fetch failed: %s", exc)
        return {"action": "buy_skipped", "symbol": symbol, "skipped": "account_fetch_failed", "error": str(exc)}

    reserve_pct = _to_float(_cfg_get(cfg, "risk", "cash_reserve_pct", default=0.05), 0.05)
    min_rebalance = _to_float(_cfg_get(cfg, "cash_proxy", "min_rebalance_usd", default=500), 500.0)
    floor = max(0.0, float(equity or 0.0)) * max(0.0, reserve_pct)
    excess = round(max(0.0, cash - floor), 2)
    if excess < min_rebalance:
        return {
            "action": "hold",
            "symbol": symbol,
            "skipped": "below_min_rebalance",
            "cash": round(cash, 2),
            "floor": round(floor, 2),
            "excess": excess,
            "cash_policy": policy,
        }

    action = submit_cash_proxy_buy(
        client,
        cfg,
        symbol,
        excess,
        dry_run=dry_run,
        reason=reason,
    )
    action["cash_policy"] = policy
    action["floor"] = round(floor, 2)
    action["cash_before"] = round(cash, 2)
    return action
