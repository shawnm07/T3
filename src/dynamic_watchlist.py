"""Auto-maintained dynamic watchlist.

The dynamic watchlist is an eligibility memory, not a preference signal. A
symbol on this list is allowed back into discovery on future scans, but scoring
must still come from live momentum, peer leadership, catalysts, and risk data.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]


def _cfg(cfg: Any, *keys: str, default: Any = None) -> Any:
    if cfg is None or not hasattr(cfg, "get"):
        return default
    return cfg.get(*keys, default=default)


def _path(cfg: Any) -> Path:
    rel = _cfg(
        cfg,
        "dynamic_watchlist",
        "state_file",
        default="data/state/dynamic_watchlist.json",
    )
    path = Path(str(rel))
    return path if path.is_absolute() else ROOT / path


def _now_iso(now: datetime | None = None) -> str:
    ts = now or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.isoformat()


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        ts = datetime.fromisoformat(text)
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _load_state(cfg: Any) -> dict[str, Any]:
    path = _path(cfg)
    if not path.exists():
        return {"symbols": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"symbols": {}}
    if isinstance(data, dict) and isinstance(data.get("symbols"), dict):
        return data
    if isinstance(data, dict):
        return {"symbols": data}
    return {"symbols": {}}


def load_dynamic_watchlist(cfg: Any, now: datetime | None = None) -> list[str]:
    """Return active dynamic symbols, filtered for TTL."""
    if not bool(_cfg(cfg, "dynamic_watchlist", "enabled", default=True)):
        return []
    ttl_days = float(_cfg(cfg, "dynamic_watchlist", "ttl_days", default=7) or 7)
    current = now or datetime.now(timezone.utc)
    symbols = _load_state(cfg).get("symbols", {})
    active: list[tuple[str, float, datetime]] = []
    for sym, info in symbols.items():
        if not isinstance(info, dict):
            continue
        seen = _parse_ts(info.get("last_seen"))
        if seen is None:
            continue
        age_days = (current - seen).total_seconds() / 86400.0
        if age_days > ttl_days:
            continue
        try:
            score = float(info.get("score", 0) or 0)
        except (TypeError, ValueError):
            score = 0.0
        active.append((str(sym).upper(), score, seen))
    active.sort(key=lambda row: (row[1], row[2]), reverse=True)
    return [sym for sym, _score, _seen in active]


def update_dynamic_watchlist(
    cfg: Any,
    candidate_pool: list[dict[str, Any]],
    *,
    selected_symbols: list[str] | None = None,
    missed_breakouts: list[dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Update the persisted dynamic watchlist from this scan's evidence."""
    if not bool(_cfg(cfg, "dynamic_watchlist", "enabled", default=True)):
        return {"skipped": "disabled"}

    add_score = float(_cfg(cfg, "dynamic_watchlist", "add_score", default=65) or 65)
    keep_score = float(_cfg(cfg, "dynamic_watchlist", "keep_score", default=45) or 45)
    ttl_days = float(_cfg(cfg, "dynamic_watchlist", "ttl_days", default=7) or 7)
    max_symbols = int(_cfg(cfg, "dynamic_watchlist", "max_symbols", default=80) or 80)
    selected = {str(s).upper() for s in selected_symbols or []}
    missed = {str(r.get("symbol") or "").upper() for r in missed_breakouts or []}
    current = now or datetime.now(timezone.utc)
    now_text = _now_iso(current)

    state = _load_state(cfg)
    symbols: dict[str, dict[str, Any]] = {
        str(sym).upper(): dict(info or {})
        for sym, info in (state.get("symbols") or {}).items()
        if sym
    }

    added_or_refreshed: list[str] = []
    for block in candidate_pool or []:
        sym = str(block.get("symbol") or "").upper()
        if not sym or "/" in sym:
            continue
        try:
            score = float(block.get("candidate_priority_score", 0) or 0)
        except (TypeError, ValueError):
            score = 0.0
        momentum_grade = str((block.get("momentum_profile") or {}).get("grade") or "")
        qualifies = (
            score >= add_score
            or sym in selected
            or sym in missed
            or momentum_grade == "strong_continuation"
        )
        if not qualifies:
            continue
        symbols[sym] = {
            "score": round(score, 2),
            "last_seen": now_text,
            "last_reason": _reason_for(block, sym in selected, sym in missed),
            "sources": list(block.get("discovery_sources") or []),
            "peer_group": block.get("peer_group"),
            "peer_rank": block.get("peer_rank"),
            "sector_rank": block.get("sector_rank"),
            "momentum_grade": momentum_grade,
        }
        added_or_refreshed.append(sym)

    kept: dict[str, dict[str, Any]] = {}
    removed: list[dict[str, Any]] = []
    for sym, info in symbols.items():
        seen = _parse_ts(info.get("last_seen"))
        age_days = (current - seen).total_seconds() / 86400.0 if seen else ttl_days + 1
        score = float(info.get("score", 0) or 0)
        if age_days > ttl_days:
            removed.append({"symbol": sym, "reason": "ttl_expired"})
            continue
        if score < keep_score and sym not in added_or_refreshed:
            removed.append({"symbol": sym, "reason": "score_below_keep"})
            continue
        kept[sym] = info

    ranked = sorted(
        kept.items(),
        key=lambda kv: (
            float(kv[1].get("score", 0) or 0),
            str(kv[1].get("last_seen", "")),
        ),
        reverse=True,
    )
    if len(ranked) > max_symbols:
        for sym, _info in ranked[max_symbols:]:
            removed.append({"symbol": sym, "reason": "max_symbols_trim"})
        ranked = ranked[:max_symbols]

    state = {
        "updated_at": now_text,
        "symbols": {sym: info for sym, info in ranked},
        "notes": "Eligibility only; dynamic-watchlist membership is not a score bonus.",
    }
    path = _path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return {
        "state_file": str(path),
        "active_count": len(ranked),
        "added_or_refreshed": sorted(set(added_or_refreshed)),
        "removed": removed,
    }


def remove_dynamic_watchlist_symbols(
    cfg: Any,
    symbols: Iterable[str],
    *,
    reason: str = "asset_not_tradable",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Remove known-bad symbols from the persisted dynamic watchlist."""
    if not bool(_cfg(cfg, "dynamic_watchlist", "enabled", default=True)):
        return {"skipped": "disabled"}

    requested = sorted({
        str(sym).strip().upper()
        for sym in symbols or []
        if str(sym or "").strip()
    })
    current = now or datetime.now(timezone.utc)
    now_text = _now_iso(current)
    state = _load_state(cfg)
    stored: dict[str, dict[str, Any]] = {
        str(sym).upper(): dict(info or {})
        for sym, info in (state.get("symbols") or {}).items()
        if sym
    }

    removed: list[dict[str, Any]] = []
    for sym in requested:
        if sym not in stored:
            continue
        stored.pop(sym, None)
        removed.append({"symbol": sym, "reason": reason})

    if not removed:
        return {
            "state_file": str(_path(cfg)),
            "active_count": len(stored),
            "removed": [],
        }

    history = list(state.get("last_removed") or [])
    history.extend({
        "symbol": row["symbol"],
        "reason": row["reason"],
        "removed_at": now_text,
    } for row in removed)

    state = {
        **{k: v for k, v in state.items() if k != "symbols"},
        "updated_at": now_text,
        "symbols": stored,
        "last_removed": history[-50:],
        "notes": state.get(
            "notes",
            "Eligibility only; dynamic-watchlist membership is not a score bonus.",
        ),
    }
    path = _path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return {
        "state_file": str(path),
        "active_count": len(stored),
        "removed": removed,
    }


def _reason_for(block: dict[str, Any], selected: bool, missed: bool) -> str:
    if selected:
        return "selected_by_portfolio_selector"
    if missed:
        return "missed_breakout_candidate"
    grade = str((block.get("momentum_profile") or {}).get("grade") or "")
    if grade == "strong_continuation":
        return "strong_live_continuation"
    return "high_candidate_priority_score"
