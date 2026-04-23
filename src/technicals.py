"""Technical analysis: trend, momentum, volatility → normalized signal score."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class TechnicalSignal:
    symbol: str
    score: float
    trend: float
    momentum: float
    volatility: float
    atr: float
    rsi: float
    price: float
    ema50: float
    ema200: float
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "score": round(self.score, 3),
            "trend": round(self.trend, 3),
            "momentum": round(self.momentum, 3),
            "volatility": round(self.volatility, 3),
            "atr": round(self.atr, 2),
            "rsi": round(self.rsi, 1),
            "price": round(self.price, 2),
            "ema50": round(self.ema50, 2),
            "ema200": round(self.ema200, 2),
            "notes": self.notes,
        }


def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def _rsi(s: pd.Series, period: int = 14) -> pd.Series:
    delta = s.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat(
        [(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def _macd(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    macd = _ema(s, 12) - _ema(s, 26)
    sig = _ema(macd, 9)
    return macd, sig


def compute_technicals(symbol: str, df: pd.DataFrame) -> TechnicalSignal | None:
    """df: columns open/high/low/close/volume, indexed by date (ascending)."""
    if df is None or len(df) < 60:
        return None
    df = df.dropna().sort_index()
    close = df["close"]

    ema20 = _ema(close, 20)
    ema50 = _ema(close, 50)
    ema200 = _ema(close, 200) if len(df) >= 200 else _ema(close, min(100, len(df) - 1))
    rsi = _rsi(close, 14)
    atr = _atr(df, 14)
    macd, macd_sig = _macd(close)

    price = float(close.iloc[-1])
    notes: list[str] = []

    # Trend: combine price vs EMA50/EMA200, EMA50 slope
    price_vs_50 = (price / float(ema50.iloc[-1])) - 1 if ema50.iloc[-1] else 0
    price_vs_200 = (price / float(ema200.iloc[-1])) - 1 if ema200.iloc[-1] else 0
    ema50_slope = (float(ema50.iloc[-1]) / float(ema50.iloc[-20]) - 1) if len(ema50) >= 21 and ema50.iloc[-20] else 0
    trend = np.tanh(4 * (0.5 * price_vs_50 + 0.3 * price_vs_200 + 0.2 * ema50_slope * 5))
    if ema50.iloc[-1] > ema200.iloc[-1]:
        notes.append("golden_cross_regime")
    else:
        notes.append("below_200ema_regime")

    # Momentum: RSI + MACD + 20d ROC
    rsi_last = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50
    rsi_score = (rsi_last - 50) / 30  # ±1 at rsi 20/80
    rsi_score = max(-1.2, min(1.2, rsi_score))
    roc20 = (price / float(close.iloc[-21]) - 1) if len(close) > 21 else 0
    macd_hist = float((macd - macd_sig).iloc[-1])
    macd_score = np.tanh(macd_hist / (price * 0.005)) if price > 0 else 0
    momentum = np.tanh(0.5 * rsi_score + 3 * roc20 + 0.5 * macd_score)
    if rsi_last > 70:
        notes.append("rsi_overbought")
    elif rsi_last < 30:
        notes.append("rsi_oversold")

    # Volatility sanity (penalize extreme vol)
    atr_last = float(atr.iloc[-1])
    atr_pct = atr_last / price if price else 0
    volatility = -np.tanh((atr_pct - 0.03) * 20)  # neutral at 3% ATR, penalize higher

    # Combine: 0.55 trend + 0.35 momentum + 0.10 volatility
    score = 0.55 * trend + 0.35 * momentum + 0.10 * volatility
    score = float(max(-1.0, min(1.0, score)))

    return TechnicalSignal(
        symbol=symbol,
        score=score,
        trend=float(trend),
        momentum=float(momentum),
        volatility=float(volatility),
        atr=atr_last,
        rsi=rsi_last,
        price=price,
        ema50=float(ema50.iloc[-1]),
        ema200=float(ema200.iloc[-1]),
        notes=notes,
    )


def technicals_for_bars_df(bars_df: pd.DataFrame) -> dict[str, TechnicalSignal]:
    """Input: multi-index (symbol, timestamp) DataFrame from Alpaca. Output: per-symbol signals."""
    out: dict[str, TechnicalSignal] = {}
    if "symbol" in bars_df.index.names:
        for sym, g in bars_df.groupby(level="symbol"):
            g = g.reset_index(level="symbol", drop=True)
            sig = compute_technicals(sym, g)
            if sig:
                out[sym] = sig
    else:
        sig = compute_technicals("UNKNOWN", bars_df)
        if sig:
            out["UNKNOWN"] = sig
    return out
