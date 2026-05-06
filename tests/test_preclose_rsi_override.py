"""Phase 5: tiered preclose RSI cap with macro-tailwind override.

The 2026-05-05 preclose flat-blocked 17 names (INTC, MU, AMZN, BAND, NOK,
PWR, WDC, ...) on RSI > 78. In a clearly-momentum tape (market_bias > 0.20,
rising tech) those leaders should still qualify; only true exhaustion (RSI
> 85) is blocked unconditionally.

These tests exercise the override decision logic directly. The selection
criteria — macro_floor, rsi_extreme_cap, momentum_ok — are the rule, so
we test them in the spirit of the orchestrator's branch.
"""
from __future__ import annotations


def _decide(*, rsi, market_bias, tech_score, tech_trend,
            cap=78.0, extreme=85.0, leader_override=True, macro_floor=0.20):
    """Mirror of the orchestrator's RSI gate decision used at preclose time.

    Returns one of: "skip_extreme", "skip_overbought", "override", "below_cap".
    """
    if rsi is not None and rsi > extreme:
        return "skip_extreme"
    if rsi is not None and rsi > cap:
        macro_ok = (market_bias >= macro_floor)
        momentum_ok = (
            tech_score is not None and float(tech_score) > 0
            and float(tech_trend or 0) > 0
        )
        if leader_override and macro_ok and momentum_ok:
            return "override"
        return "skip_overbought"
    return "below_cap"


def test_extreme_rsi_skipped_regardless_of_macro():
    """RSI > 85 always skips, even with bullish tape."""
    decision = _decide(rsi=86.5, market_bias=0.40, tech_score=0.7, tech_trend=0.5)
    assert decision == "skip_extreme"


def test_intc_at_84_with_risk_on_macro_overrides():
    """INTC RSI 84.4 + market_bias +0.29 + rising trend = leader override."""
    decision = _decide(
        rsi=84.4, market_bias=0.29, tech_score=0.55, tech_trend=0.4,
    )
    assert decision == "override"


def test_intc_at_84_with_weak_macro_skips():
    """Same RSI but flat macro — no override."""
    decision = _decide(
        rsi=84.4, market_bias=0.05, tech_score=0.55, tech_trend=0.4,
    )
    assert decision == "skip_overbought"


def test_overbought_with_falling_trend_skips():
    """RSI between cap and extreme + falling trend = skip even with macro."""
    decision = _decide(
        rsi=80.0, market_bias=0.30, tech_score=0.55, tech_trend=-0.1,
    )
    assert decision == "skip_overbought"


def test_overbought_with_negative_tech_score_skips():
    """Score must be positive, not just trend."""
    decision = _decide(
        rsi=80.0, market_bias=0.30, tech_score=-0.05, tech_trend=0.4,
    )
    assert decision == "skip_overbought"


def test_below_cap_rsi_passes():
    """RSI under 78 — no gate at all."""
    decision = _decide(rsi=65.0, market_bias=0.0, tech_score=0.0, tech_trend=0.0)
    assert decision == "below_cap"


def test_override_disabled_in_config():
    decision = _decide(
        rsi=82.0, market_bias=0.5, tech_score=0.7, tech_trend=0.5,
        leader_override=False,
    )
    assert decision == "skip_overbought"


def test_macro_floor_strict_inequality():
    """market_bias exactly at floor counts as macro_ok."""
    decision = _decide(
        rsi=82.0, market_bias=0.20, tech_score=0.5, tech_trend=0.3,
    )
    assert decision == "override"
    decision = _decide(
        rsi=82.0, market_bias=0.199, tech_score=0.5, tech_trend=0.3,
    )
    assert decision == "skip_overbought"
