"""End-to-end pipeline: gather signals → decide → size → execute. Entry + exit."""
from __future__ import annotations
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from src.ai_pipeline import AIVerdict, run_ai_on_candidates
from src.ai_research import AIResearcher
from src.alpaca_client import AlpacaClient
from src.config import Config
from src.decision import DecisionEngine, TradeDecision
from src.executor import TradeExecutor
from src.fundamentals import compute_fundamentals
from src.journal import log_decision
from src.kill_switch import check_kill_switch
from src.macro import MacroSignal, compute_macro
from src.overnight import OvernightSignal, market_bias_from_spy, score_overnight
from src.risk import RiskManager
from src.sentiment import score_news_for_symbol
from src.technicals import TechnicalSignal, compute_technicals, technicals_for_bars_df
from src.universe import build_stock_universe, crypto_universe

log = logging.getLogger(__name__)

RESEARCH_DIR = Path(__file__).resolve().parents[1] / "data" / "research"
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)


def _save_research(name: str, payload: dict[str, Any]) -> Path:
    ts = pd.Timestamp.utcnow().strftime("%Y%m%dT%H%M%S")
    path = RESEARCH_DIR / f"{ts}_{name}.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


class TradingOrchestrator:
    def __init__(self, config: Config):
        self.cfg = config
        self.client = AlpacaClient(config)
        self.risk = RiskManager(config)
        self.engine = DecisionEngine(config)
        self.executor = TradeExecutor(self.client, config, is_crypto=False)
        self.crypto_executor = TradeExecutor(self.client, config, is_crypto=True)
        self.ai = AIResearcher(config)
        self.cash_proxy_enabled = bool(config.get("cash_proxy", "enabled", default=False))
        self.cash_proxy_symbol = str(config.get("cash_proxy", "symbol", default="SPY"))
        self.cash_proxy_min = float(config.get("cash_proxy", "min_rebalance_usd", default=500))

    def _is_cash_proxy(self, symbol: str) -> bool:
        return self.cash_proxy_enabled and symbol == self.cash_proxy_symbol

    def _get_proxy_position(self, positions):
        for p in positions:
            if self._is_cash_proxy(p.symbol):
                return p
        return None

    def _ensure_cash_for(self, notional: float, equity: float) -> bool:
        """Before opening a new position: if real cash is below (notional + floor),
        sell enough cash-proxy (SPY) to cover. Returns True if funding is now ok."""
        if not self.cash_proxy_enabled:
            return True
        try:
            account = self.client.get_account()
            cash = float(account.cash)
        except Exception as e:
            log.warning("ensure_cash: account fetch failed: %s", e)
            return True  # let downstream order fail if truly insufficient
        floor = equity * self.risk.cash_reserve_min_pct
        shortfall = (notional + floor) - cash
        if shortfall <= 0:
            return True
        positions = self.client.get_positions()
        proxy = self._get_proxy_position(positions)
        if not proxy:
            log.info("ensure_cash: shortfall $%.0f but no %s held", shortfall, self.cash_proxy_symbol)
            return cash >= notional  # might still be ok if floor is the only issue
        proxy_value = abs(float(proxy.market_value))
        sell_amt = min(shortfall + 50, proxy_value)  # tiny buffer
        if sell_amt < 1:
            return True
        try:
            self.client.submit_notional(self.cash_proxy_symbol, sell_amt, side="sell")
            log.info("Sold $%.0f of %s to fund trade (shortfall=$%.0f)",
                     sell_amt, self.cash_proxy_symbol, shortfall)
            return True
        except Exception as e:
            log.warning("Cash-proxy sell failed: %s", e)
            return False

    def _sweep_cash_to_proxy(self, equity: float) -> dict[str, Any] | None:
        """After a scan's trades settle: park cash above the true-cash floor in SPY."""
        if not self.cash_proxy_enabled:
            return None
        try:
            account = self.client.get_account()
            cash = float(account.cash)
        except Exception as e:
            log.warning("sweep: account fetch failed: %s", e)
            return None
        floor = equity * self.risk.cash_reserve_pct
        excess = cash - floor
        if excess < self.cash_proxy_min:
            return None
        try:
            self.client.submit_notional(self.cash_proxy_symbol, excess, side="buy")
            log.info("Swept $%.0f idle cash into %s (floor=$%.0f)",
                     excess, self.cash_proxy_symbol, floor)
            return {"action": "buy_proxy", "symbol": self.cash_proxy_symbol,
                    "notional": round(excess, 2)}
        except Exception as e:
            log.warning("Cash-proxy buy failed: %s", e)
            return None

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

        details: dict[str, Any] = {
            "technical": tech.to_dict(),
            "sentiment": sent.to_dict(),
            "macro": macro.to_dict(),
        }
        if fund:
            details["fundamental"] = fund.to_dict()

        # Risk alignment: penalize longs in risk_off regime, shorts in risk_on
        risk_score = 0.0
        if macro.regime == "risk_off" and tech.score > 0:
            risk_score = -0.3
        elif macro.regime == "risk_on" and tech.score < 0:
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
                    "sent_map": {}, "numeric": {}}
        try:
            bars = self.client.get_stock_bars(symbols, lookback_days=252)
        except Exception as e:
            log.warning("Portfolio signals bars fetch failed: %s", e)
            return {"positions": positions, "holdings": holdings, "tech_map": {},
                    "sent_map": {}, "numeric": {}}
        tech_map = technicals_for_bars_df(bars)
        news = self.client.get_news(symbols=symbols, limit=80, days_back=3)
        sent_map: dict[str, Any] = {}
        numeric: dict[str, TradeDecision] = {}
        for p in holdings:
            sym = p.symbol
            tech = tech_map.get(sym)
            if tech is None:
                continue
            sent = score_news_for_symbol(sym, news)
            sent_map[sym] = sent
            fund = compute_fundamentals(sym)
            details: dict[str, Any] = {
                "technical": tech.to_dict(),
                "sentiment": sent.to_dict(),
                "macro": macro.to_dict(),
            }
            if fund:
                details["fundamental"] = fund.to_dict()
            risk_score = 0.0
            if macro.regime == "risk_off" and tech.score > 0:
                risk_score = -0.3
            elif macro.regime == "risk_on" and tech.score < 0:
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
                "sent_map": sent_map, "numeric": numeric, "news": news}

    # ---------- exits ----------
    def evaluate_exits(
        self,
        macro: MacroSignal,
        portfolio: dict[str, Any] | None = None,
    ) -> list[tuple[str, str]]:
        """Return list of (symbol, reason) to close. Uses pre-fetched portfolio
        signals if provided; otherwise fetches its own.
        """
        closes: list[tuple[str, str]] = []
        portfolio = portfolio or self._portfolio_signals(macro)
        holdings = portfolio.get("holdings", [])
        tech_map = portfolio.get("tech_map", {})
        sent_map = portfolio.get("sent_map", {})
        if not holdings or not tech_map:
            return closes
        stall_thr = float(self.cfg.get("risk", "exit_stall_threshold", default=0.10))
        for p in holdings:
            if p.symbol not in tech_map:
                continue
            tech = tech_map[p.symbol]
            sent = sent_map.get(p.symbol)
            sent_score = sent.score if sent else 0.0
            is_long = p.side.value == "long" if hasattr(p.side, "value") else p.side == "long"
            plpc = float(p.unrealized_plpc) if hasattr(p, "unrealized_plpc") else 0.0
            flipped = (is_long and tech.score < -0.3) or (not is_long and tech.score > 0.3)
            bad_news = (is_long and sent_score < -0.5) or (not is_long and sent_score > 0.5)
            stalled = (is_long and tech.score < stall_thr) or (not is_long and tech.score > -stall_thr)
            if flipped:
                closes.append((p.symbol, f"technical flipped (score={tech.score:.2f})"))
            elif bad_news:
                closes.append((p.symbol, f"sentiment flipped (score={sent_score:.2f})"))
            elif stalled:
                closes.append((
                    p.symbol,
                    f"momentum stalled (tech={tech.score:.2f}, pnl={plpc:+.1%}) — freeing capital",
                ))
        return closes

    # ---------- rebalance ----------
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
        return asyncio.run(_all())

    def run_rebalance(
        self,
        macro: MacroSignal,
        portfolio: dict[str, Any],
        equity: float,
        dry_run: bool = False,
        allow_adds: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute conviction-weighted partial rebalance on held positions.
        Returns list of applied action dicts. If allow_adds=False, only trims run
        (bearish-halt mode unless a position clears the high-conviction override).
        """
        from src.rebalance import (
            compute_rebalance_plan, load_tech_cache, save_tech_cache,
            select_ai_rerun_symbols,
        )
        if not bool(self.cfg.get("rebalance", "enabled", default=True)):
            return []
        holdings = portfolio.get("holdings", [])
        tech_map = portfolio.get("tech_map", {})
        sent_map = portfolio.get("sent_map", {})
        numeric = portfolio.get("numeric", {})
        if not holdings or not tech_map:
            return []

        # --- AI re-analysis on positions whose scores moved materially ---
        cache = load_tech_cache()
        tech_scores = {s: t.score for s, t in tech_map.items()}
        score_delta_threshold = float(self.cfg.get("rebalance", "rerun_ai_on_score_delta", default=0.15))
        max_reruns = int(self.cfg.get("rebalance", "max_ai_reruns_per_scan", default=8))
        ai_rerun_symbols = select_ai_rerun_symbols(
            holdings, tech_scores, cache, score_delta_threshold, max_reruns,
        )
        ai_verdicts: dict[str, Any] = {}
        if ai_rerun_symbols:
            log.info("Rebalance: re-running AI on %d held positions (material score change): %s",
                     len(ai_rerun_symbols), ai_rerun_symbols)
            portfolio_ctx = {
                "equity": equity,
                "positions_count": len(holdings),
                "context": "held-position rebalance review",
            }
            ai_verdicts = self._run_ai_on_held(
                ai_rerun_symbols, numeric, macro, portfolio_ctx,
            )

        # --- Build plan ---
        plan = compute_rebalance_plan(
            positions=holdings,
            tech_map=tech_map,
            sent_map=sent_map,
            numeric_decisions=numeric,
            ai_verdicts=ai_verdicts,
            equity=equity,
            config=self.cfg,
            cash_proxy_symbol=self.cash_proxy_symbol if self.cash_proxy_enabled else None,
        )

        # --- Bearish-day filter: adds require high-conviction override ---
        if not allow_adds:
            override = float(self.cfg.get("rebalance", "bearish_override_conf", default=0.85))
            filtered = []
            for a in plan:
                # side="sell" is always a trim for longs (or a short-scale-up for shorts).
                # Distinguish trim-of-long from short-scale-up via blended conf threshold used;
                # trims have blended < trim_floor, scale-ups have blended >= add_floor.
                trim_floor = float(self.cfg.get("rebalance", "trim_confidence_floor", default=0.40))
                is_trim = a.blended_confidence < trim_floor
                if is_trim:
                    filtered.append(a)
                elif a.blended_confidence >= override:
                    filtered.append(a)
                    log.info("[%s] bearish-day add allowed via high-conviction override (%.2f >= %.2f)",
                             a.symbol, a.blended_confidence, override)
                else:
                    log.info("[%s] bearish-day: skipping add (conf=%.2f < override=%.2f)",
                             a.symbol, a.blended_confidence, override)
            plan = filtered

        log.info("Rebalance plan: %d actions (%d trims, %d adds)",
                 len(plan),
                 sum(1 for a in plan if a.side == "sell" and a.blended_confidence < 0.5),
                 sum(1 for a in plan if a.side == "buy" or (a.side == "sell" and a.blended_confidence >= 0.5)))

        # --- Execute ---
        results: list[dict[str, Any]] = []
        for a in plan:
            if dry_run:
                log.info("[DRY] Rebalance %s", a.to_dict())
                results.append({"dry_run": True, **a.to_dict()})
                continue
            # Adds: ensure real cash via SPY cash-proxy sale
            if a.side == "buy":
                self._ensure_cash_for(a.delta_notional, equity)
            exec_result = self.executor.partial_trade(
                symbol=a.symbol, side=a.side,
                delta_notional=a.delta_notional,
                reason=a.reason,
            )
            results.append({**a.to_dict(), "execution": exec_result.to_dict()})

        # --- Update tech-score cache ---
        for sym, score in tech_scores.items():
            cache[sym] = float(score)
        # Prune stale entries
        held_syms = {p.symbol for p in holdings}
        cache = {s: v for s, v in cache.items() if s in held_syms}
        save_tech_cache(cache)

        return results

    # ---------- halt-day conservative exits ----------
    def _halt_day_exits(
        self,
        portfolio: dict[str, Any],
        macro: MacroSignal,
        equity: float,
        dry_run: bool,
    ) -> list[dict[str, Any]]:
        """On kill-switch halt, keep stop-losses live and no new entries — but still
        run AI over held positions and close any where AI strongly recommends exiting
        (profit-lock or damage control). Returns execution result dicts.
        """
        if not bool(self.cfg.get("halt_exits", "enabled", default=True)):
            return []
        if not self.ai.available():
            log.info("Halt-day AI exits skipped: AI unavailable")
            return []
        holdings = portfolio.get("holdings", [])
        numeric = portfolio.get("numeric", {})
        if not holdings:
            return []
        portfolio_ctx = {
            "equity": equity,
            "positions_count": len(holdings),
            "context": "HALT-DAY: kill-switch active, evaluating for conservative exits only",
        }
        syms = [p.symbol for p in holdings if p.symbol in numeric]
        log.info("Halt-day: asking AI about %d held positions for profit-taking / damage-control exits",
                 len(syms))
        verdicts = self._run_ai_on_held(syms, numeric, macro, portfolio_ctx)
        min_conf = float(self.cfg.get("halt_exits", "min_ai_confidence", default=0.60))
        results: list[dict[str, Any]] = []
        for p in holdings:
            v = verdicts.get(p.symbol)
            if not v:
                continue
            is_long = p.side.value == "long" if hasattr(p.side, "value") else p.side == "long"
            # AI says close if: for long, final_action in {sell_short, pass-with-low-conf}
            # OR explicit exit recommendation. We treat "sell_short" on a long
            # or "buy" on a short as "close".
            should_close = False
            reason = ""
            if is_long and v.final_action == "sell_short" and v.ai_confidence >= min_conf:
                should_close = True
                reason = f"halt-day AI close (flip to short, conf={v.ai_confidence:.2f}): {v.thesis[:100]}"
            elif not is_long and v.final_action == "buy" and v.ai_confidence >= min_conf:
                should_close = True
                reason = f"halt-day AI close (flip to long, conf={v.ai_confidence:.2f}): {v.thesis[:100]}"
            if should_close:
                log.info("[%s] halt-day close approved by AI: %s", p.symbol, reason)
                if dry_run:
                    results.append({"symbol": p.symbol, "action": "close_dry",
                                    "reason": reason, "ai_verdict": v.to_dict()})
                else:
                    res = self.executor.close_position(p.symbol, reason=reason)
                    results.append({**res.to_dict(), "ai_verdict": v.to_dict()})
        return results

    # ---------- main loop ----------
    def run_scan(self, max_candidates: int = 25, dry_run: bool = False) -> dict[str, Any]:
        log.info("=== Starting scan (dry_run=%s) ===", dry_run)
        kill = check_kill_switch(self.client, self.cfg)
        account = self.client.get_account()
        equity = float(account.equity)
        positions = self.client.get_positions()
        log.info("Account: equity=$%.0f, positions=%d, trades_today=%d",
                 equity, len(positions), kill.trades_today)
        macro = self.macro_brief()

        # ---- Kill-switch halt path: no new entries, but AI-gated profit-taking exits ----
        if kill.halted:
            log.warning("Kill switch HALTED: %s", kill.reasons)
            # Fetch portfolio signals so AI has context
            portfolio = self._portfolio_signals(macro)
            halt_exits = self._halt_day_exits(portfolio, macro, equity, dry_run)
            # Sweep any freed cash into SPY (still "cash-equivalent")
            cash_proxy_action = None if dry_run else self._sweep_cash_to_proxy(equity)
            summary = {
                "ts": pd.Timestamp.utcnow().isoformat(),
                "equity": equity,
                "positions_count": len(positions),
                "halted": True,
                "macro": macro.to_dict(),
                "kill_switch": kill.to_dict(),
                "halt_exits": halt_exits,
                "cash_proxy": cash_proxy_action,
            }
            _save_research("scan", summary)
            log.info("Scan complete (halted): halt-day exits=%d", len(halt_exits))
            return summary

        # Shared portfolio signal bundle (used for exits + rebalance)
        portfolio = self._portfolio_signals(macro)

        # Exits first (hard signals — unchanged logic)
        exit_results: list[dict[str, Any]] = []
        exits = self.evaluate_exits(macro, portfolio=portfolio)
        for sym, reason in exits:
            if dry_run:
                log.info("[DRY] Would close %s: %s", sym, reason)
                exit_results.append({"symbol": sym, "action": "close_dry", "reason": reason})
            else:
                res = self.executor.close_position(sym, reason=reason)
                exit_results.append(res.to_dict())

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
        )

        if bearish_halt:
            log.warning(
                "Bearish-day halt: macro_score=%.2f, vix=%s — skipping new screen entries "
                "(exits & rebalance-trims ran; rebalance-adds only for high-conviction)",
                macro.score, macro.vix_regime,
            )
            cash_proxy_action = None if dry_run else self._sweep_cash_to_proxy(equity)
            summary = {
                "ts": pd.Timestamp.utcnow().isoformat(),
                "equity": equity,
                "positions_count": len(positions),
                "macro": macro.to_dict(),
                "kill_switch": kill.to_dict(),
                "bearish_halt": {"score": macro.score, "vix_regime": macro.vix_regime,
                                 "threshold": halt_score},
                "exits": exit_results,
                "rebalance": rebalance_results,
                "executions": [],
                "cash_proxy": cash_proxy_action,
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

        actions = [d for d in decisions if d.action in ("buy", "sell_short")]
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
            log.info("AI research unavailable — falling back to numeric-only decisions")

        # --- Build final execution list ---
        ai_weight = float(self.cfg.get("ai", "weight", default=0.6))
        min_conf = float(self.cfg.get("risk", "min_confidence", default=0.40))
        executions: list[dict[str, Any]] = []

        # Candidates to execute: if AI is active, ONLY those AI approved (final_action in buy/sell_short).
        # If AI is inactive, numeric-only (current behavior).
        if ai_active:
            pipeline_candidates = []
            for sym, verdict in ai_verdicts.items():
                if verdict.final_action not in ("buy", "sell_short"):
                    continue
                if verdict.ai_confidence <= 0:
                    continue
                numeric = next((d for d in decisions if d.symbol == sym), None)
                if not numeric:
                    continue
                # Blend AI confidence with numeric (if same direction)
                num_dir_matches = (
                    (verdict.final_action == "buy" and numeric.combined_score >= 0)
                    or (verdict.final_action == "sell_short" and numeric.combined_score <= 0)
                )
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
            pipeline_candidates = [d for d in actions if d.confidence >= min_conf]

        log.info("Approved for execution: %d", len(pipeline_candidates))

        for d in pipeline_candidates:
            tech_detail = d.signal_details.get("technical", {})
            price = tech_detail.get("price")
            atr = tech_detail.get("atr")
            if not price or not atr:
                continue
            side = "buy" if d.action == "buy" else "sell_short"
            sizing = self.risk.size_position(
                symbol=d.symbol,
                side=side,
                price=price, atr=atr,
                confidence=d.confidence,
                equity=equity,
                existing_positions=positions,
                is_crypto=False,
            )
            if not sizing:
                continue
            if dry_run:
                log.info("[DRY] Would execute %s", sizing.to_dict())
                executions.append({"dry_run": True, "sizing": sizing.to_dict(), "decision": d.to_dict()})
            else:
                # Ensure real cash covers the notional; sell SPY cash-proxy if short.
                self._ensure_cash_for(sizing.notional, equity)
                result = self.executor.execute(d, sizing)
                executions.append(result.to_dict())
                positions = self.client.get_positions()

        # Sweep idle cash above the true-cash floor into SPY.
        # Skipped when dry-run (no real executions happened).
        cash_proxy_action = None
        if not dry_run:
            cash_proxy_action = self._sweep_cash_to_proxy(equity)

        summary = {
            "ts": pd.Timestamp.utcnow().isoformat(),
            "equity": equity,
            "positions_count": len(positions),
            "macro": macro.to_dict(),
            "kill_switch": kill.to_dict(),
            "candidates_evaluated": len(decisions),
            "actionable_numeric": len(actions),
            "ai_active": ai_active,
            "ai_verdicts": {s: v.to_dict() for s, v in ai_verdicts.items()},
            "approved_for_execution": len(pipeline_candidates),
            "exits": exit_results,
            "rebalance": rebalance_results,
            "executions": executions,
            "cash_proxy": cash_proxy_action,
            "decisions": [d.to_dict() for d in decisions],
        }
        _save_research("scan", summary)
        log.info("Scan complete: exits=%d, rebalance=%d, executions=%d",
                 len(exit_results), len(rebalance_results), len(executions))
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
        kill = check_kill_switch(self.client, self.cfg)
        if kill.halted:
            log.warning("Kill switch HALTED: %s", kill.reasons)
            return {"halted": True, "kill_switch": kill.to_dict()}

        # Config knobs
        hold_threshold = float(self.cfg.get("overnight", "hold_threshold", default=0.0))
        buy_threshold = float(self.cfg.get("overnight", "buy_threshold", default=0.35))
        max_new = int(self.cfg.get("overnight", "max_new_positions", default=3))
        size_mult = float(self.cfg.get("overnight", "size_multiplier", default=0.5))
        scan_candidates = int(self.cfg.get("overnight", "scan_candidates", default=30))
        enable_new_buys = bool(self.cfg.get("overnight", "enable_new_buys", default=True))

        account = self.client.get_account()
        equity = float(account.equity)
        positions = self.client.get_positions()
        equity_positions = [p for p in positions if "/" not in p.symbol]
        log.info("Preclose: equity=$%.0f, positions=%d (equity=%d)",
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

        hold_reports: list[dict[str, Any]] = []
        exit_results: list[dict[str, Any]] = []
        for p in equity_positions:
            sym = p.symbol
            is_long = (p.side.value == "long") if hasattr(p.side, "value") else (p.side == "long")
            tech = tech_held.get(sym)
            tech_score = tech.score if tech else 0.0
            sent = score_news_for_symbol(sym, news_held)
            sent_score = sent.score if sent else 0.0
            intraday = self._slice_symbol(intraday_held, sym)
            ov = score_overnight(sym, intraday, tech_score, sent_score, market_bias)
            if ov is None:
                log.info("[%s] no intraday data; keeping position", sym)
                hold_reports.append({"symbol": sym, "decision": "hold_no_data"})
                continue

            # For long positions, bullish overnight score is favorable.
            # For short positions, bearish overnight score is favorable.
            directional = ov.score if is_long else -ov.score
            decision = "hold" if directional >= hold_threshold else "close"
            report = {
                "symbol": sym, "is_long": is_long,
                "overnight": ov.to_dict(),
                "directional_score": round(directional, 3),
                "decision": decision,
            }
            hold_reports.append(report)
            log.info("[%s] %s directional=%+.2f (ov=%+.2f) notes=%s -> %s",
                     sym, "LONG" if is_long else "SHORT",
                     directional, ov.score, ov.notes, decision.upper())
            if decision == "close":
                reason = f"preclose overnight bias {directional:+.2f}"
                if dry_run:
                    exit_results.append({"symbol": sym, "action": "close_dry", "reason": reason})
                else:
                    res = self.executor.close_position(sym, reason=reason)
                    exit_results.append(res.to_dict())

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
            # Longs-only for overnight carry: bullish tech bias preferred.
            long_biased = [t for t in tech_top if t.score > 0.1][:scan_candidates]
            cand_syms = [t.symbol for t in long_biased]
            # Skip symbols we already hold
            held_set = {p.symbol for p in positions}
            cand_syms = [s for s in cand_syms if s not in held_set]
            long_biased = [t for t in long_biased if t.symbol in cand_syms]

            intraday_cand = self._fetch_intraday(cand_syms, minutes=5) if cand_syms else None
            news_cand = self.client.get_news(symbols=cand_syms, limit=80, days_back=2) if cand_syms else []

            scored: list[tuple[TechnicalSignal, OvernightSignal]] = []
            for t in long_biased:
                intraday = self._slice_symbol(intraday_cand, t.symbol)
                sent = score_news_for_symbol(t.symbol, news_cand)
                ov = score_overnight(t.symbol, intraday, t.score, sent.score if sent else 0.0, market_bias)
                if not ov:
                    continue
                cand_reports.append({
                    "symbol": t.symbol,
                    "tech_score": round(t.score, 3),
                    "overnight": ov.to_dict(),
                })
                if ov.score >= buy_threshold:
                    scored.append((t, ov))

            scored.sort(key=lambda x: x[1].score, reverse=True)
            picks = scored[:max_new]
            log.info("Preclose new-buy picks: %d (from %d scored, threshold=%.2f)",
                     len(picks), len(cand_reports), buy_threshold)

            # Refresh positions after closes
            if not dry_run and exit_results:
                positions = self.client.get_positions()

            for tech, ov in picks:
                price = tech.price
                atr = tech.atr
                if not price or not atr:
                    continue
                # Size more conservatively than a normal swing entry.
                sizing = self.risk.size_position(
                    symbol=tech.symbol, side="buy",
                    price=price, atr=atr,
                    confidence=max(0.0, min(1.0, ov.score)) * size_mult,
                    equity=equity,
                    existing_positions=positions,
                    is_crypto=False,
                )
                if not sizing:
                    continue
                decision_obj = TradeDecision(
                    symbol=tech.symbol,
                    action="buy",
                    confidence=ov.score,
                    combined_score=tech.score,
                    signal_scores={"technical": tech.score, "overnight": ov.score},
                    signal_details={"technical": tech.to_dict(), "overnight": ov.to_dict()},
                    reasoning=[
                        f"preclose overnight buy ov={ov.score:+.2f}",
                        f"close_strength={ov.close_strength:+.2f} late_drift={ov.late_drift:+.2f}",
                        f"market_bias={ov.market_bias:+.2f}",
                    ],
                )
                if dry_run:
                    log.info("[DRY] Would open overnight %s", sizing.to_dict())
                    new_executions.append({"dry_run": True, "sizing": sizing.to_dict(),
                                           "decision": decision_obj.to_dict()})
                else:
                    # Ensure real cash covers the notional; sell SPY if short.
                    self._ensure_cash_for(sizing.notional, equity)
                    result = self.executor.execute(decision_obj, sizing)
                    new_executions.append(result.to_dict())
                    positions = self.client.get_positions()

        # Park any remaining idle cash in SPY for overnight carry.
        cash_proxy_action = None if dry_run else self._sweep_cash_to_proxy(equity)

        summary = {
            "ts": pd.Timestamp.utcnow().isoformat(),
            "equity": equity,
            "positions_count": len(positions),
            "market_bias": round(market_bias, 3),
            "kill_switch": kill.to_dict(),
            "hold_reports": hold_reports,
            "exits": exit_results,
            "candidate_reports": cand_reports,
            "new_executions": new_executions,
            "cash_proxy": cash_proxy_action,
            "thresholds": {
                "hold": hold_threshold, "buy": buy_threshold,
                "max_new": max_new, "size_mult": size_mult,
            },
        }
        _save_research("preclose", summary)
        log.info("Preclose complete: closes=%d, new_buys=%d",
                 len(exit_results), len(new_executions))
        return summary

    def run_crypto_scan(self, dry_run: bool = False) -> dict[str, Any]:
        log.info("=== Crypto scan (dry_run=%s) ===", dry_run)
        kill = check_kill_switch(self.client, self.cfg)
        if kill.halted:
            return {"halted": True, "kill_switch": kill.to_dict()}

        account = self.client.get_account()
        equity = float(account.equity)
        positions = self.client.get_positions()

        symbols = crypto_universe(self.cfg)
        if not symbols:
            return {"skipped": "no crypto universe"}

        bars = self.client.get_crypto_bars(symbols, lookback_hours=24 * 60)
        executions: list[dict[str, Any]] = []
        for sym in symbols:
            try:
                g = bars.xs(sym, level="symbol")
                tech = compute_technicals(sym, g)
                if not tech:
                    continue
                # Simplified: only technical + macro-ish regime (crypto 24/7)
                decision = self.engine.decide(
                    symbol=sym,
                    technical_score=tech.score,
                    fundamental_score=None,
                    sentiment_score=None,
                    macro_score=None,
                    risk_score=0.0,
                    signal_details={"technical": tech.to_dict()},
                )
                log_decision({"symbol": sym, "decision": decision.to_dict()})
                if decision.action == "buy":
                    sizing = self.risk.size_position(
                        symbol=sym, side="buy",
                        price=tech.price, atr=tech.atr,
                        confidence=decision.confidence,
                        equity=equity,
                        existing_positions=positions,
                        is_crypto=True,
                    )
                    if sizing:
                        if dry_run:
                            executions.append({"dry": True, "sizing": sizing.to_dict()})
                        else:
                            res = self.crypto_executor.execute(decision, sizing)
                            executions.append(res.to_dict())
            except Exception as e:
                log.warning("Crypto eval for %s failed: %s", sym, e)
        summary = {"executions": executions, "equity": equity}
        _save_research("crypto_scan", summary)
        return summary
