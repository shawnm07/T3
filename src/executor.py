"""Trade executor: receives sized decisions and submits orders."""
from __future__ import annotations
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from src.alpaca_client import AlpacaClient
from src.config import Config
from src.decision import TradeDecision
from src.journal import log_trade
from src.risk import SizingDecision

log = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    symbol: str
    status: str  # "submitted" | "rejected" | "filled" | "unfilled"
    order_id: str | None = None
    message: str = ""
    filled_qty: float = 0.0
    filled_avg_price: float | None = None
    final_status: str = ""
    ok: bool = False  # True if order filled (or partially filled with qty > 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "status": self.status,
            "order_id": self.order_id,
            "message": self.message,
            "filled_qty": round(float(self.filled_qty), 6),
            "filled_avg_price": (round(float(self.filled_avg_price), 4)
                                 if self.filled_avg_price is not None else None),
            "final_status": self.final_status,
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
        return round(entry * (1.0 - pct), 2)

    def _take_profit_or_none(self, take_profit: float | None, entry_price: float | None) -> float | None:
        try:
            target = float(take_profit) if take_profit not in (None, "") else 0.0
            entry = float(entry_price or 0)
        except (TypeError, ValueError):
            return None
        return target if target > entry > 0 else None

    @staticmethod
    def _client_order_id(symbol: str) -> str:
        clean = "".join(ch for ch in str(symbol).upper() if ch.isalnum())[:10]
        return f"tb-protect-{clean}-{uuid.uuid4().hex[:12]}"

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

    def execute(self, decision: TradeDecision, sizing: SizingDecision) -> ExecutionResult:
        try:
            hard_stop = self._hard_stop_loss_price(sizing.entry)
            if hard_stop is None:
                raise ValueError(f"cannot compute hard stop from entry={sizing.entry}")
            take_profit = self._take_profit_or_none(sizing.take_profit, sizing.entry)
            order = self.client.submit_bracket(
                symbol=sizing.symbol,
                qty=sizing.qty,
                side="buy",
                stop_loss=hard_stop,
                take_profit=take_profit,
                tif="gtc",
                client_order_id=self._client_order_id(sizing.symbol),
            )
            order_id = str(order.id)
            filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            log_trade({
                "event": "order_submitted",
                "symbol": sizing.symbol,
                "order_id": order_id,
                "sizing": sizing.to_dict(),
                "decision": decision.to_dict(),
                "protective_stop": {
                    "type": "stop_market",
                    "entry_reference": sizing.entry,
                    "stop_loss_pct": self.hard_stop_loss_pct,
                    "stop_price": hard_stop,
                    "original_stop_loss": sizing.stop_loss,
                    "take_profit_submitted": take_profit,
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
                message=f"{sizing.side} {sizing.qty} @ ~${sizing.entry} stop ${hard_stop} [{final_status}]",
                filled_qty=filled_qty, filled_avg_price=avg_price,
                final_status=final_status, ok=ok,
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
        """Submit a protected AI-sized buy.

        The AI remains the sizing authority for share count, but Python owns
        the loss control: every BUY/ADD gets a 1% stop-market OTO/bracket leg.
        The old AI stop/take-profit fields are accepted for audit/backward
        compatibility, but they are not required and the AI stop is never used
        to widen the hard stop.
        """
        try:
            if entry_price is None and ai_audit:
                entry_price = ai_audit.get("entry_price") or ai_audit.get("ai_entry_price")
            hard_stop = self._hard_stop_loss_price(entry_price)
            if hard_stop is None:
                raise ValueError(f"cannot compute hard stop from entry_price={entry_price}")
            take_profit_to_submit = self._take_profit_or_none(take_profit, entry_price)
            order = self.client.submit_bracket(
                symbol=symbol,
                qty=qty,
                side="buy",
                stop_loss=hard_stop,
                take_profit=take_profit_to_submit,
                tif="gtc",
                client_order_id=self._client_order_id(symbol),
            )
            order_id = str(order.id)
            filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            log_trade({
                "event": "ai_order_submitted",
                "symbol": symbol,
                "order_id": order_id,
                "qty": qty,
                "stop_loss": hard_stop,
                "take_profit": take_profit_to_submit,
                "protective_stop": {
                    "type": "stop_market",
                    "entry_reference": entry_price,
                    "stop_loss_pct": self.hard_stop_loss_pct,
                    "stop_price": hard_stop,
                    "ai_stop_loss": stop_loss,
                    "ai_take_profit": take_profit,
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
                log.warning("[%s] AI bracket order %s did NOT fill (status=%s filled=%.4f)",
                            symbol, order_id, final_status, filled_qty)
            return ExecutionResult(
                symbol=symbol,
                status="filled" if ok else "unfilled",
                order_id=order_id,
                message=f"buy {qty} stop ${hard_stop} [{final_status}]",
                filled_qty=filled_qty, filled_avg_price=avg_price,
                final_status=final_status, ok=ok,
            )
        except Exception as e:
            log.error("AI bracket submission failed for %s: %s", symbol, e)
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
        every BUY/ADD must go through ``execute_ai_bracket`` and receive the
        hard protective stop. For full EXITs use ``close_position``.
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
                    message="positive qty delta requires protected buy path",
                )
            order = self.client.submit_qty(symbol, abs_qty, side=side, tif="day")
            order_id = str(order.id)
            filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            log_trade({
                "event": "ai_qty_delta",
                "symbol": symbol,
                "side": side,
                "delta_qty": float(delta_qty),
                "reason": reason,
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
            order = self.client.submit_notional(symbol, abs_notional, side=side, tif="day")
            order_id = str(order.id)
            filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            log_trade({
                "event": "rebalance_trade",
                "symbol": symbol,
                "side": side,
                "notional": round(abs_notional, 2),
                "reason": reason,
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
            order = self.client.close_position(symbol, percentage=pct)
            order_id = str(getattr(order, "id", "")) or None
            filled_qty, avg_price, final_status, ok = (0.0, None, "no_order_id", False)
            if order_id:
                filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            log_trade({
                "event": "position_trimmed", "symbol": symbol,
                "percentage": pct, "reason": reason,
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
            order = self.client.close_position(symbol)
            order_id = str(getattr(order, "id", "")) or None
            filled_qty, avg_price, final_status, ok = (0.0, None, "no_order_id", False)
            if order_id:
                filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            log_trade({
                "event": "position_closed", "symbol": symbol, "reason": reason,
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
