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
    final_action: str            # "buy" | "sell_short" | "pass"
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
            "direction_hypothesis": "long" if numeric_decision.combined_score > 0 else "short",
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
        if final_action not in ("buy", "sell_short", "pass"):
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
        kill_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Ask risk-manager agent to review the proposed book."""
        ctx = {
            "portfolio": portfolio_ctx,
            "proposed_trades": proposed_trades,
            "kill_switch_state": kill_state,
        }
        return await self.ai.call_agent(
            "risk-manager", ctx, task_type="trade_critical",
        )

    async def exit_arbiter_verdict(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Ask Opus 4.7 whether to close / reduce / hold a specific open position.
        ALL exits (including stall, technical-flip, bad-news, preclose, crypto)
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
        reason = info.get("one_sentence_reason", "")
        if isinstance(reason, str) and reason and ";" in reason:
            problems.append(f"per_symbol[{sym}].one_sentence_reason contains ';'")

    # Numeric sanity: weights sum + spy + cash ∈ [0.99, 1.01]
    try:
        weight_sum = sum(float(v) for v in target_weights.values())
        spy_t = float(result.get("spy_target_pct", 0) or 0)
        cash_t = float(result.get("cash_target_pct", 0) or 0)
        total = weight_sum + spy_t + cash_t
        if not (0.99 <= total <= 1.01):
            problems.append(f"weights+spy+cash sum out of bounds: {total:.3f}")
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
    """Synchronous Opus 4.7 single-symbol entry decision (used by crypto and
    any other path where we have one candidate and need a go/no-go).
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
        if abs(c.combined_score) >= min_score and c.action in ("buy", "sell_short", "hold")
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
