"""AI pipeline: for each top candidate, run analyst agents in parallel, then arbiter.

Inputs come from the numeric pipeline (technicals, fundamentals, sentiment, macro).
Output is a final {action, confidence, thesis, exit_conditions} dict that the
orchestrator blends with the numeric score.
"""
from __future__ import annotations
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable

from src.ai_research import AIResearcher
from src.config import Config
from src.decision import TradeDecision

log = logging.getLogger(__name__)

if sys.platform.startswith("win") and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


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

    async def aclose(self) -> None:
        await self.ai.aclose()

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
        # Python's 1% protective-stop ceiling is an execution invariant, not a
        # contradiction of that authority.
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


def _run_with_ai_cleanup(ai: AIResearcher, awaitable):
    async def _runner():
        try:
            return await awaitable
        finally:
            await ai.aclose()

    return asyncio.run(_runner())


_REQUIRED_PER_SYMBOL_FIELDS = ("target_pct", "action")
_REQUIRED_SPY_FIELDS = ("target_pct", "action")
_SOFT_FIELDS = ("opportunity_score", "one_sentence_reason")
_VALID_ACTIONS = {"BUY", "SELL", "HOLD", "EXIT", "INCREASE", "REDUCE"}


def _record_soft_warning(result: dict[str, Any], msg: str) -> None:
    """Attach a non-fatal validation note to the response for journaling.

    Soft warnings cover prose/metadata fields that the executor never reads —
    losing them must not throw away a fully-formed portfolio.
    """
    result.setdefault("_validation_warnings", []).append(msg)
    log.info("selector soft warning: %s", msg)


def _hard_stop_loss_pct(cfg: Config) -> float:
    try:
        return max(0.0, float(cfg.get("risk", "hard_stop_loss_pct", default=0.01)))
    except (TypeError, ValueError):
        return 0.01


def _max_stop_loss_pct(cfg: Config) -> float:
    hard = _hard_stop_loss_pct(cfg)
    model = str(cfg.get("risk", "stop_loss_model", default="fixed") or "fixed").lower()
    if model not in {"volatility", "atr", "atr_volatility"}:
        return hard
    try:
        configured = max(0.0, float(cfg.get("risk", "max_stop_loss_pct", default=hard)))
    except (TypeError, ValueError):
        configured = hard
    return max(hard, configured)


def _ceil_cents(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_CEILING))


def _round_cents(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


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
        for f in _SOFT_FIELDS:
            if f not in spy_dec or spy_dec[f] in (None, ""):
                _record_soft_warning(result, f"spy_decision.{f} missing")

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
        _record_soft_warning(result, "opportunity_ranking missing or not a list")

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
        for f in _SOFT_FIELDS:
            if f not in info or info[f] in (None, ""):
                _record_soft_warning(result, f"per_symbol[{sym}].{f} missing")
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
            result = _run_with_ai_cleanup(ai, pipeline.portfolio_rebalance_arbiter(context))
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
                soft = result.get("_validation_warnings") or []
                if soft:
                    log.info(
                        "PORTFOLIO ARBITER accepted with %d soft warning(s): %s",
                        len(soft), soft[:5],
                    )
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
    system_state: dict[str, Any] | None = None,
    allow_nonterminal_stop_reason: bool = False,
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

    # Empty-response guard. If none of the major selector contract fields are
    # present, the model returned a truncated or off-contract JSON (e.g. an
    # inner sub-dict picked up by the JSON extractor when the outer object
    # didn't close). Surface this as a single distinctive problem so the dump
    # captures what was actually emitted instead of producing 8 derivative
    # "missing field" complaints.
    # Phase 0: candidate_rankings was dropped from the schema — per_symbol
    # already carries the same data for every pool member.
    contract_fields = ("selected_positions", "target_weights", "per_symbol",
                       "spy_decision")
    present = [f for f in contract_fields
               if result.get(f) not in (None, [], {}, "")]
    stop_reason = result.get("_stop_reason")
    if not present:
        return False, [
            "empty_or_off_contract_response "
            f"(stop_reason={stop_reason} out_tok={result.get('_output_tokens')} "
            f"keys={sorted(k for k in result if not k.startswith('_'))[:6]})"
        ]
    if stop_reason == "max_tokens" and not allow_nonterminal_stop_reason:
        problems.append(
            f"response truncated (stop_reason=max_tokens out_tok={result.get('_output_tokens')})"
        )

    selected = result.get("selected_positions") or []
    target_w = result.get("target_weights") or {}
    per_sym = result.get("per_symbol") or {}

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
    # Phase 6 (2026-05-07): illiquid concentration cap. Names below the price
    # floor OR with 20-day ADV below the ADV floor are clamped to
    # illiquid_max_position_pct (default 8%). Catches GBTG-style $9 microcap
    # 18% concentrations. Clamping is silent (no validation problem); the
    # per-symbol entry is mutated and an audit field is recorded.
    illiquid_max_pp = float(cfg.get("risk", "illiquid_max_position_pct", default=0.08) or 0.08)
    for s, w in target_w.items():
        try:
            wf = float(w)
        except (TypeError, ValueError):
            problems.append(f"weight {s} not numeric: {w!r}")
            continue
        meta = (pool_meta.get(s) if isinstance(pool_meta, dict) else None) or {}
        if meta.get("is_illiquid") and wf > illiquid_max_pp:
            target_w[s] = illiquid_max_pp
            info = (per_sym.get(s) if isinstance(per_sym, dict) else None) or {}
            try:
                info["target_pct"] = illiquid_max_pp
                if "qty" in info and "entry_price" in info:
                    entry_p = float(info.get("entry_price") or 0)
                    if entry_p > 0:
                        info["qty"] = round(illiquid_max_pp * float(equity or 0) / entry_p, 6) if equity else info.get("qty")
            except Exception:
                pass
            result.setdefault("_auto_repaired", {}).setdefault("illiquid_clamp", {})[s] = {
                "from": wf,
                "to": illiquid_max_pp,
                "price": meta.get("price"),
                "adv": meta.get("avg_dollar_volume_20d"),
            }
            wf = illiquid_max_pp
        if not (0 < wf <= max_pp):
            problems.append(f"weight {s}={wf:.4f} out of (0, {max_pp}]")

    # AI-direct order params: qty / entry_price / delta_qty are authoritative.
    # Python enforces a protective stop floor. The default remains the hard
    # 1% stop; volatility mode allows wider AI/ATR stops up to max_stop_loss_pct.
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
    max_stop_pct = _max_stop_loss_pct(cfg)

    def _current_qty_for(sym: str) -> float:
        try:
            return float((pool_meta.get(sym, {}) or {}).get("current_qty", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

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
        hard_stop_floor = _ceil_cents(entry * (1.0 - hard_stop_pct)) if entry > 0 and hard_stop_pct > 0 else 0.0
        max_stop_floor = _ceil_cents(entry * (1.0 - max_stop_pct)) if entry > 0 and max_stop_pct > 0 else hard_stop_floor
        stop_for_risk = hard_stop_floor
        raw_stop = info.get("stop_loss")
        if raw_stop not in (None, ""):
            try:
                stop = float(raw_stop)
            except (TypeError, ValueError):
                problems.append(f"per_symbol[{s}].stop_loss not numeric")
            else:
                if stop <= 0 or stop >= entry:
                    problems.append(f"per_symbol[{s}].stop_loss ({stop}) must be > 0 and < entry_price ({entry})")
                elif max_stop_floor > 0 and stop < max_stop_floor:
                    info["stop_loss"] = max_stop_floor
                    result.setdefault("_auto_repaired", {})
                    result["_auto_repaired"].setdefault("stop_loss_floor", {})[s] = {
                        "from": stop,
                        "to": max_stop_floor,
                    }
                    stop_for_risk = max_stop_floor
                elif max_stop_floor > 0:
                    rounded_stop = _round_cents(stop)
                    if rounded_stop != stop:
                        info["stop_loss"] = rounded_stop
                        result.setdefault("_auto_repaired", {})
                        result["_auto_repaired"].setdefault("stop_loss_rounding", {})[s] = {
                            "from": stop,
                            "to": rounded_stop,
                        }
                    stop_for_risk = rounded_stop
        raw_target = info.get("take_profit")
        if raw_target not in (None, ""):
            try:
                target = float(raw_target)
            except (TypeError, ValueError):
                problems.append(f"per_symbol[{s}].take_profit not numeric")
            else:
                if target <= 0 or target <= entry:
                    problems.append(f"per_symbol[{s}].take_profit ({target}) must be > entry_price ({entry})")
        current_qty = _current_qty_for(s)
        expected_delta = qty - current_qty
        if abs(delta_qty - expected_delta) > 0.01:
            # delta_qty is fully derivable from qty - current_qty. Both qty
            # (authoritative AI sizing) and current_qty (read from the broker)
            # are trusted; delta_qty is a redundant echo the model sometimes
            # gets wrong arithmetically. Always repair from the authoritative
            # fields rather than failing the whole scan on a derived field.
            info["delta_qty"] = expected_delta
            result.setdefault("_auto_repaired", {})
            result["_auto_repaired"].setdefault("delta_qty_rounding", {})[s] = {
                "from": delta_qty,
                "to": expected_delta,
                "expected_from_qty_minus_current": True,
            }
            delta_qty = expected_delta
        # Risk-per-trade hard cap (use a contextual equity if provided).
        # Phase 2 (2026-05-07): wide stops MUST NOT kill the trade. If the
        # selector's stop produces risk_usd > cap_usd, auto-tighten the stop
        # to bring risk_usd to exactly cap_usd, clamped within
        # [hard_stop_floor, max_stop_floor]. Only if the tightened stop is
        # invalid (above market by less than min_stop_gap) do we drop the
        # symbol — and we drop just that symbol from selected, not the
        # whole batch. Today's 13:00 ET INTC/DELL/AAPL three-attempt
        # rejection becomes a successful scan with auto-tightened stops.
        if entry > 0 and hard_stop_pct > 0 and qty > 0:
            ctx_equity = 0.0
            ctx = info.get("_equity_for_validation")
            try:
                ctx_equity = float(ctx) if ctx is not None else equity_for_check
            except (TypeError, ValueError):
                ctx_equity = equity_for_check
            if ctx_equity > 0:
                risk_usd = qty * (entry - stop_for_risk)
                cap_usd = ctx_equity * max_risk_pct
                if risk_usd > cap_usd * 1.01 and cap_usd > 0:
                    tightened = entry - (cap_usd / qty)
                    # Clamp into [max_stop_floor, hard_stop_floor]: the
                    # tightened stop must be at least as tight as max_stop_floor
                    # but no tighter than hard_stop_floor (which is the
                    # closest-to-entry floor we permit).
                    if hard_stop_floor > 0:
                        tightened = min(tightened, hard_stop_floor)
                    if max_stop_floor > 0:
                        tightened = max(tightened, max_stop_floor)
                    tightened = _round_cents(tightened)
                    if tightened > 0 and tightened < entry:
                        info["stop_loss"] = tightened
                        info["stop_clamped"] = True
                        result.setdefault("_auto_repaired", {})
                        result["_auto_repaired"].setdefault("stop_risk_clamp", {})[s] = {
                            "from_stop": stop_for_risk,
                            "to_stop": tightened,
                            "from_risk_usd": round(risk_usd, 2),
                            "to_risk_usd": round(qty * (entry - tightened), 2),
                            "cap_usd": round(cap_usd, 2),
                        }
                        stop_for_risk = tightened
                    else:
                        # Cannot tighten validly. Neutralize this single
                        # symbol (qty/delta=0) so the rest of the batch ships;
                        # the executor will submit no order and the Telegram
                        # trade-failure notifier will surface it.
                        result.setdefault("_dropped_for_invalid_stop", []).append(s)
                        info["qty"] = 0.0
                        info["delta_qty"] = -current_qty if current_qty > 0 else 0.0
                        info["target_pct"] = 0.0
                        info["action"] = "PASS"
                        info["pass_reason"] = (
                            f"stop cannot meet max_risk_per_trade ${cap_usd:.0f} "
                            f"with qty {qty} at entry {entry}"
                        )
                        log.warning(
                            "per_symbol[%s] neutralized: stop cannot be tightened to "
                            "meet max_risk_per_trade $%.0f (qty=%s entry=%s)",
                            s, cap_usd, qty, entry,
                        )

    try:
        spy_t = max(0.0, float(result.get("spy_target_pct", 0) or 0))
        cash_t = max(0.0, float(result.get("cash_target_pct", 0) or 0))
        target_w = {s: max(0.0, float(v)) for s, v in target_w.items()}
        wsum = sum(target_w.values())
        total = wsum + spy_t + cash_t
        if not (0.99 <= total <= 1.01):
            if total <= 0 or total > 1.25:
                problems.append(f"weights+spy+cash sum {total:.3f} outside repair band")
                raise RuntimeError("allocation total outside repair band")
            before = {
                "target_weights": dict(target_w),
                "spy_target_pct": spy_t,
                "cash_target_pct": cash_t,
                "total": total,
            }
            if total < 0.99:
                cash_t += 1.0 - total
            elif total > 1.01:
                excess = total - 1.0
                if cash_t >= excess:
                    cash_t -= excess
                else:
                    excess -= cash_t
                    cash_t = 0.0
                    invested = wsum + spy_t
                    if invested > 0:
                        scale = max(0.0, (invested - excess) / invested)
                        target_w = {s: v * scale for s, v in target_w.items()}
                        spy_t *= scale
            target_w = {s: round(v, 6) for s, v in target_w.items() if v > 0}
            for s, w in target_w.items():
                if isinstance(per_sym, dict) and isinstance(per_sym.get(s), dict):
                    per_sym[s]["target_pct"] = w
            spy_t = round(spy_t, 6)
            cash_t = round(max(0.0, 1.0 - sum(target_w.values()) - spy_t), 6)
            result["target_weights"] = target_w
            result["spy_target_pct"] = spy_t
            result["cash_target_pct"] = cash_t
            result.setdefault("_auto_repaired", {})
            result["_auto_repaired"]["allocation_total"] = {
                "from": before,
                "to": {
                    "target_weights": dict(target_w),
                    "spy_target_pct": spy_t,
                    "cash_target_pct": cash_t,
                    "total": round(sum(target_w.values()) + spy_t + cash_t, 6),
                },
            }
            total = sum(target_w.values()) + spy_t + cash_t
            if not (0.99 <= total <= 1.01):
                problems.append(f"weights+spy+cash sum {total:.3f} outside [0.99, 1.01]")
    except (TypeError, ValueError):
        problems.append("weights/spy/cash not numeric")
        spy_t, cash_t = 0.0, 0.0
    except RuntimeError:
        spy_t, cash_t = 0.0, 0.0

    spy_dec = result.get("spy_decision")
    if not isinstance(spy_dec, dict):
        problems.append("missing spy_decision")
    else:
        for f in _REQUIRED_SPY_FIELDS:
            if f not in spy_dec or spy_dec[f] in (None, ""):
                problems.append(f"spy_decision.{f} missing")
        for f in _SOFT_FIELDS:
            if f not in spy_dec or spy_dec[f] in (None, ""):
                _record_soft_warning(result, f"spy_decision.{f} missing")

    if not isinstance(per_sym, dict):
        problems.append("per_symbol not a dict")
        per_sym = {}
    else:
        extra_per_sym = [
            s for s in list(per_sym.keys())
            if s not in pool_set and s not in set(selected)
        ]
        if extra_per_sym:
            for s in extra_per_sym:
                per_sym.pop(s, None)
            result["per_symbol"] = per_sym
            result.setdefault("_auto_repaired", {})
            result["_auto_repaired"]["per_symbol_extra_keys_removed"] = extra_per_sym

        missing_per_sym_initial = [s for s in pool_symbols if s not in per_sym]
        repairable_per_sym = [
            s for s in missing_per_sym_initial
            if s not in selected and not pool_meta.get(s, {}).get("currently_held", False)
        ]
        if missing_per_sym_initial and len(repairable_per_sym) == len(missing_per_sym_initial):
            for s in repairable_per_sym:
                # Phase 0: slim PASS auto-fill — drop exhaustion_penalty,
                # remaining_upside_score (duplicates of opportunity_score and
                # the exhaustion_penalty_applied list), and emit a short
                # reason_code instead of a full sentence.
                per_sym[s] = {
                    "target_pct": 0.0,
                    "qty": 0,
                    "delta_qty": 0,
                    "entry_price": 0,
                    "action": "PASS",
                    "confidence": 0.0,
                    "opportunity_score": 0,
                    "reason_code": "auto_pass_omitted",
                }
            result["per_symbol"] = per_sym
            result.setdefault("_auto_repaired", {})
            result["_auto_repaired"]["per_symbol_pass_fill"] = repairable_per_sym

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
            current_qty = _current_qty_for(s)
            repairable_full_exit = (
                action == "EXIT"
                and tp == 0.0
                and qty_exit == 0
                and current_qty > 0
            )
            if "delta_qty" in info:
                try:
                    dq = float(info.get("delta_qty", 0) or 0)
                except (TypeError, ValueError):
                    dq = 1.0
                if dq > 0:
                    problems.append(f"held {s} EXIT delta_qty must be <= 0, got {dq}")
                elif current_qty > 0 and abs(dq + current_qty) > 0.01:
                    if repairable_full_exit:
                        info["delta_qty"] = -current_qty
                        result.setdefault("_auto_repaired", {})
                        result["_auto_repaired"].setdefault("exit_delta_qty", {})[s] = {
                            "from": dq,
                            "to": -current_qty,
                        }
                    else:
                        problems.append(
                            f"held {s} EXIT delta_qty must equal -current_qty "
                            f"({-current_qty}), got {dq}"
                        )
            else:
                if repairable_full_exit:
                    info["delta_qty"] = -current_qty
                    result.setdefault("_auto_repaired", {})
                    result["_auto_repaired"].setdefault("exit_delta_qty", {})[s] = {
                        "from": None,
                        "to": -current_qty,
                    }
                else:
                    problems.append(
                        f"held {s} EXIT missing delta_qty"
                    )

    missing_per_sym = [s for s in pool_symbols if s not in per_sym]
    if missing_per_sym:
        problems.append(f"per_symbol missing {len(missing_per_sym)} symbols: {missing_per_sym[:5]}")
    for s, info in per_sym.items() if isinstance(per_sym, dict) else []:
        if not isinstance(info, dict):
            problems.append(f"per_symbol[{s}] not a dict")
            continue
        # Phase 0 slim schema: action / target_pct / opportunity_score are
        # always required. one_sentence_reason is required ONLY for actions
        # that move capital (BUY / INCREASE / EXIT / REDUCE); HOLD / PASS
        # may use a short `reason_code` enum or omit the reason altogether.
        # exhaustion_penalty + remaining_upside_score were dropped — they
        # duplicate the exhaustion_penalty_applied list and opportunity_score.
        for f in ("target_pct", "action"):
            if f not in info:
                problems.append(f"per_symbol[{s}].{f} missing")
        if "opportunity_score" not in info:
            _record_soft_warning(result, f"per_symbol[{s}].opportunity_score missing")
        action = str(info.get("action", "")).upper()
        if action and action not in _SELECTOR_VALID_ACTIONS:
            problems.append(f"per_symbol[{s}].action invalid: {action!r}")
        reason = info.get("one_sentence_reason", "")
        if action in ("BUY", "INCREASE", "EXIT", "REDUCE") and (
            not reason or not isinstance(reason, str) or not reason.strip()
        ):
            _record_soft_warning(
                result, f"per_symbol[{s}].one_sentence_reason missing for action={action}"
            )
        if isinstance(reason, str) and ";" in reason:
            info["one_sentence_reason"] = reason.replace(";", ".")

    # ============================================================
    # Phase A/C/D/E hard checks (2026-05-07)
    # ============================================================
    ss = system_state if isinstance(system_state, dict) else {}
    tape_state = ss.get("tape_state") or {}

    def _opp(sym: str) -> float:
        info = per_sym.get(sym) if isinstance(per_sym, dict) else None
        if not isinstance(info, dict):
            return 0.0
        try:
            return float(info.get("opportunity_score", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    # ============================================================
    # Deterministic BUY-eligibility gates with auto-repair
    # (2026-05-11): Previously each gate appended to `problems` and the
    # selector was force-retried up to 5x. In a rallying tape the entire
    # high-priority pool sits within the distance-from-high band, so every
    # retry picks the next-best names that fail the same gate — burning
    # ~$10 of Opus tokens per failed scan and ending in a safety no-op.
    # The validator now downgrades the offending selection to PASS
    # deterministically and lets the rest of the response ship.
    # Toggle via selector.auto_downgrade_buy_gate_violations (default True).
    # ============================================================
    auto_downgrade = bool(cfg.get(
        "selector", "auto_downgrade_buy_gate_violations", default=True,
    ))

    # Phase A: tape floor on BUY/INCREASE.
    # Phase C: absolute BUY floor + distance-from-high gate.
    tape_floor = 0.0
    try:
        tape_floor = float(tape_state.get("min_opportunity_score_floor", 0) or 0)
    except (TypeError, ValueError):
        tape_floor = 0.0
    abs_buy_floor = 0.0
    try:
        abs_buy_floor = float(ss.get("buy_min_opportunity_score", 0) or 0)
    except (TypeError, ValueError):
        abs_buy_floor = 0.0
    dist_high_floor = 0.0
    try:
        dist_high_floor = float(ss.get("buy_max_distance_from_high_pct", 0) or 0)
    except (TypeError, ValueError):
        dist_high_floor = 0.0
    severity = str(tape_state.get("severity_label") or "favorable")
    late_day_freeze = bool(ss.get("no_new_entries"))

    # Phase C.1 (2026-05-11): dynamic floor scaling.
    # In a favorable tape, the static 70 floor becomes too tight when the
    # pool's top score is only in the high-70s. Make both the opp-score floor
    # and the distance-from-high floor scale with (pool_top_opp, tape_badness).
    try:
        tape_badness = float(tape_state.get("tape_badness") or 0.0)
    except (TypeError, ValueError):
        tape_badness = 0.0
    tape_badness = max(0.0, min(1.0, tape_badness))
    dyn_enabled = bool(ss.get("buy_floor_dynamic_enabled", True))
    pool_top_opp = 0.0
    if isinstance(per_sym, dict):
        for _info in per_sym.values():
            if not isinstance(_info, dict):
                continue
            try:
                _o = float(_info.get("opportunity_score", 0) or 0)
            except (TypeError, ValueError):
                _o = 0.0
            if _o > pool_top_opp:
                pool_top_opp = _o
    dyn_floor: float | None = None
    if dyn_enabled and pool_top_opp > 0 and abs_buy_floor > 0:
        d_fav = float(ss.get("buy_floor_dynamic_delta_favorable", 15) or 15)
        d_sev = float(ss.get("buy_floor_dynamic_delta_severe", 5) or 5)
        # Interpolate delta: favorable tape → bigger delta (more permissive);
        # severe tape → smaller delta (only top names clear the bar).
        delta = d_fav + (d_sev - d_fav) * tape_badness
        dyn_min = float(ss.get("buy_floor_dynamic_min", 55) or 55)
        # Cap dynamic floor at static config — dynamic only loosens, never tightens
        # beyond what an operator explicitly set.
        dyn_floor = max(dyn_min, min(abs_buy_floor, pool_top_opp - delta))
    effective_abs_buy_floor = dyn_floor if dyn_floor is not None else abs_buy_floor
    effective_buy_floor = max(tape_floor, effective_abs_buy_floor)

    # Distance-from-high gate scales with tape: in favorable tape, only a
    # token pullback is required (0.25 × static); in severe risk-off, the
    # full static floor applies. Below this scaled floor, a high-confidence
    # selection can also bypass if volume isn't actively fading.
    dyn_dist_scale_min = float(ss.get("buy_distance_dynamic_min_scale", 0.25) or 0.25)
    dyn_dist_scale_min = max(0.0, min(1.0, dyn_dist_scale_min))
    effective_dist_high_floor = (
        dist_high_floor * (dyn_dist_scale_min + (1.0 - dyn_dist_scale_min) * tape_badness)
        if dyn_enabled and dist_high_floor > 0 else dist_high_floor
    )
    dist_conf_bypass = float(ss.get("buy_distance_confidence_bypass", 0.65) or 0.65)

    if dyn_enabled and (dyn_floor is not None or effective_dist_high_floor != dist_high_floor):
        log.info(
            "PORTFOLIO SELECTOR dynamic gates: tape_badness=%.2f pool_top_opp=%.1f "
            "buy_floor static=%.1f dyn=%s effective=%.1f | dist_high static=%.3f effective=%.3f "
            "| conf_bypass>=%.2f",
            tape_badness, pool_top_opp, abs_buy_floor,
            f"{dyn_floor:.1f}" if dyn_floor is not None else "—",
            effective_buy_floor, dist_high_floor, effective_dist_high_floor,
            dist_conf_bypass,
        )

    # Build deterministic BUY-ineligibility for the entire pool. Used both to
    # downgrade offending selections AND to filter `viable_new` in the
    # anti-stagnation check (don't penalize the selector for not picking a
    # name no candidate in the pool could have legally bought).
    rotations_map = ss.get("recent_selector_rotations") or {}
    rot_min_score = float(ss.get("selector_rotation_rebuy_min_score", 90) or 90)
    rot_min_delta = float(ss.get("selector_rotation_rebuy_min_score_delta", 10) or 10)

    # Phase C.1 (2026-05-11): dynamic rotation rebuy floor. With pool_top_opp
    # often in the high-70s in a favorable tape, a static 90 floor is
    # unreachable — 10 names got rotation-penalized in the 16:37 scan today.
    # The floor scales with pool_top_opp and tape_badness like the BUY floor,
    # but with a smaller delta so it stays *above* the BUY floor (a rotation
    # rebuy should clear a higher bar than a fresh entry — you're re-buying
    # something you just sold).
    dyn_rot_enabled = bool(ss.get("rotation_rebuy_dynamic_enabled", True))
    if dyn_rot_enabled and pool_top_opp > 0 and rot_min_score > 0:
        rot_d_fav = float(ss.get("rotation_rebuy_dynamic_delta_favorable", 8) or 8)
        rot_d_sev = float(ss.get("rotation_rebuy_dynamic_delta_severe", 2) or 2)
        rot_delta_dyn = rot_d_fav + (rot_d_sev - rot_d_fav) * tape_badness
        rot_dyn_min = float(ss.get("rotation_rebuy_dynamic_min", 70) or 70)
        # Dynamic only loosens — clamped between the absolute min and the static
        # config value. Also clamped to >= effective_buy_floor so rotation
        # cooldown never sinks below the floor a fresh BUY must clear.
        rot_dyn_floor = max(
            rot_dyn_min,
            effective_buy_floor,
            min(rot_min_score, pool_top_opp - rot_delta_dyn),
        )
        rot_min_score_effective = rot_dyn_floor
    else:
        rot_min_score_effective = rot_min_score

    if dyn_rot_enabled and rot_min_score > 0 and rot_min_score_effective != rot_min_score:
        log.info(
            "PORTFOLIO SELECTOR dynamic rotation floor: static=%.1f effective=%.1f "
            "(pool_top_opp=%.1f tape_badness=%.2f buy_floor=%.1f)",
            rot_min_score, rot_min_score_effective,
            pool_top_opp, tape_badness, effective_buy_floor,
        )
    pool_buy_ineligible: dict[str, str] = {}
    for s in pool_symbols:
        meta = pool_meta.get(s, {}) if isinstance(pool_meta, dict) else {}
        chart = meta.get("intraday_chart") if isinstance(meta, dict) else None
        if isinstance(chart, dict) and effective_dist_high_floor > 0:
            try:
                dh = float(chart.get("distance_from_high_pct", 1.0) or 1.0)
            except (TypeError, ValueError):
                dh = 1.0
            vt = str(chart.get("volume_trend") or "").lower()
            if dh < effective_dist_high_floor and vt != "rising":
                pool_buy_ineligible[s] = (
                    f"distance_from_high={dh:.3f}<{effective_dist_high_floor:.3f} "
                    f"vol={vt or 'unknown'}"
                )
                continue
        if isinstance(chart, dict) and severity == "strong_risk_off":
            cls = str(chart.get("classification") or "").lower()
            if cls and cls != "strong_continuation":
                pool_buy_ineligible[s] = f"risk_off_requires_strong_continuation_got_{cls}"

    gate_downgrades: dict[str, str] = {}

    def _record_gate_downgrade(sym: str, reason: str) -> None:
        gate_downgrades.setdefault(sym, reason)

    for s in selected:
        info = per_sym.get(s) if isinstance(per_sym, dict) else None
        if not isinstance(info, dict):
            continue
        action = str(info.get("action", "") or "").upper()
        if action not in ("BUY", "INCREASE"):
            continue
        # Phase E: late-day freeze.
        if late_day_freeze:
            _record_gate_downgrade(
                s,
                f"late_day_freeze (minutes_to_close={ss.get('minutes_to_close')})",
            )
            continue
        opp = _opp(s)
        # Phase A + Phase C absolute floor:
        if effective_buy_floor > 0 and opp + 1e-6 < effective_buy_floor:
            _record_gate_downgrade(
                s,
                f"opp_score={opp:.1f}<floor={effective_buy_floor:.1f}",
            )
            continue
        # Phase C distance-from-high / classification gates (from pre-computed map).
        if s in pool_buy_ineligible:
            gate_reason = pool_buy_ineligible[s]
            # Phase C.1 (2026-05-11): high-confidence bypass for the proximity
            # gate only. The risk_off-requires-strong-continuation gate is NOT
            # bypassable. The proximity bypass also requires volume is not
            # actively fading — fading volume at the high is the actual chase
            # trap, not just "trading near the high".
            if (
                dyn_enabled
                and gate_reason.startswith("distance_from_high=")
                and dist_conf_bypass > 0
            ):
                try:
                    sym_conf = float(info.get("confidence", 0) or 0)
                except (TypeError, ValueError):
                    sym_conf = 0.0
                _meta = pool_meta.get(s, {}) if isinstance(pool_meta, dict) else {}
                _chart = _meta.get("intraday_chart") if isinstance(_meta, dict) else None
                vt = str((_chart or {}).get("volume_trend") or "").lower() if isinstance(_chart, dict) else ""
                if sym_conf >= dist_conf_bypass and vt != "fading":
                    info["_gate_bypass_reason"] = (
                        f"high_conf_proximity_bypass conf={sym_conf:.2f}>={dist_conf_bypass:.2f} "
                        f"vol={vt or 'unknown'}"
                    )
                    log.info(
                        "PORTFOLIO SELECTOR proximity gate bypassed for %s "
                        "(conf=%.2f vol=%s tape_badness=%.2f)",
                        s, sym_conf, vt or "unknown", tape_badness,
                    )
                    # fall through to Phase D rotation cooldown check
                else:
                    _record_gate_downgrade(s, gate_reason)
                    continue
            else:
                _record_gate_downgrade(s, gate_reason)
                continue
        # Phase D: selector-rotation cooldown.
        rot = rotations_map.get(s) if isinstance(rotations_map, dict) else None
        if isinstance(rot, dict):
            try:
                prior = float(rot.get("opportunity_score_at_exit", 0) or 0)
            except (TypeError, ValueError):
                prior = 0.0
            if opp < rot_min_score_effective or (opp - prior) < rot_min_delta:
                _record_gate_downgrade(
                    s,
                    f"rotation_cooldown (score={opp:.1f}<floor={rot_min_score_effective:.1f} "
                    f"prior={prior:.1f} age={rot.get('minutes_ago')}m)",
                )
                continue

    if gate_downgrades and auto_downgrade:
        freed_total = 0.0
        repaired: dict[str, str] = {}
        for sym, reason in gate_downgrades.items():
            info = per_sym.get(sym) if isinstance(per_sym, dict) else None
            if not isinstance(info, dict):
                continue
            info["action"] = "PASS"
            info["target_pct"] = 0.0
            info["qty"] = 0
            info["delta_qty"] = 0
            info["_gate_downgrade_reason"] = reason
            info["pass_reason"] = f"deterministic_gate: {reason}"
            if isinstance(target_w, dict):
                freed_total += float(target_w.pop(sym, 0.0) or 0.0)
            if isinstance(selected, list) and sym in selected:
                selected.remove(sym)
            repaired[sym] = reason
        if freed_total > 0:
            try:
                cur_cash = float(result.get("cash_target_pct", 0) or 0)
            except (TypeError, ValueError):
                cur_cash = 0.0
            result["cash_target_pct"] = round(cur_cash + freed_total, 6)
        result["selected_positions"] = selected
        if isinstance(target_w, dict):
            result["target_weights"] = target_w
        result.setdefault("_auto_repaired", {})["buy_gate_downgrade"] = repaired
        log.info(
            "PORTFOLIO SELECTOR auto-downgraded %d BUY/INCREASE entr%s to PASS "
            "(freed_weight=%.3f → cash): %s",
            len(repaired), "y" if len(repaired) == 1 else "ies",
            freed_total, repaired,
        )
    elif gate_downgrades:
        # Auto-repair disabled: surface as hard problems for the legacy path.
        for sym, reason in gate_downgrades.items():
            problems.append(f"per_symbol[{sym}] BUY blocked: {reason}")

    # Phase B: top-3 concentration ratio guard. When 3+ positions are
    # selected, the top weight must be at least
    # min_top3_weight_ratio × the smallest of the top-3 weights — otherwise
    # weights are clustering at 1/N which defeats concentration sizing.
    try:
        ratio_min = float(ss.get("min_top3_weight_ratio", 0) or 0)
    except (TypeError, ValueError):
        ratio_min = 0.0
    if ratio_min > 0 and isinstance(target_w, dict) and len(selected) >= 3:
        sel_weights = sorted(
            (float(target_w.get(s, 0) or 0) for s in selected),
            reverse=True,
        )
        top3 = [w for w in sel_weights[:3] if w > 0]
        if len(top3) == 3 and top3[2] > 0:
            ratio = top3[0] / top3[2]
            if ratio + 1e-6 < ratio_min:
                problems.append(
                    f"top-3 weight ratio {ratio:.2f} < min_top3_weight_ratio {ratio_min:.2f} "
                    f"(top3={[round(w,3) for w in top3]}) — drop the weakest selected name "
                    "and reallocate to the leaders"
                )

    # Phase B (risk-off): hard cap on selected count when tape is risk_off.
    if bool(ss.get("risk_off_active")):
        try:
            cap = int(ss.get("max_positions_this_scan", 0) or 0)
        except (TypeError, ValueError):
            cap = 0
        if cap > 0 and len(selected) > cap:
            problems.append(
                f"selected count {len(selected)} > risk_off cap {cap} "
                f"(severity={severity}) — concentrate into your top {cap} by "
                "opportunity_score"
            )

    # Anti-stagnation enforcement (Phase 0: scores read from per_symbol now
    # that candidate_rankings was dropped from the schema).
    # Phase C (2026-05-07): suppressed when no fresh candidate clears the
    # absolute anti_stagnation_min_top_score floor — better to keep incumbents
    # than force a low-quality rotation.
    anti_stag_min_top = 0.0
    try:
        anti_stag_min_top = float(ss.get("anti_stagnation_min_top_score", 0) or 0)
    except (TypeError, ValueError):
        anti_stag_min_top = 0.0

    if not allow_floor_breach and selected:
        scores: dict[str, float] = {}
        if isinstance(per_sym, dict):
            for sym, info in per_sym.items():
                if not isinstance(info, dict):
                    continue
                try:
                    scores[str(sym)] = float(info.get("opportunity_score", 0) or 0)
                except (TypeError, ValueError):
                    continue
        new_in_pool = [
            s for s in pool_symbols
            if not pool_meta.get(s, {}).get("currently_held", False)
            and s not in pool_buy_ineligible  # don't blame the selector for skipping ineligible names
        ]
        new_in_selected = [s for s in selected if not pool_meta.get(s, {}).get("currently_held", False)]
        if selected:
            lowest_selected = min(scores.get(s, 0.0) for s in selected)
        else:
            lowest_selected = 0.0
        viable_new = [s for s in new_in_pool if scores.get(s, 0.0) >= (lowest_selected - 5.0)]
        # Suppress anti-stagnation when no fresh candidate would clear the
        # absolute quality floor — forcing in a low-score fresh name here is
        # exactly the failure pattern we're trying to avoid.
        if anti_stag_min_top > 0 and viable_new:
            top_fresh_score = max((scores.get(s, 0.0) for s in viable_new), default=0.0)
            if top_fresh_score + 1e-6 < anti_stag_min_top:
                viable_new = []
        if viable_new and not new_in_selected:
            problems.append(
                f"Selection failed to incorporate new opportunities despite "
                f"viable candidates: {viable_new[:5]}"
            )

    # Peer-relative pressure: if the selector chooses a weaker peer while a
    # stronger similar company is in the same pool, it must explicitly justify
    # the lower-ranked choice by naming the stronger peer. This catches AMD vs
    # INTC and MU vs SNDK/WDC style failures without blindly forcing a ticker.
    selected_set = {str(s).upper() for s in selected}
    peer_gap_threshold = float(
        cfg.get("selector", "peer_outperformance_threshold", default=10) or 10
    )
    for s in selected_set:
        meta = pool_meta.get(s, {}) if isinstance(pool_meta, dict) else {}
        pressure = meta.get("peer_pressure") or {}
        stronger = str(pressure.get("stronger_peer") or "").upper()
        try:
            gap = float(pressure.get("score_gap", 0) or 0)
        except (TypeError, ValueError):
            gap = 0.0
        if not stronger or stronger in selected_set or gap < peer_gap_threshold:
            continue
        info = per_sym.get(s, {}) if isinstance(per_sym, dict) else {}
        reason = str(info.get("one_sentence_reason", "") or "")
        if stronger.lower() not in reason.lower():
            problems.append(
                f"selected {s} trails stronger peer {stronger} by {gap:.1f} "
                "priority points without naming that peer in reason prose",
            )

    if "exhaustion_penalty_applied" not in result:
        _record_soft_warning(result, "exhaustion_penalty_applied missing")
    elif not isinstance(result.get("exhaustion_penalty_applied"), list):
        _record_soft_warning(result, "exhaustion_penalty_applied not a list")

    rp = result.get("rotation_plan") or {}
    if isinstance(rp, dict):
        for entry in rp.get("exited", []) or []:
            if not isinstance(entry, dict):
                continue
            cat = entry.get("reason_category")
            if cat is not None and cat not in _SELECTOR_EXIT_REASON_CATS:
                _record_soft_warning(
                    result,
                    f"rotation_plan.exited[{entry.get('symbol')}] bad reason_category: {cat!r}",
                )
        for entry in rp.get("entered", []) or []:
            if not isinstance(entry, dict):
                continue
            cat = entry.get("reason_category")
            if cat is not None and cat not in _SELECTOR_ENTRY_REASON_CATS:
                _record_soft_warning(
                    result,
                    f"rotation_plan.entered[{entry.get('symbol')}] bad reason_category: {cat!r}",
                )

    return (len(problems) == 0), problems


def _dump_selector_validation_failure(
    result: dict[str, Any],
    problems: list[str],
    attempt: int,
) -> None:
    """Persist the parsed selector response + validation problems on failure.
    Critical for diagnosing why the selector returns empty/incomplete JSON."""
    from datetime import datetime, timezone
    from pathlib import Path
    out_dir = Path(__file__).resolve().parents[1] / "data" / "ai_failures"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"{ts}_portfolio-selector_validation_attempt{attempt}.json"
    path.write_text(
        json.dumps({
            "attempt": attempt,
            "problems": problems,
            "stop_reason": result.get("_stop_reason"),
            "input_tokens": result.get("_input_tokens"),
            "output_tokens": result.get("_output_tokens"),
            "top_level_keys": sorted(result.keys()),
            "selected_positions": result.get("selected_positions"),
            "target_weights": result.get("target_weights"),
            "spy_decision": result.get("spy_decision"),
            "spy_target_pct": result.get("spy_target_pct"),
            "cash_target_pct": result.get("cash_target_pct"),
            "per_symbol_count": len(result.get("per_symbol") or {}),
            "raw_thesis": (result.get("portfolio_thesis") or "")[:400],
            "_raw_truncated": (result.get("_raw") or "")[:1500],
            "full_response": result,
        }, indent=2, default=str),
        encoding="utf-8",
    )


def _selector_problems_are_retryable(problems: list[str]) -> bool:
    """True when problems are exclusively count/range OR anti-stagnation —
    these are worth a feedback-prompted retry. Other problems (missing
    fields, malformed JSON) usually indicate the model went off-contract
    and aren't fixable by re-prompting."""
    if not problems:
        return False
    keywords = (
        "selected count", "duplicates in selected_positions",
        "incorporate new opportunities", "trails stronger peer",
        # Phase A/C/D/E gates (2026-05-07): all retryable — model can fix
        # by emitting PASS for the offending name(s).
        "BUY floor", "BUY blocked", "late-day freeze",
        "selector-rotation cooldown", "top-3 weight ratio",
        "risk_off cap",
    )
    return all(any(kw in p for kw in keywords) for p in problems)


def _normalize_selector_problems(problems: list[str]) -> frozenset[tuple[str, str]]:
    """Reduce a list of validator complaints to (symbol, gate_kind) tuples
    suitable for equality comparison across attempts.

    The full message includes numeric values that drift slightly between
    attempts (e.g. `distance_from_high=0.001<0.040 vol=fading` vs
    `distance_from_high=0.002<0.040`). Stripping to (sym, kind) lets us
    detect "same symbols failing the same gate" thrash without false negatives
    from numeric jitter. Returns a frozenset so order doesn't matter.
    """
    import re
    out: set[tuple[str, str]] = set()
    for p in problems or []:
        if not isinstance(p, str):
            continue
        sym_match = re.search(r"per_symbol\[([A-Z0-9.\-]+)\]", p)
        sym = sym_match.group(1) if sym_match else ""
        # Extract the gate kind: the alphabetic prefix of the reason after
        # "BUY blocked:" or similar. Falls back to a coarse signature.
        reason_match = re.search(r"BUY blocked:\s*([a-zA-Z_]+)", p)
        if reason_match:
            kind = reason_match.group(1)
        else:
            # Generic: first ~30 alnum chars of the complaint as a stable hash.
            kind = re.sub(r"[^a-zA-Z_]+", "_", p)[:32]
        out.add((sym, kind))
    return frozenset(out)


def _selector_problems_indicate_truncation(problems: list[str]) -> bool:
    """True when the response is empty / truncated. A bare retry (no feedback
    prompt) is the right move — the original prompt was fine, the model just
    cut off. Surfaced separately from _selector_problems_are_retryable because
    these don't need (and shouldn't get) the feedback string appended."""
    if not problems:
        return False
    return any(
        ("empty_or_off_contract_response" in p) or ("response truncated" in p)
        for p in problems
    )


def _record_selector_token_usage(
    config: Config,
    result: dict[str, Any],
    *,
    allow_floor_breach: bool,
) -> None:
    """Append a row to data/state/selector_token_history.jsonl + warn at 80%.

    Phase 0 telemetry: the 2026-05-05 11:00 PDT scan hit the 32K output cap
    with no warning. Surface usage trends so a future drift toward the cap
    raises a flag long before it fails a scan.
    """
    cap = int(config.get("ai", "max_tokens_per_agent", default={}).get(
        "portfolio-selector", 12000) or 12000)
    in_tok = result.get("_input_tokens")
    out_tok = result.get("_output_tokens")
    cache_read = result.get("_cache_read_tokens")

    try:
        out_int = int(out_tok or 0)
    except (TypeError, ValueError):
        out_int = 0

    if out_int >= int(cap * 0.8):
        log.warning(
            "PORTFOLIO SELECTOR token usage at %.0f%% of cap "
            "(out=%s, cap=%s) — investigate before it fails a scan",
            (out_int / max(cap, 1)) * 100, out_tok, cap,
        )

    state_dir = Path(__file__).resolve().parents[1] / "data" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "selector_token_history.jsonl"
    from datetime import datetime, timezone
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "cache_read_tokens": cache_read,
        "cap": cap,
        "pct_of_cap": (out_int / cap) if cap > 0 else None,
        "allow_floor_breach": bool(allow_floor_breach),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def run_portfolio_selector(
    config: Config,
    context: dict[str, Any],
    pool_symbols: list[str],
    pool_meta: dict[str, dict[str, Any]],
    held_symbols: list[str],
    allow_floor_breach: bool = False,
    max_attempts: int = 3,
    rebuild_with_pool_size: "Callable[[int], tuple[dict[str, Any], list[str], dict[str, dict[str, Any]]]] | None" = None,
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
    # 2026-05-11: detect identical-complaint thrash and short-circuit.
    # When the validator rejects the same (symbol, gate_kind) tuples N times
    # in a row, no number of further retries will help — the pool can't
    # produce a passing answer. Halts after 2 repeats by default.
    prev_problem_signature: frozenset[tuple[str, str]] | None = None
    short_circuit_on_repeat = bool(
        config.get("selector", "retry_short_circuit_on_repeat", default=True)
    )

    # Phase 1 (2026-05-07, hardened 2026-05-08): max_tokens fallback. First,
    # accept a capped response if the extracted JSON validates. Otherwise,
    # retry with progressively smaller pools when the caller can rebuild the
    # context. Without the callable, preserve the legacy halt behavior.
    fallback_pool_size = int(config.get("selector", "max_tokens_fallback_pool_size", default=30) or 30)
    fallback_min_pool_size = int(config.get("selector", "max_tokens_fallback_min_pool_size", default=12) or 12)
    max_tokens_retries_allowed = max(0, int(config.get("selector", "max_tokens_max_attempts", default=2) or 2) - 1)
    max_tokens_retries_used = 0

    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            result = _run_with_ai_cleanup(ai, pipeline.portfolio_selector(context))
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            log.warning("PORTFOLIO SELECTOR attempt %d/%d raised: %s",
                        attempt, max_attempts, last_error)
            result = None

        # Phase 1: a max_tokens stop is only fatal if the extracted JSON is
        # invalid and the progressive smaller-pool retries are exhausted.
        if isinstance(result, dict) and result.get("_stop_reason") == "max_tokens":
            in_tok = result.get("_input_tokens")
            out_tok = result.get("_output_tokens")
            ok, problems = validate_selector_response(
                result, held_symbols, pool_symbols, pool_meta, config, allow_floor_breach,
                equity=float(context.get("equity", 0) or 0),
                system_state=context.get("system_state") or {},
                allow_nonterminal_stop_reason=True,
            )
            last_problems = problems
            if ok:
                result["_accepted_with_stop_reason"] = "max_tokens"
                log.warning(
                    "PORTFOLIO SELECTOR hit max_tokens on attempt %d "
                    "(in=%s out=%s) but extracted JSON validated; accepting "
                    "the safe structured response.",
                    attempt, in_tok, out_tok,
                )
                try:
                    _record_selector_token_usage(
                        config, result, allow_floor_breach=allow_floor_breach,
                    )
                except Exception as e:
                    log.debug("token-usage telemetry failed: %s", e)
                return result
            try:
                _dump_selector_validation_failure(result, problems, attempt)
            except Exception as e:
                log.debug("Selector max_tokens dump failed: %s", e)

            if (
                rebuild_with_pool_size is not None
                and max_tokens_retries_used < max_tokens_retries_allowed
            ):
                retry_pool_size = int(round(fallback_pool_size * (0.67 ** max_tokens_retries_used)))
                retry_pool_size = max(fallback_min_pool_size, retry_pool_size, len(held_symbols))
                max_tokens_retries_used += 1
                log.warning(
                    "PORTFOLIO SELECTOR max_tokens on attempt %d (in=%s out=%s); "
                    "retrying with pool truncated to %d",
                    attempt, in_tok, out_tok, retry_pool_size,
                )
                try:
                    new_ctx, new_pool, new_meta = rebuild_with_pool_size(retry_pool_size)
                    context = new_ctx
                    pool_symbols = new_pool
                    pool_meta = new_meta
                    # extend the attempt budget by one so the truncated retry
                    # gets a fresh slot rather than counting against validation retries
                    max_attempts += 1
                except Exception as e:
                    log.warning("PORTFOLIO SELECTOR pool-rebuild failed: %s — halting", e)
                    last_error = f"max_tokens rebuild failed: {e}"
                    last_problems = [f"max_tokens cap hit on attempt {attempt}; rebuild failed"]
                    break
                continue  # retry immediately with the smaller pool

            log.critical(
                "PORTFOLIO SELECTOR hit max_tokens on attempt %d "
                "(in=%s out=%s) — halting scan after %d max_tokens attempts.",
                attempt, in_tok, out_tok, max_tokens_retries_used + 1,
            )
            try:
                from src.telegram_notifier import get_notifier
                get_notifier().send_alert(
                    alert_type="MAX_TOKENS",
                    task_name="portfolio-selector",
                    message=(
                        f"Selector blew the max_tokens cap on attempt {attempt} "
                        f"(in={in_tok}, out={out_tok}) "
                        f"after {max_tokens_retries_used} pool-truncation retry. "
                        f"Scan halted — investigate prompt size."
                    ),
                )
            except Exception as e:
                log.debug("Telegram max_tokens alert failed: %s", e)
            last_error = f"max_tokens (out={out_tok})"
            last_problems = [f"max_tokens cap hit on attempt {attempt} (out={out_tok})"]
            break

        if isinstance(result, dict) and not result.get("_error"):
            ok, problems = validate_selector_response(
                result, held_symbols, pool_symbols, pool_meta, config, allow_floor_breach,
                equity=float(context.get("equity", 0) or 0),
                system_state=context.get("system_state") or {},
            )
            if ok:
                log.info(
                    "PORTFOLIO SELECTOR succeeded on attempt %d/%d "
                    "(in=%s out=%s cache_read=%s)",
                    attempt, max_attempts,
                    result.get("_input_tokens"),
                    result.get("_output_tokens"),
                    result.get("_cache_read_tokens"),
                )
                soft = result.get("_validation_warnings") or []
                if soft:
                    log.info(
                        "PORTFOLIO SELECTOR accepted with %d soft warning(s): %s",
                        len(soft), soft[:5],
                    )
                # Phase 0: telemetry. Persist per-scan token usage so we can
                # spot drift toward the cap before it fails a scan, and warn
                # loudly when we creep above 80% of the configured ceiling.
                try:
                    _record_selector_token_usage(
                        config, result, allow_floor_breach=allow_floor_breach,
                    )
                except Exception as e:
                    log.debug("token-usage telemetry failed: %s", e)
                return result
            last_problems = problems
            log.warning("PORTFOLIO SELECTOR attempt %d/%d failed validation "
                        "(stop_reason=%s in=%s out=%s keys=%s): %s",
                        attempt, max_attempts,
                        result.get("_stop_reason"),
                        result.get("_input_tokens"),
                        result.get("_output_tokens"),
                        sorted(k for k in result.keys() if not k.startswith("_")),
                        problems[:5])
            try:
                _dump_selector_validation_failure(result, problems, attempt)
            except Exception as e:
                log.debug("Selector dump failed: %s", e)

            # 2026-05-11: detect identical-complaint thrash before burning
            # another Opus call. If the validator's normalized complaint set
            # (same symbols, same gate kinds) is identical to the previous
            # attempt, the model is cycling minor variants of an unachievable
            # response — short-circuit to the safety no-op.
            current_signature = _normalize_selector_problems(problems)
            if (
                short_circuit_on_repeat
                and prev_problem_signature is not None
                and current_signature == prev_problem_signature
                and len(current_signature) > 0
            ):
                log.critical(
                    "PORTFOLIO SELECTOR retry thrash detected — validator "
                    "complaint repeated identically on attempts %d and %d "
                    "(same %d (symbol, gate) tuples). Halting retry loop to "
                    "avoid token burn. signature=%s",
                    attempt - 1, attempt, len(current_signature),
                    sorted(current_signature)[:6],
                )
                last_problems = problems
                break
            prev_problem_signature = current_signature

            # Feedback-prompted retry for retryable problems (count or anti-stagnation).
            if (extra_retries_used < extra_retries_allowed
                    and _selector_problems_are_retryable(problems)):
                feedback = "Validation failed: " + " | ".join(problems[:5])
                feedback += (
                    "\nFix and re-emit the JSON. Honor the count rule and "
                    "anti-stagnation. For the new gates: any BUY/INCREASE that "
                    "fails the tape opportunity_score floor, the absolute "
                    "BUY floor, the distance-from-high gate, the late-day "
                    "freeze, the selector-rotation cooldown, the top-3 weight "
                    "ratio, or the risk_off count cap — convert that name to "
                    "PASS (or HOLD if held) and reallocate weight to a name "
                    "that actually clears the bar. If every top candidate in "
                    "the pool fails the same gate, return PASS for the slot "
                    "rather than cycling equivalent names — repeating the same "
                    "failing picks wastes tokens and produces the safety no-op. "
                    "Do NOT lower other names' scores to pass — drop offenders, "
                    "don't fudge."
                )
                ctx_with_feedback = {**context, "_validator_feedback": feedback}
                context = ctx_with_feedback  # next loop iteration uses this
                extra_retries_used += 1
                # do NOT count this as a normal attempt — extend by one
                max_attempts += 1
                log.info("PORTFOLIO SELECTOR retrying with validator feedback")
                continue

            # Truncation / off-contract responses: a clean retry has the best
            # shot. No feedback prompt — the prior context was fine, the model
            # just cut off. Don't burn the extra-retry budget on these.
            if _selector_problems_indicate_truncation(problems):
                log.info(
                    "PORTFOLIO SELECTOR attempt %d/%d looks truncated/off-contract; "
                    "will retry with a clean prompt", attempt, max_attempts,
                )
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
        result = _run_with_ai_cleanup(ai, pipeline.portfolio_verifier(context))
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
        result = _run_with_ai_cleanup(ai, pipeline.exit_arbiter_verdict(context))
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
        result = _run_with_ai_cleanup(ai, ai.call_agent(
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
        result = _run_with_ai_cleanup(ai, pipeline.earnings_gate_verdict(context))
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

    return _run_with_ai_cleanup(ai, _all())
