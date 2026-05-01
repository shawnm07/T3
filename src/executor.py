"""Trade executor: receives sized decisions and submits orders."""
from __future__ import annotations
import logging
import math
import re
import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any

from src.alpaca_client import AlpacaClient
from src.config import Config
from src.decision import TradeDecision
from src.journal import log_trade
from src.risk import SizingDecision

log = logging.getLogger(__name__)


def _ceil_cents(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_CEILING))


def _round_cents(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _floor_cents(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))


def _floor_qty(value: float, places: int = 6) -> float:
    quantum = Decimal("1").scaleb(-places)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_FLOOR))


_BASE_PRICE_RE = re.compile(r'"base_price"\s*:\s*"?(?P<price>[0-9]+(?:\.[0-9]+)?)"?')


@dataclass
class ExecutionResult:
    symbol: str
    status: str  # "submitted" | "rejected" | "filled" | "unfilled"
    order_id: str | None = None
    stop_order_id: str | None = None
    message: str = ""
    filled_qty: float = 0.0
    filled_avg_price: float | None = None
    final_status: str = ""
    stop_status: str = ""
    stop_price: float | None = None
    stop_error: str = ""
    ok: bool = False  # True if order filled (or partially filled with qty > 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "status": self.status,
            "order_id": self.order_id,
            "stop_order_id": self.stop_order_id,
            "message": self.message,
            "filled_qty": round(float(self.filled_qty), 6),
            "filled_avg_price": (round(float(self.filled_avg_price), 4)
                                 if self.filled_avg_price is not None else None),
            "final_status": self.final_status,
            "stop_status": self.stop_status,
            "stop_price": (round(float(self.stop_price), 4)
                           if self.stop_price is not None else None),
            "stop_error": self.stop_error,
            "ok": self.ok,
        }


class TradeExecutor:
    def __init__(self, client: AlpacaClient, config: Config):
        self.client = client
        self.cfg = config
        self.mode = config.alpaca.mode
        self.fill_timeout = float(config.get("execution", "fill_timeout_s", default=30))
        self.fill_poll = float(config.get("execution", "fill_poll_s", default=1.0))
        self.hard_stop_loss_pct = float(config.get("risk", "hard_stop_loss_pct", default=0.01))

    def _hard_stop_loss_price(self, entry_price: float | None) -> float | None:
        try:
            entry = float(entry_price or 0)
        except (TypeError, ValueError):
            entry = 0.0
        pct = max(0.0, float(self.hard_stop_loss_pct or 0.0))
        if entry <= 0 or pct <= 0:
            return None
        return _ceil_cents(entry * (1.0 - pct))

    def _protective_stop_loss_price(
        self,
        entry_price: float | None,
        stop_loss: float | None = None,
    ) -> tuple[float, str]:
        try:
            entry = float(entry_price or 0)
        except (TypeError, ValueError):
            entry = 0.0
        hard_stop = self._hard_stop_loss_price(entry)
        if hard_stop is None or hard_stop <= 0 or hard_stop >= entry:
            raise ValueError(f"cannot compute hard stop from entry_price={entry_price}")
        if stop_loss in (None, ""):
            return hard_stop, "hard_stop"
        try:
            ai_stop = _round_cents(float(stop_loss))
        except (TypeError, ValueError) as exc:
            raise ValueError("stop_loss not numeric") from exc
        if ai_stop <= 0:
            raise ValueError(f"stop_loss {ai_stop} must be > 0")
        if ai_stop >= entry:
            log.warning(
                "Ignoring stale/invalid AI stop %.4f because it is >= entry %.4f; "
                "using hard stop %.4f",
                ai_stop, entry, hard_stop,
            )
            return hard_stop, "ai_stop_invalid_for_entry_used_hard_stop"
        if ai_stop < hard_stop:
            log.warning("Clamping AI stop %.4f to hard stop floor %.4f", ai_stop, hard_stop)
            return hard_stop, "ai_stop_clamped_to_hard_stop"
        return ai_stop, ("ai_tighter_stop" if ai_stop > hard_stop else "hard_stop")

    def _take_profit_or_none(self, take_profit: float | None, entry_price: float | None) -> float | None:
        if take_profit in (None, ""):
            return None
        try:
            target = float(take_profit)
            entry = float(entry_price or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("take_profit not numeric") from exc
        if entry <= 0:
            raise ValueError(f"cannot validate take_profit from entry_price={entry_price}")
        if target <= entry:
            raise ValueError(f"take_profit {target} must be > entry_price {entry}")
        return target

    @staticmethod
    def _client_order_id(symbol: str, prefix: str = "tb-entry") -> str:
        clean = "".join(ch for ch in str(symbol).upper() if ch.isalnum())[:10]
        return f"{prefix}-{clean}-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _protected_bracket_qty(symbol: str, qty: float) -> int:
        """Alpaca rejects fractional bracket/OTO orders; submit whole shares."""
        try:
            qty_f = abs(float(qty))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"qty not numeric for protected order: {qty!r}") from exc
        whole_qty = math.floor(qty_f)
        if whole_qty < 1:
            raise ValueError(
                f"protected buy qty for {symbol} rounds below 1 whole share "
                f"(requested {qty_f:.6f})"
            )
        if abs(qty_f - whole_qty) > 1e-9:
            log.warning(
                "[%s] fractional protected buy qty %.6f rounded down to %d whole shares",
                symbol, qty_f, whole_qty,
            )
        return whole_qty

    def _verify_fill(self, order) -> tuple[float, float | None, str, bool]:
        """Poll the order until terminal. Returns (filled_qty, filled_avg_price, final_status, ok)."""
        try:
            order_id = str(order.id)
        except Exception:
            return (0.0, None, "unknown", False)
        final, ok = self.client.wait_for_order_fill(
            order_id, timeout_s=self.fill_timeout, poll_s=self.fill_poll,
        )
        if final is None:
            return (0.0, None, "poll_failed", False)
        status = str(getattr(final, "status", "") or "").lower().replace("orderstatus.", "")
        filled_qty = float(getattr(final, "filled_qty", 0) or 0)
        avg_price = getattr(final, "filled_avg_price", None)
        try:
            avg_price = float(avg_price) if avg_price is not None else None
        except (TypeError, ValueError):
            avg_price = None
        return (filled_qty, avg_price, status, ok)

    def _cancel_open_parent_if_needed(self, order_id: str, final_status: str, ok: bool) -> None:
        if ok:
            return
        terminal = {"rejected", "canceled", "cancelled", "expired", "suspended", "replaced"}
        if str(final_status or "").lower() in terminal:
            return
        try:
            self.client.cancel_order(order_id)
            log.warning("Canceled unfilled protective parent order %s (status=%s)",
                        order_id, final_status)
        except Exception as e:
            log.warning("Could not cancel unfilled protective parent order %s: %s",
                        order_id, e)

    @staticmethod
    def _base_price_from_error(error: str) -> float | None:
        match = _BASE_PRICE_RE.search(str(error or ""))
        if not match:
            return None
        try:
            return float(match.group("price"))
        except (TypeError, ValueError):
            return None

    def _submit_standalone_stop(
        self,
        symbol: str,
        filled_qty: float,
        entry_price: float | None,
        requested_stop_loss: float | None,
    ) -> tuple[object | None, float | None, str, str]:
        """Submit a simple sell stop for the actual filled entry quantity.

        Returns (stop_order, stop_price, stop_source, error). If Alpaca reports
        a base-price threshold, retry once at ``base_price - $0.01``.
        """
        qty = _floor_qty(abs(float(filled_qty or 0.0)))
        if qty <= 0:
            return None, None, "none", "filled_qty <= 0"
        stop_to_submit, stop_source = self._protective_stop_loss_price(
            entry_price, requested_stop_loss,
        )
        try:
            stop_order = self.client.submit_stop_loss(
                symbol=symbol,
                qty=qty,
                stop_price=stop_to_submit,
                side="sell",
                tif="day",
                client_order_id=self._client_order_id(symbol, prefix="tb-stop"),
            )
            return stop_order, stop_to_submit, stop_source, ""
        except Exception as exc:
            first_error = str(exc)
            base_price = self._base_price_from_error(first_error)
            if base_price is None:
                return None, stop_to_submit, stop_source, first_error
            adjusted_stop = _floor_cents(min(stop_to_submit, base_price - 0.01))
            if adjusted_stop <= 0 or adjusted_stop >= stop_to_submit:
                return None, stop_to_submit, stop_source, first_error
            try:
                stop_order = self.client.submit_stop_loss(
                    symbol=symbol,
                    qty=qty,
                    stop_price=adjusted_stop,
                    side="sell",
                    tif="day",
                    client_order_id=self._client_order_id(symbol, prefix="tb-stop"),
                )
                return (
                    stop_order,
                    adjusted_stop,
                    f"{stop_source}_broker_base_price_adjusted",
                    "",
                )
            except Exception as retry_exc:
                return None, adjusted_stop, stop_source, str(retry_exc)

    def _cancel_symbol_orders_before_sell(self, symbol: str, reason: str) -> int:
        """Cancel open protective child orders before sells/trims/exits."""
        if not bool(self.cfg.get("execution", "cancel_open_orders_before_sell", default=True)):
            return 0
        try:
            cancelled = self.client.cancel_open_orders_for_symbol(symbol)
            if cancelled:
                log.info("[%s] cancelled %d open order(s) before sell (%s)",
                         symbol, cancelled, reason)
            return int(cancelled or 0)
        except AttributeError:
            return 0
        except Exception as e:
            log.warning("[%s] cancel open orders before sell failed: %s", symbol, e)
            return 0

    def execute(self, decision: TradeDecision, sizing: SizingDecision) -> ExecutionResult:
        try:
            stop_to_submit, stop_source = self._protective_stop_loss_price(
                sizing.entry, sizing.stop_loss,
            )
            take_profit = self._take_profit_or_none(sizing.take_profit, sizing.entry)
            order_qty = float(sizing.qty)
            order = self.client.submit_qty(
                symbol=sizing.symbol,
                qty=order_qty,
                side="buy",
                tif="day",
                client_order_id=self._client_order_id(sizing.symbol),
            )
            order_id = str(order.id)
            filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            stop_order = None
            stop_order_id = None
            stop_status = "not_submitted_entry_unfilled"
            stop_error = ""
            actual_stop = None
            actual_stop_source = stop_source
            if ok and filled_qty > 0:
                stop_order, actual_stop, actual_stop_source, stop_error = self._submit_standalone_stop(
                    sizing.symbol,
                    filled_qty,
                    avg_price or sizing.entry,
                    sizing.stop_loss,
                )
                if stop_order is not None:
                    stop_order_id = str(getattr(stop_order, "id", "") or "")
                    stop_status = "submitted"
                else:
                    stop_status = "failed"
                    log.error("[%s] entry filled but standalone stop failed: %s",
                              sizing.symbol, stop_error)
            log_trade({
                "event": "order_submitted",
                "symbol": sizing.symbol,
                "order_id": order_id,
                "stop_order_id": stop_order_id,
                "requested_qty": sizing.qty,
                "submitted_qty": order_qty,
                "sizing": sizing.to_dict(),
                "decision": decision.to_dict(),
                "protective_stop": {
                    "type": "stop_market",
                    "placement": "standalone_after_entry_fill",
                    "entry_reference": sizing.entry,
                    "filled_avg_price_reference": avg_price,
                    "stop_loss_pct": self.hard_stop_loss_pct,
                    "hard_stop_loss_floor": self._hard_stop_loss_price(sizing.entry),
                    "pre_entry_stop_price": stop_to_submit,
                    "stop_price": actual_stop,
                    "stop_loss_source": actual_stop_source,
                    "original_stop_loss": sizing.stop_loss,
                    "take_profit_requested": take_profit,
                    "take_profit_submitted": None,
                    "stop_order_status": stop_status,
                    "stop_order_error": stop_error,
                },
                "final_status": final_status,
                "filled_qty": filled_qty,
                "filled_avg_price": avg_price,
                "ok": ok,
            })
            if not ok:
                self._cancel_open_parent_if_needed(order_id, final_status, ok)
                log.warning("[%s] order %s did NOT fill (status=%s filled=%.4f)",
                            sizing.symbol, order_id, final_status, filled_qty)
            return ExecutionResult(
                symbol=sizing.symbol,
                status="filled" if ok else "unfilled",
                order_id=order_id,
                stop_order_id=stop_order_id,
                message=(
                    f"{sizing.side} {order_qty} @ ~${sizing.entry} "
                    f"standalone stop ${actual_stop or stop_to_submit} "
                    f"[entry={final_status} stop={stop_status}]"
                ),
                filled_qty=filled_qty, filled_avg_price=avg_price,
                final_status=final_status,
                stop_status=stop_status,
                stop_price=actual_stop,
                stop_error=stop_error,
                ok=ok,
            )
        except Exception as e:
            log.error("Order submission failed for %s: %s", sizing.symbol, e)
            log_trade({"event": "order_failed", "symbol": sizing.symbol, "error": str(e), "sizing": sizing.to_dict()})
            return ExecutionResult(symbol=sizing.symbol, status="rejected", message=str(e), final_status="error")

    def execute_ai_bracket(
        self,
        symbol: str,
        qty: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        reason: str = "",
        decision: TradeDecision | None = None,
        ai_audit: dict[str, Any] | None = None,
        entry_price: float | None = None,
    ) -> ExecutionResult:
        """Submit an AI-sized buy, then place a standalone protective stop.

        The AI remains the sizing authority for share count. Python enforces
        loss control: every BUY/ADD gets a separate stop-market order no wider
        than 1% below the actual fill reference. AI stop fields are optional; a
        tighter AI stop is honored, while a wider or stale stop is clamped to
        the hard stop. Take-profit is audited but not submitted here because
        this path intentionally avoids Alpaca advanced order classes.
        """
        try:
            if entry_price is None and ai_audit:
                entry_price = ai_audit.get("entry_price") or ai_audit.get("ai_entry_price")
            stop_to_submit, stop_source = self._protective_stop_loss_price(entry_price, stop_loss)
            take_profit_to_submit = self._take_profit_or_none(take_profit, entry_price)
            order_qty = float(qty)
            order = self.client.submit_qty(
                symbol=symbol,
                qty=order_qty,
                side="buy",
                tif="day",
                client_order_id=self._client_order_id(symbol),
            )
            order_id = str(order.id)
            filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            stop_order = None
            stop_order_id = None
            stop_status = "not_submitted_entry_unfilled"
            stop_error = ""
            actual_stop = None
            actual_stop_source = stop_source
            if ok and filled_qty > 0:
                stop_order, actual_stop, actual_stop_source, stop_error = self._submit_standalone_stop(
                    symbol,
                    filled_qty,
                    avg_price or entry_price,
                    stop_loss,
                )
                if stop_order is not None:
                    stop_order_id = str(getattr(stop_order, "id", "") or "")
                    stop_status = "submitted"
                else:
                    stop_status = "failed"
                    log.error("[%s] AI entry filled but standalone stop failed: %s",
                              symbol, stop_error)
            log_trade({
                "event": "ai_order_submitted",
                "symbol": symbol,
                "order_id": order_id,
                "stop_order_id": stop_order_id,
                "qty": order_qty,
                "requested_qty": qty,
                "submitted_qty": order_qty,
                "stop_loss": stop_to_submit,
                "take_profit": None,
                "protective_stop": {
                    "type": "stop_market",
                    "placement": "standalone_after_entry_fill",
                    "entry_reference": entry_price,
                    "filled_avg_price_reference": avg_price,
                    "stop_loss_pct": self.hard_stop_loss_pct,
                    "hard_stop_loss_floor": self._hard_stop_loss_price(entry_price),
                    "pre_entry_stop_price": stop_to_submit,
                    "stop_price": actual_stop,
                    "stop_loss_source": actual_stop_source,
                    "ai_stop_loss": stop_loss,
                    "ai_take_profit": take_profit,
                    "take_profit_submitted": None,
                    "stop_order_status": stop_status,
                    "stop_order_error": stop_error,
                },
                "reason": reason,
                "ai_audit": ai_audit or {},
                "decision": decision.to_dict() if decision is not None else None,
                "final_status": final_status,
                "filled_qty": filled_qty,
                "filled_avg_price": avg_price,
                "ok": ok,
            })
            if not ok:
                self._cancel_open_parent_if_needed(order_id, final_status, ok)
                log.warning("[%s] AI entry order %s did NOT fill (status=%s filled=%.4f)",
                            symbol, order_id, final_status, filled_qty)
            return ExecutionResult(
                symbol=symbol,
                status="filled" if ok else "unfilled",
                order_id=order_id,
                stop_order_id=stop_order_id,
                message=(
                    f"buy {order_qty} standalone stop ${actual_stop or stop_to_submit} "
                    f"[entry={final_status} stop={stop_status}]"
                ),
                filled_qty=filled_qty, filled_avg_price=avg_price,
                final_status=final_status,
                stop_status=stop_status,
                stop_price=actual_stop,
                stop_error=stop_error,
                ok=ok,
            )
        except Exception as e:
            log.error("AI entry/stop submission failed for %s: %s", symbol, e)
            log_trade({"event": "ai_order_failed", "symbol": symbol, "error": str(e),
                       "qty": qty, "stop_loss": stop_loss, "take_profit": take_profit,
                       "ai_audit": ai_audit or {}})
            return ExecutionResult(symbol=symbol, status="rejected",
                                   message=str(e), final_status="error")

    def execute_ai_qty_delta(
        self,
        symbol: str,
        delta_qty: float,
        reason: str = "",
        ai_audit: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Adjust a held position by an exact share delta from the AI.

        Negative deltas trim shares. Positive deltas are rejected here because
            every BUY/ADD must go through the entry-plus-standalone-stop path.
            For full EXITs use ``close_position``.
        """
        try:
            abs_qty = abs(float(delta_qty))
            if abs_qty <= 0:
                return ExecutionResult(symbol=symbol, status="rejected",
                                       message="delta_qty == 0")
            side = "buy" if delta_qty > 0 else "sell"
            if side == "buy":
                return ExecutionResult(
                    symbol=symbol,
                    status="rejected",
                    message="positive qty delta requires entry-plus-standalone-stop buy path",
                )
            cancelled = self._cancel_symbol_orders_before_sell(symbol, reason)
            order = self.client.submit_qty(symbol, abs_qty, side=side, tif="day")
            order_id = str(order.id)
            filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            log_trade({
                "event": "ai_qty_delta",
                "symbol": symbol,
                "side": side,
                "delta_qty": float(delta_qty),
                "reason": reason,
                "cancelled_orders_before_sell": cancelled,
                "order_id": order_id,
                "ai_audit": ai_audit or {},
                "final_status": final_status,
                "filled_qty": filled_qty,
                "filled_avg_price": avg_price,
                "ok": ok,
            })
            if not ok:
                log.warning("[%s] AI qty delta %s did NOT fill (status=%s)",
                            symbol, side, final_status)
            return ExecutionResult(
                symbol=symbol,
                status="filled" if ok else "unfilled",
                order_id=order_id,
                message=f"ai {side} {abs_qty} shares ({reason}) [{final_status}]",
                filled_qty=filled_qty, filled_avg_price=avg_price,
                final_status=final_status, ok=ok,
            )
        except Exception as e:
            log.error("AI qty delta failed for %s: %s", symbol, e)
            log_trade({"event": "ai_qty_delta_failed", "symbol": symbol,
                       "delta_qty": float(delta_qty), "error": str(e)})
            return ExecutionResult(symbol=symbol, status="rejected",
                                   message=str(e), final_status="error")

    def partial_trade(self, symbol: str, side: str, delta_notional: float, reason: str = "") -> ExecutionResult:
        """Resize an existing position by a dollar amount.

        Only SELL trims are allowed here. BUY notional resizes are rejected
        because every ADD must go through the protected share-qty path.
        """
        try:
            abs_notional = abs(delta_notional)
            if abs_notional < 1:
                return ExecutionResult(symbol=symbol, status="rejected", message="delta < $1")
            if side.lower() == "buy":
                return ExecutionResult(
                    symbol=symbol,
                    status="rejected",
                    message="notional BUY path disabled; use protected share-qty execution",
                )
            # Alpaca notional market orders require tif=DAY
            cancelled = self._cancel_symbol_orders_before_sell(symbol, reason)
            order = self.client.submit_notional(symbol, abs_notional, side=side, tif="day")
            order_id = str(order.id)
            filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            log_trade({
                "event": "rebalance_trade",
                "symbol": symbol,
                "side": side,
                "notional": round(abs_notional, 2),
                "reason": reason,
                "cancelled_orders_before_sell": cancelled,
                "order_id": order_id,
                "final_status": final_status,
                "filled_qty": filled_qty,
                "filled_avg_price": avg_price,
                "ok": ok,
            })
            if not ok:
                log.warning("[%s] rebalance %s did NOT fill (status=%s)", symbol, side, final_status)
            return ExecutionResult(
                symbol=symbol,
                status="filled" if ok else "unfilled",
                order_id=order_id,
                message=f"rebalance {side} ${abs_notional:.0f} ({reason}) [{final_status}]",
                filled_qty=filled_qty, filled_avg_price=avg_price,
                final_status=final_status, ok=ok,
            )
        except Exception as e:
            log.error("Partial trade failed for %s: %s", symbol, e)
            log_trade({"event": "rebalance_failed", "symbol": symbol, "error": str(e)})
            return ExecutionResult(symbol=symbol, status="rejected", message=str(e), final_status="error")

    def reduce_position_pct(
        self, symbol: str, percentage: float, reason: str = "",
    ) -> ExecutionResult:
        """Trim an existing position by a percentage (e.g. 50 = sell half).

        Used by the earnings-gate trim_50 verdict and the preclose
        consecutive-veto circuit-breaker. Routes through the broker's
        ClosePosition with a percentage arg so we don't have to compute
        share quantity ourselves.
        """
        pct = max(1.0, min(99.0, float(percentage)))
        try:
            cancelled = self._cancel_symbol_orders_before_sell(symbol, reason)
            order = self.client.close_position(symbol, percentage=pct)
            order_id = str(getattr(order, "id", "")) or None
            filled_qty, avg_price, final_status, ok = (0.0, None, "no_order_id", False)
            if order_id:
                filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            log_trade({
                "event": "position_trimmed", "symbol": symbol,
                "percentage": pct, "reason": reason,
                "cancelled_orders_before_sell": cancelled,
                "order_id": order_id, "final_status": final_status,
                "filled_qty": filled_qty, "ok": ok,
            })
            if not ok:
                log.warning("[%s] trim %.0f%% did NOT fill (status=%s)",
                            symbol, pct, final_status)
            return ExecutionResult(
                symbol=symbol,
                status="filled" if ok else "unfilled",
                order_id=order_id,
                message=f"trim {pct:.0f}% ({reason}) [{final_status}]",
                filled_qty=filled_qty, filled_avg_price=avg_price,
                final_status=final_status, ok=ok,
            )
        except Exception as e:
            log.error("Trim failed for %s: %s", symbol, e)
            return ExecutionResult(symbol=symbol, status="rejected",
                                   message=str(e), final_status="error")

    def close_position(self, symbol: str, reason: str = "") -> ExecutionResult:
        try:
            cancelled = self._cancel_symbol_orders_before_sell(symbol, reason)
            order = self.client.close_position(symbol)
            order_id = str(getattr(order, "id", "")) or None
            filled_qty, avg_price, final_status, ok = (0.0, None, "no_order_id", False)
            if order_id:
                filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            log_trade({
                "event": "position_closed", "symbol": symbol, "reason": reason,
                "cancelled_orders_before_sell": cancelled,
                "order_id": order_id, "final_status": final_status,
                "filled_qty": filled_qty, "ok": ok,
            })
            if not ok:
                log.warning("[%s] close did NOT fill (status=%s)", symbol, final_status)
            return ExecutionResult(
                symbol=symbol,
                status="filled" if ok else "unfilled",
                order_id=order_id,
                message=f"close ({reason}) [{final_status}]",
                filled_qty=filled_qty, filled_avg_price=avg_price,
                final_status=final_status, ok=ok,
            )
        except Exception as e:
            log.error("Close failed for %s: %s", symbol, e)
            return ExecutionResult(symbol=symbol, status="rejected", message=str(e), final_status="error")
