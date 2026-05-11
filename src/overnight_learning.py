"""Learning ledger for preclose overnight candidates.

The preclose selector needs to learn from *all* candidates, not only names it
actually bought. This module records every scored candidate with the evidence
seen near the close, then later resolves the next session's open/close so the
bot can estimate symbol-, sector-, source-, earnings-, and score-bucket edge.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
_OUTCOME_CACHE: dict[tuple[str, int], tuple[float, list[dict[str, Any]]]] = {}


def _cfg_get(cfg, *keys: str, default: Any = None) -> Any:
    try:
        return cfg.get(*keys, default=default)
    except Exception:
        return default


def _enabled(cfg) -> bool:
    return bool(_cfg_get(cfg, "overnight", "learning", "enabled", default=True))


def _state_path(cfg) -> Path:
    rel = _cfg_get(
        cfg,
        "overnight", "learning", "state_file",
        default="data/state/overnight_learning_pending.json",
    )
    return ROOT / str(rel)


def _journal_path(cfg) -> Path:
    rel = _cfg_get(
        cfg,
        "overnight", "learning", "journal_file",
        default="data/journal/overnight_learning.jsonl",
    )
    return ROOT / str(rel)


def _load_state(cfg) -> dict[str, Any]:
    path = _state_path(cfg)
    if not path.exists():
        return {"pending": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"pending": {}}
    if not isinstance(data, dict):
        return {"pending": {}}
    data.setdefault("pending", {})
    return data


def _save_state(cfg, state: dict[str, Any]) -> None:
    path = _state_path(cfg)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    except OSError as exc:
        log.warning("overnight-learning state save failed: %s", exc)


def _append_jsonl(cfg, payload: dict[str, Any]) -> None:
    path = _journal_path(cfg)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str, separators=(",", ":")) + "\n")
    except OSError as exc:
        log.warning("overnight-learning journal write failed: %s", exc)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return pd.Timestamp(value).date()
        except Exception:
            return None


def _run_date(summary: dict[str, Any]) -> date:
    return _as_date(summary.get("ts")) or datetime.now(timezone.utc).date()


def _execution_symbols(summary: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for row in summary.get("new_executions") or []:
        sym = (
            row.get("symbol")
            or (row.get("execution") or {}).get("symbol")
            or ((row.get("sizing") or {}).get("symbol"))
        )
        ok = bool(row.get("ok") or (row.get("execution") or {}).get("ok") or row.get("dry_run"))
        if sym and ok:
            out.add(str(sym).upper())
    return out


def _candidate_price(report: dict[str, Any]) -> float | None:
    overnight = report.get("overnight") or {}
    price = overnight.get("price")
    if price in (None, ""):
        chart = report.get("intraday_chart") or {}
        price = chart.get("current_price")
    value = _as_float(price, 0.0)
    return value if value > 0 else None


def _score_bucket(score: float | None) -> str:
    s = _as_float(score, 0.0)
    if s >= 0.75:
        return "very_high"
    if s >= 0.55:
        return "high"
    if s >= 0.35:
        return "medium"
    if s >= 0.10:
        return "low_positive"
    if s >= -0.10:
        return "neutral"
    return "negative"


def _earnings_bucket(report: dict[str, Any]) -> str:
    profile = (
        ((report.get("overnight_edge") or {}).get("earnings_profile"))
        or report.get("earnings_profile")
        or {}
    )
    if profile.get("event_risk_overnight"):
        return "event_risk"
    if profile.get("post_earnings_session"):
        return "post_earnings"
    days = profile.get("days_until_earnings")
    if days is None:
        earnings = report.get("earnings") or {}
        days = earnings.get("days_until_earnings")
    try:
        if days is not None and 0 <= int(days) <= 2:
            return "near_earnings"
    except (TypeError, ValueError):
        pass
    return "no_near_earnings"


def _features_from_report(report: dict[str, Any]) -> dict[str, Any]:
    edge = report.get("overnight_edge") or {}
    overnight = report.get("overnight") or {}
    sector_profile = edge.get("sector_momentum") or {}
    earnings_profile = edge.get("earnings_profile") or report.get("earnings_profile") or {}
    base_score = overnight.get("score")
    adjusted_score = edge.get("adjusted_score", base_score)
    return {
        "base_score": _as_float(base_score, 0.0),
        "adjusted_score": _as_float(adjusted_score, _as_float(base_score, 0.0)),
        "score_bucket": _score_bucket(adjusted_score),
        "sector": sector_profile.get("sector") or report.get("sector") or "Other",
        "sources": sorted(str(s) for s in (report.get("discovery_sources") or [])),
        "earnings_bucket": _earnings_bucket(report),
        "earnings_timing_class": earnings_profile.get("timing_class"),
        "event_risk_overnight": bool(earnings_profile.get("event_risk_overnight")),
        "post_earnings_session": bool(earnings_profile.get("post_earnings_session")),
        "risk_flags": sorted(str(s) for s in (edge.get("risk_flags") or [])),
    }


def record_preclose_candidates(
    cfg,
    summary: dict[str, Any],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Persist every scored preclose candidate for later close-to-open outcome."""
    if not _enabled(cfg):
        return {"enabled": False}
    if dry_run and not bool(_cfg_get(cfg, "overnight", "learning", "record_dry_runs", default=True)):
        return {"enabled": True, "recorded": 0, "skipped": "dry_run_disabled"}

    run_id = str(summary.get("ts") or datetime.now(timezone.utc).isoformat())
    preclose_date = _run_date(summary).isoformat()
    executed = _execution_symbols(summary)
    state = _load_state(cfg)
    pending = state.setdefault("pending", {})
    recorded = 0
    for report in summary.get("candidate_reports") or []:
        sym = str(report.get("symbol") or "").upper()
        if not sym or "/" in sym:
            continue
        price = _candidate_price(report)
        if price is None:
            continue
        key = f"{run_id}|{sym}"
        row = {
            "event": "preclose_candidate_observed",
            "run_id": run_id,
            "symbol": sym,
            "preclose_date": preclose_date,
            "observed_at": run_id,
            "decision_price": price,
            "market_bias": summary.get("market_bias"),
            "weekend_session": bool(summary.get("weekend_session")),
            "session_gap_calendar_days": summary.get("session_gap_calendar_days"),
            "selected": bool(sym in executed or ("skipped" not in report and _as_float(((report.get("overnight_edge") or {}).get("adjusted_score")), -9) > -9)),
            "qualified": bool("skipped" not in report),
            "executed": bool(sym in executed),
            "skipped_reason": report.get("skipped"),
            "features": _features_from_report(report),
            "overnight": report.get("overnight"),
            "overnight_edge": report.get("overnight_edge"),
            "earnings": report.get("earnings"),
        }
        pending[key] = row
        _append_jsonl(cfg, row)
        recorded += 1
    _save_state(cfg, state)
    return {"enabled": True, "recorded": recorded, "pending": len(pending)}


def _slice_symbol(df, symbol: str):
    if df is None or getattr(df, "empty", True):
        return None
    try:
        if "symbol" in df.index.names:
            return df.xs(symbol, level="symbol")
        return df
    except Exception:
        return None


def _next_session_row(daily_df, symbol: str, preclose_date: date):
    slc = _slice_symbol(daily_df, symbol)
    if slc is None or getattr(slc, "empty", True):
        return None
    try:
        slc = slc.sort_index()
        for idx, row in slc.iterrows():
            row_date = idx.date() if hasattr(idx, "date") else pd.Timestamp(idx).date()
            if row_date > preclose_date:
                return row_date, row
    except Exception:
        return None
    return None


def resolve_overnight_outcomes(cfg, client) -> dict[str, Any]:
    """Resolve pending candidates once the next daily bar is available."""
    if not _enabled(cfg):
        return {"enabled": False}
    state = _load_state(cfg)
    pending = state.setdefault("pending", {})
    if not pending:
        return {"enabled": True, "pending": 0, "resolved": 0}

    max_age_days = int(_cfg_get(cfg, "overnight", "learning", "max_pending_days", default=14) or 14)
    today = datetime.now(timezone.utc).date()
    symbols = sorted({str(row.get("symbol") or "").upper() for row in pending.values() if row.get("symbol")})
    if not symbols:
        state["pending"] = {}
        _save_state(cfg, state)
        return {"enabled": True, "pending": 0, "resolved": 0}
    try:
        bars = client.get_stock_bars(symbols, lookback_days=max(max_age_days + 5, 20))
    except Exception as exc:
        log.debug("overnight-learning daily bars fetch failed: %s", exc)
        return {"enabled": True, "pending": len(pending), "resolved": 0, "error": str(exc)}

    resolved: list[dict[str, Any]] = []
    expired = 0
    for key, row in list(pending.items()):
        sym = str(row.get("symbol") or "").upper()
        pre_date = _as_date(row.get("preclose_date"))
        decision_price = _as_float(row.get("decision_price"), 0.0)
        if not sym or pre_date is None or decision_price <= 0:
            pending.pop(key, None)
            expired += 1
            continue
        if (today - pre_date).days > max_age_days:
            pending.pop(key, None)
            expired += 1
            continue
        found = _next_session_row(bars, sym, pre_date)
        if found is None:
            continue
        next_date, bar = found
        try:
            open_price = float(bar.get("open"))
            high_price = float(bar.get("high"))
            low_price = float(bar.get("low"))
            close_price = float(bar.get("close"))
        except (TypeError, ValueError):
            continue
        if open_price <= 0 or close_price <= 0:
            continue
        outcome = {
            "event": "overnight_candidate_outcome",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "run_id": row.get("run_id"),
            "symbol": sym,
            "preclose_date": pre_date.isoformat(),
            "next_session_date": next_date.isoformat(),
            "decision_price": round(decision_price, 4),
            "next_open": round(open_price, 4),
            "next_high": round(high_price, 4),
            "next_low": round(low_price, 4),
            "next_close": round(close_price, 4),
            "gap_return": round(open_price / decision_price - 1.0, 5),
            "next_close_return": round(close_price / decision_price - 1.0, 5),
            "open_to_close_return": round(close_price / open_price - 1.0, 5),
            "overnight_low_return": round(low_price / decision_price - 1.0, 5),
            "overnight_high_return": round(high_price / decision_price - 1.0, 5),
            "selected": bool(row.get("selected")),
            "qualified": bool(row.get("qualified")),
            "executed": bool(row.get("executed")),
            "skipped_reason": row.get("skipped_reason"),
            "features": row.get("features") or {},
            "overnight": row.get("overnight"),
            "overnight_edge": row.get("overnight_edge"),
            "earnings": row.get("earnings"),
        }
        _append_jsonl(cfg, outcome)
        resolved.append(outcome)
        pending.pop(key, None)
    if resolved or expired:
        _save_state(cfg, state)
    return {
        "enabled": True,
        "pending": len(pending),
        "resolved": len(resolved),
        "expired": expired,
        "symbols": sorted({r["symbol"] for r in resolved}),
    }


def _iter_outcomes(cfg, max_records: int) -> Iterable[dict[str, Any]]:
    path = _journal_path(cfg)
    if not path.exists():
        return []
    cache_key = (str(path), int(max_records))
    try:
        mtime = path.stat().st_mtime
        cached = _OUTCOME_CACHE.get(cache_key)
        if cached and cached[0] == mtime:
            return list(cached[1])
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines[-max(max_records * 3, max_records):]:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") == "overnight_candidate_outcome":
            out.append(row)
    out = out[-max_records:]
    try:
        _OUTCOME_CACHE[cache_key] = (mtime, list(out))
    except Exception:
        pass
    return out


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "sample_size": 0,
            "avg_gap_return": 0.0,
            "win_rate": 0.5,
            "gap_down_risk": 0.0,
            "p20_gap_return": 0.0,
        }
    gaps = np.array([_as_float(r.get("gap_return"), 0.0) for r in rows], dtype=float)
    return {
        "sample_size": int(len(gaps)),
        "avg_gap_return": round(float(np.mean(gaps)), 5),
        "win_rate": round(float(np.mean(gaps > 0)), 3),
        "gap_down_risk": round(float(np.mean(gaps <= -0.02)), 3),
        "p20_gap_return": round(float(np.percentile(gaps, 20)), 5),
    }


def _feature(row: dict[str, Any], name: str, default: Any = None) -> Any:
    return (row.get("features") or {}).get(name, default)


def estimate_overnight_edge(
    cfg,
    symbol: str,
    features: dict[str, Any],
) -> dict[str, Any]:
    """Return learned adjustment from prior preclose candidate outcomes."""
    if not _enabled(cfg):
        return {"enabled": False, "adjustment": 0.0, "sample_size": 0}
    max_records = int(_cfg_get(cfg, "overnight", "learning", "max_history_records", default=2000) or 2000)
    min_sample = int(_cfg_get(cfg, "overnight", "learning", "min_sample_for_adjustment", default=8) or 8)
    max_adjustment = float(_cfg_get(cfg, "overnight", "learning", "max_score_adjustment", default=0.15) or 0.15)
    rows = list(_iter_outcomes(cfg, max_records))
    if not rows:
        return {
            "enabled": True,
            "adjustment": 0.0,
            "sample_size": 0,
            "reason": "no_history_yet",
        }

    sym = str(symbol or "").upper()
    sector = str(features.get("sector") or "Other")
    score_bucket = str(features.get("score_bucket") or _score_bucket(features.get("adjusted_score")))
    earnings_bucket = str(features.get("earnings_bucket") or "no_near_earnings")
    sources = {str(s) for s in (features.get("sources") or [])}

    groups: list[tuple[str, float, list[dict[str, Any]]]] = [
        ("global", 0.20, rows),
        ("score_bucket", 0.25, [r for r in rows if _feature(r, "score_bucket") == score_bucket]),
        ("sector", 0.20, [r for r in rows if str(_feature(r, "sector", "Other")) == sector]),
        ("earnings_bucket", 0.15, [r for r in rows if _feature(r, "earnings_bucket") == earnings_bucket]),
        ("symbol", 0.25, [r for r in rows if str(r.get("symbol") or "").upper() == sym]),
    ]
    if sources:
        groups.append((
            "source_overlap",
            0.15,
            [
                r for r in rows
                if sources.intersection({str(s) for s in (_feature(r, "sources", []) or [])})
            ],
        ))

    weighted: list[tuple[float, dict[str, Any], str]] = []
    for name, weight, matched in groups:
        if name != "global" and len(matched) < min_sample:
            continue
        summary = _summarize(matched)
        if summary["sample_size"] <= 0:
            continue
        weighted.append((weight, summary, name))

    if not weighted:
        summary = _summarize(rows)
        weighted = [(1.0, summary, "global_fallback")]

    total_weight = sum(w for w, _s, _n in weighted) or 1.0
    avg_gap = sum(w * float(s["avg_gap_return"]) for w, s, _n in weighted) / total_weight
    win_rate = sum(w * float(s["win_rate"]) for w, s, _n in weighted) / total_weight
    gap_down_risk = sum(w * float(s["gap_down_risk"]) for w, s, _n in weighted) / total_weight
    p20 = sum(w * float(s["p20_gap_return"]) for w, s, _n in weighted) / total_weight
    # Translate realized edge into score-space. A +1% average gap and a 60%
    # win rate should help, but a high -2% gap-down frequency should dominate.
    raw_adj = (avg_gap * 8.0) + ((win_rate - 0.50) * 0.20) - (gap_down_risk * 0.18)
    adjustment = max(-max_adjustment, min(max_adjustment, raw_adj))
    return {
        "enabled": True,
        "adjustment": round(float(adjustment), 3),
        "sample_size": int(sum(s["sample_size"] for _w, s, _n in weighted)),
        "avg_gap_return": round(float(avg_gap), 5),
        "win_rate": round(float(win_rate), 3),
        "gap_down_risk": round(float(gap_down_risk), 3),
        "p20_gap_return": round(float(p20), 5),
        "groups_used": [name for _w, _s, name in weighted],
    }
