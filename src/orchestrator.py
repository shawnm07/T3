"""End-to-end pipeline: gather signals → decide → size → execute. Entry + exit."""
from __future__ import annotations
import json
import logging
from dataclasses import asdict
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
from src.decision import DecisionEngine, TradeDecision
from src.discovery import Candidate, discover_candidates
from src.earnings import EarningsInfo, fetch_earnings, within_window
from src.executor import TradeExecutor
from src.fundamentals import compute_fundamentals
from src.journal import log_decision
from src.kill_switch import check_kill_switch
from src.macro import MacroSignal, compute_macro
from src.market_data import get_market_data
from src.overnight import OvernightSignal, market_bias_from_spy, score_overnight
from src.rebalance import compute_rebalance_plan
from src.risk import RiskManager
from src import sector_guard
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
        self.earnings_enabled = bool(config.get("earnings", "enabled", default=True))
        self.earnings_block_days = int(config.get("earnings", "block_entry_days", default=5))
        self.earnings_trim_days = int(config.get("earnings", "trim_exit_days", default=3))
        self.earnings_override = float(config.get("earnings", "high_conviction_override", default=0.85))
        self.earnings_ttl_hours = float(config.get("earnings", "cache_ttl_hours", default=24))
        self.earnings_use_ai_gate = bool(config.get("earnings", "use_ai_gate", default=True))
        self.rebalance_use_ai_arbiter = bool(config.get("rebalance", "use_ai_arbiter", default=True))
        # New-entry earnings blackout (separate from held-position trim window)
        self.entry_earnings_blackout_days = int(
            config.get("earnings", "new_entry_earnings_blackout_days", default=7)
        )
        self.entry_earnings_override = float(
            config.get("earnings", "new_entry_earnings_override_confidence", default=0.85)
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
        return self.cash_proxy_enabled and symbol == self.cash_proxy_symbol

    def _get_proxy_position(self, positions):
        for p in positions:
            if self._is_cash_proxy(p.symbol):
                return p
        return None

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

    def _available_cash_above_floor(self, equity: float, floor_pct: float) -> float:
        try:
            account = self.client.get_account()
            cash = float(account.cash)
        except Exception as e:
            log.warning("cash budget: account fetch failed: %s", e)
            return 0.0
        return max(0.0, cash - (equity * max(0.0, floor_pct)))

    def _sell_cash_proxy_for(self, notional: float, reason: str) -> bool:
        """Sell SPY cash-proxy by qty/percentage, avoiding stale notional oversells."""
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
        """Return the buy notional allowed by confirmed cash after funding attempts."""
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
        return allowed

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
          12:00, 14:00, 15:30 ET → MIDDAY  (window: 11:00–16:00 ET)
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
                "sent_map": sent_map, "numeric": numeric, "news": news,
                "earnings_map": earnings_map}

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
            is_long = p.side.value == "long" if hasattr(p.side, "value") else p.side == "long"
            plpc = float(p.unrealized_plpc) if hasattr(p, "unrealized_plpc") else 0.0

            # Deterministic triggers become TRIGGER FLAGS in the AI payload —
            # they never fire a trade on their own.
            flipped = (is_long and tech.score < -0.3) or (not is_long and tech.score > 0.3)
            bad_news = (is_long and sent_score < -0.5) or (not is_long and sent_score > 0.5)
            stalled = (is_long and tech.score < stall_thr) or (not is_long and tech.score > -stall_thr)

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
                    is_long=is_long, plpc=plpc,
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
            if not (flipped or bad_news or stalled):
                continue

            num_dec = numeric.get(p.symbol)
            ctx = {
                "symbol": p.symbol,
                "side": "long" if is_long else "short",
                "qty": str(p.qty),
                "market_value": abs(float(p.market_value)),
                "unrealized_plpc": round(plpc, 4),
                "current_price": float(tech.price) if tech.price is not None else None,
                "atr": float(tech.atr) if tech.atr is not None else None,
                "technical": tech.to_dict(),
                "sentiment": sent.to_dict() if sent else None,
                "macro": macro.to_dict(),
                "numeric_decision": (num_dec.to_dict() if num_dec else None),
                "exit_triggers": {
                    "technical_flipped": flipped,
                    "bad_news": bad_news,
                    "momentum_stalled": stalled,
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
                closes.append((
                    p.symbol,
                    f"AI exit-arbiter (conf={conf:.2f}, model={model_used}): {reasoning}",
                ))
            elif action == "reduce" and conf >= min_exit_conf:
                # Partial reduce is handled by the rebalance arbiter on the
                # same scan; we intentionally don't hard-close here.
                log.info("[%s] exit-arbiter suggests reduce — deferring to rebalance arbiter", p.symbol)
            # else: hold / low-confidence → do nothing
        return closes

    def _earnings_gate_decision(
        self, p, einfo: EarningsInfo, tech, sent, numeric, macro: MacroSignal | None,
        is_long: bool, plpc: float,
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
            "side": "long" if is_long else "short",
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
        ai_reason = (
            f"earnings in {einfo.days_until}d ({einfo.next_date}) — AI {verdict} "
            f"(conf={conf:.2f}, model={model_used}): {rationale}"
        )
        log_decision({
            "event": "earnings_gate", "symbol": p.symbol, "model": model_used,
            "verdict": verdict, "confidence": conf, "rationale": rationale,
        })
        log.info("[%s] earnings gate (model=%s) -> %s (conf=%.2f): %s",
                 p.symbol, model_used, verdict, conf, rationale)
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
            is_long = (p.side.value == "long") if hasattr(p.side, "value") else (p.side == "long")
            entry = {
                "symbol": p.symbol,
                "side": "long" if is_long else "short",
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
    def _intraday_chart_for(intraday_df, symbol: str) -> dict[str, Any] | None:
        """Build the full intraday chart structure expected by the portfolio
        arbiter. Returns a dict containing:

          current_price, open, day_high, day_low, vwap,
          distance_from_high_pct, distance_from_low_pct, intraday_change_pct,
          recent_trend (rising|falling|flat), volume_trend (rising|falling|flat),
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

            opens = slc["open"]
            highs = slc["high"] if "high" in slc.columns else slc["close"]
            lows = slc["low"] if "low" in slc.columns else slc["close"]
            closes = slc["close"]
            volumes = slc["volume"] if "volume" in slc.columns else None

            opn = float(opens.iloc[0])
            cur = float(closes.iloc[-1])
            day_high = float(highs.max())
            day_low = float(lows.min())

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
            try:
                if volumes is not None and len(volumes) >= 4:
                    half = max(3, min(6, len(volumes) // 2))
                    recent_v = float(volumes.iloc[-half:].mean())
                    prior_v = float(volumes.iloc[-2 * half : -half].mean()) if len(volumes) >= 2 * half else float(volumes.iloc[:-half].mean() if len(volumes) > half else recent_v)
                    if prior_v > 0:
                        ratio = recent_v / prior_v
                        if ratio >= 1.10:
                            volume_trend = "rising"
                        elif ratio <= 0.90:
                            volume_trend = "falling"
            except Exception:
                volume_trend = "flat"

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

            return {
                "current_price": round(cur, 4),
                "open": round(opn, 4),
                "day_high": round(day_high, 4),
                "day_low": round(day_low, 4),
                "vwap": round(vwap_val, 4) if vwap_val is not None else None,
                "distance_from_high_pct": round(dist_from_high, 4) if dist_from_high is not None else None,
                "distance_from_low_pct": round(dist_from_low, 4) if dist_from_low is not None else None,
                "intraday_change_pct": round(intraday_chg, 4) if intraday_chg is not None else None,
                "recent_trend": recent_trend,
                "volume_trend": volume_trend,
                "classification": classification,
            }
        except Exception:
            return None

    def _build_arbiter_context(
        self,
        holdings: list,
        tech_map: dict,
        sent_map: dict,
        numeric: dict,
        earnings_map: dict,
        macro: MacroSignal,
        equity: float,
        kill_state: dict[str, Any] | None = None,
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
          - system state (kill switch, halts, dry_run)
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

        # --- Daily SPY bars for 5-day perf ---
        spy_daily = None
        try:
            spy_daily = self.client.get_stock_bars(["SPY"], lookback_days=20)
        except Exception:
            pass

        # --- SPY block (cash-like parking vehicle) ---
        spy_position_value = 0.0
        spy_qty = 0.0
        if self.cash_proxy_enabled:
            for p in holdings:
                if self._is_cash_proxy(p.symbol):
                    spy_position_value = abs(float(p.market_value))
                    try:
                        spy_qty = float(p.qty)
                    except Exception:
                        spy_qty = 0.0
                    break
        spy_chart = self._intraday_chart_for(intraday_bars, "SPY")
        spy_5d_chg = self._five_day_change_pct(spy_daily, "SPY")
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
            is_long = (p.side.value == "long") if hasattr(p.side, "value") else (p.side == "long")
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
            chart = self._intraday_chart_for(intraday_bars, sym)
            pos_ctx.append({
                "symbol": sym,
                "side": "long" if is_long else "short",
                "qty": qty_f,
                "avg_entry_price": round(avg_entry, 4),
                "current_price": round(cur_price, 4),
                "market_value_usd": round(mv * (1 if is_long else -1), 2),
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
            "max_drawdown_weekly_pct": float(self.cfg.get(
                "kill_switch", "weekly_drawdown_pct", default=0.05)),
            "max_drawdown_daily_pct": float(self.cfg.get(
                "kill_switch", "daily_drawdown_pct", default=0.025)),
            "max_position_pct": float(self.risk.max_position_pct),
            "max_sector_pct": float(self.risk.max_sector_pct),
            "max_positions": int(self.risk.max_positions),
            "max_leverage": float(self.cfg.get("risk", "max_leverage", default=1.0)),
            "cash_reserve_pct": float(self.risk.cash_reserve_pct),
            "cash_reserve_min_pct": float(self.risk.cash_reserve_min_pct),
            "max_risk_per_trade_pct": 0.005,  # mirrors risk.py hard cap
            "high_conviction_threshold": float(self.risk.high_conviction_threshold),
            "stop_loss_atr_mult": float(self.cfg.get("risk", "stop_loss_atr_mult", default=2.0)),
            "take_profit_atr_mult": float(self.cfg.get("risk", "take_profit_atr_mult", default=4.0)),
        }

        # --- Trading rules (text — guides AI judgment) ---
        trading_rules = [
            "You are the FINAL authority on every capital allocation decision.",
            "Only act on high-confidence setups; spreading capital evenly is the wrong default.",
            "Capital must be actively optimized intraday — every scan rebalances.",
            "No trade may execute without your explicit approval (you are the AI gate).",
            "Decisions are intraday-focused with a swing-trade horizon.",
            "Concentrate into highest-conviction names up to max_position_pct.",
            "Free capital from oversized / low-upside positions and redeploy.",
            "Treat SPY as cash-like; choose SPY vs cash based on macro + intraday tape.",
            "Sector caps and per-position caps are HARD constraints.",
        ]

        # --- Execution constraints ---
        execution_constraints = {
            "fractional_shares_supported": True,
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
            "kill_switch_halted": bool((kill_state or {}).get("halted", False)),
            "kill_switch_reasons": (kill_state or {}).get("reasons", []) or [],
            "weekly_return": (kill_state or {}).get("weekly_return"),
            "daily_return": (kill_state or {}).get("daily_return"),
            "trades_today": (kill_state or {}).get("trades_today"),
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
        earnings_exit_symbols: set[str] | None = None,
        kill_state: dict[str, Any] | None = None,
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
            (kill switch + execution-cost floors), not strategy.
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
            kill_state=kill_state, bearish_halt=bearish_halt, dry_run=dry_run,
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
            # Is this action reducing or increasing exposure? SELLs that *reduce*
            # a long or *unwind* a short free cash. SELLs that *grow* a short
            # consume cash. (For shorts, "sell" on an existing short means add
            # to the short — consumes buying power.)
            grows_exposure = a.current_notional < a.target_notional
            if grows_exposure:
                funded_notional = self._funded_buy_notional(
                    a.symbol, a.delta_notional, equity, cash_floor_pct,
                    "rebalance",
                )
                if funded_notional <= 0:
                    results.append({**a.to_dict(), "skipped": "insufficient_confirmed_cash"})
                    continue
                exec_result = self.executor.partial_trade(
                    symbol=a.symbol, side=a.side,
                    delta_notional=funded_notional,
                    reason=a.reason,
                )
                action_dict = a.to_dict()
                if funded_notional != round(float(a.delta_notional), 2):
                    action_dict["requested_delta_notional"] = action_dict["delta_notional"]
                    action_dict["delta_notional"] = funded_notional
                    action_dict["cash_capped"] = True
            elif a.side == "sell" and (a.target_notional <= 0 or a.target_pct <= 0 or a.ai_action == "EXIT"):
                exec_result = self.executor.close_position(a.symbol, reason=a.reason)
                action_dict = a.to_dict()
                action_dict["full_exit_via_close_position"] = True
            else:
                exec_result = self.executor.partial_trade(
                    symbol=a.symbol, side=a.side,
                    delta_notional=a.delta_notional,
                    reason=a.reason,
                )
                action_dict = a.to_dict()
            results.append({**action_dict, "execution": exec_result.to_dict()})
            if not exec_result.ok:
                log.warning("[%s] rebalance action did not fill — skipping further dependent actions for safety",
                            a.symbol)
                # Re-fetch live account state so any subsequent add sees real cash.
                # We continue the loop; the _ensure_cash_for() on the next grow
                # action will now use accurate state.

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
        try:
            self.client.submit_notional(self.cash_proxy_symbol, buy_amt, side="buy")
            log.info("SPY rebalance BUY $%.0f: %s %.1f%% → target %.1f%% of equity",
                     buy_amt, self.cash_proxy_symbol,
                     current_value / equity * 100, float(target_pct) * 100)
            return {
                "symbol": self.cash_proxy_symbol, "action": "buy",
                "delta_usd": round(buy_amt, 2),
                "current_value": round(current_value, 2),
                "target_value": round(target_value, 2),
                "ai_target_pct": round(float(target_pct), 4),
            }
        except Exception as e:
            log.warning("SPY rebalance buy failed: %s", e)
            return {"symbol": self.cash_proxy_symbol, "action": "buy_failed", "error": str(e)}

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
                    results.append({**res.to_dict(), "reason": reason, "ai_verdict": v.to_dict()})
        return results

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
        dust_closed: list[dict[str, Any]] = []
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
                # Target zero but residual shares — force full close via percentage=100.
                try:
                    log.info("Verifier dust-sweep: force-closing %s (qty=%s, target=0%%)", sym, qty)
                    order = self.client.close_position(sym, percentage=100)
                    order_id = str(getattr(order, "id", "") or "") or None
                    final_status = "submitted"
                    filled_qty = 0.0
                    if order_id:
                        final, ok = self.client.wait_for_order_fill(
                            order_id, timeout_s=30.0, poll_s=1.0,
                        )
                        if final is not None:
                            final_status = str(getattr(final, "status", "") or "submitted").lower().replace("orderstatus.", "")
                            filled_qty = float(getattr(final, "filled_qty", 0) or 0)
                    dust_closed.append({
                        "symbol": sym, "action": "force_close_100pct",
                        "qty_before": qty, "filled_qty": filled_qty,
                        "final_status": final_status, "order_id": order_id,
                    })
                except Exception as e:
                    msg = str(e)
                    log.warning("Verifier dust-sweep: close_position(%s) failed: %s", sym, msg)
                    dust_closed.append({"symbol": sym, "action": "force_close_failed",
                                        "qty_before": qty, "error": msg})

        # Refresh after dust sweep so weight calc reflects post-close state.
        if dust_closed:
            try:
                account, positions = self.client.get_snapshot(force_refresh=True, log_detail=False)
                live_equity = float(account.equity) if account else live_equity
                cash_usd = float(account.cash) if account else cash_usd
            except Exception as e:
                log.warning("Verifier: post-dust snapshot refresh failed: %s", e)

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
            diff_rows.append({
                "symbol": sym,
                "qty": round(qty, 6),
                "market_value_usd": round(mv, 2),
                "current_weight": round(cur_w, 4),
                "target_weight": round(tw, 4),
                "gap_usd": round(gap_usd, 2),
                "gap_pct_of_equity": round(gap_pct, 4),
                "above_tolerance": abs(gap_usd) > tolerance_usd,
                "opus_action": (per_symbol.get(sym, {}) or {}).get("action"),
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
                delta_usd = abs(float(prop.get("delta_usd", 0) or 0))
            except (TypeError, ValueError):
                rejected.append({"symbol": sym, "reason": "delta_usd not numeric"})
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
            if delta_usd < min_corrective_usd:
                rejected.append({"symbol": sym, "reason": f"delta ${delta_usd:.0f} < min ${min_corrective_usd:.0f}"})
                continue
            # Cap delta at the actual gap so we never overshoot Opus's target.
            capped_delta = min(delta_usd, abs(row["gap_usd"]))
            if capped_delta < min_corrective_usd:
                rejected.append({"symbol": sym, "reason": "capped delta below min_corrective"})
                continue
            try:
                if side == "buy":
                    floor_pct = max(float(cash_target or 0.0), float(self.risk.cash_reserve_pct))
                    funded_delta = self._funded_buy_notional(
                        sym, capped_delta, live_equity, floor_pct, "verifier",
                    )
                    if funded_delta < min_corrective_usd:
                        rejected.append({"symbol": sym, "reason": "insufficient_confirmed_cash"})
                        continue
                    capped_delta = funded_delta
                exec_res = self.executor.partial_trade(
                    symbol=sym, side=side, delta_notional=capped_delta,
                    reason=f"verifier reconcile to Opus target {row['target_weight']*100:.1f}% "
                           f"(gap was ${row['gap_usd']:+.0f})",
                )
                executed.append({
                    "symbol": sym, "side": side,
                    "proposed_usd": round(delta_usd, 2),
                    "executed_usd": round(capped_delta, 2),
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
        kill_state: dict[str, Any] | None,
        macro: MacroSignal,
        top_score: float | None = None,
    ) -> bool:
        """True when the 3-position floor may be relaxed to 0–6.

        Conditions are configured under ``selector.floor_breach_conditions``.
        Returns True if any enabled condition fires; False otherwise.
        """
        cfg_breach = self.cfg.get("selector", "floor_breach_conditions", default={}) or {}
        if cfg_breach.get("kill_switch_active") and (kill_state or {}).get("halted"):
            log.info("[selector] floor breach allowed: kill-switch halted")
            return True
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
        return candidates, breakdown

    def _build_selector_context(
        self,
        candidates: list[Candidate],
        portfolio: dict[str, Any],
        macro: MacroSignal,
        equity: float,
        kill_state: dict[str, Any] | None,
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
        ``{"currently_held": bool, "is_crypto": bool, "sector": str}`` for the
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
            kill_state=kill_state,
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
            "Apply exhaustion penalty to symbols near day high with fading volume.",
            "Force rotation: held symbols not in selected_positions MUST EXIT.",
            "When any new candidate is within 5 score points of your weakest "
            "selected, you MUST include at least one new candidate.",
            "Score-weighted sizing: weight ∝ opportunity_score, not equal-weight.",
            "Sector caps and per-position caps are HARD constraints.",
            (
                f"DIVERSIFICATION CAP (HARD): no more than "
                f"{int(self.cfg.get('diversification', 'max_per_gics_sector', default=3) or 3)} "
                f"selected positions may share the same GICS sector, and no more than "
                f"{int(self.cfg.get('diversification', 'max_per_theme', default=3) or 3)} "
                f"may share the same theme_bucket. Theme weight cap: "
                f"{float(self.cfg.get('diversification', 'max_theme_weight_pct', default=0.50) or 0.50):.0%}. "
                f"The executor will VETO any plan that violates these caps."
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

        for cand in candidates:
            sym = cand.symbol
            currently_held = bool(cand.is_held)
            block: dict[str, Any] = held_blocks_by_sym.get(sym, {}).copy()
            if not block:
                # Build a minimal block for non-held candidates.
                tech = tech_map.get(sym)
                sent = sent_map.get(sym)
                num = numeric.get(sym)
                einfo = earnings_map.get(sym)
                block = {
                    "symbol": sym,
                    "side": "long",  # default — selector decides direction via action
                    "qty": 0.0,
                    "avg_entry_price": 0.0,
                    "current_price": round(float(cand.price or 0), 4),
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
                    "intraday_chart": None,
                    "earnings_days_until": (einfo.days_until if einfo else None),
                    "earnings_next_date": (einfo.next_date if einfo else None),
                }
            block["currently_held"] = currently_held
            block["is_crypto"] = bool(cand.is_crypto)
            block["discovery_sources"] = list(cand.sources)
            block["intraday_change_pct"] = round(float(cand.change_pct or 0.0), 4)
            theme = (
                "crypto" if cand.is_crypto
                else sector_guard.theme_bucket_for(
                    cand.sector or "", sector_to_theme, sym, symbol_overrides
                )
            )
            block["theme_bucket"] = theme
            unified_pool.append(block)
            pool_meta[sym] = {
                "currently_held": currently_held,
                "is_crypto": bool(cand.is_crypto),
                "sector": cand.sector or "Other",
                "theme_bucket": theme,
            }

        base["candidate_pool"] = unified_pool
        base.pop("positions", None)
        base.pop("scan_candidates_summary", None)
        return base, pool_meta

    def _run_scan_with_selector(
        self,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Phase 4 cutover: unified-pool selector replaces the two-pipeline split.

        Flow:
          1. preamble: kill-switch, snapshot, macro, portfolio_signals
          2. urgent exits via exit-arbiter (kept)
          3. build unified candidate pool via discovery.py
          4. enrich + build selector context
          5. call portfolio-selector (Opus 4.7)
          6. validate; on failure → skip cycle (no trades), increment failure counter
          7. translate target_weights → compute_rebalance_plan → executor
          8. apply SPY target, run verifier
        """
        log.info("=== Starting scan via portfolio-selector (dry_run=%s) ===", dry_run)
        self._last_arbiter_set_spy_target = False
        self._last_ai_target_weights = None
        self._last_ai_per_symbol = {}
        self._last_ai_spy_target_pct = None
        self._last_ai_cash_target_pct = None
        kill = check_kill_switch(self.client, self.cfg)
        account, positions = self.client.get_snapshot(force_refresh=True, log_detail=True)
        equity = float(account.equity)
        log.info("Account: equity=$%.2f cash=$%.2f positions=%d trades_today=%d",
                 equity, float(account.cash), len(positions), kill.trades_today)
        if not dry_run:
            self._restore_cash_floor(equity)

        macro = self.macro_brief()
        scan_type = self._detect_scan_type()

        portfolio = self._portfolio_signals(macro)
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
        })

        if not candidates:
            log.warning("[selector] discovery returned empty pool — skipping cycle")
            log_decision({"event": "selector_skipped", "reason": "empty_pool"})
            return {"status": "skipped_empty_pool", "exits": exit_results}

        # 4. Floor-breach decision (heuristic — top-score gate uses numeric pre-AI)
        top_numeric = max(
            (abs(float((portfolio.get("numeric", {}) or {}).get(c.symbol).combined_score))
             for c in candidates
             if (portfolio.get("numeric", {}) or {}).get(c.symbol) is not None),
            default=None,
        )
        allow_floor_breach = self._compute_floor_breach_flag(
            kill.to_dict(), macro, top_score=top_numeric,
        )
        if kill.halted:
            allow_floor_breach = True

        # 5. Build selector context
        ctx, pool_meta = self._build_selector_context(
            candidates=candidates,
            portfolio=portfolio,
            macro=macro,
            equity=equity,
            kill_state=kill.to_dict(),
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

        # 6. Run selector
        result = run_portfolio_selector(
            self.cfg, ctx, pool_symbols=pool_symbols, pool_meta=pool_meta,
            held_symbols=held_symbols, allow_floor_breach=allow_floor_breach,
        )

        if result is None:
            consec = self._handle_selector_failure(reason="ai_failure_or_validation")
            log_decision({"event": "selector_skipped", "reason": "ai_failure",
                          "consecutive_failures": consec})
            return {
                "status": "skipped_selector_failure",
                "consecutive_failures": consec,
                "exits": exit_results,
                "pool_size": len(candidates),
                "kill_switch": kill.to_dict(),
            }

        self._reset_selector_failures()

        # Diversification veto: reject any plan that violates the per-sector
        # / per-theme cap. One repair retry, then forced compliance.
        cash_proxy = self.cash_proxy_symbol if self.cash_proxy_enabled else None
        guard = sector_guard.validate(
            target_weights=result.get("target_weights") or {},
            per_symbol=result.get("per_symbol") or {},
            pool_meta=pool_meta,
            cfg=self.cfg,
            cash_proxy_symbol=cash_proxy,
        )
        if not guard.ok:
            log_decision({"event": "sector_guard_violation",
                          "violations": [v.to_dict() for v in guard.violations]})
            ctx_retry = dict(ctx)
            ss_retry = dict(ctx_retry.get("system_state") or {})
            ss_retry["sector_guard_violations"] = [v.to_dict() for v in guard.violations]
            ss_retry["sector_guard_retry"] = True
            ctx_retry["system_state"] = ss_retry
            retry_result = run_portfolio_selector(
                self.cfg, ctx_retry, pool_symbols=pool_symbols, pool_meta=pool_meta,
                held_symbols=held_symbols, allow_floor_breach=allow_floor_breach,
            )
            if retry_result is not None:
                guard2 = sector_guard.validate(
                    target_weights=retry_result.get("target_weights") or {},
                    per_symbol=retry_result.get("per_symbol") or {},
                    pool_meta=pool_meta,
                    cfg=self.cfg,
                    cash_proxy_symbol=cash_proxy,
                )
                if guard2.ok:
                    result = retry_result
                    log_decision({"event": "sector_guard_repair_ok"})
                else:
                    forced = sector_guard.force_compliance(
                        target_weights=retry_result.get("target_weights") or {},
                        per_symbol=retry_result.get("per_symbol") or {},
                        violations=guard2.violations,
                        cash_proxy_symbol=cash_proxy,
                    )
                    result = retry_result
                    log_decision({"event": "sector_guard_forced",
                                  "forced_exits": forced,
                                  "violations": [v.to_dict() for v in guard2.violations]})
            else:
                forced = sector_guard.force_compliance(
                    target_weights=result.get("target_weights") or {},
                    per_symbol=result.get("per_symbol") or {},
                    violations=guard.violations,
                    cash_proxy_symbol=cash_proxy,
                )
                log_decision({"event": "sector_guard_forced",
                              "forced_exits": forced,
                              "violations": [v.to_dict() for v in guard.violations],
                              "retry": "ai_unavailable"})

        log_decision({"event": "selector_output", "result": result})
        log_decision({
            "event": "selector_rankings",
            "candidate_rankings": result.get("candidate_rankings", []),
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

        # 7. Translate to rebalance plan + execute
        target_weights = result.get("target_weights") or {}
        per_symbol = result.get("per_symbol") or {}
        spy_target_pct = float(result.get("spy_target_pct", 0) or 0)
        cash_target_pct = float(result.get("cash_target_pct", 0) or 0)
        selector_cash_floor_pct = max(
            cash_target_pct,
            float(self.risk.cash_reserve_pct),
        )
        self._last_ai_target_weights = dict(target_weights)
        self._last_ai_per_symbol = dict(per_symbol) if isinstance(per_symbol, dict) else {}
        self._last_ai_spy_target_pct = spy_target_pct
        self._last_ai_cash_target_pct = cash_target_pct
        # compute_rebalance_plan iterates over CURRENT positions only — it
        # produces trim/exit/grow actions for held names. New entries (selected
        # symbols not currently held) need a separate buy loop below.
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
        executions: list[dict[str, Any]] = []
        # Sells/exits first so freed cash can fund new buys.
        plan_sorted = sorted(plan or [],
                             key=lambda a: 0 if a.side == "sell" else 1)
        for a in plan_sorted:
            if dry_run:
                log.info("[DRY] Rebalance %s", a.to_dict())
                executions.append({"dry_run": True, **a.to_dict()})
                continue
            grows_exposure = a.current_notional < a.target_notional
            try:
                action_dict = a.to_dict()
                if grows_exposure:
                    funded_notional = self._funded_buy_notional(
                        a.symbol, a.delta_notional, equity,
                        selector_cash_floor_pct, "[selector] rebalance",
                    )
                    if funded_notional <= 0:
                        executions.append({**action_dict, "skipped": "insufficient_confirmed_cash"})
                        continue
                    if funded_notional != round(float(a.delta_notional), 2):
                        action_dict["requested_delta_notional"] = action_dict["delta_notional"]
                        action_dict["delta_notional"] = funded_notional
                        action_dict["cash_capped"] = True
                    exec_result = self.executor.partial_trade(
                        symbol=a.symbol, side=a.side,
                        delta_notional=funded_notional, reason=a.reason,
                    )
                elif a.side == "sell" and (a.target_notional <= 0 or a.target_pct <= 0 or a.ai_action == "EXIT"):
                    exec_result = self.executor.close_position(a.symbol, reason=a.reason)
                    action_dict["full_exit_via_close_position"] = True
                else:
                    exec_result = self.executor.partial_trade(
                        symbol=a.symbol, side=a.side,
                        delta_notional=a.delta_notional, reason=a.reason,
                    )
                executions.append({**action_dict, "execution": exec_result.to_dict()})
                if not exec_result.ok:
                    log.warning("[selector] rebalance %s did not fill", a.symbol)
            except Exception as e:
                log.warning("[selector] partial_trade failed for %s: %s", a.symbol, e)
                executions.append({**a.to_dict(), "_error": str(e)})

        # New-entry loop: any selected symbol not in current positions gets a
        # BUY for target_pct * equity. Skips crypto (separate executor path).
        held_syms_set = {p.symbol for p in portfolio.get("holdings", [])}
        for sym in result.get("selected_positions", []) or []:
            if sym in held_syms_set or "/" in sym:
                continue
            target_pct = float((per_symbol.get(sym) or {}).get("target_pct", 0) or 0)
            if target_pct <= 0:
                continue
            notional = round(target_pct * equity, 2)
            if notional < float(self.cfg.get("risk", "min_trade_usd", default=500)):
                log.info("[selector] new entry %s skipped (notional $%.0f below min)",
                         sym, notional)
                continue
            reason = (per_symbol.get(sym) or {}).get("one_sentence_reason", "selector entry")
            if dry_run:
                log.info("[DRY] Selector new entry %s notional $%.0f", sym, notional)
                executions.append({"dry_run": True, "symbol": sym, "side": "buy",
                                   "delta_notional": notional, "reason": reason,
                                   "is_new_entry": True})
                continue
            funded_notional = self._funded_buy_notional(
                sym, notional, equity, selector_cash_floor_pct,
                "[selector] new-entry",
            )
            if funded_notional <= 0:
                executions.append({"symbol": sym, "side": "buy",
                                   "delta_notional": notional, "reason": reason,
                                   "is_new_entry": True,
                                   "skipped": "insufficient_confirmed_cash"})
                continue
            try:
                exec_result = self.executor.partial_trade(
                    symbol=sym, side="buy", delta_notional=funded_notional, reason=reason,
                )
                executions.append({"symbol": sym, "side": "buy",
                                   "delta_notional": funded_notional,
                                   "requested_delta_notional": notional,
                                   "cash_capped": funded_notional != notional,
                                   "reason": reason,
                                   "is_new_entry": True,
                                   "execution": exec_result.to_dict()})
            except Exception as e:
                log.warning("[selector] new-entry partial_trade failed for %s: %s", sym, e)
                executions.append({"symbol": sym, "side": "buy",
                                   "delta_notional": notional, "reason": reason,
                                   "is_new_entry": True, "_error": str(e)})

        # 8. Apply SPY target + verifier
        cash_proxy_action = None
        if not dry_run and self.cash_proxy_enabled:
            try:
                cash_proxy_action = self._apply_spy_target(spy_target_pct, equity)
                self._last_arbiter_set_spy_target = True
            except Exception as e:
                log.warning("[selector] SPY target apply failed: %s", e)

        verifier_summary: dict[str, Any] | None = None
        if not dry_run:
            try:
                verifier_summary = self._verify_portfolio_alignment(equity)
            except Exception as e:
                log.warning("[selector] verifier raised: %s", e)
                verifier_summary = {"error": str(e)}

        summary = {
            "ts": pd.Timestamp.utcnow().isoformat(),
            "equity": equity,
            "positions_count": len(positions),
            "macro": macro.to_dict(),
            "kill_switch": kill.to_dict(),
            "selector": {
                "pool_size": len(candidates),
                "sources_breakdown": breakdown,
                "selected_positions": result.get("selected_positions", []),
                "target_weights": target_weights,
                "spy_target_pct": spy_target_pct,
                "cash_target_pct": result.get("cash_target_pct"),
                "exhaustion_penalty_applied": result.get("exhaustion_penalty_applied", []),
                "new_candidates_selected": result.get("new_candidates_selected"),
                "allow_floor_breach": allow_floor_breach,
            },
            "exits": exit_results,
            "executions": executions,
            "cash_proxy": cash_proxy_action,
            "verifier": verifier_summary,
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
        kill = check_kill_switch(self.client, self.cfg)
        # Independent valuation: equity, market_value, unrealized_pl[pc],
        # current_price are recomputed from Alpha-Vantage-sourced prices
        # (Alpaca's paper-account fields are unreliable). Full snapshot
        # audit log fires here.
        account, positions = self.client.get_snapshot(force_refresh=True, log_detail=True)
        equity = float(account.equity)
        log.info("Account: computed_equity=$%.2f, cash=$%.2f, positions=%d, trades_today=%d",
                 equity, float(account.cash), len(positions), kill.trades_today)
        if not dry_run:
            self._restore_cash_floor(equity)
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
            kill_state=kill.to_dict(),
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
                "kill_switch": kill.to_dict(),
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
            log.critical(
                "AI research (Opus 4.7) unavailable — NO NEW ENTRIES will be "
                "executed this scan. Hard rule: no trade may execute without "
                "AI approval. Skipping entry pipeline."
            )

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
                # Re-fetched per-iteration so a prior unfilled trade doesn't leave
                # us thinking we have cash we don't.
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
            "kill_switch": kill.to_dict(),
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
        kill = check_kill_switch(self.client, self.cfg)
        if kill.halted:
            log.warning("Kill switch HALTED: %s", kill.reasons)
            return {"halted": True, "kill_switch": kill.to_dict()}

        # HARD RULE: preclose closes/opens touch capital, so they must route
        # through the Opus 4.7 arbiter. No AI → no preclose trades.
        if not self.ai.available():
            log.critical(
                "run_preclose: AI (Opus 4.7) unavailable — skipping all preclose "
                "trade actions (fail-safe). Stop-losses remain live."
            )
            return {"skipped": "ai_unavailable"}

        # Config knobs
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
            is_long = (p.side.value == "long") if hasattr(p.side, "value") else (p.side == "long")
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
                    is_long=is_long, plpc=_plpc,
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
                    continue
                if _earn_verdict == "hold":
                    log.info(
                        "[%s] preclose earnings gate: hold — skipping overnight close decision",
                        sym,
                    )
                    hold_reports.append({"symbol": sym, "decision": "hold_earnings_gate"})
                    continue
                if _earn_verdict == "trim_50":
                    log.info(
                        "[%s] preclose earnings gate: trim_50 — continuing with overnight decision",
                        sym,
                    )
                # skip_no_ai or trim_50: fall through to overnight decision

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
                    "side": "long" if is_long else "short",
                    "context": "PRECLOSE overnight-hold decision",
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
                min_exit_conf = float(self.cfg.get("exit_arbiter", "min_confidence", default=0.55))
                log_decision({
                    "event": "preclose_exit_arbiter", "symbol": sym, "model": model_used,
                    "action": ai_action, "confidence": ai_conf, "reasoning": ai_reasoning,
                    "triggers": arbiter_ctx["exit_triggers"],
                })
                log.info("[%s] preclose exit-arbiter (model=%s) -> %s conf=%.2f: %s",
                         sym, model_used, ai_action, ai_conf, ai_reasoning)
                if ai_action != "exit" or ai_conf < min_exit_conf:
                    log.info("[%s] preclose close vetoed by AI — holding overnight", sym)
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

            # When the market tape is leaning down, require higher conviction
            # than the default buy_threshold.
            effective_buy_threshold = (
                bearish_buy_threshold if market_bias < 0 else buy_threshold
            )

            scored: list[tuple[TechnicalSignal, OvernightSignal]] = []
            for t in long_biased:
                intraday = self._slice_symbol(intraday_cand, t.symbol)
                sent = score_news_for_symbol(t.symbol, news_cand)
                ov = score_overnight(t.symbol, intraday, t.score, sent.score if sent else 0.0, market_bias)
                if not ov:
                    continue
                report_entry = {
                    "symbol": t.symbol,
                    "tech_score": round(t.score, 3),
                    "rsi": round(float(t.rsi), 1) if t.rsi is not None else None,
                    "overnight": ov.to_dict(),
                }
                # RSI ceiling on new overnight longs: skip extended / overbought
                # names that leave no room to run into the gap.
                if t.rsi is not None and t.rsi > max_rsi_new_buy:
                    report_entry["skipped"] = f"rsi {t.rsi:.1f} > {max_rsi_new_buy:.1f}"
                    cand_reports.append(report_entry)
                    log.info("[%s] overnight skip: RSI %.1f > %.1f (overbought)",
                             t.symbol, t.rsi, max_rsi_new_buy)
                    continue
                if ov.score < effective_buy_threshold:
                    report_entry["skipped"] = (
                        f"ov {ov.score:.2f} < threshold {effective_buy_threshold:.2f}"
                    )
                    cand_reports.append(report_entry)
                    continue
                cand_reports.append(report_entry)
                scored.append((t, ov))

            scored.sort(key=lambda x: x[1].score, reverse=True)
            picks = scored[:max_new]
            log.info("Preclose new-buy picks: %d (from %d scored, threshold=%.2f, market_bias=%+.2f)",
                     len(picks), len(cand_reports), effective_buy_threshold, market_bias)

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

            for tech, ov in picks:
                price = tech.price
                atr = tech.atr
                if not price or not atr:
                    continue

                # Opus 4.7 entry arbiter must approve every overnight buy.
                num_dec = self.engine.decide(
                    symbol=tech.symbol,
                    technical_score=tech.score,
                    fundamental_score=None,
                    sentiment_score=None,
                    macro_score=None,
                    risk_score=0.0,
                    signal_details={"technical": tech.to_dict(), "overnight": ov.to_dict()},
                )
                arbiter_ctx = {
                    "symbol": tech.symbol,
                    "context": "PRECLOSE new-buy overnight candidate",
                    "current_price": price,
                    "position_status": "not_owned",
                    "technical_analyst": tech.to_dict(),
                    "overnight_signal": ov.to_dict(),
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
                sizing = self.risk.size_position(
                    symbol=tech.symbol, side="buy",
                    price=price, atr=atr,
                    confidence=ai_conf * size_mult,
                    equity=equity,
                    existing_positions=positions,
                    is_crypto=False,
                )
                if not sizing:
                    continue
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
                    combined_score=tech.score,
                    signal_scores={"technical": tech.score, "overnight": ov.score},
                    signal_details={
                        "technical": tech.to_dict(), "overnight": ov.to_dict(),
                        "ai_verdict": verdict,
                    },
                    reasoning=[
                        f"preclose AI-approved buy conf={ai_conf:.2f} (model={model_used})",
                        f"ov={ov.score:+.2f} close_strength={ov.close_strength:+.2f}",
                        f"thesis: {ai_thesis}",
                    ],
                )
                if dry_run:
                    log.info("[DRY] Would open overnight %s", sizing.to_dict())
                    new_executions.append({"dry_run": True, "sizing": sizing.to_dict(),
                                           "decision": decision_obj.to_dict()})
                else:
                    # Ensure real cash covers the notional; sell SPY if short.
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
                    if not result.ok and sequential_cash:
                        # Refund the liquidity we pre-deducted so subsequent picks aren't starved.
                        available_liquidity += sizing.notional
                        log.warning("[%s] preclose buy did not fill — refunding $%.0f to liquidity budget",
                                    tech.symbol, sizing.notional)
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

        account, positions = self.client.get_snapshot(force_refresh=True, log_detail=True)
        equity = float(account.equity)

        symbols = crypto_universe(self.cfg)
        if not symbols:
            return {"skipped": "no crypto universe"}

        # HARD RULE: crypto trades, like every other money-moving action, must
        # be approved by the Opus 4.7 decision-arbiter. No AI → no trades.
        if not self.ai.available():
            log.critical(
                "run_crypto_scan: AI (Opus 4.7) unavailable — skipping all "
                "crypto executions (fail-safe)."
            )
            return {"skipped": "ai_unavailable", "equity": equity}

        bars = self.client.get_crypto_bars(symbols, lookback_hours=24 * 60)
        executions: list[dict[str, Any]] = []
        for sym in symbols:
            try:
                g = bars.xs(sym, level="symbol")
                tech = compute_technicals(sym, g)
                if not tech:
                    continue
                # Technical + macro become INPUTS, never triggers. The numeric
                # decision is packaged as context for the Opus entry arbiter.
                numeric = self.engine.decide(
                    symbol=sym,
                    technical_score=tech.score,
                    fundamental_score=None,
                    sentiment_score=None,
                    macro_score=None,
                    risk_score=0.0,
                    signal_details={"technical": tech.to_dict()},
                )
                log_decision({"symbol": sym, "numeric": numeric.to_dict()})

                arbiter_ctx = {
                    "symbol": sym,
                    "asset_class": "crypto",
                    "current_price": tech.price,
                    "position_status": "not_owned",
                    "numeric_decision": numeric.to_dict(),
                    "technical_analyst": tech.to_dict(),
                    "fundamental_analyst": {"note": "n/a for crypto"},
                    "sentiment_analyst": {"note": "skipped"},
                    "macro": {"note": "crypto 24/7 — macro regime not applied"},
                    "portfolio": {
                        "equity": equity,
                        "positions_count": len(positions),
                    },
                    "risk_constraints": {
                        "max_position_pct": float(self.risk.max_position_pct),
                        "cash_reserve_pct": float(self.risk.cash_reserve_pct),
                    },
                }
                verdict = run_entry_arbiter_single(self.cfg, arbiter_ctx)
                if not verdict:
                    log.critical("[%s] crypto entry arbiter unavailable/errored — skipping", sym)
                    continue
                action = str(verdict.get("final_action", "")).strip().lower()
                conf = float(verdict.get("confidence", 0.0) or 0.0)
                thesis = str(verdict.get("thesis", ""))[:200]
                model_used = verdict.get("_model", "?")
                log_decision({
                    "event": "crypto_entry_arbiter", "symbol": sym,
                    "model": model_used, "action": action,
                    "confidence": conf, "thesis": thesis,
                })
                min_conf = float(self.cfg.get("risk", "min_confidence", default=0.40))
                if action != "buy" or conf < min_conf:
                    log.info("[%s] crypto arbiter -> %s conf=%.2f (below %.2f) — skip",
                             sym, action, conf, min_conf)
                    continue
                final_decision = TradeDecision(
                    symbol=sym, action="buy", confidence=conf,
                    combined_score=numeric.combined_score,
                    signal_scores=numeric.signal_scores,
                    signal_details={**numeric.signal_details, "ai_verdict": verdict},
                    reasoning=numeric.reasoning + [
                        f"ai=buy@{conf:.2f} (model={model_used})",
                        f"thesis: {thesis}",
                    ],
                )
                sizing = self.risk.size_position(
                    symbol=sym, side="buy",
                    price=tech.price, atr=tech.atr,
                    confidence=conf,
                    equity=equity,
                    existing_positions=positions,
                    is_crypto=True,
                )
                if sizing:
                    if dry_run:
                        executions.append({"dry": True, "sizing": sizing.to_dict(),
                                           "decision": final_decision.to_dict()})
                    else:
                        res = self.crypto_executor.execute(final_decision, sizing)
                        executions.append(res.to_dict())
            except Exception as e:
                log.warning("Crypto eval for %s failed: %s", sym, e)
        summary = {"executions": executions, "equity": equity}
        _save_research("crypto_scan", summary)
        return summary
