"""Converging trailing-stop cycle — runs every 5 minutes.

Mechanics:
- Floor: stop never below avg_fill * (1 - floor_pct/100).
- Trail: stop = peak * (1 - trail_pct/100), where trail_pct linearly contracts
  from floor_pct (at 0% gain) to converged_pct (at converge_gain_pct gain).
- Ratchet: stops only move up.
- Tighter existing stops are respected; we only widen-to-2% if missing or wider.
- Extended hours: when regular session is closed and price has crossed the
  desired stop, submit a marketable limit sell with extended_hours=True.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import LimitOrderRequest

from src.alpaca_client import AlpacaClient
from src.cash_policy import resolve_active_cash_policy, sweep_cash_to_proxy_if_allowed
from src.config import Config

from .price_fetcher import PriceFetcher, build_default_fetcher
from .state import StopState

log = logging.getLogger(__name__)


def _round_cents(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def compute_trail_pct(
    gain: float,
    *,
    floor_pct: float = 2.0,
    converged_pct: float = 0.5,
    converge_gain_pct: float = 10.0,
) -> float:
    """Linear interpolation from floor_pct (gain=0) to converged_pct (gain=converge_gain_pct%).

    `gain` is fractional (0.05 = +5%).
    """
    if converge_gain_pct <= 0:
        return converged_pct
    g = max(0.0, float(gain))
    span = floor_pct - converged_pct
    converge_gain = converge_gain_pct / 100.0
    pct = floor_pct - (g / converge_gain) * span
    return max(converged_pct, min(floor_pct, pct))


def desired_stop_price(
    avg_fill: float,
    peak: float,
    *,
    floor_pct: float = 2.0,
    converged_pct: float = 0.5,
    converge_gain_pct: float = 10.0,
) -> float:
    """Compute the best (highest) stop allowed by the rule for given peak."""
    if avg_fill <= 0:
        return 0.0
    gain = max(0.0, peak / avg_fill - 1.0)
    pct = compute_trail_pct(
        gain,
        floor_pct=floor_pct,
        converged_pct=converged_pct,
        converge_gain_pct=converge_gain_pct,
    )
    trail = peak * (1.0 - pct / 100.0)
    floor = avg_fill * (1.0 - floor_pct / 100.0)
    return _round_cents(max(trail, floor))


@dataclass
class CycleResult:
    positions: int = 0
    created: int = 0
    adjusted: int = 0
    filled: int = 0
    synthetic_created: int = 0
    skipped_tighter: int = 0
    no_op: int = 0
    errors: list[str] = field(default_factory=list)
    cash_policy: dict[str, Any] | None = None
    cash_proxy_action: dict[str, Any] | None = None


@dataclass
class _SymbolView:
    symbol: str
    qty: float
    avg_fill: float
    current_price: float
    price_source: str
    existing_stop_id: str | None
    existing_stop_price: float | None


def _order_type_str(order: Any) -> str:
    raw = getattr(order, "type", None)
    if raw is None:
        return ""
    val = getattr(raw, "value", raw)
    return str(val).lower().replace("ordertype.", "")


def _order_side_str(order: Any) -> str:
    raw = getattr(order, "side", None)
    val = getattr(raw, "value", raw)
    return str(val).lower().replace("orderside.", "")


def _is_protective_stop(order: Any) -> bool:
    return (
        _order_side_str(order) == "sell"
        and _order_type_str(order) in {"stop", "stop_limit", "trailing_stop"}
    )


def _existing_protective_stop(open_orders: list[Any], symbol: str) -> Any | None:
    sym = symbol.upper()
    for o in open_orders or []:
        if str(getattr(o, "symbol", "")).upper() != sym:
            continue
        if _is_protective_stop(o):
            return o
    return None


def _is_whole_qty(qty: float) -> bool:
    try:
        q = float(qty)
    except (TypeError, ValueError):
        return False
    return q > 0 and abs(q - round(q)) < 1e-9


def _market_open(client: AlpacaClient) -> bool:
    try:
        clock = client.get_clock()
        return bool(getattr(clock, "is_open", False))
    except Exception as exc:
        log.warning("get_clock failed (assuming closed): %s", exc)
        return False


def _detect_filled_stops(
    state: StopState,
    open_orders: list[Any],
    held_symbols: set[str],
) -> list[dict]:
    """Detect tracked stops that disappeared from open orders AND position is gone.

    Returns list of {symbol, last_stop_id, last_stop_price, avg_fill}.
    """
    open_ids = {str(getattr(o, "id", "")) for o in (open_orders or [])}
    fills: list[dict] = []
    for sym, entry in state.as_dict().items():
        last_id = entry.get("last_stop_id")
        if not last_id:
            continue
        if last_id in open_ids:
            continue
        if sym.upper() in held_symbols:
            # Stop disappeared but position still held — likely cancelled by us
            # mid-cycle; not a fill.
            continue
        fills.append({
            "symbol": sym,
            "last_stop_id": last_id,
            "last_stop_price": entry.get("last_stop_price"),
            "avg_fill": entry.get("avg_fill"),
        })
    return fills


def _submit_native_stop(
    client: AlpacaClient,
    symbol: str,
    qty: float,
    stop_price: float,
    *,
    tif: str,
    dry_run: bool,
) -> str | None:
    if dry_run:
        log.info("[DRY] would submit native stop %s qty=%s @ %.2f tif=%s",
                 symbol, qty, stop_price, tif)
        return "dry-stop"
    try:
        order = client.submit_stop_loss(
            symbol=symbol,
            qty=qty,
            stop_price=stop_price,
            side="sell",
            tif=tif,
        )
        return str(getattr(order, "id", "") or "")
    except Exception as exc:
        msg = str(exc).lower()
        if "base price" in msg or "stop price" in msg:
            # Mirror executor.py fallback: retry one cent below current threshold.
            retry_price = _round_cents(stop_price - 0.01)
            log.warning(
                "Native stop %s @ %.2f rejected (%s); retry @ %.2f",
                symbol, stop_price, exc, retry_price,
            )
            try:
                order = client.submit_stop_loss(
                    symbol=symbol,
                    qty=qty,
                    stop_price=retry_price,
                    side="sell",
                    tif=tif,
                )
                return str(getattr(order, "id", "") or "")
            except Exception as exc2:
                log.error("Native stop retry failed for %s: %s", symbol, exc2)
                return None
        log.error("Native stop submission failed for %s: %s", symbol, exc)
        return None


def _submit_synthetic_stop(
    client: AlpacaClient,
    symbol: str,
    qty: float,
    current_price: float,
    discount_pct: float,
    *,
    dry_run: bool,
) -> str | None:
    """Marketable limit sell with extended_hours=True.

    Used when the regular session is closed AND the desired stop price has
    already been crossed by the live price.
    """
    limit_price = _round_cents(current_price * (1.0 - discount_pct / 100.0))
    if dry_run:
        log.info("[DRY] would submit synthetic ext-hours limit sell %s qty=%s @ %.2f",
                 symbol, qty, limit_price)
        return "dry-synth"
    if not _is_whole_qty(qty):
        log.warning(
            "Synthetic ext-hours stop for %s skipped: qty=%s not whole "
            "(Alpaca rejects fractional ext-hours orders)",
            symbol, qty,
        )
        return None
    try:
        req = LimitOrderRequest(
            symbol=symbol,
            qty=int(round(qty)),
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            limit_price=limit_price,
            extended_hours=True,
        )
        order = client.trading.submit_order(req)
        log.info(
            "Submitted synthetic ext-hours limit sell %s qty=%s @ %.2f order_id=%s",
            symbol, int(round(qty)), limit_price, getattr(order, "id", "?"),
        )
        return str(getattr(order, "id", "") or "")
    except Exception as exc:
        log.error("Synthetic ext-hours stop failed for %s: %s", symbol, exc)
        return None


def _cancel_order(client: AlpacaClient, order_id: str, *, dry_run: bool) -> bool:
    if dry_run:
        log.info("[DRY] would cancel order %s", order_id)
        return True
    try:
        client.cancel_order(order_id)
        return True
    except Exception as exc:
        log.warning("cancel_order(%s) failed: %s", order_id, exc)
        return False


def _safe_notify(notify_fn, *args, **kwargs) -> None:
    try:
        notify_fn(*args, **kwargs)
    except Exception as exc:
        log.warning("telegram notify failed: %s", exc)


def _notify_cash_policy_after_fill(
    action: dict[str, Any] | None,
    fills: list[dict],
) -> None:
    if not action:
        return
    kind = str(action.get("action") or "")
    skipped = action.get("skipped")
    if kind not in {"buy_proxy", "hold_cash", "buy_skipped"}:
        return
    symbols = ", ".join(str(f.get("symbol", "?")) for f in fills[:5])
    policy = action.get("cash_policy") or {}
    mode = str(policy.get("mode") or "?").upper()
    reason = str(policy.get("reason") or skipped or kind)
    if kind == "buy_proxy":
        msg = (
            f"Stop proceeds after {symbols} swept to {action.get('symbol', 'SPY')} "
            f"(${float(action.get('notional') or 0):,.0f}); cash policy={mode}. "
            f"{reason[:180]}"
        )
    elif skipped == "cash_policy_cash":
        msg = (
            f"Stop proceeds after {symbols} left in cash; cash policy={mode}. "
            f"{reason[:180]}"
        )
    else:
        msg = (
            f"Stop proceeds after {symbols}: SPY sweep skipped "
            f"({skipped or kind}); cash policy={mode}. {reason[:180]}"
        )
    try:
        from src.telegram_notifier import send_alert
        _safe_notify(send_alert, "cash_policy_stop_fill", "TrailingStops", msg)
    except Exception as exc:
        log.warning("notify cash policy after fill failed: %s", exc)


def run_trailing_stop_cycle(
    client: AlpacaClient,
    cfg: Config,
    *,
    state_path: Path | str | None = None,
    fetcher: PriceFetcher | None = None,
    dry_run: bool = False,
) -> CycleResult:
    result = CycleResult()

    if not cfg.get("trailing_stops", "enabled", default=True):
        log.info("trailing_stops disabled in config; skipping")
        return result

    floor_pct = float(cfg.get("trailing_stops", "floor_pct", default=2.0))
    converged_pct = float(cfg.get("trailing_stops", "converged_pct", default=0.5))
    converge_gain_pct = float(cfg.get("trailing_stops", "converge_gain_pct", default=10.0))
    notify_create = bool(cfg.get("trailing_stops", "notify_on_create", default=True))
    notify_fill = bool(cfg.get("trailing_stops", "notify_on_fill", default=True))
    notify_adjust = bool(cfg.get("trailing_stops", "notify_on_adjust", default=False))
    eh_enabled = bool(cfg.get("trailing_stops", "extended_hours", "enabled", default=True))
    eh_discount_pct = float(cfg.get("trailing_stops", "extended_hours", "limit_discount_pct", default=0.3))
    tif = str(cfg.get("trailing_stops", "extended_hours", "tif", default="gtc") or "gtc").lower()

    state_path = Path(state_path) if state_path else Path(
        cfg.get("trailing_stops", "state_file", default="Trailing_Stop/state/trailing_stops.json")
    )
    state = StopState(state_path)

    # --- positions snapshot ---
    try:
        positions = client.get_positions_raw() or []
    except Exception as exc:
        log.error("get_positions_raw failed: %s", exc)
        result.errors.append(f"positions:{exc}")
        return result

    held: dict[str, Any] = {}
    for p in positions:
        sym = str(getattr(p, "symbol", "")).upper()
        if not sym:
            continue
        try:
            qty = float(getattr(p, "qty", 0) or 0)
        except (TypeError, ValueError):
            qty = 0.0
        if qty <= 0:
            continue  # long-only by design
        held[sym] = p

    result.positions = len(held)

    # --- open orders snapshot ---
    try:
        open_orders = list(client.get_open_orders() or [])
    except Exception as exc:
        log.error("get_open_orders failed: %s", exc)
        result.errors.append(f"open_orders:{exc}")
        return result

    # --- fill detection (run BEFORE prune so we still see vanished symbols) ---
    fills = _detect_filled_stops(state, open_orders, set(held.keys()))
    if fills:
        for f in fills:
            result.filled += 1
            log.info("trailing stop FILLED: %s id=%s @ ~%.2f (avg_fill=%.2f)",
                     f["symbol"], f["last_stop_id"],
                     float(f.get("last_stop_price") or 0),
                     float(f.get("avg_fill") or 0))
            if notify_fill:
                try:
                    from src.telegram_notifier import send_alert
                    pct = 0.0
                    if f.get("avg_fill") and f.get("last_stop_price"):
                        pct = (float(f["last_stop_price"]) / float(f["avg_fill"]) - 1.0) * 100.0
                    msg = (
                        f"Trailing stop hit on {f['symbol']}: "
                        f"~${float(f.get('last_stop_price') or 0):.2f} "
                        f"({pct:+.2f}% vs avg fill ${float(f.get('avg_fill') or 0):.2f})"
                    )
                    _safe_notify(send_alert, "trailing_stop_fill", "TrailingStops", msg)
                except Exception as exc:
                    log.warning("notify trailing fill failed: %s", exc)

    # Prune state for symbols no longer held.
    removed = state.prune(held.keys())
    if removed:
        log.info("pruned %d stale state entr(ies): %s", len(removed), removed)

    if fills and cfg.get("cash_policy", "enabled", default=True):
        try:
            policy = resolve_active_cash_policy(
                cfg,
                client,
                persist_fallback=not dry_run,
            )
            result.cash_policy = policy
            try:
                account = client.get_account()
                equity = float(getattr(account, "equity", 0) or 0)
            except Exception as exc:
                equity = 0.0
                result.errors.append(f"cash_policy_account:{exc}")
            if equity > 0:
                action = sweep_cash_to_proxy_if_allowed(
                    client,
                    cfg,
                    equity,
                    policy=policy,
                    dry_run=dry_run,
                    reason="trailing_stop_fill",
                )
                result.cash_proxy_action = action
                _notify_cash_policy_after_fill(action, fills)
                if action and action.get("action") == "buy_proxy":
                    log.info(
                        "trailing-stop cash policy swept $%.0f to %s after fills=%s",
                        float(action.get("notional") or 0),
                        action.get("symbol", "SPY"),
                        [f.get("symbol") for f in fills],
                    )
                elif action:
                    log.info(
                        "trailing-stop cash policy action after fills=%s: %s",
                        [f.get("symbol") for f in fills],
                        action.get("skipped") or action.get("action"),
                    )
        except Exception as exc:
            log.warning("trailing-stop cash policy follow-through failed: %s", exc)
            result.errors.append(f"cash_policy:{exc}")

    if not held:
        if not dry_run:
            state.save()
        return result

    # --- price fetcher ---
    if fetcher is None:
        def _alpaca_lookup(sym: str) -> float | None:
            pos = held.get(sym.upper())
            if pos is None:
                return None
            raw = getattr(pos, "current_price", None)
            try:
                return float(raw) if raw is not None else None
            except (TypeError, ValueError):
                return None

        fetcher = build_default_fetcher(_alpaca_lookup)
    fetcher.reset_cycle()

    market_open_now = _market_open(client)

    # --- per-symbol cycle ---
    for sym, pos in sorted(held.items()):
        try:
            qty = float(getattr(pos, "qty", 0) or 0)
            try:
                avg_fill = float(getattr(pos, "avg_entry_price", 0) or 0)
            except (TypeError, ValueError):
                avg_fill = 0.0
            if avg_fill <= 0 or qty <= 0:
                log.warning("skip %s: invalid avg_fill=%s qty=%s", sym, avg_fill, qty)
                continue

            price, source = fetcher.get_quote(sym)
            if price is None or price <= 0:
                log.warning("skip %s: no price from any source", sym)
                result.errors.append(f"price:{sym}")
                continue

            saved = state.get(sym)
            saved_peak = float(saved.get("peak") or 0.0)
            peak = max(saved_peak, avg_fill, price)

            existing_order = _existing_protective_stop(open_orders, sym)
            existing_stop_price = None
            existing_stop_id = None
            if existing_order is not None:
                existing_stop_id = str(getattr(existing_order, "id", "") or "")
                raw_sp = getattr(existing_order, "stop_price", None)
                try:
                    existing_stop_price = float(raw_sp) if raw_sp is not None else None
                except (TypeError, ValueError):
                    existing_stop_price = None

            desired = desired_stop_price(
                avg_fill, peak,
                floor_pct=floor_pct,
                converged_pct=converged_pct,
                converge_gain_pct=converge_gain_pct,
            )

            log.info(
                "%s qty=%.4f avg_fill=%.2f peak=%.2f price=%.2f(%s) "
                "existing_stop=%s desired=%.2f",
                sym, qty, avg_fill, peak, price, source or "?",
                f"{existing_stop_price:.2f}" if existing_stop_price is not None else "none",
                desired,
            )

            new_stop_id = existing_stop_id
            new_stop_price = existing_stop_price
            synthetic_id = saved.get("synthetic_stop_id")

            # Decide action.
            if existing_stop_price is None:
                # No protective stop on book -> create at desired (>= 2% floor).
                placed_id = _submit_native_stop(
                    client, sym, qty, desired, tif=tif, dry_run=dry_run,
                )
                if placed_id:
                    result.created += 1
                    new_stop_id = placed_id
                    new_stop_price = desired
                    if notify_create:
                        try:
                            from src.telegram_notifier import send_alert
                            msg = (
                                f"Trailing stop created on {sym}: stop ${desired:.2f} "
                                f"({(desired/avg_fill - 1.0)*100:+.2f}% vs avg fill ${avg_fill:.2f})"
                            )
                            _safe_notify(send_alert, "trailing_stop_create", "TrailingStops", msg)
                        except Exception as exc:
                            log.warning("notify create failed: %s", exc)
                else:
                    result.errors.append(f"create:{sym}")
            elif existing_stop_price >= desired - 0.005:
                # Existing stop is tighter or equal — leave it alone.
                result.skipped_tighter += 1
            else:
                # Existing stop is wider — cancel and replace at desired.
                if _cancel_order(client, existing_stop_id, dry_run=dry_run):
                    if not dry_run:
                        time.sleep(0.5)  # let cancel propagate
                    placed_id = _submit_native_stop(
                        client, sym, qty, desired, tif=tif, dry_run=dry_run,
                    )
                    if placed_id:
                        result.adjusted += 1
                        new_stop_id = placed_id
                        new_stop_price = desired
                        if notify_adjust:
                            try:
                                from src.telegram_notifier import send_alert
                                msg = (
                                    f"Trailing stop tightened on {sym}: "
                                    f"${existing_stop_price:.2f} -> ${desired:.2f}"
                                )
                                _safe_notify(send_alert, "trailing_stop_adjust", "TrailingStops", msg)
                            except Exception as exc:
                                log.warning("notify adjust failed: %s", exc)
                    else:
                        result.errors.append(f"replace:{sym}")
                else:
                    result.errors.append(f"cancel:{sym}")

            # Synthetic extended-hours layer.
            if eh_enabled and not market_open_now:
                # Trigger if price has crossed the desired stop.
                if price <= desired and synthetic_id is None:
                    # Cancel any native stop first (Alpaca rejects opposite-side
                    # orders against an open stop).
                    if new_stop_id and new_stop_id != "dry-stop":
                        _cancel_order(client, new_stop_id, dry_run=dry_run)
                        new_stop_id = None
                        new_stop_price = None
                    placed = _submit_synthetic_stop(
                        client, sym, qty, price, eh_discount_pct, dry_run=dry_run,
                    )
                    if placed:
                        synthetic_id = placed
                        result.synthetic_created += 1
                        if notify_create:
                            try:
                                from src.telegram_notifier import send_alert
                                msg = (
                                    f"Ext-hours synthetic stop on {sym}: "
                                    f"limit sell ~${price * (1 - eh_discount_pct/100):.2f} "
                                    f"(price ${price:.2f} crossed stop ${desired:.2f})"
                                )
                                _safe_notify(send_alert, "trailing_stop_synthetic", "TrailingStops", msg)
                            except Exception as exc:
                                log.warning("notify synthetic failed: %s", exc)
            elif market_open_now and synthetic_id:
                # Regular session reopened: drop any leftover synthetic order so
                # the native GTC stop can take over next cycle.
                _cancel_order(client, synthetic_id, dry_run=dry_run)
                synthetic_id = None

            if existing_stop_price is not None and existing_stop_price >= desired - 0.005 \
                    and existing_stop_id != saved.get("last_stop_id"):
                # We adopted an externally-placed tighter stop into our state.
                pass

            if new_stop_id == existing_stop_id and existing_stop_price is not None \
                    and existing_stop_price >= desired - 0.005:
                # Tighter-stop branch: ensure recorded.
                pass

            if not (existing_stop_price is None
                    or existing_stop_price < desired - 0.005):
                # Tighter-stop branch did not produce a new order; record current
                # known stop into state so fill-detection still tracks it.
                pass

            if new_stop_id is None and existing_stop_id and existing_stop_price is not None:
                new_stop_id = existing_stop_id
                new_stop_price = existing_stop_price

            state.upsert(
                sym,
                avg_fill=avg_fill,
                peak=peak,
                last_stop_id=new_stop_id,
                last_stop_price=new_stop_price,
                synthetic_stop_id=synthetic_id,
            )
            if existing_stop_price is None and new_stop_id is None:
                result.no_op += 1
        except Exception as exc:
            log.exception("cycle error for %s: %s", sym, exc)
            result.errors.append(f"{sym}:{exc}")

    if not dry_run:
        state.save()
    return result
