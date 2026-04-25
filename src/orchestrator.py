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
    run_exit_arbiter, run_entry_arbiter_single,
)
from src.ai_research import AIResearcher
from src.alpaca_client import AlpacaClient
from src.config import Config
from src.decision import DecisionEngine, TradeDecision
from src.earnings import EarningsInfo, fetch_earnings, within_window
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
        # Rebalance: block large no-arbiter adds
        self.rebal_require_ai_conf = float(
            config.get("rebalance", "require_ai_above_confidence", default=0.75)
        )
        self.rebal_require_ai_usd = float(
            config.get("rebalance", "require_ai_above_delta_usd", default=5000)
        )
        # Tracks whether the most recent rebalance handled SPY/cash via the AI
        # arbiter. When True, the post-scan deterministic auto-sweep is skipped
        # so the bot never overrides an explicit AI allocation decision.
        self._last_arbiter_set_spy_target: bool = False

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

    def _restore_cash_floor(self, equity: float) -> None:
        """If cash has dipped below the minimum reserve, immediately sell SPY proxy
        to restore it. Called at the top of each scan and rebalance so we never
        start a session with a negative or dangerously thin cash balance."""
        if not self.cash_proxy_enabled:
            return
        try:
            account = self.client.get_account()
            cash = float(account.cash)
        except Exception as e:
            log.warning("restore_cash_floor: account fetch failed: %s", e)
            return
        floor = equity * self.risk.cash_reserve_min_pct
        if cash >= floor:
            return
        shortfall = floor - cash
        positions = self.client.get_positions()
        proxy = self._get_proxy_position(positions)
        if not proxy:
            log.warning("Cash below floor ($%.0f < $%.0f) but no %s proxy to sell",
                        cash, floor, self.cash_proxy_symbol)
            return
        proxy_value = abs(float(proxy.market_value))
        sell_amt = min(shortfall + 100, proxy_value)  # small buffer above exact shortfall
        if sell_amt < 1:
            return
        try:
            self.client.submit_notional(self.cash_proxy_symbol, sell_amt, side="sell")
            log.info("Cash floor restore: sold $%.0f of %s (cash was $%.0f, floor $%.0f)",
                     sell_amt, self.cash_proxy_symbol, cash, floor)
        except Exception as e:
            log.warning("Cash floor restore sell failed: %s", e)

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
    ) -> list[tuple[str, str]]:
        """Return list of (symbol, reason) to close. AI IS THE ONLY AUTHORITY.

        Deterministic signals (technical flip, stalled momentum, bad news,
        earnings window) are assembled into a structured payload and sent to
        the Opus 4.7 exit-arbiter. NOTHING CLOSES WITHOUT AI APPROVAL.
        If AI is unavailable we HOLD (fail-safe). The bot does not make
        close decisions on its own.
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
            if in_earnings_window:
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
                    # Skip secondary exit logic during earnings window — AI said hold.
                    continue
                # verdict "skip_no_ai" (fail-safe): don't close, don't run other
                # exit checks for earnings-window names.
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
        self, p, einfo: EarningsInfo, tech, sent, numeric, macro: MacroSignal,
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
            "macro": macro.to_dict(),
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
        spy_intraday_chg = self._intraday_change_pct(intraday_bars, "SPY")
        spy_5d_chg = self._five_day_change_pct(spy_daily, "SPY")
        spy_current_price = None
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
            "intraday_change_pct": round(spy_intraday_chg, 4) if spy_intraday_chg is not None else None,
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
            intraday_chg = self._intraday_change_pct(intraday_bars, sym)
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
                "intraday_change_pct": (round(intraday_chg, 4)
                                        if intraday_chg is not None else None),
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
            "approval_threshold_usd": float(self.cfg.get(
                "kill_switch", "approval_threshold_usd", default=25000)),
            "spy_treated_as_liquid": bool(self.cash_proxy_enabled),
            "spy_can_be_freely_converted_to_cash": bool(self.cash_proxy_enabled),
            "cash_proxy_min_rebalance_usd": float(self.cash_proxy_min),
        }

        # --- System state ---
        system_state = {
            "kill_switch_halted": bool((kill_state or {}).get("halted", False)),
            "kill_switch_reasons": (kill_state or {}).get("reasons", []) or [],
            "weekly_return": (kill_state or {}).get("weekly_return"),
            "daily_return": (kill_state or {}).get("daily_return"),
            "trades_today": (kill_state or {}).get("trades_today"),
            "bearish_halt_active": bool(bearish_halt),
            "dry_run": bool(dry_run),
            "rebalance_use_ai_arbiter": bool(self.rebalance_use_ai_arbiter),
        }

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

        The Opus 4.7 portfolio arbiter is the FINAL authority — it sees the full
        book + every rule + intraday context and returns quantitative target
        allocations including a SPY-vs-cash split. The executor only translates
        targets into trades. Deterministic logic does not override the AI.

        Returns list of applied action dicts. If allow_adds=False, only trims
        run (bearish-halt mode unless a position clears the high-conviction
        override).
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
            return []

        # --- BEFORE snapshot (logged after the run for diff context) ---
        before_snapshot = self._snapshot_portfolio(equity)

        # --- AI portfolio arbiter: ONE call decides target weights for all held ---
        ai_target_weights: dict[str, float] | None = None
        ai_per_symbol: dict[str, dict] | None = None
        ai_spy_target_pct: float | None = None
        ai_cash_target_pct: float | None = None
        arbiter_result: dict[str, Any] | None = None
        arbiter_ctx: dict[str, Any] | None = None
        if self.rebalance_use_ai_arbiter and self.ai.available():
            arbiter_ctx = self._build_arbiter_context(
                holdings=holdings, tech_map=tech_map, sent_map=sent_map,
                numeric=numeric, earnings_map=earnings_map, macro=macro, equity=equity,
                kill_state=kill_state, bearish_halt=bearish_halt, dry_run=dry_run,
            )
            log.info(
                "Rebalance: invoking portfolio arbiter (model=%s) on %d held positions, "
                "equity=$%.0f, cash=$%.0f, BP=$%.0f, SPY=$%.0f",
                self.cfg.get("ai", "trade_critical_model", default="?"),
                len(holdings),
                arbiter_ctx["equity"],
                arbiter_ctx["cash"]["balance"],
                arbiter_ctx["cash"]["buying_power"],
                arbiter_ctx["spy_block"]["current_value_usd"],
            )
            log_decision({
                "event": "portfolio_arbiter_input",
                "context": arbiter_ctx,
            })
            arbiter_result = run_portfolio_arbiter(self.cfg, arbiter_ctx)
            log_decision({
                "event": "portfolio_arbiter_output",
                "result": arbiter_result,
            })
            if arbiter_result:
                ai_target_weights = {
                    str(k): float(v)
                    for k, v in (arbiter_result.get("target_weights") or {}).items()
                }
                ai_per_symbol = arbiter_result.get("per_symbol") or {}
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
                for mv in (arbiter_result.get("capital_movement_plan") or []):
                    log.info("Arbiter capital plan: %s %s$%.0f — %s",
                             mv.get("symbol"),
                             "+" if float(mv.get("delta_usd", 0) or 0) >= 0 else "-",
                             abs(float(mv.get("delta_usd", 0) or 0)),
                             (mv.get("purpose") or ""))
                for flag in (arbiter_result.get("risk_flags") or []):
                    log.info("Arbiter risk flag: %s", flag)
            else:
                log.warning("Portfolio arbiter unavailable — falling back to softmax conviction weights")

        # --- Build plan ---
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

        # --- Fix 1: drop rebalance ADDS for symbols already flagged for earnings exit ---
        # Earnings-close must win; we cannot simultaneously close and scale up.
        if earnings_exit_symbols:
            before = len(plan)
            plan = [
                a for a in plan
                if not (a.symbol in earnings_exit_symbols and a.current_notional < a.target_notional)
            ]
            dropped = before - len(plan)
            if dropped:
                log.info("Rebalance: dropped %d add(s) that conflict with earnings exits: %s",
                         dropped, earnings_exit_symbols & {a.symbol for a in plan})

        # --- Fix 2: block large adds when AI arbiter didn't run (softmax fallback) ---
        # Without the full-book arbiter, we shouldn't make big sizing decisions.
        if arbiter_result is None:
            filtered_plan = []
            for a in plan:
                is_add = a.current_notional < a.target_notional
                large_add = is_add and (
                    a.blended_confidence >= self.rebal_require_ai_conf
                    or a.delta_notional >= self.rebal_require_ai_usd
                )
                if large_add:
                    log.info("[%s] rebalance large add blocked: arbiter unavailable "
                             "(conf=%.2f, delta=$%.0f)", a.symbol, a.blended_confidence, a.delta_notional)
                else:
                    filtered_plan.append(a)
            plan = filtered_plan

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
                # Verify cash before adding
                self._ensure_cash_for(a.delta_notional, equity)
            exec_result = self.executor.partial_trade(
                symbol=a.symbol, side=a.side,
                delta_notional=a.delta_notional,
                reason=a.reason,
            )
            results.append({**a.to_dict(), "execution": exec_result.to_dict()})
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
            try:
                self.client.submit_notional(self.cash_proxy_symbol, sell_amt, side="sell")
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
            except Exception as e:
                log.warning("SPY rebalance sell failed: %s", e)
                return {"symbol": self.cash_proxy_symbol, "action": "sell_failed", "error": str(e)}
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

    # ---------- main loop ----------
    def run_scan(self, max_candidates: int = 25, dry_run: bool = False) -> dict[str, Any]:
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

        # Exits first (hard signals — unchanged logic)
        exit_results: list[dict[str, Any]] = []
        exits = self.evaluate_exits(macro, portfolio=portfolio)
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
                self._ensure_cash_for(sizing.notional, equity)
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
                    self._ensure_cash_for(sizing.notional, equity)
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
