"""Phase 3: protective hard stop widens with ATR up to a 2.5% ceiling."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.executor import TradeExecutor


class _FakeCfg:
    def __init__(self, kv):
        self._kv = dict(kv)

    def get(self, *path, default=None):
        return self._kv.get(path, default)

    @property
    def alpaca(self):
        return MagicMock(mode="paper")


def _executor():
    cfg = _FakeCfg({
        ("execution", "fill_timeout_s"): 30,
        ("execution", "fill_poll_s"): 1.0,
        ("risk", "hard_stop_loss_pct"): 0.01,
        ("risk", "stop_loss_model"): "volatility",
        ("risk", "max_stop_loss_pct"): 0.025,
        ("risk", "hard_stop_loss_atr_mult"): 0.5,
        ("risk", "hard_stop_loss_pct_ceiling"): 0.025,
    })
    return TradeExecutor(client=MagicMock(), config=cfg)


def test_low_volatility_falls_back_to_one_percent():
    """A symbol with ATR/price = 0.005 stays at the 1% floor."""
    ex = _executor()
    pct = ex._effective_hard_stop_pct(entry=100.0, atr=0.5)
    assert abs(pct - 0.01) < 1e-6, f"low-vol should stay at 1%, got {pct:.4f}"


def test_high_volatility_widens_with_atr():
    """AMZN-shape: entry $276, ATR ~ $5.5/day -> ATR/price ~ 0.020 ->
    0.5 * 0.020 = 0.010. That equals floor, so still 1%. Use a higher ATR
    to actually widen."""
    ex = _executor()
    # Entry $276, ATR $11/day -> ATR/price = 0.040 -> 0.5 * 0.040 = 0.020
    pct = ex._effective_hard_stop_pct(entry=276.0, atr=11.0)
    assert abs(pct - 0.020) < 0.001, (
        f"high-vol with ~0.020 ATR ratio should give ~2% stop, got {pct:.4f}"
    )


def test_extreme_volatility_capped_at_ceiling():
    """Extreme intraday vol (e.g. AMD/MARA): ATR/price = 0.10 -> 0.5*0.10 = 0.05
    -> clamped to 0.025 ceiling."""
    ex = _executor()
    pct = ex._effective_hard_stop_pct(entry=100.0, atr=10.0)
    assert abs(pct - 0.025) < 1e-6, (
        f"extreme-vol should clamp to 2.5% ceiling, got {pct:.4f}"
    )


def test_missing_atr_falls_back_to_floor():
    """No ATR context (e.g. data-source failure) defaults to the 1% floor."""
    ex = _executor()
    pct = ex._effective_hard_stop_pct(entry=276.0, atr=None)
    assert abs(pct - 0.01) < 1e-6, f"missing ATR should fall back to 1%, got {pct:.4f}"


def test_zero_entry_returns_floor():
    ex = _executor()
    pct = ex._effective_hard_stop_pct(entry=0.0, atr=5.0)
    assert pct == 0.01


def test_protective_stop_uses_atr_aware_floor():
    """End-to-end: AMZN-shape entry with ATR widens the protective stop."""
    ex = _executor()
    # entry $276, ATR $8 -> ATR/price = 0.029 -> 0.5*0.029 = 0.0145 -> 1.45%
    stop_price, source = ex._protective_stop_loss_price(
        entry_price=276.0, stop_loss=None, atr=8.0,
    )
    # Hard stop at 1.45% below 276 = ~272.00 (rounded up to cents)
    assert 271.9 <= stop_price <= 272.0, (
        f"expected ATR-widened stop near $272, got ${stop_price}"
    )
    assert source == "hard_stop"


def test_protective_stop_low_vol_unchanged():
    """A 1% stock should still produce a 1% protective stop."""
    ex = _executor()
    stop_price, source = ex._protective_stop_loss_price(
        entry_price=100.0, stop_loss=None, atr=0.3,  # ATR/price = 0.003
    )
    # 1% of 100 = 99.00
    assert 98.99 <= stop_price <= 99.00, (
        f"expected 1% floor near $99, got ${stop_price}"
    )
