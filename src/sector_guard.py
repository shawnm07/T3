"""Portfolio-level diversification veto.

The unified portfolio-selector is asked to respect sector and theme caps in its
prompt, but the executor still validates the final allocation independently.
If the AI returns a plan that violates the caps, this module either rejects it
(triggering a one-shot retry with violations injected back into the prompt) or
force-corrects it by EXIT-ing the lowest-opportunity-score offenders.

A "theme" is a broader correlation bucket than GICS sector — e.g. semis +
data-center HVAC + power equipment all live in the ``ai_data_center`` theme,
even though they span Information Technology and Industrials in GICS terms.
That correlation is exactly what crushed the book on 2026-04-28.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Iterable

from src.config import Config

log = logging.getLogger(__name__)

@dataclass
class Violation:
    kind: str                 # "gics_sector" | "theme_count" | "theme_weight"
    bucket: str
    members: list[str]
    weight: float
    limit: float | int

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "bucket": self.bucket,
            "members": list(self.members),
            "weight": round(float(self.weight), 4),
            "limit": self.limit,
        }


@dataclass
class GuardResult:
    ok: bool
    violations: list[Violation] = field(default_factory=list)
    forced_exits: list[str] = field(default_factory=list)
    audit: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "violations": [v.to_dict() for v in self.violations],
            "forced_exits": list(self.forced_exits),
            "audit": self.audit,
        }


def _build_sector_to_theme(cfg: Config) -> dict[str, str]:
    """Invert the cfg ``diversification.themes`` map for O(1) sector->theme lookup."""
    themes = cfg.get("diversification", "themes", default={}) or {}
    out: dict[str, str] = {}
    for theme_name, sectors in themes.items():
        for sec in (sectors or []):
            out[str(sec).strip().lower()] = str(theme_name)
    return out


def _symbol_overrides(cfg: Config) -> dict[str, str]:
    raw = cfg.get("diversification", "symbol_overrides", default={}) or {}
    return {str(k).upper().strip(): str(v) for k, v in raw.items()}


def theme_bucket_for(
    sector: str,
    sector_to_theme: dict[str, str],
    symbol: str | None = None,
    symbol_overrides: dict[str, str] | None = None,
) -> str:
    """Map a (symbol, GICS sector) to a theme bucket.

    Symbol-level overrides win over the sector map. Falls back to ``"other"``
    only when neither matches.
    """
    if symbol and symbol_overrides:
        sym = symbol.upper().strip()
        if sym in symbol_overrides:
            return symbol_overrides[sym]
    if not sector:
        return "other"
    key = sector.strip().lower()
    if key in sector_to_theme:
        return sector_to_theme[key]
    # Loose substring match — sector strings from AV / sp500 sometimes carry
    # qualifiers like "Semiconductors & Semiconductor Equipment" vs the looser
    # "Semiconductors" bucket entry.
    for known, theme in sector_to_theme.items():
        if known and known in key:
            return theme
    return "other"


def validate(
    target_weights: dict[str, float],
    per_symbol: dict[str, dict[str, Any]],
    pool_meta: dict[str, dict[str, Any]],
    cfg: Config,
    cash_proxy_symbol: str | None = None,
) -> GuardResult:
    """Validate an allocation plan against the diversification caps.

    Selected = symbols with ``target_pct > 0`` AND ``target_weights[sym] > 0``.
    SPY / cash_proxy is excluded from the count and weight checks.
    """
    max_per_sector = int(cfg.get("diversification", "max_per_gics_sector", default=3) or 3)
    max_per_theme = int(cfg.get("diversification", "max_per_theme", default=3) or 3)
    max_theme_weight = float(cfg.get("diversification", "max_theme_weight_pct", default=0.50) or 0.50)
    sector_to_theme = _build_sector_to_theme(cfg)
    symbol_overrides = _symbol_overrides(cfg)

    proxy = (cash_proxy_symbol or "").upper()

    selected: list[tuple[str, float, str, str, bool]] = []
    for sym, weight in target_weights.items():
        sym_u = sym.upper()
        if sym_u == proxy:
            continue
        try:
            w = float(weight or 0)
        except (TypeError, ValueError):
            w = 0.0
        if w <= 0:
            continue
        meta = pool_meta.get(sym) or pool_meta.get(sym_u) or {}
        sector = str(meta.get("sector") or "Other")
        theme = theme_bucket_for(sector, sector_to_theme, sym_u, symbol_overrides)
        selected.append((sym_u, w, sector, theme, bool(meta.get("currently_held"))))

    sector_groups: dict[str, list[tuple[str, float]]] = {}
    theme_groups: dict[str, list[tuple[str, float]]] = {}
    audit_sector_groups: dict[str, dict[str, Any]] = {}
    audit_theme_groups: dict[str, dict[str, Any]] = {}
    for sym, w, sector, theme, currently_held in selected:
        sector_groups.setdefault(sector, []).append((sym, w))
        theme_groups.setdefault(theme, []).append((sym, w))
        sector_row = audit_sector_groups.setdefault(
            sector,
            {
                "limit": max_per_sector,
                "members": [],
                "live_holdings": [],
                "accepted_same_scan_candidates": [],
                "weight": 0.0,
            },
        )
        theme_row = audit_theme_groups.setdefault(
            theme,
            {
                "count_limit": max_per_theme,
                "weight_limit": max_theme_weight,
                "members": [],
                "live_holdings": [],
                "accepted_same_scan_candidates": [],
                "weight": 0.0,
            },
        )
        target_bucket = "live_holdings" if currently_held else "accepted_same_scan_candidates"
        for row in (sector_row, theme_row):
            row["members"].append(sym)
            row[target_bucket].append(sym)
            row["weight"] = round(float(row.get("weight", 0.0) or 0.0) + w, 4)

    violations: list[Violation] = []
    for sector, members in sector_groups.items():
        if len(members) > max_per_sector:
            violations.append(Violation(
                kind="gics_sector",
                bucket=sector,
                members=[s for s, _ in members],
                weight=sum(w for _, w in members),
                limit=max_per_sector,
            ))
    for theme, members in theme_groups.items():
        if len(members) > max_per_theme:
            violations.append(Violation(
                kind="theme_count",
                bucket=theme,
                members=[s for s, _ in members],
                weight=sum(w for _, w in members),
                limit=max_per_theme,
            ))
        total_w = sum(w for _, w in members)
        if total_w > max_theme_weight + 1e-6:
            violations.append(Violation(
                kind="theme_weight",
                bucket=theme,
                members=[s for s, _ in members],
                weight=total_w,
                limit=max_theme_weight,
            ))

    if violations:
        log.warning(
            "[sector_guard] %d violation(s): %s",
            len(violations),
            [(v.kind, v.bucket, len(v.members)) for v in violations],
        )
    audit = {
        "rule": "live holdings plus accepted same-scan candidates count; rejected/unfilled symbols do not",
        "max_per_gics_sector": max_per_sector,
        "max_per_theme": max_per_theme,
        "max_theme_weight_pct": max_theme_weight,
        "sectors": audit_sector_groups,
        "themes": audit_theme_groups,
    }
    return GuardResult(ok=not violations, violations=violations, audit=audit)


def force_compliance(
    target_weights: dict[str, float],
    per_symbol: dict[str, dict[str, Any]],
    violations: Iterable[Violation],
    cash_proxy_symbol: str | None,
) -> list[str]:
    """Mutate ``target_weights`` and ``per_symbol`` in place to satisfy caps.

    Strategy: for each violation, sort the bucket's members by
    ``opportunity_score`` ascending and EXIT enough of them to fall under the
    cap. Reclaimed weight goes to the cash proxy if provided, otherwise cash
    (left implicit — sum of weights drops below 1.0).

    Returns the list of symbols that were force-exited.
    """
    forced: list[str] = []
    proxy = (cash_proxy_symbol or "").upper() or None

    def _opp(sym: str) -> float:
        try:
            return float((per_symbol.get(sym) or {}).get("opportunity_score", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    def _sync_scaled_qty(sym: str, ratio: float) -> None:
        info = per_symbol.get(sym)
        if not isinstance(info, dict):
            return
        try:
            old_qty = float(info.get("qty", info.get("target_qty", 0)) or 0)
            old_delta = float(info.get("delta_qty", 0) or 0)
        except (TypeError, ValueError):
            return
        current_qty = old_qty - old_delta
        new_qty = round(max(0.0, old_qty * max(0.0, ratio)), 6)
        info["qty"] = new_qty
        info["target_qty"] = new_qty
        info["delta_qty"] = round(new_qty - current_qty, 6)

    def _current_qty(sym: str) -> float:
        info = per_symbol.get(sym)
        if not isinstance(info, dict):
            return 0.0
        try:
            old_qty = float(info.get("qty", info.get("target_qty", 0)) or 0)
            old_delta = float(info.get("delta_qty", 0) or 0)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, old_qty - old_delta)

    def _sync_exit_qty(sym: str) -> None:
        info = per_symbol.get(sym)
        if not isinstance(info, dict):
            return
        current_qty = _current_qty(sym)
        info["qty"] = 0
        info["target_qty"] = 0
        info["delta_qty"] = round(-current_qty, 6) if current_qty > 0 else 0

    # Process count violations FIRST so weight violations see the post-exit
    # state and don't overwrite EXIT decisions with REDUCE.
    ordered_violations = sorted(
        violations, key=lambda v: 0 if v.kind in ("gics_sector", "theme_count") else 1
    )

    for v in ordered_violations:
        if v.kind == "theme_weight":
            # Re-read current weights — earlier count-violation passes may have
            # already exited offenders. Only consider members that still carry
            # a non-zero weight, and only scale DOWN.
            live = [(s, float(target_weights.get(s, 0) or 0)) for s in v.members]
            live = [(s, w) for s, w in live if w > 0]
            current = sum(w for _, w in live)
            if current <= float(v.limit) + 1e-6:
                continue
            scale = float(v.limit) / current
            scaled_units: dict[str, int] = {
                sym: max(0, int(round(old * scale * 10000)))
                for sym, old in live
            }
            # Keep the rounded 4-decimal weights at or below the hard cap.
            # Otherwise 0.50004 can round back to 0.5001 and re-trip validate().
            limit_units = int(math.floor(float(v.limit) * 10000 + 1e-9))
            excess_units = sum(scaled_units.values()) - limit_units
            if excess_units > 0:
                for sym, _old in sorted(live, key=lambda row: _opp(row[0])):
                    if excess_units <= 0:
                        break
                    reduction = min(excess_units, scaled_units.get(sym, 0))
                    scaled_units[sym] = scaled_units.get(sym, 0) - reduction
                    excess_units -= reduction
            recovered = 0.0
            for sym, old in live:
                new = round(scaled_units.get(sym, 0) / 10000, 4)
                target_weights[sym] = new
                if sym in per_symbol:
                    per_symbol[sym]["target_pct"] = new
                    _sync_scaled_qty(sym, new / old if old > 0 else 0.0)
                    # Don't clobber EXIT/PASS. For live names, label the
                    # post-guard action by the remaining quantity direction.
                    if per_symbol[sym].get("action") not in ("EXIT", "PASS"):
                        try:
                            new_qty = float(per_symbol[sym].get("qty") or 0)
                        except (TypeError, ValueError):
                            new_qty = 0.0
                        current_qty = _current_qty(sym)
                        if current_qty <= 1e-9 and new_qty > 0:
                            per_symbol[sym]["action"] = "BUY"
                        elif new_qty < current_qty - 1e-9:
                            per_symbol[sym]["action"] = "REDUCE"
                        elif new_qty > current_qty + 1e-9:
                            per_symbol[sym]["action"] = "INCREASE"
                        else:
                            per_symbol[sym]["action"] = "HOLD"
                recovered += old - new
            if proxy and recovered > 0:
                target_weights[proxy] = round(
                    float(target_weights.get(proxy, 0) or 0) + recovered, 4
                )
            continue

        # gics_sector and theme_count: exit lowest-opportunity-score names
        # whose weight is still > 0 until the member count is within the cap.
        live_members = [s for s in v.members if float(target_weights.get(s, 0) or 0) > 0]
        excess = len(live_members) - int(v.limit)
        if excess <= 0:
            continue
        ordered = sorted(live_members, key=_opp)
        for sym in ordered[:excess]:
            old = float(target_weights.get(sym, 0) or 0)
            current_qty = _current_qty(sym)
            # Also treat positions flagged as HOLD/INCREASE/REDUCE as currently
            # held even when qty bookkeeping isn't populated (e.g. in tests or
            # when the selector omits qty fields).
            held_action = (per_symbol.get(sym) or {}).get("action") in (
                "HOLD", "INCREASE", "REDUCE"
            )
            is_held = current_qty > 1e-9 or held_action
            target_weights[sym] = 0.0
            if sym in per_symbol:
                per_symbol[sym]["target_pct"] = 0.0
                _sync_exit_qty(sym)
                if is_held:
                    per_symbol[sym]["action"] = "EXIT"
                    per_symbol[sym]["one_sentence_reason"] = (
                        f"Sector-guard forced exit: {v.kind}={v.bucket} exceeded "
                        f"cap of {v.limit}."
                    )
                else:
                    per_symbol[sym]["action"] = "PASS"
                    per_symbol[sym]["reason_code"] = "sector_capped"
                    per_symbol[sym]["one_sentence_reason"] = (
                        f"Sector-guard removed target: {v.kind}={v.bucket} exceeded "
                        f"cap of {v.limit}."
                    )
            forced.append(sym)
            if proxy and old > 0:
                target_weights[proxy] = round(
                    float(target_weights.get(proxy, 0) or 0) + old, 4
                )

    if forced:
        log.warning("[sector_guard] forced removals/exits: %s", forced)
    return forced
