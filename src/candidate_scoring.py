"""Deterministic candidate scoring helpers for discovery and selector context.

These scores do not place trades. They make sure the AI sees the right names
and enough relative-strength evidence to choose the actual outperformer rather
than the familiar ticker.
"""
from __future__ import annotations

from typing import Any, Iterable


UNBIASED_LIST_SOURCES = {
    "watchlist",
    "legacy_watchlist",
    "seed_watchlist",
    "dynamic_watchlist",
}

ACTIVE_DISCOVERY_SOURCES = {
    "av_gainers",
    "av_most_active",
    "av_news",
    "tv_breakout",
    "tv_squeeze",
}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def _norm_signal(value: Any) -> float:
    """Map a -1..+1 signal to 0..100, defaulting to neutral."""
    if value is None:
        return 50.0
    return _clamp((_num(value) + 1.0) * 50.0)


def discovery_priority_score(
    sources: Iterable[str] | None,
    *,
    change_pct: float | None = None,
    volume: float | None = None,
) -> tuple[float, list[str]]:
    """Early pre-AI priority used only to keep the best symbols in the pool.

    Seed/dynamic watchlist sources intentionally add no points. They make a
    symbol eligible for evaluation; they do not make it preferable.
    """
    src = {str(s) for s in (sources or [])}
    score = 0.0
    reasons: list[str] = []

    weighted_sources = {
        "av_gainers": 36.0,
        "tv_breakout": 34.0,
        "av_news": 28.0,
        "av_most_active": 18.0,
        "tv_squeeze": 12.0,
        "peer_group": 8.0,  # context inclusion, not a buy preference
    }
    for name, pts in weighted_sources.items():
        if name in src:
            score += pts
            reasons.append(name)

    # Losers can be useful context, but this long-only selector should not let
    # downside momentum crowd out actual upside breakouts.
    if "av_losers" in src:
        score += 3.0
        reasons.append("av_losers_context")

    chg = _num(change_pct, 0.0)
    if chg > 0:
        score += min(30.0, chg * 300.0)
        reasons.append("positive_mover")
    elif chg < -0.02:
        score -= min(12.0, abs(chg) * 120.0)
        reasons.append("negative_mover_penalty")

    vol = _num(volume, 0.0)
    if vol >= 5_000_000:
        score += 6.0
        reasons.append("high_liquidity")
    elif vol >= 1_000_000:
        score += 3.0
        reasons.append("liquid")

    if not (src - UNBIASED_LIST_SOURCES) and src:
        reasons.append("list_eligibility_no_score_bonus")

    return round(_clamp(score), 2), reasons


def selector_priority_score(block: dict[str, Any]) -> tuple[float, list[str]]:
    """Full selector-side priority from live tape, technicals, and discovery.

    This is still not the final trade decision. It is a deterministic evidence
    score that helps surface breakouts and maintain a dynamic watchlist.
    """
    reasons: list[str] = []
    profile = block.get("momentum_profile") or {}
    chart = block.get("intraday_chart") or {}
    sources = block.get("discovery_sources") or []

    momentum = _num(profile.get("score"), 0.0)
    if profile.get("grade"):
        reasons.append(str(profile.get("grade")))

    tech = _norm_signal(block.get("tech_score"))
    sent = _norm_signal(block.get("sent_score"))

    source_score, source_reasons = discovery_priority_score(
        sources,
        change_pct=block.get("intraday_change_pct"),
        volume=chart.get("session_volume"),
    )
    reasons.extend(source_reasons)

    rel_vol = _num(block.get("twenty_day_volume_ratio"), 1.0)
    if rel_vol > 0:
        rel_vol_score = _clamp(45.0 + min(45.0, (rel_vol - 1.0) * 30.0))
        if rel_vol >= 1.5:
            reasons.append("relative_volume_leadership")
    else:
        rel_vol_score = 45.0

    intraday = _num(block.get("intraday_change_pct"), 0.0)
    intraday_score = _clamp(50.0 + intraday * 800.0)
    if intraday >= 0.02:
        reasons.append("intraday_outperformer")

    score = (
        0.38 * momentum
        + 0.20 * tech
        + 0.10 * sent
        + 0.12 * source_score
        + 0.10 * rel_vol_score
        + 0.10 * intraday_score
    )

    if (profile or {}).get("gap_only_risk") or chart.get("gap_only_risk"):
        score -= 18.0
        reasons.append("gap_only_penalty")
    if str(profile.get("grade") or "") == "missing_intraday":
        score -= 20.0
        reasons.append("missing_intraday_penalty")
    if profile and not profile.get("passes_new_entry_gate") and not block.get("currently_held"):
        score -= 8.0
        reasons.append("new_entry_gate_not_confirmed")

    return round(_clamp(score), 2), _dedupe(reasons)


def annotate_candidate_leadership(
    candidate_pool: list[dict[str, Any]],
    peer_groups: dict[str, list[str]] | None,
    *,
    peer_gap_threshold: float = 10.0,
) -> None:
    """Mutate candidate blocks with priority, peer, and sector leadership data."""
    if not candidate_pool:
        return

    peer_by_symbol: dict[str, str] = {}
    for group_name, members in (peer_groups or {}).items():
        for sym in members or []:
            peer_by_symbol[str(sym).upper()] = str(group_name)

    for block in candidate_pool:
        sym = str(block.get("symbol") or "").upper()
        block["symbol"] = sym
        score, reasons = selector_priority_score(block)
        block["candidate_priority_score"] = score
        block["candidate_priority_reasons"] = reasons
        block["peer_group"] = peer_by_symbol.get(sym)

    def _annotate_group(
        key_name: str,
        value_getter,
        rank_prefix: str,
    ) -> None:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for block in candidate_pool:
            value = value_getter(block)
            if not value:
                continue
            grouped.setdefault(str(value), []).append(block)
        for group_value, members in grouped.items():
            ranked = sorted(
                members,
                key=lambda b: _num(b.get("candidate_priority_score"), 0.0),
                reverse=True,
            )
            if not ranked:
                continue
            leader = ranked[0]
            leader_score = _num(leader.get("candidate_priority_score"), 0.0)
            size = len(ranked)
            for idx, block in enumerate(ranked, start=1):
                score = _num(block.get("candidate_priority_score"), 0.0)
                percentile = 1.0 if size == 1 else 1.0 - ((idx - 1) / (size - 1))
                block[f"{rank_prefix}_rank"] = idx
                block[f"{rank_prefix}_group_size"] = size
                block[f"{rank_prefix}_leader"] = leader.get("symbol")
                block[f"{rank_prefix}_leader_score"] = round(leader_score, 2)
                block[f"{rank_prefix}_relative_score"] = round(score - leader_score, 2)
                block[f"{rank_prefix}_percentile"] = round(percentile, 3)
                if rank_prefix == "peer" and idx > 1:
                    gap = leader_score - score
                    block["peer_pressure"] = {
                        "stronger_peer": leader.get("symbol"),
                        "stronger_peer_score": round(leader_score, 2),
                        "score_gap": round(gap, 2),
                        "requires_explicit_justification": gap >= peer_gap_threshold,
                    }
                elif rank_prefix == "peer":
                    block["peer_pressure"] = {
                        "stronger_peer": None,
                        "score_gap": 0.0,
                        "requires_explicit_justification": False,
                    }
                block[f"{rank_prefix}_comparison_summary"] = (
                    f"{block.get('symbol')} ranks {idx}/{size} in {group_value}; "
                    f"leader {leader.get('symbol')} scores {leader_score:.1f}."
                )

    _annotate_group("peer_group", lambda b: b.get("peer_group"), "peer")
    _annotate_group("sector", lambda b: b.get("sector"), "sector")
    _annotate_group("theme_bucket", lambda b: b.get("theme_bucket"), "theme")


def missed_breakout_candidates(
    candidate_pool: list[dict[str, Any]],
    selected_symbols: Iterable[str],
    per_symbol: dict[str, dict[str, Any]] | None,
    *,
    threshold: float = 72.0,
) -> list[dict[str, Any]]:
    """Return high-priority non-selected names for scan diagnostics."""
    selected = {str(s).upper() for s in selected_symbols or []}
    per_symbol = per_symbol or {}
    out: list[dict[str, Any]] = []
    for block in candidate_pool or []:
        sym = str(block.get("symbol") or "").upper()
        if not sym or sym in selected:
            continue
        score = _num(block.get("candidate_priority_score"), 0.0)
        profile = block.get("momentum_profile") or {}
        grade = str(profile.get("grade") or "")
        strong_live = grade == "strong_continuation"
        if score < threshold and not strong_live:
            continue
        info = per_symbol.get(sym) or {}
        out.append({
            "symbol": sym,
            "candidate_priority_score": round(score, 2),
            "momentum_grade": grade,
            "selector_action": info.get("action", "PASS"),
            "selector_reason": info.get("one_sentence_reason"),
            "discovery_sources": block.get("discovery_sources", []),
            "peer_group": block.get("peer_group"),
            "peer_rank": block.get("peer_rank"),
            "sector_rank": block.get("sector_rank"),
            "reason": "High-priority breakout/leader was not selected.",
        })
    out.sort(key=lambda r: r["candidate_priority_score"], reverse=True)
    return out


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out
