"""Local read-only web dashboard for the trading bot.

The server intentionally lives inside dashboard/ and only reads bot artifacts
from data/, config.yaml, and optional live account APIs. It does not write to
the trading bot or place trades.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import socketserver
import sys
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = Path(__file__).resolve().parent
STATIC_DIR = DASHBOARD_DIR / "static"

PERFORMANCE_PATH = ROOT / "data" / "performance" / "portfolio_vs_spy.json"
RESEARCH_DIR = ROOT / "data" / "research"
JOURNAL_DIR = ROOT / "data" / "journal"
STATE_DIR = ROOT / "data" / "state"


def build_dashboard_payload(*, include_live: bool = False) -> dict[str, Any]:
    """Build the API document used by the browser."""
    latest_scan_file, latest_scan = _latest_scan()
    latest_preclose_file, latest_preclose = _latest_json("*_preclose.json")
    latest_weekly_file, latest_weekly = _latest_json("*_weekly.json")

    eod = _eod_payload()
    performance = _performance_payload()
    raw_trades = _read_jsonl_tail(JOURNAL_DIR / "trades.jsonl", 300)
    compact_scan = _scan_payload(latest_scan_file, latest_scan, eod=eod, raw_trades=raw_trades)
    trades = [_compact_trade(row) for row in raw_trades[-100:]]
    decisions = [_compact_decision(row) for row in _read_jsonl_tail(JOURNAL_DIR / "decisions.jsonl", 140)]
    watchlist = _watchlist_payload()
    config = _config_summary()
    selector_state = _load_json(STATE_DIR / "selector_state.json", default={})

    payload: dict[str, Any] = {
        "generated_at_utc": _now_iso(),
        "root": str(ROOT),
        "status": _status_payload(performance, eod, compact_scan, trades, config),
        "performance": performance,
        "eod": eod,
        "latest_scan": compact_scan,
        "latest_preclose": {
            "file": _file_info(latest_preclose_file),
            "summary": _prune(latest_preclose, max_depth=2, max_list=8),
        },
        "latest_weekly": {
            "file": _file_info(latest_weekly_file),
            "summary": _prune(latest_weekly, max_depth=2, max_list=8),
        },
        "journals": {
            "trades": trades,
            "decisions": decisions,
            "files": {
                "trades": _file_info(JOURNAL_DIR / "trades.jsonl"),
                "decisions": _file_info(JOURNAL_DIR / "decisions.jsonl"),
            },
        },
        "watchlist": watchlist,
        "state": {
            "selector": selector_state,
            "files": {
                "dynamic_watchlist": _file_info(STATE_DIR / "dynamic_watchlist.json"),
                "selector_state": _file_info(STATE_DIR / "selector_state.json"),
                "api_key_pool": _file_info(STATE_DIR / "api_key_pool.json"),
                "daily_baseline": _file_info(STATE_DIR / "daily_baseline.json"),
            },
        },
        "config": config,
        "sources": _sources_payload(latest_scan_file),
        "live": {"requested": False, "ok": False, "error": None, "account": None, "positions": []},
    }
    if include_live:
        payload["live"] = _live_snapshot()
        payload["status"] = _status_payload(performance, eod, compact_scan, trades, config, payload["live"])
    return payload


def _performance_payload() -> dict[str, Any]:
    doc = _load_json(PERFORMANCE_PATH, default=None)
    points_raw: list[Any] = []
    meta: dict[str, Any] = {}
    if isinstance(doc, list):
        points_raw = doc
    elif isinstance(doc, dict):
        points_raw = doc.get("points") if isinstance(doc.get("points"), list) else []
        meta = {k: v for k, v in doc.items() if k != "points"}

    points: list[dict[str, Any]] = []
    portfolio_base: float | None = None
    spy_base: float | None = None
    for row in points_raw:
        if not isinstance(row, dict):
            continue
        portfolio_value = _safe_float(row.get("portfolio_value"))
        spy_price = _safe_float(row.get("spy_price"))
        if portfolio_base is None and portfolio_value and portfolio_value > 0:
            portfolio_base = portfolio_value
        if spy_base is None and spy_price and spy_price > 0:
            spy_base = spy_price
        point = {
            "timestamp_utc": row.get("timestamp_utc"),
            "timestamp_et": row.get("timestamp_et"),
            "scan_started_at_utc": row.get("scan_started_at_utc"),
            "portfolio_value": portfolio_value,
            "spy_price": spy_price,
            "cash": _safe_float(row.get("cash")),
            "positions_value": _safe_float(row.get("positions_value")),
            "priced_positions_value": _safe_float(row.get("priced_positions_value")),
            "benchmark_symbol": row.get("benchmark_symbol") or "SPY",
            "complete": bool(row.get("complete", False)),
            "portfolio_complete": bool(row.get("portfolio_complete", False)),
            "benchmark_complete": bool(row.get("benchmark_complete", False)),
            "pricing_source": row.get("pricing_source") or "twelve_data",
            "position_count": len(row.get("positions") or []),
            "missing_symbols": row.get("missing_symbols") or [],
        }
        if portfolio_base and portfolio_value is not None:
            point["portfolio_return_pct"] = ((portfolio_value / portfolio_base) - 1.0) * 100.0
        else:
            point["portfolio_return_pct"] = None
        if spy_base and spy_price is not None:
            point["spy_return_pct"] = ((spy_price / spy_base) - 1.0) * 100.0
        else:
            point["spy_return_pct"] = None
        if point["portfolio_return_pct"] is not None and point["spy_return_pct"] is not None:
            point["relative_return_pct"] = point["portfolio_return_pct"] - point["spy_return_pct"]
        else:
            point["relative_return_pct"] = None
        points.append(point)

    latest = points[-1] if points else None
    return {
        "source_path": _rel(PERFORMANCE_PATH),
        "file": _file_info(PERFORMANCE_PATH),
        "meta": meta,
        "points": points,
        "latest": latest,
        "point_count": len(points),
        "has_enough_for_line": len(points) >= 2,
        "empty_reason": None if points else "No scheduled performance points have been written yet.",
    }


def _eod_payload() -> dict[str, Any]:
    files = sorted(RESEARCH_DIR.glob("*_eod.json"), key=_file_sort_key)
    history: list[dict[str, Any]] = []
    for path in files:
        doc = _load_json(path, default={})
        if not isinstance(doc, dict):
            continue
        as_of = doc.get("date") or _date_from_name(path.name)
        history.append(
            {
                "date": as_of,
                "ts": as_of,
                "equity": _safe_float(doc.get("equity")),
                "cash": _safe_float(doc.get("cash")),
                "daily_return": _safe_float(doc.get("daily_return")),
                "daily_vs_spy": _safe_float(doc.get("daily_vs_spy")),
                "period_return": _safe_float(doc.get("period_return")),
                "period_vs_spy": _safe_float(doc.get("period_vs_spy")),
                "spy_daily": _safe_float(doc.get("spy_daily")),
                "spy_30d": _safe_float(doc.get("spy_30d")),
                "positions_count": _safe_int(doc.get("positions_count")),
                "trades_today": _safe_int(doc.get("trades_today")),
                "positions": [
                    _compact_position(p, total_equity=_safe_float(doc.get("equity")), as_of=as_of)
                    for p in doc.get("positions") or []
                ],
                "file": _file_info(path),
            }
        )
    latest = history[-1] if history else None
    return {
        "history": history,
        "latest": latest,
        "position_history": _position_history(history),
        "files": [_file_info(path) for path in files[-20:]],
    }


def _scan_payload(
    path: Path | None,
    scan: Any,
    *,
    eod: dict[str, Any] | None = None,
    raw_trades: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(scan, dict):
        scan = {}
    selector = scan.get("selector") if isinstance(scan.get("selector"), dict) else {}
    plan = scan.get("unified_portfolio_plan") if isinstance(scan.get("unified_portfolio_plan"), dict) else {}
    current_portfolio = plan.get("current_portfolio") if isinstance(plan.get("current_portfolio"), dict) else {}
    final_portfolio = plan.get("final_portfolio") if isinstance(plan.get("final_portfolio"), dict) else {}
    all_decisions = plan.get("all_symbol_decisions") if isinstance(plan.get("all_symbol_decisions"), list) else []
    capital_plan = plan.get("capital_movement_plan") if isinstance(plan.get("capital_movement_plan"), list) else []
    executions = scan.get("executions") if isinstance(scan.get("executions"), list) else []
    macro = scan.get("macro") if isinstance(scan.get("macro"), dict) else {}
    scan_ts = scan.get("ts")
    all_decisions = _stamp_items(all_decisions, scan_ts)
    current_positions = _stamp_items(current_portfolio.get("positions") or [], scan_ts)
    final_positions = _stamp_items(final_portfolio.get("positions") or [], scan_ts)
    executions = _stamp_items(executions, scan_ts)
    blocked_rows = _stamp_items(selector.get("blocked_new_entries") or plan.get("blocked_new_entries") or [], scan_ts)
    missed_rows = _stamp_items(selector.get("missed_breakouts") or [], scan_ts)
    capital_plan = _enrich_capital_plan(
        capital_plan,
        scan_ts=scan_ts,
        decisions=all_decisions,
        current_positions=current_positions,
        eod=eod or {},
        raw_trades=raw_trades or [],
    )

    return {
        "file": _file_info(path),
        "ts": scan_ts,
        "equity": _safe_float(scan.get("equity")),
        "positions_count": _safe_int(scan.get("positions_count")),
        "macro": macro,
        "selector": {
            "pool_size": _safe_int(selector.get("pool_size")),
            "sources_breakdown": selector.get("sources_breakdown") or {},
            "selected_positions": selector.get("selected_positions") or plan.get("selected_positions") or [],
            "target_weights": selector.get("target_weights") or {},
            "execution_target_weights": selector.get("execution_target_weights") or {},
            "cash_target_pct": _safe_float(selector.get("cash_target_pct")),
            "execution_cash_target_pct": _safe_float(selector.get("execution_cash_target_pct")),
            "spy_target_pct": _safe_float(selector.get("spy_target_pct")),
            "new_candidates_selected": _safe_int(selector.get("new_candidates_selected")),
            "allow_floor_breach": selector.get("allow_floor_breach"),
            "exhaustion_penalty_applied": selector.get("exhaustion_penalty_applied") or [],
            "missed_breakouts": missed_rows,
            "blocked_new_entries": blocked_rows,
            "new_entry_staging": _stamp_items(selector.get("new_entry_staging") or [], scan_ts),
        },
        "portfolio_thesis": plan.get("portfolio_thesis"),
        "current_portfolio": {
            "equity": _safe_float(current_portfolio.get("equity")),
            "cash_usd": _safe_float(current_portfolio.get("cash_usd")),
            "cash_pct": _safe_float(current_portfolio.get("cash_pct")),
            "positions": current_positions,
        },
        "final_portfolio": {
            "positions": final_positions,
            "spy_target_pct": _safe_float(final_portfolio.get("spy_target_pct")),
            "cash_target_pct": _safe_float(final_portfolio.get("cash_target_pct")),
            "cash_target_usd": _safe_float(final_portfolio.get("cash_target_usd")),
        },
        "all_symbol_decisions": all_decisions,
        "capital_movement_plan": capital_plan,
        "executions": executions,
        "exits": scan.get("exits") or [],
        "cash_proxy": scan.get("cash_proxy"),
        "verifier": scan.get("verifier"),
        "rotation_plan": plan.get("rotation_plan") or {},
        "summary": _scan_summary(scan, selector, plan),
    }


def _scan_summary(scan: dict[str, Any], selector: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    blocked = plan.get("blocked_new_entries") or selector.get("blocked_new_entries") or []
    return {
        "selected_count": len(selector.get("selected_positions") or plan.get("selected_positions") or []),
        "blocked_count": len(blocked),
        "missed_breakout_count": len(selector.get("missed_breakouts") or []),
        "execution_count": len(scan.get("executions") or []),
        "portfolio_thesis": plan.get("portfolio_thesis"),
    }


def _stamp_items(rows: list[Any], ts: Any) -> list[dict[str, Any]]:
    stamped: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        item.setdefault("ts", ts)
        item.setdefault("scan_ts", ts)
        stamped.append(item)
    return stamped


def _enrich_capital_plan(
    rows: list[Any],
    *,
    scan_ts: Any,
    decisions: list[dict[str, Any]],
    current_positions: list[dict[str, Any]],
    eod: dict[str, Any],
    raw_trades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decision_by_symbol = {
        str(row.get("symbol") or "").upper(): row
        for row in decisions
        if row.get("symbol")
    }
    current_by_symbol = {
        str(row.get("symbol") or "").upper(): row
        for row in current_positions
        if row.get("symbol")
    }
    latest_eod_positions = ((eod.get("latest") or {}).get("positions") or []) if isinstance(eod, dict) else []
    eod_by_symbol = {
        str(row.get("symbol") or "").upper(): row
        for row in latest_eod_positions
        if isinstance(row, dict) and row.get("symbol")
    }
    trades_by_symbol = _sell_trade_index(raw_trades)
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        item.setdefault("ts", scan_ts)
        item.setdefault("scan_ts", scan_ts)
        symbol = str(item.get("symbol") or "").upper()
        decision = decision_by_symbol.get(symbol, {})
        current = current_by_symbol.get(symbol, {})
        eod_row = eod_by_symbol.get(symbol, {})
        sell_trade = _nearest_trade(trades_by_symbol.get(symbol, []), scan_ts)
        item["exit_pnl"] = _exit_pnl(
            item,
            decision=decision,
            current=current,
            eod_row=eod_row,
            sell_trade=sell_trade,
        )
        out.append(item)
    return out


def _sell_trade_index(raw_trades: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for row in raw_trades:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or "").upper()
        if not symbol:
            continue
        side = str(row.get("side") or "").lower()
        event = str(row.get("event") or "").lower()
        if side != "sell" and "position_closed" not in event and "sell" not in event:
            continue
        by_symbol.setdefault(symbol, []).append(row)
    return by_symbol


def _nearest_trade(rows: list[dict[str, Any]], scan_ts: Any, *, max_seconds: float = 3600.0) -> dict[str, Any] | None:
    if not rows:
        return None
    scan_dt = _parse_dt(scan_ts)
    if scan_dt is None:
        return None
    best: tuple[float, dict[str, Any]] | None = None
    for row in rows:
        row_dt = _parse_dt(row.get("ts"))
        if row_dt is None:
            continue
        distance = abs((row_dt - scan_dt).total_seconds())
        if best is None or distance < best[0]:
            best = (distance, row)
    if best and best[0] <= max_seconds:
        return best[1]
    return None


def _exit_pnl(
    row: dict[str, Any],
    *,
    decision: dict[str, Any],
    current: dict[str, Any],
    eod_row: dict[str, Any],
    sell_trade: dict[str, Any] | None,
) -> dict[str, Any] | None:
    action_text = " ".join(str(row.get(k) or "") for k in ("action", "side", "ai_action", "selector_action", "final_action")).lower()
    if not any(token in action_text for token in ("exit", "sell", "reduce", "trim")):
        return None

    qty = abs(_first_number(row.get("delta_qty"), row.get("current_qty"), decision.get("current_qty"), current.get("current_qty"), sell_trade.get("filled_qty") if sell_trade else None) or 0.0)
    avg_entry = _first_number(
        row.get("avg_entry_price"),
        row.get("avg_entry"),
        decision.get("avg_entry_price"),
        decision.get("avg_entry"),
        current.get("avg_entry_price"),
        current.get("avg_entry"),
        eod_row.get("avg_entry"),
        eod_row.get("avg_entry_price"),
    )
    exit_price_source = "unavailable"
    exit_price = None
    if sell_trade:
        exit_price = _first_number(sell_trade.get("filled_avg_price"))
        if exit_price is not None:
            exit_price_source = "actual_filled_trade"
    if exit_price is None:
        exit_price = _first_number(
            row.get("avg_exit_price"),
            row.get("exit_price"),
            row.get("current_price"),
            row.get("ai_entry_price"),
            decision.get("current_price"),
            decision.get("ai_entry_price"),
            current.get("current_price"),
            eod_row.get("current_price"),
        )
        if exit_price is not None:
            exit_price_source = "scan_or_eod_reference"
    if exit_price is None:
        notional = abs(_first_number(row.get("delta_usd"), row.get("delta_notional"), row.get("notional")) or 0.0)
        if qty > 0 and notional > 0:
            exit_price = notional / qty
            exit_price_source = "delta_notional_div_qty"

    complete = bool(qty > 0 and avg_entry is not None and avg_entry > 0 and exit_price is not None and exit_price > 0)
    result: dict[str, Any] = {
        "complete": complete,
        "qty": qty if qty > 0 else None,
        "avg_entry_price": avg_entry,
        "avg_exit_price": exit_price,
        "price_source": exit_price_source,
        "trade_ts": sell_trade.get("ts") if sell_trade else None,
    }
    if complete:
        pnl_per_share = float(exit_price) - float(avg_entry)
        pnl_value = pnl_per_share * qty
        pnl_pct = (float(exit_price) / float(avg_entry)) - 1.0
        result.update(
            {
                "pnl_per_share": round(pnl_per_share, 4),
                "pnl_value": round(pnl_value, 2),
                "pnl_pct": pnl_pct,
            }
        )
    else:
        missing = []
        if not qty:
            missing.append("qty")
        if avg_entry is None:
            missing.append("avg_entry_price")
        if exit_price is None:
            missing.append("avg_exit_price")
        result["missing"] = missing
    return result


def _watchlist_payload() -> dict[str, Any]:
    path = STATE_DIR / "dynamic_watchlist.json"
    doc = _load_json(path, default={})
    symbols = doc.get("symbols") if isinstance(doc, dict) and isinstance(doc.get("symbols"), dict) else {}
    rows = []
    for symbol, row in symbols.items():
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "symbol": symbol,
                "score": _safe_float(row.get("score")),
                "last_seen": row.get("last_seen"),
                "last_reason": row.get("last_reason"),
                "sources": row.get("sources") or [],
                "peer_group": row.get("peer_group"),
                "peer_rank": row.get("peer_rank"),
                "sector_rank": row.get("sector_rank"),
                "momentum_grade": row.get("momentum_grade"),
            }
        )
    rows.sort(key=lambda r: (r["score"] if r["score"] is not None else -999), reverse=True)
    return {
        "file": _file_info(path),
        "updated_at": doc.get("updated_at") if isinstance(doc, dict) else None,
        "active_count": len(rows),
        "symbols": rows,
        "notes": doc.get("notes") if isinstance(doc, dict) else None,
    }


def _status_payload(
    performance: dict[str, Any],
    eod: dict[str, Any],
    scan: dict[str, Any],
    trades: list[dict[str, Any]],
    config: dict[str, Any],
    live: dict[str, Any] | None = None,
) -> dict[str, Any]:
    latest_perf = performance.get("latest") or {}
    latest_eod = eod.get("latest") or {}
    live_account = (live or {}).get("account") if live and live.get("ok") else None
    equity = _first_number(
        live_account.get("equity") if isinstance(live_account, dict) else None,
        latest_perf.get("portfolio_value"),
        latest_eod.get("equity"),
        scan.get("equity"),
    )
    cash = _first_number(
        live_account.get("cash") if isinstance(live_account, dict) else None,
        latest_perf.get("cash"),
        latest_eod.get("cash"),
        scan.get("current_portfolio", {}).get("cash_usd") if isinstance(scan.get("current_portfolio"), dict) else None,
    )
    positions_count = _first_number(
        len((live or {}).get("positions") or []) if live and live.get("ok") else None,
        latest_eod.get("positions_count"),
        scan.get("positions_count"),
    )
    failed_trade_count = sum(1 for tr in trades if "fail" in str(tr.get("event", "")).lower())
    latest_trade = trades[-1] if trades else None
    return {
        "mode": config.get("mode"),
        "equity": equity,
        "cash": cash,
        "positions_count": positions_count,
        "performance_points": performance.get("point_count", 0),
        "relative_return_pct": latest_perf.get("relative_return_pct"),
        "last_performance_timestamp": latest_perf.get("timestamp_utc"),
        "last_scan_timestamp": scan.get("ts"),
        "last_scan_file": scan.get("file", {}).get("path"),
        "last_eod_date": latest_eod.get("date"),
        "latest_trade": latest_trade,
        "recent_failed_trade_count": failed_trade_count,
        "schedule": config.get("scheduling", {}),
        "live_ok": bool(live and live.get("ok")),
        "live_error": (live or {}).get("error") if live else None,
    }


def _sources_payload(latest_scan_file: Path | None) -> dict[str, Any]:
    scan_files = [p for p in RESEARCH_DIR.glob("*_scan.json") if "_crypto_scan" not in p.name]
    preclose_files = list(RESEARCH_DIR.glob("*_preclose.json"))
    eod_files = list(RESEARCH_DIR.glob("*_eod.json"))
    return {
        "performance_history": _file_info(PERFORMANCE_PATH),
        "latest_scan": _file_info(latest_scan_file),
        "research_dir": _file_info(RESEARCH_DIR),
        "journal_dir": _file_info(JOURNAL_DIR),
        "counts": {
            "scan_reports": len(scan_files),
            "preclose_reports": len(preclose_files),
            "eod_reports": len(eod_files),
            "trade_journal_rows": _line_count(JOURNAL_DIR / "trades.jsonl"),
            "decision_journal_rows": _line_count(JOURNAL_DIR / "decisions.jsonl"),
        },
    }


def _config_summary() -> dict[str, Any]:
    path = ROOT / "config.yaml"
    raw: dict[str, Any] = {}
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            raw = loaded
    except Exception as exc:
        return {"file": _file_info(path), "error": f"{type(exc).__name__}: {exc}"}
    return {
        "file": _file_info(path),
        "mode": raw.get("mode"),
        "risk_profile": raw.get("risk_profile"),
        "benchmark": raw.get("benchmark"),
        "scheduling": raw.get("scheduling") or {},
        "performance_history": raw.get("performance_history") or {},
        "risk": raw.get("risk") or {},
        "selector": raw.get("selector") or {},
        "rebalance": raw.get("rebalance") or {},
        "cash_proxy": raw.get("cash_proxy") or {},
        "ai": {
            "enabled": (raw.get("ai") or {}).get("enabled"),
            "trade_critical_model": (raw.get("ai") or {}).get("trade_critical_model"),
            "verifier_model": (raw.get("ai") or {}).get("verifier_model"),
            "max_candidates_per_scan": (raw.get("ai") or {}).get("max_candidates_per_scan"),
            "timeout_seconds": (raw.get("ai") or {}).get("timeout_seconds"),
        },
    }


def _live_snapshot() -> dict[str, Any]:
    started = _now_iso()
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from src.alpaca_client import AlpacaClient
        from src.config import Config

        cfg = Config.load(ROOT / "config.yaml")
        client = AlpacaClient(cfg)
        account, positions = client.get_snapshot(force_refresh=True, log_detail=False)
        try:
            clock = client.get_clock()
            clock_payload = {
                "is_open": bool(getattr(clock, "is_open", False)),
                "timestamp": str(getattr(clock, "timestamp", "") or ""),
                "next_open": str(getattr(clock, "next_open", "") or ""),
                "next_close": str(getattr(clock, "next_close", "") or ""),
            }
        except Exception as exc:
            clock_payload = {"is_open": None, "error": f"{type(exc).__name__}: {exc}"}
        return {
            "requested": True,
            "ok": True,
            "started_at_utc": started,
            "finished_at_utc": _now_iso(),
            "error": None,
            "clock": clock_payload,
            "account": _serialize_account(account),
            "positions": [
                _compact_position(
                    _object_to_dict(pos),
                    total_equity=_safe_float(getattr(account, "equity", None)),
                    as_of=_now_iso(),
                )
                for pos in positions
            ],
            "note": "Live positions use Alpaca for account/quantity access and the bot valuation layer for prices.",
        }
    except Exception as exc:
        return {
            "requested": True,
            "ok": False,
            "started_at_utc": started,
            "finished_at_utc": _now_iso(),
            "error": f"{type(exc).__name__}: {exc}",
            "clock": None,
            "account": None,
            "positions": [],
        }


def _serialize_account(account: Any) -> dict[str, Any]:
    return {
        "equity": _safe_float(getattr(account, "equity", None)),
        "cash": _safe_float(getattr(account, "cash", None)),
        "buying_power": _safe_float(getattr(account, "buying_power", None)),
        "market_value": _safe_float(getattr(account, "market_value", None)),
        "long_market_value": _safe_float(getattr(account, "long_market_value", None)),
        "short_market_value": _safe_float(getattr(account, "short_market_value", None)),
        "currency": getattr(account, "currency", "USD"),
    }


def _compact_position(row: Any, *, total_equity: float | None = None, as_of: Any = None) -> dict[str, Any]:
    if not isinstance(row, dict):
        row = _object_to_dict(row)
    market_value = _first_number(row.get("market_value"), row.get("market_value_usd"), row.get("current_notional_usd"))
    pnl_pct = _first_number(row.get("pnl_pct"), row.get("unrealized_plpc"))
    weight = _first_number(row.get("current_weight_pct"), row.get("weight_pct"))
    if weight is None and market_value is not None and total_equity:
        weight = market_value / total_equity
    return {
        "symbol": row.get("symbol"),
        "ts": as_of or row.get("ts") or row.get("timestamp"),
        "as_of": as_of or row.get("as_of") or row.get("ts") or row.get("timestamp"),
        "side": str(row.get("side") or "").split(".")[-1].lower() or None,
        "qty": _first_number(row.get("qty"), row.get("current_qty")),
        "avg_entry": _first_number(row.get("avg_entry"), row.get("avg_entry_price")),
        "current_price": _first_number(row.get("current_price"), row.get("price")),
        "market_value": market_value,
        "weight_pct": weight,
        "pnl_pct": pnl_pct,
        "pnl_dollars": _first_number(row.get("pnl_dollars"), row.get("unrealized_pl"), row.get("unrealized_pl_usd")),
        "price_source": row.get("price_source"),
        "target_pct": _safe_float(row.get("target_pct")),
        "target_qty": _safe_float(row.get("target_qty")),
        "reason": row.get("reason"),
    }


def _compact_trade(row: dict[str, Any]) -> dict[str, Any]:
    sizing = row.get("sizing") if isinstance(row.get("sizing"), dict) else {}
    decision = row.get("decision") if isinstance(row.get("decision"), dict) else {}
    detail = (
        sizing.get("reasoning")
        or row.get("reason")
        or row.get("error")
        or decision.get("reasoning")
        or row.get("final_status")
        or ""
    )
    return {
        "ts": row.get("ts"),
        "event": row.get("event"),
        "symbol": row.get("symbol") or sizing.get("symbol") or decision.get("symbol"),
        "side": sizing.get("side") or row.get("side"),
        "order_id": row.get("order_id"),
        "qty": _first_number(row.get("qty"), sizing.get("qty"), row.get("filled_qty")),
        "notional": _first_number(sizing.get("notional"), row.get("delta_notional")),
        "filled_qty": _safe_float(row.get("filled_qty")),
        "filled_avg_price": _safe_float(row.get("filled_avg_price")),
        "status": row.get("final_status") or row.get("status"),
        "ok": row.get("ok"),
        "detail": _truncate(detail, 360),
        "error": _truncate(row.get("error"), 360),
        "raw": _prune(row, max_depth=3, max_list=8),
    }


def _compact_decision(row: dict[str, Any]) -> dict[str, Any]:
    result = row.get("result") if isinstance(row.get("result"), dict) else {}
    context = row.get("context") if isinstance(row.get("context"), dict) else {}
    verdict = row.get("verdict") if isinstance(row.get("verdict"), dict) else {}
    detail = (
        row.get("reasoning")
        or row.get("reason")
        or verdict.get("thesis")
        or result.get("portfolio_thesis")
        or context.get("portfolio_thesis")
        or ""
    )
    return {
        "ts": row.get("ts"),
        "event": row.get("event"),
        "symbol": row.get("symbol") or verdict.get("symbol"),
        "action": row.get("action") or verdict.get("final_action") or result.get("action"),
        "confidence": _first_number(row.get("confidence"), verdict.get("confidence")),
        "model": row.get("model") or verdict.get("_model"),
        "detail": _truncate(detail, 420),
        "raw": _prune(row, max_depth=3, max_list=8),
    }


def _position_history(eod_history: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for day in eod_history:
        date = day.get("date")
        for pos in day.get("positions") or []:
            symbol = str(pos.get("symbol") or "").upper()
            if not symbol:
                continue
            out.setdefault(symbol, []).append(
                {
                    "date": date,
                    "market_value": pos.get("market_value"),
                    "pnl_pct": pos.get("pnl_pct"),
                    "qty": pos.get("qty"),
                    "current_price": pos.get("current_price"),
                }
            )
    return out


def _latest_scan() -> tuple[Path | None, Any]:
    paths = [p for p in RESEARCH_DIR.glob("*_scan.json") if "_crypto_scan" not in p.name]
    return _latest_from_paths(paths)


def _latest_json(pattern: str) -> tuple[Path | None, Any]:
    return _latest_from_paths(RESEARCH_DIR.glob(pattern))


def _latest_from_paths(paths: Any) -> tuple[Path | None, Any]:
    items = sorted(list(paths), key=_file_sort_key)
    if not items:
        return None, None
    path = items[-1]
    return path, _load_json(path, default={})


def _load_json(path: Path, *, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _read_jsonl_tail(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in deque(fh, maxlen=limit):
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    rows.append(parsed)
    except OSError:
        return []
    return rows


def _file_sort_key(path: Path) -> tuple[str, float]:
    return (path.name, path.stat().st_mtime if path.exists() else 0.0)


def _file_info(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"path": None, "exists": False}
    exists = path.exists()
    info = {"path": _rel(path), "exists": exists}
    if exists:
        try:
            stat = path.stat()
            info.update(
                {
                    "modified_at_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
                    "bytes": stat.st_size,
                    "is_dir": path.is_dir(),
                }
            )
        except OSError:
            pass
    return info


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def _date_from_name(name: str) -> str | None:
    if len(name) >= 10 and name[4] == "-" and name[7] == "-":
        return name[:10]
    return None


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _first_number(*values: Any) -> float | None:
    for value in values:
        parsed = _safe_float(value)
        if parsed is not None:
            return parsed
    return None


def _truncate(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _object_to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    out: dict[str, Any] = {}
    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            value = getattr(obj, name)
        except Exception:
            continue
        if callable(value):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[name] = value
        else:
            out[name] = str(value)
    return out


def _prune(value: Any, *, max_depth: int = 3, max_list: int = 10, _depth: int = 0) -> Any:
    if _depth >= max_depth:
        if isinstance(value, dict):
            return {"_type": "dict", "_keys": list(value.keys())[:20]}
        if isinstance(value, list):
            return {"_type": "list", "_length": len(value)}
        return _truncate(value, 500)
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for idx, (key, item) in enumerate(value.items()):
            if idx >= 36:
                out["_truncated_keys"] = max(0, len(value) - idx)
                break
            out[str(key)] = _prune(item, max_depth=max_depth, max_list=max_list, _depth=_depth + 1)
        return out
    if isinstance(value, list):
        return [_prune(item, max_depth=max_depth, max_list=max_list, _depth=_depth + 1) for item in value[:max_list]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return _truncate(value, 1000) if isinstance(value, str) else value
    return _truncate(value, 500)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value)
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "TradingBotDashboard/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path in ("", "/", "/index.html"):
                self._send_file(STATIC_DIR / "index.html")
                return
            if path == "/api/dashboard":
                params = parse_qs(parsed.query)
                live = str((params.get("live") or ["0"])[0]).lower() in {"1", "true", "yes"}
                self._send_json(build_dashboard_payload(include_live=live))
                return
            if path == "/api/raw/performance":
                self._send_json(_load_json(PERFORMANCE_PATH, default={"points": []}))
                return
            if path == "/api/raw/latest-scan":
                _, doc = _latest_scan()
                self._send_json(doc or {})
                return
            if path.startswith("/static/"):
                rel = path[len("/static/") :]
                self._send_file(_safe_static_path(rel))
                return
            self._send_file(_safe_static_path(path.lstrip("/")))
        except FileNotFoundError:
            self._send_json({"error": "not_found", "path": path}, status=404)
        except PermissionError:
            self._send_json({"error": "forbidden", "path": path}, status=403)
        except Exception as exc:
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))

    def _send_json(self, payload: Any, *, status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(str(path))
        body = path.read_bytes()
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _safe_static_path(rel: str) -> Path:
    target = (STATIC_DIR / rel).resolve()
    static_root = STATIC_DIR.resolve()
    if target != static_root and static_root not in target.parents:
        raise PermissionError(rel)
    return target


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local trading bot dashboard.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    with ThreadingHTTPServer((args.host, args.port), DashboardHandler) as httpd:
        print(f"Trading bot dashboard running at http://{args.host}:{args.port}")
        print(f"Reading performance history from {_rel(PERFORMANCE_PATH)}")
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
