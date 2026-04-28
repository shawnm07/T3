"""Trade executor: receives sized decisions, applies approval gate, submits orders."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any

from src.alpaca_client import AlpacaClient
from src.config import Config
from src.decision import TradeDecision
from src.journal import log_trade
from src.kill_switch import increment_trade_counter
from src.risk import SizingDecision

log = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    symbol: str
    status: str  # "submitted" | "rejected" | "filled" | "unfilled"
    order_id: str | None = None
    approval_id: str | None = None
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
            "approval_id": self.approval_id,
            "message": self.message,
            "filled_qty": round(float(self.filled_qty), 6),
            "filled_avg_price": (round(float(self.filled_avg_price), 4)
                                 if self.filled_avg_price is not None else None),
            "final_status": self.final_status,
            "ok": self.ok,
        }


class TradeExecutor:
    def __init__(self, client: AlpacaClient, config: Config, is_crypto: bool = False):
        self.client = client
        self.cfg = config
        self.is_crypto = is_crypto
        self.mode = config.alpaca.mode
        self.fill_timeout = float(config.get("execution", "fill_timeout_s", default=30))
        self.fill_poll = float(config.get("execution", "fill_poll_s", default=1.0))

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

    def execute(self, decision: TradeDecision, sizing: SizingDecision) -> ExecutionResult:
        try:
            tif = "gtc" if self.is_crypto else "day"
            order = self.client.submit_bracket(
                symbol=sizing.symbol,
                qty=sizing.qty,
                side="buy" if sizing.side == "buy" else "sell",
                stop_loss=sizing.stop_loss if not self.is_crypto else None,
                take_profit=sizing.take_profit if not self.is_crypto else None,
                tif=tif,
            )
            increment_trade_counter()
            order_id = str(order.id)
            filled_qty, avg_price, final_status, ok = self._verify_fill(order)
            log_trade({
                "event": "order_submitted",
                "symbol": sizing.symbol,
                "order_id": order_id,
                "sizing": sizing.to_dict(),
                "decision": decision.to_dict(),
                "final_status": final_status,
                "filled_qty": filled_qty,
                "filled_avg_price": avg_price,
                "ok": ok,
            })
            if not ok:
                log.warning("[%s] order %s did NOT fill (status=%s filled=%.4f)",
                            sizing.symbol, order_id, final_status, filled_qty)
            return ExecutionResult(
                symbol=sizing.symbol,
                status="filled" if ok else "unfilled",
                order_id=order_id,
                message=f"{sizing.side} {sizing.qty} @ ~${sizing.entry} [{final_status}]",
                filled_qty=filled_qty, filled_avg_price=avg_price,
                final_status=final_status, ok=ok,
            )
        except Exception as e:
            log.error("Order submission failed for %s: %s", sizing.symbol, e)
            log_trade({"event": "order_failed", "symbol": sizing.symbol, "error": str(e), "sizing": sizing.to_dict()})
            return ExecutionResult(symbol=sizing.symbol, status="rejected", message=str(e), final_status="error")

    def partial_trade(self, symbol: str, side: str, delta_notional: float, reason: str = "") -> ExecutionResult:
        """Resize an existing position by a dollar amount. Uses a plain (non-bracket)
        notional order. For BUYs this adds shares; for SELLs this trims them.
        Existing bracket stop/target remain on the original entry.
        """
        try:
            abs_notional = abs(delta_notional)
            if abs_notional < 1:
                return ExecutionResult(symbol=symbol, status="rejected", message="delta < $1")
            # Alpaca notional market orders require tif=DAY
            order = self.client.submit_notional(symbol, abs_notional, side=side, tif="day")
            increment_trade_counter()
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
