"""Trade executor: receives sized decisions and submits orders."""
from __future__ import annotations
import json
import logging
import math
import re
import time
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
_WASH_TRADE_CODE = 40310000


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
    def _enum_text(value: Any) -> str:
        raw = getattr(value, "value", value)
        text = str(raw or "").lower()
        return text.rsplit(".", 1)[-1]

    @staticmethod
    def _parse_broker_error(exc: Exception) -> dict[str, Any]:
        text = str(exc)
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _wash_trade_payload(self, exc: Exception) -> dict[str, Any] | None:
        data = self._parse_broker_error(exc)
        message = str(data.get("message") or "").lower()
        reject_reason = str(data.get("reject_reason") or "").lower()
        if (
            data.get("code") == _WASH_TRADE_CODE
            and "wash trade" in message
            and "opposite side" in reject_reason
            and data.get("existing_order_id")
        ):
            return data
        return None

    def _cancel_wait_status(self, order_id: str, timeout_s: float = 10.0) -> str:
        try:
            self.client.cancel_order(order_id)
        except Exception as exc:
            log.warning("Cancel request for wash-trade blocker %s failed: %s", order_id, exc)
        deadline = time.monotonic() + max(0.0, timeout_s)
        last_status = ""
        while True:
            try:
                order = self.client.get_order(order_id)
            except Exception as exc:
                return f"lookup_failed:{exc}"
            last_status = self._enum_text(getattr(order, "status", ""))
            if last_status in {
                "canceled",
                "cancelled",
                "expired",
                "rejected",
                "filled",
                "suspended",
            }:
                return last_status
            if time.monotonic() >= deadline:
                return last_status or "unknown"
            time.sleep(0.25)

    def _protective_stop_snapshot(self, order: Any) -> dict[str, Any]:
        return {
            "id": str(getattr(order, "id", "") or ""),
            "symbol": str(getattr(order, "symbol", "") or "").upper(),
            "side": self._enum_text(getattr(order, "side", "")),
            "type": self._enum_text(getattr(order, "type", "")),
            "status": self._enum_text(getattr(order, "status", "")),
            "qty": float(getattr(order, "qty", 0) or 0),
            "stop_price": (
                float(getattr(order, "stop_price", 0) or 0)
                if getattr(order, "stop_price", None) not in (None, "")
                else None
            ),
            "order_class": self._enum_text(getattr(order, "order_class", "")),
            "client_order_id": str(getattr(order, "client_order_id", "") or ""),
        }

    def _is_recoverable_wash_blocker(self, symbol: str, order: Any) -> bool:
        snap = self._protective_stop_snapshot(order)
        return (
            snap["symbol"] == str(symbol or "").upper()
            and snap["side"] == "sell"
            and snap["type"] in {"stop", "stop_limit", "trailing_stop"}
            and snap["qty"] > 0
            and (snap["stop_price"] is not None or snap["type"] == "trailing_stop")
            and snap["status"] not in {"filled", "canceled", "cancelled", "expired", "rejected"}
        )

    def _restore_cancelled_stop(self, symbol: str, retry_info: dict[str, Any], reason: str) -> dict[str, Any]:
        cancelled = dict(retry_info.get("cancelled_order") or {})
        qty = float(cancelled.get("qty") or 0)
        stop_price = cancelled.get("stop_price")
        if qty <= 0 or stop_price in (None, ""):
            return {"status": "skipped", "reason": "no_restorable_stop_snapshot"}
        try:
            restored = self.client.submit_stop_loss(
                symbol=symbol,
                qty=_floor_qty(qty),
                stop_price=float(stop_price),
                side="sell",
                tif="day",
                client_order_id=self._client_order_id(symbol, prefix="tb-stop-restore"),
            )
            return {
                "status": "submitted",
                "reason": reason,
                "order_id": str(getattr(restored, "id", "") or ""),
                "qty": _floor_qty(qty),
                "stop_price": _round_cents(float(stop_price)),
            }
        except Exception as exc:
            log.error("[%s] failed to restore cancelled protective stop: %s", symbol, exc)
            return {"status": "failed", "reason": reason, "error": str(exc)}

    def _position_qty_or_fallback(self, symbol: str, filled_qty: float, retry_info: dict[str, Any]) -> float:
        sym = str(symbol or "").upper()
        try:
            for pos in self.client.get_positions_raw() or []:
                if str(getattr(pos, "symbol", "") or "").upper() == sym:
                    qty = abs(float(getattr(pos, "qty", 0) or 0))
                    if qty > 0:
                        return _floor_qty(qty)
        except Exception as exc:
            log.warning("[%s] could not refresh position qty after wash recovery: %s", sym, exc)
        prior_qty = float((retry_info.get("cancelled_order") or {}).get("qty") or 0)
        return _floor_qty(max(0.0, prior_qty + float(filled_qty or 0.0)))

    def _submit_buy_with_wash_recovery(
        self,
        symbol: str,
        qty: float,
        *,
        client_order_id: str,
    ) -> tuple[Any, dict[str, Any]]:
        """Submit a BUY, recovering once from Alpaca's opposite-stop wash guard."""
        try:
            order = self.client.submit_qty(
                symbol=symbol,
                qty=qty,
                side="buy",
                tif="day",
                client_order_id=client_order_id,
            )
            return order, {"triggered": False}
        except Exception as first_exc:
            payload = self._wash_trade_payload(first_exc)
            if payload is None:
                raise
            existing_order_id = str(payload.get("existing_order_id") or "")
            blocker = self.client.get_order(existing_order_id)
            if not self._is_recoverable_wash_blocker(symbol, blocker):
                raise
            cancelled_snapshot = self._protective_stop_snapshot(blocker)
            cancel_status = self._cancel_wait_status(existing_order_id)
            if cancel_status not in {"canceled", "cancelled", "expired", "rejected"}:
                raise RuntimeError(
                    f"wash-trade blocker {existing_order_id} not safely cancelled "
                    f"(status={cancel_status})"
                ) from first_exc

            retry_info = {
                "triggered": True,
                "broker_error": payload,
                "existing_order_id": existing_order_id,
                "cancel_status": cancel_status,
                "cancelled_order": cancelled_snapshot,
            }
            retry_client_order_id = self._client_order_id(symbol, prefix="tb-entry-retry")
            retry_info["retry_client_order_id"] = retry_client_order_id
            log.warning(
                "[%s] wash-trade guard blocked buy because stop %s was open; "
                "cancelled stop and retrying entry",
                symbol,
                existing_order_id,
            )
            try:
                order = self.client.submit_qty(
                    symbol=symbol,
                    qty=qty,
                    side="buy",
                    tif="day",
                    client_order_id=retry_client_order_id,
                )
                return order, retry_info
            except Exception as retry_exc:
                retry_info["retry_error"] = str(retry_exc)
                retry_info["restored_stop"] = self._restore_cancelled_stop(
                    symbol,
                    retry_info,
                    reason="entry_retry_failed",
                )
                log_trade({
                    "event": "wash_trade_recovery_failed",
                    "symbol": symbol,
                    "qty": qty,
                    "recovery": retry_info,
                })
                raise

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

    def _normalize_buy_qty_for_asset(self, symbol: str, qty: float) -> tuple[float, dict[str, Any]]:
        normalizer = getattr(self.client, "normalize_buy_qty_for_asset", None)
        if normalizer is None:
            return float(qty), {}
        submitted_qty, asset_audit, reject_reason = normalizer(symbol, qty)
        if reject_reason:
            exc = ValueError(reject_reason)
            setattr(exc, "asset_audit", dict(asset_audit or {}))
            raise exc
        return float(submitted_qty), dict(asset_audit or {})

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
            order_qty, asset_audit = self._normalize_buy_qty_for_asset(
                sizing.symbol, order_qty,
            )
            order, wash_recovery = self._submit_buy_with_wash_recovery(
                symbol=sizing.symbol,
                qty=order_qty,
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
                stop_qty = filled_qty
                if wash_recovery.get("triggered"):
                    stop_qty = self._position_qty_or_fallback(
                        sizing.symbol,
                        filled_qty,
                        wash_recovery,
                    )
                stop_order, actual_stop, actual_stop_source, stop_error = self._submit_standalone_stop(
                    sizing.symbol,
                    stop_qty,
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
            elif wash_recovery.get("triggered"):
                self._cancel_open_parent_if_needed(order_id, final_status, ok)
                wash_recovery["retry_parent_cancelled_before_stop_restore"] = True
                wash_recovery["restored_stop"] = self._restore_cancelled_stop(
                    sizing.symbol,
                    wash_recovery,
                    reason="entry_unfilled_after_wash_retry",
                )
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
                    "asset_check": asset_audit,
                },
                "wash_trade_recovery": wash_recovery if wash_recovery.get("triggered") else None,
                "final_status": final_status,
                "filled_qty": filled_qty,
                "filled_avg_price": avg_price,
                "ok": ok,
            })
            if wash_recovery.get("triggered"):
                log_trade({
                    "event": "wash_trade_recovery",
                    "symbol": sizing.symbol,
                    "entry_order_id": order_id,
                    "stop_order_id": stop_order_id,
                    "final_status": final_status,
                    "filled_qty": filled_qty,
                    "stop_status": stop_status,
                    "recovery": wash_recovery,
                    "ok": ok,
                })
            if not ok and not wash_recovery.get("retry_parent_cancelled_before_stop_restore"):
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
        working_ai_audit = dict(ai_audit or {})
        try:
            if entry_price is None and ai_audit:
                entry_price = ai_audit.get("entry_price") or ai_audit.get("ai_entry_price")
            stop_to_submit, stop_source = self._protective_stop_loss_price(entry_price, stop_loss)
            take_profit_to_submit = self._take_profit_or_none(take_profit, entry_price)
            order_qty = float(qty)
            order_qty, asset_audit = self._normalize_buy_qty_for_asset(symbol, order_qty)
            if asset_audit:
                working_ai_audit["asset_check"] = asset_audit
            order, wash_recovery = self._submit_buy_with_wash_recovery(
                symbol=symbol,
                qty=order_qty,
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
                stop_qty = filled_qty
                if wash_recovery.get("triggered"):
                    stop_qty = self._position_qty_or_fallback(
                        symbol,
                        filled_qty,
                        wash_recovery,
                    )
                stop_order, actual_stop, actual_stop_source, stop_error = self._submit_standalone_stop(
                    symbol,
                    stop_qty,
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
            elif wash_recovery.get("triggered"):
                self._cancel_open_parent_if_needed(order_id, final_status, ok)
                wash_recovery["retry_parent_cancelled_before_stop_restore"] = True
                wash_recovery["restored_stop"] = self._restore_cancelled_stop(
                    symbol,
                    wash_recovery,
                    reason="entry_unfilled_after_wash_retry",
                )
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
                "wash_trade_recovery": wash_recovery if wash_recovery.get("triggered") else None,
                "reason": reason,
                "ai_audit": working_ai_audit,
                "decision": decision.to_dict() if decision is not None else None,
                "final_status": final_status,
                "filled_qty": filled_qty,
                "filled_avg_price": avg_price,
                "ok": ok,
            })
            if wash_recovery.get("triggered"):
                log_trade({
                    "event": "wash_trade_recovery",
                    "symbol": symbol,
                    "entry_order_id": order_id,
                    "stop_order_id": stop_order_id,
                    "final_status": final_status,
                    "filled_qty": filled_qty,
                    "stop_status": stop_status,
                    "recovery": wash_recovery,
                    "ok": ok,
                })
            if not ok and not wash_recovery.get("retry_parent_cancelled_before_stop_restore"):
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
            asset_audit = getattr(e, "asset_audit", None)
            if asset_audit:
                working_ai_audit["asset_check"] = asset_audit
            log.error("AI entry/stop submission failed for %s: %s", symbol, e)
            log_trade({"event": "ai_order_failed", "symbol": symbol, "error": str(e),
                       "qty": qty, "stop_loss": stop_loss, "take_profit": take_profit,
                       "ai_audit": working_ai_audit})
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
