"""AI pipeline: for each top candidate, run analyst agents in parallel, then arbiter.

Inputs come from the numeric pipeline (technicals, fundamentals, sentiment, macro).
Output is a final {action, confidence, thesis, exit_conditions} dict that the
orchestrator blends with the numeric score.
"""
from __future__ import annotations
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from src.ai_research import AIResearcher
from src.config import Config
from src.decision import TradeDecision

log = logging.getLogger(__name__)


@dataclass
class AIVerdict:
    symbol: str
    final_action: str            # "buy" | "pass"
    ai_confidence: float         # 0..1
    agent_grades: dict[str, str] = field(default_factory=dict)
    thesis: str = ""
    exit_conditions: list[str] = field(default_factory=list)
    disagreements: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    raw_outputs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "final_action": self.final_action,
            "ai_confidence": round(self.ai_confidence, 3),
            "agent_grades": self.agent_grades,
            "thesis": self.thesis,
            "exit_conditions": self.exit_conditions,
            "disagreements": self.disagreements,
            "errors": self.errors,
        }


def _truncate_headlines(headlines: list[str], limit: int = 8) -> list[str]:
    return [h for h in headlines if h][:limit]


class AIPipeline:
    def __init__(self, config: Config, researcher: AIResearcher | None = None):
        self.cfg = config
        self.ai = researcher or AIResearcher(config)

    async def analyze_candidate(
        self,
        symbol: str,
        numeric_decision: TradeDecision,
        macro_ctx: dict[str, Any],
        portfolio_ctx: dict[str, Any],
    ) -> AIVerdict:
        """Run technical + fundamental + sentiment agents in parallel, then arbiter."""
        details = numeric_decision.signal_details or {}
        technical = details.get("technical", {})
        fundamental = details.get("fundamental", {})
        sentiment = details.get("sentiment", {})

        tech_ctx = {
            "symbol": symbol,
            "direction_hypothesis": "long" if numeric_decision.combined_score > 0 else "none",
            "technical_numbers": technical,
            "macro_backdrop": {
                "regime": macro_ctx.get("regime"),
                "score": macro_ctx.get("score"),
                "notes": macro_ctx.get("notes", []),
            },
        }
        fund_ctx = {
            "symbol": symbol,
            "fundamentals_numbers": fundamental or {"note": "yfinance returned no data"},
            "direction_hypothesis": tech_ctx["direction_hypothesis"],
        }
        sent_ctx = {
            "symbol": symbol,
            "sentiment_numbers": {
                "score": sentiment.get("score"),
                "article_count": sentiment.get("article_count"),
                "positive_hits": sentiment.get("positive_hits"),
                "negative_hits": sentiment.get("negative_hits"),
            },
            "recent_headlines": _truncate_headlines(sentiment.get("top_headlines", []), 8),
        }

        # Analyst agents use Haiku (fast, cheap); arbiter uses Sonnet (full reasoning).
        haiku = self.ai.haiku_model
        parallel = self.cfg.get("ai", "parallel_analyst_calls", default=True)
        if parallel:
            tech_task = self.ai.call_agent("technical-analyst", tech_ctx, model=haiku)
            fund_task = self.ai.call_agent("fundamental-analyst", fund_ctx, model=haiku)
            sent_task = self.ai.call_agent("sentiment-analyst", sent_ctx, model=haiku)
            tech_out, fund_out, sent_out = await asyncio.gather(
                tech_task, fund_task, sent_task, return_exceptions=True
            )
        else:
            tech_out = await self.ai.call_agent("technical-analyst", tech_ctx, model=haiku)
            fund_out = await self.ai.call_agent("fundamental-analyst", fund_ctx, model=haiku)
            sent_out = await self.ai.call_agent("sentiment-analyst", sent_ctx, model=haiku)

        errors: list[str] = []
        outputs = {}
        for name, out in (("technical", tech_out), ("fundamental", fund_out), ("sentiment", sent_out)):
            if isinstance(out, Exception):
                errors.append(f"{name}: {out}")
                outputs[name] = {"_error": str(out)}
            elif isinstance(out, dict) and out.get("_error"):
                errors.append(f"{name}: {out['_error']}")
                outputs[name] = out
            else:
                outputs[name] = out

        arbiter_ctx = {
            "symbol": symbol,
            "numeric_decision": numeric_decision.to_dict(),
            "technical_analyst": outputs["technical"],
            "fundamental_analyst": outputs["fundamental"],
            "sentiment_analyst": outputs["sentiment"],
            "macro": macro_ctx,
            "portfolio": portfolio_ctx,
        }
        # decision-arbiter is the FINAL trade-critical decision for entries.
        # Model is forced to Opus 4.7 inside call_agent (trade-critical gate).
        arbiter_out = await self.ai.call_agent(
            "decision-arbiter", arbiter_ctx, task_type="trade_critical",
        )
        if isinstance(arbiter_out, dict) and arbiter_out.get("_error"):
            errors.append(f"arbiter: {arbiter_out['_error']}")

        # Extract final verdict from arbiter
        final_action = (arbiter_out or {}).get("final_action", "pass")
        if final_action not in ("buy", "pass"):
            final_action = "pass"
        ai_confidence = float((arbiter_out or {}).get("confidence", 0.0) or 0.0)
        agent_grades = (arbiter_out or {}).get("agent_grades", {}) or {}
        thesis = (arbiter_out or {}).get("thesis", "") or ""
        exits = (arbiter_out or {}).get("exit_conditions", []) or []
        disagreements = (arbiter_out or {}).get("disagreements", []) or []

        return AIVerdict(
            symbol=symbol,
            final_action=final_action,
            ai_confidence=ai_confidence,
            agent_grades=agent_grades,
            thesis=thesis,
            exit_conditions=exits if isinstance(exits, list) else [str(exits)],
            disagreements=disagreements if isinstance(disagreements, list) else [str(disagreements)],
            errors=errors,
            raw_outputs=outputs | {"arbiter": arbiter_out},
        )

    async def portfolio_rebalance_arbiter(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """One AI call for the entire portfolio rebalance. Returns:
        {
          "portfolio_thesis": str,
          "cash_target_pct": float,
          "target_weights": {symbol: weight_fraction, ...},
          "per_symbol": {symbol: {target_pct, action, conviction, rationale}, ...},
          "risk_flags": [str, ...],
          "_error": str (on failure)
        }
        """
        return await self.ai.call_agent(
            "portfolio-arbiter", context, task_type="trade_critical",
        )

    async def portfolio_selector(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """One AI call to select 3-6 positions from a unified candidate pool.

        Replaces the two-pipeline split (portfolio-arbiter + decision-arbiter).
        Returns the JSON contract documented in
        ``.claude/agents/portfolio-selector.md`` — selected_positions,
        target_weights, per_symbol, candidate_rankings, rotation_plan,
        exhaustion_penalty_applied, etc.
        """
        return await self.ai.call_agent(
            "portfolio-selector", context, task_type="trade_critical",
        )

    async def portfolio_verifier(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Sonnet post-execution reconciler. Compares actual portfolio to
        Opus's targets and proposes corrective trades. Bypasses the trade-
        critical Opus rule because the verifier can only ENFORCE existing
        Opus decisions, not originate them. Returns:
          { "verifier_thesis": str,
            "corrective_trades": [{symbol, side, delta_qty, ...}, ...],
            "skipped": [{symbol, reason}, ...] }
        """
        return await self.ai.call_agent("portfolio-verifier", context)

    async def earnings_gate_verdict(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Decide close / trim_50 / hold for a single position entering earnings window."""
        return await self.ai.call_agent(
            "earnings-gate", context, task_type="trade_critical",
        )

    async def portfolio_risk_check(
        self,
        portfolio_ctx: dict[str, Any],
        proposed_trades: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Ask risk-manager agent to review the proposed book."""
        ctx = {
            "portfolio": portfolio_ctx,
            "proposed_trades": proposed_trades,
        }
        return await self.ai.call_agent(
            "risk-manager", ctx, task_type="trade_critical",
        )

    async def exit_arbiter_verdict(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Ask Opus 4.7 whether to close / reduce / hold a specific open position.
        ALL exits (including stall, technical-flip, bad-news, and preclose)
        must route through this. Returns:
          { "action": "exit" | "reduce" | "hold",
            "confidence": 0..1, "reasoning": str,
            "size_fraction": 0..1 (if action=reduce) }
        """
        return await self.ai.call_agent(
            "exit-arbiter", context, task_type="trade_critical",
        )


_REQUIRED_PER_SYMBOL_FIELDS = (
    "target_pct", "action", "opportunity_score", "one_sentence_reason",
)
_REQUIRED_SPY_FIELDS = (
    "target_pct", "action", "opportunity_score", "one_sentence_reason",
)
_VALID_ACTIONS = {"BUY", "SELL", "HOLD", "EXIT", "INCREASE", "REDUCE"}


def _hard_stop_loss_pct(cfg: Config) -> float:
    try:
        return max(0.0, float(cfg.get("risk", "hard_stop_loss_pct", default=0.01)))
    except (TypeError, ValueError):
        return 0.01


def validate_arbiter_response(
    result: dict[str, Any] | None,
    held_symbols: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """Validate that the arbiter response carries every field the executor
    needs. Returns (is_valid, list_of_problems). The bot rejects the response
    on ANY problem and executes NO trades.
    """
    problems: list[str] = []
    if not isinstance(result, dict) or result.get("_error"):
        return False, [f"non-dict or error: {(result or {}).get('_error') if isinstance(result, dict) else type(result).__name__}"]

    if "spy_target_pct" not in result:
        problems.append("missing spy_target_pct")
    if "cash_target_pct" not in result:
        problems.append("missing cash_target_pct")

    spy_dec = result.get("spy_decision")
    if not isinstance(spy_dec, dict):
        problems.append("missing spy_decision")
    else:
        for f in _REQUIRED_SPY_FIELDS:
            if f not in spy_dec or spy_dec[f] in (None, ""):
                problems.append(f"spy_decision.{f} missing")

    target_weights = result.get("target_weights")
    if not isinstance(target_weights, dict):
        problems.append("target_weights missing or not a dict")
        target_weights = {}

    per_symbol = result.get("per_symbol")
    if not isinstance(per_symbol, dict):
        problems.append("per_symbol missing or not a dict")
        per_symbol = {}

    ranking = result.get("opportunity_ranking")
    if not isinstance(ranking, list):
        problems.append("opportunity_ranking missing or not a list")

    held = set(held_symbols or [])
    # Every held symbol must show up in target_weights, per_symbol, ranking
    for sym in held:
        if sym not in target_weights:
            problems.append(f"target_weights missing held symbol {sym}")
        info = per_symbol.get(sym) if isinstance(per_symbol, dict) else None
        if not isinstance(info, dict):
            problems.append(f"per_symbol missing held symbol {sym}")
            continue
        for f in _REQUIRED_PER_SYMBOL_FIELDS:
            if f not in info or info[f] in (None, ""):
                problems.append(f"per_symbol[{sym}].{f} missing")
        action = str(info.get("action", "")).upper()
        if action and action not in _VALID_ACTIONS:
            problems.append(f"per_symbol[{sym}].action invalid ({action!r})")
        # Sanitize: replace any semicolons with periods (style guide says "exactly
        # one sentence, no semicolons stitching"). Mutates result in place so the
        # downstream consumer sees the cleaned string. Not worth burning a retry on.
        reason = info.get("one_sentence_reason", "")
        if isinstance(reason, str) and ";" in reason:
            info["one_sentence_reason"] = reason.replace(";", ".")

    # Numeric sanity: weights sum + spy + cash ∈ [0.99, 1.01].
    # Auto-repair when slightly off: Opus often leaves a few percent unallocated
    # (e.g. weights=0.95, spy=0, cash=0). Treat the gap as implicit cash —
    # Opus chose not to deploy it, which IS a cash decision. Mutates result so
    # downstream sees the repaired values. Only reject if grossly malformed.
    try:
        weight_sum = sum(float(v) for v in target_weights.values())
        spy_t = float(result.get("spy_target_pct", 0) or 0)
        cash_t = float(result.get("cash_target_pct", 0) or 0)
        total = weight_sum + spy_t + cash_t
        if 0.85 <= total < 0.99:
            # Under-allocated: park the missing slice in cash.
            gap = round(1.0 - total, 4)
            new_cash = round(cash_t + gap, 4)
            log.info(
                "Arbiter weight-sum auto-repair: total=%.3f → adding %.3f to cash "
                "(was %.3f → %.3f), weights+spy untouched.",
                total, gap, cash_t, new_cash,
            )
            result["cash_target_pct"] = new_cash
            result["_auto_repaired"] = {"action": "padded_cash", "gap": gap, "original_total": round(total, 4)}
        elif 1.01 < total <= 1.15:
            # Over-allocated: scale weights down proportionally to make total = 1.
            # SPY/cash kept fixed (they're explicit reserve choices); weights absorb the cut.
            scale = (1.0 - spy_t - cash_t) / weight_sum if weight_sum > 0 else 1.0
            if scale > 0:
                result["target_weights"] = {
                    s: round(float(v) * scale, 4) for s, v in target_weights.items()
                }
                log.info(
                    "Arbiter weight-sum auto-repair: total=%.3f → scaled weights by %.4f "
                    "to fit (spy=%.3f cash=%.3f untouched).",
                    total, scale, spy_t, cash_t,
                )
                result["_auto_repaired"] = {"action": "scaled_weights", "scale": round(scale, 4),
                                            "original_total": round(total, 4)}
            else:
                problems.append(f"weights+spy+cash sum out of bounds: {total:.3f} (cannot scale)")
        elif not (0.99 <= total <= 1.01):
            problems.append(f"weights+spy+cash sum out of bounds: {total:.3f} (outside repair band 0.85–1.15)")
    except (TypeError, ValueError):
        problems.append("weights/spy/cash not numeric")

    return (len(problems) == 0), problems


def run_portfolio_arbiter(
    config: Config,
    context: dict[str, Any],
    held_symbols: list[str] | None = None,
    max_attempts: int = 3,
) -> dict[str, Any] | None:
    """Synchronous entry point for the portfolio rebalance arbiter.

    Hard rule: the bot has NO non-AI fallback. We retry with exponential
    backoff and validate the response. If every attempt fails or every
    response is incomplete, return None — the caller MUST treat None as
    'execute no trades this scan'.
    """
    ai = AIResearcher(config)
    if not ai.available():
        log.critical(
            "PORTFOLIO ARBITER: AI unavailable (enabled=%s, key=%s) — "
            "no rebalance trades will execute (fail-safe)",
            ai.enabled, bool(ai.api_key),
        )
        return None

    pipeline = AIPipeline(config, ai)
    last_error: str = ""
    last_problems: list[str] = []
    for attempt in range(1, max_attempts + 1):
        try:
            result = asyncio.run(pipeline.portfolio_rebalance_arbiter(context))
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            log.warning(
                "PORTFOLIO ARBITER attempt %d/%d raised: %s",
                attempt, max_attempts, last_error,
            )
            result = None

        if isinstance(result, dict) and not result.get("_error"):
            ok, problems = validate_arbiter_response(result, held_symbols)
            if ok:
                if attempt > 1:
                    log.info("PORTFOLIO ARBITER succeeded on attempt %d/%d", attempt, max_attempts)
                return result
            last_problems = problems
            log.warning(
                "PORTFOLIO ARBITER attempt %d/%d returned incomplete response: %s",
                attempt, max_attempts, problems[:5],
            )
        elif isinstance(result, dict):
            last_error = str(result.get("_error", "unknown"))
            log.warning(
                "PORTFOLIO ARBITER attempt %d/%d returned error: %s",
                attempt, max_attempts, last_error,
            )

        if attempt < max_attempts:
            backoff = 2 ** attempt  # 2s, 4s, 8s ...
            log.info("PORTFOLIO ARBITER retrying in %ds", backoff)
            time.sleep(backoff)

    log.critical(
        "PORTFOLIO ARBITER FAILED after %d attempts — NO trades will execute "
        "this scan (last_error=%s, last_validation_problems=%s)",
        max_attempts, last_error, last_problems[:5],
    )
    try:
        from src.journal import log_decision
        log_decision({
            "event": "ai_failure",
            "agent": "portfolio-arbiter",
            "attempts": max_attempts,
            "last_error": last_error,
            "last_problems": last_problems,
        })
    except Exception:
        pass
    return None


# --------------------------------------------------------------------------- #
#  Portfolio selector (Phase 3+) — unified 3-6 selector validator + runner    #
# --------------------------------------------------------------------------- #


_SELECTOR_VALID_ACTIONS = {"BUY", "INCREASE", "HOLD", "REDUCE", "EXIT", "PASS"}
_SELECTOR_EXIT_REASON_CATS = {
    "replaced_by_higher_opportunity",
    "removed_due_to_exhaustion",
    "removed_due_to_weak_continuation",
    "floor_breach",
    "earnings_proximity",
    "other",
}
_SELECTOR_ENTRY_REASON_CATS = {
    "stronger_remaining_upside",
    "breakout_continuation",
    "anti_stagnation_inclusion",
    "other",
}


def validate_selector_response(
    result: dict[str, Any] | None,
    held_symbols: list[str],
    pool_symbols: list[str],
    pool_meta: dict[str, dict[str, Any]],
    cfg: Config,
    allow_floor_breach: bool,
    equity: float | None = None,
) -> tuple[bool, list[str]]:
    """Validate the portfolio-selector response against the strict 3-6 contract.

    ``pool_meta`` maps symbol → {"currently_held": bool, ...} so anti-stagnation
    can be enforced without depending on the model's own ``currently_held``
    flagging being correct.

    Returns ``(ok, problems)``. The bot rejects on ANY problem — no auto-repair.
    """
    problems: list[str] = []
    if not isinstance(result, dict) or result.get("_error"):
        err = (result or {}).get("_error") if isinstance(result, dict) else type(result).__name__
        return False, [f"non-dict or error: {err}"]

    selected = result.get("selected_positions") or []
    target_w = result.get("target_weights") or {}
    per_sym = result.get("per_symbol") or {}
    rankings = result.get("candidate_rankings") or []

    min_pos = 0 if allow_floor_breach else int(cfg.get("selector", "min_positions", default=3))
    max_pos = int(cfg.get("selector", "max_positions", default=6))
    max_pp = float(cfg.get("risk", "max_position_pct", default=0.50))

    if not isinstance(selected, list):
        problems.append(f"selected_positions not a list: {type(selected).__name__}")
        selected = []
    if not (min_pos <= len(selected) <= max_pos):
        problems.append(f"selected count {len(selected)} not in [{min_pos},{max_pos}]")
    if len(set(selected)) != len(selected):
        problems.append("duplicates in selected_positions")
    pool_set = set(pool_symbols)
    for s in selected:
        if s not in pool_set:
            problems.append(f"selected {s} not in candidate pool")

    if not isinstance(target_w, dict):
        problems.append("target_weights not a dict")
        target_w = {}
    if set(target_w.keys()) != set(selected):
        missing = set(selected) - set(target_w.keys())
        extra = set(target_w.keys()) - set(selected)
        if missing:
            problems.append(f"target_weights missing {sorted(missing)}")
        if extra:
            problems.append(f"target_weights has non-selected {sorted(extra)}")
    for s, w in target_w.items():
        try:
            wf = float(w)
        except (TypeError, ValueError):
            problems.append(f"weight {s} not numeric: {w!r}")
            continue
        if not (0 < wf <= max_pp):
            problems.append(f"weight {s}={wf:.4f} out of (0, {max_pp}]")

    # AI-direct order params: qty / entry_price / delta_qty are authoritative.
    # Python owns the protective stop and attaches a hard 1% stop-market order
    # at execution time, so stop_loss / take_profit are optional AI commentary.
    equity_for_check = 0.0
    try:
        equity_for_check = float(equity or 0)
    except (TypeError, ValueError):
        equity_for_check = 0.0
    if equity_for_check <= 0:
        try:
            equity_for_check = float(cfg.get("account", "equity_hint", default=0) or 0)
        except (TypeError, ValueError):
            equity_for_check = 0.0
    max_risk_pct = float(cfg.get("risk", "max_risk_per_trade_pct", default=0.005))
    hard_stop_pct = _hard_stop_loss_pct(cfg)
    for s in selected:
        info = per_sym.get(s) if isinstance(per_sym, dict) else None
        if not isinstance(info, dict):
            continue  # missing-per-symbol problem already recorded above
        for f in ("qty", "entry_price", "delta_qty"):
            if f not in info:
                problems.append(f"per_symbol[{s}].{f} missing (AI-direct sizing required)")
        try:
            qty = float(info.get("qty", 0) or 0)
            entry = float(info.get("entry_price", 0) or 0)
            delta_qty = float(info.get("delta_qty", 0) or 0)
        except (TypeError, ValueError):
            problems.append(f"per_symbol[{s}] qty/entry/delta_qty not numeric")
            continue
        if qty <= 0:
            problems.append(f"per_symbol[{s}].qty must be > 0 for selected positions, got {qty}")
        if entry <= 0:
            problems.append(f"per_symbol[{s}].entry_price must be > 0, got {entry}")
        raw_stop = info.get("stop_loss")
        if raw_stop not in (None, ""):
            try:
                stop = float(raw_stop)
            except (TypeError, ValueError):
                problems.append(f"per_symbol[{s}].stop_loss not numeric")
            else:
                if stop <= 0 or stop >= entry:
                    problems.append(f"per_symbol[{s}].stop_loss ({stop}) must be > 0 and < entry_price ({entry})")
        raw_target = info.get("take_profit")
        if raw_target not in (None, ""):
            try:
                target = float(raw_target)
            except (TypeError, ValueError):
                problems.append(f"per_symbol[{s}].take_profit not numeric")
            else:
                if target <= 0 or target <= entry:
                    problems.append(f"per_symbol[{s}].take_profit ({target}) must be > entry_price ({entry})")
        meta = pool_meta.get(s, {}) if isinstance(pool_meta, dict) else {}
        try:
            current_qty = float(meta.get("current_qty", 0) or 0)
        except (TypeError, ValueError):
            current_qty = 0.0
        expected_delta = qty - current_qty
        if abs(delta_qty - expected_delta) > 0.01:
            problems.append(
                f"per_symbol[{s}].delta_qty {delta_qty} inconsistent with "
                f"qty {qty} minus current_qty {current_qty}"
            )
        # Risk-per-trade hard cap (use a contextual equity if provided)
        if entry > 0 and hard_stop_pct > 0:
            ctx_equity = 0.0
            ctx = info.get("_equity_for_validation")
            try:
                ctx_equity = float(ctx) if ctx is not None else equity_for_check
            except (TypeError, ValueError):
                ctx_equity = equity_for_check
            if ctx_equity > 0:
                stop = entry * (1.0 - hard_stop_pct)
                risk_usd = qty * (entry - stop)
                cap_usd = ctx_equity * max_risk_pct
                # 1% slack over the configured cap before rejecting.
                if risk_usd > cap_usd * 1.01:
                    problems.append(
                        f"per_symbol[{s}] risk ${risk_usd:.0f} exceeds "
                        f"max_risk_per_trade ${cap_usd:.0f}"
                    )

    try:
        spy_t = float(result.get("spy_target_pct", 0) or 0)
        cash_t = float(result.get("cash_target_pct", 0) or 0)
        wsum = sum(float(v) for v in target_w.values())
        total = wsum + spy_t + cash_t
        if not (0.99 <= total <= 1.01):
            problems.append(f"weights+spy+cash sum {total:.3f} outside [0.99, 1.01]")
    except (TypeError, ValueError):
        problems.append("weights/spy/cash not numeric")
        spy_t, cash_t = 0.0, 0.0

    spy_dec = result.get("spy_decision")
    if not isinstance(spy_dec, dict):
        problems.append("missing spy_decision")
    else:
        for f in ("target_pct", "action", "opportunity_score", "one_sentence_reason"):
            if f not in spy_dec or spy_dec[f] in (None, ""):
                problems.append(f"spy_decision.{f} missing")

    if not isinstance(per_sym, dict):
        problems.append("per_symbol not a dict")
        per_sym = {}

    for s in held_symbols:
        if s not in selected:
            info = per_sym.get(s) if isinstance(per_sym, dict) else None
            if not isinstance(info, dict):
                problems.append(f"held {s} not selected and missing per_symbol entry")
                continue
            tp_raw = info.get("target_pct")
            if tp_raw is None:
                tp = None
            else:
                try:
                    tp = float(tp_raw)
                except (TypeError, ValueError):
                    tp = None
            action = str(info.get("action", "")).upper()
            if tp != 0.0 or action != "EXIT":
                problems.append(f"held {s} not selected but per_symbol.action={action!r} target_pct={tp}")
            # EXIT must have qty=0 and a non-positive delta_qty (to flatten the position).
            try:
                qty_exit = float(info.get("qty", 0) or 0)
            except (TypeError, ValueError):
                qty_exit = -1.0
            if qty_exit != 0:
                problems.append(f"held {s} EXIT requires qty=0, got {qty_exit}")
            if "delta_qty" in info:
                try:
                    dq = float(info.get("delta_qty", 0) or 0)
                except (TypeError, ValueError):
                    dq = 1.0
                if dq > 0:
                    problems.append(f"held {s} EXIT delta_qty must be <= 0, got {dq}")
                try:
                    current_qty = float((pool_meta.get(s, {}) or {}).get("current_qty", 0) or 0)
                except (TypeError, ValueError):
                    current_qty = 0.0
                if current_qty > 0 and abs(dq + current_qty) > 0.01:
                    problems.append(
                        f"held {s} EXIT delta_qty must equal -current_qty "
                        f"({-current_qty}), got {dq}"
                    )
            else:
                problems.append(f"held {s} EXIT missing delta_qty")

    missing_per_sym = [s for s in pool_symbols if s not in per_sym]
    if missing_per_sym:
        problems.append(f"per_symbol missing {len(missing_per_sym)} symbols: {missing_per_sym[:5]}")
    for s, info in per_sym.items() if isinstance(per_sym, dict) else []:
        if not isinstance(info, dict):
            problems.append(f"per_symbol[{s}] not a dict")
            continue
        for f in ("target_pct", "action", "opportunity_score", "one_sentence_reason",
                  "exhaustion_penalty", "remaining_upside_score"):
            if f not in info:
                problems.append(f"per_symbol[{s}].{f} missing")
        action = str(info.get("action", "")).upper()
        if action and action not in _SELECTOR_VALID_ACTIONS:
            problems.append(f"per_symbol[{s}].action invalid: {action!r}")
        reason = info.get("one_sentence_reason", "")
        if isinstance(reason, str) and ";" in reason:
            info["one_sentence_reason"] = reason.replace(";", ".")

    if not isinstance(rankings, list):
        problems.append("candidate_rankings not a list")
    else:
        ranked_syms = {r.get("symbol") for r in rankings if isinstance(r, dict)}
        missing_rank = pool_set - ranked_syms
        extra_rank = ranked_syms - pool_set
        if missing_rank:
            problems.append(f"candidate_rankings missing {len(missing_rank)} symbols: {sorted(missing_rank)[:5]}")
        if extra_rank:
            problems.append(f"candidate_rankings has non-pool symbols: {sorted(extra_rank)[:5]}")

    # Anti-stagnation enforcement
    if not allow_floor_breach and selected:
        scores: dict[str, float] = {}
        for r in rankings if isinstance(rankings, list) else []:
            if isinstance(r, dict):
                try:
                    scores[r.get("symbol", "")] = float(r.get("opportunity_score", 0) or 0)
                except (TypeError, ValueError):
                    continue
        new_in_pool = [s for s in pool_symbols if not pool_meta.get(s, {}).get("currently_held", False)]
        new_in_selected = [s for s in selected if not pool_meta.get(s, {}).get("currently_held", False)]
        if selected:
            lowest_selected = min(scores.get(s, 0.0) for s in selected)
        else:
            lowest_selected = 0.0
        viable_new = [s for s in new_in_pool if scores.get(s, 0.0) >= (lowest_selected - 5.0)]
        if viable_new and not new_in_selected:
            problems.append(
                f"Selection failed to incorporate new opportunities despite "
                f"viable candidates: {viable_new[:5]}"
            )

    if "exhaustion_penalty_applied" not in result:
        problems.append("exhaustion_penalty_applied missing")
    elif not isinstance(result.get("exhaustion_penalty_applied"), list):
        problems.append("exhaustion_penalty_applied not a list")

    rp = result.get("rotation_plan") or {}
    if isinstance(rp, dict):
        for entry in rp.get("exited", []) or []:
            if not isinstance(entry, dict):
                continue
            cat = entry.get("reason_category")
            if cat is not None and cat not in _SELECTOR_EXIT_REASON_CATS:
                problems.append(f"rotation_plan.exited[{entry.get('symbol')}] bad reason_category: {cat!r}")
        for entry in rp.get("entered", []) or []:
            if not isinstance(entry, dict):
                continue
            cat = entry.get("reason_category")
            if cat is not None and cat not in _SELECTOR_ENTRY_REASON_CATS:
                problems.append(f"rotation_plan.entered[{entry.get('symbol')}] bad reason_category: {cat!r}")

    return (len(problems) == 0), problems


def _selector_problems_are_retryable(problems: list[str]) -> bool:
    """True when problems are exclusively count/range OR anti-stagnation —
    these are worth a feedback-prompted retry. Other problems (missing
    fields, malformed JSON) usually indicate the model went off-contract
    and aren't fixable by re-prompting."""
    if not problems:
        return False
    keywords = ("selected count", "duplicates in selected_positions",
                "incorporate new opportunities")
    return all(any(kw in p for kw in keywords) for p in problems)


def run_portfolio_selector(
    config: Config,
    context: dict[str, Any],
    pool_symbols: list[str],
    pool_meta: dict[str, dict[str, Any]],
    held_symbols: list[str],
    allow_floor_breach: bool = False,
    max_attempts: int = 3,
) -> dict[str, Any] | None:
    """Synchronous entry point for the unified portfolio selector.

    Hard rule (matches portfolio-arbiter): NO non-AI fallback. Retry with
    exponential backoff and validate the response. If every attempt fails
    or returns invalid, return None — caller MUST treat None as
    'execute no trades this scan, leave positions untouched'.

    On count/range or anti-stagnation validation failure, one extra
    feedback-prompted retry is attempted before giving up (controlled by
    ``selector.retry_validation_failures``).
    """
    ai = AIResearcher(config)
    if not ai.available():
        log.critical(
            "PORTFOLIO SELECTOR: AI unavailable (enabled=%s, key=%s) — "
            "no trades will execute (fail-safe)",
            ai.enabled, bool(ai.api_key),
        )
        return None

    pipeline = AIPipeline(config, ai)
    extra_retries_allowed = int(config.get("selector", "retry_validation_failures", default=1) or 0)
    extra_retries_used = 0
    last_error: str = ""
    last_problems: list[str] = []

    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            result = asyncio.run(pipeline.portfolio_selector(context))
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            log.warning("PORTFOLIO SELECTOR attempt %d/%d raised: %s",
                        attempt, max_attempts, last_error)
            result = None

        if isinstance(result, dict) and not result.get("_error"):
            ok, problems = validate_selector_response(
                result, held_symbols, pool_symbols, pool_meta, config, allow_floor_breach,
                equity=float(context.get("equity", 0) or 0),
            )
            if ok:
                if attempt > 1:
                    log.info("PORTFOLIO SELECTOR succeeded on attempt %d/%d",
                             attempt, max_attempts)
                return result
            last_problems = problems
            log.warning("PORTFOLIO SELECTOR attempt %d/%d failed validation: %s",
                        attempt, max_attempts, problems[:5])

            # Feedback-prompted retry for retryable problems (count or anti-stagnation).
            if (extra_retries_used < extra_retries_allowed
                    and _selector_problems_are_retryable(problems)):
                feedback = "Validation failed: " + " | ".join(problems[:5])
                feedback += (
                    "\nFix and re-emit the JSON. You MUST honor the 3-6 selection "
                    "count rule and the anti-stagnation rule (include at least one "
                    "currently_held=false candidate within 5 score points of your "
                    "lowest selected position)."
                )
                ctx_with_feedback = {**context, "_validator_feedback": feedback}
                context = ctx_with_feedback  # next loop iteration uses this
                extra_retries_used += 1
                # do NOT count this as a normal attempt — extend by one
                max_attempts += 1
                log.info("PORTFOLIO SELECTOR retrying with validator feedback")
                continue
        elif isinstance(result, dict):
            last_error = str(result.get("_error", "unknown"))
            log.warning("PORTFOLIO SELECTOR attempt %d/%d returned error: %s",
                        attempt, max_attempts, last_error)

        if attempt < max_attempts:
            # 429 rate-limit errors require waiting at least one full window
            # (60s for input-token TPM); shorter backoff just hits 429 again.
            is_rate_limit = "429" in last_error or "rate_limit" in last_error.lower()
            backoff = 70 if is_rate_limit else 2 ** attempt  # 2s, 4s, 8s normally
            log.info("PORTFOLIO SELECTOR retrying in %ds%s",
                     backoff, " (rate-limit)" if is_rate_limit else "")
            time.sleep(backoff)

    log.critical(
        "PORTFOLIO SELECTOR FAILED after %d attempts — NO trades will execute "
        "(last_error=%s, last_validation_problems=%s)",
        max_attempts, last_error, last_problems[:5],
    )
    try:
        from src.journal import log_decision
        log_decision({
            "event": "ai_failure",
            "agent": "portfolio-selector",
            "attempts": max_attempts,
            "last_error": last_error,
            "last_problems": last_problems,
        })
    except Exception:
        pass
    return None


def run_portfolio_verifier(
    config: Config,
    context: dict[str, Any],
) -> dict[str, Any] | None:
    """Synchronous Sonnet verifier call. Returns parsed dict or None on failure.

    Unlike the Opus arbiter we do NOT retry — the verifier's role is purely
    advisory + corrective; if it fails we just skip reconciliation this scan.
    The portfolio is still in the state Opus aimed at (minus fill drift), so
    skipping a verifier pass costs alignment, not safety.
    """
    ai = AIResearcher(config)
    if not ai.available():
        log.warning(
            "PORTFOLIO VERIFIER: AI unavailable (enabled=%s, key=%s) — "
            "skipping post-execution reconcile",
            ai.enabled, bool(ai.api_key),
        )
        return None
    pipeline = AIPipeline(config, ai)
    try:
        result = asyncio.run(pipeline.portfolio_verifier(context))
    except Exception as e:
        log.warning("PORTFOLIO VERIFIER call raised: %s — skipping reconcile", e)
        return None
    if not isinstance(result, dict) or result.get("_error"):
        err = (result or {}).get("_error") if isinstance(result, dict) else type(result).__name__
        log.warning("PORTFOLIO VERIFIER returned error: %s — skipping reconcile", err)
        return None
    return result


def run_exit_arbiter(
    config: Config,
    context: dict[str, Any],
) -> dict[str, Any] | None:
    """Synchronous Opus 4.7 exit decision. Returns None if AI unavailable or
    the arbiter errored — callers MUST treat None as 'do not close' (fail-safe:
    never execute a trade without AI approval).
    """
    ai = AIResearcher(config)
    if not ai.available():
        log.critical(
            "EXIT ARBITER: AI unavailable (enabled=%s, key=%s) — "
            "cannot approve exit; holding position (fail-safe)",
            ai.enabled, bool(ai.api_key),
        )
        return None
    pipeline = AIPipeline(config, ai)
    try:
        result = asyncio.run(pipeline.exit_arbiter_verdict(context))
    except Exception as e:
        log.critical("EXIT ARBITER call failed: %s — holding position (fail-safe)", e)
        return None
    if not isinstance(result, dict) or result.get("_error"):
        log.critical(
            "EXIT ARBITER returned error: %s — holding position (fail-safe)",
            (result or {}).get("_error"),
        )
        return None
    return result


def run_entry_arbiter_single(
    config: Config,
    context: dict[str, Any],
) -> dict[str, Any] | None:
    """Synchronous Opus 4.7 single-symbol entry decision.

    Used by paths where we have one candidate and need a go/no-go.
    Returns None on failure; caller must treat None as 'do not trade'.
    """
    ai = AIResearcher(config)
    if not ai.available():
        log.critical(
            "ENTRY ARBITER: AI unavailable — no trade approved (fail-safe)",
        )
        return None
    try:
        result = asyncio.run(ai.call_agent(
            "decision-arbiter", context, task_type="trade_critical",
        ))
    except Exception as e:
        log.critical("ENTRY ARBITER call failed: %s — no trade approved", e)
        return None
    if not isinstance(result, dict) or result.get("_error"):
        log.critical("ENTRY ARBITER returned error: %s — no trade approved",
                     (result or {}).get("_error"))
        return None
    return result


def run_earnings_gate(
    config: Config,
    context: dict[str, Any],
) -> dict[str, Any] | None:
    """Synchronous entry point for a single-symbol earnings-gate decision."""
    ai = AIResearcher(config)
    if not ai.available():
        return None
    pipeline = AIPipeline(config, ai)
    try:
        result = asyncio.run(pipeline.earnings_gate_verdict(context))
    except Exception as e:
        log.warning("Earnings gate failed: %s", e)
        return None
    if not isinstance(result, dict) or result.get("_error"):
        log.warning("Earnings gate returned error: %s", (result or {}).get("_error"))
        return None
    return result


def run_ai_on_candidates(
    config: Config,
    candidates: list[TradeDecision],
    macro_ctx: dict[str, Any],
    portfolio_ctx: dict[str, Any],
) -> dict[str, AIVerdict]:
    """Synchronous entry point that executes the async pipeline and returns verdicts."""
    ai = AIResearcher(config)
    if not ai.available():
        log.info("AI research unavailable (enabled=%s, key=%s) — skipping",
                 ai.enabled, bool(ai.api_key))
        return {}

    max_n = config.get("ai", "max_candidates_per_scan", default=5)
    min_score = config.get("ai", "min_numeric_combined_for_ai", default=0.30)
    filtered = [
        c for c in candidates
        if abs(c.combined_score) >= min_score and c.action in ("buy", "hold")
    ]
    filtered.sort(key=lambda c: abs(c.combined_score), reverse=True)
    filtered = filtered[:max_n]
    if not filtered:
        log.info("No candidates meet AI threshold (min combined=%s)", min_score)
        return {}

    pipeline = AIPipeline(config, ai)

    async def _all() -> dict[str, AIVerdict]:
        tasks = [
            pipeline.analyze_candidate(c.symbol, c, macro_ctx, portfolio_ctx)
            for c in filtered
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out: dict[str, AIVerdict] = {}
        for c, r in zip(filtered, results):
            if isinstance(r, Exception):
                log.warning("AI analysis for %s failed: %s", c.symbol, r)
                continue
            out[c.symbol] = r
        return out

    return asyncio.run(_all())
