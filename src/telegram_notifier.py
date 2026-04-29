"""Telegram notifications for scheduled tasks and alerts."""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# Ensure .env is loaded
_root = Path(__file__).resolve().parents[1]
load_dotenv(_root / ".env")

log = logging.getLogger(__name__)


def _get_phoenix_timestamp() -> str:
    """Return current time in Phoenix (MST) timezone as formatted string."""
    from datetime import datetime, timedelta
    utc_now = datetime.now(timezone.utc)
    phoenix_tz = timezone(timedelta(hours=-7))
    phoenix_now = utc_now.astimezone(phoenix_tz)
    return phoenix_now.strftime("%Y-%m-%d %H:%M:%S")


def _esc(s: Any) -> str:
    """Escape a value for Telegram HTML parse_mode (<, >, &)."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _format_number(val: float) -> str:
    """Format number with sign and 2 decimals."""
    if val >= 0:
        return f"+{val:.2f}"
    return f"{val:.2f}"


def _is_rebalance_shape(ex: dict[str, Any]) -> bool:
    """Detect a selector-rebalance execution dict.

    Rebalance items get rendered in the dedicated AI REBALANCE block, so we
    must exclude them from the DECISIONS loop or they appear twice (once
    correctly, once as garbage with ``?`` placeholders because the notifier's
    DECISIONS code expects nested ``sizing``/``decision`` dicts).

    Heuristic: presence of ``ai_action`` (RebalanceAction.to_dict's signature
    field) AND no nested ``sizing`` dict.
    """
    if "sizing" in ex and isinstance(ex.get("sizing"), dict) and ex["sizing"]:
        return False
    return bool(ex.get("ai_action")) or "delta_notional" in ex


def _format_money(val: Any) -> str:
    """Render a numeric or '?' as a money string.

    Returns ``"?"`` only if val is None / non-numeric, never silently zero.
    """
    if val is None or val == "?":
        return "?"
    try:
        f = float(val)
    except (TypeError, ValueError):
        return "?"
    return f"{f:,.2f}"


def _normalize_execution(
    ex: dict[str, Any],
    decisions_by_symbol: dict[str, dict[str, Any]] | None = None,
    equity: float = 0.0,
) -> dict[str, Any]:
    """Return a uniform shape for a DECISIONS-block execution.

    Reads nested ``sizing``/``decision`` dicts when present (legacy/new-entry
    path), then falls back to top-level keys (selector-skipped path), then
    looks up the matching ``decision`` from the orchestrator's decisions list
    by symbol so RSI/scores/details survive even when the execution dict
    didn't carry them.
    """
    sizing = ex.get("sizing") or {}
    decision = ex.get("decision") or {}
    sym = (
        decision.get("symbol")
        or sizing.get("symbol")
        or ex.get("symbol")
        or "?"
    )
    if decisions_by_symbol and sym in decisions_by_symbol and not decision:
        decision = decisions_by_symbol[sym]

    action = decision.get("action") or ex.get("side") or "?"
    if action == "buy":
        side_label = "BUY"
    elif action == "sell":
        side_label = "SELL"
    else:
        side_label = str(action).upper()

    qty = sizing.get("qty", ex.get("qty", "?"))
    entry = sizing.get("entry", sizing.get("entry_price", ex.get("entry", "?")))
    stop = sizing.get("stop_loss", sizing.get("stop_price", ex.get("stop", "?")))
    target = sizing.get("take_profit", sizing.get("target_price", ex.get("target", "?")))
    notional = sizing.get("notional") or ex.get("notional") or ex.get("delta_notional") or 0.0
    notional = float(notional or 0.0)
    if equity:
        position_pct = notional / equity
    else:
        position_pct = float(sizing.get("position_pct", 0.0) or 0.0)

    return {
        "kind": (
            "skipped" if ex.get("skipped")
            else "entry"
        ),
        "skipped": ex.get("skipped"),
        "symbol": sym,
        "side_label": side_label,
        "qty": qty,
        "entry": entry,
        "stop": stop,
        "target": target,
        "notional": notional,
        "position_pct": position_pct,
        "signal_scores": decision.get("signal_scores", {}) or {},
        "signal_details": decision.get("signal_details", {}) or {},
        "risk_sizer": ex.get("risk_sizer") or sizing.get("limits") or {},
        "reason": ex.get("reason") or ex.get("message") or "",
    }


class TelegramNotifier:
    def __init__(self, token: str | None = None, chat_id: str | None = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def _send(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send raw message to Telegram. Returns True if successful."""
        if not self.token or not self.chat_id:
            log.warning("Telegram notifier not configured (token=%s, chat_id=%s)",
                       bool(self.token), bool(self.chat_id))
            return False
        try:
            resp = requests.post(
                self.api_url,
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": parse_mode,
                },
                timeout=10,
            )
            if resp.status_code != 200:
                log.warning("Telegram send failed: status=%d body=%s", resp.status_code, resp.text)
                return False
            return True
        except Exception as e:
            log.warning("Telegram send error: %s", e)
            return False

    # ---------- Scan & Trade Notifications ----------

    def notify_scan_execution(
        self,
        scan_name: str,
        macro: dict[str, Any],
        decisions: list[dict[str, Any]],
        executions: list[dict[str, Any]],
        exits: list[dict[str, Any]],
        equity: float = 0,
        positions_count: int = 0,
        daily_pnl: float = 0.0,
        daily_pnl_pct: float = 0.0,
        spy_daily_pct: float = 0.0,
        ai_verdicts: dict[str, Any] | None = None,
        ai_active: bool = False,
        rebalance: list[dict[str, Any]] | None = None,
        opportunity_ranking: list[str] | None = None,
        ai_arbiter_skipped: str | None = None,
    ) -> bool:
        """Format and send clean scan execution notification focused on decisions."""
        ts = _get_phoenix_timestamp()
        msg = f"SCAN {scan_name} | {ts}\n"
        msg += "─" * 20 + "\n\n"

        # P&L Section. "Account" = total balance (cash + position market
        # value), not market-value-only. Daily % is anchored to today's
        # baseline equity (computed by daily_pnl module), not Alpaca's data.
        msg += "<b>ACCOUNT STATUS</b>\n"
        pnl_icon = "▲" if daily_pnl_pct >= 0 else "▼"
        spy_comp = daily_pnl_pct - spy_daily_pct
        spy_icon = "▲" if spy_comp >= 0 else "▼"
        msg += f"Account: ${equity:,.0f} | Daily: {pnl_icon} {daily_pnl_pct*100:+.2f}% (${daily_pnl:+,.0f})\n"
        msg += f"vs S&P 500: {spy_icon} {spy_comp*100:+.2f}% (S&P: {spy_daily_pct*100:+.2f}%)\n"
        msg += f"Positions: {positions_count}\n\n"

        # Decisions - exclude rebalance-shape executions (they render in the
        # AI REBALANCE block below). Look up missing decision metadata from
        # the orchestrator's full decisions list by symbol.
        decisions_by_symbol = {
            d.get("symbol"): d for d in (decisions or []) if d.get("symbol")
        }
        decision_executions = [
            ex for ex in (executions or [])
            if not ex.get("dry_run") and not _is_rebalance_shape(ex)
        ]

        msg += "<b>DECISIONS</b>\n"
        decisions_body = ""

        # Entries (and any selector-path skipped items)
        for ex in decision_executions:
            norm = _normalize_execution(ex, decisions_by_symbol, equity=equity)

            if norm["kind"] == "skipped":
                decisions_body += (
                    f"\n⊘ SKIP {_esc(norm['symbol'])} — {_esc(norm['skipped'])}"
                )
                if norm["reason"]:
                    decisions_body += f" ({_esc(norm['reason'])})"
                decisions_body += "\n"
                continue

            signal_details = norm["signal_details"]
            tech_detail = signal_details.get("technical", {}) or {}
            fund_detail = signal_details.get("fundamental", {}) or {}
            earn_detail = signal_details.get("earnings", {}) or {}

            tech_score = norm["signal_scores"].get("technical", 0.0)
            tech_reason = tech_detail.get("rsi")
            tech_str = f"RSI {tech_reason}" if tech_reason is not None else "RSI N/A"

            fund_reason = "N/A"
            if fund_detail:
                pe = fund_detail.get("pe_ratio", "N/A")
                growth = fund_detail.get("revenue_growth", 0.0)
                fund_reason = f"PE {pe} | Growth {growth:+.0%}"

            entry_s = _format_money(norm["entry"])
            stop_s = _format_money(norm["stop"])
            target_s = _format_money(norm["target"])

            decisions_body += f"\n{norm['side_label']} {_esc(norm['symbol'])}\n"
            decisions_body += (
                f"  Entry: ${entry_s} | Stop: ${stop_s} | Target: ${target_s} "
                f"(Size: {norm['position_pct']:.1%})\n"
            )

            risk_sizer = norm["risk_sizer"]
            if risk_sizer:
                risk_notional = (
                    risk_sizer.get("post_cash_cap_notional")
                    or risk_sizer.get("post_selector_cap_notional")
                    or risk_sizer.get("final_notional")
                    or risk_sizer.get("risk_sized_notional")
                )
                selector_notional = risk_sizer.get("selector_target_notional")
                limiter = risk_sizer.get("limiting_factor") or risk_sizer.get("post_risk_cap_reason")
                if risk_notional:
                    decisions_body += f"  Risk sizer: ${float(risk_notional):,.0f}"
                    if selector_notional:
                        decisions_body += f" vs selector ${float(selector_notional):,.0f}"
                    if limiter:
                        decisions_body += f" ({_esc(limiter)})"
                    decisions_body += "\n"

            decisions_body += f"  Technical: {tech_score:+.2f} ({tech_str})\n"
            decisions_body += f"  Fundamental: {fund_reason}\n"
            days_until = earn_detail.get("days_until_earnings")
            if days_until is not None:
                decisions_body += (
                    f"  Earnings: {earn_detail.get('next_earnings_date','?')} (in {days_until}d)\n"
                )

        # Exits
        for exit_item in (exits or []):
            sym = exit_item.get("symbol", "?")
            reason = exit_item.get("reason", exit_item.get("message", "?"))
            decisions_body += f"\n⊘ CLOSE {_esc(sym)}\n"
            decisions_body += f"  Reason: {_esc(reason)}\n"

        # Defensive: if everything got filtered out, fall back to "holding"
        # rather than emitting an empty DECISIONS section.
        if not decisions_body.strip():
            decisions_body = "No action taken (holding)\n"
        msg += decisions_body + "\n"

        # AI Rebalance section — every action carries one_sentence_reason
        # and opportunity_score from the Opus 4.7 portfolio arbiter.
        if ai_arbiter_skipped:
            msg += "<b>AI REBALANCE</b>\n"
            msg += f"⚠️ Skipped: {_esc(ai_arbiter_skipped)} (no trades executed)\n\n"
        elif rebalance:
            msg += "<b>AI REBALANCE</b>\n"
            for a in rebalance:
                if a.get("event") == "spy_rebalance":
                    sym = a.get("symbol", "SPY")
                    action = a.get("action", "?")
                    delta = float(a.get("delta_usd", 0) or 0)
                    sign = "+" if delta >= 0 else ""
                    msg += f"\n{_esc(sym)} {action.upper()} ({sign}${delta:,.0f})\n"
                    continue
                sym = a.get("symbol", "?")
                ai_action = a.get("ai_action") or ("ADD" if a.get("side") == "buy" else "TRIM")
                delta_notional = float(a.get("delta_notional", 0) or 0)
                # Convention: "sell" reduces longs (negative cash impact for the position)
                signed = -delta_notional if a.get("side") == "sell" else delta_notional
                opp = a.get("opportunity_score", 0)
                target_pct = float(a.get("target_pct", 0) or 0) * 100
                osr = a.get("one_sentence_reason") or a.get("reason") or ""
                msg += (f"\n{_esc(ai_action)} {_esc(sym)} "
                        f"({signed:+,.0f} → {target_pct:.1f}%, opp={opp:.0f})\n")
                if osr:
                    msg += f"  {_esc(osr)}\n"
            if opportunity_ranking:
                ranked = " > ".join(_esc(s) for s in opportunity_ranking[:8])
                msg += f"\nRanking: {ranked}\n"
            msg += "\n"

        # Top candidates (for context)
        top_actionable = [d for d in decisions if d.get("action") == "buy"]
        if not top_actionable and decisions:
            top_candidates = sorted(decisions, key=lambda d: abs(d.get("combined_score", 0)), reverse=True)[:3]
            msg += "<b>TOP CANDIDATES SCREENED (Held)</b>\n"
            for d in top_candidates:
                sym = d.get("symbol", "?")
                score = d.get("combined_score", 0.0)
                action = "BUY" if score > 0 else "HOLD"
                msg += f"  {sym}: {action} {score:+.2f}\n"

        return self._send(msg)

    # ---------- Premarket Brief Notifications ----------

    def notify_premarket(
        self,
        macro: dict[str, Any],
        positions_count: int = 0,
        total_pnl: float = 0.0,
        cancelled_orders: int = 0,
        positions_list: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Format and send premarket brief notification."""
        ts = _get_phoenix_timestamp()
        msg = f"PREMARKET | {ts}\n"
        msg += "─" * 20 + "\n\n"

        # Market context
        msg += "<b>MARKET</b>\n"
        regime = macro.get('regime', '?')
        msg += f"Regime: {regime} | SPY: {macro.get('spy_trend', 0):+.1f}% | VIX: {macro.get('vix_regime', '?')}\n\n"

        # Cancelled orders
        if cancelled_orders > 0:
            msg += f"Cancelled {cancelled_orders} stale orders\n\n"

        # Positions snapshot
        msg += f"<b>POSITIONS</b> ({positions_count} open)\n"
        if positions_list:
            for p in positions_list[:10]:  # Show first 10
                sym = p.get("symbol", "?")
                side = p.get("side", "?")
                qty = p.get("qty", "?")
                unrealized = p.get("unrealized_pnl", 0.0)
                icon = "▲" if unrealized >= 0 else "▼"
                line = f"  {icon} {sym:5} {side:5} {qty:>4} sh | P&L: {unrealized:+,.0f}"
                days_until = p.get("earnings_days")
                if days_until is not None and days_until <= 7:
                    line += f" | ⚠ earnings in {days_until}d"
                msg += line + "\n"

        if total_pnl != 0:
            icon = "▲" if total_pnl >= 0 else "▼"
            msg += f"\nTotal P&L: {icon} {total_pnl:+,.0f}\n"

        return self._send(msg)

    # ---------- EOD Report Notifications ----------

    def notify_eod(
        self,
        daily_return: float = 0.0,
        daily_vs_spy: float = 0.0,
        spy_daily: float = 0.0,
        trades_today: int = 0,
        positions_count: int = 0,
        equity: float = 0.0,
        cash: float = 0.0,
    ) -> bool:
        """Format and send EOD report notification."""
        ts = _get_phoenix_timestamp()
        msg = f"EOD REPORT | {ts}\n"
        msg += "─" * 20 + "\n\n"

        # Daily P&L
        pnl_icon = "▲" if daily_return >= 0 else "▼"
        spy_comp = daily_vs_spy
        spy_icon = "▲" if spy_comp >= 0 else "▼"

        msg += "<b>PERFORMANCE</b>\n"
        msg += f"Daily: {pnl_icon} {daily_return * 100:+.2f}%\n"
        msg += f"vs S&P 500: {spy_icon} {spy_comp * 100:+.2f}% (S&P: {spy_daily * 100:+.2f}%)\n\n"

        # Summary — single Account line per user preference (cash + positions
        # combined; the user wants total balance, not the cash/equity split).
        msg += "<b>SUMMARY</b>\n"
        msg += f"Trades: {trades_today} | Positions: {positions_count} open\n"
        msg += f"Account: ${equity:,.0f}\n"

        return self._send(msg)

    # ---------- Weekly Review Notifications ----------

    def notify_weekly(
        self,
        weekly_return: float = 0.0,
        weekly_vs_spy: float = 0.0,
        monthly_return: float = 0.0,
        monthly_vs_spy: float = 0.0,
        trades_week: int = 0,
        trades_month: int = 0,
        best_performer: str = "",
        worst_performer: str = "",
        win_rate: float = 0.0,
    ) -> bool:
        """Format and send weekly review notification."""
        ts = _get_phoenix_timestamp()
        msg = f"WEEKLY REVIEW | {ts}\n"
        msg += "─" * 20 + "\n\n"

        # Weekly return
        week_icon = "▲" if weekly_return >= 0 else "▼"
        week_spy_icon = "▲" if weekly_vs_spy >= 0 else "▼"
        msg += "<b>1-WEEK</b>\n"
        msg += f"Return: {week_icon} {weekly_return * 100:+.2f}%\n"
        msg += f"vs S&P: {week_spy_icon} {weekly_vs_spy * 100:+.2f}%\n\n"

        # Monthly return
        month_icon = "▲" if monthly_return >= 0 else "▼"
        month_spy_icon = "▲" if monthly_vs_spy >= 0 else "▼"
        msg += "<b>1-MONTH</b>\n"
        msg += f"Return: {month_icon} {monthly_return * 100:+.2f}%\n"
        msg += f"vs S&P: {month_spy_icon} {monthly_vs_spy * 100:+.2f}%\n\n"

        # Trade stats
        msg += "<b>TRADES</b>\n"
        msg += f"This Week: {trades_week} | This Month: {trades_month}\n"
        msg += f"Win Rate: {win_rate:.1%}\n"

        # Best/worst performers
        if best_performer or worst_performer:
            msg += "\n<b>PERFORMERS</b>\n"
            if best_performer:
                msg += f"Best: {best_performer}\n"
            if worst_performer:
                msg += f"Worst: {worst_performer}\n"

        return self._send(msg)

    # ---------- Preclose Notifications ----------

    def notify_preclose(
        self,
        equity: float,
        positions_count: int,
        market_bias: float,
        hold_reports: list[dict[str, Any]],
        exits: list[dict[str, Any]],
        new_executions: list[dict[str, Any]],
        bearish_halt: bool = False,
        halt_threshold: float = -0.55,
        dry_run: bool = False,
    ) -> bool:
        """Format and send preclose overnight-decision notification."""
        ts = _get_phoenix_timestamp()
        suffix = " [DRY]" if dry_run else ""
        msg = f"PRECLOSE{suffix} | {ts}\n"
        msg += "─" * 20 + "\n\n"

        if bearish_halt:
            msg += f"⚠️  BEARISH HALT: market_bias={market_bias:+.2f} ≤ {halt_threshold:+.2f} — no new overnight buys\n\n"

        bias_icon = "▲" if market_bias >= 0 else "▼"
        msg += "<b>ACCOUNT</b>\n"
        msg += f"Account: ${equity:,.0f} | Positions: {positions_count}\n"
        msg += f"SPY late-day bias: {bias_icon} {market_bias:+.2f}\n\n"

        held = sum(1 for r in hold_reports if r.get("decision") in ("hold", "hold_no_data"))
        closed = len(exits)
        bought = len([x for x in new_executions if not x.get("dry_run")])
        dry_bought = len([x for x in new_executions if x.get("dry_run")])

        msg += "<b>OVERNIGHT DECISIONS</b>\n"
        msg += f"Held: {held} | Closed: {closed} | New buys: {bought + dry_bought}\n"

        if exits:
            msg += "\n<b>CLOSED</b>\n"
            for ex in exits:
                sym = ex.get("symbol", "?")
                reason = ex.get("reason", ex.get("message", "?"))
                msg += f"  ⊘ {_esc(sym)} — {_esc(reason)}\n"

        if new_executions:
            msg += "\n<b>NEW OVERNIGHT BUYS</b>\n"
            for x in new_executions:
                sizing = x.get("sizing", {})
                decision = x.get("decision", {})
                sym = sizing.get("symbol", decision.get("symbol", "?"))
                qty = sizing.get("qty", "?")
                entry = sizing.get("entry", "?")
                notional = sizing.get("notional", 0.0)
                pct = (notional / equity) if equity else 0.0
                ov = (decision.get("signal_scores", {}) or {}).get("overnight", 0.0)
                tag = " [DRY]" if x.get("dry_run") else ""
                msg += f"  BUY {sym}{tag} qty={qty} @ ${entry} (${notional:,.0f}, {pct:.1%}) ov={ov:+.2f}\n"

        return self._send(msg)

    # ---------- Alert Notifications ----------

    def send_alert(
        self,
        alert_type: str,
        task_name: str,
        message: str,
        error_details: str = "",
    ) -> bool:
        """Send immediate alert (error, halt, etc.)."""
        ts = _get_phoenix_timestamp()
        msg = f"⚠️  {alert_type} | {task_name} | {ts}\n"
        msg += "─" * 20 + "\n\n"
        msg += f"{message}\n"
        if error_details:
            msg += f"\nDetails:\n<code>{_esc(error_details[:500])}</code>\n"

        return self._send(msg)


# Module-level convenience functions
_notifier = None


def get_notifier() -> TelegramNotifier:
    """Get or create the global notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier


def notify_scan_execution(
    scan_name: str,
    macro: dict[str, Any],
    decisions: list[dict[str, Any]],
    executions: list[dict[str, Any]],
    exits: list[dict[str, Any]],
    **kwargs: Any,
) -> bool:
    """Convenience function for scan notifications."""
    return get_notifier().notify_scan_execution(
        scan_name, macro, decisions, executions, exits, **kwargs
    )


def notify_premarket(
    macro: dict[str, Any],
    **kwargs: Any,
) -> bool:
    """Convenience function for premarket notifications."""
    return get_notifier().notify_premarket(macro, **kwargs)


def notify_eod(**kwargs: Any) -> bool:
    """Convenience function for EOD notifications."""
    return get_notifier().notify_eod(**kwargs)


def notify_preclose(**kwargs: Any) -> bool:
    """Convenience function for preclose notifications."""
    return get_notifier().notify_preclose(**kwargs)


def notify_weekly(**kwargs: Any) -> bool:
    """Convenience function for weekly notifications."""
    return get_notifier().notify_weekly(**kwargs)


def send_alert(alert_type: str, task_name: str, message: str, **kwargs: Any) -> bool:
    """Convenience function for alerts."""
    return get_notifier().send_alert(alert_type, task_name, message, **kwargs)
