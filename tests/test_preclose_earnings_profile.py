from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.earnings as earnings
from src.earnings import (
    EarningsInfo,
    build_preclose_earnings_profile,
    classify_earnings_timing,
    compute_earnings_research_score,
)


def test_day0_amc_is_overnight_event_risk():
    info = EarningsInfo("ABC", "2026-05-07", 0, time_of_day="amc")

    timing = classify_earnings_timing(info)

    assert timing["event_risk_overnight"] is True
    assert timing["post_earnings_session"] is False
    assert timing["timing_class"] == "tonight_event"


def test_day0_bmo_is_post_earnings_drift_candidate():
    info = EarningsInfo("ABC", "2026-05-07", 0, time_of_day="bmo")

    timing = classify_earnings_timing(info)

    assert timing["event_risk_overnight"] is False
    assert timing["post_earnings_session"] is True
    assert timing["timing_class"] == "post_earnings_same_day"


def test_day1_bmo_crosses_event_before_next_open():
    info = EarningsInfo("ABC", "2026-05-08", 1, time_of_day="bmo")

    timing = classify_earnings_timing(info)

    assert timing["event_risk_overnight"] is True
    assert timing["timing_class"] == "tomorrow_bmo_event"


def test_day1_amc_does_not_cross_next_open_event():
    info = EarningsInfo("ABC", "2026-05-08", 1, time_of_day="amc")

    timing = classify_earnings_timing(info)

    assert timing["event_risk_overnight"] is False
    assert timing["timing_class"] == "tomorrow_after_close"


def test_event_risk_requires_live_catalyst_and_positive_research():
    info = EarningsInfo("ABC", "2026-05-07", 0, time_of_day="amc")

    weak = build_preclose_earnings_profile(
        info,
        {"score": 0.10, "components": {}, "available_components": ["sentiment"]},
        sentiment_score=0.20,
        catalyst_source=True,
        min_research_score=0.25,
    )
    strong = build_preclose_earnings_profile(
        info,
        {"score": 0.45, "components": {}, "available_components": ["sentiment"]},
        sentiment_score=0.20,
        catalyst_source=True,
        min_research_score=0.25,
    )

    assert weak["entry_allowed"] is False
    assert "research_score_below_event_minimum" in weak["reasons"]
    assert strong["entry_allowed"] is True
    assert strong["threshold_floor"] == 0.65
    assert strong["size_multiplier"] == 0.30


def test_post_earnings_profile_allows_drift_with_sentiment():
    info = EarningsInfo("ABC", "2026-05-07", 0, time_of_day="bmo")

    profile = build_preclose_earnings_profile(
        info,
        {"score": -0.10, "components": {}, "available_components": ["sentiment"]},
        sentiment_score=0.12,
        catalyst_source=False,
    )

    assert profile["entry_allowed"] is True
    assert profile["post_earnings_session"] is True
    assert profile["threshold_floor"] == 0.50
    assert profile["score_adjustment"] > 0


def test_cached_research_refreshes_live_sentiment_component(tmp_path, monkeypatch):
    cache_file = tmp_path / "research.json"
    cache_file.write_text(json.dumps({
        "ABC": {
            "fetched_at": time.time(),
            "payload": {
                "score": 0.4,
                "components": {
                    "beat_history": 0.4,
                    "pt_trend": None,
                    "implied_move": None,
                    "sentiment": None,
                },
                "available_components": ["beat_history"],
            },
        }
    }))
    monkeypatch.setattr(earnings, "RESEARCH_CACHE_FILE", cache_file)

    payload = compute_earnings_research_score("ABC", sentiment_score=-1.0)

    assert payload["components"]["sentiment"] == -1.0
    assert "sentiment" in payload["available_components"]
    assert payload["score"] < 0.4
