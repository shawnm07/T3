"""Conviction-weighted portfolio rebalance.

Each scan, held positions are re-scored (technical + sentiment, optionally AI).
Weak positions are trimmed toward their conviction-proportional target size;
strong positions are scaled up. Winners in profit are protected from trimming.
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
    side: str                     # "buy" (add) or "sell" (trim)
    delta_notional: float         # always positive
    current_notional: float
    target_notional: float
    blended_confidence: float
    tech_score: float
    unrealized_plpc: float
    reason: str
    ai_used: bool = False
    ai_grades: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol, "side": self.side,
            "delta_notional": round(self.delta_notional, 2),
            "current_notional": round(self.current_notional, 2),
            "target_notional": round(self.target_notional, 2),
            "blended_confidence": round(self.blended_confidence, 3),
            "tech_score": round(self.tech_score, 3),
            "unrealized_plpc": round(self.unrealized_plpc, 4),
            "reason": self.reason,
            "ai_used": self.ai_used,
            "ai_grades": self.ai_grades,
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
            # New to cache — always rerun
            candidates.append((sym, 1.0))
            continue
        delta = abs(current - cached)
        if delta >= score_delta_threshold:
            candidates.append((sym, delta))
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [sym for sym, _ in candidates[:max_reruns]]


def compute_rebalance_plan(
    positions: list,
    tech_map: dict,                       # symbol -> TechnicalSignal
    sent_map: dict,                       # symbol -> SentimentSignal | None
    numeric_decisions: dict,              # symbol -> TradeDecision (from DecisionEngine)
    ai_verdicts: dict,                    # symbol -> AIVerdict (subset, only AI-rerun'd)
    equity: float,
    config: Config,
    cash_proxy_symbol: str | None = None,
    ai_target_weights: dict[str, float] | None = None,  # symbol -> fraction of equity (from portfolio arbiter)
    ai_per_symbol: dict[str, dict] | None = None,        # symbol -> {action, rationale, ...}
) -> list[RebalanceAction]:
    """Build the list of partial buys/sells that move each position toward its
    conviction-proportional target. Does not execute — caller applies.
    """
    if not bool(config.get("rebalance", "enabled", default=True)):
        return []

    max_position_pct = float(config.get("risk", "max_position_pct", default=0.50))
    min_delta_pct = float(config.get("rebalance", "min_delta_pct", default=0.15))
    min_delta_usd = float(config.get("rebalance", "min_delta_usd", default=500))
    trim_floor = float(config.get("rebalance", "trim_confidence_floor", default=0.40))
    add_floor = float(config.get("rebalance", "add_confidence_floor", default=0.55))
    winner_threshold = float(config.get("rebalance", "winner_profit_threshold", default=0.03))
    ai_weight = float(config.get("ai", "weight", default=0.6))
    block_on_risk_reject = bool(config.get("rebalance", "block_on_risk_reject", default=True))
    concentration_k = float(config.get("rebalance", "concentration_k", default=2.0))
    use_ai_arbiter = ai_target_weights is not None and len(ai_target_weights) > 0
    underwater_plpc_thr = float(config.get("rebalance", "underwater_plpc_threshold", default=-0.005))
    underwater_cap_mult = float(config.get("rebalance", "underwater_add_cap_multiplier", default=1.25))

    # --- Pre-compute per-position conviction (used for fallback softmax and logging) ---
    convictions: dict[str, float] = {}
    tech_aligned_map: dict[str, float] = {}
    for p in positions:
        sym = p.symbol
        if cash_proxy_symbol and sym == cash_proxy_symbol:
            continue
        if "/" in sym:
            continue
        tech = tech_map.get(sym)
        if tech is None:
            continue
        is_long = (p.side.value == "long") if hasattr(p.side, "value") else (p.side == "long")
        tech_aligned = tech.score if is_long else -tech.score
        tech_aligned_map[sym] = tech_aligned
        numeric = numeric_decisions.get(sym)
        numeric_conf = 0.0
        if numeric is not None:
            num_aligned = (
                (is_long and numeric.combined_score > 0)
                or (not is_long and numeric.combined_score < 0)
            )
            numeric_conf = numeric.confidence if num_aligned else 0.0
        ai_v = ai_verdicts.get(sym)
        if ai_v is not None:
            ai_side_ok = (
                (is_long and ai_v.final_action == "buy")
                or (not is_long and ai_v.final_action == "sell_short")
                or ai_v.final_action == "pass"
            )
            ai_conf = ai_v.ai_confidence if ai_side_ok else 0.0
            if ai_v.final_action == "pass":
                ai_conf = min(ai_conf, 0.4)
            blended = ai_weight * ai_conf + (1 - ai_weight) * numeric_conf
        else:
            blended = numeric_conf
        if tech_aligned > 0.5:
            blended = max(blended, 0.4 + 0.4 * min(1.0, tech_aligned))
        convictions[sym] = max(0.0, min(1.0, blended))

    # --- Fallback softmax targets (only used when AI arbiter is absent) ---
    softmax_targets: dict[str, float] = {}
    if not use_ai_arbiter and convictions:
        # Raw weights ∝ conviction^k. Budget = 1 - cash_reserve.
        cash_reserve = float(config.get("risk", "cash_reserve_pct", default=0.05))
        budget = max(0.0, 1.0 - cash_reserve)
        raw = {s: (c ** concentration_k) for s, c in convictions.items() if c > 0}
        total = sum(raw.values())
        if total > 0:
            for s, r in raw.items():
                w = (r / total) * budget
                softmax_targets[s] = min(max_position_pct, w)

    actions: list[RebalanceAction] = []
    for p in positions:
        sym = p.symbol
        if cash_proxy_symbol and sym == cash_proxy_symbol:
            continue
        if "/" in sym:
            continue
        tech = tech_map.get(sym)
        if tech is None:
            continue
        is_long = (p.side.value == "long") if hasattr(p.side, "value") else (p.side == "long")
        plpc = float(p.unrealized_plpc) if hasattr(p, "unrealized_plpc") else 0.0
        current_notional = abs(float(p.market_value))
        blended = convictions.get(sym, 0.0)
        tech_aligned = tech_aligned_map.get(sym, 0.0)
        ai_v = ai_verdicts.get(sym)
        ai_used = ai_v is not None
        ai_grades = (ai_v.agent_grades or {}) if ai_used else {}

        # --- Determine target weight ---
        ai_rationale = ""
        ai_action_hint = ""
        if use_ai_arbiter:
            target_weight = ai_target_weights.get(sym)
            if target_weight is None:
                # AI didn't name this symbol — leave it alone (conservative).
                log.info("[%s] arbiter did not set target weight — holding", sym)
                continue
            target_weight = max(0.0, min(max_position_pct, float(target_weight)))
            if ai_per_symbol and sym in ai_per_symbol:
                info = ai_per_symbol[sym] or {}
                ai_rationale = str(info.get("rationale", ""))[:200]
                ai_action_hint = str(info.get("action", ""))
        else:
            target_weight = softmax_targets.get(sym, 0.0)

        target_notional = target_weight * equity
        delta = target_notional - current_notional  # positive = ADD, negative = TRIM
        abs_delta = abs(delta)
        if abs_delta < min_delta_usd:
            continue
        if current_notional > 0 and (abs_delta / current_notional) < min_delta_pct:
            continue

        if delta < 0:  # TRIM
            if use_ai_arbiter:
                reason = (
                    f"arbiter trim -> {target_weight*100:.1f}% "
                    f"(from {(current_notional/equity)*100:.1f}%): {ai_rationale}"
                    if ai_rationale else
                    f"arbiter trim -> {target_weight*100:.1f}%"
                )
            else:
                if plpc > winner_threshold and tech_aligned > 0:
                    log.info("[%s] winner-protected: pnl=%+.1f%% tech=%+.2f — skip trim",
                             sym, plpc * 100, tech_aligned)
                    continue
                if blended >= trim_floor:
                    continue
                reason = (
                    f"trim -> {target_weight*100:.1f}% (conf={blended:.2f}, "
                    f"tech={tech_aligned:+.2f}, pnl={plpc:+.1%})"
                )
            actions.append(RebalanceAction(
                symbol=sym, side="sell", delta_notional=abs_delta,
                current_notional=current_notional, target_notional=target_notional,
                blended_confidence=blended, tech_score=tech.score,
                unrealized_plpc=plpc, reason=reason,
                ai_used=ai_used or use_ai_arbiter, ai_grades=ai_grades,
            ))
        else:  # ADD
            if not use_ai_arbiter:
                if blended < add_floor:
                    continue
                if block_on_risk_reject and ai_used:
                    risk_grade = (ai_grades.get("risk") or ai_grades.get("risk_manager") or "").strip().lower()
                    if risk_grade in ("reject", "f", "fail", "d", "d-"):
                        log.info("[%s] rebalance add blocked: AI risk grade=%s", sym, risk_grade)
                        continue
            # Underwater dampener: cap growth when position is in a loss to avoid
            # doubling down on names the market is rejecting.
            if plpc < underwater_plpc_thr:
                max_add = current_notional * (underwater_cap_mult - 1.0)
                if abs_delta > max_add:
                    log.info("[%s] underwater add dampened: pnl=%+.1f%% capping add at $%.0f (was $%.0f)",
                             sym, plpc * 100, max_add, abs_delta)
                    delta = min(delta, max_add)
                    abs_delta = delta
                    if abs_delta < min_delta_usd:
                        continue
            max_notional = equity * max_position_pct
            if current_notional >= max_notional:
                continue
            capped_delta = min(abs_delta, max_notional - current_notional)
            if capped_delta < min_delta_usd:
                continue
            if use_ai_arbiter:
                reason = (
                    f"arbiter add -> {target_weight*100:.1f}% "
                    f"(from {(current_notional/equity)*100:.1f}%): {ai_rationale}"
                    if ai_rationale else
                    f"arbiter add -> {target_weight*100:.1f}%"
                )
            else:
                reason = (
                    f"add -> {target_weight*100:.1f}% (conf={blended:.2f}, "
                    f"tech={tech_aligned:+.2f}, pnl={plpc:+.1%})"
                )
            side = "buy" if is_long else "sell"
            actions.append(RebalanceAction(
                symbol=sym, side=side, delta_notional=capped_delta,
                current_notional=current_notional, target_notional=target_notional,
                blended_confidence=blended, tech_score=tech.score,
                unrealized_plpc=plpc, reason=reason,
                ai_used=ai_used or use_ai_arbiter, ai_grades=ai_grades,
            ))

    # Trims first, adds second — so freed cash (or SPY sale) funds adds.
    actions.sort(key=lambda a: 0 if a.side == "sell" and a.current_notional > a.target_notional else 1)
    return actions
