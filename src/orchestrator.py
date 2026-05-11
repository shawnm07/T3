"""End-to-end pipeline: gather signals → decide → size → execute. Entry + exit."""
from __future__ import annotations
import json
import logging
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.ai_pipeline import (
    AIVerdict, run_ai_on_candidates, run_earnings_gate, run_portfolio_arbiter,
    run_portfolio_selector, run_exit_arbiter, run_entry_arbiter_single,
)
from src.ai_research import AIResearcher
from src.alpaca_client import AlpacaClient
from src.config import Config
from src.candidate_scoring import (
    annotate_candidate_leadership,
    missed_breakout_candidates,
)
from src.cash_policy import (
    build_selector_cash_policy_decision,
    save_cash_policy,
    submit_cash_proxy_buy,
    sweep_cash_to_proxy_if_allowed,
)
from src.decision import DecisionEngine, TradeDecision
from src.discovery import Candidate, discover_candidates
from src.dynamic_watchlist import (
    remove_dynamic_watchlist_symbols,
    update_dynamic_watchlist,
)
from src.earnings import (
    EarningsInfo,
    build_preclose_earnings_profile,
    compute_earnings_research_score,
    fetch_earnings,
    within_window,
)
from src.executor import TradeExecutor
from src.fundamentals import compute_fundamentals
from src.intraday_tape import TapeSignal, compute_tape_signal
from src.journal import log_decision
from src.macro import MacroSignal, compute_macro
from src.market_data import get_market_data
from src.overnight import (
    OvernightSignal,
    build_preclose_edge,
    compute_sector_momentum,
    market_bias_from_spy,
    score_overnight,
)
from src.overnight_learning import (
    estimate_overnight_edge,
    record_preclose_candidates,
    resolve_overnight_outcomes,
)
from src.rebalance import compute_rebalance_plan
from src.risk import RiskManager
from src import sector_guard
from src.sentiment import score_news_for_symbol
from src.technicals import TechnicalSignal, compute_technicals, technicals_for_bars_df
from src.universe import build_stock_universe, sp500_sectors

log = logging.getLogger(__name__)

RESEARCH_DIR = Path(__file__).resolve().parents[1] / "data" / "research"
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)


def _save_research(name: str, payload: dict[str, Any]) -> Path:
    ts = pd.Timestamp.utcnow().strftime("%Y%m%dT%H%M%S")
    path = RESEARCH_DIR / f"{ts}_{name}.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


# ---------------------------------------------------------------------------
# Phase 0b: selector input slimming
# ---------------------------------------------------------------------------

# Fields dropped before sending the candidate pool to portfolio-selector. Each
# is either pure prose duplication of numeric fields the model already sees,
# or zero-valued noise on non-held candidates.
_SELECTOR_PRUNE_KEYS_ALWAYS = (
    # Prose narrative duplicating numeric *_rank / *_leader / *_relative_score.
    "sector_comparison_summary",
    "theme_comparison_summary",
    "peer_comparison_summary",
    # Duplicates candidate_priority_reasons.
    "discovery_priority_reasons",
)

# Zero/empty fields that are only meaningful for held positions; on fresh
# candidates they add noise without signal.
_SELECTOR_PRUNE_KEYS_NON_HELD = (
    "qty",
    "avg_entry_price",
    "market_value_usd",
    "abs_market_value_usd",
    "unrealized_pl_usd",
    "unrealized_plpc",
)


def _slim_selector_pool_blocks(pool: list[dict[str, Any]]) -> None:
    """Mutate the candidate pool in place to drop duplicate / noisy fields.

    Roughly halves the per-candidate payload (2.2KB → ~1.1KB measured on the
    2026-05-05 11:00 PDT scan that hit max_tokens). The selector still
    receives every numeric ranking signal — only narrative duplicates are
    removed. See EXECUTION_PLAN.md Phase 0b for the audit.
    """
    for block in pool:
        for k in _SELECTOR_PRUNE_KEYS_ALWAYS:
            block.pop(k, None)

        if not block.get("currently_held"):
            for k in _SELECTOR_PRUNE_KEYS_NON_HELD:
                block.pop(k, None)

        # momentum_profile.reasons duplicates fields the candidate already
        # exposes top-level (price_vs_vwap_pct, ema_state, recent_trend,
        # volume_trend, distance_from_high_pct...). min_score is a static
        # config knob the selector doesn't need to see per symbol.
        mp = block.get("momentum_profile")
        if isinstance(mp, dict):
            mp.pop("reasons", None)
            mp.pop("min_score", None)

        # peer_pressure: keep only the *signal* (which peer is stronger and
        # whether justification is required). Drop redundant numeric fields
        # already exposed elsewhere as peer_relative_score / peer_rank.
        pp = block.get("peer_pressure")
        if isinstance(pp, dict):
            slim = {}
            if pp.get("stronger_peer"):
                slim["stronger_peer"] = pp["stronger_peer"]
            if pp.get("requires_explicit_justification"):
                slim["must_justify"] = True
            if slim:
                block["peer_pressure"] = slim
            else:
                block.pop("peer_pressure", None)

        # position_lifecycle: keep only fields useful for the selector's
        # forward decision (when entered, what action). Drop the long
        # historical reason narrative — it biases the selector toward the
        # prior plan and is the largest sub-field.
        pl = block.get("position_lifecycle")
        if isinstance(pl, dict):
            slim_pl = {}
            if pl.get("entry_ts"):
                slim_pl["entry_ts"] = pl["entry_ts"]
            if pl.get("ai_action"):
                slim_pl["last_ai_action"] = pl["ai_action"]
            if pl.get("filled_avg_price") is not None:
                slim_pl["filled_avg_price"] = pl["filled_avg_price"]
            if slim_pl:
                block["position_lifecycle"] = slim_pl
            else:
                block.pop("position_lifecycle", None)

        # Strip None / null fields to shrink JSON.
        for k in [k for k, v in block.items() if v is None]:
            block.pop(k, None)


class TradingOrchestrator:
    def __init__(self, config: Config):
        self.cfg = config
        self.client = AlpacaClient(config)
        self.risk = RiskManager(config)
        self.engine = DecisionEngine(config)
        self.executor = TradeExecutor(self.client, config)
        self.ai = AIResearcher(config)
        self.cash_proxy_enabled = bool(config.get("cash_proxy", "enabled", default=False))
        self.cash_proxy_symbol = str(config.get("cash_proxy", "symbol", default="SPY"))
        self.cash_proxy_min = float(config.get("cash_proxy", "min_rebalance_usd", default=500))
        self.earnings_enabled = bool(config.get("earnings", "enabled", default=True))
        self.earnings_block_days = int(config.get("earnings", "block_entry_days", default=2))
        self.earnings_trim_days = int(config.get("earnings", "trim_exit_days", default=2))
        self.earnings_override = float(config.get("earnings", "high_conviction_override", default=0.85))
        self.earnings_ttl_hours = float(config.get("earnings", "cache_ttl_hours", default=24))
        self.earnings_use_ai_gate = bool(config.get("earnings", "use_ai_gate", default=True))
        # Day-of/day-before/day-2 minimum confidence for an AI 'hold' verdict
        # to actually hold. Below the threshold, 'hold' is downgraded to trim_50.
        self.earnings_day_0_1_hold_min_conf = float(
            config.get("earnings", "day_0_1_hold_min_confidence", default=0.90)
        )
        self.earnings_day2_hold_min_conf = float(
            config.get("earnings", "day2_hold_min_confidence", default=0.75)
        )
        self.rebalance_use_ai_arbiter = bool(config.get("rebalance", "use_ai_arbiter", default=True))
        # New-entry earnings blackout (separate from held-position trim window)
        self.entry_earnings_blackout_days = int(
            config.get("earnings", "new_entry_earnings_blackout_days", default=2)
        )
        self.entry_earnings_override = float(
            config.get("earnings", "new_entry_earnings_override_confidence", default=0.90)
        )
        # NOTE: legacy `rebalance.require_ai_above_*` knobs are no longer
        # consulted — there is no non-AI fallback. Hard rule: no AI → no trades.
        # Tracks whether the most recent rebalance handled SPY/cash via the AI
        # arbiter. When True, the post-scan deterministic auto-sweep is skipped
        # so the bot never overrides an explicit AI allocation decision.
        self._last_arbiter_set_spy_target: bool = False
        # Most-recent arbiter outputs surfaced for the scan summary (Telegram).
        self._last_opportunity_ranking: list[str] = []
        self._last_arbiter_skipped: str | None = None
        self._last_ai_target_weights: dict[str, float] | None = None
        self._last_ai_per_symbol: dict[str, dict[str, Any]] = {}
        self._last_ai_spy_target_pct: float | None = None
        self._last_ai_cash_target_pct: float | None = None

    def _is_cash_proxy(self, symbol: str) -> bool:
        return (
            self.cash_proxy_enabled
            and str(symbol or "").strip().upper() == str(self.cash_proxy_symbol or "").strip().upper()
        )

    def _resolve_trade_learning(self, phase: str) -> dict[str, Any] | None:
        try:
            from src.trade_learning import resolve_exit_learning_metrics
            result = resolve_exit_learning_metrics(
                self.cfg,
                self.client,
                cash_proxy_symbol=self.cash_proxy_symbol if self.cash_proxy_enabled else None,
            )
            if result and result.get("resolved"):
                log_decision({
                    "event": "trade_learning_resolved",
                    "phase": phase,
                    "result": result,
                })
            return result
        except Exception as exc:
            log.debug("trade learning resolve failed (%s): %s", phase, exc)
            return {"error": str(exc), "phase": phase}

    def _asset_ai_reject_reason(self, info: dict[str, Any]) -> str | None:
        status = str(info.get("status") or "").lower()
        if status != "active":
            return f"asset_not_active:{status or 'unknown'}"
        if info.get("tradable") is not True:
            return "asset_not_tradable"
        return None

    @staticmethod
    def _asset_lookup_failure_reason(exc: Exception) -> str:
        msg = str(exc).lower()
        if "404" in msg or "not found" in msg:
            return "asset_not_found"
        return "asset_lookup_failed"

    def _prune_untradable_candidates(
        self,
        candidates: list[Candidate],
        held_symbols: set[str],
    ) -> tuple[list[Candidate], list[dict[str, Any]]]:
        """Remove non-held candidates Alpaca does not verify as tradable."""
        held = {str(sym or "").upper() for sym in held_symbols}
        kept: list[Candidate] = []
        removed: list[dict[str, Any]] = []

        for cand in candidates or []:
            sym = str(cand.symbol or "").strip().upper()
            if not sym:
                continue
            if cand.is_held or sym in held or "/" in sym or self._is_cash_proxy(sym):
                kept.append(cand)
                continue
            try:
                asset = self.client.get_asset_info(sym)
            except Exception as exc:
                removed.append({
                    "symbol": sym,
                    "reason": self._asset_lookup_failure_reason(exc),
                    "error": str(exc),
                    "sources": list(cand.sources),
                })
                continue

            reason = self._asset_ai_reject_reason(asset)
            if reason:
                removed.append({
                    "symbol": sym,
                    "reason": reason,
                    "asset": asset,
                    "sources": list(cand.sources),
                })
                continue
            kept.append(cand)

        if not removed:
            return kept, []

        persisted_symbols = [
            row["symbol"]
            for row in removed
            if row.get("reason") != "asset_lookup_failed"
        ]
        dynamic_update: dict[str, Any] | None = None
        if persisted_symbols:
            try:
                dynamic_update = remove_dynamic_watchlist_symbols(
                    self.cfg,
                    persisted_symbols,
                    reason="alpaca_asset_not_ai_eligible",
                )
            except Exception as exc:
                dynamic_update = {"error": str(exc)}
                log.warning("[dynamic_watchlist] asset-prune removal failed: %s", exc)

        log_decision({
            "event": "candidate_pool_asset_pruned",
            "removed": removed,
            "dynamic_watchlist": dynamic_update,
        })
        log.info(
            "[selector] removed %d non-AI-eligible candidates after Alpaca asset check: %s",
            len(removed),
            ", ".join(f"{row['symbol']}:{row['reason']}" for row in removed),
        )
        return kept, removed

    def _get_proxy_position(self, positions):
        for p in positions or []:
            if self._is_cash_proxy(getattr(p, "symbol", "")):
                return p
        return None

    # ---- preclose veto circuit-breaker -------------------------------------
    # The exit-arbiter prompt biases hard toward 'hold' for positions with
    # intact technicals. On 2026-04-27 DELL was vetoed at preclose (directional
    # -0.05, tech 0.79) and bled out the next day. This breaker forces a 50%
    # trim once the same position has been vetoed N times in a row while
    # directional was negative.

    def _veto_state_path(self) -> Path:
        rel = self.cfg.get(
            "overnight", "veto_circuit_breaker", "state_file",
            default="data/state/preclose_veto_history.json",
        )
        return Path(__file__).resolve().parents[1] / rel

    def _load_veto_state(self) -> dict[str, Any]:
        path = self._veto_state_path()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}
        ttl = int(self.cfg.get("overnight", "veto_circuit_breaker", "ttl_days", default=7))
        cutoff = (date.today() - timedelta(days=ttl)).isoformat()
        cleaned = {
            sym: entry for sym, entry in data.items()
            if isinstance(entry, dict) and entry.get("last_date", "") >= cutoff
        }
        return cleaned

    def _save_veto_state(self, state: dict[str, Any]) -> None:
        path = self._veto_state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(state, indent=2))
        except OSError as e:
            log.warning("preclose veto state save failed: %s", e)

    def _record_preclose_veto(self, symbol: str) -> None:
        if not bool(self.cfg.get("overnight", "veto_circuit_breaker", "enabled", default=True)):
            return
        state = self._load_veto_state()
        entry = state.get(symbol) or {"count": 0, "last_date": ""}
        entry["count"] = int(entry.get("count", 0)) + 1
        entry["last_date"] = date.today().isoformat()
        state[symbol] = entry
        self._save_veto_state(state)

    def _reset_preclose_veto(self, symbol: str) -> None:
        state = self._load_veto_state()
        if symbol in state:
            state.pop(symbol, None)
            self._save_veto_state(state)

    def _preclose_veto_count(self, symbol: str) -> int:
        state = self._load_veto_state()
        entry = state.get(symbol) or {}
        return int(entry.get("count", 0))

    # ---- position lifecycle / fresh-exit guard -----------------------------

    def _position_lifecycle_path(self) -> Path:
        rel = self.cfg.get(
            "selector", "position_lifecycle_state_file",
            default="data/state/position_lifecycle.json",
        )
        return Path(__file__).resolve().parents[1] / rel

    def _load_position_lifecycle(self) -> dict[str, Any]:
        path = self._position_lifecycle_path()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save_position_lifecycle(self, state: dict[str, Any]) -> None:
        path = self._position_lifecycle_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        except OSError as exc:
            log.warning("position lifecycle save failed: %s", exc)

    @staticmethod
    def _parse_lifecycle_ts(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            return None
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    def _record_position_entry(
        self,
        symbol: str,
        *,
        source: str,
        execution: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        sym = str(symbol or "").strip().upper()
        if not sym or self._is_cash_proxy(sym) or "/" in sym:
            return
        state = self._load_position_lifecycle()
        context = dict(context or {})
        execution = dict(execution or {})
        state[sym] = {
            "entry_ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "filled_qty": execution.get("filled_qty"),
            "filled_avg_price": execution.get("filled_avg_price"),
            "order_id": execution.get("order_id"),
            "reason": context.get("reason") or context.get("one_sentence_reason"),
            "ai_action": context.get("ai_action"),
            "ai_confidence": context.get("ai_confidence") or context.get("confidence"),
            "opportunity_score": context.get("opportunity_score"),
        }
        self._save_position_lifecycle(state)

    def _clear_position_lifecycle(self, symbol: str) -> None:
        sym = str(symbol or "").strip().upper()
        if not sym:
            return
        state = self._load_position_lifecycle()
        if sym in state:
            state.pop(sym, None)
            self._save_position_lifecycle(state)

    def _position_lifecycle_context(self, symbol: str) -> dict[str, Any]:
        sym = str(symbol or "").strip().upper()
        entry = (self._load_position_lifecycle().get(sym) or {})
        if not isinstance(entry, dict):
            return {}
        ts = self._parse_lifecycle_ts(entry.get("entry_ts"))
        if ts is None:
            return {}
        age_minutes = max(0.0, (datetime.now(timezone.utc) - ts).total_seconds() / 60.0)
        cooldown = float(self.cfg.get("selector", "fresh_exit_cooldown_minutes", default=120) or 120)
        return {
            **entry,
            "age_minutes": round(age_minutes, 1),
            "fresh_exit_cooldown_minutes": cooldown,
            "fresh_exit_cooldown_active": age_minutes < cooldown,
        }

    def _predetermined_dust_sweep_for_buys(
        self,
        target_weights: dict[str, float] | None,
    ) -> list[dict[str, Any]]:
        """Phase 1a: dust-sweep off-target held positions BEFORE the buy phase.

        Runs the same deterministic check as the post-execution verifier
        (see ``_verify_portfolio_alignment``) but earlier in the scan so the
        proceeds can fund the same scan's buys. Honors the same fresh-entry
        guard. Returns a list of execution result dicts to append to the
        scan summary. Empty when nothing needs sweeping.
        """
        if not target_weights:
            return []
        try:
            account, positions = self.client.get_snapshot(force_refresh=True, log_detail=False)
        except Exception as e:
            log.warning("pre-buy dust-sweep: snapshot failed: %s", e)
            return []
        if not positions:
            return []
        guard_loss_floor = float(
            self.cfg.get("portfolio_verifier", "fresh_entry_loss_floor_pct",
                         default=-0.005) or -0.005
        )
        results: list[dict[str, Any]] = []
        for p in positions:
            sym = getattr(p, "symbol", None)
            if not sym or sym == self.cash_proxy_symbol:
                continue
            try:
                qty = abs(float(p.qty))
            except (TypeError, ValueError):
                continue
            if qty <= 0:
                continue
            tw = float(target_weights.get(sym, 0.0) or 0.0)
            if tw > 0:
                continue
            if self._verifier_dust_sweep_blocked_fresh(
                sym, p, loss_floor_pct=guard_loss_floor,
            ):
                continue
            log.info(
                "[selector] pre-buy dust-sweep: closing %s (qty=%s, target=0%%)",
                sym, qty,
            )
            try:
                exec_result = self.executor.close_position(
                    sym, reason="pre-buy dust-sweep target=0",
                )
            except Exception as e:
                log.warning("pre-buy dust-sweep failed for %s: %s", sym, e)
                continue
            if exec_result.ok:
                self._clear_position_lifecycle(sym)
            results.append({
                "symbol": sym,
                "side": "sell",
                "is_new_entry": False,
                "skipped": None,
                "execution": exec_result.to_dict() if hasattr(exec_result, "to_dict") else {
                    "ok": getattr(exec_result, "ok", False),
                    "filled_qty": getattr(exec_result, "filled_qty", None),
                    "order_id": getattr(exec_result, "order_id", None),
                },
                "label": "[selector] pre-buy dust-sweep",
                "qty_before": qty,
            })
        return results

    def _verifier_dust_sweep_blocked_fresh(
        self,
        symbol: str,
        position: Any,
        *,
        loss_floor_pct: float,
    ) -> bool:
        """Phase 1b: skip verifier dust-sweep for very-fresh entries.

        Returns True when the position was opened today by the same intraday
        scan flow AND it isn't already materially in the red. The selector
        flipping its target from 100% to 0% within an hour is the dominant
        churn mode (see EXECUTION_PLAN.md Phase 1b). Only block when:
          - position has a recorded entry_ts within today's session, AND
          - unrealized P&L pct >= ``loss_floor_pct`` (default -0.5%), AND
          - protective stop has not been breached (executor handles that).
        Logs a single WARN line per skip so operators can audit the guard.
        """
        sym = str(symbol or "").strip().upper()
        if not sym:
            return False
        ctx = self._position_lifecycle_context(sym)
        if not ctx:
            return False
        ts = self._parse_lifecycle_ts(ctx.get("entry_ts"))
        if ts is None:
            return False
        # Same-day check: in UTC, compare calendar date with now().
        now = datetime.now(timezone.utc)
        if ts.date() != now.date():
            return False
        try:
            plpc = float(getattr(position, "unrealized_plpc", 0.0) or 0.0)
        except (TypeError, ValueError):
            plpc = 0.0
        if plpc <= loss_floor_pct:
            # Already losing money — let the dust-sweep run.
            return False
        log.warning(
            "[verifier] %s dust-sweep BLOCKED by fresh-entry guard "
            "(entry_ts=%s, age=%.1fmin, plpc=%.4f, loss_floor=%.4f)",
            sym, ctx.get("entry_ts"), ctx.get("age_minutes", 0.0),
            plpc, loss_floor_pct,
        )
        return True

    def _fresh_exit_guard(self, action: Any, *, full_exit: bool) -> dict[str, Any] | None:
        """Phase 5 (2026-05-07): tiered minimum-hold cooldown.

        Tiers (configurable under ``selector:`` in config.yaml):
          age <  short_min  : require conf ≥ short_min_conf AND
                              (unrealized_plpc < short_floor_pl OR severe-reason
                              OR stop breach). Else: downgrade EXIT to
                              REDUCE short_trim_pct of the position.
          age <  medium_min : require conf ≥ medium_min_conf, else downgrade
                              EXIT to REDUCE medium_trim_pct.
          age >= medium_min : no cooldown gate.

        Returns None to allow the exit, or a dict to either skip or downgrade
        to a partial sell. Downgrade key: ``downgrade_to_reduce_pct`` in (0, 1].
        """
        lifecycle = self._position_lifecycle_context(getattr(action, "symbol", ""))
        if not lifecycle:
            return None
        age_min = float(lifecycle.get("age_minutes") or 0.0)
        short_min = float(self.cfg.get("selector", "fresh_exit_cooldown_short_min", default=90) or 90)
        medium_min = float(self.cfg.get("selector", "fresh_exit_cooldown_medium_min", default=240) or 240)
        if age_min >= medium_min:
            return None
        try:
            conf = float(getattr(action, "ai_confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            conf = 0.0
        try:
            plpc = float(getattr(action, "unrealized_plpc", 0.0) or 0.0)
        except (TypeError, ValueError):
            plpc = 0.0
        try:
            opportunity = float(getattr(action, "opportunity_score", 0.0) or 0.0)
        except (TypeError, ValueError):
            opportunity = 0.0
        reason = (
            f"{getattr(action, 'reason', '')} "
            f"{getattr(action, 'one_sentence_reason', '')} "
            f"{getattr(action, 'ai_action', '')}"
        ).lower()
        severe_terms = (
            "thesis gone", "signals gone", "breakdown", "failed continuation",
            "weak continuation", "underperform", "reversal", "bearish",
            "stop", "risk", "earnings", "bad news", "loss", "capital protection",
        )
        severe_reason = any(term in reason for term in severe_terms)
        severe_underperformance = plpc <= -0.015
        severe_opportunity_loss = opportunity > 0 and opportunity <= 25
        # Short tier: tightest bar
        if age_min < short_min:
            short_min_conf = float(self.cfg.get("selector", "fresh_exit_short_min_conf", default=0.85) or 0.85)
            short_floor_pl = float(self.cfg.get("selector", "fresh_exit_short_floor_pl", default=-0.005) or -0.005)
            if (
                conf >= short_min_conf
                or severe_reason
                or plpc <= short_floor_pl
                or severe_underperformance
                or severe_opportunity_loss
            ):
                return None
            trim_pct = float(self.cfg.get("selector", "fresh_exit_short_trim_pct", default=0.50) or 0.50)
            return {
                "reason": "fresh_exit_cooldown_short_trimmed",
                "full_exit": bool(full_exit),
                "ai_confidence": round(conf, 3),
                "min_confidence": short_min_conf,
                "tier": "short",
                "age_minutes": round(age_min, 1),
                "unrealized_plpc": round(plpc, 4),
                "opportunity_score": opportunity,
                "downgrade_to_reduce_pct": trim_pct,
                "lifecycle": lifecycle,
            }
        # Medium tier
        medium_min_conf = float(self.cfg.get("selector", "fresh_exit_medium_min_conf", default=0.75) or 0.75)
        if conf >= medium_min_conf or severe_reason or severe_underperformance or severe_opportunity_loss:
            return None
        trim_pct = float(self.cfg.get("selector", "fresh_exit_medium_trim_pct", default=0.33) or 0.33)
        return {
            "reason": "fresh_exit_cooldown_medium_trimmed",
            "full_exit": bool(full_exit),
            "ai_confidence": round(conf, 3),
            "min_confidence": medium_min_conf,
            "tier": "medium",
            "age_minutes": round(age_min, 1),
            "unrealized_plpc": round(plpc, 4),
            "opportunity_score": opportunity,
            "downgrade_to_reduce_pct": trim_pct,
            "lifecycle": lifecycle,
        }

    # ---- weekend protection enforcement ------------------------------------

    @staticmethod
    def _order_enum_text(value: Any) -> str:
        raw = getattr(value, "value", value)
        return str(raw or "").lower().rsplit(".", 1)[-1]

    def _protective_order_snapshot(self, order: Any) -> dict[str, Any]:
        return {
            "id": str(getattr(order, "id", "") or ""),
            "symbol": str(getattr(order, "symbol", "") or "").upper(),
            "side": self._order_enum_text(getattr(order, "side", "")),
            "type": self._order_enum_text(getattr(order, "type", "")),
            "time_in_force": self._order_enum_text(getattr(order, "time_in_force", "")),
            "status": self._order_enum_text(getattr(order, "status", "")),
            "qty": float(getattr(order, "qty", 0) or 0),
            "stop_price": (
                float(getattr(order, "stop_price", 0) or 0)
                if getattr(order, "stop_price", None) not in (None, "")
                else None
            ),
        }

    def _is_open_protective_stop(self, order: Any, symbol: str) -> bool:
        snap = self._protective_order_snapshot(order)
        return (
            snap["symbol"] == str(symbol or "").upper()
            and snap["side"] == "sell"
            and snap["type"] in {"stop", "stop_limit", "trailing_stop"}
            and snap["status"] not in {"filled", "canceled", "cancelled", "expired", "rejected"}
            and snap["qty"] > 0
        )

    def _weekend_stop_protection(
        self,
        position: Any,
        open_orders: list[Any],
        *,
        dry_run: bool,
    ) -> dict[str, Any]:
        sym = str(getattr(position, "symbol", "") or "").upper()
        qty = abs(float(getattr(position, "qty", 0) or 0))
        market_value = abs(float(getattr(position, "market_value", 0) or 0))
        current_price = float(
            getattr(position, "current_price", 0)
            or getattr(position, "avg_entry_price", 0)
            or 0
        )
        if not sym or qty <= 0:
            return {"symbol": sym, "status": "skipped", "reason": "no_position_qty"}
        whole_qty = int(qty)
        fractional_qty = max(0.0, qty - whole_qty)
        fractional_value = fractional_qty * current_price if current_price > 0 else 0.0
        allowed_dust = float(self.cfg.get(
            "overnight", "weekend", "allow_unprotected_fractional_dust_usd",
            default=500,
        ) or 500)
        tif = str(self.cfg.get(
            "overnight", "weekend", "protective_stop_tif", default="gtc",
        ) or "gtc").lower()
        base = {
            "symbol": sym,
            "qty": round(qty, 6),
            "whole_qty": whole_qty,
            "fractional_qty": round(fractional_qty, 6),
            "fractional_value": round(fractional_value, 2),
            "market_value": round(market_value, 2),
            "current_price": round(current_price, 4),
            "required_tif": tif,
        }
        if fractional_qty > 1e-6 and fractional_value > allowed_dust:
            reason = (
                f"weekend protection: fractional dust ${fractional_value:.0f} "
                f"exceeds allowed ${allowed_dust:.0f}"
            )
            if dry_run:
                return {**base, "status": "close_dry", "reason": reason}
            res = self.executor.close_position(sym, reason=reason)
            if res.ok:
                self._clear_position_lifecycle(sym)
            return {**base, "status": "closed" if res.ok else "close_failed",
                    "reason": reason, "execution": res.to_dict()}
        if whole_qty < 1:
            if market_value <= allowed_dust:
                return {**base, "status": "allowed_fractional_dust_only"}
            reason = "weekend protection: no whole shares available for GTC stop"
            if dry_run:
                return {**base, "status": "close_dry", "reason": reason}
            res = self.executor.close_position(sym, reason=reason)
            if res.ok:
                self._clear_position_lifecycle(sym)
            return {**base, "status": "closed" if res.ok else "close_failed",
                    "reason": reason, "execution": res.to_dict()}

        protective = [
            self._protective_order_snapshot(o)
            for o in (open_orders or [])
            if self._is_open_protective_stop(o, sym)
        ]
        gtc_qty = sum(
            float(o.get("qty") or 0)
            for o in protective
            if str(o.get("time_in_force") or "").lower() == "gtc"
        )
        if gtc_qty + 1e-6 >= whole_qty:
            return {**base, "status": "protected_existing_gtc", "orders": protective}
        if dry_run:
            return {**base, "status": "submit_gtc_stop_dry", "orders": protective}

        cancelled = self.executor._cancel_symbol_orders_before_sell(
            sym,
            reason="replace weekend DAY protection with GTC stop",
        )
        stop_ref = current_price or float(getattr(position, "avg_entry_price", 0) or 0)
        try:
            stop_price = self.risk.protective_stop_loss_price(stop_ref, None)
        except Exception:
            stop_price = round(max(0.01, stop_ref * 0.99), 2)
        if current_price > 0:
            buffer_pct = float(self.cfg.get(
                "opening_stop_guard", "rearm_below_market_buffer_pct", default=0.003,
            ) or 0.003)
            if stop_price >= current_price:
                stop_price = round(max(0.01, current_price * (1.0 - buffer_pct)), 2)
        try:
            order = self.client.submit_stop_loss(
                symbol=sym,
                qty=whole_qty,
                stop_price=stop_price,
                side="sell",
                tif=tif,
            )
            return {
                **base,
                "status": "protected_new_gtc",
                "cancelled_orders_before_stop": cancelled,
                "stop_order_id": str(getattr(order, "id", "") or ""),
                "stop_price": stop_price,
            }
        except Exception as exc:
            reason = f"weekend protection failed to submit {tif.upper()} stop: {exc}"
            log.error("[%s] %s", sym, reason)
            res = self.executor.close_position(sym, reason=reason)
            if res.ok:
                self._clear_position_lifecycle(sym)
            return {
                **base,
                "status": "closed" if res.ok else "close_failed",
                "reason": reason,
                "cancelled_orders_before_stop": cancelled,
                "execution": res.to_dict(),
            }

    def _enforce_weekend_protection(
        self,
        positions: list[Any],
        *,
        dry_run: bool,
    ) -> dict[str, Any]:
        if not bool(self.cfg.get("overnight", "weekend", "require_protective_stop", default=False)):
            return {"enabled": False}
        try:
            open_orders = self.client.get_open_orders()
        except Exception as exc:
            log.warning("weekend protection: open-order fetch failed: %s", exc)
            open_orders = []
        actions: list[dict[str, Any]] = []
        for p in positions or []:
            sym = str(getattr(p, "symbol", "") or "").upper()
            if not sym or "/" in sym or self._is_cash_proxy(sym):
                continue
            if abs(float(getattr(p, "qty", 0) or 0)) <= 0:
                continue
            actions.append(self._weekend_stop_protection(p, open_orders, dry_run=dry_run))
        return {"enabled": True, "actions": actions}

    def _veto_circuit_breaker_should_trim(self, symbol: str, directional: float) -> bool:
        if not bool(self.cfg.get("overnight", "veto_circuit_breaker", "enabled", default=True)):
            return False
        if directional >= 0:
            return False
        threshold = int(self.cfg.get(
            "overnight", "veto_circuit_breaker", "trim_after_consecutive_vetoes",
            default=2,
        ))
        # We just incremented the counter via _record_preclose_veto; the
        # current count *includes* this veto.
        return self._preclose_veto_count(symbol) >= threshold

    # ---- diversification pre-trade enforcement -----------------------------

    def _holdings_theme_state(
        self, positions: list[Any], equity: float,
    ) -> dict[str, dict[str, Any]]:
        """Compute per-theme {count, weight, members} for current holdings.

        Used by the pre-trade gate and the audit log so we don't have to wait
        for sector_guard to repair a violation post-execution.
        """
        sector_to_theme = sector_guard._build_sector_to_theme(self.cfg)
        symbol_overrides = sector_guard._symbol_overrides(self.cfg)
        proxy = (self.cash_proxy_symbol or "").upper() if self.cash_proxy_enabled else ""
        themes: dict[str, dict[str, Any]] = {}
        for p in positions:
            sym = (p.symbol or "").upper()
            if not sym or sym == proxy or "/" in sym:
                continue
            sector = ""
            try:
                # AlpacaClient enriches positions with sector via the universe
                # loader; fall back to "" if absent. theme_bucket_for handles
                # the missing-sector case via symbol_overrides.
                sector = str(getattr(p, "sector", "") or "")
            except Exception:
                pass
            theme = sector_guard.theme_bucket_for(
                sector, sector_to_theme, sym, symbol_overrides,
            )
            mv = abs(float(getattr(p, "market_value", 0) or 0))
            entry = themes.setdefault(theme, {"count": 0, "weight": 0.0, "members": []})
            entry["count"] += 1
            entry["weight"] += (mv / equity) if equity else 0.0
            entry["members"].append(sym)
        return themes

    def _audit_themes(self, positions: list[Any], equity: float) -> None:
        """Log a WARNING for any theme that already exceeds count or weight cap.

        Visible at scan start so a violation is caught on the first scan
        rather than buried inside a sector_guard repair event.
        """
        max_per_theme = int(self.cfg.get("diversification", "max_per_theme", default=3) or 3)
        max_w = float(
            self.cfg.get("diversification", "max_theme_weight_pct", default=0.50) or 0.50
        )
        state = self._holdings_theme_state(positions, equity)
        for theme, info in state.items():
            if info["count"] > max_per_theme:
                log.warning(
                    "[diversification] theme=%s count=%d > max_per_theme=%d members=%s",
                    theme, info["count"], max_per_theme, info["members"],
                )
            if info["weight"] > max_w + 1e-6:
                log.warning(
                    "[diversification] theme=%s weight=%.2f > max=%.2f members=%s",
                    theme, info["weight"], max_w, info["members"],
                )

    def _theme_cap_pre_block(
        self,
        sym: str,
        delta_notional: float,
        positions: list[Any],
        equity: float,
        pool_meta: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        """Block a new-entry / increase if it would breach the theme cap.

        Returns a block-dict to short-circuit, or None if OK to proceed.
        """
        max_per_theme = int(self.cfg.get("diversification", "max_per_theme", default=3) or 3)
        max_w = float(
            self.cfg.get("diversification", "max_theme_weight_pct", default=0.50) or 0.50
        )
        sector_to_theme = sector_guard._build_sector_to_theme(self.cfg)
        symbol_overrides = sector_guard._symbol_overrides(self.cfg)
        sector = (pool_meta or {}).get(sym, {}).get("sector", "") or ""
        cand_theme = sector_guard.theme_bucket_for(
            sector, sector_to_theme, sym, symbol_overrides,
        )
        if cand_theme == "other":
            return None  # untracked theme, no cap to enforce here
        state = self._holdings_theme_state(positions, equity)
        info = state.get(cand_theme, {"count": 0, "weight": 0.0, "members": []})
        # Only block NEW entries on count cap (existing positions can grow);
        # for adds, we'd block on weight only (caller passes their delta).
        proxy = (self.cash_proxy_symbol or "").upper() if self.cash_proxy_enabled else ""
        is_new_entry = sym.upper() not in {m.upper() for m in info["members"]}
        if is_new_entry and info["count"] >= max_per_theme:
            return {
                "reason": "theme_count_cap",
                "theme": cand_theme,
                "current_count": info["count"],
                "limit": max_per_theme,
                "members": info["members"],
            }
        added_weight = (float(delta_notional) / equity) if equity else 0.0
        new_weight = info["weight"] + added_weight
        if new_weight > max_w + 1e-6:
            return {
                "reason": "theme_weight_cap",
                "theme": cand_theme,
                "current_weight": round(info["weight"], 4),
                "added_weight": round(added_weight, 4),
                "new_weight_would_be": round(new_weight, 4),
                "limit": max_w,
                "members": info["members"],
            }
        return None

    def _minutes_to_close(self) -> float | None:
        """Return minutes remaining in today's regular session, or None if
        the broker clock is unavailable. Used to block selector new-entries
        in the last N minutes (preclose owns that window)."""
        try:
            clock = self.client.trading.get_clock()
        except Exception as e:
            log.debug("clock lookup failed: %s", e)
            return None
        if not getattr(clock, "is_open", False):
            return 0.0
        next_close = getattr(clock, "next_close", None)
        ts = getattr(clock, "timestamp", None)
        if next_close is None or ts is None:
            return None
        try:
            delta = (next_close - ts).total_seconds() / 60.0
        except Exception:
            return None
        return max(0.0, float(delta))

    def _is_late_session_no_new_entries(self) -> tuple[bool, float | None]:
        """Legacy helper for optional late-session entry blocking.

        Current config sets this cutoff to 0 because intraday scans may open
        continuation-confirmed entries; preclose owns explicit overnight buys.
        Returns (is_late, minutes_to_close). If the broker clock is
        unavailable, defaults to False so the bot still trades — better to
        let the existing gates catch it than to halt all new entries blindly.
        """
        cutoff = float(self.cfg.get(
            "scheduling", "late_session_no_new_entries_minutes", default=0,
        ))
        if cutoff <= 0:
            return (False, None)
        m = self._minutes_to_close()
        if m is None:
            return (False, None)
        return (m <= cutoff, m)

    def _session_gap_calendar_days(self) -> int:
        """Calendar-day gap between today's close and the next trading session.

        Used to decide whether a preclose should apply weekend-style hold
        rules. Returns 1 for normal weekday → next-day, 3 for Friday → Monday,
        4+ for pre-holiday weekends. Falls back to a Python weekday heuristic
        if the broker calendar is unavailable.
        """
        today = date.today()
        # Try the broker calendar first (handles holidays correctly).
        try:
            from alpaca.trading.requests import GetCalendarRequest
            req = GetCalendarRequest(start=today, end=today + timedelta(days=10))
            cal = self.client.trading.get_calendar(filters=req)
            future = [c for c in (cal or []) if getattr(c, "date", None) and c.date > today]
            if future:
                next_day = future[0].date
                return (next_day - today).days
        except Exception as e:
            log.debug("broker calendar lookup failed: %s — using weekday fallback", e)
        # Fallback: Friday → 3 days, Sat/Sun → next Mon, weekday → 1 day.
        wd = today.weekday()  # 0=Mon ... 6=Sun
        if wd == 4:
            return 3  # Friday → Monday
        if wd == 5:
            return 2  # Saturday → Monday
        if wd == 6:
            return 1  # Sunday → Monday
        return 1

    def _wait_order_ok(self, order) -> bool:
        """Wait for an order to fill enough to count as usable funding."""
        order_id = str(getattr(order, "id", "") or "")
        if not order_id:
            return False
        _, ok = self.client.wait_for_order_fill(
            order_id,
            timeout_s=float(self.cfg.get("execution", "fill_timeout_s", default=30)),
            poll_s=float(self.cfg.get("execution", "fill_poll_s", default=1.0)),
        )
        try:
            self.client.invalidate_snapshot()
        except Exception:
            pass
        return bool(ok)

    def _available_cash_above_floor(
        self, equity: float, floor_pct: float, *, soft: bool = True,
    ) -> float:
        """Cash available for new buys after honoring the in-flight cash floor.

        Strict (soft=False): always reserve `equity * floor_pct` of cash; if
        the account is below that, return 0.

        Soft (soft=True, default; toggle via cash.soft_floor_when_below):
        when the account is *already* below the requested floor at scan time
        (selector emitted high cash_target_pct but holdings haven't sold yet),
        the strict rule locks out every entry forever — there's nothing to
        reserve from. Soft mode treats the current cash ratio as the in-flight
        floor for this scan: allow buys up to actual confirmed cash, then rely
        on post-execution `_restore_cash_floor` / `_sweep_cash_to_proxy` to
        true the cash ratio back to the target afterward. See 2026-05-11
        16:22 scan where $5,150 cash vs. $30,964 required floor blocked AAON
        entirely despite the selector explicitly picking it.
        """
        try:
            account = self.client.get_account()
            cash = float(account.cash)
        except Exception as e:
            log.warning("cash budget: account fetch failed: %s", e)
            return 0.0
        floor_pct = max(0.0, float(floor_pct or 0.0))
        reserved = equity * floor_pct
        if soft and bool(self.cfg.get("cash", "soft_floor_when_below", default=True)):
            if cash + 0.01 < reserved and equity > 0:
                actual_pct = max(0.0, cash / equity)
                log.info(
                    "cash floor softened in-flight: actual=%.2f%% < target=%.2f%% "
                    "— allowing buys up to confirmed cash ($%.2f)",
                    actual_pct * 100.0, floor_pct * 100.0, cash,
                )
                return max(0.0, cash)
        return max(0.0, cash - reserved)

    def _sell_cash_proxy_for(self, notional: float, reason: str) -> bool:
        """Sell SPY cash-proxy by qty/percentage, avoiding stale notional oversells.

        The cash-proxy normally has a protective trailing stop attached (created
        by the trailing-stop bot after every entry). That stop reserves every
        share as `held_for_orders`, so Alpaca rejects any incremental sell with
        "insufficient qty available for order". Before any sell we cancel the
        proxy's open orders so the qty becomes available — the trailing-stop
        bot will recreate the stop on its next pass against the new position.
        See 2026-05-11 09:22 scan: $91K cash on the books but every BE/PWR/AAON
        buy skipped on `insufficient_confirmed_cash` because the proxy sell was
        rejected by Alpaca on `held_for_orders`.
        """
        if not self.cash_proxy_enabled or notional <= 0:
            return False
        positions = self.client.get_positions()
        proxy = self._get_proxy_position(positions)
        if not proxy:
            log.info("cash proxy: no %s held for %s", self.cash_proxy_symbol, reason)
            return False
        proxy_value = abs(float(proxy.market_value))
        proxy_qty = abs(float(proxy.qty))
        if proxy_value <= 0 or proxy_qty <= 0:
            return False
        # Release any held_for_orders reservation (typically the trailing stop)
        # so the qty actually becomes available for this sell.
        try:
            cancelled = self.client.cancel_open_orders_for_symbol(
                self.cash_proxy_symbol,
            )
            if cancelled:
                log.info(
                    "Cash-proxy funding: cancelled %d open %s order(s) before sell (%s)",
                    cancelled, self.cash_proxy_symbol, reason,
                )
        except Exception as e:
            log.warning(
                "Cash-proxy funding: cancel open orders for %s failed: %s",
                self.cash_proxy_symbol, e,
            )
        sell_value = min(notional, proxy_value)
        try:
            if sell_value >= proxy_value * 0.98:
                order = self.client.close_position(self.cash_proxy_symbol, percentage=100)
                log.info("Cash-proxy funding: closing all %s for %s (need $%.0f)",
                         self.cash_proxy_symbol, reason, notional)
            else:
                sell_qty = min(proxy_qty * 0.999, (sell_value / proxy_value) * proxy_qty)
                sell_qty = round(max(0.0, sell_qty), 6)
                if sell_qty <= 0:
                    return False
                order = self.client.close_position(self.cash_proxy_symbol, qty=sell_qty)
                log.info("Cash-proxy funding: selling %.6f %s for %s (need $%.0f)",
                         sell_qty, self.cash_proxy_symbol, reason, notional)
            return self._wait_order_ok(order)
        except Exception as e:
            log.warning("Cash-proxy sell failed: %s", e)
            return False

    def _ensure_cash_for(
        self,
        notional: float,
        equity: float,
        floor_pct: float | None = None,
        buffer_usd: float = 50.0,
    ) -> bool:
        """Before opening a new position: if real cash is below (notional + floor),
        sell enough cash-proxy (SPY) to cover. Returns True if funding is now ok."""
        notional = max(0.0, float(notional or 0.0))
        reserve_pct = (
            float(floor_pct)
            if floor_pct is not None
            else float(self.risk.cash_reserve_min_pct)
        )
        try:
            account = self.client.get_account()
            cash = float(account.cash)
        except Exception as e:
            log.warning("ensure_cash: account fetch failed: %s", e)
            return False
        floor = equity * max(0.0, reserve_pct)
        shortfall = (notional + floor) - cash
        if shortfall <= 0:
            return True
        if not self.cash_proxy_enabled:
            log.warning("ensure_cash: need $%.0f but cash is $%.0f and cash-proxy disabled",
                        notional + floor, cash)
            return False
        sold = self._sell_cash_proxy_for(shortfall + buffer_usd, "fund trade")
        if not sold:
            log.warning("ensure_cash: unable to fund $%.0f shortfall before buy", shortfall)
            return False
        try:
            account = self.client.get_account()
            cash = float(account.cash)
        except Exception as e:
            log.warning("ensure_cash: post-funding account fetch failed: %s", e)
            return False
        ok = cash >= (notional + floor)
        if not ok:
            log.warning(
                "ensure_cash: confirmed cash $%.0f still below required $%.0f "
                "(notional=$%.0f floor=$%.0f)",
                cash, notional + floor, notional, floor,
            )
        return ok

    def _funded_buy_notional(
        self,
        symbol: str,
        requested_notional: float,
        equity: float,
        floor_pct: float,
        context: str,
    ) -> float:
        """Return the buy notional allowed by confirmed cash after funding attempts.

        Phase 2b (2026-05-05): if the funding cap shrinks the order below
        ``cash.cap_drop_threshold_pct`` of its requested size, DROP the buy
        entirely instead of submitting a stub. Today's scan #3 produced
        $609 single-share buys of GEV/GOOGL/MRVL when each was meant to be
        a $7-8K position — those stubs were no-ops that immediately got
        stopped out and tied up a slot. Better to fail loudly and let the
        next scan retry with full cash.
        """
        requested = round(max(0.0, float(requested_notional or 0.0)), 2)
        if requested <= 0:
            return 0.0
        funding_ok = self._ensure_cash_for(requested, equity, floor_pct=floor_pct)
        if not funding_ok:
            log.warning("%s: funding incomplete; capping %s buy to confirmed cash",
                        context, symbol)
        available = self._available_cash_above_floor(equity, floor_pct)
        allowed = round(min(requested, available), 2)
        min_trade = float(self.cfg.get("risk", "min_trade_usd", default=500))
        if allowed + 0.01 < requested:
            log.warning("%s: capped %s buy $%.0f -> $%.0f to preserve %.1f%% cash floor",
                        context, symbol, requested, allowed, floor_pct * 100)
        if allowed < min_trade:
            log.warning("%s: skipping %s buy; allowed $%.0f below min trade $%.0f",
                        context, symbol, allowed, min_trade)
            return 0.0
        # Phase 2b: drop sub-threshold caps instead of stubbing.
        cap_drop_pct = float(self.cfg.get(
            "cash", "cap_drop_threshold_pct", default=0.40,
        ) or 0.40)
        if requested > 0 and (allowed / requested) < cap_drop_pct and not (
            requested - allowed < 50
        ):
            log.warning(
                "%s: DROPPING %s buy — cash-capped to %.0f%% of target "
                "(target=$%.0f, allowed=$%.0f). Skipping the slot.",
                context, symbol, (allowed / requested) * 100, requested, allowed,
            )
            return 0.0
        return allowed

    def _sweep_cash_to_proxy(
        self,
        equity: float,
        cash_policy_decision: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """After trades settle, park excess cash in SPY only when policy allows."""
        if not self.cash_proxy_enabled:
            return None
        action = sweep_cash_to_proxy_if_allowed(
            self.client,
            self.cfg,
            equity,
            policy=cash_policy_decision,
            reason="scan_idle_cash_sweep",
        )
        if not action:
            return None
        if action.get("action") == "buy_proxy":
            log.info(
                "Swept $%.0f idle cash into %s (policy=%s floor=$%.0f)",
                float(action.get("notional") or 0),
                self.cash_proxy_symbol,
                (action.get("cash_policy") or {}).get("mode"),
                float(action.get("floor") or 0),
            )
        elif action.get("skipped"):
            log.info(
                "Cash-proxy sweep skipped: %s (policy=%s)",
                action.get("skipped"),
                (action.get("cash_policy") or {}).get("mode"),
            )
        return action

    def _restore_cash_floor(self, equity: float) -> None:
        """If cash has dipped below the minimum reserve, immediately sell SPY proxy
        to restore it. Called at the top of each scan and rebalance so we never
        start a session with a negative or dangerously thin cash balance."""
        self._ensure_cash_for(
            0.0,
            equity,
            floor_pct=float(self.risk.cash_reserve_min_pct),
            buffer_usd=100.0,
        )

    # ---------- macro ----------
    def macro_brief(self) -> MacroSignal:
        universe = build_stock_universe(self.cfg)[:60]  # sample for breadth
        macro = compute_macro(self.client, breadth_symbols=universe)
        log.info(
            "Macro: regime=%s score=%.2f spy_trend=%.2f vix=%s breadth=%s",
            macro.regime, macro.score, macro.spy_trend, macro.vix_regime,
            f"{macro.breadth_pct_above_50:.0%}" if macro.breadth_pct_above_50 else "n/a",
        )
        return macro

    def _detect_scan_type(self) -> str:
        """Return 'FIRST', 'MIDDAY', or 'UNKNOWN' based on current Eastern Time.

        Deterministic and filesystem-free. The scheduled scan times are:
          10:00 ET → FIRST  (window: 09:30–11:00 ET)
          11:00, 12:00, 13:00, 14:00, 15:00 ET → MIDDAY
            (window: 11:00–16:00 ET)
        Anything outside market hours returns UNKNOWN and earnings checks are
        skipped (fail-safe: never assume first scan).
        """
        et_now = pd.Timestamp.now(tz="America/New_York")
        et_min = et_now.hour * 60 + et_now.minute
        if 9 * 60 + 30 <= et_min < 11 * 60:
            return "FIRST"
        if 11 * 60 <= et_min <= 16 * 60:
            return "MIDDAY"
        return "UNKNOWN"

    # ---------- screening ----------
    def technical_screen(self, symbols: list[str], top_n: int = 40) -> list[TechnicalSignal]:
        """Get bars for universe, compute technicals, return top-N absolute score."""
        signals: list[TechnicalSignal] = []
        batch_size = 100
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            try:
                bars = self.client.get_stock_bars(batch, lookback_days=252)
            except Exception as e:
                log.warning("Bars batch %d failed: %s", i, e)
                continue
            batch_signals = technicals_for_bars_df(bars)
            signals.extend(batch_signals.values())
        signals.sort(key=lambda s: abs(s.score), reverse=True)
        return signals[:top_n]

    # ---------- per-symbol deep dive ----------
    def evaluate_symbol(
        self,
        tech: TechnicalSignal,
        macro: MacroSignal,
        news_items: list,
    ) -> TradeDecision:
        fund = compute_fundamentals(tech.symbol)
        sent = score_news_for_symbol(tech.symbol, news_items)
        earnings = (
            fetch_earnings(tech.symbol, ttl_hours=self.earnings_ttl_hours)
            if self.earnings_enabled else None
        )

        details: dict[str, Any] = {
            "technical": tech.to_dict(),
            "sentiment": sent.to_dict(),
            "macro": macro.to_dict(),
        }
        if fund:
            details["fundamental"] = fund.to_dict()
        if earnings:
            details["earnings"] = earnings.to_dict()

        # Risk alignment: penalize long entries in risk-off regimes.
        risk_score = 0.0
        if macro.regime == "risk_off" and tech.score > 0:
            risk_score = -0.3
        elif macro.regime == "risk_on" and tech.score > 0:
            risk_score = 0.2

        decision = self.engine.decide(
            symbol=tech.symbol,
            technical_score=tech.score,
            fundamental_score=fund.score if fund else None,
            sentiment_score=sent.score,
            macro_score=macro.score,
            risk_score=risk_score,
            signal_details=details,
        )
        log_decision({"symbol": tech.symbol, "decision": decision.to_dict()})
        return decision

    # ---------- portfolio signal bundle (shared by exits + rebalance) ----------
    def _portfolio_signals(self, macro: MacroSignal) -> dict[str, Any]:
        """Fetch bars+news for held positions and compute tech/sent/numeric-decision
        per position. Shared input for both exit evaluation and rebalance planning.
        """
        positions = self.client.get_positions()
        # Non-cash-proxy equity positions only
        holdings = [p for p in positions if "/" not in p.symbol and not self._is_cash_proxy(p.symbol)]
        symbols = [p.symbol for p in holdings]
        if not symbols:
            return {"positions": positions, "holdings": [], "tech_map": {},
                    "sent_map": {}, "numeric": {}, "earnings_map": {}, "news": [],
                    "intraday_bars": None}
        try:
            bars = self.client.get_stock_bars(symbols, lookback_days=252)
        except Exception as e:
            log.warning("Portfolio signals bars fetch failed: %s", e)
            return {"positions": positions, "holdings": holdings, "tech_map": {},
                    "sent_map": {}, "numeric": {}, "earnings_map": {}, "news": [],
                    "intraday_bars": None}
        tech_map = technicals_for_bars_df(bars)
        news = self.client.get_news(symbols=symbols, limit=80, days_back=3)
        intraday_bars = None
        try:
            intraday_bars = self._fetch_intraday(symbols, minutes=5)
        except Exception as e:
            log.info("Portfolio signals intraday fetch failed: %s", e)
        sent_map: dict[str, Any] = {}
        numeric: dict[str, TradeDecision] = {}
        earnings_map: dict[str, EarningsInfo] = {}
        for p in holdings:
            sym = p.symbol
            tech = tech_map.get(sym)
            if tech is None:
                continue
            sent = score_news_for_symbol(sym, news)
            sent_map[sym] = sent
            fund = compute_fundamentals(sym)
            earnings = (
                fetch_earnings(sym, ttl_hours=self.earnings_ttl_hours)
                if self.earnings_enabled else None
            )
            if earnings:
                earnings_map[sym] = earnings
            details: dict[str, Any] = {
                "technical": tech.to_dict(),
                "sentiment": sent.to_dict(),
                "macro": macro.to_dict(),
            }
            if fund:
                details["fundamental"] = fund.to_dict()
            if earnings:
                details["earnings"] = earnings.to_dict()
            risk_score = 0.0
            if macro.regime == "risk_off" and tech.score > 0:
                risk_score = -0.3
            elif macro.regime == "risk_on" and tech.score > 0:
                risk_score = 0.2
            numeric[sym] = self.engine.decide(
                symbol=sym,
                technical_score=tech.score,
                fundamental_score=fund.score if fund else None,
                sentiment_score=sent.score,
                macro_score=macro.score,
                risk_score=risk_score,
                signal_details=details,
            )
        return {"positions": positions, "holdings": holdings, "tech_map": tech_map,
                "sent_map": sent_map, "numeric": numeric, "news": news,
                "earnings_map": earnings_map, "intraday_bars": intraday_bars}

    def _enrich_selector_candidates(
        self,
        portfolio: dict[str, Any],
        candidates: list[Candidate],
        macro: MacroSignal,
    ) -> dict[str, Any]:
        """Add technical, sentiment, numeric, and earnings data for new names.

        Held symbols already arrive through ``_portfolio_signals``. The selector
        also needs the same basic risk/event data for newly discovered names so
        it cannot accidentally buy into an imminent earnings event.
        """
        symbols = sorted({
            c.symbol for c in candidates
            if c.symbol and "/" not in c.symbol and not self._is_cash_proxy(c.symbol)
        })
        if not symbols:
            return portfolio

        tech_map = dict(portfolio.get("tech_map", {}) or {})
        sent_map = dict(portfolio.get("sent_map", {}) or {})
        numeric = dict(portfolio.get("numeric", {}) or {})
        earnings_map = dict(portfolio.get("earnings_map", {}) or {})

        missing_tech = [s for s in symbols if s not in tech_map]
        if missing_tech:
            try:
                bars = self.client.get_stock_bars(missing_tech, lookback_days=252)
                tech_map.update(technicals_for_bars_df(bars))
            except Exception as e:
                log.warning("[selector] candidate technical enrichment failed: %s", e)

        try:
            news = self.client.get_news(symbols=symbols, limit=100, days_back=3)
        except Exception as e:
            log.warning("[selector] candidate news enrichment failed: %s", e)
            news = portfolio.get("news", []) or []

        for sym in symbols:
            tech = tech_map.get(sym)
            if tech is None:
                continue
            sent = sent_map.get(sym) or score_news_for_symbol(sym, news)
            sent_map[sym] = sent
            fund = compute_fundamentals(sym)
            earnings = earnings_map.get(sym)
            if earnings is None and self.earnings_enabled:
                try:
                    earnings = fetch_earnings(sym, ttl_hours=self.earnings_ttl_hours)
                except Exception as e:
                    log.warning("[%s] selector earnings enrichment failed: %s", sym, e)
                    earnings = None
            if earnings:
                earnings_map[sym] = earnings
            details: dict[str, Any] = {
                "technical": tech.to_dict(),
                "sentiment": sent.to_dict(),
                "macro": macro.to_dict(),
            }
            if fund:
                details["fundamental"] = fund.to_dict()
            if earnings:
                details["earnings"] = earnings.to_dict()
            risk_score = 0.0
            if macro.regime == "risk_off" and tech.score > 0:
                risk_score = -0.3
            elif macro.regime == "risk_on" and tech.score > 0:
                risk_score = 0.2
            numeric[sym] = self.engine.decide(
                symbol=sym,
                technical_score=tech.score,
                fundamental_score=fund.score if fund else None,
                sentiment_score=sent.score,
                macro_score=macro.score,
                risk_score=risk_score,
                signal_details=details,
            )

        portfolio["tech_map"] = tech_map
        portfolio["sent_map"] = sent_map
        portfolio["numeric"] = numeric
        portfolio["earnings_map"] = earnings_map
        portfolio["news"] = news
        log.info(
            "[selector] enriched %d candidate(s): tech=%d sentiment=%d earnings=%d",
            len(symbols), len(tech_map), len(sent_map), len(earnings_map),
        )
        return portfolio

    @staticmethod
    def _selector_entry_confidence(info: dict[str, Any]) -> float:
        raw = info.get("confidence")
        if raw is None:
            raw = float(info.get("opportunity_score", 0) or 0) / 100.0
        try:
            conf = float(raw)
        except (TypeError, ValueError):
            conf = 0.0
        return max(0.0, min(1.0, conf))

    @staticmethod
    def _cap_sizing_notional(
        sizing,
        cap_notional: float,
        reason: str,
    ):
        cap = round(max(0.0, float(cap_notional or 0.0)), 2)
        if cap <= 0 or cap >= sizing.notional:
            return sizing
        qty = round(cap / sizing.entry, 4) if sizing.entry else 0.0
        risk_usd = sizing.risk_usd * (cap / sizing.notional) if sizing.notional else 0.0
        limits = dict(sizing.limits or {})
        limits["post_risk_cap_reason"] = reason
        limits["post_risk_cap_notional"] = cap
        return replace(
            sizing,
            qty=qty,
            notional=qty * sizing.entry,
            risk_usd=risk_usd,
            reasoning=f"{sizing.reasoning}; {reason}",
            limits=limits,
        )

    def _selector_entry_earnings_block(
        self,
        sym: str,
        confidence: float,
        earnings_map: dict[str, EarningsInfo],
    ) -> dict[str, Any] | None:
        """Phase 7 (2026-05-07): research-gated pre-earnings entry.

        Replaces the previous "hard block days 0-1, conf>=0.90 day 2" rule
        with an evidence-based gate. The bot computes an
        ``earnings_research_score`` (beat history + analyst PT trend +
        implied move + sentiment) and decides:

        - score >= research_score_strong (default 0.30): allow normal entry.
        - score in [research_score_neutral, strong): require confidence
          >= research_neutral_min_selector_conf (default 0.65).
        - score < research_negative_floor AND days_until <= 1: block (the
          bot has affirmative negative evidence).
        - days_until >= 3 (or None): no block.

        Legacy ``research_gate_enabled=false`` falls back to the prior
        hard-block behavior.
        """
        if not self.earnings_enabled:
            return None
        einfo = earnings_map.get(sym)
        days_until = einfo.days_until if einfo else None
        if days_until is None or days_until < 0:
            return None
        if days_until > self.entry_earnings_blackout_days:
            return None

        if not bool(self.cfg.get("earnings", "research_gate_enabled", default=True)):
            # Legacy hard block path — kept for the safety toggle.
            if days_until <= 1:
                return {
                    "symbol": sym,
                    "days_until_earnings": days_until,
                    "next_earnings_date": einfo.next_date,
                    "confidence": round(confidence, 3),
                    "override_confidence": None,
                    "blackout_days": self.entry_earnings_blackout_days,
                    "reason": "hard_block_day_0_or_1",
                }
            if confidence >= self.entry_earnings_override:
                return None
            return {
                "symbol": sym,
                "days_until_earnings": days_until,
                "next_earnings_date": einfo.next_date,
                "confidence": round(confidence, 3),
                "override_confidence": self.entry_earnings_override,
                "blackout_days": self.entry_earnings_blackout_days,
                "reason": "below_override_confidence",
            }

        # Research-gated path
        try:
            from src.earnings import compute_earnings_research_score
            ttl = float(self.cfg.get("earnings", "research_cache_ttl_hours", default=12) or 12)
            research = compute_earnings_research_score(sym, ttl_hours=ttl)
        except Exception as e:
            log.debug("earnings research score for %s failed: %s", sym, e)
            research = {"score": 0.0, "components": {}, "available_components": []}
        score = float(research.get("score") or 0.0)
        strong = float(self.cfg.get("earnings", "research_score_strong", default=0.30) or 0.30)
        neutral = float(self.cfg.get("earnings", "research_score_neutral", default=0.0) or 0.0)
        neutral_min_conf = float(
            self.cfg.get("earnings", "research_neutral_min_selector_conf", default=0.65) or 0.65
        )
        negative_floor = float(self.cfg.get("earnings", "research_negative_floor", default=0.0) or 0.0)

        if score >= strong:
            return None  # strong setup → normal entry
        if score >= neutral:
            if confidence >= neutral_min_conf:
                return None
            return {
                "symbol": sym,
                "days_until_earnings": days_until,
                "next_earnings_date": einfo.next_date,
                "confidence": round(confidence, 3),
                "research_score": score,
                "research_threshold": strong,
                "neutral_min_confidence": neutral_min_conf,
                "blackout_days": self.entry_earnings_blackout_days,
                "reason": "below_neutral_confidence_for_research_score",
            }
        # score < negative_floor: block only when day 0 or 1 (affirmative negative evidence)
        if score < negative_floor and days_until <= 1:
            return {
                "symbol": sym,
                "days_until_earnings": days_until,
                "next_earnings_date": einfo.next_date,
                "confidence": round(confidence, 3),
                "research_score": score,
                "negative_floor": negative_floor,
                "blackout_days": self.entry_earnings_blackout_days,
                "reason": "negative_research_score_in_window",
            }
        # Otherwise allow but note the soft signal — caller may downsize.
        return None

    # ---------- exits ----------
    def evaluate_exits(
        self,
        macro: MacroSignal,
        portfolio: dict[str, Any] | None = None,
        scan_type: str = "UNKNOWN",
    ) -> list[tuple[str, str]]:
        """Return list of (symbol, reason) to close. AI IS THE ONLY AUTHORITY.

        Deterministic signals (technical flip, stalled momentum, bad news,
        earnings window) are assembled into a structured payload and sent to
        the Opus 4.7 exit-arbiter. NOTHING CLOSES WITHOUT AI APPROVAL.
        If AI is unavailable we HOLD (fail-safe). The bot does not make
        close decisions on its own.

        scan_type controls earnings-risk gating:
          "FIRST"   → earnings gate runs; earnings-window positions evaluated by AI
          "MIDDAY"  → earnings-window positions FROZEN (no exit of any kind)
          "UNKNOWN" → earnings checks skipped (fail-safe: never assume first scan)
        Pre-close earnings handling is done in run_preclose(), not here.
        """
        closes: list[tuple[str, str]] = []
        portfolio = portfolio or self._portfolio_signals(macro)
        holdings = portfolio.get("holdings", [])
        tech_map = portfolio.get("tech_map", {})
        sent_map = portfolio.get("sent_map", {})
        earnings_map = portfolio.get("earnings_map", {})
        numeric = portfolio.get("numeric", {})
        intraday_bars = portfolio.get("intraday_bars")
        if not holdings or not tech_map:
            return closes

        if not self.ai.available():
            log.critical(
                "evaluate_exits: AI (Opus 4.7) unavailable — NO exits executed "
                "(fail-safe: no trade may run without AI approval). holdings=%d",
                len(holdings),
            )
            return closes

        stall_thr = float(self.cfg.get("risk", "exit_stall_threshold", default=0.10))
        min_exit_conf = float(self.cfg.get("exit_arbiter", "min_confidence", default=0.55))
        daily_bars = None
        held_syms = [p.symbol for p in holdings if "/" not in p.symbol]
        if intraday_bars is None and held_syms:
            try:
                intraday_bars = self._fetch_intraday(held_syms, minutes=5)
            except Exception as e:
                log.info("evaluate_exits: intraday fetch failed: %s", e)
        if held_syms:
            try:
                daily_bars = self.client.get_stock_bars(held_syms, lookback_days=30)
            except Exception:
                daily_bars = None

        if scan_type == "FIRST":
            log.info(
                "evaluate_exits: Earnings-risk check RUNNING (first scan) — "
                "earnings-window positions will be evaluated by AI gate"
            )
        elif scan_type == "MIDDAY":
            log.info(
                "evaluate_exits: Earnings-risk check SKIPPED (intraday scan — "
                "only runs first + pre-close). Earnings-window positions are FROZEN."
            )
        else:
            log.info(
                "evaluate_exits: scan_type=UNKNOWN — earnings-risk checks SKIPPED "
                "(fail-safe: never assume first scan outside scheduled windows)"
            )

        for p in holdings:
            if p.symbol not in tech_map:
                continue
            tech = tech_map[p.symbol]
            sent = sent_map.get(p.symbol)
            sent_score = sent.score if sent else 0.0
            plpc = float(p.unrealized_plpc) if hasattr(p, "unrealized_plpc") else 0.0

            # Deterministic triggers become TRIGGER FLAGS in the AI payload —
            # they never fire a trade on their own.
            flipped = tech.score < -0.3
            bad_news = sent_score < -0.5
            stalled = tech.score < stall_thr
            intraday_chart = self._intraday_chart_for(intraday_bars, p.symbol, daily_bars)
            momentum_exit = self._momentum_exit_signal(intraday_chart)

            einfo = earnings_map.get(p.symbol) if self.earnings_enabled else None
            in_earnings_window = bool(einfo and within_window(einfo, self.earnings_trim_days))

            # The earnings gate is itself an Opus 4.7 agent. If it returns close
            # we treat that as the exit-arbiter verdict; if it says trim we log
            # and defer. Otherwise we route everything through the generic exit
            # arbiter. In both paths the bot is *never* the decision-maker.
            #
            # FIRST scan: AI earnings gate runs; gate verdict determines action.
            # MIDDAY scan: position is FROZEN — no exit of any kind is allowed,
            #   including technical, sentiment, or any other exit path.
            # UNKNOWN / pre-close: earnings checks skipped (pre-close uses run_preclose()).
            if in_earnings_window and scan_type == "FIRST":
                log.info(
                    "[%s] Earnings-risk check RUNNING (first scan) — earnings in %dd",
                    p.symbol, einfo.days_until,
                )
                verdict, reason = self._earnings_gate_decision(
                    p=p, einfo=einfo, tech=tech, sent=sent,
                    numeric=numeric.get(p.symbol), macro=macro,
                    plpc=plpc,
                )
                if verdict == "close":
                    closes.append((p.symbol, reason))
                    continue
                if verdict == "trim_50":
                    log.info("[%s] earnings gate: trim_50 — deferring to rebalance arbiter", p.symbol)
                    continue
                if verdict == "hold":
                    # AI said hold — skip all secondary exit logic this scan.
                    continue
                # verdict "skip_no_ai" (fail-safe): hold, skip other exit checks.
                continue
            elif in_earnings_window and scan_type == "MIDDAY":
                # FREEZE: earnings-window positions must not be touched intraday.
                # No technical, sentiment, or any other exit is permitted.
                log.info(
                    "[%s] Earnings-window position SKIPPED entirely during intraday scan "
                    "(earnings in %dd — frozen until first/pre-close scan)",
                    p.symbol, einfo.days_until,
                )
                continue
            elif in_earnings_window:
                # UNKNOWN scan type: skip earnings checks (fail-safe).
                log.info(
                    "[%s] Earnings-window position SKIPPED (scan_type=UNKNOWN — fail-safe hold)",
                    p.symbol,
                )
                continue

            # If no candidate exit signal, don't burn an Opus call.
            if not (flipped or bad_news or stalled or momentum_exit.get("triggered")):
                continue

            num_dec = numeric.get(p.symbol)
            ctx = {
                "symbol": p.symbol,
                "side": "long",
                "qty": str(p.qty),
                "market_value": abs(float(p.market_value)),
                "unrealized_plpc": round(plpc, 4),
                "current_price": float(tech.price) if tech.price is not None else None,
                "atr": float(tech.atr) if tech.atr is not None else None,
                "technical": tech.to_dict(),
                "intraday_chart": intraday_chart,
                "sentiment": sent.to_dict() if sent else None,
                "macro": macro.to_dict(),
                "numeric_decision": (num_dec.to_dict() if num_dec else None),
                "exit_triggers": {
                    "technical_flipped": flipped,
                    "bad_news": bad_news,
                    "momentum_stalled": stalled,
                    "intraday_momentum_lost": bool(momentum_exit.get("triggered")),
                    "intraday_momentum_reasons": momentum_exit.get("reasons", []),
                    "stall_threshold": stall_thr,
                },
                "risk_constraints": {
                    "max_position_pct": float(self.risk.max_position_pct),
                    "cash_reserve_pct": float(self.risk.cash_reserve_pct),
                },
                "context_note": (
                    "Final arbiter for an open position. Return "
                    "{action: exit|reduce|hold, confidence: 0..1, reasoning: str, "
                    "size_fraction?: 0..1}. If you have ANY doubt, return hold."
                ),
            }
            verdict = run_exit_arbiter(self.cfg, ctx)
            if not verdict:
                log.critical(
                    "[%s] exit arbiter failed/unavailable — holding position (fail-safe)",
                    p.symbol,
                )
                continue

            action = str(verdict.get("action", "")).strip().lower()
            conf = float(verdict.get("confidence", 0.0) or 0.0)
            reasoning = str(verdict.get("reasoning", ""))[:200]
            model_used = verdict.get("_model", "?")
            log_decision({
                "event": "exit_arbiter",
                "symbol": p.symbol,
                "model": model_used,
                "action": action,
                "confidence": conf,
                "reasoning": reasoning,
                "triggers": ctx["exit_triggers"],
            })
            log.info("[%s] exit-arbiter (model=%s) -> %s conf=%.2f: %s",
                     p.symbol, model_used, action, conf, reasoning)

            if action == "exit" and conf >= min_exit_conf:
                # Phase 4a: 30-min hold confirmation buffer. Today's review
                # showed PWR exited on a momentum-fade signal that recovered
                # +$94 within the next 30 min. Require a second consecutive
                # exit signal at least N minutes apart, OR a stop-loss
                # breach / earnings-window override.
                buffer_action = self._exit_confirmation_buffer_check(
                    symbol=p.symbol,
                    macro=macro,
                    triggers=ctx.get("exit_triggers") or {},
                    plpc=plpc,
                )
                if buffer_action == "skip":
                    log.info(
                        "[%s] exit-arbiter EXIT held by 30-min confirmation buffer "
                        "(first signal recorded; need 2nd confirmation)",
                        p.symbol,
                    )
                    continue
                closes.append((
                    p.symbol,
                    f"AI exit-arbiter (conf={conf:.2f}, model={model_used}): {reasoning}",
                ))
                self._exit_confirmation_buffer_clear(p.symbol)
                self._record_exit_arbiter_action(p.symbol, "exit", conf, reasoning)
            elif action == "reduce" and conf >= min_exit_conf:
                # Phase 4b: act on reduce immediately — 50% partial sell +
                # tighten stop. Previously this deferred to the rebalance
                # arbiter which then ran a full EXIT, producing all-or-nothing
                # behavior when a true reduce was the request.
                self._handle_exit_arbiter_reduce(p, plpc, conf, reasoning)
                self._exit_confirmation_buffer_clear(p.symbol)
                self._record_exit_arbiter_action(p.symbol, "reduce", conf, reasoning)
            elif action == "hold":
                # Phase 4 (2026-05-07): record HOLD verdicts too. The selector
                # uses these as continuation evidence when weighing rotation
                # decisions. Recording is symmetric — HOLD raises the rotation
                # bar but EXIT lowers it (no incumbent bias).
                self._record_exit_arbiter_action(p.symbol, "hold", conf, reasoning)
            # else: low-confidence / unknown → do nothing
        return closes

    def _exit_confirmation_buffer_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "data" / "state" / "exit_signal_buffer.json"

    def _load_exit_confirmation_buffer(self) -> dict[str, Any]:
        path = self._exit_confirmation_buffer_path()
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except Exception as e:
            log.warning("exit-buffer load failed: %s", e)
            return {}

    def _save_exit_confirmation_buffer(self, state: dict[str, Any]) -> None:
        path = self._exit_confirmation_buffer_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("exit-buffer save failed: %s", e)

    def _exit_confirmation_buffer_clear(self, symbol: str) -> None:
        sym = str(symbol or "").strip().upper()
        if not sym:
            return
        state = self._load_exit_confirmation_buffer()
        if sym in state:
            state.pop(sym, None)
            self._save_exit_confirmation_buffer(state)

    def _exit_arbiter_actions_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "data" / "state" / "recent_exit_actions.json"

    def _load_recent_exit_actions(self) -> dict[str, Any]:
        path = self._exit_arbiter_actions_path()
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except Exception as e:
            log.warning("recent-exit-actions load failed: %s", e)
            return {}

    def _save_recent_exit_actions(self, state: dict[str, Any]) -> None:
        path = self._exit_arbiter_actions_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("recent-exit-actions save failed: %s", e)

    def _record_exit_arbiter_action(
        self, symbol: str, action: str, confidence: float, reasoning: str,
    ) -> None:
        sym = str(symbol or "").strip().upper()
        if not sym:
            return
        state = self._load_recent_exit_actions()
        state[sym] = {
            "action": str(action or "").strip().lower(),
            "ts": datetime.now(timezone.utc).isoformat(),
            "confidence": round(float(confidence), 3),
            "reason": str(reasoning or "")[:200],
        }
        self._save_recent_exit_actions(state)

    # ---------- Phase A/D/E helpers (2026-05-07) ----------

    def _compute_tape_state_for_selector(self) -> dict[str, Any]:
        """Compute the proportional intraday SPY tape filter signal.

        Returns the ``TapeSignal`` as a dict suitable for inclusion in
        ``system_state.tape_state``. Always returns a usable dict; on data
        unavailability the floor is the configured base and severity is
        ``favorable`` (i.e. no penalty).
        """
        try:
            tape_cfg = self.cfg.get("macro", "intraday_tape_filter", default={}) or {}
        except Exception:
            tape_cfg = {}
        if not bool(tape_cfg.get("enabled", True)):
            base_floor = float(tape_cfg.get("base_min_opportunity_score", 65) or 65)
            return {
                "enabled": False,
                "min_opportunity_score_floor": base_floor,
                "severity_label": "favorable",
                "tape_badness": 0.0,
                "spy_intraday_change_pct": 0.0,
                "spy_vs_vwap_pct": 0.0,
                "has_data": False,
                "notes": ["filter_disabled"],
            }
        try:
            spy_intraday = self._fetch_intraday(["SPY"], minutes=5)
        except Exception as e:
            log.info("[tape] SPY intraday fetch failed: %s", e)
            spy_intraday = None
        spy_slice = self._slice_symbol(spy_intraday, "SPY") if spy_intraday is not None else None
        signal = compute_tape_signal(spy_slice, tape_cfg)
        out = signal.to_dict()
        out["enabled"] = True
        log.info(
            "[tape] severity=%s badness=%.2f spy_intra=%+.2f%% vs_vwap=%+.3f%% "
            "buy_floor=%.0f",
            signal.severity_label,
            signal.tape_badness,
            signal.spy_intraday_change_pct * 100.0,
            signal.spy_vs_vwap_pct * 100.0,
            signal.min_opportunity_score_floor,
        )
        return out

    def _minutes_to_close_with_freeze_flag(self) -> tuple[int | None, bool]:
        """Return (minutes_to_close, no_new_entries) using the broker clock.

        ``no_new_entries`` is True when ``minutes_to_close`` is below the
        configured threshold ``selector.no_new_entries_minutes_before_close``.
        Returns (None, False) when the clock is unavailable.
        """
        threshold = int(
            self.cfg.get(
                "selector", "no_new_entries_minutes_before_close", default=30
            ) or 30
        )
        try:
            clock = self.client.get_clock()
        except Exception as e:
            log.info("[late-day-freeze] clock unavailable: %s", e)
            return None, False
        if clock is None:
            return None, False
        try:
            is_open = bool(getattr(clock, "is_open", False))
            next_close = getattr(clock, "next_close", None)
            now_attr = getattr(clock, "timestamp", None) or datetime.now(timezone.utc)
            if not is_open or next_close is None:
                return None, False
            now_dt = pd.Timestamp(now_attr).tz_convert("UTC") if pd.Timestamp(now_attr).tzinfo else pd.Timestamp(now_attr).tz_localize("UTC")
            close_dt = pd.Timestamp(next_close).tz_convert("UTC") if pd.Timestamp(next_close).tzinfo else pd.Timestamp(next_close).tz_localize("UTC")
            mins = int(max(0, (close_dt - now_dt).total_seconds() // 60))
        except Exception as e:
            log.info("[late-day-freeze] clock parse failed: %s", e)
            return None, False
        no_new = mins <= threshold
        if no_new:
            log.info("[late-day-freeze] active: %d min to close (threshold=%d)", mins, threshold)
        return mins, no_new

    # Phase D: selector-source rotation cooldown — separate state file from
    # exit-arbiter so the two cooldowns can be tuned and read independently.
    def _selector_rotations_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "data" / "state" / "recent_selector_rotations.json"

    def _load_recent_selector_rotations(self) -> dict[str, Any]:
        path = self._selector_rotations_path()
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except Exception as e:
            log.warning("recent-selector-rotations load failed: %s", e)
            return {}

    def _save_recent_selector_rotations(self, state: dict[str, Any]) -> None:
        path = self._selector_rotations_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("recent-selector-rotations save failed: %s", e)

    def record_selector_rotation_exit(
        self, symbol: str, opportunity_score: float, reason: str = "",
    ) -> None:
        """Record a selector-driven EXIT so future selector scans can't
        immediately re-buy without clearing the rebuy bar."""
        sym = str(symbol or "").strip().upper()
        if not sym:
            return
        state = self._load_recent_selector_rotations()
        state[sym] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "opportunity_score_at_exit": round(float(opportunity_score or 0), 1),
            "reason": str(reason or "")[:200],
        }
        self._save_recent_selector_rotations(state)

    def _recent_selector_rotations_for_selector(self) -> dict[str, Any]:
        """Return selector rotations still inside the cooldown window."""
        cooldown_min = float(
            self.cfg.get("selector", "selector_rotation_cooldown_minutes", default=90) or 90
        )
        if cooldown_min <= 0:
            return {}
        state = self._load_recent_selector_rotations()
        if not state:
            return {}
        now = datetime.now(timezone.utc)
        out: dict[str, Any] = {}
        changed = False
        for sym, entry in list(state.items()):
            ts = self._parse_lifecycle_ts((entry or {}).get("ts"))
            if ts is None:
                state.pop(sym, None)
                changed = True
                continue
            age_min = (now - ts).total_seconds() / 60.0
            if age_min > cooldown_min:
                state.pop(sym, None)
                changed = True
                continue
            out[sym] = {
                "minutes_ago": round(age_min, 1),
                "minutes_remaining": round(cooldown_min - age_min, 1),
                "opportunity_score_at_exit": entry.get("opportunity_score_at_exit"),
                "reason": entry.get("reason"),
            }
        if changed:
            self._save_recent_selector_rotations(state)
        return out

    def _recent_exit_actions_for_selector(self) -> dict[str, Any]:
        """Return exit-arbiter actions still inside the cooldown window.

        Surfaced to the portfolio selector as `system_state.recent_exit_actions`
        so the selector cannot quietly reverse a recent EXIT/REDUCE without
        elevated confidence. Stale entries past the cooldown are pruned.
        """
        cooldown_min = float(
            self.cfg.get("exit_arbiter", "rebuy_cooldown_minutes", default=60) or 60
        )
        if cooldown_min <= 0:
            return {}
        state = self._load_recent_exit_actions()
        if not state:
            return {}
        now = datetime.now(timezone.utc)
        out: dict[str, Any] = {}
        changed = False
        for sym, entry in list(state.items()):
            ts = self._parse_lifecycle_ts((entry or {}).get("ts"))
            if ts is None:
                state.pop(sym, None)
                changed = True
                continue
            age_min = (now - ts).total_seconds() / 60.0
            if age_min > cooldown_min:
                state.pop(sym, None)
                changed = True
                continue
            out[sym] = {
                "action": entry.get("action"),
                "confidence": entry.get("confidence"),
                "minutes_ago": round(age_min, 1),
                "minutes_remaining": round(cooldown_min - age_min, 1),
                "reason": entry.get("reason"),
            }
        if changed:
            self._save_recent_exit_actions(state)
        return out

    def _exit_confirmation_buffer_check(
        self,
        symbol: str,
        macro: MacroSignal | None,
        triggers: dict[str, Any] | None,
        plpc: float,
    ) -> str:
        """Phase 4a: enforce a confirmation window before AI-opinion exits.

        Returns "proceed" to allow the exit, or "skip" to hold this scan
        and require a second consecutive exit signal ≥ N minutes later.

        Skips the buffer (returns "proceed") when:
          - macro halt is active (urgent risk-off)
          - position is in earnings window (handled by earnings-gate)
          - signal is a stop-loss breach (deterministic, not opinion)
          - position is already losing materially (plpc <= -loss_floor)
        """
        if not bool(self.cfg.get("exit_arbiter", "confirmation_buffer_enabled", default=True)):
            return "proceed"
        # Skip buffer in urgent contexts.
        if macro is not None and (
            getattr(macro, "score", 0.0) <= float(
                self.cfg.get("macro", "bearish_halt_score", default=-0.55) or -0.55
            )
        ):
            return "proceed"
        triggers = dict(triggers or {})
        if triggers.get("stop_loss_breach"):
            return "proceed"
        if triggers.get("earnings_window") or triggers.get("earnings_close"):
            return "proceed"
        loss_floor = float(self.cfg.get(
            "exit_arbiter", "confirmation_buffer_loss_floor_pct", default=-0.015,
        ) or -0.015)
        if plpc <= loss_floor:
            # Already losing materially — let the AI exit immediately.
            return "proceed"

        confirm_minutes = float(self.cfg.get(
            "exit_arbiter", "confirmation_minutes", default=30,
        ) or 30)

        sym = str(symbol or "").strip().upper()
        state = self._load_exit_confirmation_buffer()
        entry = state.get(sym) or {}
        now = datetime.now(timezone.utc)
        first_ts_raw = entry.get("first_signal_ts")
        first_ts = self._parse_lifecycle_ts(first_ts_raw)
        if first_ts is None:
            # First exit signal — record and ask for confirmation.
            state[sym] = {
                "first_signal_ts": now.isoformat(),
                "plpc_at_signal": round(float(plpc), 4),
            }
            self._save_exit_confirmation_buffer(state)
            return "skip"
        age_min = (now - first_ts).total_seconds() / 60.0
        if age_min < confirm_minutes:
            # Still inside the confirmation window. Hold.
            return "skip"
        # Second confirmation arrived after the buffer expired — proceed.
        return "proceed"

    def _handle_exit_arbiter_reduce(
        self,
        p: Any,
        plpc: float,
        conf: float,
        reasoning: str,
    ) -> None:
        """Phase 4b: act on exit-arbiter `reduce` — 50% partial sell + tighter stop."""
        try:
            qty = abs(float(p.qty))
        except (TypeError, ValueError):
            qty = 0.0
        if qty <= 0:
            log.info("[%s] reduce skipped: zero qty", p.symbol)
            return
        trim_fraction = float(self.cfg.get(
            "exit_arbiter", "reduce_trim_fraction", default=0.5,
        ) or 0.5)
        trim_fraction = max(0.05, min(0.95, trim_fraction))
        sell_qty = qty * trim_fraction
        # Whole-share quantization for protected stocks; allow fractional only
        # for sub-$10 names (consistent with the rest of the codebase).
        try:
            price_for_round = float(getattr(p, "current_price", 0) or 0)
        except (TypeError, ValueError):
            price_for_round = 0.0
        if price_for_round >= 10.0:
            sell_qty = float(int(sell_qty))
        if sell_qty <= 0:
            log.info(
                "[%s] reduce computed zero sell qty (qty=%s, fraction=%.2f) — skip",
                p.symbol, qty, trim_fraction,
            )
            return
        try:
            exec_result = self.executor.execute_ai_qty_delta(
                symbol=p.symbol,
                delta_qty=-sell_qty,
                reason=(
                    f"AI exit-arbiter REDUCE (conf={conf:.2f}): {reasoning}"
                ),
            )
        except Exception as e:
            log.warning("[%s] reduce execution raised: %s", p.symbol, e)
            return
        if not getattr(exec_result, "ok", False):
            log.warning(
                "[%s] reduce sell did not fill: status=%s",
                p.symbol, getattr(exec_result, "final_status", "?"),
            )
            return
        log.info(
            "[%s] reduce: trimmed %s shares (%.0f%% of position) — exit-arbiter confirmed",
            p.symbol, sell_qty, trim_fraction * 100,
        )

    def _earnings_gate_decision(
        self, p, einfo: EarningsInfo, tech, sent, numeric, macro: MacroSignal | None,
        plpc: float,
    ) -> tuple[str, str]:
        """Return (verdict, human-readable-reason) for a position entering its
        earnings trim window. verdict ∈ {"close", "trim_50", "hold", "skip_no_ai"}.

        AI IS THE ONLY AUTHORITY. No numeric fallback is allowed to close
        a position — if Opus 4.7 earnings-gate is unavailable we return
        "skip_no_ai" and the position is held. The bot never trades around
        earnings on deterministic logic alone.
        """
        if not self.earnings_use_ai_gate or not self.ai.available():
            log.critical(
                "[%s] earnings-gate (Opus 4.7) unavailable — HOLDING "
                "(fail-safe: no earnings close without AI approval)",
                p.symbol,
            )
            return (
                "skip_no_ai",
                f"earnings in {einfo.days_until}d — AI unavailable, held (fail-safe)",
            )

        ctx = {
            "symbol": p.symbol,
            "side": "long",
            "market_value": abs(float(p.market_value)),
            "unrealized_plpc": round(plpc, 4),
            "current_weight_pct": round(abs(float(p.market_value)) / float(self.client.get_account().equity), 4),
            "earnings": {
                "next_date": einfo.next_date,
                "days_until_earnings": einfo.days_until,
                "time_of_day": getattr(einfo, "time_of_day", "unknown"),
            },
            "tech_score": round(float(tech.score), 3) if tech else None,
            "rsi": round(float(tech.rsi), 1) if tech and tech.rsi is not None else None,
            "price": float(tech.price) if tech and tech.price is not None else None,
            "atr": float(tech.atr) if tech and tech.atr is not None else None,
            "sent_score": round(float(sent.score), 3) if sent else None,
            "headline_count": getattr(sent, "article_count", None) if sent else None,
            "numeric_decision": (numeric.to_dict() if numeric else None),
            "macro": macro.to_dict() if macro is not None else None,
        }
        try:
            result = run_earnings_gate(self.cfg, ctx)
        except Exception as e:
            log.warning("[%s] earnings gate call error: %s", p.symbol, e)
            result = None
        if not result:
            log.critical(
                "[%s] earnings-gate call failed — HOLDING (fail-safe: no "
                "earnings close without AI approval)", p.symbol,
            )
            return (
                "skip_no_ai",
                f"earnings in {einfo.days_until}d — AI call failed, held (fail-safe)",
            )
        verdict = str(result.get("verdict", "")).strip().lower()
        if verdict not in ("close", "trim_50", "hold"):
            log.critical(
                "[%s] earnings-gate returned invalid verdict=%r — HOLDING (fail-safe)",
                p.symbol, verdict,
            )
            return (
                "skip_no_ai",
                f"earnings in {einfo.days_until}d — invalid AI verdict, held (fail-safe)",
            )
        rationale = str(result.get("rationale", ""))[:200]
        conf = float(result.get("confidence", 0.0) or 0.0)
        model_used = result.get("_model", "?")

        # Confidence post-filter: a 'hold' verdict near earnings is only
        # accepted when conviction is exceptional. Otherwise downgrade to
        # trim_50 — keep some exposure but halve gap risk.
        original_verdict = verdict
        downgraded = False
        days_until = int(einfo.days_until or 0)
        if verdict == "hold":
            if days_until <= 1 and conf < self.earnings_day_0_1_hold_min_conf:
                verdict = "trim_50"
                downgraded = True
                rationale = (
                    f"AI hold conf={conf:.2f} < day_0_1_min={self.earnings_day_0_1_hold_min_conf:.2f}"
                    f" — downgraded to trim_50. Original: {rationale}"
                )
            elif days_until == 2 and conf < self.earnings_day2_hold_min_conf:
                verdict = "trim_50"
                downgraded = True
                rationale = (
                    f"AI hold conf={conf:.2f} < day2_min={self.earnings_day2_hold_min_conf:.2f}"
                    f" — downgraded to trim_50. Original: {rationale}"
                )

        ai_reason = (
            f"earnings in {einfo.days_until}d ({einfo.next_date}) — AI {verdict} "
            f"(conf={conf:.2f}, model={model_used}): {rationale}"
        )
        log_decision({
            "event": "earnings_gate", "symbol": p.symbol, "model": model_used,
            "verdict": verdict, "original_verdict": original_verdict,
            "downgraded": downgraded,
            "confidence": conf, "rationale": rationale,
        })
        log.info("[%s] earnings gate (model=%s) -> %s%s (conf=%.2f): %s",
                 p.symbol, model_used, verdict,
                 f" (downgraded from {original_verdict})" if downgraded else "",
                 conf, rationale)
        return (verdict, ai_reason)

    # ---------- rebalance ----------
    def _snapshot_portfolio(self, equity_hint: float | None = None) -> dict[str, Any]:
        """Lightweight before/after snapshot for arbiter logging."""
        try:
            acct = self.client.get_account()
            cash = float(acct.cash)
            equity = float(acct.equity)
        except Exception:
            cash = 0.0
            equity = float(equity_hint or 0.0)
        try:
            positions = self.client.get_positions()
        except Exception:
            positions = []
        spy_value = 0.0
        pos_dump: list[dict[str, Any]] = []
        for p in positions:
            mv = abs(float(getattr(p, "market_value", 0) or 0))
            entry = {
                "symbol": p.symbol,
                "side": "long",
                "qty": float(getattr(p, "qty", 0) or 0),
                "avg_entry_price": float(getattr(p, "avg_entry_price", 0) or 0),
                "current_price": float(getattr(p, "current_price", 0) or 0),
                "market_value_usd": round(mv, 2),
                "weight_pct": round(mv / equity, 4) if equity else 0.0,
                "unrealized_pl_usd": round(float(getattr(p, "unrealized_pl", 0) or 0), 2),
                "unrealized_plpc": round(float(getattr(p, "unrealized_plpc", 0) or 0), 4),
            }
            if self._is_cash_proxy(p.symbol):
                spy_value = mv
                entry["role"] = "cash_proxy"
            pos_dump.append(entry)
        return {
            "ts": pd.Timestamp.utcnow().isoformat(),
            "equity": round(equity, 2),
            "cash": round(cash, 2),
            "spy_value": round(spy_value, 2),
            "cash_pct": round(cash / equity, 4) if equity else 0.0,
            "spy_pct": round(spy_value / equity, 4) if equity else 0.0,
            "positions": pos_dump,
        }

    @staticmethod
    def _intraday_change_pct(intraday_df, symbol: str) -> float | None:
        """Return today's session % change for a symbol from intraday bars.
        Uses (last_close - first_open) / first_open. None if data missing."""
        if intraday_df is None:
            return None
        try:
            if "symbol" in intraday_df.index.names:
                slc = intraday_df.xs(symbol, level="symbol")
            else:
                slc = intraday_df
            if slc is None or slc.empty:
                return None
            # Restrict to today's UTC date so prior session bars don't pollute.
            try:
                last_ts = slc.index[-1]
                today = last_ts.date() if hasattr(last_ts, "date") else None
                if today is not None:
                    same_day = slc[slc.index.map(lambda t: t.date() == today)]
                    if not same_day.empty:
                        slc = same_day
            except Exception:
                pass
            opn = float(slc["open"].iloc[0])
            lst = float(slc["close"].iloc[-1])
            if opn <= 0:
                return None
            return (lst - opn) / opn
        except Exception:
            return None

    @staticmethod
    def _five_day_change_pct(daily_df, symbol: str) -> float | None:
        """Last close vs close-5-bars-ago, from daily bars."""
        if daily_df is None:
            return None
        try:
            if "symbol" in daily_df.index.names:
                slc = daily_df.xs(symbol, level="symbol")
            else:
                slc = daily_df
            closes = slc["close"]
            if len(closes) < 6:
                return None
            return float(closes.iloc[-1] / closes.iloc[-6] - 1.0)
        except Exception:
            return None

    @staticmethod
    def _intraday_chart_for(
        intraday_df,
        symbol: str,
        daily_df=None,
    ) -> dict[str, Any] | None:
        """Build the full intraday chart structure expected by the portfolio
        arbiter. Returns a dict containing:

          current_price, open, day_high, day_low, vwap,
          distance_from_high_pct, distance_from_low_pct, intraday_change_pct,
          gap_from_prior_close_pct, price_vs_vwap_pct, 5-minute EMA state,
          recent_slope_pct, volume_trend (rising|fading|flat),
          classification (near_high|near_low|breaking_out|fading|consolidating|recovering)

        Returns None when bars are unavailable.
        """
        if intraday_df is None:
            return None
        try:
            if "symbol" in intraday_df.index.names:
                slc = intraday_df.xs(symbol, level="symbol")
            else:
                slc = intraday_df
            if slc is None or slc.empty:
                return None
            # Restrict to today's session bars
            try:
                last_ts = slc.index[-1]
                today = last_ts.date() if hasattr(last_ts, "date") else None
                if today is not None:
                    same_day = slc[slc.index.map(lambda t: t.date() == today)]
                    if not same_day.empty:
                        slc = same_day
            except Exception:
                pass
            if slc.empty:
                return None
            slc = slc.sort_index()

            opens = slc["open"]
            highs = slc["high"] if "high" in slc.columns else slc["close"]
            lows = slc["low"] if "low" in slc.columns else slc["close"]
            closes = slc["close"]
            volumes = slc["volume"] if "volume" in slc.columns else None

            opn = float(opens.iloc[0])
            cur = float(closes.iloc[-1])
            day_high = float(highs.max())
            day_low = float(lows.min())
            session_volume = float(volumes.sum()) if volumes is not None else 0.0

            # VWAP across the session bars (typical price * volume / volume)
            vwap_val: float | None = None
            try:
                if volumes is not None and float(volumes.sum()) > 0:
                    typical = (highs + lows + closes) / 3.0
                    vwap_val = float((typical * volumes).sum() / volumes.sum())
            except Exception:
                vwap_val = None

            dist_from_high = (cur - day_high) / day_high if day_high > 0 else None
            dist_from_low = (cur - day_low) / day_low if day_low > 0 else None
            intraday_chg = (cur - opn) / opn if opn > 0 else None
            price_vs_vwap = (cur - vwap_val) / vwap_val if vwap_val and vwap_val > 0 else None

            # Daily context: previous close for gap-vs-continuation and rough
            # relative volume. If daily bars include today's row, use the prior
            # row; otherwise use the latest available close.
            prior_close: float | None = None
            twenty_day_volume_ratio: float | None = None
            try:
                if daily_df is not None:
                    if "symbol" in daily_df.index.names:
                        daily_slc = daily_df.xs(symbol, level="symbol")
                    else:
                        daily_slc = daily_df
                    daily_slc = daily_slc.sort_index()
                    if not daily_slc.empty:
                        last_daily_ts = daily_slc.index[-1]
                        last_daily_date = (
                            last_daily_ts.date()
                            if hasattr(last_daily_ts, "date") else None
                        )
                        intraday_date = (
                            slc.index[-1].date()
                            if hasattr(slc.index[-1], "date") else None
                        )
                        prior_idx = -2 if (
                            intraday_date is not None
                            and last_daily_date == intraday_date
                            and len(daily_slc) >= 2
                        ) else -1
                        prior_close = float(daily_slc["close"].iloc[prior_idx])
                        if "volume" in daily_slc.columns and len(daily_slc) >= 5:
                            hist_vol = daily_slc["volume"].iloc[-21:-1]
                            if hist_vol.empty:
                                hist_vol = daily_slc["volume"].iloc[:-1]
                            avg_vol = float(hist_vol.tail(20).mean()) if not hist_vol.empty else 0.0
                            if avg_vol > 0 and session_volume > 0:
                                twenty_day_volume_ratio = session_volume / avg_vol
            except Exception:
                prior_close = None
                twenty_day_volume_ratio = None
            gap_from_prior = (
                (opn - prior_close) / prior_close
                if prior_close and prior_close > 0 else None
            )

            # Recent trend: slope of the last ~6 bars' close
            def _slope(series) -> float:
                n = len(series)
                if n < 2:
                    return 0.0
                first = float(series.iloc[0])
                last = float(series.iloc[-1])
                if first == 0:
                    return 0.0
                return (last - first) / abs(first)

            recent_n = min(6, len(closes))
            recent = closes.iloc[-recent_n:]
            slope = _slope(recent)
            if slope > 0.0015:
                recent_trend = "rising"
            elif slope < -0.0015:
                recent_trend = "falling"
            else:
                recent_trend = "flat"

            # Volume trend: recent 6-bar mean vs prior 6-bar mean
            volume_trend = "flat"
            volume_ratio_recent_to_prior: float | None = None
            try:
                if volumes is not None and len(volumes) >= 4:
                    half = max(3, min(6, len(volumes) // 2))
                    recent_v = float(volumes.iloc[-half:].mean())
                    prior_v = float(volumes.iloc[-2 * half : -half].mean()) if len(volumes) >= 2 * half else float(volumes.iloc[:-half].mean() if len(volumes) > half else recent_v)
                    if prior_v > 0:
                        ratio = recent_v / prior_v
                        volume_ratio_recent_to_prior = ratio
                        if ratio >= 1.10:
                            volume_trend = "rising"
                        elif ratio <= 0.90:
                            volume_trend = "fading"
            except Exception:
                volume_trend = "flat"

            # 5-minute EMA state from the same intraday bars.
            ema5 = None
            ema20 = None
            ema_state = "unknown"
            price_vs_ema20 = None
            ema20_slope = None
            try:
                ema5_series = closes.ewm(span=5, adjust=False).mean()
                ema20_series = closes.ewm(span=20, adjust=False).mean()
                ema5 = float(ema5_series.iloc[-1])
                ema20 = float(ema20_series.iloc[-1])
                price_vs_ema20 = (cur - ema20) / ema20 if ema20 > 0 else None
                if len(ema20_series) >= 6 and float(ema20_series.iloc[-6]) != 0:
                    ema20_slope = (ema20 / float(ema20_series.iloc[-6])) - 1.0
                if cur >= ema20 and ema5 >= ema20:
                    ema_state = "bullish"
                elif cur < ema20 and ema5 < ema20:
                    ema_state = "bearish"
                elif cur >= ema20:
                    ema_state = "price_above_ema20"
                else:
                    ema_state = "price_below_ema20"
            except Exception:
                ema_state = "unknown"

            # Classification
            near_high = dist_from_high is not None and dist_from_high >= -0.005
            near_low = dist_from_low is not None and dist_from_low <= 0.005
            if near_high and recent_trend == "rising" and volume_trend == "rising":
                classification = "breaking_out"
            elif near_high:
                classification = "near_high"
            elif near_low and recent_trend == "rising":
                classification = "recovering"
            elif near_low:
                classification = "near_low"
            elif recent_trend == "falling":
                classification = "fading"
            else:
                classification = "consolidating"

            gap_only_risk = False
            if gap_from_prior is not None and intraday_chg is not None:
                gap_only_risk = (
                    gap_from_prior >= 0.01
                    and abs(intraday_chg) <= 0.003
                    and recent_trend in ("flat", "falling")
                    and volume_trend != "rising"
                )

            return {
                "current_price": round(cur, 4),
                "open": round(opn, 4),
                "day_high": round(day_high, 4),
                "day_low": round(day_low, 4),
                "vwap": round(vwap_val, 4) if vwap_val is not None else None,
                "prior_close": round(prior_close, 4) if prior_close is not None else None,
                "gap_from_prior_close_pct": round(gap_from_prior, 4) if gap_from_prior is not None else None,
                "price_vs_vwap_pct": round(price_vs_vwap, 4) if price_vs_vwap is not None else None,
                "distance_from_high_pct": round(dist_from_high, 4) if dist_from_high is not None else None,
                "distance_from_low_pct": round(dist_from_low, 4) if dist_from_low is not None else None,
                "intraday_change_pct": round(intraday_chg, 4) if intraday_chg is not None else None,
                "recent_trend": recent_trend,
                "recent_slope_pct": round(slope, 4),
                "volume_trend": volume_trend,
                "volume_ratio_recent_to_prior": (
                    round(volume_ratio_recent_to_prior, 3)
                    if volume_ratio_recent_to_prior is not None else None
                ),
                "twenty_day_volume_ratio": (
                    round(twenty_day_volume_ratio, 3)
                    if twenty_day_volume_ratio is not None else None
                ),
                "ema5": round(ema5, 4) if ema5 is not None else None,
                "ema20": round(ema20, 4) if ema20 is not None else None,
                "ema_state": ema_state,
                "price_vs_ema20_pct": round(price_vs_ema20, 4) if price_vs_ema20 is not None else None,
                "ema20_slope_pct": round(ema20_slope, 4) if ema20_slope is not None else None,
                "classification": classification,
                "gap_only_risk": bool(gap_only_risk),
                "session_volume": int(session_volume),
                "session_bar_count": int(len(slc)),
            }
        except Exception:
            return None

    def _momentum_profile(self, chart: dict[str, Any] | None) -> dict[str, Any]:
        """Score live continuation vs gap-only/stale tape risk.

        This is not a standalone trade decision. It is structured context for
        the selector plus an execution gate for brand-new entries.
        """
        if not chart:
            return {
                "score": 0,
                "grade": "missing_intraday",
                "passes_new_entry_gate": False,
                "gap_only_risk": False,
                "reasons": ["missing_intraday_chart"],
            }

        score = 50.0
        reasons: list[str] = []

        price_vs_vwap = chart.get("price_vs_vwap_pct")
        if price_vs_vwap is not None:
            if float(price_vs_vwap) >= 0.001:
                score += 12
                reasons.append("above_vwap")
            elif float(price_vs_vwap) <= -0.001:
                score -= 18
                reasons.append("below_vwap")

        ema_state = str(chart.get("ema_state") or "")
        if ema_state == "bullish":
            score += 14
            reasons.append("ema5_above_ema20")
        elif ema_state in ("bearish", "price_below_ema20"):
            score -= 16
            reasons.append("below_5min_ema20")

        recent_trend = str(chart.get("recent_trend") or "")
        if recent_trend == "rising":
            score += 15
            reasons.append("recent_trend_rising")
        elif recent_trend == "falling":
            score -= 20
            reasons.append("recent_trend_falling")
        else:
            score -= 5
            reasons.append("recent_trend_flat")

        volume_trend = str(chart.get("volume_trend") or "")
        if volume_trend == "rising":
            score += 12
            reasons.append("volume_rising")
        elif volume_trend == "fading":
            score -= 12
            reasons.append("volume_fading")

        classification = str(chart.get("classification") or "")
        if classification == "breaking_out":
            score += 12
            reasons.append("breaking_out")
        elif classification == "fading":
            score -= 15
            reasons.append("fading_from_intraday_high")

        dist_high = chart.get("distance_from_high_pct")
        if dist_high is not None:
            dh = float(dist_high)
            if dh >= -0.006 and recent_trend == "rising":
                score += 6
                reasons.append("pressing_day_high")
            elif dh <= -0.02:
                score -= 8
                reasons.append("well_off_day_high")

        if chart.get("gap_only_risk"):
            score -= 28
            reasons.append("gap_only_no_continuation")

        intraday_change = chart.get("intraday_change_pct")
        if intraday_change is not None and float(intraday_change) > 0.05:
            if recent_trend != "rising" or volume_trend != "rising":
                score -= 15
                reasons.append("large_move_without_fresh_push")

        score = max(0.0, min(100.0, score))
        min_score = float(self.cfg.get(
            "selector", "continuation_gate", "min_score", default=55,
        ))
        allow_missing = bool(self.cfg.get(
            "selector", "continuation_gate", "allow_missing_intraday", default=False,
        ))
        passes = bool(
            score >= min_score
            and not chart.get("gap_only_risk")
            and (chart is not None or allow_missing)
        )
        if score >= 75:
            grade = "strong_continuation"
        elif score >= min_score:
            grade = "acceptable_continuation"
        elif chart.get("gap_only_risk"):
            grade = "gap_only"
        elif recent_trend == "falling" or classification == "fading":
            grade = "fading"
        else:
            grade = "weak_or_flat"

        return {
            "score": round(score, 1),
            "grade": grade,
            "passes_new_entry_gate": passes,
            "gap_only_risk": bool(chart.get("gap_only_risk")),
            "min_score": min_score,
            "reasons": reasons,
        }

    def _new_entry_momentum_gate(
        self,
        sym: str,
        pool_meta: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Return a block dict when a fresh selector entry lacks live momentum."""
        if not bool(self.cfg.get("selector", "continuation_gate", "enabled", default=True)):
            return None
        profile = (pool_meta.get(sym) or {}).get("momentum_profile") or {}
        if profile.get("passes_new_entry_gate"):
            return None
        return {
            "symbol": sym,
            "reason": "failed_continuation_gate",
            "momentum_profile": profile,
        }

    def _momentum_exit_signal(self, chart: dict[str, Any] | None) -> dict[str, Any]:
        """Describe whether a held position's intraday momentum has ended."""
        if not chart:
            return {"triggered": False, "reasons": ["missing_intraday_chart"]}
        reasons: list[str] = []
        price_vs_vwap = chart.get("price_vs_vwap_pct")
        price_vs_ema20 = chart.get("price_vs_ema20_pct")
        recent_trend = str(chart.get("recent_trend") or "")
        volume_trend = str(chart.get("volume_trend") or "")
        classification = str(chart.get("classification") or "")
        dist_high = chart.get("distance_from_high_pct")

        if price_vs_vwap is not None and float(price_vs_vwap) < -0.001:
            reasons.append("lost_vwap")
        if price_vs_ema20 is not None and float(price_vs_ema20) < -0.001:
            reasons.append("lost_5min_ema20")
        if recent_trend == "falling" and volume_trend in ("fading", "flat"):
            reasons.append("trend_falling_without_volume_support")
        if classification == "fading":
            reasons.append("classified_fading")
        if dist_high is not None and float(dist_high) <= -0.015 and recent_trend != "rising":
            reasons.append("pulled_back_from_day_high")

        hard_loss = "lost_vwap" in reasons and "lost_5min_ema20" in reasons
        exhaustion = (
            "trend_falling_without_volume_support" in reasons
            or "classified_fading" in reasons
        )
        return {
            "triggered": bool(hard_loss or exhaustion),
            "reasons": reasons,
            "chart": chart,
        }

    def _scan_time_context(self) -> dict[str, Any]:
        mtc = self._minutes_to_close()
        if mtc is None:
            phase = "unknown"
        elif mtc > 240:
            phase = "early"
        elif mtc > 90:
            phase = "midday"
        elif mtc > 20:
            phase = "late_intraday"
        else:
            phase = "preclose"
        return {
            "minutes_to_close": round(mtc, 1) if mtc is not None else None,
            "phase": phase,
            "intraday_new_entries_allowed": True,
            "preclose_overnight_task_handles_overnight_buys": True,
        }

    def _build_arbiter_context(
        self,
        holdings: list,
        tech_map: dict,
        sent_map: dict,
        numeric: dict,
        earnings_map: dict,
        macro: MacroSignal,
        equity: float,
        bearish_halt: bool = False,
        dry_run: bool = False,
        scan_candidates: list[dict[str, Any]] | None = None,
        earnings_close_symbols: set[str] | list[str] | None = None,
    ) -> dict[str, Any]:
        """Shape the FULL portfolio + rules + intraday + SPY context for the
        portfolio-arbiter agent.

        Required inputs the AI receives every call:
          - cash + buying power
          - every position with qty / avg_entry / current_price / weight / pnl
          - SPY in its own block (cash-equivalent parking vehicle)
          - risk profile + trading rules + execution constraints
          - current allocation breakdown (cash%, SPY%, equity%, sector%)
          - macro + intraday tape
          - system state (market halts, dry_run)
        """
        from src.universe import sp500_sectors
        sectors = sp500_sectors()

        # --- Account / cash ---
        try:
            acct = self.client.get_account()
            cash = float(acct.cash)
            buying_power = float(acct.buying_power) if hasattr(acct, "buying_power") else cash
        except Exception:
            cash = 0.0
            buying_power = 0.0

        # --- Intraday bars: SPY + every held symbol (one batch) ---
        held_syms = [p.symbol for p in holdings if "/" not in p.symbol]
        intraday_syms = list({*held_syms, "SPY"})
        intraday_bars = None
        try:
            intraday_bars = self._fetch_intraday(intraday_syms, minutes=5)
        except Exception as e:
            log.info("Arbiter context: intraday fetch failed (%s) — proceeding without it", e)

        # --- Daily bars for prior-close gaps, 5-day perf, and volume context ---
        daily_bars = None
        try:
            daily_bars = self.client.get_stock_bars(intraday_syms, lookback_days=30)
        except Exception:
            pass

        # --- SPY block (cash-like parking vehicle) ---
        spy_position_value = 0.0
        spy_qty = 0.0
        if self.cash_proxy_enabled:
            position_sources = list(holdings or [])
            try:
                snapshot_positions = self.client.get_positions()
            except Exception:
                snapshot_positions = []
            position_sources.extend(snapshot_positions or [])
            for p in position_sources:
                if self._is_cash_proxy(getattr(p, "symbol", "")):
                    spy_position_value = abs(float(getattr(p, "market_value", 0) or 0))
                    try:
                        spy_qty = float(getattr(p, "qty", 0) or 0)
                    except Exception:
                        spy_qty = 0.0
                    break
        spy_chart = self._intraday_chart_for(intraday_bars, "SPY", daily_bars)
        spy_5d_chg = self._five_day_change_pct(daily_bars, "SPY")
        spy_current_price = (spy_chart or {}).get("current_price")
        if spy_current_price is None:
            try:
                spy_quote = self.client.get_stock_quote("SPY")
                spy_current_price = float(getattr(spy_quote, "ask_price", 0)
                                          or getattr(spy_quote, "bid_price", 0)
                                          or 0) or None
            except Exception:
                spy_current_price = None
        spy_block: dict[str, Any] = {
            "symbol": self.cash_proxy_symbol,
            "role": "cash_equivalent_parking_vehicle",
            "treated_as": "liquid_cash_alternative",
            "held": spy_position_value > 0,
            "qty": round(spy_qty, 4),
            "current_value_usd": round(spy_position_value, 2),
            "current_weight_pct": round(spy_position_value / equity, 4) if equity else 0.0,
            "current_price": spy_current_price,
            "intraday_chart": spy_chart,
            "five_day_change_pct": round(spy_5d_chg, 4) if spy_5d_chg is not None else None,
            "macro_trend": round(float(macro.spy_trend), 3),
            "macro_vs_200ema": round(float(macro.spy_vs_200ema), 4),
            "macro_regime": macro.regime,
            "vix_regime": macro.vix_regime,
            "notes": macro.notes or [],
        }

        # --- Per-position blocks (full quantitative detail) ---
        sector_exposure_usd: dict[str, float] = {}
        pos_ctx: list[dict[str, Any]] = []
        for p in holdings:
            if self._is_cash_proxy(p.symbol):
                continue
            sym = p.symbol
            tech = tech_map.get(sym)
            sent = sent_map.get(sym)
            num = numeric.get(sym)
            einfo = earnings_map.get(sym)
            mv = abs(float(p.market_value))
            avg_entry = float(getattr(p, "avg_entry_price", 0) or 0)
            cur_price = float(getattr(p, "current_price", 0) or 0)
            try:
                qty_f = float(p.qty)
            except Exception:
                qty_f = 0.0
            unreal_pl = float(getattr(p, "unrealized_pl", 0) or 0)
            unreal_plpc = float(getattr(p, "unrealized_plpc", 0) or 0)
            sector = sectors.get(sym, "unknown")
            sector_exposure_usd[sector] = sector_exposure_usd.get(sector, 0.0) + mv
            chart = self._intraday_chart_for(intraday_bars, sym, daily_bars)
            momentum_profile = self._momentum_profile(chart)
            pos_ctx.append({
                "symbol": sym,
                "side": "long",
                "qty": qty_f,
                "avg_entry_price": round(avg_entry, 4),
                "current_price": round(cur_price, 4),
                "market_value_usd": round(mv, 2),
                "abs_market_value_usd": round(mv, 2),
                "current_weight_pct": round(mv / equity, 4) if equity else 0.0,
                "unrealized_pl_usd": round(unreal_pl, 2),
                "unrealized_plpc": round(unreal_plpc, 4),
                "sector": sector,
                "tech_score": round(float(tech.score), 3) if tech else None,
                "rsi": round(float(tech.rsi), 1) if tech and tech.rsi is not None else None,
                "atr": round(float(tech.atr), 3) if tech and tech.atr is not None else None,
                "sent_score": round(float(sent.score), 3) if sent else None,
                "numeric_confidence": round(float(num.confidence), 3) if num else None,
                "numeric_combined_score": round(float(num.combined_score), 3) if num else None,
                "numeric_action": num.action if num else None,
                "intraday_chart": chart,
                "momentum_profile": momentum_profile,
                "earnings_days_until": (einfo.days_until if einfo else None),
                "earnings_next_date": (einfo.next_date if einfo else None),
            })

        # --- Allocation breakdown ---
        invested_equity = sum(p["abs_market_value_usd"] for p in pos_ctx)
        sector_breakdown_pct = (
            {k: round(v / equity, 4) for k, v in sector_exposure_usd.items()}
            if equity else {}
        )
        current_alloc = {
            "cash_pct": round(cash / equity, 4) if equity else 0.0,
            "spy_pct": round(spy_position_value / equity, 4) if equity else 0.0,
            "equity_pct": round(invested_equity / equity, 4) if equity else 0.0,
            "sector_breakdown_pct": sector_breakdown_pct,
            "top_positions": sorted(
                [{"symbol": p["symbol"], "weight_pct": p["current_weight_pct"]}
                 for p in pos_ctx],
                key=lambda x: x["weight_pct"], reverse=True,
            )[:5],
        }

        # --- Risk profile ---
        risk_profile = {
            "max_position_pct": float(self.risk.max_position_pct),
            "max_sector_pct": float(self.risk.max_sector_pct),
            "max_positions": int(self.risk.max_positions),
            "max_leverage": float(self.cfg.get("risk", "max_leverage", default=1.0)),
            "cash_reserve_pct": float(self.risk.cash_reserve_pct),
            "cash_reserve_min_pct": float(self.risk.cash_reserve_min_pct),
            "max_risk_per_trade_pct": float(self.cfg.get("risk", "max_risk_per_trade_pct", default=0.005)),
            "high_conviction_threshold": float(self.risk.high_conviction_threshold),
            "stop_loss_atr_mult": float(self.cfg.get("risk", "stop_loss_atr_mult", default=2.0)),
            "take_profit_atr_mult": float(self.cfg.get("risk", "take_profit_atr_mult", default=4.0)),
            "hard_stop_loss_pct": float(self.cfg.get("risk", "hard_stop_loss_pct", default=0.01)),
        }

        # --- Trading rules (text — guides AI judgment) ---
        trading_rules = [
            "You are the FINAL authority on every capital allocation decision.",
            "Only act on high-confidence setups; spreading capital evenly is the wrong default.",
            "Capital must be actively optimized intraday — every scan rebalances.",
            "No trade may execute without your explicit AI decision.",
            "Decisions are intraday-focused with a swing-trade horizon.",
            "Concentrate into highest-conviction names up to max_position_pct.",
            "Free capital from oversized / low-upside positions and redeploy.",
            "Treat SPY as cash-like; choose SPY vs cash based on macro + intraday tape.",
            "Sector caps and per-position caps are HARD constraints.",
        ]

        # --- Execution constraints ---
        execution_constraints = {
            "fractional_shares_supported_for_entry_orders": True,
            "buy_entry_order_class": "simple",
            "attached_stop_loss_on_entry_order": False,
            "protective_stop_order": "submitted_as_separate_simple_sell_stop_after_entry_fill",
            "fractional_stop_orders_require_time_in_force_day": True,
            "non_fractionable_assets": "executor rounds BUY qty down to whole shares; below 1 share is rejected",
            "non_tradable_assets": "executor rejects before order submission",
            "time_in_force": "day",
            "min_trade_usd": float(self.cfg.get("risk", "min_trade_usd", default=500)),
            "min_rebalance_delta_usd": float(self.cfg.get(
                "rebalance", "min_delta_usd", default=500)),
            "min_rebalance_delta_pct": float(self.cfg.get(
                "rebalance", "min_delta_pct", default=0.15)),
            "spy_treated_as_liquid": bool(self.cash_proxy_enabled),
            "spy_can_be_freely_converted_to_cash": bool(self.cash_proxy_enabled),
            "cash_proxy_min_rebalance_usd": float(self.cash_proxy_min),
        }

        # --- System state ---
        ec_syms = sorted(list(earnings_close_symbols)) if earnings_close_symbols else []
        system_state = {
            "bearish_halt_active": bool(bearish_halt),
            "earnings_close_symbols": ec_syms,
            "dry_run": bool(dry_run),
            "rebalance_use_ai_arbiter": bool(self.rebalance_use_ai_arbiter),
        }

        # --- Recent decision context (today + previous trading day) ---
        try:
            from src.journal import load_recent_decisions
            recent_decisions = load_recent_decisions(days_back=1)
        except Exception as e:
            log.info("Arbiter context: recent_decisions load failed (%s)", e)
            recent_decisions = {"today": [], "previous_trading_day": []}

        return {
            "equity": round(equity, 2),
            "cash": {
                "balance": round(cash, 2),
                "buying_power": round(buying_power, 2),
            },
            "current_allocation": current_alloc,
            "risk_profile": risk_profile,
            "trading_rules": trading_rules,
            "execution_constraints": execution_constraints,
            "system_state": system_state,
            "time_context": self._scan_time_context(),
            "macro": macro.to_dict(),
            "spy_block": spy_block,
            "positions": pos_ctx,
            "recent_decisions": recent_decisions,
            "scan_candidates_summary": (scan_candidates or [])[:10],
        }

    def _run_ai_on_held(
        self,
        symbols: list[str],
        numeric_map: dict,
        macro: MacroSignal,
        portfolio_ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Run the AI pipeline on a subset of held positions to get updated verdicts."""
        if not symbols or not self.ai.available():
            return {}
        candidates = [numeric_map[s] for s in symbols if s in numeric_map]
        if not candidates:
            return {}
        from src.ai_pipeline import AIPipeline
        import asyncio
        pipeline = AIPipeline(self.cfg, self.ai)
        async def _all():
            try:
                tasks = [pipeline.analyze_candidate(d.symbol, d, macro.to_dict(), portfolio_ctx)
                         for d in candidates]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                out = {}
                for d, r in zip(candidates, results):
                    if isinstance(r, Exception):
                        log.warning("AI on held %s failed: %s", d.symbol, r)
                        continue
                    out[d.symbol] = r
                return out
            finally:
                await pipeline.aclose()
        return asyncio.run(_all())

    def _validate_rebalance_buy_action(
        self,
        action: Any,
        equity: float,
    ) -> tuple[bool, dict[str, Any]]:
        """Validate a unified-plan BUY/ADD before submitting a protected order."""
        try:
            qty = float(action.ai_delta_qty or 0)
        except (TypeError, ValueError):
            qty = 0.0
        try:
            entry = float(action.ai_entry_price or 0)
        except (TypeError, ValueError):
            entry = 0.0
        if entry <= 0 and qty > 0:
            try:
                entry = float(action.delta_notional) / qty
            except (TypeError, ValueError, ZeroDivisionError):
                entry = 0.0
        audit: dict[str, Any] = {
            "source": "unified_rebalance_buy_safety",
            "symbol": action.symbol,
            "qty_delta": qty,
            "entry_price": entry,
            "is_new_entry": bool(getattr(action, "is_new_entry", False)),
            "current_notional": float(action.current_notional or 0),
            "target_notional": float(action.target_notional or 0),
            "target_pct": float(action.target_pct or 0),
            "hard_stop_loss_pct": float(self.risk.hard_stop_loss_pct),
            "max_position_pct": float(self.risk.max_position_pct),
            "max_risk_per_trade_pct": float(self.cfg.get("risk", "max_risk_per_trade_pct", default=0.005)),
        }
        if qty <= 0 or entry <= 0:
            audit.update({"status": "rejected", "reject_reason": "non_positive_qty_or_entry"})
            return False, audit
        submitted_qty = qty
        normalizer = getattr(self.client, "normalize_buy_qty_for_asset", None)
        if normalizer is not None:
            try:
                submitted_qty, asset_audit, asset_reject = normalizer(action.symbol, qty)
            except Exception as exc:
                audit.update({
                    "status": "rejected",
                    "reject_reason": f"asset_preflight_failed: {exc}",
                })
                return False, audit
            audit["asset_check"] = asset_audit
            if asset_reject:
                audit.update({
                    "status": "rejected",
                    "reject_reason": asset_reject,
                })
                return False, audit
        audit["submitted_qty"] = submitted_qty
        try:
            protective_stop = self.risk.protective_stop_loss_price(entry, action.ai_stop_loss)
        except ValueError as exc:
            audit.update({"status": "rejected", "reject_reason": str(exc)})
            return False, audit
        audit["stop_loss"] = protective_stop
        audit["hard_stop_loss_floor"] = self.risk.hard_stop_loss_price(entry)
        if action.ai_take_profit not in (None, ""):
            try:
                take_profit = float(action.ai_take_profit)
            except (TypeError, ValueError):
                audit.update({"status": "rejected", "reject_reason": "take_profit_not_numeric"})
                return False, audit
            if take_profit <= entry:
                audit.update({"status": "rejected", "reject_reason": "target_not_above_entry"})
                return False, audit

        delta_notional = submitted_qty * entry
        post_notional = float(action.current_notional or 0) + delta_notional
        max_notional = float(equity) * float(self.risk.max_position_pct)
        audit["delta_notional"] = round(delta_notional, 2)
        audit["post_trade_notional"] = round(post_notional, 2)
        audit["max_notional"] = round(max_notional, 2)
        if delta_notional < float(self.risk.min_trade):
            audit.update({
                "status": "rejected",
                "reject_reason": f"notional ${delta_notional:,.0f} below min_trade ${self.risk.min_trade}",
            })
            return False, audit
        if post_notional > max_notional * 1.01:
            audit.update({
                "status": "rejected",
                "reject_reason": (
                    f"post-trade notional ${post_notional:,.0f} exceeds "
                    f"max_position_pct ${max_notional:,.0f}"
                ),
            })
            return False, audit

        risk_usd = submitted_qty * (entry - protective_stop)
        risk_cap = float(equity) * float(audit["max_risk_per_trade_pct"])
        audit["risk_usd"] = round(risk_usd, 2)
        audit["max_risk_usd"] = round(risk_cap, 2)
        if risk_usd > risk_cap * 1.01:
            audit.update({
                "status": "rejected",
                "reject_reason": f"risk ${risk_usd:,.0f} exceeds max_risk_per_trade ${risk_cap:,.0f}",
            })
            return False, audit

        if bool(getattr(action, "is_new_entry", False)) and not self._is_cash_proxy(action.symbol):
            try:
                live_positions = self.client.get_positions()
            except Exception:
                live_positions = []
            held_syms = {
                p.symbol for p in live_positions
                if not self._is_cash_proxy(p.symbol) and abs(float(getattr(p, "qty", 0) or 0)) > 0
            }
            audit["held_count_before_new_entry"] = len(held_syms)
            audit["max_positions"] = int(self.risk.max_positions)
            if action.symbol not in held_syms and len(held_syms) >= int(self.risk.max_positions):
                audit.update({
                    "status": "rejected",
                    "reject_reason": f"max_positions_{int(self.risk.max_positions)}_reached",
                })
                return False, audit

        audit["status"] = "approved"
        return True, audit

    def _execute_ai_rebalance_action(
        self,
        action: Any,
        equity: float,
        cash_floor_pct: float,
        label: str,
    ) -> dict[str, Any]:
        """Execute one AI rebalance action without recomputing share size.

        The selector/arbiter emits the share delta. This helper either submits
        that exact delta or skips fail-closed; it never converts a target weight
        into a Python-sized trade.
        """
        action_dict = action.to_dict()
        full_exit = (
            action.side == "sell"
            and (action.target_notional <= 0 or action.target_pct <= 0 or action.ai_action == "EXIT")
        )
        # Phase 3: surface ATR to the executor so the protective stop can be
        # ATR-aware. ``action.tech_score`` doesn't carry ATR directly; pull
        # from the live tech_map captured for this scan.
        atr_for_stop = None
        try:
            tech_for_sym = (
                getattr(self, "_last_tech_map", None) or {}
            ).get(getattr(action, "symbol", ""))
            if tech_for_sym is not None:
                atr_for_stop = float(getattr(tech_for_sym, "atr", 0) or 0) or None
        except (TypeError, ValueError, AttributeError):
            atr_for_stop = None
        ai_audit = {
            "source": "ai_direct_rebalance",
            "label": label,
            "ai_delta_qty": action.ai_delta_qty,
            "ai_entry_price": getattr(action, "ai_entry_price", None),
            "ai_stop_loss": action.ai_stop_loss,
            "ai_take_profit": action.ai_take_profit,
            "target_pct": action.target_pct,
            "target_qty": action.target_qty,
            "current_qty": getattr(action, "current_qty", None),
            "delta_notional_reference": action.delta_notional,
            "current_notional": action.current_notional,
            "target_notional": action.target_notional,
            "ai_action": action.ai_action,
            "ai_confidence": getattr(action, "ai_confidence", None),
            "opportunity_score": getattr(action, "opportunity_score", None),
            # Phase 3: ATR for ATR-aware protective-stop floor.
            "atr": atr_for_stop,
        }
        try:
            if action.side == "sell":
                fresh_guard = self._fresh_exit_guard(action, full_exit=full_exit)
                if fresh_guard:
                    trim_pct = float(fresh_guard.get("downgrade_to_reduce_pct", 0) or 0)
                    if trim_pct > 0 and trim_pct < 1.0:
                        # Phase 5: downgrade full EXIT to partial REDUCE.
                        # Recompute delta_qty as a fraction of current_qty so
                        # the executor submits a partial sell rather than
                        # a close_position. Mutate the action in place.
                        try:
                            current_qty = abs(float(getattr(action, "current_qty", 0) or 0))
                        except (TypeError, ValueError):
                            current_qty = 0.0
                        if current_qty <= 0:
                            log.info(
                                "[%s] %s fresh-exit downgrade requested but current_qty unknown; skipping",
                                action.symbol, label,
                            )
                            return {
                                **action_dict,
                                "skipped": "fresh_exit_cooldown_low_confidence",
                                "fresh_exit_guard": fresh_guard,
                            }
                        trim_qty = round(current_qty * trim_pct, 6)
                        if trim_qty <= 0:
                            return {
                                **action_dict,
                                "skipped": "fresh_exit_cooldown_low_confidence",
                                "fresh_exit_guard": fresh_guard,
                            }
                        log.info(
                            "[%s] %s fresh-exit guard tier=%s age=%.1fm: "
                            "downgraded EXIT → REDUCE %.0f%% (qty=%.4f of %.4f)",
                            action.symbol, label,
                            fresh_guard.get("tier"),
                            fresh_guard.get("age_minutes", 0.0),
                            trim_pct * 100, trim_qty, current_qty,
                        )
                        log_decision({
                            "event": "fresh_exit_guard_downgraded",
                            "symbol": action.symbol,
                            "action": action_dict,
                            "guard": fresh_guard,
                            "trim_qty": trim_qty,
                            "current_qty": current_qty,
                        })
                        # Replace the full exit with a partial sell.
                        action.ai_delta_qty = -trim_qty
                        action.target_pct = max(0.0, float(getattr(action, "target_pct", 0.0) or 0.0))
                        # Force the caller out of the full_exit branch.
                        full_exit = False
                        ai_audit["fresh_exit_downgraded"] = {
                            "tier": fresh_guard.get("tier"),
                            "trim_pct": trim_pct,
                            "trim_qty": trim_qty,
                            "current_qty": current_qty,
                        }
                    else:
                        log.info(
                            "[%s] %s sell skipped by fresh-exit guard: conf=%.2f < %.2f",
                            action.symbol, label,
                            fresh_guard.get("ai_confidence", 0.0),
                            fresh_guard.get("min_confidence", 0.0),
                        )
                        log_decision({
                            "event": "fresh_exit_guard_skipped",
                            "symbol": action.symbol,
                            "action": action_dict,
                            "guard": fresh_guard,
                        })
                        return {
                            **action_dict,
                            "skipped": "fresh_exit_cooldown_low_confidence",
                            "fresh_exit_guard": fresh_guard,
                        }
            if full_exit:
                if action.ai_delta_qty is not None:
                    try:
                        if float(action.ai_delta_qty) > 0:
                            return {**action_dict, "skipped": "ai_delta_qty_side_mismatch"}
                    except (TypeError, ValueError):
                        return {**action_dict, "skipped": "invalid_ai_delta_qty"}
                exec_result = self.executor.close_position(action.symbol, reason=action.reason)
                action_dict["full_exit_via_close_position"] = True
                if exec_result.ok:
                    self._clear_position_lifecycle(action.symbol)
                return {**action_dict, "execution": exec_result.to_dict()}

            if action.ai_delta_qty is None:
                return {**action_dict, "skipped": "missing_ai_delta_qty"}
            try:
                delta_qty = float(action.ai_delta_qty)
            except (TypeError, ValueError):
                return {**action_dict, "skipped": "invalid_ai_delta_qty"}
            if abs(delta_qty) <= 0:
                return {**action_dict, "skipped": "zero_ai_delta_qty"}
            if action.side == "buy" and delta_qty <= 0:
                return {**action_dict, "skipped": "ai_delta_qty_side_mismatch"}
            if action.side == "sell" and delta_qty >= 0:
                return {**action_dict, "skipped": "ai_delta_qty_side_mismatch"}

            if action.side == "buy":
                ok, buy_audit = self._validate_rebalance_buy_action(action, equity)
                ai_audit["buy_safety"] = buy_audit
                if not ok:
                    return {
                        **action_dict,
                        "skipped": "buy_safety_rejected",
                        "risk_sizer": buy_audit,
                    }
                entry_ref = getattr(action, "ai_entry_price", None)
                if not entry_ref and abs(delta_qty) > 0:
                    entry_ref = float(action.delta_notional) / abs(delta_qty)
                submitted_qty = float(buy_audit.get("submitted_qty") or delta_qty)
                preflight_ok, preflight = self.executor.preflight_buy(
                    symbol=action.symbol,
                    qty=submitted_qty,
                    entry_price=float(entry_ref or 0),
                    stop_loss=action.ai_stop_loss,
                    take_profit=action.ai_take_profit,
                )
                ai_audit["execution_preflight"] = preflight
                if not preflight_ok:
                    return {
                        **action_dict,
                        "skipped": "execution_preflight_rejected",
                        "execution_preflight": preflight,
                    }
                submitted_qty = float(preflight.get("submitted_qty") or submitted_qty)
                funding_requirement = submitted_qty * float(entry_ref or 0)
                if funding_requirement <= 0:
                    funding_requirement = float(action.delta_notional)
                funded_notional = self._funded_buy_notional(
                    action.symbol, funding_requirement, equity, cash_floor_pct, label,
                )
                if funded_notional + 0.01 < funding_requirement:
                    return {
                        **action_dict,
                        "skipped": "insufficient_confirmed_cash",
                        "funded_notional": round(funded_notional, 2),
                    }
                ai_audit["submitted_qty"] = submitted_qty
                ai_audit["funding_requirement"] = round(funding_requirement, 2)
                exec_result = self.executor.execute_ai_bracket(
                    symbol=action.symbol,
                    qty=submitted_qty,
                    entry_price=float(entry_ref),
                    stop_loss=action.ai_stop_loss,
                    take_profit=action.ai_take_profit,
                    reason=action.reason,
                    ai_audit=ai_audit,
                )
                if exec_result.ok:
                    self._record_position_entry(
                        action.symbol,
                        source=label,
                        execution=exec_result.to_dict(),
                        context={
                            **ai_audit,
                            "reason": action.reason,
                            "one_sentence_reason": getattr(action, "one_sentence_reason", ""),
                            "ai_confidence": getattr(action, "ai_confidence", None),
                            "opportunity_score": getattr(action, "opportunity_score", None),
                        },
                    )
            elif action.side == "sell":
                exec_result = self.executor.execute_ai_qty_delta(
                    symbol=action.symbol,
                    delta_qty=delta_qty,
                    reason=action.reason,
                    ai_audit=ai_audit,
                )
            else:
                return {**action_dict, "skipped": f"invalid_side_{action.side}"}

            return {**action_dict, "execution": exec_result.to_dict()}
        except Exception as e:
            log.warning("[%s] %s AI rebalance action failed: %s", action.symbol, label, e)
            return {**action_dict, "_error": str(e)}

    def run_rebalance(
        self,
        macro: MacroSignal,
        portfolio: dict[str, Any],
        equity: float,
        dry_run: bool = False,
        allow_adds: bool = True,
        earnings_exit_symbols: set[str] | None = None,
        bearish_halt: bool = False,
    ) -> list[dict[str, Any]]:
        """Execute AI-driven portfolio rebalance.

        Hard rules:
          * The Opus 4.7 portfolio arbiter is the SOLE decision-maker.
          * NO non-AI fallback. If the AI is unavailable or returns an
            incomplete response after retries, this function logs a CRITICAL
            warning and executes ZERO trades (returns []).
          * NO post-AI overrides. Earnings windows, bearish-halt status, and
            recent decisions are passed INTO the AI as context — the AI
            decides what to do with them. The system enforces only safety
            (execution-cost floors), not strategy.
          * Runs every scan. If the arbiter says HOLD on every position,
            we still log a `rebalance_summary` so behavior is observable.

        Args:
            allow_adds: retained for backward compatibility; no longer
                filters AI decisions. The bearish_halt flag itself is
                forwarded as context to the arbiter.
        """
        from src.rebalance import (
            compute_rebalance_plan, load_tech_cache, save_tech_cache,
        )
        if not bool(self.cfg.get("rebalance", "enabled", default=True)):
            return []
        holdings = portfolio.get("holdings", [])
        tech_map = portfolio.get("tech_map", {})
        sent_map = portfolio.get("sent_map", {})
        numeric = portfolio.get("numeric", {})
        earnings_map = portfolio.get("earnings_map", {})
        if not holdings or not tech_map:
            log.info("Rebalance: no holdings or tech_map — nothing to do")
            return []
        # `allow_adds` is intentionally not consulted post-AI (fix #5). The
        # bearish_halt flag is passed to the arbiter as input context only.
        _ = allow_adds  # kept in signature for compatibility

        # --- BEFORE snapshot (logged after the run for diff context) ---
        before_snapshot = self._snapshot_portfolio(equity)

        # --- AI portfolio arbiter: ONE call decides target weights for all held ---
        ai_target_weights: dict[str, float] | None = None
        ai_per_symbol: dict[str, dict] | None = None
        ai_spy_target_pct: float | None = None
        ai_cash_target_pct: float | None = None
        ai_opportunity_ranking: list[str] = []
        arbiter_result: dict[str, Any] | None = None
        arbiter_ctx: dict[str, Any] | None = None

        # Hard rule: AI is the only path. If the AI is disabled or unavailable,
        # we execute zero trades and skip the rebalance. No deterministic fallback.
        # Reset per-scan arbiter telemetry
        self._last_opportunity_ranking = []
        self._last_arbiter_skipped = None
        self._last_arbiter_set_spy_target = False
        self._last_ai_target_weights = None
        self._last_ai_per_symbol = None
        self._last_ai_spy_target_pct = None
        self._last_ai_cash_target_pct = None

        if not (self.rebalance_use_ai_arbiter and self.ai.available()):
            log.critical(
                "REBALANCE SKIPPED: AI arbiter unavailable "
                "(use_ai_arbiter=%s, ai_available=%s) — no trades will execute "
                "this scan (fail-safe: no AI → no trades).",
                self.rebalance_use_ai_arbiter, self.ai.available(),
            )
            log_decision({
                "event": "ai_failure",
                "agent": "portfolio-arbiter",
                "reason": "ai_unavailable",
                "use_ai_arbiter": bool(self.rebalance_use_ai_arbiter),
                "ai_available": bool(self.ai.available()),
            })
            self._last_arbiter_skipped = "ai_unavailable"
            return []

        held_symbol_list = [
            p.symbol for p in holdings
            if not self._is_cash_proxy(p.symbol) and "/" not in p.symbol
        ]
        arbiter_ctx = self._build_arbiter_context(
            holdings=holdings, tech_map=tech_map, sent_map=sent_map,
            numeric=numeric, earnings_map=earnings_map, macro=macro, equity=equity,
            bearish_halt=bearish_halt, dry_run=dry_run,
            earnings_close_symbols=earnings_exit_symbols,
        )
        log.info(
            "Rebalance: invoking portfolio arbiter (model=%s) on %d held positions, "
            "equity=$%.0f, cash=$%.0f, BP=$%.0f, SPY=$%.0f, "
            "recent_decisions=%d today + %d prev day",
            self.cfg.get("ai", "trade_critical_model", default="?"),
            len(holdings),
            arbiter_ctx["equity"],
            arbiter_ctx["cash"]["balance"],
            arbiter_ctx["cash"]["buying_power"],
            arbiter_ctx["spy_block"]["current_value_usd"],
            len((arbiter_ctx.get("recent_decisions") or {}).get("today", [])),
            len((arbiter_ctx.get("recent_decisions") or {}).get("previous_trading_day", [])),
        )
        log_decision({
            "event": "portfolio_arbiter_input",
            "held_symbols": held_symbol_list,
            "intraday_chart_present": {
                "spy": bool(arbiter_ctx["spy_block"].get("intraday_chart")),
                **{p["symbol"]: bool(p.get("intraday_chart")) for p in arbiter_ctx["positions"]},
            },
            "context": arbiter_ctx,
        })
        arbiter_result = run_portfolio_arbiter(
            self.cfg, arbiter_ctx, held_symbols=held_symbol_list,
        )
        log_decision({
            "event": "portfolio_arbiter_output",
            "result": arbiter_result,
        })

        if not arbiter_result:
            log.critical(
                "REBALANCE SKIPPED: portfolio arbiter returned no valid response "
                "after retries — no trades will execute this scan."
            )
            after_snapshot = self._snapshot_portfolio(equity)
            log_decision({
                "event": "rebalance_summary",
                "before": before_snapshot,
                "after": after_snapshot,
                "arbiter_input_present": True,
                "arbiter_output_present": False,
                "actions_executed": 0,
                "skipped_reason": "ai_failure_after_retries",
                "dry_run": dry_run,
            })
            self._last_arbiter_skipped = "ai_failure_after_retries"
            return []

        ai_target_weights = {
            str(k): float(v)
            for k, v in (arbiter_result.get("target_weights") or {}).items()
        }
        ai_per_symbol = arbiter_result.get("per_symbol") or {}
        ai_opportunity_ranking = list(arbiter_result.get("opportunity_ranking") or [])
        self._last_opportunity_ranking = ai_opportunity_ranking
        spy_t = arbiter_result.get("spy_target_pct")
        cash_t = arbiter_result.get("cash_target_pct")
        if spy_t is not None:
            try:
                ai_spy_target_pct = max(0.0, min(1.0, float(spy_t)))
            except (TypeError, ValueError):
                ai_spy_target_pct = None
        if cash_t is not None:
            try:
                ai_cash_target_pct = max(0.0, min(1.0, float(cash_t)))
            except (TypeError, ValueError):
                ai_cash_target_pct = None
        log.info("Arbiter thesis: %s", (arbiter_result.get("portfolio_thesis") or "")[:200])
        log.info("Arbiter targets: %s",
                 {s: round(w, 3) for s, w in ai_target_weights.items()})
        log.info("Arbiter SPY target=%s%% cash target=%s%% (reasoning: %s)",
                 f"{ai_spy_target_pct*100:.1f}" if ai_spy_target_pct is not None else "n/a",
                 f"{ai_cash_target_pct*100:.1f}" if ai_cash_target_pct is not None else "n/a",
                 (arbiter_result.get("spy_vs_cash_reasoning") or "")[:200])
        cash_floor_pct = max(
            float(ai_cash_target_pct or 0.0),
            float(self.risk.cash_reserve_pct),
        )
        log.info("Arbiter opportunity ranking: %s", ai_opportunity_ranking)
        # Stash for the post-execution Sonnet verifier (run by orchestrator after
        # rebalance + entries + cash sweep complete). The verifier needs Opus's
        # exact targets to know what discrepancies to correct.
        self._last_ai_target_weights = dict(ai_target_weights)
        self._last_ai_per_symbol = dict(ai_per_symbol) if isinstance(ai_per_symbol, dict) else {}
        self._last_ai_spy_target_pct = ai_spy_target_pct
        self._last_ai_cash_target_pct = ai_cash_target_pct
        # Per-symbol audit log: action + opportunity_score + one_sentence_reason
        for sym in held_symbol_list:
            info = (ai_per_symbol or {}).get(sym, {})
            log.info(
                "Arbiter[%s] action=%s target=%.1f%% conf=%.2f opportunity=%.0f reason=%s",
                sym,
                info.get("action", "?"),
                float(info.get("target_pct", 0) or 0) * 100,
                float(info.get("confidence", 0) or 0),
                float(info.get("opportunity_score", 0) or 0),
                (info.get("one_sentence_reason") or "")[:160],
            )
        spy_dec = arbiter_result.get("spy_decision") or {}
        if spy_dec:
            log.info(
                "Arbiter[SPY] action=%s target=%.1f%% opportunity=%.0f reason=%s",
                spy_dec.get("action", "?"),
                float(spy_dec.get("target_pct", 0) or 0) * 100,
                float(spy_dec.get("opportunity_score", 0) or 0),
                (spy_dec.get("one_sentence_reason") or "")[:160],
            )
        for mv in (arbiter_result.get("capital_movement_plan") or []):
            log.info("Arbiter capital plan: %s %s$%.0f — %s",
                     mv.get("symbol"),
                     "+" if float(mv.get("delta_usd", 0) or 0) >= 0 else "-",
                     abs(float(mv.get("delta_usd", 0) or 0)),
                     (mv.get("purpose") or ""))
        for flag in (arbiter_result.get("risk_flags") or []):
            log.info("Arbiter risk flag: %s", flag)

        # --- Build plan from AI output (no post-AI overrides) ---
        plan = compute_rebalance_plan(
            positions=holdings,
            tech_map=tech_map,
            sent_map=sent_map,
            numeric_decisions=numeric,
            ai_verdicts={},
            equity=equity,
            config=self.cfg,
            cash_proxy_symbol=self.cash_proxy_symbol if self.cash_proxy_enabled else None,
            ai_target_weights=ai_target_weights,
            ai_per_symbol=ai_per_symbol,
        )

        log.info(
            "Rebalance plan: %d actions (%d trims/exits, %d adds)",
            len(plan),
            sum(1 for a in plan if a.current_notional > a.target_notional),
            sum(1 for a in plan if a.current_notional < a.target_notional),
        )

        # --- Execute with fill verification and per-action cash reassessment ---
        results: list[dict[str, Any]] = []
        for a in plan:
            if dry_run:
                log.info("[DRY] Rebalance %s", a.to_dict())
                results.append({"dry_run": True, **a.to_dict()})
                continue
            action_result = self._execute_ai_rebalance_action(
                a, equity=equity, cash_floor_pct=cash_floor_pct, label="rebalance",
            )
            results.append(action_result)
            exec_result = action_result.get("execution") or {}
            if exec_result and not exec_result.get("ok"):
                log.warning("[%s] rebalance action did not fill", a.symbol)

        # --- Honor AI's SPY-vs-cash split ---
        # When the arbiter set spy_target_pct we move SPY toward that target
        # explicitly (rather than letting the deterministic auto-sweep decide).
        # SPY is treated as fully liquid: any delta is a notional buy/sell.
        spy_action_result: dict[str, Any] | None = None
        self._last_arbiter_set_spy_target = (
            arbiter_result is not None and ai_spy_target_pct is not None
        )
        if (not dry_run and self.cash_proxy_enabled and arbiter_result is not None
                and ai_spy_target_pct is not None):
            spy_action_result = self._apply_spy_target(
                target_pct=ai_spy_target_pct, equity=equity,
            )
            if spy_action_result:
                results.append({"event": "spy_rebalance", **spy_action_result})

        # --- Update tech-score cache (kept for any consumer; arbiter doesn't use it) ---
        cache = load_tech_cache()
        for sym, t in tech_map.items():
            cache[sym] = float(t.score)
        held_syms = {p.symbol for p in holdings}
        cache = {s: v for s, v in cache.items() if s in held_syms}
        save_tech_cache(cache)

        # --- AFTER snapshot + diff log ---
        after_snapshot = self._snapshot_portfolio(equity)
        log_decision({
            "event": "rebalance_summary",
            "before": before_snapshot,
            "after": after_snapshot,
            "arbiter_input_present": arbiter_ctx is not None,
            "arbiter_output_present": arbiter_result is not None,
            "ai_spy_target_pct": ai_spy_target_pct,
            "ai_cash_target_pct": ai_cash_target_pct,
            "ai_opportunity_ranking": ai_opportunity_ranking,
            "ai_actions": [
                {
                    "symbol": a["symbol"],
                    "ai_action": a.get("ai_action"),
                    "side": a.get("side"),
                    "delta_notional": a.get("delta_notional"),
                    "target_pct": a.get("target_pct"),
                    "opportunity_score": a.get("opportunity_score"),
                    "one_sentence_reason": a.get("one_sentence_reason"),
                }
                for a in results if "symbol" in a
            ],
            "actions_executed": len(results),
            "dry_run": dry_run,
        })
        log.info(
            "Rebalance done: equity $%.0f→$%.0f, cash $%.0f→$%.0f, SPY $%.0f→$%.0f, "
            "actions=%d (incl SPY=%s)",
            before_snapshot["equity"], after_snapshot["equity"],
            before_snapshot["cash"], after_snapshot["cash"],
            before_snapshot["spy_value"], after_snapshot["spy_value"],
            len(results), "yes" if spy_action_result else "no",
        )

        return results

    def _apply_spy_target(self, target_pct: float, equity: float) -> dict[str, Any] | None:
        """Move SPY position toward AI's target weight. SPY is fully liquid; we
        sell to free cash or buy to absorb idle cash. No-op if delta is below
        the cash-proxy minimum threshold.
        """
        if not self.cash_proxy_enabled or equity <= 0:
            return None
        try:
            positions = self.client.get_positions()
        except Exception as e:
            log.warning("SPY target apply: positions fetch failed: %s", e)
            return None
        proxy = self._get_proxy_position(positions)
        current_value = abs(float(proxy.market_value)) if proxy else 0.0
        target_value = max(0.0, float(target_pct)) * equity
        delta = target_value - current_value
        if abs(delta) < self.cash_proxy_min:
            log.info("SPY at target: current=$%.0f, target=$%.0f (delta $%.0f < min $%.0f)",
                     current_value, target_value, abs(delta), self.cash_proxy_min)
            return {
                "symbol": self.cash_proxy_symbol, "action": "hold",
                "current_value": round(current_value, 2),
                "target_value": round(target_value, 2),
                "delta_usd": round(delta, 2),
                "ai_target_pct": round(float(target_pct), 4),
            }
        side = "buy" if delta > 0 else "sell"
        # If buying SPY, ensure cash is available; if selling, no cash check needed.
        if side == "sell":
            sell_amt = min(abs(delta), current_value)
            ok = self._sell_cash_proxy_for(sell_amt, "SPY target rebalance")
            if ok:
                log.info("SPY rebalance SELL $%.0f: %s %.1f%% → target %.1f%% of equity",
                         sell_amt, self.cash_proxy_symbol,
                         current_value / equity * 100, float(target_pct) * 100)
                return {
                    "symbol": self.cash_proxy_symbol, "action": "sell",
                    "delta_usd": round(-sell_amt, 2),
                    "current_value": round(current_value, 2),
                    "target_value": round(target_value, 2),
                    "ai_target_pct": round(float(target_pct), 4),
                }
            return {
                "symbol": self.cash_proxy_symbol,
                "action": "sell_failed",
                "requested_delta_usd": round(-sell_amt, 2),
            }
        # BUY: only buy with cash above the hard floor
        try:
            acct = self.client.get_account()
            cash = float(acct.cash)
        except Exception as e:
            log.warning("SPY rebalance buy: account fetch failed: %s", e)
            return None
        floor = equity * self.risk.cash_reserve_min_pct
        affordable = max(0.0, cash - floor)
        buy_amt = min(abs(delta), affordable)
        if buy_amt < self.cash_proxy_min:
            log.info("SPY rebalance buy skipped: cash above floor only $%.0f (need $%.0f)",
                     affordable, abs(delta))
            return {
                "symbol": self.cash_proxy_symbol, "action": "buy_capped",
                "delta_usd": round(buy_amt, 2),
                "available_cash_above_floor": round(affordable, 2),
                "ai_target_pct": round(float(target_pct), 4),
            }
        buy_result = submit_cash_proxy_buy(
            self.client,
            self.cfg,
            self.cash_proxy_symbol,
            buy_amt,
            reason="SPY target rebalance",
        )
        if buy_result.get("action") == "buy_proxy" and buy_result.get("ok", True):
            log.info("SPY rebalance BUY $%.0f: %s %.1f%% → target %.1f%% of equity",
                     buy_amt, self.cash_proxy_symbol,
                     current_value / equity * 100, float(target_pct) * 100)
            return {
                "symbol": self.cash_proxy_symbol, "action": "buy",
                "delta_usd": round(buy_amt, 2),
                "current_value": round(current_value, 2),
                "target_value": round(target_value, 2),
                "ai_target_pct": round(float(target_pct), 4),
                "cash_proxy_buy": buy_result,
            }
        log.warning("SPY rebalance buy failed/skipped: %s", buy_result)
        return {
            "symbol": self.cash_proxy_symbol,
            "action": "buy_failed" if buy_result.get("action") == "buy_failed" else "buy_skipped",
            "requested_delta_usd": round(buy_amt, 2),
            "cash_proxy_buy": buy_result,
        }

    # ---------- post-execution portfolio verifier (Sonnet 4.6) ----------
    def _verify_portfolio_alignment(self, equity: float) -> dict[str, Any] | None:
        """Reconcile actual portfolio against the targets the Opus arbiter set
        for this scan. Two passes:

        1. Deterministic dust sweep: any symbol where Opus target is 0 (or
           absent from target_weights) but the position still has any shares
           is force-closed via Alpaca's `close_position` API (qty-based, no
           dust). This fixes the chronic "0.09 shares left after liquidate"
           problem caused by notional-sized closes drifting on price.

        2. Sonnet 4.6 corrective pass: builds a current-vs-target diff over
           the tolerance band and asks the verifier to propose corrective
           trades. Sonnet's response is hard-filtered server-side — only
           same-direction toward-target trades on Opus-approved symbols
           survive. Anything else is rejected before execution.

        Skipped if: arbiter didn't run / set targets this scan, AI unavailable,
        verifier disabled in config. Never raises — returns a summary dict
        (or None on skip).
        """
        from src.ai_pipeline import run_portfolio_verifier

        if not bool(self.cfg.get("portfolio_verifier", "enabled", default=True)):
            return None
        target_weights = self._last_ai_target_weights
        if not isinstance(target_weights, dict) or not target_weights:
            log.info("Verifier skipped: no Opus targets stashed this scan "
                     "(arbiter skipped or returned no targets).")
            return None

        spy_target = self._last_ai_spy_target_pct
        cash_target = self._last_ai_cash_target_pct
        per_symbol = self._last_ai_per_symbol or {}

        try:
            account, positions = self.client.get_snapshot(force_refresh=True, log_detail=False)
        except Exception as e:
            log.warning("Verifier: snapshot fetch failed: %s — skipping reconcile", e)
            return None
        live_equity = float(account.equity) if account else equity
        cash_usd = float(account.cash) if account else 0.0

        # ---- Pass 1: deterministic dust sweep ----
        # Phase 1b: same-day fresh-entry guard. Today's review (2026-05-05)
        # showed 5 positions opened by the selector dust-swept on the very
        # next scan because the selector's targets evicted them within 1-2
        # hours of entry. This produced ~$50K of churn for a tiny net P&L.
        # Guard: if a position was opened today and isn't materially in the
        # red, skip the dust-sweep — give the thesis a chance to play out.
        guard_loss_floor = float(
            self.cfg.get("portfolio_verifier", "fresh_entry_loss_floor_pct",
                         default=-0.005) or -0.005
        )
        dust_closed: list[dict[str, Any]] = []
        skipped_fresh: list[dict[str, Any]] = []
        for p in positions:
            sym = p.symbol
            # SPY is reconciled separately via _apply_spy_target — skip here.
            if sym == self.cash_proxy_symbol:
                continue
            qty = abs(float(p.qty))
            if qty <= 0:
                continue
            tw = float(target_weights.get(sym, 0.0) or 0.0)
            if tw <= 0.0:
                # Phase 1b guard: skip dust-sweep for very-fresh entries
                # that aren't already losing money.
                if self._verifier_dust_sweep_blocked_fresh(
                    sym, p, loss_floor_pct=guard_loss_floor,
                ):
                    skipped_fresh.append({"symbol": sym, "qty_before": qty})
                    continue
                # Target zero but residual shares. Route through the executor so
                # protective child orders are canceled before the close request.
                log.info("Verifier dust-sweep: force-closing %s (qty=%s, target=0%%)", sym, qty)
                exec_result = self.executor.close_position(
                    sym,
                    reason="verifier dust-sweep target=0",
                )
                action = "force_close_100pct" if exec_result.ok else "force_close_failed"
                dust_closed.append({
                    "symbol": sym,
                    "action": action,
                    "qty_before": qty,
                    "filled_qty": exec_result.filled_qty,
                    "final_status": exec_result.final_status,
                    "order_id": exec_result.order_id,
                    "error": None if exec_result.ok else exec_result.message,
                })
                if exec_result.ok:
                    self._clear_position_lifecycle(sym)

        # Refresh after dust sweep so weight calc reflects post-close state.
        if dust_closed:
            try:
                account, positions = self.client.get_snapshot(force_refresh=True, log_detail=False)
                live_equity = float(account.equity) if account else live_equity
                cash_usd = float(account.cash) if account else cash_usd
            except Exception as e:
                log.warning("Verifier: post-dust snapshot refresh failed: %s", e)
        if skipped_fresh:
            log.info(
                "Verifier: dust-sweep skipped on %d fresh-entry position(s): %s",
                len(skipped_fresh),
                ", ".join(s["symbol"] for s in skipped_fresh),
            )

        # ---- Build current-vs-target diff for Sonnet ----
        tolerance_pct = float(self.cfg.get("portfolio_verifier", "tolerance_pct_of_equity", default=0.005))
        tolerance_usd = tolerance_pct * live_equity
        min_corrective_usd = float(self.cfg.get("portfolio_verifier", "min_corrective_usd", default=50))

        # All symbols Opus had a target for, even if currently flat (might need to add).
        # Plus any current position not in targets (already swept above, but defensive).
        symbols_to_consider: set[str] = set(str(s) for s in target_weights.keys())
        symbols_to_consider.update(p.symbol for p in positions
                                   if p.symbol != self.cash_proxy_symbol
                                   and abs(float(p.qty)) > 0)
        # Drop dust-closed (fully liquidated) so verifier doesn't try to add back.
        dust_closed_syms = {d["symbol"] for d in dust_closed
                            if d.get("action") == "force_close_100pct"}

        pos_by_sym = {p.symbol: p for p in positions}
        diff_rows: list[dict[str, Any]] = []
        for sym in sorted(symbols_to_consider):
            tw = float(target_weights.get(sym, 0.0) or 0.0)
            if tw <= 0.0:
                continue  # target=0 cases handled by dust sweep
            p = pos_by_sym.get(sym)
            mv = abs(float(p.market_value)) if p else 0.0
            qty = float(p.qty) if p else 0.0
            cur_w = (mv / live_equity) if live_equity > 0 else 0.0
            target_usd = tw * live_equity
            gap_usd = target_usd - mv  # positive => under target (need buy)
            gap_pct = (gap_usd / live_equity) if live_equity > 0 else 0.0
            info = per_symbol.get(sym, {}) or {}
            current_price = float(getattr(p, "current_price", 0) or 0) if p else 0.0
            if current_price <= 0:
                try:
                    current_price = float(info.get("entry_price", 0) or 0)
                except (TypeError, ValueError):
                    current_price = 0.0
            diff_rows.append({
                "symbol": sym,
                "qty": round(qty, 6),
                "current_price": round(current_price, 4),
                "market_value_usd": round(mv, 2),
                "current_weight": round(cur_w, 4),
                "target_weight": round(tw, 4),
                "target_qty": info.get("qty"),
                "gap_usd": round(gap_usd, 2),
                "gap_pct_of_equity": round(gap_pct, 4),
                "above_tolerance": abs(gap_usd) > tolerance_usd,
                "opus_action": info.get("action"),
            })

        ctx = {
            "equity": round(live_equity, 2),
            "tolerance_pct_of_equity": tolerance_pct,
            "tolerance_usd": round(tolerance_usd, 2),
            "min_corrective_usd": min_corrective_usd,
            "opus_targets": {
                "target_weights": {s: round(float(w), 4) for s, w in target_weights.items()},
                "spy_target_pct": spy_target,
                "cash_target_pct": cash_target,
                "per_symbol": {s: {"action": (info or {}).get("action"),
                                    "qty": (info or {}).get("qty"),
                                    "delta_qty": (info or {}).get("delta_qty"),
                                    "entry_price": (info or {}).get("entry_price"),
                                    "stop_loss": (info or {}).get("stop_loss"),
                                    "take_profit": (info or {}).get("take_profit"),
                                    "one_sentence_reason": (info or {}).get("one_sentence_reason")}
                               for s, info in per_symbol.items()},
            },
            "current_portfolio": {
                "cash_usd": round(cash_usd, 2),
                "positions": diff_rows,
            },
            "dust_already_liquidated": sorted(dust_closed_syms),
        }

        log.info(
            "Verifier: equity=$%.0f, tolerance=$%.0f (%.2f%% of eq), "
            "off-target positions=%d, dust closed=%d",
            live_equity, tolerance_usd, tolerance_pct * 100,
            sum(1 for r in diff_rows if r["above_tolerance"]),
            len(dust_closed),
        )

        out = run_portfolio_verifier(self.cfg, ctx)
        if not out:
            return {"dust_closed": dust_closed, "verifier_skipped": "no_response",
                    "corrective_trades": []}

        log.info("Verifier thesis: %s", (out.get("verifier_thesis") or "")[:200])

        # ---- Hard filter Sonnet's proposed trades (defense in depth) ----
        proposed = out.get("corrective_trades") or []
        if not isinstance(proposed, list):
            log.warning("Verifier: corrective_trades not a list — discarding")
            proposed = []

        diff_by_sym = {r["symbol"]: r for r in diff_rows}
        executed: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for prop in proposed:
            if not isinstance(prop, dict):
                rejected.append({"reason": "non-dict", "raw": str(prop)[:120]})
                continue
            sym = str(prop.get("symbol", "")).strip()
            side = str(prop.get("side", "")).lower().strip()
            try:
                delta_qty = abs(float(prop.get("delta_qty", 0) or 0))
            except (TypeError, ValueError):
                rejected.append({"symbol": sym, "reason": "delta_qty not numeric"})
                continue
            if not sym:
                rejected.append({"reason": "missing symbol"})
                continue
            if sym in dust_closed_syms:
                rejected.append({"symbol": sym, "reason": "already dust-liquidated this pass"})
                continue
            row = diff_by_sym.get(sym)
            if not row:
                rejected.append({"symbol": sym, "reason": "not in Opus target_weights — verifier may not introduce new symbols"})
                continue
            if not row["above_tolerance"]:
                rejected.append({"symbol": sym, "reason": f"within tolerance band (gap ${row['gap_usd']:.0f} <= ${tolerance_usd:.0f})"})
                continue
            if side not in ("buy", "sell"):
                rejected.append({"symbol": sym, "reason": f"invalid side {side!r}"})
                continue
            required_side = "buy" if row["gap_usd"] > 0 else "sell"
            if side != required_side:
                rejected.append({"symbol": sym, "reason": f"side {side} would move away from target (need {required_side})"})
                continue
            current_price = float(row.get("current_price", 0) or 0)
            if current_price <= 0:
                rejected.append({"symbol": sym, "reason": "missing current_price for qty validation"})
                continue
            delta_usd = delta_qty * current_price
            if delta_qty <= 0:
                rejected.append({"symbol": sym, "reason": "delta_qty must be > 0"})
                continue
            if delta_usd < min_corrective_usd:
                rejected.append({"symbol": sym, "reason": f"delta ${delta_usd:.0f} < min ${min_corrective_usd:.0f}"})
                continue
            if delta_usd > abs(row["gap_usd"]) * 1.01:
                rejected.append({"symbol": sym, "reason": f"delta_qty would overshoot gap (${delta_usd:.0f} > ${abs(row['gap_usd']):.0f})"})
                continue
            if side == "sell" and delta_qty > abs(float(row.get("qty", 0) or 0)) * 1.01:
                rejected.append({"symbol": sym, "reason": "delta_qty exceeds held qty"})
                continue
            try:
                if side == "buy":
                    floor_pct = max(float(cash_target or 0.0), float(self.risk.cash_reserve_pct))
                    opus_info = per_symbol.get(sym, {}) or {}
                    entry_ref = opus_info.get("entry_price") or current_price
                    preflight_ok, preflight = self.executor.preflight_buy(
                        symbol=sym,
                        qty=delta_qty,
                        entry_price=float(entry_ref),
                        stop_loss=opus_info.get("stop_loss"),
                        take_profit=opus_info.get("take_profit"),
                    )
                    if not preflight_ok:
                        rejected.append({
                            "symbol": sym,
                            "reason": "execution_preflight_rejected",
                            "execution_preflight": preflight,
                        })
                        continue
                    submitted_qty = float(preflight.get("submitted_qty") or delta_qty)
                    if abs(submitted_qty - delta_qty) > 1e-9:
                        delta_qty = submitted_qty
                        delta_usd = submitted_qty * current_price
                    funded_delta = self._funded_buy_notional(
                        sym, delta_usd, live_equity, floor_pct, "verifier",
                    )
                    if funded_delta + 0.01 < delta_usd:
                        rejected.append({"symbol": sym, "reason": "insufficient_confirmed_cash"})
                        continue
                    exec_res = self.executor.execute_ai_bracket(
                        symbol=sym,
                        qty=delta_qty,
                        entry_price=float(entry_ref),
                        stop_loss=opus_info.get("stop_loss"),
                        take_profit=opus_info.get("take_profit"),
                        reason=f"verifier reconcile to Opus target {row['target_weight']*100:.1f}% "
                               f"(gap was ${row['gap_usd']:+.0f})",
                        ai_audit={"source": "portfolio_verifier", "proposal": prop,
                                  "row": row, "per_symbol": opus_info,
                                  "execution_preflight": preflight},
                    )
                    if exec_res.ok:
                        self._record_position_entry(
                            sym,
                            source="portfolio_verifier",
                            execution=exec_res.to_dict(),
                            context={
                                "reason": f"verifier reconcile to Opus target {row['target_weight']*100:.1f}%",
                                "ai_action": opus_info.get("action"),
                                "ai_confidence": opus_info.get("confidence"),
                                "opportunity_score": opus_info.get("opportunity_score"),
                            },
                        )
                else:
                    exec_res = self.executor.execute_ai_qty_delta(
                        symbol=sym,
                        delta_qty=-delta_qty,
                        reason=f"verifier reconcile to Opus target {row['target_weight']*100:.1f}% "
                               f"(gap was ${row['gap_usd']:+.0f})",
                        ai_audit={"source": "portfolio_verifier", "proposal": prop, "row": row},
                    )
                executed.append({
                    "symbol": sym, "side": side,
                    "proposed_qty": round(delta_qty, 6),
                    "estimated_usd": round(delta_usd, 2),
                    "current_weight": row["current_weight"],
                    "target_weight": row["target_weight"],
                    "gap_usd_before": row["gap_usd"],
                    "execution": exec_res.to_dict(),
                })
                if not exec_res.ok:
                    log.warning("[%s] verifier corrective %s did not fill", sym, side)
            except Exception as e:
                log.warning("[%s] verifier corrective %s raised: %s", sym, side, e)
                rejected.append({"symbol": sym, "reason": f"execution raised: {e}"})

        log.info("Verifier: corrective trades executed=%d, rejected=%d, dust closed=%d",
                 len(executed), len(rejected), len(dust_closed))
        return {
            "verifier_thesis": out.get("verifier_thesis", ""),
            "tolerance_usd": round(tolerance_usd, 2),
            "dust_closed": dust_closed,
            "corrective_trades": executed,
            "rejected_proposals": rejected,
            "raw_proposals": proposed,
        }

    # ---------- portfolio-selector (Phase 4 cutover) ----------

    def _compute_floor_breach_flag(
        self,
        macro: MacroSignal,
        top_score: float | None = None,
    ) -> bool:
        """True when the 3-position floor may be relaxed to 0–6.

        Conditions are configured under ``selector.floor_breach_conditions``.
        Returns True if any enabled condition fires; False otherwise.
        """
        cfg_breach = self.cfg.get("selector", "floor_breach_conditions", default={}) or {}
        if cfg_breach.get("bear_regime"):
            sev = float(macro.score) < -0.5
            below_200 = float(getattr(macro, "spy_vs_200ema", 0.0) or 0.0) < 0.0
            if sev and below_200:
                log.info("[selector] floor breach allowed: bear regime "
                         "(score=%.2f, spy_vs_200ema<0)", macro.score)
                return True
        ts_below = cfg_breach.get("top_score_below")
        if ts_below is not None and top_score is not None:
            try:
                if float(top_score) < float(ts_below):
                    log.info("[selector] floor breach allowed: top_score=%.2f < %.2f",
                             top_score, ts_below)
                    return True
            except (TypeError, ValueError):
                pass
        return False

    def _selector_state_path(self) -> Path:
        rel = self.cfg.get("selector", "state_file",
                           default="data/state/selector_state.json")
        return Path(__file__).resolve().parents[1] / rel

    def _handle_selector_failure(self, reason: str) -> int:
        """Persist consecutive-failure counter; escalate at threshold."""
        path = self._selector_state_path()
        state: dict[str, Any] = {"consecutive_failures": 0, "last_failure_ts": None}
        if path.exists():
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        state["consecutive_failures"] = int(state.get("consecutive_failures", 0)) + 1
        state["last_failure_ts"] = pd.Timestamp.utcnow().isoformat()
        state["last_reason"] = reason
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(state), encoding="utf-8")
        except OSError as e:
            log.warning("[selector] could not persist state: %s", e)
        threshold = int(self.cfg.get("selector", "max_consecutive_failures", default=3) or 3)
        if state["consecutive_failures"] >= threshold:
            log_decision({
                "event": "selector_failure_escalated",
                "consecutive_count": state["consecutive_failures"],
                "reason": reason,
            })
            try:
                if hasattr(self, "telegram") and self.telegram is not None:
                    self.telegram.send_error(
                        f"CRITICAL: portfolio-selector failed "
                        f"{state['consecutive_failures']} consecutive scans "
                        f"(reason: {reason}) — manual intervention required."
                    )
            except Exception as e:
                log.warning("[selector] telegram escalation failed: %s", e)
        return state["consecutive_failures"]

    def _reset_selector_failures(self) -> None:
        path = self._selector_state_path()
        try:
            if path.exists():
                state = json.loads(path.read_text(encoding="utf-8"))
                if state.get("consecutive_failures", 0) > 0:
                    state["consecutive_failures"] = 0
                    state["last_success_ts"] = pd.Timestamp.utcnow().isoformat()
                    path.write_text(json.dumps(state), encoding="utf-8")
        except (OSError, json.JSONDecodeError):
            pass

    def _build_unified_candidate_pool(
        self,
        portfolio: dict[str, Any],
    ) -> tuple[list[Candidate], dict[str, int]]:
        """Build the discovery pool {held ∪ newly discovered}, returning the
        Candidate list and a sources-breakdown counter for logging.
        """
        held_syms = [
            p.symbol for p in portfolio.get("holdings", [])
            if not self._is_cash_proxy(p.symbol)
        ]
        mds = get_market_data(self.cfg)
        candidates, breakdown = discover_candidates(
            self.cfg, mds, held_symbols=held_syms,
        )
        candidates, asset_removed = self._prune_untradable_candidates(
            candidates,
            set(held_syms),
        )
        for row in asset_removed:
            reason = str(row.get("reason") or "unknown").split(":", 1)[0]
            key = f"alpaca_{reason}_removed"
            breakdown[key] = int(breakdown.get(key, 0) or 0) + 1
        return candidates, breakdown

    def _seed_cash_proxy_target_weight(self, result: dict[str, Any]) -> None:
        """Mirror selector spy_target_pct into target_weights before repairs.

        The sector guard moves rejected stock allocation into the cash proxy.
        Its inputs are target_weights-only, while the selector normally keeps
        SPY in a separate spy_target_pct field, so seed the proxy weight first
        to preserve the original SPY target plus any recovered allocation.
        """
        if not self.cash_proxy_enabled:
            return
        target_weights = result.get("target_weights")
        if not isinstance(target_weights, dict):
            return
        proxy = str(self.cash_proxy_symbol or "").upper()
        if not proxy or proxy in {str(s).upper() for s in target_weights.keys()}:
            return
        try:
            spy_target = float(result.get("spy_target_pct", 0) or 0)
        except (TypeError, ValueError):
            return
        if spy_target > 0:
            target_weights[proxy] = round(max(0.0, min(1.0, spy_target)), 4)

    def _sync_cash_proxy_target_from_weights(self, result: dict[str, Any]) -> None:
        """Keep spy_target_pct consistent when guard repairs target_weights."""
        if not self.cash_proxy_enabled:
            return
        target_weights = result.get("target_weights")
        if not isinstance(target_weights, dict):
            return
        proxy = str(self.cash_proxy_symbol or "").upper()
        match = next(
            (s for s in target_weights.keys() if str(s).upper() == proxy),
            None,
        )
        if match is None:
            return
        try:
            proxy_weight = float(target_weights.get(match, 0) or 0)
        except (TypeError, ValueError):
            return
        proxy_weight = round(max(0.0, min(1.0, proxy_weight)), 4)
        result["spy_target_pct"] = proxy_weight
        spy_decision = result.get("spy_decision")
        if isinstance(spy_decision, dict):
            spy_decision["target_pct"] = proxy_weight

    def _prune_zero_target_selected_positions(self, result: dict[str, Any]) -> list[str]:
        """Drop guard-removed zero-weight symbols from selected_positions."""
        selected = result.get("selected_positions")
        target_weights = result.get("target_weights")
        if not isinstance(selected, list) or not isinstance(target_weights, dict):
            return []
        proxy = str(self.cash_proxy_symbol or "").upper() if self.cash_proxy_enabled else ""
        kept: list[str] = []
        removed: list[str] = []
        for sym in selected:
            sym_s = str(sym)
            if proxy and sym_s.upper() == proxy:
                continue
            try:
                target = float(target_weights.get(sym_s, 0.0) or 0.0)
            except (TypeError, ValueError):
                target = 0.0
            if target > 0:
                kept.append(sym_s)
            else:
                removed.append(sym_s)
        if removed:
            result["selected_positions"] = kept
            result["sector_guard_removed_targets"] = removed
        return removed

    def _stage_new_entry_targets(
        self,
        result: dict[str, Any],
        held_symbols: set[str],
        equity: float,
    ) -> tuple[dict[str, float], dict[str, dict[str, Any]], float, list[dict[str, Any]]]:
        """Apply the configured starter fraction to brand-new selector entries.

        The selector can still rank and size against the desired final book, but
        the first fill starts at ~70% of that target. The remaining target is
        treated as cash for this scan so the verifier does not immediately buy
        the other 30% back in the same cycle.
        """
        target_weights = {
            str(s): float(w or 0.0)
            for s, w in (result.get("target_weights") or {}).items()
        }
        per_symbol = {
            str(s): dict(info or {})
            for s, info in (result.get("per_symbol") or {}).items()
        }
        cash_target_pct = float(result.get("cash_target_pct", 0) or 0)
        base_fraction = float(self.cfg.get(
            "selector", "new_entry_initial_fraction", default=0.70,
        ) or 0.70)
        base_fraction = max(0.05, min(1.0, base_fraction))
        strong_fraction = float(self.cfg.get(
            "selector", "new_entry_strong_initial_fraction", default=0.85,
        ) or 0.85)
        max_fraction = float(self.cfg.get(
            "selector", "new_entry_max_initial_fraction", default=0.90,
        ) or 0.90)
        strong_fraction = max(base_fraction, min(max_fraction, strong_fraction))
        strong_min_score = float(self.cfg.get(
            "selector", "new_entry_strong_min_opportunity_score", default=85,
        ) or 85)
        strong_min_conf = float(self.cfg.get(
            "selector", "new_entry_strong_min_confidence", default=0.75,
        ) or 0.75)
        tape_state = result.get("_tape_state") or {}
        tape_severity = str((tape_state or {}).get("severity_label") or "favorable")
        risk_off_tape = tape_severity in ("mild_risk_off", "strong_risk_off")
        if base_fraction >= 0.999:
            return target_weights, per_symbol, cash_target_pct, []

        adjustments: list[dict[str, Any]] = []
        selected = set(str(s) for s in (result.get("selected_positions") or []))
        for sym in sorted(selected - held_symbols):
            if "/" in sym:
                continue
            original_w = float(target_weights.get(sym, 0.0) or 0.0)
            if original_w <= 0:
                continue
            info = dict(per_symbol.get(sym) or {})
            try:
                opp_score = float(info.get("opportunity_score", 0) or 0)
            except (TypeError, ValueError):
                opp_score = 0.0
            confidence = self._selector_entry_confidence(info)
            fraction = base_fraction
            fraction_reason = "base"
            if (
                not risk_off_tape
                and opp_score >= strong_min_score
                and confidence >= strong_min_conf
            ):
                fraction = strong_fraction
                fraction_reason = "strong_opportunity"
            staged_w = round(original_w * fraction, 4)
            if staged_w <= 0:
                continue
            freed_w = max(0.0, original_w - staged_w)
            try:
                entry = float(info.get("entry_price", 0) or 0)
                original_qty = float(info.get("qty", 0) or 0)
            except (TypeError, ValueError):
                entry = 0.0
                original_qty = 0.0
            staged_qty = original_qty
            if entry > 0:
                staged_qty = min(original_qty, (staged_w * equity) / entry)
                staged_qty = round(max(0.0, staged_qty), 4)
            info["target_pct"] = staged_w
            info["qty"] = staged_qty
            info["delta_qty"] = staged_qty
            info["_staged_entry"] = True
            info["_original_target_pct"] = round(original_w, 4)
            info["_staged_fraction"] = fraction
            info["_staged_fraction_reason"] = fraction_reason
            reason = str(info.get("one_sentence_reason") or "")
            if reason and "starter" not in reason.lower():
                info["one_sentence_reason"] = (
                    f"{reason} Starter entry is staged at {fraction:.0%} of target pending continuation."
                )
            target_weights[sym] = staged_w
            per_symbol[sym] = info
            cash_target_pct = round(cash_target_pct + freed_w, 4)
            adjustments.append({
                "symbol": sym,
                "original_target_pct": round(original_w, 4),
                "staged_target_pct": staged_w,
                "staged_fraction": fraction,
                "cash_target_added_pct": round(freed_w, 4),
                "original_qty": original_qty,
                "staged_qty": staged_qty,
                "staged_fraction_reason": fraction_reason,
                "opportunity_score": opp_score,
                "confidence": confidence,
                "tape_severity": tape_severity,
            })

        return target_weights, per_symbol, cash_target_pct, adjustments

    def _apply_new_entry_execution_gates(
        self,
        result: dict[str, Any],
        target_weights: dict[str, float],
        per_symbol: dict[str, dict[str, Any]],
        held_symbols: set[str],
        pool_meta: dict[str, dict[str, Any]],
        portfolio: dict[str, Any],
        equity: float,
    ) -> tuple[dict[str, float], dict[str, dict[str, Any]], float, list[dict[str, Any]]]:
        """Remove fresh entries that fail hard pre-execution gates.

        The selector remains the authority on the desired final book. These are
        execution guardrails: no gap-only fresh buys, no earnings-blackout fresh
        buys, no sub-minimum entries, and no missing broker-ready sizing. Failed
        target weight is moved to cash so the verifier does not re-buy it in the
        same scan.
        """
        cash_target_pct = float(result.get("execution_cash_target_pct",
                                           result.get("cash_target_pct", 0)) or 0)
        selected = set(str(s) for s in (result.get("selected_positions") or []))
        blocked: list[dict[str, Any]] = []

        def _block(sym: str, reason: str, **extra: Any) -> None:
            nonlocal cash_target_pct
            failed_w = float(target_weights.pop(sym, 0.0) or 0.0)
            if failed_w > 0:
                cash_target_pct = round(cash_target_pct + failed_w, 4)
            info = dict(per_symbol.get(sym) or {})
            info["target_pct"] = 0.0
            info["qty"] = 0
            info["delta_qty"] = 0
            info["action"] = "PASS"
            info["_execution_target_removed"] = reason
            per_symbol[sym] = info
            blocked.append({
                "symbol": sym,
                "reason": reason,
                "removed_target_pct": round(failed_w, 4),
                **extra,
            })

        for sym in sorted(selected - held_symbols):
            if "/" in sym:
                continue
            info = per_symbol.get(sym) or {}
            target_pct = float(target_weights.get(sym, 0.0) or 0.0)
            if target_pct <= 0:
                continue
            target_notional = round(target_pct * equity, 2)
            min_entry_pct = float(self.cfg.get(
                "selector", "min_new_entry_pct",
                default=float(self.cfg.get("selector", "min_per_position_pct", default=0.04) or 0.04),
            ) or 0.04)
            if target_pct < min_entry_pct:
                _block(sym, "below_min_new_entry_pct",
                       requested_target_pct=round(target_pct, 4),
                       min_new_entry_pct=min_entry_pct,
                       requested_delta_notional=target_notional)
                continue
            min_trade = float(self.cfg.get("risk", "min_trade_usd", default=500))
            if target_notional < min_trade:
                _block(sym, "below_min_trade",
                       requested_delta_notional=target_notional,
                       min_trade_usd=min_trade)
                continue
            momentum_block = self._new_entry_momentum_gate(sym, pool_meta)
            if momentum_block:
                _block(sym, "failed_continuation_gate",
                       requested_delta_notional=target_notional,
                       momentum_gate=momentum_block)
                continue
            confidence = self._selector_entry_confidence(info)
            earnings_block = self._selector_entry_earnings_block(
                sym, confidence, portfolio.get("earnings_map", {}) or {},
            )
            if earnings_block:
                _block(sym, "earnings_blackout",
                       requested_delta_notional=target_notional,
                       earnings=earnings_block)
                continue
            try:
                qty = float(info.get("qty") or 0)
                entry = float(info.get("entry_price") or 0)
                delta_qty = float(info.get("delta_qty") or 0)
            except (TypeError, ValueError):
                qty = entry = delta_qty = 0.0
            if qty <= 0 or entry <= 0 or delta_qty <= 0:
                _block(sym, "missing_ai_sizing_params",
                       requested_delta_notional=target_notional,
                       ai_inputs={
                           "qty": info.get("qty"),
                           "entry_price": info.get("entry_price"),
                           "delta_qty": info.get("delta_qty"),
                       })

        if blocked:
            result["execution_target_weights"] = target_weights
            result["execution_per_symbol"] = per_symbol
            result["execution_cash_target_pct"] = cash_target_pct
        return target_weights, per_symbol, cash_target_pct, blocked

    def _build_unified_portfolio_plan_audit(
        self,
        result: dict[str, Any],
        target_weights: dict[str, float],
        per_symbol: dict[str, dict[str, Any]],
        pool_meta: dict[str, dict[str, Any]],
        portfolio: dict[str, Any],
        equity: float,
        cash_usd: float,
        spy_target_pct: float,
        cash_target_pct: float,
        blocked_new_entries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create one human-readable table for the final target portfolio.

        This is the audit artifact the user asked for: current portfolio,
        exits, entries, holds, target book, and every stock's reason in one
        coherent object before the rebalance executor acts.
        """
        holdings = {
            p.symbol: p
            for p in portfolio.get("holdings", [])
            if not self._is_cash_proxy(p.symbol)
        }
        all_symbols = sorted(set(pool_meta.keys()) | set(per_symbol.keys()) | set(holdings.keys()))
        blocked_by_sym = {b.get("symbol"): b for b in blocked_new_entries}
        rows: list[dict[str, Any]] = []
        final_positions: list[dict[str, Any]] = []
        movement: list[dict[str, Any]] = []

        def _float(v: Any, default: float = 0.0) -> float:
            try:
                return float(v)
            except (TypeError, ValueError):
                return default

        for sym in all_symbols:
            info = per_symbol.get(sym) or {}
            meta = pool_meta.get(sym) or {}
            p = holdings.get(sym)
            current_qty = _float(meta.get("current_qty"), 0.0)
            if p is not None and current_qty <= 0:
                current_qty = abs(_float(getattr(p, "qty", 0), 0.0))
            current_notional = abs(_float(getattr(p, "market_value", 0), 0.0)) if p is not None else 0.0
            current_price = _float(info.get("entry_price"), 0.0)
            if current_price <= 0 and p is not None:
                current_price = _float(getattr(p, "current_price", 0), 0.0)
            if current_price <= 0:
                chart = meta.get("intraday_chart") or {}
                current_price = _float(chart.get("current_price"), 0.0)
            target_pct = _float(target_weights.get(sym, info.get("target_pct", 0.0)), 0.0)
            target_qty = _float(info.get("qty"), 0.0)
            delta_qty = _float(info.get("delta_qty"), 0.0)
            target_notional = target_pct * equity
            if target_qty > 0 and current_price > 0:
                target_notional = target_qty * current_price
            delta_notional = target_notional - current_notional
            action = str(info.get("action") or "").upper()
            if sym in blocked_by_sym:
                final_action = "BLOCKED_ENTRY"
            elif current_qty <= 0 and target_pct > 0:
                final_action = "ENTER"
            elif current_qty > 0 and target_pct <= 0:
                final_action = "EXIT"
            elif current_qty > 0 and delta_qty > 0:
                final_action = "INCREASE"
            elif current_qty > 0 and delta_qty < 0:
                final_action = "REDUCE"
            elif current_qty > 0:
                final_action = "HOLD"
            else:
                final_action = "PASS"

            row = {
                "symbol": sym,
                "final_action": final_action,
                "selector_action": action,
                "currently_held": bool(meta.get("currently_held", p is not None)),
                "current_qty": round(current_qty, 6),
                "current_price": round(current_price, 4) if current_price > 0 else None,
                "current_notional_usd": round(current_notional, 2),
                "current_weight_pct": round(current_notional / equity, 4) if equity else 0.0,
                "target_pct": round(target_pct, 4),
                "target_qty": round(target_qty, 6),
                "target_notional_usd": round(target_notional, 2),
                "delta_qty": round(delta_qty, 6),
                "delta_usd": round(delta_notional, 2),
                "opportunity_score": _float(info.get("opportunity_score"), 0.0),
                "remaining_upside_score": _float(info.get("remaining_upside_score"), 0.0),
                "candidate_priority_score": _float(meta.get("candidate_priority_score"), 0.0),
                "momentum_grade": (meta.get("momentum_profile") or {}).get("grade"),
                "peer_group": meta.get("peer_group"),
                "peer_rank": meta.get("peer_rank"),
                "peer_leader": meta.get("peer_leader"),
                "peer_pressure": meta.get("peer_pressure"),
                "sector_rank": meta.get("sector_rank"),
                "sector_leader": meta.get("sector_leader"),
                "reason": info.get("one_sentence_reason"),
            }
            if sym in blocked_by_sym:
                row["blocked_entry"] = blocked_by_sym[sym]
            rows.append(row)
            if target_pct > 0:
                final_positions.append({
                    "symbol": sym,
                    "target_pct": round(target_pct, 4),
                    "target_qty": round(target_qty, 6),
                    "target_notional_usd": round(target_notional, 2),
                    "opportunity_score": row["opportunity_score"],
                    "reason": row["reason"],
                })
            if final_action in {"ENTER", "INCREASE", "REDUCE", "EXIT", "BLOCKED_ENTRY"}:
                movement.append({
                    "symbol": sym,
                    "action": final_action,
                    "delta_usd": row["delta_usd"],
                    "delta_qty": row["delta_qty"],
                    "reason": row["reason"],
                })

        final_positions.sort(key=lambda r: float(r.get("target_pct", 0) or 0), reverse=True)
        return {
            "portfolio_thesis": result.get("portfolio_thesis"),
            "current_portfolio": {
                "equity": round(equity, 2),
                "cash_usd": round(cash_usd, 2),
                "cash_pct": round(cash_usd / equity, 4) if equity else 0.0,
                "positions": [
                    r for r in rows
                    if r["currently_held"] and r["current_qty"] > 0
                ],
            },
            "final_portfolio": {
                "positions": final_positions,
                "spy_target_pct": round(float(spy_target_pct or 0), 4),
                "cash_target_pct": round(float(cash_target_pct or 0), 4),
                "cash_target_usd": round(float(cash_target_pct or 0) * equity, 2),
            },
            "all_symbol_decisions": rows,
            "capital_movement_plan": movement,
            "blocked_new_entries": blocked_new_entries,
            "selected_positions": result.get("selected_positions", []),
            "rotation_plan": result.get("rotation_plan") or {},
        }

    def _build_selector_context(
        self,
        candidates: list[Candidate],
        portfolio: dict[str, Any],
        macro: MacroSignal,
        equity: float,
        bearish_halt: bool,
        dry_run: bool,
        allow_floor_breach: bool,
        earnings_close_symbols: set[str] | list[str] | None = None,
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        """Assemble the selector input context.

        Reuses ``_build_arbiter_context`` for the shared book/risk/macro shell,
        then replaces ``positions`` + ``scan_candidates_summary`` with a unified
        ``candidate_pool`` array where every entry has the same schema and a
        ``currently_held`` flag.

        Returns ``(context, pool_meta)`` — ``pool_meta`` maps symbol to
        ``{"currently_held": bool, "sector": str}`` for the
        validator to enforce anti-stagnation server-side.
        """
        holdings = portfolio.get("holdings", [])
        tech_map = portfolio.get("tech_map", {}) or {}
        sent_map = portfolio.get("sent_map", {}) or {}
        numeric = portfolio.get("numeric", {}) or {}
        earnings_map = portfolio.get("earnings_map", {}) or {}

        # Base context from the arbiter helper (gives us risk_profile,
        # trading_rules, execution_constraints, system_state, macro, spy_block,
        # current_allocation, recent_decisions, cash, equity).
        base = self._build_arbiter_context(
            holdings=holdings,
            tech_map=tech_map,
            sent_map=sent_map,
            numeric=numeric,
            earnings_map=earnings_map,
            macro=macro,
            equity=equity,
            bearish_halt=bearish_halt,
            dry_run=dry_run,
            scan_candidates=None,
            earnings_close_symbols=earnings_close_symbols,
        )

        # Override trading_rules with selector-specific guidance (no incumbent
        # bias, forced rotation, exhaustion penalty, anti-stagnation).
        base["trading_rules"] = [
            "You are the SOLE authority on which 3-6 positions the bot holds.",
            "Optimize for REMAINING upside between NOW and the NEXT SCAN.",
            "currently_held flag carries ZERO weight. P&L is sunk and irrelevant.",
            (
                f"Fresh entries inside {float(self.cfg.get('selector', 'fresh_exit_cooldown_minutes', default=120) or 120):.0f} "
                "minutes get a conservative first read: reduce/exit only when the entry thesis is gone, "
                "the position is materially underperforming, protective risk changed, or your confidence is very high."
            ),
            "Fresh BUYs require live continuation; gap-only, flat-after-open names should PASS.",
            (
                f"Do not open novelty starter positions below "
                f"{float(self.cfg.get('selector', 'min_new_entry_pct', default=0.04) or 0.04):.0%} "
                "of equity after staging; PASS them until the setup deserves real capital."
            ),
            "Use momentum_profile, VWAP, 5-minute EMA state, recent slope, and volume trend.",
            "Apply exhaustion penalty to symbols near day high with fading volume.",
            "Force rotation: held symbols not in selected_positions MUST EXIT.",
            "When any new candidate is within 5 score points of your weakest "
            "selected, you MUST include at least one new candidate.",
            f"New entries should start near {float(self.cfg.get('selector', 'new_entry_initial_fraction', default=0.70) or 0.70):.0%} "
            "of the desired final target and scale on later scans if continuation persists.",
            "Score-weighted sizing: weight ∝ opportunity_score^k where k = "
            "system_state.concentration_exponent. Top-conviction names get a "
            "real majority share — equal-ish weights across 5-6 names is the "
            "failure pattern this rule corrects. If your top-3 weights span "
            "less than system_state.min_top3_weight_ratio (max/min), drop the "
            "weakest and reallocate.",
            "Sector caps and per-position caps are HARD constraints.",
            (
                "Phase A intraday tape filter: BUY/INCREASE actions REQUIRE "
                "opportunity_score >= max(system_state.buy_min_opportunity_score, "
                "system_state.tape_state.min_opportunity_score_floor). The tape "
                "floor scales with how bad SPY is doing intraday — a -1% SPY "
                "session may push the floor to ~85. There is NO hard halt: any "
                "number of names that clear the floor are allowed."
            ),
            (
                "Phase B risk-off concentration: when system_state.risk_off_active "
                "is true, return at most system_state.max_positions_this_scan "
                "selected positions and use the higher concentration_exponent "
                "the system_state already provides. Capital not deployed to "
                "selected names may stay in cash only when SPY/tape is bearish; "
                "otherwise assign it to spy_target_pct."
            ),
            (
                "Phase C quality gates: a BUY MUST also satisfy "
                "distance_from_high_pct >= buy_max_distance_from_high_pct "
                "OR have rising volume — chasing names within 4% of intraday "
                "high with fading/flat volume is a hard PASS."
            ),
            (
                "Phase D selector-rotation cooldown: symbols in "
                "system_state.recent_selector_rotations may NOT be re-bought "
                "unless your opportunity_score >= "
                "selector_rotation_rebuy_min_score AND beats the prior exit "
                "score by >= selector_rotation_rebuy_min_score_delta. Otherwise "
                "PASS — do not round-trip the same symbol within the cooldown."
            ),
            (
                "Phase E late-day freeze: when system_state.no_new_entries=true "
                "(within minutes_to_close of the bell), NO BUY or INCREASE "
                "actions. HOLD/EXIT/REDUCE/PASS only. There is not enough "
                "runway for a fresh entry."
            ),
            (
                f"DIVERSIFICATION CAP (HARD): no more than "
                f"{int(self.cfg.get('diversification', 'max_per_gics_sector', default=3) or 3)} "
                f"selected positions may share the same GICS sector, and no more than "
                f"{int(self.cfg.get('diversification', 'max_per_theme', default=3) or 3)} "
                f"may share the same theme_bucket. Theme weight cap: "
                f"{float(self.cfg.get('diversification', 'max_theme_weight_pct', default=0.50) or 0.50):.0%}. "
                f"The executor will VETO any plan that violates these caps."
            ),
            (
                "Cash-vs-SPY decision: explicitly decide whether excess idle "
                "money is better in true cash or SPY. Use cash_target_pct above "
                "the reserve only when SPY/tape is bearish or cash is clearly "
                "safer than market exposure; otherwise use spy_target_pct so "
                "the account participates in constructive SPY tape."
            ),
        ]

        # Drop recent_decisions: it's anti-thrash context for the legacy
        # rebalance arbiter and grows unboundedly with journal size. The
        # selector doesn't need decision history (it ranks fresh every scan).
        # Keeping it pushed input tokens past the 30k/min org rate limit.
        base.pop("recent_decisions", None)

        # Mark whether floor-breach (0-2 positions allowed) is active this scan.
        ss = base.setdefault("system_state", {})
        ss["allow_floor_breach"] = bool(allow_floor_breach)
        ss["intraday_new_entries_allowed"] = True
        # Surface recent exit-arbiter actions (cooldown window, default 60 min)
        # so the selector cannot silently reverse a just-applied EXIT/REDUCE.
        recent_exits = self._recent_exit_actions_for_selector()
        if recent_exits:
            ss["recent_exit_actions"] = recent_exits
            ss["recent_exit_rebuy_min_confidence"] = float(
                self.cfg.get(
                    "exit_arbiter", "rebuy_min_confidence", default=0.80
                ) or 0.80
            )

        # Phase A (2026-05-07): proportional intraday SPY tape filter. Computed
        # from SPY 5-min bars; raises the BUY opportunity_score floor smoothly
        # with how bad the tape is, never hard-blocks. Independent of the
        # daily macro halt.
        ss["tape_state"] = self._compute_tape_state_for_selector()
        # Phase B (2026-05-07): concentration-weighted sizing knobs.
        risk_off_now = (ss["tape_state"].get("severity_label") in ("mild_risk_off", "strong_risk_off"))
        ss["risk_off_active"] = bool(risk_off_now)
        if risk_off_now:
            ss["concentration_exponent"] = float(
                self.cfg.get("selector", "concentration_exponent_risk_off", default=5.0) or 5.0
            )
            ss["max_positions_this_scan"] = int(
                self.cfg.get("selector", "max_positions_risk_off", default=3) or 3
            )
        else:
            ss["concentration_exponent"] = float(
                self.cfg.get("selector", "concentration_exponent", default=3.0) or 3.0
            )
            ss["max_positions_this_scan"] = int(
                self.cfg.get("selector", "max_positions", default=6) or 6
            )
        ss["min_top3_weight_ratio"] = float(
            self.cfg.get("selector", "min_top3_weight_ratio", default=1.5) or 1.5
        )
        # Phase C (2026-05-07): hard quality gates above BUY threshold.
        ss["buy_min_opportunity_score"] = float(
            self.cfg.get("selector", "buy_min_opportunity_score", default=70) or 70
        )
        ss["buy_max_distance_from_high_pct"] = float(
            self.cfg.get("selector", "buy_max_distance_from_high_pct", default=0.04) or 0.04
        )
        # Phase C.1 (2026-05-11): dynamic gate softening. Both the opp-score
        # floor and the distance-from-high floor scale with (a) the pool's
        # top opportunity score and (b) tape_badness ∈ [0,1]. In a favorable
        # tape with a top score of 78, a 70-flat floor leaves a 8-pt working
        # band — too tight, and "don't chase the high" filters out leaders
        # for being leaders. See ai_pipeline._validate_selector_output.
        ss["buy_floor_dynamic_enabled"] = bool(
            self.cfg.get("selector", "buy_floor_dynamic_enabled", default=True)
        )
        ss["buy_floor_dynamic_min"] = float(
            self.cfg.get("selector", "buy_floor_dynamic_min", default=55) or 55
        )
        ss["buy_floor_dynamic_delta_favorable"] = float(
            self.cfg.get("selector", "buy_floor_dynamic_delta_favorable", default=15) or 15
        )
        ss["buy_floor_dynamic_delta_severe"] = float(
            self.cfg.get("selector", "buy_floor_dynamic_delta_severe", default=5) or 5
        )
        ss["buy_distance_dynamic_min_scale"] = float(
            self.cfg.get("selector", "buy_distance_dynamic_min_scale", default=0.25) or 0.25
        )
        ss["buy_distance_confidence_bypass"] = float(
            self.cfg.get("selector", "buy_distance_confidence_bypass", default=0.65) or 0.65
        )
        # Phase C.1 (2026-05-11): dynamic rotation-cooldown floor.
        ss["rotation_rebuy_dynamic_enabled"] = bool(
            self.cfg.get("selector", "rotation_rebuy_dynamic_enabled", default=True)
        )
        ss["rotation_rebuy_dynamic_min"] = float(
            self.cfg.get("selector", "rotation_rebuy_dynamic_min", default=70) or 70
        )
        ss["rotation_rebuy_dynamic_delta_favorable"] = float(
            self.cfg.get("selector", "rotation_rebuy_dynamic_delta_favorable", default=8) or 8
        )
        ss["rotation_rebuy_dynamic_delta_severe"] = float(
            self.cfg.get("selector", "rotation_rebuy_dynamic_delta_severe", default=2) or 2
        )
        ss["anti_stagnation_min_top_score"] = float(
            self.cfg.get("selector", "anti_stagnation_min_top_score", default=70) or 70
        )
        # Phase D (2026-05-07): selector-source rotation cooldown — surface
        # selector-driven exits so the selector can't immediately reverse them.
        recent_rotations = self._recent_selector_rotations_for_selector()
        if recent_rotations:
            ss["recent_selector_rotations"] = recent_rotations
            ss["selector_rotation_rebuy_min_score"] = float(
                self.cfg.get("selector", "selector_rotation_rebuy_min_score", default=90) or 90
            )
            ss["selector_rotation_rebuy_min_score_delta"] = float(
                self.cfg.get(
                    "selector", "selector_rotation_rebuy_min_score_delta", default=10
                ) or 10
            )
        # Phase E (2026-05-07): late-day entry freeze. Compute minutes to close
        # so the selector and validator can block fresh BUYs in the last N min.
        mins_to_close, no_new_entries = self._minutes_to_close_with_freeze_flag()
        if mins_to_close is not None:
            ss["minutes_to_close"] = mins_to_close
        ss["no_new_entries"] = bool(no_new_entries)
        ss["no_new_entries_minutes_before_close"] = int(
            self.cfg.get("selector", "no_new_entries_minutes_before_close", default=30) or 30
        )

        # Build unified candidate_pool. Held positions get full block (qty,
        # weight, pnl); new candidates get zeros for those fields plus discovery
        # metadata.
        held_blocks_by_sym: dict[str, dict[str, Any]] = {
            p["symbol"]: p for p in (base.get("positions") or [])
        }
        pool_meta: dict[str, dict[str, Any]] = {}
        unified_pool: list[dict[str, Any]] = []
        sector_to_theme = sector_guard._build_sector_to_theme(self.cfg)
        symbol_overrides = sector_guard._symbol_overrides(self.cfg)
        all_pool_symbols = sorted({
            c.symbol for c in candidates
            if c.symbol and "/" not in c.symbol and not self._is_cash_proxy(c.symbol)
        } | {"SPY"})
        selector_intraday = portfolio.get("intraday_bars")
        selector_daily = None
        try:
            selector_intraday = self._fetch_intraday(all_pool_symbols, minutes=5)
        except Exception as e:
            log.info("[selector] full-pool intraday fetch failed: %s", e)
        try:
            selector_daily = self.client.get_stock_bars(all_pool_symbols, lookback_days=30)
        except Exception as e:
            log.info("[selector] full-pool daily context fetch failed: %s", e)

        for cand in candidates:
            sym = cand.symbol
            currently_held = bool(cand.is_held)
            block: dict[str, Any] = held_blocks_by_sym.get(sym, {}).copy()
            einfo = earnings_map.get(sym)
            chart = self._intraday_chart_for(selector_intraday, sym, selector_daily)
            momentum_profile = self._momentum_profile(chart)
            five_day_change = self._five_day_change_pct(selector_daily, sym)
            chart_price = (chart or {}).get("current_price")
            if not block:
                # Build a minimal block for non-held candidates.
                tech = tech_map.get(sym)
                sent = sent_map.get(sym)
                num = numeric.get(sym)
                block = {
                    "symbol": sym,
                    "side": "long",  # default — selector decides direction via action
                    "qty": 0.0,
                    "avg_entry_price": 0.0,
                    "current_price": round(float(chart_price or cand.price or getattr(tech, "price", 0) or 0), 4),
                    "market_value_usd": 0.0,
                    "abs_market_value_usd": 0.0,
                    "current_weight_pct": 0.0,
                    "unrealized_pl_usd": 0.0,
                    "unrealized_plpc": 0.0,
                    "sector": cand.sector or "Other",
                    "tech_score": (round(float(tech.score), 3) if tech else None),
                    "rsi": (round(float(tech.rsi), 1) if tech and tech.rsi is not None else None),
                    "atr": (round(float(tech.atr), 3) if tech and tech.atr is not None else None),
                    "sent_score": (round(float(sent.score), 3) if sent else None),
                    "numeric_confidence": (round(float(num.confidence), 3) if num else None),
                    "numeric_combined_score": (round(float(num.combined_score), 3) if num else None),
                    "numeric_action": (num.action if num else None),
                    # intraday_chart fields are surfaced top-level below
                    # (price_vs_vwap_pct, distance_from_high_pct, etc.) so we
                    # don't embed the raw chart dict here — that would duplicate
                    # ~640 bytes per candidate and inflated input tokens 50x
                    # with no extra signal for the selector.
                    "momentum_profile": momentum_profile,
                    "earnings_days_until": (einfo.days_until if einfo else None),
                    "earnings_next_date": (einfo.next_date if einfo else None),
                }
            # Phase 7 (2026-05-07): surface earnings research evidence so the
            # selector can size & confidence-weight pre-earnings entries.
            if einfo and einfo.days_until is not None and 0 <= einfo.days_until <= self.entry_earnings_blackout_days:
                try:
                    from src.earnings import compute_earnings_research_score
                    ttl = float(self.cfg.get("earnings", "research_cache_ttl_hours", default=12) or 12)
                    research = compute_earnings_research_score(sym, ttl_hours=ttl)
                    block["earnings_research_score"] = research.get("score")
                    block["earnings_research_components"] = research.get("components")
                    block["pre_earnings_size_multiplier"] = float(
                        self.cfg.get("earnings", "pre_earnings_size_multiplier", default=0.75) or 0.75
                    )
                except Exception as e:
                    log.debug("earnings research surface for %s failed: %s", sym, e)
            else:
                # Held blocks come from _portfolio_signals which DOES embed
                # intraday_chart. Drop it here to keep the selector context
                # lean — the same signals are surfaced top-level below.
                block.pop("intraday_chart", None)
                block["momentum_profile"] = momentum_profile
                if chart_price:
                    block["current_price"] = round(float(chart_price), 4)
            lifecycle = self._position_lifecycle_context(sym) if currently_held else {}
            if lifecycle:
                block["position_lifecycle"] = lifecycle
            block["currently_held"] = currently_held
            try:
                current_qty = float(block.get("qty", 0) or 0) if currently_held else 0.0
            except (TypeError, ValueError):
                current_qty = 0.0
            block["current_qty"] = current_qty
            block["discovery_sources"] = list(cand.sources)
            block["discovery_priority_score"] = round(
                float(getattr(cand, "discovery_priority_score", 0.0) or 0.0), 2
            )
            block["discovery_priority_reasons"] = list(
                getattr(cand, "discovery_priority_reasons", []) or []
            )
            block["intraday_change_pct"] = (
                (chart or {}).get("intraday_change_pct")
                if chart and (chart or {}).get("intraday_change_pct") is not None
                else round(float(cand.change_pct or 0.0), 4)
            )
            block["gap_from_prior_close_pct"] = (
                (chart or {}).get("gap_from_prior_close_pct") if chart else None
            )
            block["price_vs_vwap_pct"] = (
                (chart or {}).get("price_vs_vwap_pct") if chart else None
            )
            block["ema_state"] = (chart or {}).get("ema_state") if chart else None
            block["distance_from_high_pct"] = (
                (chart or {}).get("distance_from_high_pct") if chart else None
            )
            block["distance_from_low_pct"] = (
                (chart or {}).get("distance_from_low_pct") if chart else None
            )
            block["recent_trend"] = (chart or {}).get("recent_trend") if chart else None
            block["recent_slope_pct"] = (chart or {}).get("recent_slope_pct") if chart else None
            block["volume_trend"] = (chart or {}).get("volume_trend") if chart else None
            block["classification"] = (chart or {}).get("classification") if chart else None
            block["five_day_change_pct"] = (
                round(five_day_change, 4) if five_day_change is not None else None
            )
            block["twenty_day_volume_ratio"] = (
                (chart or {}).get("twenty_day_volume_ratio") if chart else None
            )
            theme = sector_guard.theme_bucket_for(
                cand.sector or "", sector_to_theme, sym, symbol_overrides
            )
            block["theme_bucket"] = theme
            unified_pool.append(block)
            pool_meta[sym] = {
                "currently_held": currently_held,
                "sector": cand.sector or "Other",
                "theme_bucket": theme,
                "current_qty": current_qty,
                "momentum_profile": momentum_profile,
                "intraday_chart": chart,
                "position_lifecycle": lifecycle,
            }
            # Phase 6 (2026-05-07): liquidity-aware concentration cap inputs.
            # is_illiquid drives selector validator clamping AND surfaces in
            # the candidate block so the selector can self-cap. Daily bars
            # cache is shared with technicals so ADV is essentially free
            # after the first call.
            try:
                price_thresh = float(self.cfg.get("risk", "illiquid_price_threshold", default=20.0) or 20.0)
                adv_thresh = float(self.cfg.get("risk", "illiquid_adv_threshold", default=50_000_000) or 50_000_000)
                cand_price = float(getattr(cand, "price", 0) or 0)
                is_illiq_price = cand_price > 0 and cand_price < price_thresh
                adv_value: float | None = None
                if not is_illiq_price and adv_thresh > 0:
                    try:
                        mds_local = get_market_data(self.cfg)
                        adv_value = mds_local.get_avg_dollar_volume(sym, days=20)
                    except Exception:
                        adv_value = None
                else:
                    try:
                        adv_value = get_market_data(self.cfg).get_avg_dollar_volume(sym, days=20)
                    except Exception:
                        adv_value = None
                is_illiq_adv = adv_value is not None and adv_value < adv_thresh
                is_illiq = bool(is_illiq_price or is_illiq_adv)
                pool_meta[sym]["price"] = cand_price or None
                pool_meta[sym]["avg_dollar_volume_20d"] = adv_value
                pool_meta[sym]["is_illiquid"] = is_illiq
                if is_illiq:
                    block["is_illiquid"] = True
                    block["illiquid_max_position_pct"] = float(
                        self.cfg.get("risk", "illiquid_max_position_pct", default=0.08) or 0.08
                    )
            except Exception as e:
                log.debug("[selector] illiquid-check failed for %s: %s", sym, e)

        annotate_candidate_leadership(
            unified_pool,
            self.cfg.get("universe", "peer_groups", default={}) or {},
            peer_gap_threshold=float(
                self.cfg.get("selector", "peer_outperformance_threshold", default=10) or 10
            ),
        )
        for block in unified_pool:
            sym = block.get("symbol")
            if not sym or sym not in pool_meta:
                continue
            for key in (
                "candidate_priority_score",
                "candidate_priority_reasons",
                "peer_group",
                "peer_rank",
                "peer_group_size",
                "peer_lone",
                "peer_leader",
                "peer_leader_score",
                "peer_relative_score",
                "peer_percentile",
                "peer_pressure",
                "peer_comparison_summary",
                "sector_rank",
                "sector_group_size",
                "sector_lone",
                "sector_leader",
                "sector_leader_score",
                "sector_relative_score",
                "sector_percentile",
                "sector_comparison_summary",
                "theme_rank",
                "theme_group_size",
                "theme_lone",
                "theme_leader",
                "theme_leader_score",
                "theme_relative_score",
                "theme_percentile",
                "theme_comparison_summary",
            ):
                if key in block:
                    pool_meta[sym][key] = block.get(key)

        # Phase 0b: slim the per-candidate payload before sending to the
        # selector. Today's bloat audit (2026-05-05) showed 28K input tokens
        # for a 50-symbol pool, with ~7KB of *prose narrative* duplicating
        # numeric `*_rank` / `*_leader` fields. The selector needs the
        # signal, not three sentences saying the same thing.
        # See EXECUTION_PLAN.md Phase 0b.
        _slim_selector_pool_blocks(unified_pool)

        base["candidate_pool"] = unified_pool
        base.pop("positions", None)
        base.pop("scan_candidates_summary", None)
        return base, pool_meta

    def _build_selector_safety_noop_result(
        self,
        *,
        reason: str,
        ctx: dict[str, Any],
        pool_meta: dict[str, dict[str, Any]],
        portfolio: dict[str, Any],
        account: Any,
        equity: float,
        consecutive_failures: int,
    ) -> dict[str, Any]:
        """Return a broker-neutral selector result that makes no selector trades.

        This is the final safety net when the AI selector is unavailable,
        truncated, or invalid after all retries. It does not originate trades;
        it freezes the current non-SPY book at current quantities and marks
        every fresh candidate PASS so downstream reporting still completes.
        """
        holdings = {
            str(getattr(p, "symbol", "") or ""): p
            for p in portfolio.get("holdings", [])
            if getattr(p, "symbol", None)
            and "/" not in str(getattr(p, "symbol", ""))
            and not self._is_cash_proxy(str(getattr(p, "symbol", "")))
        }
        candidate_pool = ctx.get("candidate_pool") or []
        pool_symbols = {
            str(row.get("symbol") or "")
            for row in candidate_pool
            if isinstance(row, dict) and row.get("symbol")
        }

        per_symbol: dict[str, dict[str, Any]] = {}
        target_weights: dict[str, float] = {}
        selected: list[str] = []

        def _float(v: Any, default: float = 0.0) -> float:
            try:
                return float(v)
            except (TypeError, ValueError):
                return default

        for sym in sorted(pool_symbols | set(holdings.keys())):
            if not sym or self._is_cash_proxy(sym) or "/" in sym:
                continue
            p = holdings.get(sym)
            meta = pool_meta.get(sym) or {}
            if p is not None:
                qty = abs(_float(getattr(p, "qty", 0), 0.0))
                notional = abs(_float(getattr(p, "market_value", 0), 0.0))
                price = (notional / qty) if qty > 0 and notional > 0 else _float(
                    getattr(p, "current_price", 0), 0.0
                )
                target_pct = round((notional / equity) if equity > 0 else 0.0, 6)
                if qty > 0 and target_pct > 0:
                    selected.append(sym)
                    target_weights[sym] = target_pct
                per_symbol[sym] = {
                    "target_pct": target_pct,
                    "qty": qty,
                    "delta_qty": 0,
                    "entry_price": round(price, 4) if price > 0 else 0,
                    "stop_loss": None,
                    "take_profit": None,
                    "action": "HOLD",
                    "confidence": 0.0,
                    "opportunity_score": _float(meta.get("candidate_priority_score"), 0.0),
                    "one_sentence_reason": None,
                    "reason_code": "selector_safety_noop",
                }
                continue

            chart = meta.get("intraday_chart") if isinstance(meta, dict) else None
            price = _float((chart or {}).get("current_price"), 0.0)
            per_symbol[sym] = {
                "target_pct": 0.0,
                "qty": 0,
                "delta_qty": 0,
                "entry_price": round(price, 4) if price > 0 else 0,
                "stop_loss": None,
                "take_profit": None,
                "action": "PASS",
                "confidence": 0.0,
                "opportunity_score": _float(meta.get("candidate_priority_score"), 0.0),
                "one_sentence_reason": None,
                "reason_code": "selector_unavailable",
            }

        spy_target_pct = 0.0
        for p in portfolio.get("holdings", []) or []:
            sym = str(getattr(p, "symbol", "") or "")
            if self._is_cash_proxy(sym):
                spy_target_pct += (abs(_float(getattr(p, "market_value", 0), 0.0)) / equity) if equity > 0 else 0.0
        spy_target_pct = round(max(0.0, spy_target_pct), 6)
        current_cash_pct = (max(0.0, _float(getattr(account, "cash", 0), 0.0)) / equity) if equity > 0 else 0.0
        total = sum(target_weights.values()) + spy_target_pct + current_cash_pct
        if not (0.99 <= total <= 1.01):
            current_cash_pct = max(0.0, 1.0 - sum(target_weights.values()) - spy_target_pct)
        cash_target_pct = round(current_cash_pct, 6)

        return {
            "portfolio_thesis": (
                "Selector AI failed after retries; safety no-op is holding the current "
                "book and making no selector-driven allocation changes."
            ),
            "spy_target_pct": spy_target_pct,
            "cash_target_pct": cash_target_pct,
            "spy_decision": {
                "target_pct": spy_target_pct,
                "action": "HOLD",
                "opportunity_score": 0,
                "one_sentence_reason": "Safety no-op preserves the current SPY allocation because selector AI failed.",
            },
            "spy_vs_cash_reasoning": "Safety no-op preserves current cash and SPY exposure.",
            "selected_positions": selected,
            "target_weights": target_weights,
            "per_symbol": per_symbol,
            "exhaustion_penalty_applied": [],
            "rotation_plan": {"exited": [], "entered": [], "held": [
                {"symbol": sym, "reason": "selector_safety_noop"} for sym in selected
            ]},
            "capital_movement_plan": [],
            "risk_flags": [f"selector_safety_noop: {reason}"],
            "_selector_safety_noop": True,
            "_selector_failure_reason": reason,
            "_selector_consecutive_failures": consecutive_failures,
        }

    def _run_scan_with_selector(
        self,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Phase 4 cutover: unified-pool selector replaces the two-pipeline split.

        Flow:
          1. preamble: snapshot, macro, portfolio_signals
          2. urgent exits via exit-arbiter (kept)
          3. build unified candidate pool via discovery.py
          4. enrich + build selector context
          5. call portfolio-selector (Opus 4.7)
          6. validate; on failure → skip cycle (no trades), increment failure counter
          7. translate target_weights → compute_rebalance_plan → executor
          8. apply SPY target, run verifier
        """
        log.info("=== Starting scan via portfolio-selector (dry_run=%s) ===", dry_run)
        trade_learning_start = self._resolve_trade_learning("scan_start")
        self._last_arbiter_set_spy_target = False
        self._last_ai_target_weights = None
        self._last_ai_per_symbol = {}
        self._last_ai_spy_target_pct = None
        self._last_ai_cash_target_pct = None
        account, positions = self.client.get_snapshot(force_refresh=True, log_detail=True)
        equity = float(account.equity)
        log.info("Account: equity=$%.2f cash=$%.2f positions=%d",
                 equity, float(account.cash), len(positions))
        if not dry_run:
            # Safety net: ensure every open position has an active protective
            # stop in the order book before anything else runs. Catches the
            # HCAI failure mode (entry filled but stop rejected → naked
            # position) on subsequent scans.
            try:
                cov = self.executor.ensure_stop_coverage(source="scan_selector")
                if cov.get("added") or cov.get("errors"):
                    log_decision({"event": "stop_coverage", **cov})
            except Exception as e:
                log.error("[stop-coverage] safety net raised: %s", e)
            self._restore_cash_floor(equity)

        # Diversification audit at scan start: surfaces any theme cap
        # violation immediately, not after a sector_guard repair.
        self._audit_themes(positions, equity)

        macro = self.macro_brief()
        scan_type = self._detect_scan_type()

        portfolio = self._portfolio_signals(macro)
        # Phase 3: stash tech_map so the rebalance executor can read ATR per
        # symbol when constructing the protective stop.
        self._last_tech_map = portfolio.get("tech_map", {}) or {}
        exit_results: list[dict[str, Any]] = []
        exits = self.evaluate_exits(macro, portfolio=portfolio, scan_type=scan_type)
        earnings_exit_syms: set[str] = {
            sym for sym, reason in exits if "earnings" in reason.lower()
        }
        for sym, reason in exits:
            if dry_run:
                log.info("[DRY] Would close %s: %s", sym, reason)
                exit_results.append({"symbol": sym, "action": "close_dry", "reason": reason})
            else:
                res = self.executor.close_position(sym, reason=reason)
                exit_results.append({**res.to_dict(), "reason": reason})
                if res.ok:
                    self._clear_position_lifecycle(sym)
        if exit_results and not dry_run:
            exited_syms = {e.get("symbol") for e in exit_results
                           if e.get("status") != "rejected"}
            portfolio["holdings"] = [p for p in portfolio.get("holdings", [])
                                     if p.symbol not in exited_syms]

        halt_score = float(self.cfg.get("macro", "bearish_halt_score", default=-0.55))
        halt_on_spike = bool(self.cfg.get("macro", "bearish_halt_on_vix_spike", default=True))
        bearish_halt = macro.score <= halt_score or (halt_on_spike and macro.vix_regime == "spike")

        # 3. Build unified pool
        candidates, breakdown = self._build_unified_candidate_pool(portfolio)
        log_decision({
            "event": "selector_pool",
            "pool_size": len(candidates),
            "sources_breakdown": breakdown,
            "symbols": [c.symbol for c in candidates],
            "discovery_priority": [
                {
                    "symbol": c.symbol,
                    "score": round(float(getattr(c, "discovery_priority_score", 0) or 0), 2),
                    "sources": list(c.sources),
                    "reasons": list(getattr(c, "discovery_priority_reasons", []) or []),
                    "held": bool(c.is_held),
                }
                for c in sorted(
                    candidates,
                    key=lambda x: float(getattr(x, "discovery_priority_score", 0) or 0),
                    reverse=True,
                )
            ],
        })

        if not candidates:
            log.warning("[selector] discovery returned empty pool — skipping cycle")
            log_decision({"event": "selector_skipped", "reason": "empty_pool"})
            return {
                "status": "skipped_empty_pool",
                "equity": equity,
                "positions_count": len(positions),
                "exits": exit_results,
                "executions": [],
                "decisions": [],
            }

        portfolio = self._enrich_selector_candidates(portfolio, candidates, macro)

        # 4. Floor-breach decision (heuristic — top-score gate uses numeric pre-AI)
        top_numeric = max(
            (abs(float((portfolio.get("numeric", {}) or {}).get(c.symbol).combined_score))
             for c in candidates
             if (portfolio.get("numeric", {}) or {}).get(c.symbol) is not None),
            default=None,
        )
        allow_floor_breach = self._compute_floor_breach_flag(
            macro, top_score=top_numeric,
        )

        # 5. Build selector context
        ctx, pool_meta = self._build_selector_context(
            candidates=candidates,
            portfolio=portfolio,
            macro=macro,
            equity=equity,
            bearish_halt=bearish_halt,
            dry_run=dry_run,
            allow_floor_breach=allow_floor_breach,
            earnings_close_symbols=earnings_exit_syms,
        )
        held_symbols = [c.symbol for c in candidates if c.is_held]
        pool_symbols = [c.symbol for c in candidates]
        log_decision({
            "event": "selector_input",
            "context": ctx,
            "allow_floor_breach": allow_floor_breach,
        })
        dynamic_watchlist_update: dict[str, Any] | None = None

        # 6. Run selector
        # Phase 1 (2026-05-07): on max_tokens, retry with a smaller pool. The
        # callable preserves held candidates and re-ranks the rest by
        # discovery_priority_score (matches discovery._truncate_pool semantics).
        def _rebuild_with_pool_size(
            n: int,
        ) -> tuple[dict[str, Any], list[str], dict[str, dict[str, Any]]]:
            held_set = {c.symbol for c in candidates if c.is_held}
            held_cands = [c for c in candidates if c.symbol in held_set]
            rest = [c for c in candidates if c.symbol not in held_set]
            rest.sort(
                key=lambda c: (
                    -float(getattr(c, "discovery_priority_score", 0.0) or 0.0),
                    -abs(float(getattr(c, "change_pct", 0.0) or 0.0)),
                    c.symbol,
                )
            )
            keep = held_cands + rest[: max(0, n - len(held_cands))]
            log.info(
                "[selector] max_tokens fallback: rebuilding context with %d candidates "
                "(held=%d, fresh=%d)",
                len(keep), len(held_cands), len(keep) - len(held_cands),
            )
            new_ctx, new_pool_meta = self._build_selector_context(
                candidates=keep,
                portfolio=portfolio,
                macro=macro,
                equity=equity,
                bearish_halt=bearish_halt,
                dry_run=dry_run,
                allow_floor_breach=allow_floor_breach,
                earnings_close_symbols=earnings_exit_syms,
            )
            new_pool_symbols = [c.symbol for c in keep]
            return new_ctx, new_pool_symbols, new_pool_meta

        result = run_portfolio_selector(
            self.cfg, ctx, pool_symbols=pool_symbols, pool_meta=pool_meta,
            held_symbols=held_symbols, allow_floor_breach=allow_floor_breach,
            rebuild_with_pool_size=_rebuild_with_pool_size,
        )

        selector_safety_noop = False
        if result is None:
            try:
                dynamic_watchlist_update = update_dynamic_watchlist(
                    self.cfg,
                    ctx.get("candidate_pool") or [],
                )
                log_decision({
                    "event": "dynamic_watchlist_update",
                    "update": dynamic_watchlist_update,
                    "phase": "selector_failed",
                })
            except Exception as e:
                log.warning("[dynamic_watchlist] update failed after selector failure: %s", e)
            consec = self._handle_selector_failure(reason="ai_failure_or_validation")
            log_decision({"event": "selector_skipped", "reason": "ai_failure",
                          "consecutive_failures": consec})
            selector_safety_noop = True
            result = self._build_selector_safety_noop_result(
                reason="ai_failure_or_validation",
                ctx=ctx,
                pool_meta=pool_meta,
                portfolio=portfolio,
                account=account,
                equity=equity,
                consecutive_failures=consec,
            )
            log_decision({
                "event": "selector_safety_noop",
                "reason": "ai_failure_or_validation",
                "consecutive_failures": consec,
                "selected_positions": result.get("selected_positions", []),
                "target_weights": result.get("target_weights", {}),
            })
        else:
            self._reset_selector_failures()

        # Diversification veto: force deterministic compliance with per-sector
        # / per-theme caps before execution. This avoids another large Opus
        # call immediately after selector success, which can hit TPM limits.
        cash_proxy = self.cash_proxy_symbol if self.cash_proxy_enabled else None
        sector_guard_audit: dict[str, Any] | None = None
        if not selector_safety_noop:
            self._seed_cash_proxy_target_weight(result)
            guard = sector_guard.validate(
                target_weights=result.get("target_weights") or {},
                per_symbol=result.get("per_symbol") or {},
                pool_meta=pool_meta,
                cfg=self.cfg,
                cash_proxy_symbol=cash_proxy,
            )
            sector_guard_audit = guard.to_dict()
            if not guard.ok:
                log_decision({"event": "sector_guard_violation",
                              "violations": [v.to_dict() for v in guard.violations],
                              "audit": guard.to_dict()})
                forced = sector_guard.force_compliance(
                    target_weights=result.get("target_weights") or {},
                    per_symbol=result.get("per_symbol") or {},
                    violations=guard.violations,
                    cash_proxy_symbol=cash_proxy,
                )
                guard_after = sector_guard.validate(
                    target_weights=result.get("target_weights") or {},
                    per_symbol=result.get("per_symbol") or {},
                    pool_meta=pool_meta,
                    cfg=self.cfg,
                    cash_proxy_symbol=cash_proxy,
                )
                sector_guard_audit = guard_after.to_dict()
                log_decision({"event": "sector_guard_forced",
                              "forced_exits": forced,
                              "violations": [v.to_dict() for v in guard.violations],
                              "post_guard_ok": guard_after.ok,
                              "post_guard_violations": [
                                  v.to_dict() for v in guard_after.violations
                              ],
                              "pre_audit": guard.to_dict(),
                              "post_audit": guard_after.to_dict()})
                removed_selected = self._prune_zero_target_selected_positions(result)
                if removed_selected:
                    log_decision({
                        "event": "sector_guard_selected_positions_pruned",
                        "removed": removed_selected,
                        "selected_positions": result.get("selected_positions", []),
                    })
            self._sync_cash_proxy_target_from_weights(result)

        log_decision({"event": "selector_output", "result": result})

        selector_tape_state = ((ctx.get("system_state") or {}).get("tape_state") or {})
        result["_tape_state"] = selector_tape_state
        cash_policy_decision: dict[str, Any] | None = None
        if not selector_safety_noop:
            try:
                cash_policy_decision = build_selector_cash_policy_decision(
                    self.cfg,
                    result,
                    tape_state=selector_tape_state,
                    spy_target_pct=float(result.get("spy_target_pct", 0) or 0),
                    cash_target_pct=float(result.get("cash_target_pct", 0) or 0),
                    scan_ts=pd.Timestamp.utcnow().isoformat(),
                )
                if not dry_run:
                    save_cash_policy(self.cfg, cash_policy_decision)
                log_decision({
                    "event": "cash_policy_selector_decision",
                    "policy": cash_policy_decision,
                    "dry_run": dry_run,
                })
            except Exception as e:
                log.warning("[selector] cash policy persist failed: %s", e)
                cash_policy_decision = {"error": str(e)}

        # Phase D (2026-05-07): record every selector-driven EXIT so the next
        # scan cannot immediately reverse the rotation without clearing the
        # rebuy bar. We record on plan emission (before execution) — the
        # selector intent IS what the cooldown protects against repeating.
        try:
            for _sym, _info in (result.get("per_symbol") or {}).items():
                if not isinstance(_info, dict):
                    continue
                _action = str(_info.get("action", "") or "").upper()
                if _action != "EXIT":
                    continue
                # Only record when the symbol was actually held this scan —
                # PASS-as-EXIT is just "not selected", no cooldown needed.
                if not pool_meta.get(_sym, {}).get("currently_held", False):
                    continue
                self.record_selector_rotation_exit(
                    symbol=_sym,
                    opportunity_score=float(_info.get("opportunity_score", 0) or 0),
                    reason=str(_info.get("one_sentence_reason") or _info.get("exit_reason") or "")[:200],
                )
        except Exception as _e:
            log.warning("[selector] rotation cooldown recording failed: %s", _e)

        # Phase 0: candidate_rankings was dropped from the schema. Reconstitute
        # a ranking list from per_symbol so downstream journal consumers keep
        # working without forcing the model to emit a 50-row duplicate.
        per_symbol_dump = result.get("per_symbol") or {}
        rankings = sorted(
            (
                {
                    "symbol": sym,
                    "opportunity_score": info.get("opportunity_score", 0),
                    "action": info.get("action"),
                    "currently_held": bool(
                        pool_meta.get(sym, {}).get("currently_held", False)
                    ),
                }
                for sym, info in per_symbol_dump.items()
                if isinstance(info, dict)
            ),
            key=lambda r: -float(r.get("opportunity_score", 0) or 0),
        )
        for i, r in enumerate(rankings, start=1):
            r["rank"] = i
        log_decision({
            "event": "selector_rankings",
            "candidate_rankings": rankings,
        })
        log_decision({
            "event": "selector_exhaustion",
            "exhaustion_penalty_applied": result.get("exhaustion_penalty_applied", []),
            "count": len(result.get("exhaustion_penalty_applied", []) or []),
        })
        rotation = result.get("rotation_plan") or {}
        # Build rotation_reason_summary
        reason_sum: dict[str, int] = {}
        for entry in rotation.get("exited", []) or []:
            cat = entry.get("reason_category", "other")
            reason_sum[cat] = reason_sum.get(cat, 0) + 1
        log_decision({
            "event": "selector_rotation",
            "selected": result.get("selected_positions", []),
            "exited": rotation.get("exited", []),
            "entered": rotation.get("entered", []),
            "held": rotation.get("held", []),
            "new_candidates_considered": result.get("new_candidates_considered"),
            "new_candidates_selected": result.get("new_candidates_selected"),
            "rotation_reason_summary": reason_sum,
        })

        missed_breakouts = missed_breakout_candidates(
            ctx.get("candidate_pool") or [],
            result.get("selected_positions") or [],
            result.get("per_symbol") or {},
            threshold=float(
                self.cfg.get("selector", "missed_breakout_threshold", default=72) or 72
            ),
        )
        log_decision({
            "event": "missed_breakout_detection",
            "missed_breakouts": missed_breakouts,
            "count": len(missed_breakouts),
        })
        if not selector_safety_noop:
            try:
                dynamic_watchlist_update = update_dynamic_watchlist(
                    self.cfg,
                    ctx.get("candidate_pool") or [],
                    selected_symbols=result.get("selected_positions") or [],
                    missed_breakouts=missed_breakouts,
                )
                log_decision({
                    "event": "dynamic_watchlist_update",
                    "update": dynamic_watchlist_update,
                    "phase": "selector_completed",
                })
            except Exception as e:
                dynamic_watchlist_update = {"error": str(e)}
                log.warning("[dynamic_watchlist] update failed: %s", e)

        # 7. Build one final target portfolio, then execute it as one rebalance.
        original_target_weights = result.get("target_weights") or {}
        spy_target_pct = float(result.get("spy_target_pct", 0) or 0)
        held_syms_set = {p.symbol for p in portfolio.get("holdings", [])}
        target_weights, per_symbol, cash_target_pct, staging_adjustments = (
            self._stage_new_entry_targets(result, held_syms_set, equity)
        )
        if staging_adjustments:
            result["execution_target_weights"] = target_weights
            result["execution_per_symbol"] = per_symbol
            result["execution_cash_target_pct"] = cash_target_pct
            result["new_entry_staging"] = staging_adjustments
            log_decision({
                "event": "selector_new_entry_staging",
                "adjustments": staging_adjustments,
            })
        target_weights, per_symbol, cash_target_pct, blocked_new_entries = (
            self._apply_new_entry_execution_gates(
                result=result,
                target_weights=target_weights,
                per_symbol=per_symbol,
                held_symbols=held_syms_set,
                pool_meta=pool_meta,
                portfolio=portfolio,
                equity=equity,
            )
        )
        if blocked_new_entries:
            log_decision({
                "event": "selector_new_entry_targets_removed_pre_plan",
                "removed": blocked_new_entries,
                "execution_target_weights": target_weights,
                "execution_cash_target_pct": cash_target_pct,
            })
        # Cash floor for buy execution must reflect the SELECTOR'S ORIGINAL
        # cash intent, not the post-stage/post-block bumped value. Staging
        # (70-85% of target) and execution-gate blocks reclassify portions of
        # would-be entry weight as cash, inflating `cash_target_pct` here. If
        # we then use that inflated value as the buy floor we lock ourselves
        # out of the very entries whose weight got bumped. See 2026-05-11
        # 07:03 scan: selector emitted cash=5%, post-stage+block hit ~25%,
        # buy floor used 25% and skipped INOD/NVDA/RKLX with
        # insufficient_confirmed_cash even though SPY proxy had ample cover.
        original_cash_target_pct = float(result.get("cash_target_pct", 0) or 0)
        selector_cash_floor_pct = max(
            original_cash_target_pct,
            float(self.risk.cash_reserve_pct),
        )
        unified_portfolio_plan = self._build_unified_portfolio_plan_audit(
            result=result,
            target_weights=target_weights,
            per_symbol=per_symbol,
            pool_meta=pool_meta,
            portfolio=portfolio,
            equity=equity,
            cash_usd=float(account.cash),
            spy_target_pct=spy_target_pct,
            cash_target_pct=cash_target_pct,
            blocked_new_entries=blocked_new_entries,
        )
        log_decision({
            "event": "unified_portfolio_target_plan",
            "plan": unified_portfolio_plan,
        })

        # compute_rebalance_plan covers the union of current holdings and
        # selected new entries, so trims, exits, adds, and fresh buys are one
        # capital-allocation plan instead of competing execution paths.
        plan = compute_rebalance_plan(
            positions=portfolio.get("holdings", []),
            tech_map=portfolio.get("tech_map", {}) or {},
            sent_map=portfolio.get("sent_map", {}) or {},
            numeric_decisions=portfolio.get("numeric", {}) or {},
            ai_verdicts={},
            equity=equity,
            config=self.cfg,
            cash_proxy_symbol=self.cash_proxy_symbol if self.cash_proxy_enabled else None,
            ai_target_weights=target_weights,
            ai_per_symbol=per_symbol,
        )
        log_decision({
            "event": "unified_rebalance_plan",
            "actions": [a.to_dict() for a in plan or []],
            "cash_floor_pct": selector_cash_floor_pct,
            "target_weights": target_weights,
            "cash_target_pct": cash_target_pct,
        })
        executions: list[dict[str, Any]] = []
        # Phase 1a: split rebalance into Sell + DustSweep + Buy passes so
        # freed cash funds buys instead of buys racing the sell fills and
        # being capped to single-share lots. The pre-buy dust-sweep also
        # handles positions where the selector silently dropped a target
        # (off-pool drift, residual fractional shares) — without waiting for
        # the post-execution verifier (which today runs AFTER the buy
        # phase, too late to fund anything).
        sell_actions = [a for a in (plan or []) if a.side == "sell"]
        buy_actions = [a for a in (plan or []) if a.side == "buy"]

        # --- Sell phase ---
        for a in sell_actions:
            if dry_run:
                log.info("[DRY] Rebalance %s", a.to_dict())
                executions.append({"dry_run": True, **a.to_dict()})
                continue
            action_result = self._execute_ai_rebalance_action(
                a, equity=equity, cash_floor_pct=selector_cash_floor_pct,
                label="[selector] rebalance",
            )
            executions.append(action_result)
            exec_result = action_result.get("execution") or {}
            if exec_result and not exec_result.get("ok"):
                log.warning("[selector] rebalance %s did not fill", a.symbol)

        # --- Pre-buy dust-sweep ---
        # Catch any held position whose target is 0% but didn't make it into
        # the sell plan (compute_rebalance_plan can drop it under certain
        # conditions). Running this BEFORE the buy phase means dust-sweep
        # proceeds fund buys; the post-execution verifier still runs as a
        # final reconciliation pass.
        if not dry_run:
            try:
                pre_buy_dust = self._predetermined_dust_sweep_for_buys(target_weights)
                if pre_buy_dust:
                    executions.extend(pre_buy_dust)
            except Exception as e:
                log.warning("[selector] pre-buy dust-sweep failed: %s", e)

        # --- Buy phase ---
        for a in buy_actions:
            if dry_run:
                log.info("[DRY] Rebalance %s", a.to_dict())
                executions.append({"dry_run": True, **a.to_dict()})
                continue
            action_result = self._execute_ai_rebalance_action(
                a, equity=equity, cash_floor_pct=selector_cash_floor_pct,
                label="[selector] rebalance",
            )
            executions.append(action_result)
            exec_result = action_result.get("execution") or {}
            if exec_result and not exec_result.get("ok"):
                log.warning("[selector] rebalance %s did not fill", a.symbol)

        failed_new_entry_targets: list[dict[str, Any]] = []
        for action_result in executions:
            sym = action_result.get("symbol")
            if not sym or sym in held_syms_set:
                continue
            if not action_result.get("is_new_entry") or action_result.get("side") != "buy":
                continue
            exec_result = action_result.get("execution") or {}
            failed_reason = None
            if action_result.get("skipped"):
                failed_reason = action_result.get("skipped")
            elif action_result.get("_error"):
                failed_reason = "execution_exception"
            elif exec_result and not exec_result.get("ok"):
                failed_reason = exec_result.get("status") or "execution_not_filled"
            if failed_reason:
                failed_new_entry_targets.append({
                    "symbol": sym,
                    "reason": failed_reason,
                    "execution": action_result,
                })

        if failed_new_entry_targets:
            for item in failed_new_entry_targets:
                sym = item.get("symbol")
                if not sym:
                    continue
                failed_w = float(target_weights.pop(sym, 0.0) or 0.0)
                if failed_w > 0:
                    cash_target_pct = round(cash_target_pct + failed_w, 4)
                info = dict(per_symbol.get(sym) or {})
                info["target_pct"] = 0.0
                info["qty"] = 0
                info["delta_qty"] = 0
                info["action"] = "PASS"
                info["_execution_target_removed"] = item.get("reason")
                per_symbol[sym] = info
            unified_portfolio_plan["post_execution_target_removals"] = failed_new_entry_targets
            log_decision({
                "event": "selector_failed_new_entry_targets_removed",
                "removed": failed_new_entry_targets,
                "execution_target_weights": target_weights,
                "execution_cash_target_pct": cash_target_pct,
            })
            unified_portfolio_plan = self._build_unified_portfolio_plan_audit(
                result=result,
                target_weights=target_weights,
                per_symbol=per_symbol,
                pool_meta=pool_meta,
                portfolio=portfolio,
                equity=equity,
                cash_usd=float(account.cash),
                spy_target_pct=spy_target_pct,
                cash_target_pct=cash_target_pct,
                blocked_new_entries=[
                    *blocked_new_entries,
                    *[
                        {
                            "symbol": item.get("symbol"),
                            "reason": item.get("reason"),
                            "phase": "post_execution",
                        }
                        for item in failed_new_entry_targets
                    ],
                ],
            )
            unified_portfolio_plan["post_execution_target_removals"] = failed_new_entry_targets

        self._last_ai_target_weights = dict(target_weights)
        self._last_ai_per_symbol = dict(per_symbol) if isinstance(per_symbol, dict) else {}
        self._last_ai_spy_target_pct = spy_target_pct
        self._last_ai_cash_target_pct = cash_target_pct

        # 8. Apply SPY target + verifier
        cash_proxy_action = None
        if not selector_safety_noop and not dry_run and self.cash_proxy_enabled:
            try:
                cash_proxy_action = self._apply_spy_target(spy_target_pct, equity)
                self._last_arbiter_set_spy_target = True
            except Exception as e:
                log.warning("[selector] SPY target apply failed: %s", e)
        elif selector_safety_noop:
            cash_proxy_action = {"skipped": "selector_safety_noop"}

        verifier_summary: dict[str, Any] | None = None
        if selector_safety_noop:
            verifier_summary = {"skipped": "selector_safety_noop"}
        elif not dry_run:
            try:
                verifier_summary = self._verify_portfolio_alignment(equity)
            except Exception as e:
                log.warning("[selector] verifier raised: %s", e)
                verifier_summary = {"error": str(e)}

        # Policy-aware SPY-as-cash discipline. Excess cash is parked only when
        # the persisted selector/tape policy says SPY is the better idle sink.
        # A selector cash decision is locked so the 5-minute stop checker does
        # not reverse it immediately after a scan.
        idle_park_action = None
        if not selector_safety_noop and not dry_run and self.cash_proxy_enabled:
            try:
                idle_park_action = self._sweep_cash_to_proxy(
                    equity, cash_policy_decision=cash_policy_decision,
                )
                if idle_park_action and idle_park_action.get("action") == "buy_proxy":
                    log.info(
                        "[selector] SPY-as-cash sweep: $%.0f idle parked",
                        float(idle_park_action.get("notional") or 0),
                    )
            except Exception as e:
                log.warning("[selector] idle-cash SPY sweep failed: %s", e)
        trade_learning_end = self._resolve_trade_learning("scan_end")

        # Phase 3 (2026-05-07): consolidated trade-failure Telegram alert.
        # Diff selector intent (per_symbol with non-PASS action) against
        # actual executor outcomes. Fires for: stop-clamp neutralized symbols,
        # blocked new entries, post-execution removals, and any execution
        # whose ExecutionResult status is rejected/unfilled/not_submitted.
        try:
            if bool(self.cfg.get("telegram", "notify_trade_failures", default=True)):
                from src.telegram_notifier import get_notifier

                mismatches: list[dict[str, Any]] = []
                errors: list[dict[str, Any]] = []

                # Stop-tighten neutralizations from validator (#2 path).
                dropped_for_stop = result.get("_dropped_for_invalid_stop") if isinstance(result, dict) else None
                for sym in dropped_for_stop or []:
                    info = (per_symbol or {}).get(sym) or {}
                    mismatches.append({
                        "symbol": sym,
                        "action": "PASS (stop-clamp neutralized)",
                        "reason": info.get("pass_reason") or "stop cannot meet max_risk_per_trade",
                    })

                # Blocked new entries (e.g. earnings, sector cap).
                for entry in blocked_new_entries or []:
                    mismatches.append({
                        "symbol": entry.get("symbol", "?"),
                        "action": entry.get("action", "BUY"),
                        "reason": entry.get("reason", "blocked"),
                    })

                # Post-execution removals (selector said BUY but execution failed).
                for entry in failed_new_entry_targets or []:
                    errors.append({
                        "symbol": entry.get("symbol", "?"),
                        "status": "execution_failed",
                        "reason": entry.get("reason", "unknown"),
                    })

                # Sweep executions for any explicit error status.
                for ex in executions or []:
                    if not isinstance(ex, dict):
                        continue
                    if ex.get("dry_run"):
                        continue
                    sym = ex.get("symbol")
                    if not sym:
                        continue
                    er = ex.get("execution") or {}
                    status = er.get("status")
                    if status in {"rejected", "unfilled", "not_submitted_entry_unfilled"}:
                        errors.append({
                            "symbol": sym,
                            "status": status,
                            "reason": er.get("message") or er.get("reject_reason") or "no detail",
                        })

                if mismatches or errors:
                    label = "selector-scan"
                    get_notifier().notify_trade_failure(
                        scan_label=label,
                        mismatches=mismatches,
                        errors=errors,
                    )
        except Exception as e:
            log.debug("Telegram trade-failure notify failed: %s", e)

        if isinstance(unified_portfolio_plan, dict):
            unified_portfolio_plan["cash_policy"] = cash_policy_decision
            unified_portfolio_plan["sector_guard"] = sector_guard_audit

        summary = {
            "ts": pd.Timestamp.utcnow().isoformat(),
            "equity": equity,
            "positions_count": len(positions),
            "macro": macro.to_dict(),
            "selector": {
                "pool_size": len(candidates),
                "sources_breakdown": breakdown,
                "selected_positions": result.get("selected_positions", []),
                "target_weights": original_target_weights,
                "execution_target_weights": target_weights,
                "spy_target_pct": spy_target_pct,
                "cash_target_pct": result.get("cash_target_pct"),
                "execution_cash_target_pct": cash_target_pct,
                "exhaustion_penalty_applied": result.get("exhaustion_penalty_applied", []),
                "new_candidates_selected": result.get("new_candidates_selected"),
                "new_entry_staging": staging_adjustments,
                "blocked_new_entries": blocked_new_entries,
                "post_execution_target_removals": failed_new_entry_targets,
                "allow_floor_breach": allow_floor_breach,
                "missed_breakouts": missed_breakouts,
                "dynamic_watchlist": dynamic_watchlist_update,
                "cash_policy": cash_policy_decision,
                "sector_guard": sector_guard_audit,
                "safety_noop": selector_safety_noop,
                "safety_noop_reason": result.get("_selector_failure_reason"),
                "consecutive_failures": result.get("_selector_consecutive_failures"),
            },
            "unified_portfolio_plan": unified_portfolio_plan,
            "exits": exit_results,
            "executions": executions,
            "cash_proxy": cash_proxy_action,
            "idle_park": idle_park_action,
            "cash_policy": cash_policy_decision,
            "verifier": verifier_summary,
            "trade_learning": {
                "start": trade_learning_start,
                "end": trade_learning_end,
            },
        }
        _save_research("scan", summary)
        log.info("Scan complete (selector): selected=%d, exits=%d, executions=%d",
                 len(result.get("selected_positions", [])),
                 len(exit_results), len(executions))
        return summary

    # ---------- main loop ----------
    def run_scan(self, max_candidates: int = 25, dry_run: bool = False) -> dict[str, Any]:
        # Phase 4 cutover: when the unified-selector feature flag is on, route
        # to the new pipeline. Legacy two-pipeline path runs only when off.
        if self.cfg.get("selector", "enabled", default=False):
            return self._run_scan_with_selector(dry_run=dry_run)
        log.info("=== Starting scan (dry_run=%s) ===", dry_run)
        # Independent valuation: equity, market_value, unrealized_pl[pc],
        # current_price are recomputed from Alpha-Vantage-sourced prices
        # (Alpaca's paper-account fields are unreliable). Full snapshot
        # audit log fires here.
        account, positions = self.client.get_snapshot(force_refresh=True, log_detail=True)
        equity = float(account.equity)
        log.info("Account: computed_equity=$%.2f, cash=$%.2f, positions=%d",
                 equity, float(account.cash), len(positions))
        if not dry_run:
            try:
                cov = self.executor.ensure_stop_coverage(source="scan_legacy")
                if cov.get("added") or cov.get("errors"):
                    log_decision({"event": "stop_coverage", **cov})
            except Exception as e:
                log.error("[stop-coverage] safety net raised: %s", e)
            self._restore_cash_floor(equity)
        macro = self.macro_brief()

        # Shared portfolio signal bundle (used for exits + rebalance)
        portfolio = self._portfolio_signals(macro)

        # Detect scan type by Eastern Time — no filesystem dependency.
        # FIRST (09:30–11:00 ET): earnings gate runs.
        # MIDDAY (11:00–16:00 ET): earnings-window positions frozen, no exits allowed.
        # UNKNOWN: earnings checks skipped (fail-safe).
        scan_type = self._detect_scan_type()
        log.info("Scan type detected: %s (time-based, America/New_York)", scan_type)

        # Exits first (hard signals — unchanged logic)
        exit_results: list[dict[str, Any]] = []
        exits = self.evaluate_exits(macro, portfolio=portfolio, scan_type=scan_type)
        # Track which symbols were closed for earnings so rebalance won't add back.
        earnings_exit_syms: set[str] = {
            sym for sym, reason in exits if "earnings" in reason.lower()
        }
        for sym, reason in exits:
            if dry_run:
                log.info("[DRY] Would close %s: %s", sym, reason)
                exit_results.append({"symbol": sym, "action": "close_dry", "reason": reason})
            else:
                res = self.executor.close_position(sym, reason=reason)
                exit_results.append({**res.to_dict(), "reason": reason})
                if res.ok:
                    self._clear_position_lifecycle(sym)

        # After closes, refresh portfolio state and rebuild signal bundle so rebalance
        # sees the accurate current book. (Drop exited symbols from the in-memory bundle.)
        if exit_results and not dry_run:
            exited_syms = {e.get("symbol") for e in exit_results if e.get("status") != "rejected"}
            portfolio["holdings"] = [p for p in portfolio.get("holdings", [])
                                     if p.symbol not in exited_syms]

        # Bearish-day flag
        halt_score = float(self.cfg.get("macro", "bearish_halt_score", default=-0.55))
        halt_on_spike = bool(self.cfg.get("macro", "bearish_halt_on_vix_spike", default=True))
        bearish_halt = macro.score <= halt_score or (halt_on_spike and macro.vix_regime == "spike")

        # Rebalance surviving positions (trims always; adds gated on bearish days)
        rebalance_results = self.run_rebalance(
            macro=macro, portfolio=portfolio, equity=equity,
            dry_run=dry_run, allow_adds=not bearish_halt,
            earnings_exit_symbols=earnings_exit_syms,
            bearish_halt=bearish_halt,
        )

        if bearish_halt:
            log.warning(
                "Bearish-day halt: macro_score=%.2f, vix=%s — skipping new screen entries. "
                "Exits + AI-arbiter rebalance still ran; AI received bearish_halt_active=true "
                "as context and decided allocations accordingly.",
                macro.score, macro.vix_regime,
            )
            cash_proxy_action = None
            if not dry_run:
                if self._last_arbiter_set_spy_target:
                    log.info("Auto-sweep skipped: AI arbiter set SPY target this scan")
                    cash_proxy_action = {"skipped": "ai_arbiter_set_spy_target"}
                else:
                    cash_proxy_action = self._sweep_cash_to_proxy(equity)
            verifier_summary: dict[str, Any] | None = None
            if not dry_run:
                try:
                    verifier_summary = self._verify_portfolio_alignment(equity)
                except Exception as e:
                    log.warning("Portfolio verifier raised (bearish-halt path): %s", e)
                    verifier_summary = {"error": str(e)}
            summary = {
                "ts": pd.Timestamp.utcnow().isoformat(),
                "equity": equity,
                "positions_count": len(positions),
                "macro": macro.to_dict(),
                "bearish_halt": {"score": macro.score, "vix_regime": macro.vix_regime,
                                 "threshold": halt_score},
                "exits": exit_results,
                "rebalance": rebalance_results,
                "opportunity_ranking": list(self._last_opportunity_ranking),
                "ai_arbiter_skipped": self._last_arbiter_skipped,
                "executions": [],
                "cash_proxy": cash_proxy_action,
                "verifier": verifier_summary,
            }
            _save_research("scan", summary)
            log.info("Scan complete (bearish halt): exits=%d, rebalance=%d, executions=0",
                     len(exit_results), len(rebalance_results))
            return summary

        # Entries
        universe = build_stock_universe(self.cfg)
        log.info("Universe: %d symbols", len(universe))
        tech_top = self.technical_screen(universe, top_n=max_candidates)
        log.info("Top %d candidates by |technical score|", len(tech_top))

        # Gather news once for top candidates
        top_symbols = [t.symbol for t in tech_top]
        try:
            news_items = self.client.get_news(symbols=top_symbols, limit=100, days_back=3)
        except Exception as e:
            log.warning("News fetch failed: %s", e)
            news_items = []

        decisions: list[TradeDecision] = []
        for tech in tech_top:
            d = self.evaluate_symbol(tech, macro, news_items)
            decisions.append(d)

        actions = [d for d in decisions if d.action == "buy"]
        log.info("Actionable numeric signals: %d / %d", len(actions), len(decisions))

        # --- AI layer: run subagents on top candidates; if available, AI is the gate ---
        ai_verdicts: dict[str, AIVerdict] = {}
        ai_active = self.ai.available()
        if ai_active:
            portfolio_ctx = {
                "equity": equity,
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "positions_count": len(positions),
                "positions": [
                    {"symbol": p.symbol, "side": str(p.side), "qty": str(p.qty),
                     "market_value": str(p.market_value),
                     "unrealized_plpc": float(p.unrealized_plpc)}
                    for p in positions
                ],
            }
            log.info("AI research enabled (model=%s). Running subagents on top candidates…",
                     self.cfg.get("ai", "model", default="?"))
            ai_verdicts = run_ai_on_candidates(
                self.cfg,
                candidates=decisions,
                macro_ctx=macro.to_dict(),
                portfolio_ctx=portfolio_ctx,
            )
            for sym, v in ai_verdicts.items():
                log.info("AI[%s] action=%s conf=%.2f grades=%s%s",
                         sym, v.final_action, v.ai_confidence, v.agent_grades,
                         f" errors={v.errors}" if v.errors else "")
                log_decision({"event": "ai_verdict", "symbol": sym, "verdict": v.to_dict()})
        else:
            log.critical(
                "AI research (Opus 4.7) unavailable — NO NEW ENTRIES will be "
                "executed this scan. Hard rule: no trade may execute without "
                "AI approval. Skipping entry pipeline."
            )

        # --- Build final execution list ---
        ai_weight = float(self.cfg.get("ai", "weight", default=0.6))
        min_conf = float(self.cfg.get("risk", "min_confidence", default=0.40))
        executions: list[dict[str, Any]] = []

        # Candidates to execute: if AI is active, ONLY those AI approved for buys.
        # If AI is inactive, numeric-only (current behavior).
        if ai_active:
            pipeline_candidates = []
            for sym, verdict in ai_verdicts.items():
                if verdict.final_action != "buy":
                    continue
                if verdict.ai_confidence <= 0:
                    continue
                numeric = next((d for d in decisions if d.symbol == sym), None)
                if not numeric:
                    continue
                # Blend AI confidence with numeric when the numeric score is long-biased.
                num_dir_matches = numeric.combined_score >= 0
                numeric_conf = numeric.confidence if num_dir_matches else 0.0
                blended_conf = ai_weight * verdict.ai_confidence + (1 - ai_weight) * numeric_conf
                if blended_conf < min_conf:
                    log.info("Skipping %s: blended confidence %.2f < %.2f",
                             sym, blended_conf, min_conf)
                    continue
                # Clone numeric decision with AI-blended confidence and AI-chosen action
                final_decision = TradeDecision(
                    symbol=sym,
                    action=verdict.final_action,
                    confidence=blended_conf,
                    combined_score=numeric.combined_score,
                    signal_scores=numeric.signal_scores,
                    signal_details={
                        **numeric.signal_details,
                        "ai_verdict": verdict.to_dict(),
                    },
                    reasoning=numeric.reasoning + [
                        f"ai={verdict.final_action}@{verdict.ai_confidence:.2f}",
                        f"blended_conf={blended_conf:.2f}",
                        f"thesis: {verdict.thesis[:120]}",
                    ],
                )
                pipeline_candidates.append(final_decision)
        else:
            # Fail-safe: AI unavailable means we cannot execute any entries.
            # Deterministic signals are NOT allowed to trigger trades on their own.
            pipeline_candidates = []

        log.info("Approved for execution: %d", len(pipeline_candidates))

        # Earnings gate on new entries. Use the wider 7-day new-entry blackout
        # (separate from the 3-day held-position trim window).
        if self.earnings_enabled and pipeline_candidates:
            gated: list[TradeDecision] = []
            for d in pipeline_candidates:
                einfo_dict = d.signal_details.get("earnings") or {}
                days_until = einfo_dict.get("days_until_earnings")
                if days_until is not None and 0 <= days_until <= self.entry_earnings_blackout_days:
                    if d.confidence < self.entry_earnings_override:
                        log.info(
                            "[%s] earnings in %dd (%s) — blocking NEW entry "
                            "(conf=%.2f < override=%.2f, blackout=%dd)",
                            d.symbol, days_until,
                            einfo_dict.get("next_earnings_date"),
                            d.confidence, self.entry_earnings_override,
                            self.entry_earnings_blackout_days,
                        )
                        continue
                    log.info(
                        "[%s] earnings in %dd but conf=%.2f >= %.2f — allowing entry",
                        d.symbol, days_until, d.confidence, self.entry_earnings_override,
                    )
                gated.append(d)
            pipeline_candidates = gated
            log.info("Approved after earnings gate: %d", len(pipeline_candidates))

        for d in pipeline_candidates:
            tech_detail = d.signal_details.get("technical", {})
            price = tech_detail.get("price")
            atr = tech_detail.get("atr")
            if not price or not atr:
                continue
            sizing = self.risk.size_position(
                symbol=d.symbol,
                side="buy",
                price=price, atr=atr,
                confidence=d.confidence,
                equity=equity,
                existing_positions=positions,
            )
            if not sizing:
                continue
            if dry_run:
                log.info("[DRY] Would execute %s", sizing.to_dict())
                executions.append({"dry_run": True, "sizing": sizing.to_dict(), "decision": d.to_dict()})
            else:
                # Ensure real cash covers the notional; sell SPY cash-proxy if needed.
                # Re-fetched per-iteration so a prior unfilled trade doesn't leave
                # us thinking we have cash we don't.
                preflight_ok, preflight = self.executor.preflight_buy(
                    symbol=d.symbol,
                    qty=sizing.qty,
                    entry_price=sizing.entry,
                    stop_loss=sizing.stop_loss,
                    take_profit=sizing.take_profit,
                )
                if not preflight_ok:
                    log.warning("[%s] entry preflight rejected: %s",
                                d.symbol, preflight.get("reject_reason"))
                    executions.append({
                        "sizing": sizing.to_dict(),
                        "decision": d.to_dict(),
                        "status": "skipped",
                        "message": "execution_preflight_rejected",
                        "execution_preflight": preflight,
                    })
                    continue
                submitted_qty = float(preflight.get("submitted_qty") or sizing.qty)
                if abs(submitted_qty - float(sizing.qty)) > 1e-9 and sizing.entry:
                    sizing = replace(
                        sizing,
                        qty=submitted_qty,
                        notional=round(submitted_qty * float(sizing.entry), 2),
                        risk_usd=round(
                            submitted_qty * (float(sizing.entry) - float(sizing.stop_loss)),
                            2,
                        ),
                        limits={**dict(sizing.limits), "execution_preflight": preflight},
                    )
                else:
                    sizing.limits["execution_preflight"] = preflight
                if not self._ensure_cash_for(sizing.notional, equity):
                    log.warning("[%s] entry skipped: insufficient confirmed cash", d.symbol)
                    executions.append({
                        "sizing": sizing.to_dict(),
                        "decision": d.to_dict(),
                        "status": "skipped",
                        "message": "insufficient_confirmed_cash",
                    })
                    continue
                result = self.executor.execute(d, sizing)
                executions.append({
                    "sizing": sizing.to_dict(),
                    "decision": d.to_dict(),
                    "execution": result.to_dict(),
                    **result.to_dict(),
                })
                if result.ok:
                    self._record_position_entry(
                        d.symbol,
                        source="legacy_scan",
                        execution=result.to_dict(),
                        context={
                            "reason": "; ".join(d.reasoning),
                            "confidence": d.confidence,
                            "ai_action": d.action,
                        },
                    )
                if not result.ok:
                    log.warning("[%s] entry did not fill — refreshing positions before next sizing",
                                d.symbol)
                # Always refresh positions so the next size_position sees the
                # accurate book (including failed-fill state, which leaves cash intact).
                positions = self.client.get_positions()

        # Sweep idle cash above the true-cash floor into SPY — UNLESS the AI
        # portfolio arbiter explicitly set a SPY target this scan (in which case
        # the SPY/cash split is the AI's decision, and the bot must not override
        # it deterministically).
        cash_proxy_action = None
        if not dry_run:
            if self._last_arbiter_set_spy_target:
                log.info("Auto-sweep skipped: AI arbiter set SPY target this scan")
                cash_proxy_action = {"skipped": "ai_arbiter_set_spy_target"}
            else:
                cash_proxy_action = self._sweep_cash_to_proxy(equity)

        # ---- Post-execution Sonnet verifier ----
        # Reconcile actual portfolio against the targets the Opus arbiter set
        # this scan: force-close any target=0 dust, and ask Sonnet to surface
        # any remaining sub-target gaps above the tolerance band. Always runs
        # (when arbiter set targets); skipped on dry-run.
        verifier_summary: dict[str, Any] | None = None
        if not dry_run:
            try:
                verifier_summary = self._verify_portfolio_alignment(equity)
            except Exception as e:
                log.warning("Portfolio verifier raised: %s — continuing without reconcile", e)
                verifier_summary = {"error": str(e)}

        summary = {
            "ts": pd.Timestamp.utcnow().isoformat(),
            "equity": equity,
            "positions_count": len(positions),
            "macro": macro.to_dict(),
            "candidates_evaluated": len(decisions),
            "actionable_numeric": len(actions),
            "ai_active": ai_active,
            "ai_verdicts": {s: v.to_dict() for s, v in ai_verdicts.items()},
            "approved_for_execution": len(pipeline_candidates),
            "exits": exit_results,
            "rebalance": rebalance_results,
            "opportunity_ranking": list(self._last_opportunity_ranking),
            "ai_arbiter_skipped": self._last_arbiter_skipped,
            "executions": executions,
            "cash_proxy": cash_proxy_action,
            "verifier": verifier_summary,
            "decisions": [d.to_dict() for d in decisions],
        }
        _save_research("scan", summary)
        verifier_corrects = (
            len((verifier_summary or {}).get("corrective_trades") or []) if verifier_summary else 0
        )
        verifier_dust = (
            len((verifier_summary or {}).get("dust_closed") or []) if verifier_summary else 0
        )
        log.info("Scan complete: exits=%d, rebalance=%d, executions=%d, verifier_corrects=%d, dust_closed=%d",
                 len(exit_results), len(rebalance_results), len(executions),
                 verifier_corrects, verifier_dust)
        return summary

    # ---------- pre-close overnight decision ----------
    def _fetch_intraday(self, symbols: list[str], minutes: int = 5):
        """Fetch intraday bars for today's session. Returns multi-index df or empty."""
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
        if not symbols:
            return None
        try:
            tf = TimeFrame(minutes, TimeFrameUnit.Minute)
            return self.client.get_stock_bars(symbols, timeframe=tf, lookback_days=2)
        except Exception as e:
            log.warning("Intraday bars fetch failed: %s", e)
            return None

    @staticmethod
    def _slice_symbol(bars_df, symbol: str):
        if bars_df is None or bars_df.empty:
            return None
        try:
            if "symbol" in bars_df.index.names:
                g = bars_df.xs(symbol, level="symbol")
                return g
            return bars_df
        except KeyError:
            return None

    def run_preclose(self, dry_run: bool = False) -> dict[str, Any]:
        """~5 min before the close: decide whether to hold each position overnight,
        and optionally open new positions likely to gap up at the next open."""
        log.info("=== Pre-close overnight decision (dry_run=%s) ===", dry_run)
        trade_learning_start = self._resolve_trade_learning("preclose_start")
        try:
            overnight_learning_start = resolve_overnight_outcomes(self.cfg, self.client)
        except Exception as e:
            log.warning("overnight-learning resolve failed at preclose start: %s", e)
            overnight_learning_start = {"enabled": True, "error": str(e)}

        # HARD RULE: preclose closes/opens touch capital, so they must route
        # through the Opus 4.7 arbiter. No AI → no preclose trades.
        if not self.ai.available():
            log.critical(
                "run_preclose: AI (Opus 4.7) unavailable — skipping all preclose "
                "trade actions (fail-safe). Stop-losses remain live."
            )
            # Best-effort equity read for the notification — preclose ran too
            # early to have it computed yet, so do a quick snapshot here.
            try:
                _account, _positions = self.client.get_snapshot(log_detail=False)
                _equity = float(_account.equity)
                _pos_count = len([p for p in _positions if "/" not in p.symbol])
            except Exception:
                _equity = 0.0
                _pos_count = 0
            return {
                "skipped": "ai_unavailable",
                "equity": _equity,
                "positions_count": _pos_count,
                "hold_reports": [],
                "exits": [],
                "new_executions": [],
                "market_bias": 0.0,
                "trade_learning": {"start": trade_learning_start},
                "overnight_learning": {"start": overnight_learning_start},
            }

        # Config knobs (weekday defaults)
        hold_threshold = float(self.cfg.get("overnight", "hold_threshold", default=0.0))
        buy_threshold = float(self.cfg.get("overnight", "buy_threshold", default=0.35))
        bearish_buy_threshold = float(
            self.cfg.get("overnight", "bearish_bias_buy_threshold", default=0.45)
        )
        max_new = int(self.cfg.get("overnight", "max_new_positions", default=3))
        size_mult = float(self.cfg.get("overnight", "size_multiplier", default=0.5))
        scan_candidates = int(self.cfg.get("overnight", "scan_candidates", default=30))
        enable_new_buys = bool(self.cfg.get("overnight", "enable_new_buys", default=True))
        max_rsi_new_buy = float(self.cfg.get("overnight", "max_rsi_for_new_buy", default=78))
        sequential_cash = bool(self.cfg.get("overnight", "sequential_cash_check", default=True))
        catalyst_enabled = bool(
            self.cfg.get("preclose_earnings_catalyst", "enabled", default=True)
        )
        catalyst_lookahead_days = int(
            self.cfg.get("preclose_earnings_catalyst", "lookahead_days", default=1) or 1
        )
        catalyst_buy_threshold = float(
            self.cfg.get("preclose_earnings_catalyst", "buy_threshold", default=0.60)
            or 0.60
        )
        catalyst_min_sentiment = float(
            self.cfg.get("preclose_earnings_catalyst", "min_sentiment", default=0.05)
            or 0.05
        )
        catalyst_size_multiplier = float(
            self.cfg.get("preclose_earnings_catalyst", "size_multiplier", default=0.35)
            or 0.35
        )
        catalyst_allowed_sources = {
            str(s)
            for s in (
                self.cfg.get(
                    "preclose_earnings_catalyst",
                    "allowed_sources",
                    default=["av_news", "av_gainers", "tv_breakout"],
                )
                or []
            )
        }
        catalyst_min_research = float(
            self.cfg.get("preclose_earnings_catalyst", "min_research_score", default=0.25)
            or 0.25
        )
        catalyst_event_threshold = float(
            self.cfg.get("preclose_earnings_catalyst", "event_risk_buy_threshold", default=0.65)
            or 0.65
        )
        catalyst_post_threshold = float(
            self.cfg.get("preclose_earnings_catalyst", "post_earnings_buy_threshold", default=0.50)
            or 0.50
        )
        catalyst_non_event_threshold = float(
            self.cfg.get("preclose_earnings_catalyst", "non_event_buy_threshold", default=0.58)
            or 0.58
        )
        catalyst_unknown_time_is_event = bool(
            self.cfg.get("preclose_earnings_catalyst", "unknown_time_is_event_risk", default=True)
        )
        edge_weights = {
            "momentum": float(self.cfg.get("overnight", "edge", "momentum_weight", default=0.12) or 0.12),
            "sector": float(self.cfg.get("overnight", "edge", "sector_weight", default=0.10) or 0.10),
            "earnings": float(self.cfg.get("overnight", "edge", "earnings_weight", default=1.0) or 1.0),
            "learned": float(self.cfg.get("overnight", "edge", "learned_weight", default=1.0) or 1.0),
            "gap_only_penalty": float(self.cfg.get("overnight", "edge", "gap_only_penalty", default=0.18) or 0.18),
            "fading_penalty": float(self.cfg.get("overnight", "edge", "fading_penalty", default=0.10) or 0.10),
            "high_atr_penalty": float(self.cfg.get("overnight", "edge", "high_atr_penalty", default=0.08) or 0.08),
            "high_atr_pct": float(self.cfg.get("overnight", "edge", "high_atr_pct", default=0.08) or 0.08),
        }

        # Weekend / pre-holiday detection: when the gap to the next trading
        # session is ≥ 2 calendar days, swap in stricter weekend thresholds
        # and lower the bar to override an AI hold verdict (easier to close
        # before a multi-day overnight).
        session_gap_days = self._session_gap_calendar_days()
        weekend_session = session_gap_days >= 2
        weekend_min_exit_conf: float | None = None
        if weekend_session:
            wk = self.cfg.get("overnight", "weekend", default={}) or {}
            hold_threshold = float(wk.get("hold_threshold", 0.20))
            buy_threshold = float(wk.get("buy_threshold", 0.55))
            bearish_buy_threshold = float(wk.get("bearish_buy_threshold", 0.65))
            weekend_min_exit_conf = float(wk.get("exit_arbiter_min_confidence", 0.40))
            log.info(
                "Preclose weekend mode: session_gap=%d days, "
                "hold_threshold=%.2f buy_threshold=%.2f exit_min_conf=%.2f",
                session_gap_days, hold_threshold, buy_threshold,
                weekend_min_exit_conf,
            )

        account, positions = self.client.get_snapshot(force_refresh=True, log_detail=True)
        equity = float(account.equity)
        equity_positions = [p for p in positions if "/" not in p.symbol]
        log.info("Preclose: computed_equity=$%.2f, positions=%d (equity=%d)",
                 equity, len(positions), len(equity_positions))

        # Market tape read from SPY intraday
        spy_intraday = self._fetch_intraday(["SPY"], minutes=5)
        spy_slice = self._slice_symbol(spy_intraday, "SPY")
        market_bias = market_bias_from_spy(spy_slice)
        log.info("Preclose market_bias (SPY late-day): %+.2f", market_bias)

        # ---------- Evaluate held positions ----------
        held_syms = [p.symbol for p in equity_positions]
        intraday_held = self._fetch_intraday(held_syms, minutes=5) if held_syms else None
        daily_held = None
        if held_syms:
            try:
                daily_held = self.client.get_stock_bars(held_syms, lookback_days=252)
            except Exception as e:
                log.warning("Daily bars for held failed: %s", e)
        tech_held = technicals_for_bars_df(daily_held) if daily_held is not None else {}
        news_held = self.client.get_news(symbols=held_syms, limit=80, days_back=2) if held_syms else []

        # Fetch earnings data for earnings-risk gate (pre-close scan runs the same
        # earnings gate logic as the first scan of the day).
        earnings_map_preclose: dict[str, EarningsInfo] = {}
        if self.earnings_enabled and held_syms:
            for _sym in held_syms:
                try:
                    _einfo = fetch_earnings(_sym, ttl_hours=self.earnings_ttl_hours)
                    if _einfo:
                        earnings_map_preclose[_sym] = _einfo
                except Exception as _e:
                    log.warning("[%s] preclose earnings fetch failed: %s", _sym, _e)
        if earnings_map_preclose:
            log.info(
                "Preclose earnings-risk gate: %d held position(s) have earnings data",
                len(earnings_map_preclose),
            )

        hold_reports: list[dict[str, Any]] = []
        exit_results: list[dict[str, Any]] = []
        for p in equity_positions:
            sym = p.symbol
            tech = tech_held.get(sym)
            tech_score = tech.score if tech else 0.0
            sent = score_news_for_symbol(sym, news_held)
            sent_score = sent.score if sent else 0.0

            # Earnings-risk gate: pre-close scan runs the same earnings gate as the
            # first scan of the day. If the AI says close/hold here, we skip the
            # overnight scoring decision entirely for that position.
            _einfo_pre = earnings_map_preclose.get(sym) if self.earnings_enabled else None
            _in_earn_win = bool(_einfo_pre and within_window(_einfo_pre, self.earnings_trim_days))
            if _in_earn_win:
                log.info(
                    "[%s] earnings-risk gate running (pre-close scan — earnings in %dd)",
                    sym, _einfo_pre.days_until,
                )
                _plpc = float(p.unrealized_plpc) if hasattr(p, "unrealized_plpc") else 0.0
                _earn_verdict, _earn_reason = self._earnings_gate_decision(
                    p=p, einfo=_einfo_pre, tech=tech, sent=sent,
                    numeric=None, macro=None,
                    plpc=_plpc,
                )
                if _earn_verdict == "close":
                    hold_reports.append({"symbol": sym, "decision": "close_earnings_gate"})
                    if dry_run:
                        exit_results.append({
                            "symbol": sym, "action": "close_dry", "reason": _earn_reason,
                        })
                    else:
                        _res = self.executor.close_position(sym, reason=_earn_reason)
                        exit_results.append({**_res.to_dict(), "reason": _earn_reason})
                        if _res.ok:
                            self._clear_position_lifecycle(sym)
                    continue
                if _earn_verdict == "hold":
                    log.info(
                        "[%s] preclose earnings gate: hold — skipping overnight close decision",
                        sym,
                    )
                    hold_reports.append({"symbol": sym, "decision": "hold_earnings_gate"})
                    continue
                if _earn_verdict == "trim_50":
                    # Execute the trim now and skip the overnight decision —
                    # the position size is already deliberately reduced.
                    log.info(
                        "[%s] preclose earnings gate: trim_50 — executing 50%% trim",
                        sym,
                    )
                    hold_reports.append({"symbol": sym, "decision": "trim_50_earnings_gate"})
                    if dry_run:
                        exit_results.append({
                            "symbol": sym, "action": "trim_50_dry", "reason": _earn_reason,
                        })
                    else:
                        _res = self.executor.reduce_position_pct(
                            sym, percentage=50.0, reason=_earn_reason,
                        )
                        exit_results.append({**_res.to_dict(), "reason": _earn_reason})
                    continue
                # skip_no_ai: fall through to overnight decision

            intraday = self._slice_symbol(intraday_held, sym)
            ov = score_overnight(sym, intraday, tech_score, sent_score, market_bias)
            if ov is None:
                log.info("[%s] no intraday data; keeping position", sym)
                hold_reports.append({"symbol": sym, "decision": "hold_no_data"})
                continue

            directional = ov.score
            decision = "hold" if directional >= hold_threshold else "close"
            report = {
                "symbol": sym,
                "overnight": ov.to_dict(),
                "directional_score": round(directional, 3),
                "decision": decision,
                "weekend_session": weekend_session,
            }
            hold_reports.append(report)
            log.info("[%s] directional=%+.2f (ov=%+.2f) notes=%s -> %s",
                     sym, directional, ov.score, ov.notes, decision.upper())
            # Reset the veto-circuit-breaker counter on a healthy directional day.
            if directional >= 0:
                self._reset_preclose_veto(sym)
            if decision == "close":
                # Route every preclose close through Opus 4.7 exit-arbiter.
                num_dec = self.engine.decide(
                    symbol=sym,
                    technical_score=tech.score if tech else 0.0,
                    fundamental_score=None,
                    sentiment_score=sent_score,
                    macro_score=None,
                    risk_score=0.0,
                    signal_details={"overnight": ov.to_dict()},
                )
                arbiter_ctx = {
                    "symbol": sym,
                    "side": "long",
                    "context": "PRECLOSE overnight-hold decision",
                    "weekend_session": weekend_session,
                    "session_gap_calendar_days": session_gap_days,
                    "market_value": abs(float(p.market_value)),
                    "unrealized_plpc": float(p.unrealized_plpc) if hasattr(p, "unrealized_plpc") else 0.0,
                    "current_price": float(tech.price) if tech and tech.price is not None else None,
                    "technical": tech.to_dict() if tech else None,
                    "sentiment": sent.to_dict() if sent else None,
                    "overnight": ov.to_dict(),
                    "market_bias_spy_lateday": round(market_bias, 3),
                    "numeric_decision": num_dec.to_dict(),
                    "exit_triggers": {
                        "preclose_directional_score": round(directional, 3),
                        "hold_threshold": hold_threshold,
                        "weekend_session": weekend_session,
                    },
                    "context_note": (
                        "Decide whether to close this position before the bell. "
                        "Return {action: exit|reduce|hold, confidence: 0..1, reasoning: str}."
                    ),
                }
                verdict = run_exit_arbiter(self.cfg, arbiter_ctx)
                if not verdict:
                    log.critical("[%s] preclose exit-arbiter unavailable — HOLDING (fail-safe)", sym)
                    continue
                ai_action = str(verdict.get("action", "")).strip().lower()
                ai_conf = float(verdict.get("confidence", 0.0) or 0.0)
                ai_reasoning = str(verdict.get("reasoning", ""))[:200]
                model_used = verdict.get("_model", "?")
                # Min-conf for an AI 'exit' verdict to actually execute.
                # On weekend sessions we use a lower bar so a confidence-0.40
                # AI exit is enough to close (vs the 0.55 default). Outside
                # weekends the preclose-specific override (0.50) takes over.
                if weekend_session and weekend_min_exit_conf is not None:
                    min_exit_conf = weekend_min_exit_conf
                else:
                    min_exit_conf = float(self.cfg.get(
                        "overnight", "preclose_exit_arbiter_min_confidence",
                        default=float(self.cfg.get("exit_arbiter", "min_confidence", default=0.55)),
                    ))
                log_decision({
                    "event": "preclose_exit_arbiter", "symbol": sym, "model": model_used,
                    "action": ai_action, "confidence": ai_conf, "reasoning": ai_reasoning,
                    "min_exit_conf_used": round(min_exit_conf, 2),
                    "weekend_session": weekend_session,
                    "triggers": arbiter_ctx["exit_triggers"],
                })
                log.info("[%s] preclose exit-arbiter (model=%s) -> %s conf=%.2f "
                         "(min_exit_conf=%.2f, weekend=%s): %s",
                         sym, model_used, ai_action, ai_conf,
                         min_exit_conf, weekend_session, ai_reasoning)
                report["ai_action"] = ai_action
                report["ai_confidence"] = round(ai_conf, 3)
                if ai_conf < min_exit_conf:
                    log.info("[%s] preclose close vetoed by AI — holding overnight", sym)
                    self._record_preclose_veto(sym)
                    # Veto circuit-breaker: if the AI has held the same name
                    # through 2+ consecutive negative-directional preclose
                    # decisions, force a 50% trim now.
                    if self._veto_circuit_breaker_should_trim(sym, directional):
                        trim_reason = (
                            f"veto-cap trim_50: AI vetoed close "
                            f"{self._preclose_veto_count(sym)}x in a row "
                            f"(directional={directional:+.2f}, last AI: {ai_reasoning})"
                        )
                        log.warning("[%s] %s", sym, trim_reason)
                        if dry_run:
                            exit_results.append({
                                "symbol": sym, "action": "trim_50_dry",
                                "reason": trim_reason, "ai_verdict": verdict,
                            })
                        else:
                            res = self.executor.reduce_position_pct(
                                sym, percentage=50.0, reason=trim_reason,
                            )
                            exit_results.append({
                                **res.to_dict(), "reason": trim_reason,
                                "ai_verdict": verdict,
                            })
                        self._reset_preclose_veto(sym)
                    continue
                if ai_action == "reduce":
                    pct_raw = (
                        verdict.get("percentage")
                        or verdict.get("reduce_pct")
                        or verdict.get("trim_pct")
                    )
                    if pct_raw in (None, "") and verdict.get("size_fraction") not in (None, ""):
                        try:
                            pct_raw = float(verdict.get("size_fraction")) * 100.0
                        except (TypeError, ValueError):
                            pct_raw = None
                    try:
                        reduce_pct = float(pct_raw) if pct_raw not in (None, "") else float(
                            self.cfg.get("overnight", "preclose_reduce_default_pct", default=50)
                        )
                    except (TypeError, ValueError):
                        reduce_pct = 50.0
                    reduce_pct = max(1.0, min(99.0, reduce_pct))
                    reason = (
                        f"preclose AI reduce {reduce_pct:.0f}% "
                        f"(conf={ai_conf:.2f}, model={model_used}): {ai_reasoning}"
                    )
                    if dry_run:
                        exit_results.append({"symbol": sym, "action": "reduce_dry",
                                             "percentage": reduce_pct,
                                             "reason": reason, "ai_verdict": verdict})
                    else:
                        res = self.executor.reduce_position_pct(
                            sym, percentage=reduce_pct, reason=reason,
                        )
                        exit_results.append({**res.to_dict(), "reason": reason,
                                             "ai_verdict": verdict})
                    self._reset_preclose_veto(sym)
                    continue
                if ai_action != "exit":
                    log.info("[%s] preclose close vetoed by AI action=%s — holding overnight",
                             sym, ai_action)
                    self._record_preclose_veto(sym)
                    if self._veto_circuit_breaker_should_trim(sym, directional):
                        trim_reason = (
                            f"veto-cap trim_50: AI vetoed close "
                            f"{self._preclose_veto_count(sym)}x in a row "
                            f"(directional={directional:+.2f}, last AI: {ai_reasoning})"
                        )
                        log.warning("[%s] %s", sym, trim_reason)
                        if dry_run:
                            exit_results.append({
                                "symbol": sym, "action": "trim_50_dry",
                                "reason": trim_reason, "ai_verdict": verdict,
                            })
                        else:
                            res = self.executor.reduce_position_pct(
                                sym, percentage=50.0, reason=trim_reason,
                            )
                            exit_results.append({
                                **res.to_dict(), "reason": trim_reason,
                                "ai_verdict": verdict,
                            })
                        self._reset_preclose_veto(sym)
                    continue
                reason = (
                    f"preclose AI close (conf={ai_conf:.2f}, model={model_used}): {ai_reasoning}"
                )
                if dry_run:
                    exit_results.append({"symbol": sym, "action": "close_dry",
                                         "reason": reason, "ai_verdict": verdict})
                else:
                    res = self.executor.close_position(sym, reason=reason)
                    exit_results.append({**res.to_dict(), "reason": reason, "ai_verdict": verdict})
                    if res.ok:
                        self._clear_position_lifecycle(sym)
                self._reset_preclose_veto(sym)

        # ---------- Find new overnight candidates ----------
        new_executions: list[dict[str, Any]] = []
        cand_reports: list[dict[str, Any]] = []
        # Respect bearish-day halt: if SPY late-day tape is deeply negative, skip new buys.
        halt_bias = float(self.cfg.get("macro", "bearish_halt_score", default=-0.55))
        if enable_new_buys and market_bias <= halt_bias:
            log.warning("Preclose bearish halt: market_bias=%.2f — skipping new overnight buys", market_bias)
            enable_new_buys = False
        if enable_new_buys:
            universe = build_stock_universe(self.cfg)
            tech_top = self.technical_screen(universe, top_n=scan_candidates)
            held_set = {p.symbol for p in positions}
            tech_by_sym: dict[str, TechnicalSignal] = {t.symbol: t for t in tech_top}
            discovery_sources: dict[str, list[str]] = {}
            discovery_meta: dict[str, dict[str, Any]] = {}
            discovery_breakdown: dict[str, int] = {}
            try:
                discovered, discovery_breakdown = discover_candidates(
                    self.cfg,
                    get_market_data(self.cfg),
                    held_symbols=held_set,
                )
                for c in discovered:
                    if c.symbol in held_set or "/" in c.symbol:
                        continue
                    discovery_sources[c.symbol] = list(c.sources)
                    discovery_meta[c.symbol] = {
                        "sector": c.sector,
                        "price": c.price,
                        "change_pct": c.change_pct,
                        "volume": c.volume,
                        "market_cap_usd": c.market_cap_usd,
                        "discovery_priority_score": c.discovery_priority_score,
                        "discovery_priority_reasons": c.discovery_priority_reasons,
                    }
            except Exception as e:
                log.warning("Preclose discovery failed: %s", e)
                discovered = []

            extra_syms = [
                s for s in discovery_sources
                if s not in tech_by_sym and s not in held_set
            ]
            if extra_syms:
                try:
                    bars_extra = self.client.get_stock_bars(extra_syms, lookback_days=252)
                    tech_by_sym.update(technicals_for_bars_df(bars_extra))
                except Exception as e:
                    log.warning("Preclose extra technical enrichment failed: %s", e)

            candidate_syms: list[str] = []
            seen_preclose: set[str] = set()
            for sym in [t.symbol for t in tech_top] + list(discovery_sources.keys()):
                if sym in held_set or sym in seen_preclose or "/" in sym:
                    continue
                if sym not in tech_by_sym:
                    continue
                seen_preclose.add(sym)
                candidate_syms.append(sym)

            def _preclose_rank(sym: str) -> float:
                tech = tech_by_sym[sym]
                sources = set(discovery_sources.get(sym, []))
                source_bonus = 0.0
                if "av_news" in sources:
                    source_bonus += 0.08
                if "tv_breakout" in sources:
                    source_bonus += 0.06
                if "av_gainers" in sources:
                    source_bonus += 0.06
                # No seed/dynamic watchlist or peer-group bonus here. Those
                # sources make the ticker eligible only; the rank must come
                # from actual market/catalyst evidence.
                return float(tech.score) + source_bonus

            candidate_syms.sort(key=_preclose_rank, reverse=True)
            pool_cap = int(self.cfg.get("overnight", "discovery_pool_size", default=45) or 45)
            cand_syms = candidate_syms[:max(scan_candidates, pool_cap)]
            long_biased = []
            for s in cand_syms:
                tech = tech_by_sym[s]
                sources = set(discovery_sources.get(s, []))
                active_catalyst_source = bool(sources.intersection(catalyst_allowed_sources))
                # Normal preclose entries still need positive technical bias.
                # Earnings-catalyst candidates may be flat before the event, so
                # active discovery sources are allowed into scoring even when
                # the daily technical score has not yet turned up.
                if tech.score > 0.05 or active_catalyst_source:
                    long_biased.append(tech)
            intraday_cand = self._fetch_intraday(cand_syms, minutes=5) if cand_syms else None
            news_cand = self.client.get_news(symbols=cand_syms, limit=80, days_back=2) if cand_syms else []
            daily_cand = None
            try:
                daily_cand = self.client.get_stock_bars(cand_syms, lookback_days=30) if cand_syms else None
            except Exception:
                daily_cand = None
            try:
                sector_lookup = sp500_sectors()
            except Exception:
                sector_lookup = {}
            sectors_by_sym = {
                s: (
                    (discovery_meta.get(s) or {}).get("sector")
                    or sector_lookup.get(s)
                    or "Other"
                )
                for s in cand_syms
            }
            sector_momentum_by_sym = compute_sector_momentum(
                daily_cand, cand_syms, sectors_by_sym,
            )

            # When the market tape is leaning down, require higher conviction
            # than the default buy_threshold.
            effective_buy_threshold = (
                bearish_buy_threshold if market_bias < 0 else buy_threshold
            )

            scored: list[tuple[TechnicalSignal, OvernightSignal, dict[str, Any]]] = []
            preclose_ctx_by_sym: dict[str, dict[str, Any]] = {}
            for t in long_biased:
                intraday = self._slice_symbol(intraday_cand, t.symbol)
                sent = score_news_for_symbol(t.symbol, news_cand)
                sent_score = sent.score if sent else 0.0
                ov = score_overnight(t.symbol, intraday, t.score, sent_score, market_bias)
                if not ov:
                    continue
                chart = self._intraday_chart_for(intraday_cand, t.symbol, daily_cand)
                momentum_profile = self._momentum_profile(chart)
                earnings_info = (
                    fetch_earnings(t.symbol, ttl_hours=self.earnings_ttl_hours)
                    if self.earnings_enabled else None
                )
                days_until_earnings = earnings_info.days_until if earnings_info else None
                sources = set(discovery_sources.get(t.symbol, []))
                near_earnings = (
                    days_until_earnings is not None
                    and 0 <= days_until_earnings <= catalyst_lookahead_days
                )
                catalyst_source = bool(sources.intersection(catalyst_allowed_sources))
                catalyst_sentiment = bool(sent_score >= catalyst_min_sentiment)
                earnings_research = None
                earnings_profile = {
                    "near_earnings": False,
                    "entry_allowed": True,
                    "score_adjustment": 0.0,
                    "reasons": ["earnings_disabled_or_not_in_window"],
                }
                if self.earnings_enabled and earnings_info is not None:
                    if near_earnings or "earnings_calendar" in sources:
                        try:
                            earnings_research = compute_earnings_research_score(
                                t.symbol,
                                sentiment_score=sent_score,
                                ttl_hours=float(
                                    self.cfg.get(
                                        "earnings", "research_cache_ttl_hours",
                                        default=12,
                                    ) or 12
                                ),
                            )
                        except Exception as e:
                            log.debug("[%s] preclose earnings research failed: %s", t.symbol, e)
                            earnings_research = {
                                "score": 0.0,
                                "components": {},
                                "available_components": [],
                            }
                    earnings_profile = build_preclose_earnings_profile(
                        earnings_info,
                        earnings_research,
                        sentiment_score=sent_score,
                        catalyst_source=catalyst_source,
                        lookahead_days=catalyst_lookahead_days,
                        min_sentiment=catalyst_min_sentiment,
                        min_research_score=catalyst_min_research,
                        neutral_research_score=float(
                            self.cfg.get("earnings", "research_score_neutral", default=0.0)
                            or 0.0
                        ),
                        event_risk_buy_threshold=catalyst_event_threshold,
                        post_earnings_buy_threshold=catalyst_post_threshold,
                        non_event_buy_threshold=catalyst_non_event_threshold,
                        event_risk_size_multiplier=catalyst_size_multiplier,
                        post_earnings_size_multiplier=min(size_mult, 0.50),
                        unknown_time_is_event_risk=catalyst_unknown_time_is_event,
                    )
                    near_earnings = bool(earnings_profile.get("near_earnings"))
                earnings_catalyst_exception = bool(
                    catalyst_enabled
                    and near_earnings
                    and earnings_profile.get("entry_allowed")
                )
                sector_profile = sector_momentum_by_sym.get(t.symbol, {
                    "sector": sectors_by_sym.get(t.symbol, "Other"),
                    "score": 0.0,
                })
                learning_features = {
                    "adjusted_score": ov.score,
                    "sector": sector_profile.get("sector"),
                    "sources": sorted(sources),
                    "earnings_bucket": (
                        "event_risk" if earnings_profile.get("event_risk_overnight")
                        else "post_earnings" if earnings_profile.get("post_earnings_session")
                        else "near_earnings" if near_earnings
                        else "no_near_earnings"
                    ),
                }
                learned_edge = estimate_overnight_edge(self.cfg, t.symbol, learning_features)
                atr_pct = (
                    float(t.atr) / float(t.price)
                    if t.atr is not None and t.price not in (None, 0)
                    else None
                )
                edge = build_preclose_edge(
                    ov,
                    chart=chart,
                    momentum_profile=momentum_profile,
                    sector_momentum=sector_profile,
                    earnings_profile=earnings_profile,
                    learned_edge=learned_edge,
                    atr_pct=atr_pct,
                    weights=edge_weights,
                )
                report_entry = {
                    "symbol": t.symbol,
                    "sector": sector_profile.get("sector"),
                    "tech_score": round(t.score, 3),
                    "rsi": round(float(t.rsi), 1) if t.rsi is not None else None,
                    "overnight": ov.to_dict(),
                    "overnight_edge": edge,
                    "intraday_chart": chart,
                    "momentum_profile": momentum_profile,
                    "earnings": earnings_info.to_dict() if earnings_info else None,
                    "earnings_research": earnings_research,
                    "earnings_profile": earnings_profile,
                    "earnings_catalyst_exception": {
                        "enabled": earnings_catalyst_exception,
                        "near_earnings": near_earnings,
                        "days_until_earnings": days_until_earnings,
                        "time_of_day": (
                            earnings_info.time_of_day if earnings_info else None
                        ),
                        "event_risk_overnight": earnings_profile.get("event_risk_overnight"),
                        "post_earnings_session": earnings_profile.get("post_earnings_session"),
                        "catalyst_source": catalyst_source,
                        "catalyst_sentiment": catalyst_sentiment,
                        "research_score": earnings_profile.get("research_score"),
                        "buy_threshold": (
                            earnings_profile.get("threshold_floor")
                            or catalyst_buy_threshold
                        ),
                        "size_multiplier": (
                            earnings_profile.get("size_multiplier")
                            or catalyst_size_multiplier
                        ),
                        "reasons": earnings_profile.get("reasons", []),
                    },
                    "discovery_sources": discovery_sources.get(t.symbol, []),
                    "discovery_meta": discovery_meta.get(t.symbol, {}),
                }
                preclose_ctx_by_sym[t.symbol] = report_entry
                # Phase 5 (2026-05-05): tiered RSI gate. The flat 78-cap on
                # 2026-05-05 blocked 17 names — including most of the day's
                # strongest performers — even though macro was risk-on
                # (breadth 69%, score +0.28). Tier the cap so genuine
                # leaders in a momentum tape still qualify, but extreme
                # overbought (RSI > 85) always skips.
                rsi_extreme_cap = float(
                    self.cfg.get("preclose", "rsi_extreme_cap", default=85.0) or 85.0
                )
                rsi_leader_override = bool(
                    self.cfg.get("preclose", "rsi_leader_override", default=True)
                )
                rsi_macro_floor = float(
                    self.cfg.get("preclose", "rsi_macro_floor", default=0.20) or 0.20
                )
                if t.rsi is not None and t.rsi > rsi_extreme_cap:
                    report_entry["skipped"] = (
                        f"rsi {t.rsi:.1f} > {rsi_extreme_cap:.1f} (extreme overbought, no override)"
                    )
                    cand_reports.append(report_entry)
                    log.info(
                        "[%s] overnight skip: RSI %.1f > %.1f (extreme — no override)",
                        t.symbol, t.rsi, rsi_extreme_cap,
                    )
                    continue
                if t.rsi is not None and t.rsi > max_rsi_new_buy:
                    # Try the leader/macro override before skipping.
                    macro_ok = (market_bias >= rsi_macro_floor)
                    momentum_ok = (
                        getattr(t, "score", 0) is not None
                        and float(t.score or 0) > 0
                        and float(getattr(t, "trend", 0) or 0) > 0
                    )
                    if (
                        rsi_leader_override
                        and macro_ok
                        and momentum_ok
                    ):
                        log.info(
                            "[%s] preclose RSI %.1f > %.1f BUT macro=%.2f & "
                            "tech.score=%.2f, tech.trend=%.2f — leader override",
                            t.symbol, t.rsi, max_rsi_new_buy, market_bias,
                            float(t.score or 0), float(getattr(t, "trend", 0) or 0),
                        )
                        report_entry["rsi_leader_override"] = {
                            "rsi": round(float(t.rsi), 1),
                            "rsi_cap": float(max_rsi_new_buy),
                            "rsi_extreme_cap": rsi_extreme_cap,
                            "market_bias": round(float(market_bias), 3),
                            "macro_floor": rsi_macro_floor,
                            "tech_score": round(float(t.score or 0), 3),
                            "tech_trend": round(float(getattr(t, "trend", 0) or 0), 3),
                        }
                        # Fall through and let the candidate score normally.
                    else:
                        report_entry["skipped"] = f"rsi {t.rsi:.1f} > {max_rsi_new_buy:.1f}"
                        cand_reports.append(report_entry)
                        log.info(
                            "[%s] overnight skip: RSI %.1f > %.1f "
                            "(macro_ok=%s momentum_ok=%s)",
                            t.symbol, t.rsi, max_rsi_new_buy, macro_ok, momentum_ok,
                        )
                        continue
                if near_earnings and not earnings_catalyst_exception:
                    report_entry["skipped"] = (
                        "near earnings without research-approved preclose catalyst exception"
                    )
                    cand_reports.append(report_entry)
                    log.info(
                        "[%s] overnight skip: earnings in %s day(s) without "
                        "research-approved catalyst exception (%s)",
                        t.symbol, days_until_earnings,
                        ",".join(earnings_profile.get("reasons", [])),
                    )
                    continue
                symbol_buy_threshold = (
                    max(
                        effective_buy_threshold,
                        float(
                            earnings_profile.get("threshold_floor")
                            or catalyst_buy_threshold
                        ),
                    )
                    if earnings_catalyst_exception
                    else effective_buy_threshold
                )
                report_entry["buy_threshold"] = round(float(symbol_buy_threshold), 3)
                edge_score = float(edge.get("adjusted_score", ov.score))
                if edge_score < symbol_buy_threshold:
                    report_entry["skipped"] = (
                        f"edge {edge_score:.2f} < threshold {symbol_buy_threshold:.2f}"
                    )
                    cand_reports.append(report_entry)
                    continue
                cand_reports.append(report_entry)
                scored.append((t, ov, edge))

            scored.sort(key=lambda x: float(x[2].get("adjusted_score", x[1].score)), reverse=True)
            picks = scored[:max_new]
            log.info(
                "Preclose new-buy picks: %d (from %d scored, threshold=%.2f, "
                "earnings_catalyst_threshold=%.2f, market_bias=%+.2f, discovery=%s)",
                len(picks), len(cand_reports), effective_buy_threshold,
                catalyst_buy_threshold, market_bias, discovery_breakdown,
            )

            # Refresh positions after closes
            if not dry_run and exit_results:
                positions = self.client.get_positions()

            # Sequential cash accounting: deduct each confirmed buy from the
            # running liquidity figure (real cash + SPY cash-proxy) so two
            # concurrent preclose buys can't both pass the 5% floor check.
            cash_floor = equity * self.risk.cash_reserve_pct
            if sequential_cash and not dry_run:
                try:
                    acct_now = self.client.get_account()
                    live_cash = float(acct_now.cash)
                except Exception:
                    live_cash = float(account.cash)
                proxy_value = 0.0
                if self.cash_proxy_enabled:
                    proxy = self._get_proxy_position(positions)
                    if proxy:
                        proxy_value = abs(float(proxy.market_value))
                available_liquidity = live_cash + proxy_value - cash_floor
            else:
                available_liquidity = float("inf")

            for tech, ov, edge in picks:
                price = tech.price
                atr = tech.atr
                if not price or not atr:
                    continue
                preclose_ctx = preclose_ctx_by_sym.get(tech.symbol, {})

                # Opus 4.7 entry arbiter must approve every overnight buy.
                num_dec = self.engine.decide(
                    symbol=tech.symbol,
                    technical_score=tech.score,
                    fundamental_score=None,
                    sentiment_score=None,
                    macro_score=None,
                    risk_score=0.0,
                    signal_details={
                        "technical": tech.to_dict(),
                        "overnight": ov.to_dict(),
                        "overnight_edge": edge,
                    },
                )
                symbol_threshold = float(
                    preclose_ctx.get("buy_threshold")
                    or effective_buy_threshold
                )
                arbiter_ctx = {
                    "symbol": tech.symbol,
                    "context": "PRECLOSE new-buy overnight candidate",
                    "time_horizon": {
                        "minutes_to_close": self._scan_time_context().get("minutes_to_close"),
                        "must_evaluate": [
                            "remaining upside before today's close",
                            "overnight gap upside",
                            "next-session continuation upside",
                        ],
                        "higher_threshold_applied": symbol_threshold,
                    },
                    "current_price": price,
                    "position_status": "not_owned",
                    "technical_analyst": tech.to_dict(),
                    "overnight_signal": ov.to_dict(),
                    "overnight_edge": edge,
                    "intraday_chart": preclose_ctx.get("intraday_chart"),
                    "momentum_profile": preclose_ctx.get("momentum_profile"),
                    "earnings": preclose_ctx.get("earnings"),
                    "earnings_research": preclose_ctx.get("earnings_research"),
                    "earnings_profile": preclose_ctx.get("earnings_profile"),
                    "preclose_earnings_catalyst_exception": preclose_ctx.get(
                        "earnings_catalyst_exception"
                    ),
                    "discovery_sources": preclose_ctx.get("discovery_sources", []),
                    "discovery_meta": preclose_ctx.get("discovery_meta", {}),
                    "market_bias_spy_lateday": round(market_bias, 3),
                    "fundamental_analyst": {"note": "not computed for preclose speed"},
                    "sentiment_analyst": {"note": "embedded in overnight signal"},
                    "numeric_decision": num_dec.to_dict(),
                    "portfolio": {
                        "equity": equity, "positions_count": len(positions),
                    },
                    "risk_constraints": {
                        "max_position_pct": float(self.risk.max_position_pct),
                        "cash_reserve_pct": float(self.risk.cash_reserve_pct),
                        "hard_stop_loss_pct": float(self.cfg.get("risk", "hard_stop_loss_pct", default=0.01)),
                    },
                }
                verdict = run_entry_arbiter_single(self.cfg, arbiter_ctx)
                if not verdict:
                    log.critical("[%s] preclose entry arbiter unavailable — skipping", tech.symbol)
                    continue
                ai_action = str(verdict.get("final_action", "")).strip().lower()
                ai_conf = float(verdict.get("confidence", 0.0) or 0.0)
                ai_thesis = str(verdict.get("thesis", ""))[:200]
                model_used = verdict.get("_model", "?")
                log_decision({
                    "event": "preclose_entry_arbiter", "symbol": tech.symbol,
                    "model": model_used, "action": ai_action,
                    "confidence": ai_conf, "thesis": ai_thesis,
                })
                log.info("[%s] preclose entry-arbiter (model=%s) -> %s conf=%.2f: %s",
                         tech.symbol, model_used, ai_action, ai_conf, ai_thesis)
                if ai_action != "buy" or ai_conf < float(
                    self.cfg.get("risk", "min_confidence", default=0.40)
                ):
                    log.info("[%s] preclose buy vetoed by AI — skipping", tech.symbol)
                    continue

                # Size based on AI-approved confidence, not raw ov.score.
                catalyst_ctx = preclose_ctx.get("earnings_catalyst_exception") or {}
                earnings_profile = preclose_ctx.get("earnings_profile") or {}
                effective_size_mult = (
                    min(
                        size_mult,
                        float(
                            earnings_profile.get("size_multiplier")
                            or catalyst_size_multiplier
                        ),
                    )
                    if catalyst_ctx.get("enabled")
                    else size_mult
                )
                learned_ctx = edge.get("learned_edge") or {}
                risk_flags = set(edge.get("risk_flags") or [])
                edge_size_scalar = 1.0
                gap_down_risk = float(learned_ctx.get("gap_down_risk") or 0.0)
                if gap_down_risk >= float(
                    self.cfg.get(
                        "overnight", "edge_sizing", "gap_down_risk_threshold",
                        default=0.35,
                    ) or 0.35
                ):
                    edge_size_scalar *= float(
                        self.cfg.get(
                            "overnight", "edge_sizing", "gap_down_risk_multiplier",
                            default=0.65,
                        ) or 0.65
                    )
                if risk_flags.intersection({
                    "gap_only_risk", "fading_into_close",
                    "high_atr_gap_risk", "earnings_event_overnight",
                }):
                    edge_size_scalar *= float(
                        self.cfg.get(
                            "overnight", "edge_sizing", "risk_flag_multiplier",
                            default=0.80,
                        ) or 0.80
                    )
                edge_score = float(edge.get("adjusted_score", ov.score))
                if (
                    edge_score >= symbol_threshold + float(
                        self.cfg.get(
                            "overnight", "edge_sizing", "boost_score_margin",
                            default=0.20,
                        ) or 0.20
                    )
                    and not risk_flags
                ):
                    edge_size_scalar *= float(
                        self.cfg.get(
                            "overnight", "edge_sizing", "strong_edge_multiplier",
                            default=1.15,
                        ) or 1.15
                    )
                edge_size_scalar = min(
                    float(
                        self.cfg.get(
                            "overnight", "edge_sizing", "max_scalar",
                            default=1.25,
                        ) or 1.25
                    ),
                    max(
                        float(
                            self.cfg.get(
                                "overnight", "edge_sizing", "min_scalar",
                                default=0.40,
                            ) or 0.40
                        ),
                        edge_size_scalar,
                    ),
                )
                effective_size_mult *= edge_size_scalar
                preclose_ctx["effective_size_multiplier"] = round(effective_size_mult, 3)
                sizing = self.risk.size_position(
                    symbol=tech.symbol, side="buy",
                    price=price, atr=atr,
                    confidence=ai_conf * effective_size_mult,
                    equity=equity,
                    existing_positions=positions,
                )
                if not sizing:
                    continue
                if not dry_run:
                    preflight_ok, preflight = self.executor.preflight_buy(
                        symbol=tech.symbol,
                        qty=sizing.qty,
                        entry_price=sizing.entry,
                        stop_loss=sizing.stop_loss,
                        take_profit=sizing.take_profit,
                    )
                    if not preflight_ok:
                        log.warning("[%s] preclose buy preflight rejected: %s",
                                    tech.symbol, preflight.get("reject_reason"))
                        new_executions.append({
                            "sizing": sizing.to_dict(),
                            "status": "skipped",
                            "message": "execution_preflight_rejected",
                            "execution_preflight": preflight,
                        })
                        continue
                    submitted_qty = float(preflight.get("submitted_qty") or sizing.qty)
                    if abs(submitted_qty - float(sizing.qty)) > 1e-9 and sizing.entry:
                        sizing = replace(
                            sizing,
                            qty=submitted_qty,
                            notional=round(submitted_qty * float(sizing.entry), 2),
                            risk_usd=round(
                                submitted_qty * (float(sizing.entry) - float(sizing.stop_loss)),
                                2,
                            ),
                            limits={**dict(sizing.limits), "execution_preflight": preflight},
                        )
                    else:
                        sizing.limits["execution_preflight"] = preflight
                if sequential_cash and not dry_run:
                    if sizing.notional > available_liquidity:
                        log.info(
                            "[%s] overnight skip: notional $%.0f > available liquidity $%.0f "
                            "(preserving cash_reserve_pct floor)",
                            tech.symbol, sizing.notional, max(0.0, available_liquidity),
                        )
                        continue
                    available_liquidity -= sizing.notional
                decision_obj = TradeDecision(
                    symbol=tech.symbol,
                    action="buy",
                    confidence=ai_conf,
                    combined_score=edge_score,
                    signal_scores={
                        "technical": tech.score,
                        "overnight": ov.score,
                        "overnight_edge": edge_score,
                    },
                    signal_details={
                        "technical": tech.to_dict(), "overnight": ov.to_dict(),
                        "overnight_edge": edge,
                        "ai_verdict": verdict,
                    },
                    reasoning=[
                        f"preclose AI-approved buy conf={ai_conf:.2f} (model={model_used})",
                        f"edge={edge_score:+.2f} raw_ov={ov.score:+.2f} close_strength={ov.close_strength:+.2f}",
                        f"risk_flags={','.join(edge.get('risk_flags') or []) or 'none'}",
                        f"thesis: {ai_thesis}",
                    ],
                )
                if dry_run:
                    log.info("[DRY] Would open overnight %s", sizing.to_dict())
                    new_executions.append({"dry_run": True, "sizing": sizing.to_dict(),
                                           "decision": decision_obj.to_dict()})
                else:
                    # Ensure real cash covers the notional; sell SPY if needed.
                    if not self._ensure_cash_for(
                        sizing.notional,
                        equity,
                        floor_pct=float(self.risk.cash_reserve_pct),
                    ):
                        if sequential_cash:
                            available_liquidity += sizing.notional
                        log.warning("[%s] preclose buy skipped: insufficient confirmed cash",
                                    tech.symbol)
                        new_executions.append({
                            "sizing": sizing.to_dict(),
                            "decision": decision_obj.to_dict(),
                            "status": "skipped",
                            "message": "insufficient_confirmed_cash",
                        })
                        continue
                    result = self.executor.execute(decision_obj, sizing)
                    new_executions.append({
                        "sizing": sizing.to_dict(),
                        "decision": decision_obj.to_dict(),
                        "execution": result.to_dict(),
                        **result.to_dict(),  # keep top-level symbol/status for easy reads
                    })
                    if result.ok:
                        self._record_position_entry(
                            tech.symbol,
                            source="preclose",
                            execution=result.to_dict(),
                            context={
                                "reason": "; ".join(decision_obj.reasoning),
                                "confidence": ai_conf,
                                "ai_action": ai_action,
                                "opportunity_score": round(float(edge_score) * 100, 1),
                                "raw_overnight_score": round(float(ov.score) * 100, 1),
                                "risk_flags": edge.get("risk_flags") or [],
                            },
                        )
                    if not result.ok and sequential_cash:
                        # Refund the liquidity we pre-deducted so subsequent picks aren't starved.
                        available_liquidity += sizing.notional
                        log.warning("[%s] preclose buy did not fill — refunding $%.0f to liquidity budget",
                                    tech.symbol, sizing.notional)
                    positions = self.client.get_positions()

        weekend_protection = None
        if weekend_session:
            if not dry_run:
                try:
                    positions = self.client.get_positions()
                except Exception:
                    pass
            weekend_protection = self._enforce_weekend_protection(
                positions,
                dry_run=dry_run,
            )
            for action in (weekend_protection.get("actions") or []):
                if action.get("execution"):
                    exit_results.append({
                        **(action.get("execution") or {}),
                        "symbol": action.get("symbol"),
                        "reason": action.get("reason"),
                        "weekend_protection": action,
                    })
            if not dry_run:
                try:
                    positions = self.client.get_positions()
                except Exception:
                    pass

        # Park any remaining idle cash in SPY for overnight carry.
        cash_proxy_action = None if dry_run else self._sweep_cash_to_proxy(equity)
        trade_learning_end = self._resolve_trade_learning("preclose_end")

        summary = {
            "ts": pd.Timestamp.utcnow().isoformat(),
            "equity": equity,
            "positions_count": len(positions),
            "market_bias": round(market_bias, 3),
            "weekend_session": weekend_session,
            "session_gap_calendar_days": session_gap_days,
            "hold_reports": hold_reports,
            "exits": exit_results,
            "candidate_reports": cand_reports,
            "new_executions": new_executions,
            "weekend_protection": weekend_protection,
            "cash_proxy": cash_proxy_action,
            "trade_learning": {
                "start": trade_learning_start,
                "end": trade_learning_end,
            },
            "overnight_learning": {
                "start": overnight_learning_start,
            },
            "thresholds": {
                "hold": hold_threshold, "buy": buy_threshold,
                "max_new": max_new, "size_mult": size_mult,
                "weekend_session": weekend_session,
            },
        }
        try:
            summary["overnight_learning"]["record"] = record_preclose_candidates(
                self.cfg,
                summary,
                dry_run=dry_run,
            )
        except Exception as e:
            log.warning("overnight-learning record failed at preclose end: %s", e)
            summary["overnight_learning"]["record"] = {"error": str(e)}
        # Per-decision tally for the auditable summary line — surfaces
        # "what scored, what held, what got AI-vetoed, what closed for earnings"
        # at one glance so a missing intraday-data path doesn't go unnoticed.
        tally: dict[str, int] = {
            "held": len(hold_reports),
            "scored": 0,
            "hold": 0,
            "close": 0,
            "no_data": 0,
            "earnings_close": 0,
            "earnings_trim_50": 0,
            "earnings_hold": 0,
            "ai_vetoed_held": 0,
            "veto_cap_trim": 0,
        }
        for rep in hold_reports:
            d = rep.get("decision", "")
            if d == "hold":
                tally["scored"] += 1
                tally["hold"] += 1
            elif d == "close":
                tally["scored"] += 1
                tally["close"] += 1
            elif d == "hold_no_data":
                tally["no_data"] += 1
            elif d == "close_earnings_gate":
                tally["earnings_close"] += 1
            elif d == "trim_50_earnings_gate":
                tally["earnings_trim_50"] += 1
            elif d == "hold_earnings_gate":
                tally["earnings_hold"] += 1
        # AI-vetoed holds are reports where decision was "close" but no exit
        # row exists for that symbol (i.e., AI returned hold and we kept it).
        exited_syms = {x.get("symbol") for x in exit_results if x.get("symbol")}
        for rep in hold_reports:
            if rep.get("decision") == "close" and rep.get("symbol") not in exited_syms:
                tally["ai_vetoed_held"] += 1
        for x in exit_results:
            if "veto-cap" in str(x.get("reason", "")):
                tally["veto_cap_trim"] += 1
        summary["tally"] = tally
        _save_research("preclose", summary)
        log.info(
            "Preclose summary: held=%d scored=%d hold=%d close=%d no_data=%d "
            "earnings(close=%d trim50=%d hold=%d) ai_vetoed=%d veto_cap_trim=%d "
            "exits=%d new_buys=%d weekend=%s",
            tally["held"], tally["scored"], tally["hold"], tally["close"],
            tally["no_data"], tally["earnings_close"], tally["earnings_trim_50"],
            tally["earnings_hold"], tally["ai_vetoed_held"], tally["veto_cap_trim"],
            len(exit_results), len(new_executions), weekend_session,
        )
        log.info("Preclose complete: closes=%d, new_buys=%d",
                 len(exit_results), len(new_executions))
        return summary
