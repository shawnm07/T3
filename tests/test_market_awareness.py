"""Tests for the 2026-05-12 market-awareness overhaul.

Covers:
- sector_etfs: regime build, rotation score, leading/lagging, score adjustment
- intraday_tape.sector_tape_adjustment: per-sector floor
- dynamic_watchlist decay: half-life behavior
- discovery_meanrev: dip-buy eligibility + scoring
- tape_recovery: peak-then-fall detection
- tactical_hedge: open/close transitions
- defensive_lane: activation + injection
- open_of_day_audit: held-in-lagging flag
"""
import sys
import types
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml  # noqa: F401
except ModuleNotFoundError:
    sys.modules["yaml"] = types.SimpleNamespace(
        safe_load=lambda *a, **k: {},
        safe_dump=lambda *a, **k: "",
    )
try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda *a, **k: None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.defensive_lane import build_defensive_candidates, is_lane_active
from src.discovery_meanrev import discover_dipbuys
from src.dynamic_watchlist import _decayed_score
from src.intraday_tape import TapeSignal, sector_tape_adjustment
from src.open_of_day_audit import audit as ofd_audit
from src.sector_etfs import (
    SectorRegime,
    SectorSnapshot,
    _rotation_score,
    compute_sector_regime,
    held_position_in_lagging,
    sector_relative_score_adjustment,
)
from src.tactical_hedge import decide as hedge_decide
from src.tape_recovery import record_and_detect


@dataclass
class _Cfg:
    raw: dict

    def get(self, *keys, default=None):
        node = self.raw
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node


def _mk_snap(symbol, sector, intra, ret_5d=0.0, ret_1d=0.0):
    return SectorSnapshot(
        symbol=symbol, sector_name=sector,
        price=100.0, ret_1d=ret_1d, ret_5d=ret_5d, ret_20d=0.0,
        intraday_change_pct=intra, intraday_rs_vs_spy=intra,
    )


# ---------- sector_etfs ----------

def test_rotation_score_zero_when_ranks_match():
    same = ["A", "B", "C", "D"]
    assert _rotation_score(same, same) == 0.0


def test_rotation_score_nonzero_when_reversed():
    rs = _rotation_score(["A", "B", "C", "D"], ["D", "C", "B", "A"])
    assert rs > 0.5


def test_compute_sector_regime_flags_defensive_rotation():
    cfg = _Cfg({"sector_rotation": {"rotation_alert_score": 0.40}})
    snaps = [
        _mk_snap("XLV", "Health Care", +0.012, ret_5d=+0.030),
        _mk_snap("XLP", "Consumer Staples", +0.010, ret_5d=+0.025),
        _mk_snap("XLU", "Utilities", +0.008, ret_5d=+0.020),
        _mk_snap("XLF", "Financials", +0.002, ret_5d=+0.001),
        _mk_snap("XLI", "Industrials", -0.001, ret_5d=-0.005),
        _mk_snap("XLB", "Materials", -0.002, ret_5d=-0.006),
        _mk_snap("XLE", "Energy", -0.003, ret_5d=-0.007),
        _mk_snap("XLRE", "Real Estate", +0.001, ret_5d=-0.001),
        _mk_snap("XLK", "Information Technology", -0.018, ret_5d=+0.040),
        _mk_snap("XLY", "Consumer Discretionary", -0.015, ret_5d=+0.030),
        _mk_snap("XLC", "Communication Services", -0.012, ret_5d=+0.020),
    ]
    regime = compute_sector_regime(cfg, snaps)
    # XLV/XLP/XLU lead, XLK/XLY/XLC lag
    assert set(regime.leading) == {"XLV", "XLP", "XLU"}
    assert set(regime.lagging) == {"XLK", "XLY", "XLC"}
    assert regime.defensives_leading is True
    assert regime.cyclicals_lagging is True
    # Today's top reverses the 5d top → rotation
    assert regime.rotation_score > 0.30


def test_sector_relative_score_adjustment_penalizes_tech():
    cfg = _Cfg({"sector_rotation": {"sector_relative_score_pct_to_points": 50.0}})
    snap = _mk_snap("XLK", "Information Technology", -0.018)
    regime = SectorRegime(
        leading=[], lagging=["XLK"], rotation_score=0.6,
        rotation_regime="rotating", defensives_leading=True,
        cyclicals_lagging=True, snapshots=[snap],
    )
    adj, audit = sector_relative_score_adjustment(cfg, "Information Technology", regime)
    # -1.8% rs × 50 = -0.9 (clamped to -30..30, so -0.9)
    assert adj < 0
    assert audit["sector_etf"] == "XLK"


def test_held_position_in_lagging_flags_tech_holding():
    cfg = _Cfg({"sector_rotation": {
        "proactive_trim_rs_threshold": -0.005,
        "proactive_trim_pct": 0.25,
    }})
    snap = _mk_snap("XLK", "Information Technology", -0.020)
    regime = SectorRegime(
        leading=["XLV"], lagging=["XLK"], rotation_score=0.6,
        rotation_regime="rotating", defensives_leading=False,
        cyclicals_lagging=True, snapshots=[snap],
    )
    flagged = held_position_in_lagging(cfg, {"NVDA": "Information Technology", "UNH": "Health Care"}, regime)
    assert len(flagged) == 1
    assert flagged[0]["symbol"] == "NVDA"
    assert flagged[0]["proposed_trim_pct"] == 0.25


# ---------- intraday_tape.sector_tape_adjustment ----------

def test_per_sector_tape_floor():
    base = TapeSignal(
        spy_intraday_change_pct=-0.004, spy_vs_vwap_pct=0.0,
        spy_intraday_low_break_pct=0.0, tape_badness=0.15,
        min_opportunity_score_floor=68.0, severity_label="neutral",
        notes=[], has_data=True,
    )
    regime_dict = {
        "snapshots": [{
            "symbol": "XLK", "sector_name": "Information Technology",
            "intraday_rs_vs_spy": -0.018, "intraday_change_pct": -0.022,
            "price": 200.0, "ret_1d": 0.0, "ret_5d": 0.0, "ret_20d": 0.0,
        }],
    }
    floor, audit = sector_tape_adjustment(base, "Information Technology", regime_dict)
    assert floor > 68.0  # tech penalized
    assert audit["floor_adjustment_points"] > 0


def test_per_sector_tape_floor_no_data_passthrough():
    base = TapeSignal(0.0, 0.0, 0.0, 0.0, 65.0, "favorable", [], True)
    floor, audit = sector_tape_adjustment(base, None, None)
    assert floor == 65.0


# ---------- dynamic_watchlist decay ----------

def test_dynamic_watchlist_decay_halflife():
    cfg = _Cfg({"dynamic_watchlist_decay": {"enabled": True, "half_life_days": 3.0}})
    # 65 raw points, 3 days old → ~32.5
    decayed = _decayed_score(65.0, age_days=3.0, cfg=cfg)
    assert abs(decayed - 32.5) < 0.5
    # 6 days → ~16.25
    decayed_6 = _decayed_score(65.0, age_days=6.0, cfg=cfg)
    assert abs(decayed_6 - 16.25) < 0.5


def test_dynamic_watchlist_decay_disabled():
    cfg = _Cfg({"dynamic_watchlist_decay": {"enabled": False}})
    assert _decayed_score(65.0, age_days=10.0, cfg=cfg) == 65.0


# ---------- discovery_meanrev ----------

def test_meanrev_filters_high_quality_oversold():
    cfg = _Cfg({"mean_reversion_lane": {
        "enabled": True,
        "min_market_cap_usd": 20e9,
        "require_sp500": False,
        "min_intraday_drop_pct": 0.03,
        "min_drop_vs_5d_high_pct": 0.05,
        "max_rsi": 35,
        "require_higher_low_30m": True,
        "min_intraday_rs_vs_sector": 0.0,
        "max_candidates": 3,
    }})
    raw = [
        # Passes
        {"symbol": "NVDA", "market_cap": 1e12, "intraday_change_pct": -0.04,
         "drop_vs_5d_high_pct": -0.06, "rsi_14": 28, "higher_low_30m": True,
         "intraday_rs_vs_sector_pct": 0.005},
        # Fails: not oversold enough
        {"symbol": "AAPL", "market_cap": 3e12, "intraday_change_pct": -0.01,
         "drop_vs_5d_high_pct": -0.02, "rsi_14": 50, "higher_low_30m": True,
         "intraday_rs_vs_sector_pct": 0.0},
        # Fails: no higher low pattern
        {"symbol": "META", "market_cap": 1e12, "intraday_change_pct": -0.05,
         "drop_vs_5d_high_pct": -0.07, "rsi_14": 25, "higher_low_30m": False,
         "intraday_rs_vs_sector_pct": 0.005},
    ]
    out = discover_dipbuys(cfg, raw)
    syms = [c["symbol"] for c in out]
    assert syms == ["NVDA"]


# ---------- tape_recovery ----------

def test_tape_recovery_detects_peak_then_fall(tmp_path):
    cfg = _Cfg({"tape_recovery": {
        "enabled": True,
        "consecutive_falling_bars": 2,
        "opportunity_score_boost": 5,
        "state_file": str(tmp_path / "tr.json"),
    }})
    # Climb to a peak then fall: 0.05, 0.20, 0.45, 0.30, 0.15
    record_and_detect(cfg, 0.05, now=1000)
    record_and_detect(cfg, 0.20, now=2000)
    record_and_detect(cfg, 0.45, now=3000)
    record_and_detect(cfg, 0.30, now=4000)
    state = record_and_detect(cfg, 0.15, now=5000)
    assert state["recovering"] is True
    assert state["opportunity_score_boost"] == 5


def test_tape_recovery_no_signal_on_flat(tmp_path):
    cfg = _Cfg({"tape_recovery": {
        "enabled": True,
        "consecutive_falling_bars": 2,
        "opportunity_score_boost": 5,
        "state_file": str(tmp_path / "tr2.json"),
    }})
    for i, b in enumerate([0.10, 0.12, 0.11, 0.13, 0.12]):
        s = record_and_detect(cfg, b, now=1000 + i * 1000)
    # No clear peak ≥ 0.20 — not recovering.
    assert s["recovering"] is False


# ---------- tactical_hedge ----------

def test_tactical_hedge_opens_on_risk_off_with_lagging_top_theme(tmp_path):
    cfg = _Cfg({"tactical_hedge": {
        "enabled": True, "symbol": "SH", "max_pct": 0.05,
        "open_macro_score_threshold": -0.20,
        "close_macro_score_threshold": 0.0,
        "shadow_mode": True,
        "state_file": str(tmp_path / "th.json"),
    }})
    sr = {
        "lagging": ["XLK"],
        "snapshots": [{"symbol": "XLK", "sector_name": "Information Technology"}],
    }
    audit = hedge_decide(
        cfg, macro_score=-0.30, sector_regime=sr,
        held_themes={"Information Technology"}, equity=100000,
    )
    assert audit["action"] == "open"
    assert audit["proposed_notional"] == 5000.0


def test_tactical_hedge_closes_on_recovery(tmp_path):
    cfg = _Cfg({"tactical_hedge": {
        "enabled": True, "symbol": "SH", "max_pct": 0.05,
        "open_macro_score_threshold": -0.20,
        "close_macro_score_threshold": 0.0,
        "shadow_mode": True,
        "state_file": str(tmp_path / "th2.json"),
    }})
    sr = {"lagging": ["XLK"],
          "snapshots": [{"symbol": "XLK", "sector_name": "Information Technology"}]}
    hedge_decide(cfg, macro_score=-0.30, sector_regime=sr,
                 held_themes={"Information Technology"}, equity=100000)
    audit2 = hedge_decide(cfg, macro_score=0.10, sector_regime=sr,
                          held_themes={"Information Technology"}, equity=100000)
    assert audit2["action"] == "close"


# ---------- defensive_lane ----------

def test_defensive_lane_activation():
    cfg = _Cfg({
        "defensive_lane": {
            "enabled": True,
            "etfs": ["XLV", "XLP", "XLU"],
            "require_min_evaluated": 2,
            "max_total_pct": 0.30,
        },
        "sector_rotation": {"rotation_alert_score": 0.40},
    })
    inactive = {"defensives_leading": False, "rotation_score": 0.60}
    assert is_lane_active(cfg, inactive) is False
    active = {"defensives_leading": True, "rotation_score": 0.60, "snapshots": []}
    assert is_lane_active(cfg, active) is True
    cands = build_defensive_candidates(cfg, active)
    assert len(cands) == 3
    assert {c["symbol"] for c in cands} == {"XLV", "XLP", "XLU"}


# ---------- open_of_day_audit ----------

def test_open_of_day_audit_flags_held_in_lagging():
    cfg = _Cfg({
        "open_of_day_audit": {"enabled": True, "trim_pct": 0.25},
        "sector_rotation": {
            "proactive_trim_rs_threshold": -0.005,
            "proactive_trim_pct": 0.25,
        },
    })
    sr_dict = {
        "leading": ["XLV"], "lagging": ["XLK"],
        "rotation_score": 0.6, "rotation_regime": "rotating",
        "defensives_leading": True, "cyclicals_lagging": True,
        "snapshots": [
            {"symbol": "XLK", "sector_name": "Information Technology",
             "intraday_rs_vs_spy": -0.020,
             "intraday_change_pct": -0.02, "price": 200, "ret_1d": 0, "ret_5d": 0, "ret_20d": 0},
        ],
    }
    out = ofd_audit(cfg, "FIRST", {"NVDA": "Information Technology"}, sr_dict)
    assert out["status"] == "ok"
    assert out["flagged_count"] == 1
    assert out["flagged"][0]["symbol"] == "NVDA"


def test_open_of_day_audit_skips_non_first_scan():
    cfg = _Cfg({"open_of_day_audit": {"enabled": True}})
    out = ofd_audit(cfg, "MIDDAY", {}, None)
    assert out["status"] == "skipped_not_first_scan"
