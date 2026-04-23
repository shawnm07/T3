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


def _format_number(val: float) -> str:
    """Format number with sign and 2 decimals."""
    if val >= 0:
        return f"+{val:.2f}"
    return f"{val:.2f}"


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
        kill_switch: dict[str, Any] | None = None,
        equity: float = 0,
        positions_count: int = 0,
        daily_pnl: float = 0.0,
        daily_pnl_pct: float = 0.0,
        spy_daily_pct: float = 0.0,
        ai_verdicts: dict[str, Any] | None = None,
        ai_active: bool = False,
    ) -> bool:
        """Format and send clean scan execution notification focused on decisions."""
        ts = _get_phoenix_timestamp()
        msg = f"SCAN {scan_name} | {ts}\n"
        msg += "─" * 20 + "\n\n"

        # Kill switch alert
        if kill_switch and kill_switch.get("halted"):
            reasons = kill_switch.get("reasons", [])
            msg += f"⚠️  HALTED: {', '.join(reasons)}\n\n"
            self._send(msg)
            return True

        # P&L Section
        msg += "<b>ACCOUNT STATUS</b>\n"
        pnl_icon = "▲" if daily_pnl_pct >= 0 else "▼"
        spy_comp = daily_pnl_pct - spy_daily_pct
        spy_icon = "▲" if spy_comp >= 0 else "▼"
        msg += f"Equity: ${equity:,.0f} | Daily: {pnl_icon} {daily_pnl_pct*100:+.2f}% (${daily_pnl:+,.0f})\n"
        msg += f"vs S&P 500: {spy_icon} {spy_comp*100:+.2f}% (S&P: {spy_daily_pct*100:+.2f}%)\n"
        msg += f"Positions: {positions_count}\n\n"

        # Decisions - focus on what was traded
        if executions or exits:
            msg += "<b>DECISIONS</b>\n"

            # Entries
            for ex in executions:
                if ex.get("dry_run"):
                    continue
                sizing = ex.get("sizing", {})
                decision = ex.get("decision", {})
                sym = decision.get("symbol", "?")
                action = decision.get("action", "?")
                side = "BUY" if action == "buy" else "SHORT"

                qty = sizing.get("qty", "?")
                entry = sizing.get("entry_price", "?")
                stop = sizing.get("stop_price", "?")
                target = sizing.get("target_price", "?")
                position_pct = sizing.get("position_pct", 0.0)

                signals = decision.get("signal_scores", {})
                signal_details = decision.get("signal_details", {})
                tech_detail = signal_details.get("technical", {})
                fund_detail = signal_details.get("fundamental", {})

                # Technical summary
                tech_score = signals.get("technical", 0.0)
                tech_reason = tech_detail.get("rsi", "N/A")

                # Fundamental summary (one line)
                fund_reason = "N/A"
                if fund_detail:
                    pe = fund_detail.get("pe_ratio", "N/A")
                    growth = fund_detail.get("revenue_growth", 0.0)
                    fund_reason = f"PE {pe} | Growth {growth:+.0%}"

                msg += f"\n{side} {sym}\n"
                msg += f"  Entry: ${entry} | Stop: ${stop} | Target: ${target} (Size: {position_pct:.1%})\n"
                msg += f"  Technical: {tech_score:+.2f} (RSI {tech_reason})\n"
                msg += f"  Fundamental: {fund_reason}\n"

            # Exits
            for exit_item in exits:
                sym = exit_item.get("symbol", "?")
                reason = exit_item.get("reason", "?")
                msg += f"\n⊘ CLOSE {sym}\n"
                msg += f"  Reason: {reason}\n"

            msg += "\n"

        else:
            msg += "<b>DECISIONS</b>\n"
            msg += "No action taken (holding)\n\n"

        # Top candidates (for context)
        top_actionable = [d for d in decisions if d.get("action") in ("buy", "sell_short")]
        if not top_actionable and decisions:
            top_candidates = sorted(decisions, key=lambda d: abs(d.get("combined_score", 0)), reverse=True)[:3]
            msg += "<b>TOP CANDIDATES SCREENED (Held)</b>\n"
            for d in top_candidates:
                sym = d.get("symbol", "?")
                score = d.get("combined_score", 0.0)
                action = "BUY" if score > 0 else "SHORT"
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
                msg += f"  {icon} {sym:5} {side:5} {qty:>4} sh | P&L: {unrealized:+,.0f}\n"

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

        # Summary
        msg += "<b>SUMMARY</b>\n"
        msg += f"Trades: {trades_today} | Positions: {positions_count} open\n"
        msg += f"Equity: ${equity:,.0f} | Cash: ${cash:,.0f}\n"

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
        kill_switch: dict[str, Any] | None = None,
        bearish_halt: bool = False,
        halt_threshold: float = -0.55,
        dry_run: bool = False,
    ) -> bool:
        """Format and send preclose overnight-decision notification."""
        ts = _get_phoenix_timestamp()
        suffix = " [DRY]" if dry_run else ""
        msg = f"PRECLOSE{suffix} | {ts}\n"
        msg += "─" * 20 + "\n\n"

        if kill_switch and kill_switch.get("halted"):
            reasons = kill_switch.get("reasons", [])
            msg += f"⚠️  HALTED: {', '.join(reasons)}\n"
            return self._send(msg)

        if bearish_halt:
            msg += f"⚠️  BEARISH HALT: market_bias={market_bias:+.2f} ≤ {halt_threshold:+.2f} — no new overnight buys\n\n"

        bias_icon = "▲" if market_bias >= 0 else "▼"
        msg += "<b>ACCOUNT</b>\n"
        msg += f"Equity: ${equity:,.0f} | Positions: {positions_count}\n"
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
                msg += f"  ⊘ {sym} — {reason}\n"

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
            msg += f"\nDetails:\n<code>{error_details[:500]}</code>\n"

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
    kill_switch: dict[str, Any] | None = None,
    **kwargs: Any,
) -> bool:
    """Convenience function for scan notifications."""
    return get_notifier().notify_scan_execution(
        scan_name, macro, decisions, executions, exits, kill_switch, **kwargs
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
