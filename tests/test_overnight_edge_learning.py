from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.overnight import (
    OvernightSignal,
    build_preclose_edge,
    compute_sector_momentum,
)
from src.overnight_learning import (
    estimate_overnight_edge,
    record_preclose_candidates,
    resolve_overnight_outcomes,
)


class _Cfg:
    def __init__(self, raw):
        self.raw = raw

    def get(self, *keys, default=None):
        node = self.raw
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node


def _daily_df(symbols_to_closes: dict[str, list[float]]) -> pd.DataFrame:
    rows = []
    idx = []
    dates = pd.date_range("2026-05-01", periods=6, freq="D")
    for sym, closes in symbols_to_closes.items():
        for ts, close in zip(dates, closes):
            idx.append((sym, ts))
            rows.append({
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume": 1_000_000,
            })
    return pd.DataFrame(
        rows,
        index=pd.MultiIndex.from_tuples(idx, names=["symbol", "timestamp"]),
    )


def test_sector_momentum_rewards_hot_group_and_relative_leader():
    df = _daily_df({
        "AAA": [100, 101, 102, 103, 104, 110],
        "BBB": [50, 51, 52, 53, 54, 55],
        "CCC": [80, 80, 79, 79, 78, 77],
    })

    scores = compute_sector_momentum(
        df,
        ["AAA", "BBB", "CCC"],
        {"AAA": "Tech", "BBB": "Tech", "CCC": "Utilities"},
    )

    assert scores["AAA"]["score"] > 0
    assert scores["BBB"]["score"] > 0
    assert scores["AAA"]["score"] > scores["BBB"]["score"]
    assert scores["CCC"]["score"] < 0


def test_preclose_edge_blends_boosts_and_penalties():
    signal = OvernightSignal(
        symbol="AAA",
        score=0.50,
        close_strength=0.70,
        late_drift=0.40,
        tech_bias=0.30,
        sent_bias=0.10,
        market_bias=0.20,
        price=100.0,
    )

    edge = build_preclose_edge(
        signal,
        chart={"recent_trend": "rising", "volume_trend": "rising"},
        momentum_profile={"score": 82, "grade": "strong_continuation"},
        sector_momentum={"sector": "Tech", "score": 0.60},
        earnings_profile={"score_adjustment": 0.04, "post_earnings_session": True},
        learned_edge={"adjustment": 0.05, "gap_down_risk": 0.10},
        atr_pct=0.03,
    )
    weak_edge = build_preclose_edge(
        signal,
        chart={"recent_trend": "falling", "volume_trend": "fading", "gap_only_risk": True},
        momentum_profile={"score": 35, "grade": "fading", "gap_only_risk": True},
        sector_momentum={"sector": "Tech", "score": -0.60},
        learned_edge={"adjustment": -0.05, "gap_down_risk": 0.50},
        atr_pct=0.12,
    )

    assert edge["adjusted_score"] > signal.score
    assert "post_earnings_drift_candidate" in edge["notes"]
    assert weak_edge["adjusted_score"] < signal.score
    assert "gap_only_risk" in weak_edge["risk_flags"]
    assert "high_atr_gap_risk" in weak_edge["risk_flags"]
    assert "learned_gap_down_risk" in weak_edge["risk_flags"]


class _FakeClient:
    def get_stock_bars(self, symbols, lookback_days=20):
        idx = pd.MultiIndex.from_tuples(
            [("AAA", pd.Timestamp("2026-05-08"))],
            names=["symbol", "timestamp"],
        )
        return pd.DataFrame(
            [{
                "open": 103.0,
                "high": 106.0,
                "low": 101.0,
                "close": 105.0,
                "volume": 2_000_000,
            }],
            index=idx,
        )


def test_overnight_learning_records_resolves_and_estimates(tmp_path, monkeypatch):
    import src.overnight_learning as ol

    monkeypatch.setattr(ol, "ROOT", tmp_path)
    cfg = _Cfg({
        "overnight": {
            "learning": {
                "enabled": True,
                "state_file": "state.json",
                "journal_file": "journal.jsonl",
                "record_dry_runs": True,
                "max_pending_days": 14,
                "max_history_records": 100,
                "min_sample_for_adjustment": 1,
                "max_score_adjustment": 0.15,
            }
        }
    })
    summary = {
        "ts": "2026-05-07T20:00:00+00:00",
        "market_bias": 0.20,
        "candidate_reports": [{
            "symbol": "AAA",
            "overnight": {"score": 0.62, "price": 100.0},
            "overnight_edge": {
                "adjusted_score": 0.70,
                "sector_momentum": {"sector": "Tech", "score": 0.5},
                "earnings_profile": {"event_risk_overnight": False},
                "risk_flags": [],
            },
            "discovery_sources": ["av_gainers"],
        }],
        "new_executions": [{"dry_run": True, "sizing": {"symbol": "AAA"}}],
    }

    recorded = record_preclose_candidates(cfg, summary, dry_run=True)
    resolved = resolve_overnight_outcomes(cfg, _FakeClient())
    edge = estimate_overnight_edge(
        cfg,
        "AAA",
        {
            "adjusted_score": 0.70,
            "sector": "Tech",
            "sources": ["av_gainers"],
            "earnings_bucket": "no_near_earnings",
        },
    )

    assert recorded["recorded"] == 1
    assert resolved["resolved"] == 1
    assert edge["sample_size"] >= 1
    assert edge["avg_gap_return"] > 0
    assert edge["adjustment"] > 0
