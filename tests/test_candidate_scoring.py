from __future__ import annotations

import copy
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml  # noqa: F401
except ModuleNotFoundError:
    sys.modules["yaml"] = types.SimpleNamespace(safe_load=lambda *_args, **_kwargs: {})

try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda *_args, **_kwargs: None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai_pipeline import validate_selector_response
from src.candidate_scoring import (
    annotate_candidate_leadership,
    discovery_priority_score,
    missed_breakout_candidates,
)
from src.dynamic_watchlist import load_dynamic_watchlist, update_dynamic_watchlist


class DummyConfig:
    def __init__(self, state_file: str | None = None):
        self.raw = {
            "risk": {
                "max_position_pct": 1.0,
                "max_risk_per_trade_pct": 0.005,
                "hard_stop_loss_pct": 0.01,
            },
            "selector": {
                "min_positions": 3,
                "max_positions": 6,
                "peer_outperformance_threshold": 10,
            },
            "dynamic_watchlist": {
                "enabled": True,
                "state_file": state_file or "data/state/test_dynamic_watchlist.json",
                "max_symbols": 5,
                "ttl_days": 7,
                "add_score": 65,
                "keep_score": 45,
            },
        }

    def get(self, *keys: str, default=None):
        node = self.raw
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node


def _block(symbol: str, score: float, intraday: float, source: str):
    return {
        "symbol": symbol,
        "currently_held": False,
        "sector": "Information Technology",
        "theme_bucket": "ai_data_center",
        "tech_score": 0.6,
        "sent_score": 0.2,
        "intraday_change_pct": intraday,
        "twenty_day_volume_ratio": 2.0,
        "discovery_sources": [source],
        "momentum_profile": {
            "score": score,
            "grade": "strong_continuation" if score >= 75 else "weak_or_flat",
            "passes_new_entry_gate": score >= 55,
            "gap_only_risk": False,
        },
        "intraday_chart": {"session_volume": 10_000_000},
    }


def test_list_sources_are_eligibility_only():
    list_score, list_reasons = discovery_priority_score(
        ["seed_watchlist", "dynamic_watchlist"],
        change_pct=0,
        volume=0,
    )
    mover_score, mover_reasons = discovery_priority_score(
        ["av_gainers"],
        change_pct=0.03,
        volume=2_000_000,
    )

    assert list_score == 0
    assert "list_eligibility_no_score_bonus" in list_reasons
    assert mover_score > 40
    assert "av_gainers" in mover_reasons


def test_peer_leadership_marks_weaker_peer_pressure():
    pool = [
        _block("INTC", 90, 0.045, "av_gainers"),
        _block("AMD", 52, 0.002, "seed_watchlist"),
    ]

    annotate_candidate_leadership(
        pool,
        {"semiconductors": ["AMD", "INTC"]},
        peer_gap_threshold=10,
    )
    by_symbol = {row["symbol"]: row for row in pool}

    assert by_symbol["INTC"]["peer_rank"] == 1
    assert by_symbol["AMD"]["peer_pressure"]["stronger_peer"] == "INTC"
    assert by_symbol["AMD"]["peer_pressure"]["requires_explicit_justification"]


def _selector_result(reason: str):
    return {
        "portfolio_thesis": "Test",
        "spy_target_pct": 0.0,
        "cash_target_pct": 0.0,
        "spy_decision": {
            "target_pct": 0,
            "action": "HOLD",
            "opportunity_score": 0,
            "one_sentence_reason": "No SPY target.",
        },
        "selected_positions": ["AMD"],
        "target_weights": {"AMD": 1.0},
        "per_symbol": {
            "AMD": {
                "target_pct": 1.0,
                "qty": 100,
                "delta_qty": 100,
                "entry_price": 100,
                "stop_loss": None,
                "take_profit": None,
                "action": "BUY",
                "confidence": 0.8,
                "opportunity_score": 80,
                "one_sentence_reason": reason,
                "exhaustion_penalty": False,
                "remaining_upside_score": 80,
            }
        },
        "candidate_rankings": [
            {
                "symbol": "INTC",
                "rank": 1,
                "opportunity_score": 90,
                "currently_held": False,
                "exhausted": False,
                "remaining_upside_score": 90,
                "one_sentence_reason": "Peer leader.",
            },
            {
                "symbol": "AMD",
                "rank": 2,
                "opportunity_score": 80,
                "currently_held": False,
                "exhausted": False,
                "remaining_upside_score": 80,
                "one_sentence_reason": reason,
            },
        ],
        "exhaustion_penalty_applied": [],
        "rotation_plan": {"entered": [], "exited": [], "held": []},
    }


def test_validator_requires_explicit_peer_justification():
    cfg = DummyConfig()
    pool_meta = {
        "AMD": {
            "currently_held": False,
            "current_qty": 0,
            "peer_pressure": {
                "stronger_peer": "INTC",
                "score_gap": 20,
                "requires_explicit_justification": True,
            },
        },
        "INTC": {"currently_held": False, "current_qty": 0},
    }

    bad = _selector_result("AMD has acceptable momentum.")
    ok, problems = validate_selector_response(
        bad,
        held_symbols=[],
        pool_symbols=["AMD", "INTC"],
        pool_meta=pool_meta,
        cfg=cfg,
        allow_floor_breach=True,
        equity=100_000,
    )
    assert not ok
    assert any("trails stronger peer INTC" in p for p in problems)

    good = _selector_result("AMD is chosen over INTC because its catalyst is more specific today.")
    ok, problems = validate_selector_response(
        copy.deepcopy(good),
        held_symbols=[],
        pool_symbols=["AMD", "INTC"],
        pool_meta=pool_meta,
        cfg=cfg,
        allow_floor_breach=True,
        equity=100_000,
    )
    assert ok, problems


def test_dynamic_watchlist_updates_without_list_bias():
    with tempfile.TemporaryDirectory() as tmp:
        state_file = str(Path(tmp) / "dynamic_watchlist.json")
        cfg = DummyConfig(state_file)
        now = datetime(2026, 4, 29, tzinfo=timezone.utc)
        pool = [_block("BE", 88, 0.035, "av_gainers")]
        annotate_candidate_leadership(pool, {"ai_data_center_power": ["BE"]})

        update = update_dynamic_watchlist(cfg, pool, now=now)
        assert "BE" in update["added_or_refreshed"]
        assert load_dynamic_watchlist(cfg, now=now) == ["BE"]

        future = now + timedelta(days=8)
        update_dynamic_watchlist(cfg, [], now=future)
        assert load_dynamic_watchlist(cfg, now=future) == []


def test_missed_breakout_detection_catches_unselected_leader():
    pool = [_block("BE", 88, 0.035, "av_gainers")]
    annotate_candidate_leadership(pool, {"ai_data_center_power": ["BE"]})
    missed = missed_breakout_candidates(pool, selected_symbols=[], per_symbol={})

    assert missed
    assert missed[0]["symbol"] == "BE"


if __name__ == "__main__":
    test_list_sources_are_eligibility_only()
    test_peer_leadership_marks_weaker_peer_pressure()
    test_validator_requires_explicit_peer_justification()
    test_dynamic_watchlist_updates_without_list_bias()
    test_missed_breakout_detection_catches_unselected_leader()
    print("candidate scoring tests passed")
