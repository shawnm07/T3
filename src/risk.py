"""Risk management: position sizing, stop/target levels, portfolio-level checks."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any

from src.config import Config
from src.universe import sp500_sectors

log = logging.getLogger(__name__)


@dataclass
class SizingDecision:
    symbol: str
    side: str  # "buy" | "sell_short"
    qty: float
    notional: float
    entry: float
    stop_loss: float
    take_profit: float
    risk_usd: float
    confidence: float
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "notional": round(self.notional, 2),
            "entry": round(self.entry, 2),
            "stop_loss": round(self.stop_loss, 2),
            "take_profit": round(self.take_profit, 2),
            "risk_usd": round(self.risk_usd, 2),
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
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
        self.max_positions = config.get("risk", "max_positions", default=6)
        self.min_trade = config.get("risk", "min_trade_usd", default=500)
        self.cash_reserve_pct = config.get("risk", "cash_reserve_pct", default=0.20)
        self.cash_reserve_min_pct = config.get("risk", "cash_reserve_min_pct", default=0.10)
        self.high_conviction_threshold = config.get("risk", "high_conviction_threshold", default=0.75)
        # Cash-proxy symbol is treated as liquid cash, not a real position.
        self.cash_proxy_enabled = bool(config.get("cash_proxy", "enabled", default=False))
        self.cash_proxy_symbol = str(config.get("cash_proxy", "symbol", default="SPY"))

    def _is_cash_proxy(self, symbol: str) -> bool:
        return self.cash_proxy_enabled and symbol == self.cash_proxy_symbol

    def size_position(
        self,
        symbol: str,
        side: str,
        price: float,
        atr: float,
        confidence: float,
        equity: float,
        existing_positions: list,
        is_crypto: bool = False,
    ) -> SizingDecision | None:
        reasons: list[str] = []

        # Exclude cash-proxy (e.g. SPY) from position limits — it's treated as liquid cash.
        real_positions = [p for p in existing_positions if not self._is_cash_proxy(p.symbol)]

        # Pre-checks
        if len(real_positions) >= self.max_positions:
            log.info("Skipping %s: at max positions (%d)", symbol, self.max_positions)
            return None
        if any(p.symbol == symbol for p in real_positions):
            return None  # already in

        # Sector concentration (stocks only)
        if not is_crypto:
            sectors = sp500_sectors()
            sector = sectors.get(symbol)
            if sector:
                sector_exposure = sum(
                    float(p.market_value) for p in real_positions
                    if sectors.get(p.symbol) == sector
                )
                if sector_exposure / equity > self.max_sector_pct:
                    log.info("Skipping %s: sector %s over limit", symbol, sector)
                    return None
                reasons.append(f"sector={sector}")

        # Base position size: confidence-scaled within ENTRY cap (smaller than the
        # absolute per-position cap; AI rebalance arbiter grows winners later).
        cap_pct = min(self.initial_entry_cap_pct, self.max_position_pct)
        size_pct = cap_pct * (0.4 + 0.6 * confidence)  # 40%-100% of entry cap by confidence
        notional = size_pct * equity
        if notional < self.min_trade:
            log.info("Skipping %s: notional $%.0f below min", symbol, notional)
            return None

        # Cash reserve enforcement. High-conviction trades can dip into the reserve.
        # Crypto positions count toward invested capital; cash-proxy (SPY) does NOT —
        # it's liquid and will be auto-sold to fund this trade if cash is short.
        invested = sum(abs(float(p.market_value)) for p in real_positions)
        is_high_conviction = confidence >= self.high_conviction_threshold
        reserve_pct = self.cash_reserve_min_pct if is_high_conviction else self.cash_reserve_pct
        max_invested = equity * (1.0 - reserve_pct)
        available = max_invested - invested
        if available < self.min_trade:
            log.info(
                "Skipping %s: cash reserve floor reached (invested=$%.0f, cap=$%.0f, reserve=%.0f%%%s)",
                symbol, invested, max_invested, reserve_pct * 100,
                ", high-conviction" if is_high_conviction else "",
            )
            return None
        if notional > available:
            notional = available
            reasons.append(f"reserve_capped@{reserve_pct*100:.0f}%")
        if is_high_conviction:
            reasons.append("high_conviction")

        # Stop & target from ATR
        if side == "buy":
            stop = price - self.stop_atr_mult * atr
            target = price + self.tp_atr_mult * atr
        else:  # sell_short
            stop = price + self.stop_atr_mult * atr
            target = price - self.tp_atr_mult * atr

        risk_per_share = abs(price - stop)
        risk_usd = risk_per_share * (notional / price) if price else 0
        # Cap total risk to 0.5% of equity per trade
        max_risk = equity * 0.005
        if risk_usd > max_risk and risk_per_share > 0:
            adjusted_notional = max_risk * price / risk_per_share
            notional = min(notional, adjusted_notional)
            risk_usd = max_risk
            reasons.append("risk_adjusted")

        if is_crypto:
            qty = notional / price  # fractional
        else:
            qty = float(int(notional / price))
            if qty == 0:
                # Allow fractional for high-priced names (account supports it)
                qty = round(notional / price, 4)

        if qty <= 0:
            return None

        reasons.append(f"size={round(size_pct*100,1)}%cap")
        return SizingDecision(
            symbol=symbol, side=side, qty=qty,
            notional=qty * price, entry=price,
            stop_loss=round(stop, 2), take_profit=round(target, 2),
            risk_usd=risk_usd, confidence=confidence,
            reasoning="; ".join(reasons),
        )
