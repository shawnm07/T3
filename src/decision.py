"""Decision engine: weighted multi-signal consensus → BUY / SELL_SHORT / HOLD."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any

from src.config import Config

log = logging.getLogger(__name__)


@dataclass
class TradeDecision:
    symbol: str
    action: str  # "buy" | "sell_short" | "close" | "hold"
    confidence: float
    combined_score: float
    signal_scores: dict[str, float] = field(default_factory=dict)
    signal_details: dict[str, Any] = field(default_factory=dict)
    reasoning: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "confidence": round(self.confidence, 3),
            "combined_score": round(self.combined_score, 3),
            "signal_scores": {k: round(v, 3) for k, v in self.signal_scores.items()},
            "signal_details": self.signal_details,
            "reasoning": self.reasoning,
        }


class DecisionEngine:
    def __init__(self, config: Config):
        self.cfg = config
        self.weights = config.get("signals", "weights", default={
            "macro": 0.15, "technical": 0.35, "fundamental": 0.20,
            "sentiment": 0.15, "risk": 0.15,
        }) or {}
        self.min_confidence = config.get("risk", "min_confidence", default=0.70)

    def decide(
        self,
        symbol: str,
        technical_score: float | None,
        fundamental_score: float | None,
        sentiment_score: float | None,
        macro_score: float | None,
        risk_score: float = 0.0,
        signal_details: dict[str, Any] | None = None,
    ) -> TradeDecision:
        scores: dict[str, float] = {}
        if technical_score is not None: scores["technical"] = technical_score
        if fundamental_score is not None: scores["fundamental"] = fundamental_score
        if sentiment_score is not None: scores["sentiment"] = sentiment_score
        if macro_score is not None: scores["macro"] = macro_score
        scores["risk"] = risk_score

        w_sum = 0.0
        combined = 0.0
        for k, s in scores.items():
            w = self.weights.get(k, 0.0)
            combined += w * s
            w_sum += w
        if w_sum > 0:
            combined = combined / w_sum
        combined = max(-1.0, min(1.0, combined))

        reasoning: list[str] = []
        for k, s in scores.items():
            reasoning.append(f"{k}={s:+.2f}")

        # Agreement check: need at least 2 primary signals (technical + 1 other) agreeing on direction
        primaries = {k: v for k, v in scores.items() if k in ("technical", "fundamental", "sentiment", "macro")}
        positive = sum(1 for v in primaries.values() if v > 0.1)
        negative = sum(1 for v in primaries.values() if v < -0.1)

        # Confidence: how strong is combined score + how many agents agree
        agreement_boost = 0
        if combined > 0 and positive >= 3: agreement_boost = 0.10
        elif combined > 0 and positive >= 2: agreement_boost = 0.05
        elif combined < 0 and negative >= 3: agreement_boost = 0.10
        elif combined < 0 and negative >= 2: agreement_boost = 0.05

        confidence = min(1.0, abs(combined) + agreement_boost)

        tech = scores.get("technical", 0)
        if combined >= self.min_confidence and positive >= 2 and tech > 0:
            action = "buy"
        elif combined <= -self.min_confidence and negative >= 2 and tech < 0:
            action = "sell_short"
        else:
            action = "hold"
            reasoning.append(
                f"below_threshold (|combined|={abs(combined):.2f} < {self.min_confidence:.2f} "
                f"or positive={positive}, negative={negative})"
            )

        return TradeDecision(
            symbol=symbol,
            action=action,
            confidence=confidence,
            combined_score=combined,
            signal_scores=scores,
            signal_details=signal_details or {},
            reasoning=reasoning,
        )

    def decide_exit(
        self,
        symbol: str,
        current_signal: TradeDecision,
        position_side: str,
    ) -> TradeDecision:
        """Evaluate whether to close an existing position."""
        if position_side == "long":
            if current_signal.combined_score < -0.2:
                current_signal.action = "close"
                current_signal.reasoning.append("long position with bearish combined signal")
        elif position_side == "short":
            if current_signal.combined_score > 0.2:
                current_signal.action = "close"
                current_signal.reasoning.append("short position with bullish combined signal")
        return current_signal
