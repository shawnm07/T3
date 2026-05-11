"""Telegram notifications for bot status, scans, and alerts.

This module is intentionally presentation-only. Account balance and positions
must be passed in after the caller has built an independent valuation snapshot:
Alpaca is allowed for cash and share quantities, but market prices must come
from non-Alpaca providers.
"""
from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv

_root = Path(__file__).resolve().parents[1]
load_dotenv(_root / ".env")

log = logging.getLogger(__name__)

_MAX_TELEGRAM_LEN = 3800


def _get_phoenix_timestamp() -> str:
    phoenix_tz = timezone(timedelta(hours=-7))
    return datetime.now(phoenix_tz).strftime("%Y-%m-%d %H:%M:%S")


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except (TypeError, ValueError):
        return default


def _fmt_money(value: Any, decimals: int = 0) -> str:
    return f"${_to_float(value):,.{decimals}f}"


def _fmt_signed_money(value: Any, decimals: int = 0) -> str:
    val = _to_float(value)
    sign = "+" if val >= 0 else "-"
    return f"{sign}${abs(val):,.{decimals}f}"


def _fmt_pct(value: Any, decimals: int = 2, signed: bool = True) -> str:
    val = _to_float(value) * 100.0
    sign = "+" if signed and val >= 0 else ""
    return f"{sign}{val:.{decimals}f}%"


def _fmt_qty(value: Any) -> str:
    val = _to_float(value)
    if abs(val - round(val)) < 1e-6:
        return f"{val:,.0f}"
    return f"{val:,.4f}".rstrip("0").rstrip(".")


def _short_text(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _source_summary(positions: Iterable[Any] | None) -> str:
    sources: set[str] = set()
    missing: list[str] = []
    for p in positions or []:
        source = str(_get(p, "price_source", "") or "")
        if source:
            sources.add(source)
        if source.startswith("fallback") or source in {"", "missing"}:
            sym = str(_get(p, "symbol", "?"))
            missing.append(sym)
    if not sources:
        return "prices: not provided"
    ordered = ", ".join(sorted(sources))
    if missing:
        ordered += f" | missing live external price: {', '.join(missing[:8])}"
    return f"prices: {ordered}"


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _position_rows(positions: Iterable[Any] | None, account_balance: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in positions or []:
        sym = str(_get(p, "symbol", "") or "")
        if not sym or "/" in sym:
            continue
        mv = abs(_to_float(_get(p, "market_value", 0)))
        qty = abs(_to_float(_get(p, "qty", 0)))
        price = _to_float(_get(p, "current_price", 0))
        avg_entry = _to_float(_get(p, "avg_entry_price", 0))
        weight = (mv / account_balance) if account_balance > 0 else 0.0
        if avg_entry > 0 and price > 0 and qty > 0:
            pnl = (price - avg_entry) * qty
            pnl_pct = (price / avg_entry) - 1
        else:
            pnl = _to_float(_get(p, "unrealized_pl", 0))
            pnl_pct = _to_float(_get(p, "unrealized_plpc", 0))
        rows.append({
            "symbol": sym,
            "qty": qty,
            "avg_entry": avg_entry,
            "price": price,
            "market_value": mv,
            "weight": weight,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "source": str(_get(p, "price_source", "") or "?"),
        })
    rows.sort(key=lambda r: r["market_value"], reverse=True)
    return rows


def _split_message(message: str, max_len: int = _MAX_TELEGRAM_LEN) -> list[str]:
    if len(message) <= max_len:
        return [message]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in message.splitlines():
        line_len = len(line) + 1
        if line_len > max_len:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            for i in range(0, len(line), max_len):
                chunks.append(line[i:i + max_len])
            continue
        if current and current_len + line_len > max_len:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len
    if current:
        chunks.append("\n".join(current))
    if len(chunks) == 1:
        return chunks
    total = len(chunks)
    return [f"[{idx}/{total}]\n{chunk}" for idx, chunk in enumerate(chunks, start=1)]


def _execution_status(row: dict[str, Any]) -> str:
    if row.get("dry_run"):
        return "dry-run"
    if row.get("skipped"):
        return f"skipped: {row.get('skipped')}"
    ex = row.get("execution") or {}
    status = ex.get("final_status") or ex.get("status") or row.get("final_status") or row.get("status")
    if not status:
        return "submitted"
    ok = ex.get("ok", row.get("ok"))
    if ok is True and status != "filled":
        return f"{status}, filled"
    return str(status)


def _trade_side(row: dict[str, Any]) -> str:
    sizing = row.get("sizing") or {}
    decision = row.get("decision") or {}
    side = row.get("side") or sizing.get("side") or decision.get("action") or ""
    return str(side).lower()


def _trade_symbol(row: dict[str, Any]) -> str:
    sizing = row.get("sizing") or {}
    decision = row.get("decision") or {}
    return str(row.get("symbol") or sizing.get("symbol") or decision.get("symbol") or "?")


def _trade_delta_notional(row: dict[str, Any]) -> float:
    sizing = row.get("sizing") or {}
    if row.get("delta_notional") is not None:
        return abs(_to_float(row.get("delta_notional")))
    if row.get("delta_usd") is not None:
        return abs(_to_float(row.get("delta_usd")))
    if row.get("notional") is not None:
        return abs(_to_float(row.get("notional")))
    return abs(_to_float(sizing.get("notional")))


def _trade_reason(row: dict[str, Any], decision: dict[str, Any] | None = None) -> str:
    decision = decision or row.get("decision") or {}
    reason = row.get("one_sentence_reason") or decision.get("reason") or row.get("reason")
    if not reason:
        reasoning = decision.get("reasoning")
        if isinstance(reasoning, list) and reasoning:
            reason = "; ".join(str(x) for x in reasoning[:3])
        else:
            reason = row.get("message", "")
    return str(reason or "")


def _symbol_decision_index(plan: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in ((plan or {}).get("all_symbol_decisions") or []):
        sym = str(row.get("symbol", "") or "")
        if sym:
            out[sym] = row
    return out


def _render_account_block(
    *,
    account_balance: float,
    cash: float | None,
    positions: Iterable[Any] | None,
    daily_pnl: float,
    daily_pnl_pct: float,
    spy_daily_pct: float,
    positions_count: int,
) -> list[str]:
    delta = daily_pnl_pct - spy_daily_pct
    cash_line = f"Cash: {_fmt_money(cash)}" if cash is not None else "Cash: not provided"
    lines = [
        "ACCOUNT",
        f"Total account balance: {_fmt_money(account_balance)}",
        cash_line,
        (
            f"Today: bot {_fmt_pct(daily_pnl_pct)} ({_fmt_signed_money(daily_pnl)}) | "
            f"SPY {_fmt_pct(spy_daily_pct)} | alpha/delta {_fmt_pct(delta)}"
        ),
        f"Open positions: {positions_count}",
        (
            "Valuation: cash, share quantities, and average entry from Alpaca; "
            "market value and P&L use external current prices "
            f"({_source_summary(positions)})."
        ),
    ]
    return lines


def _render_position_sizes(
    positions: Iterable[Any] | None,
    account_balance: float,
    cash: float | None,
    limit: int = 30,
) -> list[str]:
    rows = _position_rows(positions, account_balance)
    lines = ["CURRENT POSITION SIZES"]
    if cash is not None:
        cash_weight = (_to_float(cash) / account_balance) if account_balance > 0 else 0.0
        lines.append(f"Cash: {_fmt_money(cash)} ({_fmt_pct(cash_weight, signed=False)})")
    if not rows:
        lines.append("No open stock positions.")
        return lines
    for r in rows[:limit]:
        lines.append(
            f"{r['symbol']}: {_fmt_qty(r['qty'])} sh | avg {_fmt_money(r['avg_entry'], 2)} -> "
            f"now {_fmt_money(r['price'], 2)} = "
            f"{_fmt_money(r['market_value'])} ({_fmt_pct(r['weight'], signed=False)}) | "
            f"P/L {_fmt_signed_money(r['pnl'])} ({_fmt_pct(r['pnl_pct'])}) | {r['source']}"
        )
    if len(rows) > limit:
        lines.append(f"... {len(rows) - limit} more positions omitted")
    return lines


class TelegramNotifier:
    def __init__(self, token: str | None = None, chat_id: str | None = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def _send(self, message: str, parse_mode: str | None = None) -> bool:
        if not self.token or not self.chat_id:
            log.warning(
                "Telegram notifier not configured (token=%s, chat_id=%s)",
                bool(self.token),
                bool(self.chat_id),
            )
            return False

        ok = True
        for chunk in _split_message(message):
            payload: dict[str, Any] = {
                "chat_id": self.chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            }
            if parse_mode:
                payload["parse_mode"] = parse_mode
            try:
                resp = requests.post(self.api_url, json=payload, timeout=15)
                if resp.status_code != 200:
                    log.warning(
                        "Telegram send failed: status=%d body=%s",
                        resp.status_code,
                        resp.text[:500],
                    )
                    ok = False
            except Exception as e:
                log.warning("Telegram send error: %s", e)
                ok = False
        return ok

    # ---------- Scan Notifications ----------

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
        selector: dict[str, Any] | None = None,
        unified_portfolio_plan: dict[str, Any] | None = None,
        cash: float | None = None,
        positions: list[Any] | None = None,
        **_: Any,
    ) -> bool:
        account_balance = _to_float(equity)
        selector = selector or {}
        plan = unified_portfolio_plan or {}
        symbol_decisions = _symbol_decision_index(plan)
        active_rebalance = [*(rebalance or []), *(executions or [])]

        buy_rows = [r for r in active_rebalance if _trade_side(r) == "buy"]
        sell_rows = [r for r in active_rebalance if _trade_side(r) == "sell"]
        blocked = list(selector.get("blocked_new_entries") or plan.get("blocked_new_entries") or [])
        removals = list(selector.get("post_execution_target_removals") or [])
        selected = list(selector.get("selected_positions") or plan.get("selected_positions") or [])

        add_total = sum(_trade_delta_notional(r) for r in buy_rows)
        reduce_total = sum(_trade_delta_notional(r) for r in sell_rows)
        gross_total = add_total + reduce_total

        lines: list[str] = [f"SCAN {scan_name} | {_get_phoenix_timestamp()}", ""]
        lines.extend(_render_account_block(
            account_balance=account_balance,
            cash=cash,
            positions=positions,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            spy_daily_pct=spy_daily_pct,
            positions_count=positions_count,
        ))

        macro_notes = ", ".join(str(x) for x in (macro or {}).get("notes", [])[:4])
        lines.extend([
            "",
            "MARKET",
            (
                f"Regime: {(macro or {}).get('regime', '?')} | "
                f"macro score {_to_float((macro or {}).get('score')):+.3f} | "
                f"VIX {(macro or {}).get('vix_regime', '?')} | "
                f"breadth {_fmt_pct((macro or {}).get('breadth_pct_above_50'), signed=False)}"
            ),
        ])
        if macro_notes:
            lines.append(f"Notes: {macro_notes}")

        lines.extend([
            "",
            "SCAN RESULTS",
            (
                f"Pool: {selector.get('pool_size', len(decisions or []))} | "
                f"selected: {', '.join(selected) if selected else 'none'} | "
                f"executed actions: {len(executions or [])} | exits: {len(exits or [])} | "
                f"blocked: {len(blocked) + len(removals)}"
            ),
            (
                f"Rebalanced: gross {_fmt_money(gross_total)} | adds {_fmt_money(add_total)} | "
                f"reductions {_fmt_money(reduce_total)} | net {_fmt_signed_money(add_total - reduce_total)}"
            ),
        ])
        if ai_arbiter_skipped:
            lines.append(f"AI rebalance skipped: {ai_arbiter_skipped}")
        if selector.get("execution_cash_target_pct") is not None or selector.get("spy_target_pct") is not None:
            lines.append(
                f"Targets: cash {_fmt_pct(selector.get('execution_cash_target_pct', selector.get('cash_target_pct')), signed=False)} | "
                f"SPY {_fmt_pct(selector.get('spy_target_pct'), signed=False)}"
            )
        cash_policy = selector.get("cash_policy") or plan.get("cash_policy") or {}
        if isinstance(cash_policy, dict) and cash_policy.get("mode"):
            lock_until = cash_policy.get("lock_until")
            lock_part = f" | lock {lock_until}" if lock_until else ""
            lines.append(
                f"Cash policy: {str(cash_policy.get('mode')).upper()} "
                f"({cash_policy.get('source', '?')}{lock_part}) - "
                f"{_short_text(cash_policy.get('reason'), 180)}"
            )
        if opportunity_ranking:
            lines.append(f"Opportunity ranking: {' > '.join(str(s) for s in opportunity_ranking[:10])}")

        thesis = plan.get("portfolio_thesis")
        if thesis:
            lines.extend(["", "AI PORTFOLIO THESIS", _short_text(thesis, 900)])

        final_positions = (plan.get("final_portfolio") or {}).get("positions") or []
        if final_positions:
            lines.extend(["", "FINAL TARGET PORTFOLIO"])
            for row in final_positions:
                reason = _short_text(row.get("reason"), 180)
                lines.append(
                    f"{row.get('symbol', '?')}: target {_fmt_pct(row.get('target_pct'), signed=False)} "
                    f"({_fmt_money(row.get('target_notional_usd'))}, {_fmt_qty(row.get('target_qty'))} sh), "
                    f"opp {_to_float(row.get('opportunity_score')):.0f} - {reason}"
                )
            fp = plan.get("final_portfolio") or {}
            lines.append(
                f"Cash target: {_fmt_pct(fp.get('cash_target_pct'), signed=False)} "
                f"({_fmt_money(fp.get('cash_target_usd'))}) | "
                f"SPY target: {_fmt_pct(fp.get('spy_target_pct'), signed=False)}"
            )

        lines.extend(["", "BOUGHT / INCREASED"])
        if buy_rows:
            for row in buy_rows:
                sym = _trade_symbol(row)
                decision = symbol_decisions.get(sym, {})
                if not decision and isinstance(row.get("decision"), dict):
                    decision = row["decision"]
                sizing = row.get("sizing") or {}
                reason = _trade_reason(row, decision)
                ex = row.get("execution") or {}
                filled = ex.get("filled_qty") or row.get("filled_qty")
                filled_part = f" | filled {_fmt_qty(filled)} sh" if _to_float(filled) > 0 else ""
                target_pct = row.get("target_pct", decision.get("target_pct"))
                if target_pct is None and account_balance > 0:
                    target_pct = _trade_delta_notional(row) / account_balance
                target_qty = row.get("target_qty", decision.get("target_qty", sizing.get("qty")))
                lines.append(
                    f"{sym}: {_execution_status(row)} | add {_fmt_money(_trade_delta_notional(row))} "
                    f"to target {_fmt_pct(target_pct, signed=False)} "
                    f"({_fmt_qty(target_qty)} sh)"
                    f"{filled_part}"
                )
                lines.append(
                    f"  AI: {row.get('ai_action', decision.get('selector_action', '?'))}, "
                    f"conf {_to_float(row.get('ai_confidence')):.2f}, "
                    f"opp {_to_float(row.get('opportunity_score', decision.get('opportunity_score'))):.0f} - "
                    f"{_short_text(reason, 260)}"
                )
        else:
            lines.append("No buy or increase actions.")

        lines.extend(["", "SELL / TRIM / EXIT DECISIONS"])
        rendered_sell = False
        for row in sell_rows:
            rendered_sell = True
            sym = _trade_symbol(row)
            decision = symbol_decisions.get(sym, {})
            if not decision and isinstance(row.get("decision"), dict):
                decision = row["decision"]
            reason = _trade_reason(row, decision)
            lines.append(
                f"{sym}: {_execution_status(row)} | reduce {_fmt_money(_trade_delta_notional(row))} "
                f"from {_fmt_money(row.get('current_notional'))} to "
                f"{_fmt_money(row.get('target_notional'))} "
                f"(target {_fmt_pct(row.get('target_pct', decision.get('target_pct')), signed=False)})"
            )
            lines.append(
                f"  AI: {row.get('ai_action', decision.get('selector_action', '?'))}, "
                f"conf {_to_float(row.get('ai_confidence')):.2f}, "
                f"opp {_to_float(row.get('opportunity_score', decision.get('opportunity_score'))):.0f} - "
                f"{_short_text(reason, 260)}"
            )
        for row in exits or []:
            rendered_sell = True
            lines.append(
                f"{row.get('symbol', '?')}: {_execution_status(row)} | close decision - "
                f"{_short_text(row.get('reason') or row.get('message'), 260)}"
            )
        if not rendered_sell:
            lines.append("No sell, trim, or close decisions.")

        if blocked or removals:
            lines.extend(["", "BLOCKED / REMOVED TARGETS"])
            for row in [*blocked, *removals]:
                sym = row.get("symbol", "?")
                reason = row.get("reason") or row.get("phase") or "removed"
                removed = row.get("removed_target_pct")
                lines.append(
                    f"{sym}: {reason} | target removed {_fmt_pct(removed, signed=False)} | "
                    f"requested {_fmt_money(row.get('requested_delta_notional'))}"
                )
                if row.get("earnings"):
                    e = row["earnings"]
                    lines.append(
                        f"  Earnings: {e.get('next_earnings_date')} ({e.get('days_until_earnings')}d), "
                        f"rule {e.get('reason')}"
                    )
        sector_guard = selector.get("sector_guard") or plan.get("sector_guard") or {}
        if isinstance(sector_guard, dict) and sector_guard.get("violations"):
            lines.extend(["", "SECTOR / THEME CAPS"])
            for v in sector_guard.get("violations", [])[:6]:
                lines.append(
                    f"{v.get('kind', '?')} {v.get('bucket', '?')}: "
                    f"{', '.join(str(s) for s in (v.get('members') or []))} "
                    f"> limit {v.get('limit')}"
                )

        pass_rows = [
            r for r in (plan.get("all_symbol_decisions") or [])
            if str(r.get("final_action", "")).upper() == "PASS"
        ]
        pass_rows.sort(
            key=lambda r: max(
                _to_float(r.get("opportunity_score")),
                _to_float(r.get("candidate_priority_score")),
            ),
            reverse=True,
        )
        missed = selector.get("missed_breakouts") or []
        if pass_rows or missed:
            lines.extend(["", "INTERESTED BUT NOT BOUGHT"])
            seen: set[str] = set()
            for row in pass_rows[:10]:
                sym = str(row.get("symbol", "?"))
                seen.add(sym)
                lines.append(
                    f"{sym}: action {row.get('selector_action', row.get('final_action'))}, "
                    f"opp {_to_float(row.get('opportunity_score')):.0f}, "
                    f"priority {_to_float(row.get('candidate_priority_score')):.0f}, "
                    f"{row.get('momentum_grade') or 'no grade'} - "
                    f"{_short_text(row.get('reason'), 220)}"
                )
            for row in missed[:5]:
                sym = str(row.get("symbol", "?"))
                if sym in seen:
                    continue
                lines.append(
                    f"{sym}: missed breakout priority {_to_float(row.get('candidate_priority_score')):.0f} - "
                    f"{_short_text(row.get('selector_reason') or row.get('reason'), 220)}"
                )

        lines.extend(["", *_render_position_sizes(positions, account_balance, cash)])

        return self._send("\n".join(lines))

    # ---------- Premarket Brief Notifications ----------

    def notify_premarket(
        self,
        macro: dict[str, Any],
        positions_count: int = 0,
        total_pnl: float = 0.0,
        cancelled_orders: int = 0,
        positions_list: list[dict[str, Any]] | None = None,
        account_balance: float = 0.0,
        cash: float | None = None,
        daily_pnl_pct: float = 0.0,
        spy_daily_pct: float = 0.0,
        daily_pnl: float = 0.0,
    ) -> bool:
        lines = [f"PREMARKET | {_get_phoenix_timestamp()}", ""]
        lines.extend(_render_account_block(
            account_balance=account_balance,
            cash=cash,
            positions=positions_list,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            spy_daily_pct=spy_daily_pct,
            positions_count=positions_count,
        ))
        lines.extend([
            "",
            "MARKET",
            f"Regime: {macro.get('regime', '?')} | SPY trend {_to_float(macro.get('spy_trend')):+.3f} | VIX {macro.get('vix_regime', '?')}",
        ])
        if cancelled_orders:
            lines.append(f"Cancelled stale orders: {cancelled_orders}")
        lines.extend(["", "POSITIONS"])
        if positions_list:
            for p in positions_list:
                line = (
                    f"{p.get('symbol', '?')}: {_fmt_qty(p.get('qty'))} sh | "
                    f"P/L {_fmt_signed_money(p.get('unrealized_pnl'))}"
                )
                if p.get("earnings_days") is not None and int(p["earnings_days"]) <= 7:
                    line += f" | earnings {p.get('earnings_date')} ({p.get('earnings_days')}d)"
                lines.append(line)
        else:
            lines.append("No open stock positions.")
        if total_pnl:
            lines.append(f"Total open-position P/L: {_fmt_signed_money(total_pnl)}")
        return self._send("\n".join(lines))

    # ---------- EOD Report Notifications ----------

    def notify_eod(
        self,
        daily_return: float = 0.0,
        daily_vs_spy: float = 0.0,
        spy_daily: float = 0.0,
        daily_pnl: float = 0.0,
        trades_today: int = 0,
        positions_count: int = 0,
        equity: float = 0.0,
        cash: float = 0.0,
        positions: list[Any] | None = None,
    ) -> bool:
        lines = [f"EOD REPORT | {_get_phoenix_timestamp()}", ""]
        lines.extend(_render_account_block(
            account_balance=_to_float(equity),
            cash=cash,
            positions=positions,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_return,
            spy_daily_pct=spy_daily,
            positions_count=positions_count,
        ))
        lines.extend([
            "",
            "SUMMARY",
            f"Trades today: {trades_today}",
            f"Daily alpha/delta vs SPY: {_fmt_pct(daily_vs_spy)}",
            "",
            *_render_position_sizes(positions, _to_float(equity), cash),
        ])
        return self._send("\n".join(lines))

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
        lines = [
            f"WEEKLY REVIEW | {_get_phoenix_timestamp()}",
            "",
            "PERFORMANCE",
            f"1-week: bot {_fmt_pct(weekly_return)} | alpha/delta {_fmt_pct(weekly_vs_spy)}",
            f"1-month: bot {_fmt_pct(monthly_return)} | alpha/delta {_fmt_pct(monthly_vs_spy)}",
            "",
            "TRADES",
            f"This week: {trades_week} | this month: {trades_month} | win rate {_fmt_pct(win_rate, signed=False)}",
        ]
        if best_performer or worst_performer:
            lines.append("")
            lines.append("PERFORMERS")
            if best_performer:
                lines.append(f"Best: {best_performer}")
            if worst_performer:
                lines.append(f"Worst: {worst_performer}")
        return self._send("\n".join(lines))

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
        cash: float | None = None,
        positions: list[Any] | None = None,
        daily_pnl_pct: float = 0.0,
        spy_daily_pct: float = 0.0,
        daily_pnl: float = 0.0,
    ) -> bool:
        suffix = " [DRY]" if dry_run else ""
        lines = [f"PRECLOSE{suffix} | {_get_phoenix_timestamp()}", ""]
        lines.extend(_render_account_block(
            account_balance=_to_float(equity),
            cash=cash,
            positions=positions,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            spy_daily_pct=spy_daily_pct,
            positions_count=positions_count,
        ))
        lines.extend([
            "",
            "OVERNIGHT DECISIONS",
            f"SPY late-day bias: {market_bias:+.3f}",
        ])
        if bearish_halt:
            lines.append(f"Bearish halt active: bias {market_bias:+.3f} <= {halt_threshold:+.3f}")
        held = sum(1 for r in hold_reports if r.get("decision") in ("hold", "hold_no_data", "hold_earnings_gate"))
        lines.append(f"Held: {held} | closed/trimmed: {len(exits)} | new buys: {len(new_executions)}")
        if exits:
            lines.append("")
            lines.append("SELL / CLOSE")
            for row in exits:
                lines.append(
                    f"{row.get('symbol', '?')}: {_execution_status(row)} - "
                    f"{_short_text(row.get('reason') or row.get('message'), 260)}"
                )
        if new_executions:
            lines.append("")
            lines.append("NEW OVERNIGHT BUYS")
            for row in new_executions:
                sizing = row.get("sizing") or {}
                decision = row.get("decision") or {}
                sym = sizing.get("symbol") or decision.get("symbol") or row.get("symbol", "?")
                lines.append(
                    f"{sym}: {_execution_status(row)} | {_fmt_qty(sizing.get('qty'))} sh | "
                    f"{_fmt_money(sizing.get('notional'))} | {_short_text((decision.get('reasoning') or [''])[0], 180)}"
                )
        lines.extend(["", *_render_position_sizes(positions, _to_float(equity), cash)])
        return self._send("\n".join(lines))

    # ---------- Test / Alert Notifications ----------

    def notify_test_status(
        self,
        account_balance: float,
        cash: float,
        positions: list[Any],
        daily_pnl: float,
        daily_pnl_pct: float,
        spy_daily_pct: float,
        spy_source: str = "",
        note: str = "",
    ) -> bool:
        lines = [f"TELEGRAM TEST | {_get_phoenix_timestamp()}", ""]
        lines.extend(_render_account_block(
            account_balance=account_balance,
            cash=cash,
            positions=positions,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            spy_daily_pct=spy_daily_pct,
            positions_count=len(_position_rows(positions, account_balance)),
        ))
        if spy_source:
            lines.append(f"SPY benchmark source: {spy_source}")
        if note:
            lines.extend(["", "TEST NOTE", _short_text(note, 900)])
        lines.extend(["", *_render_position_sizes(positions, account_balance, cash)])
        return self._send("\n".join(lines))

    def send_alert(
        self,
        alert_type: str,
        task_name: str,
        message: str,
        error_details: str = "",
    ) -> bool:
        lines = [
            f"ALERT: {alert_type} | {task_name} | {_get_phoenix_timestamp()}",
            "",
            _short_text(message, 1200),
        ]
        if error_details:
            lines.extend(["", "DETAILS", _short_text(error_details, 1800)])
        return self._send("\n".join(lines))

    def notify_trade_failure(
        self,
        scan_label: str,
        mismatches: list[dict] | None = None,
        errors: list[dict] | None = None,
    ) -> bool:
        """Phase 3 (2026-05-07): consolidated end-of-scan trade-failure alert.

        Fires when the selector emitted BUY/INCREASE/EXIT/REDUCE for a symbol
        but no order was submitted (mismatch) or the order was rejected /
        unfilled (executor error). Caller passes lists of dicts with at least
        ``symbol`` and ``reason`` keys.

        Returns True when a message was sent. If both lists are empty, no
        message is sent and the function returns False.
        """
        mismatches = mismatches or []
        errors = errors or []
        if not mismatches and not errors:
            return False
        lines = [
            f"TRADE FAILURE: {scan_label} | {_get_phoenix_timestamp()}",
        ]
        if mismatches:
            lines.append("")
            lines.append(f"selector→no-execute ({len(mismatches)}):")
            for m in mismatches[:8]:
                sym = m.get("symbol", "?")
                action = m.get("action", "?")
                reason = _short_text(str(m.get("reason", "")), 200)
                lines.append(f"  {sym} {action}: {reason}")
            if len(mismatches) > 8:
                lines.append(f"  …+{len(mismatches) - 8} more")
        if errors:
            lines.append("")
            lines.append(f"executor errors ({len(errors)}):")
            for e in errors[:8]:
                sym = e.get("symbol", "?")
                status = e.get("status", "?")
                reason = _short_text(str(e.get("reason", e.get("message", ""))), 200)
                lines.append(f"  {sym} {status}: {reason}")
            if len(errors) > 8:
                lines.append(f"  …+{len(errors) - 8} more")
        return self._send("\n".join(lines))


_notifier: TelegramNotifier | None = None


def get_notifier() -> TelegramNotifier:
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
    return get_notifier().notify_scan_execution(
        scan_name, macro, decisions, executions, exits, **kwargs
    )


def notify_premarket(macro: dict[str, Any], **kwargs: Any) -> bool:
    return get_notifier().notify_premarket(macro, **kwargs)


def notify_eod(**kwargs: Any) -> bool:
    return get_notifier().notify_eod(**kwargs)


def notify_preclose(**kwargs: Any) -> bool:
    return get_notifier().notify_preclose(**kwargs)


def notify_weekly(**kwargs: Any) -> bool:
    return get_notifier().notify_weekly(**kwargs)


def notify_test_status(**kwargs: Any) -> bool:
    return get_notifier().notify_test_status(**kwargs)


def send_alert(alert_type: str, task_name: str, message: str, **kwargs: Any) -> bool:
    return get_notifier().send_alert(alert_type, task_name, message, **kwargs)
