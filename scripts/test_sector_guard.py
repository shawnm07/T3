"""Smoke test for src/sector_guard.py — runnable directly:

    python scripts/test_sector_guard.py

No pytest dependency. Exits non-zero if any assertion fails.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `src` importable when run from the repo root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import sector_guard  # noqa: E402


class FakeCfg:
    """Minimal Config stand-in supporting cfg.get(*path, default=...)."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def get(self, *path, default=None):
        cur = self._data
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return default
            cur = cur[p]
        return cur


CFG = FakeCfg({
    "diversification": {
        "max_per_gics_sector": 3,
        "max_per_theme": 3,
        "max_theme_weight_pct": 0.50,
        "themes": {
            "ai_data_center": [
                "Semiconductors",
                "Semiconductors & Semiconductor Equipment",
                "Technology Hardware, Storage & Peripherals",
                "Electrical Components & Equipment",
                "Building Products",
                "Heavy Electrical Equipment",
            ],
            "healthcare": ["Pharmaceuticals", "Biotechnology"],
            "financials": ["Banks", "Capital Markets"],
        },
    },
})


def case_six_semis_rejected():
    """Today's actual book: six AI/semis names — must be rejected."""
    weights = {"MU": 0.28, "DELL": 0.18, "FIX": 0.13, "VRT": 0.14, "AVGO": 0.07, "AMD": 0.05}
    per_sym = {
        "MU":   {"target_pct": 0.28, "opportunity_score": 65},
        "DELL": {"target_pct": 0.18, "opportunity_score": 60},
        "FIX":  {"target_pct": 0.13, "opportunity_score": 50},
        "VRT":  {"target_pct": 0.14, "opportunity_score": 55},
        "AVGO": {"target_pct": 0.07, "opportunity_score": 70},
        "AMD":  {"target_pct": 0.05, "opportunity_score": 45},
    }
    pool_meta = {
        "MU":   {"sector": "Semiconductors"},
        "DELL": {"sector": "Technology Hardware, Storage & Peripherals"},
        "AVGO": {"sector": "Semiconductors"},
        "AMD":  {"sector": "Semiconductors"},
        "VRT":  {"sector": "Electrical Components & Equipment"},
        "FIX":  {"sector": "Building Products"},
    }
    res = sector_guard.validate(weights, per_sym, pool_meta, CFG, cash_proxy_symbol="SPY")
    assert not res.ok, "six-semi book should fail"
    kinds = {v.kind for v in res.violations}
    assert "theme_count" in kinds, f"expected theme_count violation, got {kinds}"
    assert "theme_weight" in kinds, f"expected theme_weight violation, got {kinds}"
    print("[PASS] six-semi book correctly rejected:",
          [(v.kind, v.bucket, len(v.members)) for v in res.violations])


def case_diversified_passes():
    weights = {"MU": 0.20, "AMD": 0.15, "LLY": 0.15, "JPM": 0.15, "AVGO": 0.10, "SPY": 0.20}
    per_sym = {s: {"target_pct": w, "opportunity_score": 70} for s, w in weights.items()}
    pool_meta = {
        "MU":   {"sector": "Semiconductors"},
        "AMD":  {"sector": "Semiconductors"},
        "AVGO": {"sector": "Semiconductors"},
        "LLY":  {"sector": "Pharmaceuticals"},
        "JPM":  {"sector": "Banks"},
        "SPY":  {"sector": "Other"},
    }
    res = sector_guard.validate(weights, per_sym, pool_meta, CFG, cash_proxy_symbol="SPY")
    assert res.ok, f"diversified book should pass, got {res.violations}"
    print("[PASS] diversified book accepted")


def case_force_compliance_exits_lowest():
    weights = {"MU": 0.20, "AMD": 0.15, "AVGO": 0.10, "DELL": 0.10}
    per_sym = {
        "MU":   {"target_pct": 0.20, "opportunity_score": 80, "action": "INCREASE"},
        "AMD":  {"target_pct": 0.15, "opportunity_score": 30, "action": "HOLD"},
        "AVGO": {"target_pct": 0.10, "opportunity_score": 70, "action": "HOLD"},
        "DELL": {"target_pct": 0.10, "opportunity_score": 40, "action": "HOLD"},
    }
    pool_meta = {
        "MU":   {"sector": "Semiconductors"},
        "AMD":  {"sector": "Semiconductors"},
        "AVGO": {"sector": "Semiconductors"},
        "DELL": {"sector": "Technology Hardware, Storage & Peripherals"},
    }
    res = sector_guard.validate(weights, per_sym, pool_meta, CFG, cash_proxy_symbol="SPY")
    assert not res.ok
    forced = sector_guard.force_compliance(weights, per_sym, res.violations, "SPY")
    res2 = sector_guard.validate(weights, per_sym, pool_meta, CFG, cash_proxy_symbol="SPY")
    assert res2.ok, f"after force_compliance should pass, got {res2.violations}"
    assert "AMD" in forced, f"AMD (lowest score) should be exited, forced={forced}"
    assert per_sym["AMD"]["action"] == "EXIT"
    assert weights["AMD"] == 0.0
    print("[PASS] force_compliance exited lowest-score offender:", forced)


def case_theme_weight_trims():
    """Three semis at 60% combined — count is fine but theme weight cap (50%) trips."""
    weights = {"MU": 0.25, "AMD": 0.20, "AVGO": 0.15, "LLY": 0.10, "JPM": 0.05}
    per_sym = {s: {"target_pct": w, "opportunity_score": 60} for s, w in weights.items()}
    pool_meta = {
        "MU":   {"sector": "Semiconductors"},
        "AMD":  {"sector": "Semiconductors"},
        "AVGO": {"sector": "Semiconductors"},
        "LLY":  {"sector": "Pharmaceuticals"},
        "JPM":  {"sector": "Banks"},
    }
    res = sector_guard.validate(weights, per_sym, pool_meta, CFG, cash_proxy_symbol="SPY")
    assert any(v.kind == "theme_weight" for v in res.violations), "expected theme_weight breach"
    sector_guard.force_compliance(weights, per_sym, res.violations, "SPY")
    res2 = sector_guard.validate(weights, per_sym, pool_meta, CFG, cash_proxy_symbol="SPY")
    assert res2.ok, f"trim should bring theme weight under cap, got {res2.violations}"
    print("[PASS] theme weight trimmed to cap; SPY caught the residual")


def main():
    cases = [
        case_six_semis_rejected,
        case_diversified_passes,
        case_force_compliance_exits_lowest,
        case_theme_weight_trims,
    ]
    failed = 0
    for c in cases:
        try:
            c()
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {c.__name__}: {e}")
    if failed:
        print(f"\n{failed}/{len(cases)} test(s) failed")
        sys.exit(1)
    print(f"\nAll {len(cases)} tests passed")


if __name__ == "__main__":
    main()
