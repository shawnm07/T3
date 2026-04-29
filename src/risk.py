"""Risk management: long-equity position sizing and protective stop levels."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any

from src.config import Config
from src.universe import sp500_sectors

log = logging.getLogger(__name__)


@dataclass
class SizingDecision:
    symbol: str
    side: str  # "buy"
    qty: float
    notional: float
    entry: float
    stop_loss: float
    take_profit: float | None
    risk_usd: float
    confidence: float
    reasoning: str
    limits: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "notional": round(self.notional, 2),
            "entry": round(self.entry, 2),
            "stop_loss": round(self.stop_loss, 2),
            "take_profit": (round(self.take_profit, 2)
                            if self.take_profit is not None else None),
            "risk_usd": round(self.risk_usd, 2),
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "limits": self.limits,
        }


class RiskManager:
    def __init__(self, config: Config):
        self.cfg = config
        self.max_position_pct = config.get("risk", "max_position_pct", default=0.50)
        # New entries cap at this lower fraction; AI arbiter scales them up over
        # subsequent scans toward max_position_pct based on conviction.
        self.initial_entry_cap_pct = config.get("risk", "initial_entry_cap_pct", default=0.15)
        self.max_sector_pct = config.get("risk", "max_sector_pct", default=0.30)
        self.max_leverage = config.get("risk", "max_leverage", default=1.0)
        self.stop_atr_mult = config.get("risk", "stop_loss_atr_mult", default=2.0)
        self.tp_atr_mult = config.get("risk", "take_profit_atr_mult", default=4.0)
        self.hard_stop_loss_pct = float(config.get("risk", "hard_stop_loss_pct", default=0.01))
        self.max_positions = config.get("risk", "max_positions", default=6)
        self.min_trade = config.get("risk", "min_trade_usd", default=500)
        self.cash_reserve_pct = config.get("risk", "cash_reserve_pct", default=0.20)
        self.cash_reserve_min_pct = config.get("risk", "cash_reserve_min_pct", default=0.10)
        self.high_conviction_threshold = config.get("risk", "high_conviction_threshold", default=0.75)
        # Cash-proxy symbol is treated as liquid cash, not a real position.
        self.cash_proxy_enabled = bool(config.get("cash_proxy", "enabled", default=False))
        self.cash_proxy_symbol = str(config.get("cash_proxy", "symbol", default="SPY"))
        self.last_sizing_audit: dict[str, Any] | None = None

    def _is_cash_proxy(self, symbol: str) -> bool:
        return self.cash_proxy_enabled and symbol == self.cash_proxy_symbol

    def hard_stop_loss_price(self, entry: float) -> float:
        """Return the execution-layer hard stop price for a long entry."""
        entry_f = float(entry or 0.0)
        pct = max(0.0, float(self.hard_stop_loss_pct or 0.0))
        if entry_f <= 0 or pct <= 0:
            return 0.0
        return round(entry_f * (1.0 - pct), 2)

    def validate_ai_sizing(
        self,
        symbol: str,
        qty: float,
        entry: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        equity: float = 0.0,
        existing_positions: list | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Hard-cap safety check on AI-supplied order parameters.

        The AI is the sizing authority for qty/entry. Python owns the hard
        stop. This function only enforces non-negotiable invariants that protect
        the account from a malformed AI response: long-only, max_position_pct,
        max_risk_per_trade_pct, max_positions, no duplicate. It does not
        resize the AI's qty; it ACCEPTS or REJECTS the trade.
        Returns (ok, audit_dict). On reject, audit_dict carries the reason.
        """
        try:
            ai_stop_f = float(stop_loss or 0)
        except (TypeError, ValueError):
            ai_stop_f = 0.0
        try:
            ai_take_f = float(take_profit or 0)
        except (TypeError, ValueError):
            ai_take_f = 0.0
        audit: dict[str, Any] = {
            "symbol": symbol,
            "qty": float(qty or 0),
            "entry": float(entry or 0),
            "ai_stop_loss": ai_stop_f,
            "ai_take_profit": ai_take_f,
            "hard_stop_loss_pct": float(self.hard_stop_loss_pct),
            "equity": float(equity or 0),
            "max_position_pct": float(self.max_position_pct),
            "max_risk_per_trade_pct": float(self.cfg.get("risk", "max_risk_per_trade_pct", default=0.005)),
            "max_positions": int(self.max_positions),
            "status": "approved",
        }
        if qty <= 0 or entry <= 0:
            audit["status"] = "rejected"
            audit["reject_reason"] = "non_positive_qty_or_entry"
            self.last_sizing_audit = audit
            return False, audit
        hard_stop = self.hard_stop_loss_price(entry)
        audit["stop_loss"] = hard_stop
        if hard_stop <= 0 or hard_stop >= entry:
            audit["status"] = "rejected"
            audit["reject_reason"] = "invalid_hard_stop"
            self.last_sizing_audit = audit
            return False, audit
        if take_profit not in (None, ""):
            try:
                take_profit_f = float(take_profit)
            except (TypeError, ValueError):
                take_profit_f = 0.0
            if take_profit_f and take_profit_f <= entry:
                audit["status"] = "rejected"
                audit["reject_reason"] = "target_not_above_entry"
                self.last_sizing_audit = audit
                return False, audit
        # Duplicate / max-positions check (skip for cash proxy)
        if not self._is_cash_proxy(symbol):
            held_syms = {getattr(p, "symbol", "") for p in (existing_positions or [])}
            held_syms.discard(self.cash_proxy_symbol if self.cash_proxy_enabled else "")
            if symbol in held_syms:
                audit["status"] = "rejected"
                audit["reject_reason"] = "already_held_use_rebalance_path"
                self.last_sizing_audit = audit
                return False, audit
            if len(held_syms) >= int(self.max_positions):
                audit["status"] = "rejected"
                audit["reject_reason"] = f"max_positions_{int(self.max_positions)}_reached"
                self.last_sizing_audit = audit
                return False, audit
        # Position-size cap
        notional = qty * entry
        max_notional = float(equity) * float(self.max_position_pct)
        audit["notional"] = round(notional, 2)
        audit["max_notional"] = round(max_notional, 2)
        if notional > max_notional * 1.01:
            audit["status"] = "rejected"
            audit["reject_reason"] = (
                f"qty*entry ${notional:,.0f} exceeds max_position_pct "
                f"${max_notional:,.0f}"
            )
            self.last_sizing_audit = audit
            return False, audit
        # Per-trade risk cap
        risk_usd = qty * (entry - hard_stop)
        cap = float(equity) * float(audit["max_risk_per_trade_pct"])
        audit["risk_usd"] = round(risk_usd, 2)
        audit["max_risk_usd"] = round(cap, 2)
        if risk_usd > cap * 1.01:
            audit["status"] = "rejected"
            audit["reject_reason"] = (
                f"risk ${risk_usd:,.0f} exceeds max_risk_per_trade ${cap:,.0f}"
            )
            self.last_sizing_audit = audit
            return False, audit
        # Min-trade floor
        if notional < float(self.min_trade):
            audit["status"] = "rejected"
            audit["reject_reason"] = f"notional ${notional:,.0f} below min_trade ${self.min_trade}"
            self.last_sizing_audit = audit
            return False, audit
        self.last_sizing_audit = audit
        return True, audit

    def build_sizing_from_ai(
        self,
        symbol: str,
        qty: float,
        entry: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        confidence: float = 0.0,
        reasoning: str = "",
    ) -> SizingDecision:
        """Wrap AI-supplied order params in a SizingDecision for journaling."""
        hard_stop = self.hard_stop_loss_price(entry)
        try:
            take_profit_f = float(take_profit) if take_profit not in (None, "") else None
        except (TypeError, ValueError):
            take_profit_f = None
        return SizingDecision(
            symbol=symbol,
            side="buy",
            qty=float(qty),
            notional=round(float(qty) * float(entry), 2),
            entry=float(entry),
            stop_loss=hard_stop,
            take_profit=take_profit_f,
            risk_usd=round(float(qty) * (float(entry) - float(hard_stop)), 2),
            confidence=float(confidence),
            reasoning=reasoning or "ai-direct sizing",
            limits={
                "source": "ai_direct",
                "hard_stop_loss_pct": float(self.hard_stop_loss_pct),
                "ai_stop_loss": stop_loss,
                "ai_take_profit": take_profit,
            },
        )

    def size_position(
        self,
        symbol: str,
        side: str,
        price: float,
        atr: float,
        confidence: float,
        equity: float,
        existing_positions: list,
    ) -> SizingDecision | None:
        reasons: list[str] = []
        audit: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "equity": round(float(equity or 0), 2),
            "price": round(float(price or 0), 4),
            "atr": round(float(atr or 0), 4),
            "confidence": round(float(confidence or 0), 4),
            "max_position_pct": float(self.max_position_pct),
            "initial_entry_cap_pct": float(self.initial_entry_cap_pct),
            "cash_reserve_pct": float(self.cash_reserve_pct),
            "cash_reserve_min_pct": float(self.cash_reserve_min_pct),
            "high_conviction_threshold": float(self.high_conviction_threshold),
            "max_risk_per_trade_pct": float(self.cfg.get("risk", "max_risk_per_trade_pct", default=0.005)),
        }
        self.last_sizing_audit = audit

        def reject(reason: str, **extra: Any) -> None:
            audit.update({"status": "rejected", "reject_reason": reason, **extra})
            self.last_sizing_audit = audit
            return None

        if side != "buy":
            return reject("long_only")

        # Exclude cash-proxy (e.g. SPY) from position limits — it's treated as liquid cash.
        real_positions = [p for p in existing_positions if not self._is_cash_proxy(p.symbol)]
        audit["existing_position_count"] = len(real_positions)

        # Pre-checks
        if len(real_positions) >= self.max_positions:
            log.info("Skipping %s: at max positions (%d)", symbol, self.max_positions)
            return reject("max_positions", max_positions=int(self.max_positions))
        if any(p.symbol == symbol for p in real_positions):
            return reject("already_in_position")

        sectors = sp500_sectors()
        sector = sectors.get(symbol)
        if sector:
            sector_exposure = sum(
                abs(float(p.market_value)) for p in real_positions
                if sectors.get(p.symbol) == sector
            )
            sector_pct = sector_exposure / equity if equity else 0.0
            audit["sector"] = sector
            audit["sector_exposure_pct_before"] = round(sector_pct, 4)
            audit["max_sector_pct"] = float(self.max_sector_pct)
            if sector_pct > self.max_sector_pct:
                log.info("Skipping %s: sector %s over limit", symbol, sector)
                return reject("sector_limit", sector=sector, sector_exposure_pct=round(sector_pct, 4))
            reasons.append(f"sector={sector}")

        # Base position size: confidence-scaled within ENTRY cap (smaller than the
        # absolute per-position cap; AI rebalance arbiter grows winners later).
        cap_pct = min(self.initial_entry_cap_pct, self.max_position_pct)
        size_pct = cap_pct * (0.4 + 0.6 * confidence)  # 40%-100% of entry cap by confidence
        notional = size_pct * equity
        audit.update({
            "entry_cap_pct": round(float(cap_pct), 4),
            "confidence_scaled_size_pct": round(float(size_pct), 4),
            "confidence_scaled_notional": round(float(notional), 2),
            "limiting_factor": "confidence_scaled_entry_cap",
        })
        if notional < self.min_trade:
            log.info("Skipping %s: notional $%.0f below min", symbol, notional)
            return reject("below_min_trade", raw_notional=round(notional, 2),
                          min_trade_usd=float(self.min_trade))

        # Cash reserve enforcement. High-conviction trades can dip into the reserve.
        invested = sum(abs(float(p.market_value)) for p in real_positions)
        is_high_conviction = confidence >= self.high_conviction_threshold
        reserve_pct = self.cash_reserve_min_pct if is_high_conviction else self.cash_reserve_pct
        max_invested = equity * (1.0 - reserve_pct)
        available = max_invested - invested
        audit.update({
            "invested_ex_cash_proxy": round(float(invested), 2),
            "reserve_pct_applied": round(float(reserve_pct), 4),
            "max_invested_after_reserve": round(float(max_invested), 2),
            "available_after_reserve": round(float(available), 2),
        })
        if available < self.min_trade:
            log.info(
                "Skipping %s: cash reserve floor reached (invested=$%.0f, cap=$%.0f, reserve=%.0f%%%s)",
                symbol, invested, max_invested, reserve_pct * 100,
                ", high-conviction" if is_high_conviction else "",
            )
            return reject("cash_reserve_floor", available_after_reserve=round(available, 2))
        if notional > available:
            notional = available
            reasons.append(f"reserve_capped@{reserve_pct*100:.0f}%")
            audit["limiting_factor"] = "cash_reserve"
        if is_high_conviction:
            reasons.append("high_conviction")

        # Python owns the hard execution stop: every strategy entry/add gets a
        # 1% protective stop by default. ATR remains useful for the optional
        # profit target and as audit context, but it no longer controls max loss.
        atr_stop = price - self.stop_atr_mult * atr
        stop = self.hard_stop_loss_price(price)
        target = price + self.tp_atr_mult * atr

        risk_per_share = abs(price - stop)
        risk_usd = risk_per_share * (notional / price) if price else 0
        # Cap total risk to 0.5% of equity per trade
        max_risk = equity * float(self.cfg.get("risk", "max_risk_per_trade_pct", default=0.005))
        audit.update({
            "stop_loss": round(float(stop), 4),
            "atr_reference_stop_loss": round(float(atr_stop), 4),
            "hard_stop_loss_pct": round(float(self.hard_stop_loss_pct), 4),
            "take_profit": round(float(target), 4),
            "risk_per_share": round(float(risk_per_share), 4),
            "risk_usd_before_risk_cap": round(float(risk_usd), 2),
            "max_risk_usd": round(float(max_risk), 2),
        })
        if risk_usd > max_risk and risk_per_share > 0:
            adjusted_notional = max_risk * price / risk_per_share
            notional = min(notional, adjusted_notional)
            risk_usd = max_risk
            reasons.append("risk_adjusted")
            audit["risk_adjusted_notional"] = round(float(adjusted_notional), 2)
            audit["limiting_factor"] = "max_risk_per_trade"

        qty = float(int(notional / price)) if price else 0.0
        if qty == 0 and price:
            # Allow fractional for high-priced names (account supports it)
            qty = round(notional / price, 4)

        if qty <= 0:
            return reject("zero_quantity")

        reasons.append(f"size={round(size_pct*100,1)}%cap")
        final_notional = qty * price
        if final_notional < self.min_trade:
            return reject("final_notional_below_min_trade",
                          final_notional=round(final_notional, 2),
                          min_trade_usd=float(self.min_trade))
        audit.update({
            "status": "approved",
            "qty": round(float(qty), 6),
            "final_notional": round(float(final_notional), 2),
            "final_position_pct": round(float(final_notional / equity), 4) if equity else 0.0,
            "risk_usd": round(float(risk_usd), 2),
            "reasoning": "; ".join(reasons),
        })
        self.last_sizing_audit = audit
        return SizingDecision(
            symbol=symbol, side=side, qty=qty,
            notional=final_notional, entry=price,
            stop_loss=round(stop, 2), take_profit=round(target, 2),
            risk_usd=risk_usd, confidence=confidence,
            reasoning="; ".join(reasons), limits=dict(audit),
        )
