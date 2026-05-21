"""Tests for the 2026-05-11 EOD overhaul modules.

Covers:
- hold_time_guard: blocks low-conf, allows high-conf, exempts stops
- theme_cooldown: blocks same-theme replacement, allows on higher score
- daily_fill_cap: caps at N, stops excluded
- spy_ballast: reroutes overflow to BIL
- discovery_smallcap: applies lower mcap floor + scoring gates
- carry_forward: persists unpicked, decrements TTL
- av_budget: rolling-window throttling
- scanning_failure_alert: streak detection
- postmortem: writes records + computes accuracy
"""
import sys
import types
from dataclasses import dataclass
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

import time

from src.av_budget import record_request, remaining_pct, should_defer_non_critical
from src.carry_forward import (
    get_carry_forward_symbols,
    record_unpicked,
)
from src.daily_fill_cap import _state_path as _fc_state, fills_today, is_capped, record_fill
from src.discovery_smallcap import filter_universe, score_and_select
from src.hold_time_guard import should_block_discretionary_exit
from src.postmortem import _journal_path, exit_arbiter_accuracy, record_postmortem
from src.scanning_failure_alert import _state_path as _sf_state, record_scan_outcome
from src.spy_ballast import force_deploy_failure, split_idle_ballast
from src.theme_cooldown import _state_path as _tc_state, is_blocked, record_exit


# ---- minimal Config stub (avoids loading real config.yaml / env) ----
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


def _isolated_state(tmp_path, key, sub):
    """Return a config that points the module's state file under tmp_path."""
    base = {key: {sub: str(tmp_path / f"{key}.json")}}
    return base


# ---------- hold_time_guard ----------

def test_hold_time_guard_blocks_low_conf_within_window():
    cfg = _Cfg({"risk": {"min_hold_minutes": 390, "min_hold_override_confidence": 0.80}})
    blocked, audit = should_block_discretionary_exit(
        cfg, entry_time=time.time() - 60 * 60, confidence=0.60, is_stop_loss=False,
    )
    assert blocked is True
    assert audit["reason"] == "min_hold_active"


def test_hold_time_guard_allows_high_conf_override():
    cfg = _Cfg({"risk": {"min_hold_minutes": 390, "min_hold_override_confidence": 0.80}})
    blocked, audit = should_block_discretionary_exit(
        cfg, entry_time=time.time() - 60 * 60, confidence=0.85, is_stop_loss=False,
    )
    assert blocked is False
    assert audit["reason"] == "high_confidence_override"


def test_hold_time_guard_exempts_stop_loss():
    cfg = _Cfg({"risk": {"min_hold_minutes": 390, "min_hold_override_confidence": 0.80}})
    blocked, _ = should_block_discretionary_exit(
        cfg, entry_time=time.time() - 60, confidence=0.10, is_stop_loss=True,
    )
    assert blocked is False


def test_hold_time_guard_allows_after_window():
    cfg = _Cfg({"risk": {"min_hold_minutes": 10, "min_hold_override_confidence": 0.80}})
    blocked, _ = should_block_discretionary_exit(
        cfg, entry_time=time.time() - 60 * 60, confidence=0.60, is_stop_loss=False,
    )
    assert blocked is False


# ---------- theme_cooldown ----------

def test_theme_cooldown_blocks_replacement(tmp_path):
    state = str(tmp_path / "tc.json")
    cfg = _Cfg({
        "diversification": {
            "theme_cooldown_minutes": 2880,
            "theme_cooldown_score_delta": 20.0,
            "theme_cooldown_state_file": state,
            "themes": {"technology": ["Information Technology"]},
            "symbol_overrides": {"AMD": "ai_data_center", "MU": "ai_data_center"},
        }
    })
    record_exit(cfg, "AMD", sector="Information Technology", exit_score=75.0)
    blocked, audit = is_blocked(cfg, "MU", sector="Information Technology", candidate_score=80.0)
    assert blocked is True
    assert audit["theme"] == "ai_data_center"


def test_theme_cooldown_allows_higher_score(tmp_path):
    state = str(tmp_path / "tc.json")
    cfg = _Cfg({
        "diversification": {
            "theme_cooldown_minutes": 2880,
            "theme_cooldown_score_delta": 20.0,
            "theme_cooldown_state_file": state,
            "themes": {},
            "symbol_overrides": {"AMD": "ai_data_center", "MU": "ai_data_center"},
        }
    })
    record_exit(cfg, "AMD", sector="Information Technology", exit_score=75.0)
    blocked, audit = is_blocked(cfg, "MU", sector="Information Technology", candidate_score=96.0)
    assert blocked is False
    assert audit["reason"] == "cooldown_overridden_by_higher_score"


# ---------- daily_fill_cap ----------

def test_daily_fill_cap_blocks_after_n_fills(tmp_path, monkeypatch):
    monkeypatch.setattr("src.daily_fill_cap._STATE_FILE", str(tmp_path / "dfc.json"))
    # Re-monkey: _state_path uses module-level _STATE_FILE; the function resolves
    # the path lazily so the monkeypatch takes effect.
    cfg = _Cfg({"risk": {"max_daily_fills": 3}})
    record_fill("AAA")
    record_fill("BBB")
    capped, _ = is_capped(cfg)
    assert capped is False
    record_fill("CCC")
    capped, audit = is_capped(cfg)
    assert capped is True
    assert audit["fills_today"] == 3


def test_daily_fill_cap_excludes_stops(tmp_path, monkeypatch):
    monkeypatch.setattr("src.daily_fill_cap._STATE_FILE", str(tmp_path / "dfc2.json"))
    cfg = _Cfg({"risk": {"max_daily_fills": 2}})
    record_fill("AAA", is_stop_loss=True)
    record_fill("BBB", is_stop_loss=True)
    record_fill("CCC", is_stop_loss=True)
    assert fills_today() == 0
    capped, _ = is_capped(cfg)
    assert capped is False


# ---------- spy_ballast ----------

def test_split_idle_ballast_routes_overflow_to_bil():
    cfg = _Cfg({"risk": {"max_spy_pct": 0.30, "cash_proxy_idle_symbol": "BIL"}})
    targets = split_idle_ballast(cfg, proposed_spy_pct=0.78)
    assert targets.spy_target_pct == 0.30
    assert abs(targets.bil_target_pct - 0.48) < 1e-9
    assert abs(targets.rerouted_pct - 0.48) < 1e-9


def test_split_idle_ballast_under_cap_unchanged():
    cfg = _Cfg({"risk": {"max_spy_pct": 0.30, "cash_proxy_idle_symbol": "BIL"}})
    targets = split_idle_ballast(cfg, proposed_spy_pct=0.20)
    assert targets.spy_target_pct == 0.20
    assert targets.bil_target_pct == 0.0


def test_force_deploy_failure_fires_on_idle_riskon():
    cfg = _Cfg({})
    audit = force_deploy_failure(cfg, macro_score=0.50, cash_pct=0.40, selected_count=1)
    assert audit is not None
    assert audit["kind"] == "force_deploy_failure"


def test_force_deploy_failure_skips_when_deployed():
    cfg = _Cfg({})
    audit = force_deploy_failure(cfg, macro_score=0.50, cash_pct=0.40, selected_count=5)
    assert audit is None


# ---------- discovery_smallcap ----------

def test_smallcap_lane_filters_universe():
    cfg = _Cfg({"discovery": {"smallcap_lane": {
        "enabled": True,
        "min_market_cap_usd": 300_000_000,
        "min_price": 3.0,
        "min_dollar_volume_usd": 25_000_000,
        "min_technical_score": 0.50,
        "min_sentiment_score": 0.30,
        "max_candidates": 10,
    }}})
    raw = [
        # Passes: $500M mcap, $17 price, $130M $vol
        {"symbol": "AKAN", "market_cap": 500_000_000, "price": 17.0,
         "avg_dollar_volume_20d": 130_000_000, "pct_change": 44.5},
        # Fails: too small mcap
        {"symbol": "PENNY", "market_cap": 50_000_000, "price": 0.50,
         "avg_dollar_volume_20d": 1_000_000, "pct_change": 100.0},
        # Fails: too thin
        {"symbol": "THIN", "market_cap": 500_000_000, "price": 10.0,
         "avg_dollar_volume_20d": 5_000_000, "pct_change": 10.0},
    ]
    out = filter_universe(cfg, raw)
    assert [c.symbol for c in out] == ["AKAN"]


def test_smallcap_lane_scoring_gates():
    cfg = _Cfg({"discovery": {"smallcap_lane": {
        "enabled": True,
        "min_market_cap_usd": 300_000_000,
        "min_price": 3.0,
        "min_dollar_volume_usd": 25_000_000,
        "min_technical_score": 0.50,
        "min_sentiment_score": 0.30,
        "max_candidates": 10,
    }}})
    raw = [{"symbol": "AKAN", "market_cap": 500_000_000, "price": 17.0,
            "avg_dollar_volume_20d": 130_000_000, "pct_change": 44.5}]
    cands = filter_universe(cfg, raw)
    # Strong tech + good sentiment → pass
    sel = score_and_select(cfg, cands,
                           technical_scores={"AKAN": 0.65},
                           sentiment_scores={"AKAN": 0.40})
    assert len(sel) == 1
    # Weak tech → drop
    sel2 = score_and_select(cfg, cands,
                            technical_scores={"AKAN": 0.30},
                            sentiment_scores={"AKAN": 0.40})
    assert sel2 == []


# ---------- carry_forward ----------

def test_carry_forward_persists_unpicked(tmp_path):
    state = str(tmp_path / "cf.json")
    cfg = _Cfg({"discovery": {
        "carry_forward_enabled": True,
        "carry_forward_min_score": 0.30,
        "carry_forward_ttl_scans": 3,
        "carry_forward_state_file": state,
    }})
    record_unpicked(cfg, [("AAA", 0.45), ("BBB", 0.20), ("CCC", 0.55)], selected={"CCC"})
    rows = get_carry_forward_symbols(cfg)
    syms = {r["symbol"] for r in rows}
    # AAA carries (score 0.45 above floor, not selected)
    # BBB below floor, dropped
    # CCC selected, not carried
    assert "AAA" in syms
    assert "BBB" not in syms
    assert "CCC" not in syms


def test_carry_forward_decrements_ttl(tmp_path):
    state = str(tmp_path / "cf2.json")
    cfg = _Cfg({"discovery": {
        "carry_forward_enabled": True,
        "carry_forward_min_score": 0.30,
        "carry_forward_ttl_scans": 2,
        "carry_forward_state_file": state,
    }})
    record_unpicked(cfg, [("AAA", 0.45)], selected=set())
    # AAA absent from next scan — TTL decrements
    record_unpicked(cfg, [("BBB", 0.50)], selected=set())
    record_unpicked(cfg, [("CCC", 0.50)], selected=set())
    rows = {r["symbol"]: r for r in get_carry_forward_symbols(cfg)}
    # AAA should now be gone (TTL was 2 → 1 → 0)
    assert "AAA" not in rows
    assert "BBB" in rows
    assert "CCC" in rows


# ---------- av_budget ----------

def test_av_budget_remaining_pct(tmp_path):
    state = str(tmp_path / "avb.json")
    cfg = _Cfg({"av_budget": {
        "enabled": True,
        "rate_limit_per_min": 10,
        "defer_below_pct": 0.20,
        "state_file": state,
    }})
    assert remaining_pct(cfg) == 1.0
    for _ in range(9):
        record_request(cfg, "TIME_SERIES_DAILY")
    rp = remaining_pct(cfg)
    assert 0.05 < rp < 0.15
    # at 90% used → defer non-critical
    assert should_defer_non_critical(cfg) is True


# ---------- scanning_failure_alert ----------

def test_scanning_failure_streak(tmp_path):
    state = str(tmp_path / "sf.json")
    cfg = _Cfg({"scanning_failure_alert": {
        "enabled": True,
        "consecutive_days": 3,
        "state_file": state,
    }})
    # Day 1: 100% reject
    import json as _j
    s = record_scan_outcome(cfg, candidates_evaluated=3, candidates_accepted=0)
    assert s["streak"] == 1
    # Reset state to simulate fresh day
    _j_dump = {**s, "last_day": "1970-01-01"}
    Path(state).write_text(_j.dumps(_j_dump))
    s = record_scan_outcome(cfg, candidates_evaluated=3, candidates_accepted=0)
    assert s["streak"] == 2
    Path(state).write_text(_j.dumps({**s, "last_day": "1970-01-02"}))
    s = record_scan_outcome(cfg, candidates_evaluated=3, candidates_accepted=0)
    assert s["streak"] == 3
    assert s.get("should_alert") is True


# ---------- postmortem ----------

def test_postmortem_record_and_accuracy(tmp_path):
    pm_file = str(tmp_path / "pm.jsonl")
    cfg = _Cfg({"postmortem": {"enabled": True, "journal_file": pm_file}})
    # Winning trade → not flagged as needing arbiter accuracy
    record_postmortem(
        cfg, symbol="WINNER", theme="t", sector="s",
        entry_ts=time.time() - 3600, exit_ts=time.time(),
        entry_price=100.0, exit_price=102.0, qty=10,
        entry_score=0.5, exit_score=0.4,
        exit_kind="exit_arbiter",
    )
    # Losing trade → "correct" exit (saved further drawdown)
    record_postmortem(
        cfg, symbol="LOSER", theme="t", sector="s",
        entry_ts=time.time() - 3600, exit_ts=time.time(),
        entry_price=100.0, exit_price=98.0, qty=10,
        entry_score=0.5, exit_score=0.2,
        exit_kind="exit_arbiter",
    )
    from src.postmortem import read_recent
    rows = read_recent(cfg, days=1)
    assert len(rows) == 2
    diag = exit_arbiter_accuracy(rows)
    assert diag["sample"] == 2
    # LOSER counts as "correct"; WINNER did not need exit → accuracy 0.5
    assert 0.4 <= diag["accuracy"] <= 0.6
