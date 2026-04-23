"""Trade executor: receives sized decisions, applies approval gate, submits orders."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any

from src.alpaca_client import AlpacaClient
from src.config import Config
from src.decision import TradeDecision
from src.journal import enqueue_approval, log_trade
from src.kill_switch import increment_trade_counter
from src.risk import SizingDecision

log = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    symbol: str
    status: str  # "submitted" | "queued_for_approval" | "rejected"
    order_id: str | None = None
    approval_id: str | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "status": self.status,
            "order_id": self.order_id,
            "approval_id": self.approval_id,
            "message": self.message,
        }


class TradeExecutor:
    def __init__(self, client: AlpacaClient, config: Config, is_crypto: bool = False):
        self.client = client
        self.cfg = config
        self.is_crypto = is_crypto
        self.approval_threshold = config.get("kill_switch", "approval_threshold_usd", default=10000)
        self.mode = config.alpaca.mode

    def execute(self, decision: TradeDecision, sizing: SizingDecision) -> ExecutionResult:
        notional = sizing.notional

        if notional > self.approval_threshold:
            approval_id = enqueue_approval({
                "decision": decision.to_dict(),
                "sizing": sizing.to_dict(),
                "notional": notional,
                "threshold": self.approval_threshold,
            })
            msg = f"${notional:.0f} > threshold ${self.approval_threshold:.0f}, queued as {approval_id}"
            log.info("[%s] APPROVAL REQUIRED: %s", sizing.symbol, msg)
            log_trade({
                "event": "approval_queued",
                "symbol": sizing.symbol,
                "sizing": sizing.to_dict(),
                "decision": decision.to_dict(),
                "approval_id": approval_id,
            })
            return ExecutionResult(
                symbol=sizing.symbol, status="queued_for_approval",
                approval_id=approval_id, message=msg,
            )

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
            log_trade({
                "event": "order_submitted",
                "symbol": sizing.symbol,
                "order_id": str(order.id),
                "sizing": sizing.to_dict(),
                "decision": decision.to_dict(),
            })
            return ExecutionResult(
                symbol=sizing.symbol, status="submitted",
                order_id=str(order.id),
                message=f"submitted {sizing.side} {sizing.qty} @ ~${sizing.entry}",
            )
        except Exception as e:
            log.error("Order submission failed for %s: %s", sizing.symbol, e)
            log_trade({"event": "order_failed", "symbol": sizing.symbol, "error": str(e), "sizing": sizing.to_dict()})
            return ExecutionResult(symbol=sizing.symbol, status="rejected", message=str(e))

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
            log_trade({
                "event": "rebalance_trade",
                "symbol": symbol,
                "side": side,
                "notional": round(abs_notional, 2),
                "reason": reason,
                "order_id": str(order.id),
            })
            return ExecutionResult(
                symbol=symbol, status="submitted",
                order_id=str(order.id),
                message=f"rebalance {side} ${abs_notional:.0f} ({reason})",
            )
        except Exception as e:
            log.error("Partial trade failed for %s: %s", symbol, e)
            log_trade({"event": "rebalance_failed", "symbol": symbol, "error": str(e)})
            return ExecutionResult(symbol=symbol, status="rejected", message=str(e))

    def close_position(self, symbol: str, reason: str = "") -> ExecutionResult:
        try:
            self.client.close_position(symbol)
            log_trade({"event": "position_closed", "symbol": symbol, "reason": reason})
            return ExecutionResult(symbol=symbol, status="submitted", message=f"closed ({reason})")
        except Exception as e:
            log.error("Close failed for %s: %s", symbol, e)
            return ExecutionResult(symbol=symbol, status="rejected", message=str(e))
