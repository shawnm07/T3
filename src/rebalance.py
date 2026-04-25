"""AI-driven portfolio rebalance.

The Opus 4.7 portfolio arbiter is the SOLE authority on capital allocation.
This module is a thin executor: it converts the arbiter's `target_weights` +
`per_symbol` block into per-symbol delta actions. There is NO non-AI fallback,
NO post-AI override (no winner protection, no risk-grade veto, no underwater
dampener, no add/trim confidence floors). Every per-symbol entry is required
to carry `one_sentence_reason` and `opportunity_score` from the arbiter.
"""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config import Config

log = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).resolve().parents[1] / "data" / "state" / "held_tech_cache.json"


@dataclass
class RebalanceAction:
    symbol: str
    side: str                     # "buy" (add) or "sell" (trim/exit)
    delta_notional: float         # always positive
    current_notional: float
    target_notional: float
    tech_score: float
    unrealized_plpc: float
    reason: str
    # AI-arbiter-mandatory fields (validated upstream — present here)
    one_sentence_reason: str = ""
    opportunity_score: float = 0.0
    ai_action: str = ""           # raw arbiter action (BUY/SELL/HOLD/EXIT/INCREASE/REDUCE)
    ai_confidence: float = 0.0
    target_pct: float = 0.0
    target_qty: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol, "side": self.side,
            "delta_notional": round(self.delta_notional, 2),
            "current_notional": round(self.current_notional, 2),
            "target_notional": round(self.target_notional, 2),
            "tech_score": round(self.tech_score, 3),
            "unrealized_plpc": round(self.unrealized_plpc, 4),
            "reason": self.reason,
            "one_sentence_reason": self.one_sentence_reason,
            "opportunity_score": round(float(self.opportunity_score), 1),
            "ai_action": self.ai_action,
            "ai_confidence": round(float(self.ai_confidence), 3),
            "target_pct": round(float(self.target_pct), 4),
            "target_qty": (round(float(self.target_qty), 4)
                           if self.target_qty is not None else None),
        }


def load_tech_cache() -> dict[str, float]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_tech_cache(cache: dict[str, float]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2, default=str))


def select_ai_rerun_symbols(
    positions: list,
    tech_scores: dict[str, float],
    cache: dict[str, float],
    score_delta_threshold: float,
    max_reruns: int,
) -> list[str]:
    """Pick held symbols whose technical score has moved materially since the
    last cached scan (or are new to the cache). Capped at max_reruns.
    Preference: largest absolute deltas first.
    """
    candidates: list[tuple[str, float]] = []
    for p in positions:
        sym = p.symbol
        current = tech_scores.get(sym)
        if current is None:
            continue
        cached = cache.get(sym)
        if cached is None:
            candidates.append((sym, 1.0))
            continue
        delta = abs(current - cached)
        if delta >= score_delta_threshold:
            candidates.append((sym, delta))
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [sym for sym, _ in candidates[:max_reruns]]


def compute_rebalance_plan(
    positions: list,
    tech_map: dict,                       # symbol -> TechnicalSignal (informational only)
    sent_map: dict,                       # symbol -> SentimentSignal | None (unused, kept for API)
    numeric_decisions: dict,              # symbol -> TradeDecision (informational only)
    ai_verdicts: dict,                    # unused, kept for API compatibility
    equity: float,
    config: Config,
    cash_proxy_symbol: str | None = None,
    ai_target_weights: dict[str, float] | None = None,  # REQUIRED — None → no actions
    ai_per_symbol: dict[str, dict] | None = None,        # REQUIRED — None → no actions
) -> list[RebalanceAction]:
    """Translate the arbiter's targets into per-symbol delta actions.

    Hard rules:
      * AI is the sole authority. If `ai_target_weights` / `ai_per_symbol` are
        absent, return [] (no trades).
      * Every action carries `one_sentence_reason` + `opportunity_score` from
        the arbiter — these come back through to the journal and Telegram.
      * No deterministic post-filter (winner protection, risk-grade veto,
        underwater dampener, confidence floors) — those are pre-AI inputs, not
        post-AI overrides.
      * Action gates: `min_delta_pct` and `min_delta_usd` from config still
        apply (they are execution-cost floors, not opinion overrides).
    """
    if not bool(config.get("rebalance", "enabled", default=True)):
        return []
    if not ai_target_weights or not ai_per_symbol:
        log.warning(
            "compute_rebalance_plan: AI arbiter targets missing — returning "
            "no actions (no fallback)."
        )
        return []

    max_position_pct = float(config.get("risk", "max_position_pct", default=0.50))
    min_delta_pct = float(config.get("rebalance", "min_delta_pct", default=0.15))
    min_delta_usd = float(config.get("rebalance", "min_delta_usd", default=500))

    actions: list[RebalanceAction] = []
    for p in positions:
        sym = p.symbol
        if cash_proxy_symbol and sym == cash_proxy_symbol:
            continue
        if "/" in sym:
            continue
        is_long = (p.side.value == "long") if hasattr(p.side, "value") else (p.side == "long")
        plpc = float(p.unrealized_plpc) if hasattr(p, "unrealized_plpc") else 0.0
        current_notional = abs(float(p.market_value))
        tech = tech_map.get(sym)
        tech_score = float(tech.score) if tech else 0.0

        target_weight = ai_target_weights.get(sym)
        if target_weight is None:
            log.info("[%s] arbiter omitted target weight — holding", sym)
            continue
        target_weight = max(0.0, min(max_position_pct, float(target_weight)))

        info = ai_per_symbol.get(sym) or {}
        ai_action_raw = str(info.get("action", "")).upper()
        one_sentence = str(info.get("one_sentence_reason") or "").strip()
        try:
            opportunity_score = float(info.get("opportunity_score", 0) or 0)
        except (TypeError, ValueError):
            opportunity_score = 0.0
        try:
            ai_confidence = float(info.get("confidence", 0) or 0)
        except (TypeError, ValueError):
            ai_confidence = 0.0
        target_qty = info.get("target_qty")
        try:
            target_qty_f = float(target_qty) if target_qty is not None else None
        except (TypeError, ValueError):
            target_qty_f = None

        target_notional = target_weight * equity
        delta = target_notional - current_notional  # positive = ADD, negative = TRIM/EXIT
        abs_delta = abs(delta)

        # Execution-cost floors (NOT opinion overrides). EXIT (target=0) bypasses
        # the floors so the arbiter can always close a position.
        is_exit = ai_action_raw == "EXIT" or target_weight == 0.0
        if not is_exit:
            if abs_delta < min_delta_usd:
                continue
            if current_notional > 0 and (abs_delta / current_notional) < min_delta_pct:
                continue

        # On an EXIT we sell the entire current notional even if target_notional
        # rounds to a tiny residual.
        if is_exit and current_notional > 0:
            abs_delta = current_notional
            delta = -current_notional
            target_notional = 0.0

        if delta < 0:  # TRIM / EXIT
            side = "sell"
        else:  # ADD
            max_notional = equity * max_position_pct
            if current_notional >= max_notional and not is_exit:
                continue
            capped_delta = min(abs_delta, max_notional - current_notional)
            if capped_delta < min_delta_usd:
                continue
            abs_delta = capped_delta
            side = "buy" if is_long else "sell"

        if abs_delta <= 0:
            continue

        # Compose human-readable reason. The arbiter's `one_sentence_reason` is
        # always preserved verbatim alongside.
        if one_sentence:
            reason = (
                f"arbiter {ai_action_raw or ('add' if delta > 0 else 'trim')} "
                f"-> {target_weight*100:.1f}% (from {(current_notional/equity)*100:.1f}%): "
                f"{one_sentence}"
            )
        else:
            reason = (
                f"arbiter {ai_action_raw or ('add' if delta > 0 else 'trim')} "
                f"-> {target_weight*100:.1f}% (from {(current_notional/equity)*100:.1f}%)"
            )

        actions.append(RebalanceAction(
            symbol=sym, side=side, delta_notional=abs_delta,
            current_notional=current_notional, target_notional=target_notional,
            tech_score=tech_score, unrealized_plpc=plpc,
            reason=reason,
            one_sentence_reason=one_sentence,
            opportunity_score=opportunity_score,
            ai_action=ai_action_raw,
            ai_confidence=ai_confidence,
            target_pct=target_weight,
            target_qty=target_qty_f,
        ))

    # Trims/exits first, adds second — so freed cash funds adds.
    actions.sort(key=lambda a: 0 if a.side == "sell" and a.current_notional > a.target_notional else 1)
    return actions
