"""Overnight-hold scoring: does a position/candidate likely gap favorably tomorrow?

Used by the pre-close routine (~5 min before the bell) to:
  - decide whether to close each currently-held equity position before the bell
  - find fresh candidates likely to open higher the next morning

Signals blended:
  - late-day closing-range strength (close vs today's high-low range)
  - intraday drift vs VWAP in the final hour
  - daily technical score (trend/momentum backdrop)
  - recent news sentiment
  - SPY late-day tape as a crude market overlay
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


@dataclass
class OvernightSignal:
    symbol: str
    score: float           # -1..+1, positive = bullish overnight
    close_strength: float  # -1..+1, closing-range within today's bar
    late_drift: float      # -1..+1, last-hour return vs vwap
    tech_bias: float       # -1..+1, daily technical score
    sent_bias: float       # -1..+1, recent news sentiment score
    market_bias: float     # -1..+1, SPY late-day drift
    price: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "score": round(self.score, 3),
            "close_strength": round(self.close_strength, 3),
            "late_drift": round(self.late_drift, 3),
            "tech_bias": round(self.tech_bias, 3),
            "sent_bias": round(self.sent_bias, 3),
            "market_bias": round(self.market_bias, 3),
            "price": round(self.price, 2),
            "notes": self.notes,
        }


def _today_utc_date() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc).date())


def _filter_today(df: pd.DataFrame) -> pd.DataFrame:
    """Subset rows that belong to the most recent trading session present in df."""
    if df is None or df.empty:
        return df
    idx = df.index
    if isinstance(idx, pd.MultiIndex):
        # Expect (symbol, timestamp) but this helper is called after single-symbol slicing.
        return df
    try:
        ts = pd.to_datetime(idx)
    except Exception:
        return df
    last_day = ts[-1].normalize()
    mask = ts.normalize() == last_day
    return df.loc[mask]


def _closing_range(bars_today: pd.DataFrame) -> float:
    """+1 if close at today's high, -1 if at today's low. Neutral at mid."""
    if bars_today is None or bars_today.empty:
        return 0.0
    high = float(bars_today["high"].max())
    low = float(bars_today["low"].min())
    close = float(bars_today["close"].iloc[-1])
    if high <= low:
        return 0.0
    pos = (close - low) / (high - low)  # 0..1
    return float(np.clip(2 * pos - 1, -1.0, 1.0))


def _late_drift(bars_today: pd.DataFrame, last_n: int = 12) -> float:
    """Last-hour (assuming ~5m bars) return vs VWAP, tanh-scaled."""
    if bars_today is None or bars_today.empty or len(bars_today) < 2:
        return 0.0
    tail = bars_today.tail(last_n)
    if tail.empty:
        return 0.0
    tp = (tail["high"] + tail["low"] + tail["close"]) / 3
    vol = tail["volume"].replace(0, np.nan)
    vwap_num = (tp * vol).sum()
    vwap_den = vol.sum()
    if not vwap_den or np.isnan(vwap_den):
        return 0.0
    vwap = float(vwap_num / vwap_den)
    last = float(tail["close"].iloc[-1])
    if vwap <= 0:
        return 0.0
    drift = (last / vwap) - 1
    # last-hour return on top of vwap distance
    ret = (last / float(tail["close"].iloc[0])) - 1 if tail["close"].iloc[0] else 0
    raw = 0.6 * drift + 0.4 * ret
    return float(np.tanh(raw * 60))  # scale so ~1% move pegs signal


def _sent_from_score(score: float | None) -> float:
    if score is None:
        return 0.0
    return float(np.clip(score, -1.0, 1.0))


def score_overnight(
    symbol: str,
    intraday_df: pd.DataFrame | None,
    tech_score: float,
    sent_score: float | None,
    market_bias: float,
) -> OvernightSignal | None:
    """Compute overnight bias for one symbol.

    intraday_df: DataFrame of intraday bars (any fine timeframe) for this symbol,
                 single-index by timestamp, covering at least today's session.
    """
    if intraday_df is None or intraday_df.empty:
        return None
    today = _filter_today(intraday_df)
    if today.empty:
        return None

    close_strength = _closing_range(today)
    late = _late_drift(today)
    tech_bias = float(np.clip(tech_score, -1.0, 1.0))
    sent_bias = _sent_from_score(sent_score)
    mkt = float(np.clip(market_bias, -1.0, 1.0))

    # Weighted blend: prioritize what happens in the final hour of trade.
    score = (
        0.30 * close_strength
        + 0.25 * late
        + 0.20 * tech_bias
        + 0.15 * sent_bias
        + 0.10 * mkt
    )
    score = float(np.clip(score, -1.0, 1.0))

    notes: list[str] = []
    if close_strength >= 0.6:
        notes.append("closing_near_high")
    elif close_strength <= -0.6:
        notes.append("closing_near_low")
    if late >= 0.5:
        notes.append("late_day_strength")
    elif late <= -0.5:
        notes.append("late_day_weakness")
    if mkt >= 0.4:
        notes.append("market_tape_supportive")
    elif mkt <= -0.4:
        notes.append("market_tape_heavy")

    return OvernightSignal(
        symbol=symbol,
        score=score,
        close_strength=close_strength,
        late_drift=late,
        tech_bias=tech_bias,
        sent_bias=sent_bias,
        market_bias=mkt,
        price=float(today["close"].iloc[-1]),
        notes=notes,
    )


def market_bias_from_spy(spy_intraday: pd.DataFrame | None) -> float:
    """Crude late-day market regime read from SPY intraday bars."""
    if spy_intraday is None or spy_intraday.empty:
        return 0.0
    today = _filter_today(spy_intraday)
    if today.empty or len(today) < 2:
        return 0.0
    return _late_drift(today) * 0.7 + _closing_range(today) * 0.3
