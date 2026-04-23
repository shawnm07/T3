"""Macro regime: risk-on / neutral / risk-off based on SPY trend, VIX, breadth."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.alpaca_client import AlpacaClient
from src.technicals import _atr, _ema, _rsi

log = logging.getLogger(__name__)


@dataclass
class MacroSignal:
    regime: str  # "risk_on" | "neutral" | "risk_off"
    score: float  # -1 risk_off ... +1 risk_on
    spy_trend: float
    spy_vs_200ema: float
    vix_level: float | None
    vix_regime: str
    breadth_pct_above_50: float | None
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime": self.regime,
            "score": round(self.score, 3),
            "spy_trend": round(self.spy_trend, 3),
            "spy_vs_200ema": round(self.spy_vs_200ema, 3),
            "vix_level": self.vix_level,
            "vix_regime": self.vix_regime,
            "breadth_pct_above_50": self.breadth_pct_above_50,
            "notes": self.notes,
        }


def compute_macro(client: AlpacaClient, breadth_symbols: list[str] | None = None) -> MacroSignal:
    notes: list[str] = []

    # SPY trend
    spy_bars = client.get_stock_bars(["SPY"], lookback_days=252)
    spy = spy_bars.xs("SPY", level="symbol") if "symbol" in spy_bars.index.names else spy_bars
    spy_close = spy["close"]
    ema50 = _ema(spy_close, 50)
    ema200 = _ema(spy_close, 200) if len(spy_close) >= 200 else _ema(spy_close, 100)
    price = float(spy_close.iloc[-1])
    spy_vs_200 = price / float(ema200.iloc[-1]) - 1 if ema200.iloc[-1] else 0
    spy_trend = np.tanh(5 * spy_vs_200)
    if price > ema50.iloc[-1] > ema200.iloc[-1]:
        notes.append("spy_uptrend")
    elif price < ema50.iloc[-1] < ema200.iloc[-1]:
        notes.append("spy_downtrend")
    else:
        notes.append("spy_mixed")

    # VIX: try VIXY as proxy (Alpaca doesn't have ^VIX directly)
    vix_level: float | None = None
    vix_score = 0.0
    vix_regime = "unknown"
    try:
        vixy_bars = client.get_stock_bars(["VIXY"], lookback_days=60)
        vixy = vixy_bars.xs("VIXY", level="symbol") if "symbol" in vixy_bars.index.names else vixy_bars
        vixy_last = float(vixy["close"].iloc[-1])
        vixy_20d_avg = float(vixy["close"].rolling(20).mean().iloc[-1])
        vix_level = vixy_last
        ratio = vixy_last / vixy_20d_avg if vixy_20d_avg else 1
        if ratio < 0.90:
            vix_regime = "low_vol"
            vix_score = 0.5
        elif ratio < 1.10:
            vix_regime = "normal"
            vix_score = 0.0
        elif ratio < 1.30:
            vix_regime = "elevated"
            vix_score = -0.3
        else:
            vix_regime = "spike"
            vix_score = -0.8
        notes.append(f"vixy_ratio_{round(ratio, 2)}")
    except Exception as e:
        log.info("VIXY unavailable: %s", e)

    # Breadth
    breadth_score = 0.0
    breadth_pct: float | None = None
    if breadth_symbols:
        try:
            sample = breadth_symbols[:50]
            bars = client.get_stock_bars(sample, lookback_days=80)
            above = 0
            counted = 0
            for sym in sample:
                try:
                    s = bars.xs(sym, level="symbol")
                    if len(s) < 50:
                        continue
                    ema50_s = float(_ema(s["close"], 50).iloc[-1])
                    counted += 1
                    if float(s["close"].iloc[-1]) > ema50_s:
                        above += 1
                except Exception:
                    continue
            if counted:
                breadth_pct = above / counted
                breadth_score = (breadth_pct - 0.5) * 2  # [-1,1]
                notes.append(f"breadth_{round(breadth_pct*100)}pct")
        except Exception as e:
            log.info("Breadth calc failed: %s", e)

    score = 0.45 * spy_trend + 0.30 * vix_score + 0.25 * breadth_score
    score = float(max(-1.0, min(1.0, score)))
    if score > 0.35:
        regime = "risk_on"
    elif score < -0.35:
        regime = "risk_off"
    else:
        regime = "neutral"

    return MacroSignal(
        regime=regime,
        score=score,
        spy_trend=float(spy_trend),
        spy_vs_200ema=float(spy_vs_200),
        vix_level=vix_level,
        vix_regime=vix_regime,
        breadth_pct_above_50=breadth_pct,
        notes=notes,
    )
