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


# --------------------------------------------------------------------------- #
#  Preclose edge profile                                                       #
# --------------------------------------------------------------------------- #


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clip(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return float(max(lo, min(hi, value)))


def _symbol_daily_slice(daily_df: pd.DataFrame | None, symbol: str) -> pd.DataFrame | None:
    if daily_df is None or daily_df.empty:
        return None
    try:
        if "symbol" in daily_df.index.names:
            slc = daily_df.xs(symbol, level="symbol")
        else:
            slc = daily_df
        if slc is None or slc.empty:
            return None
        return slc.sort_index()
    except Exception:
        return None


def _daily_return(slc: pd.DataFrame | None, bars_back: int) -> float | None:
    if slc is None or slc.empty or "close" not in slc.columns:
        return None
    closes = slc["close"].dropna()
    need = bars_back + 1
    if len(closes) < need:
        return None
    prev = float(closes.iloc[-need])
    cur = float(closes.iloc[-1])
    if prev <= 0:
        return None
    return cur / prev - 1.0


def compute_sector_momentum(
    daily_df: pd.DataFrame | None,
    symbols: list[str],
    sectors_by_symbol: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Estimate hot-sector tailwind for preclose candidates.

    Returns a per-symbol dict containing a normalized sector score in [-1,+1].
    The score blends sector-average 1-day and 5-day returns, plus a smaller
    symbol-vs-sector relative strength term. This lets the preclose selector
    favor names riding a real group move instead of a one-off late-day pop.
    """
    sectors_by_symbol = {str(k).upper(): str(v or "Other") for k, v in (sectors_by_symbol or {}).items()}
    rows: dict[str, dict[str, Any]] = {}
    for sym in [str(s).upper() for s in symbols or []]:
        slc = _symbol_daily_slice(daily_df, sym)
        ret_1d = _daily_return(slc, 1)
        ret_5d = _daily_return(slc, 5)
        sector = sectors_by_symbol.get(sym) or "Other"
        rows[sym] = {
            "symbol": sym,
            "sector": sector,
            "ret_1d": ret_1d,
            "ret_5d": ret_5d,
        }

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows.values():
        grouped.setdefault(str(row.get("sector") or "Other"), []).append(row)

    out: dict[str, dict[str, Any]] = {}
    for sector, members in grouped.items():
        vals_1d = [float(m["ret_1d"]) for m in members if m.get("ret_1d") is not None]
        vals_5d = [float(m["ret_5d"]) for m in members if m.get("ret_5d") is not None]
        avg_1d = float(np.mean(vals_1d)) if vals_1d else 0.0
        avg_5d = float(np.mean(vals_5d)) if vals_5d else 0.0
        # A +2% sector day or +5% sector week should matter, but should not
        # overwhelm the symbol's own close-strength/late-drift evidence.
        sector_score = _clip(float(np.tanh(18.0 * avg_1d + 8.0 * avg_5d)))
        for row in members:
            sym = str(row["symbol"])
            rel_1d = None
            if row.get("ret_1d") is not None:
                rel_1d = float(row["ret_1d"]) - avg_1d
            rel_score = _clip(float(np.tanh(24.0 * rel_1d))) if rel_1d is not None else 0.0
            combined = _clip(0.75 * sector_score + 0.25 * rel_score)
            out[sym] = {
                "sector": sector,
                "sector_member_count": len(members),
                "sector_avg_1d": round(avg_1d, 4),
                "sector_avg_5d": round(avg_5d, 4),
                "symbol_ret_1d": round(float(row["ret_1d"]), 4) if row.get("ret_1d") is not None else None,
                "symbol_ret_5d": round(float(row["ret_5d"]), 4) if row.get("ret_5d") is not None else None,
                "relative_1d": round(rel_1d, 4) if rel_1d is not None else None,
                "score": round(combined, 3),
            }
    return out


def build_preclose_edge(
    signal: OvernightSignal,
    *,
    chart: dict[str, Any] | None = None,
    momentum_profile: dict[str, Any] | None = None,
    sector_momentum: dict[str, Any] | None = None,
    earnings_profile: dict[str, Any] | None = None,
    learned_edge: dict[str, Any] | None = None,
    atr_pct: float | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Blend raw overnight score with tradeability, sector, earnings, and learning.

    The raw ``score_overnight`` signal is intentionally simple and stable. This
    profile is the preclose-specific expected-edge layer used for thresholding,
    ranking, and sizing context.
    """
    weights = weights or {}
    momentum_weight = float(weights.get("momentum", 0.12))
    sector_weight = float(weights.get("sector", 0.10))
    earnings_weight = float(weights.get("earnings", 1.0))
    learned_weight = float(weights.get("learned", 1.0))
    gap_only_penalty = float(weights.get("gap_only_penalty", 0.18))
    fading_penalty = float(weights.get("fading_penalty", 0.10))
    high_atr_penalty = float(weights.get("high_atr_penalty", 0.08))
    high_atr_pct = float(weights.get("high_atr_pct", 0.08))

    components: dict[str, float] = {
        "base_overnight": round(float(signal.score), 3),
    }
    notes = list(signal.notes or [])
    risk_flags: list[str] = []
    adjusted = float(signal.score)

    if momentum_profile:
        mp_score = _as_float(momentum_profile.get("score"), 50.0)
        # 55 is the existing selector continuation floor. Above it adds, below
        # it subtracts, capped so a pretty chart cannot rescue a bad overnight
        # signal by itself.
        continuation = _clip((mp_score - 55.0) / 45.0)
        adj = momentum_weight * continuation
        adjusted += adj
        components["continuation"] = round(adj, 3)
        grade = str(momentum_profile.get("grade") or "")
        if momentum_profile.get("gap_only_risk"):
            adjusted -= gap_only_penalty
            components["gap_only_penalty"] = round(-gap_only_penalty, 3)
            risk_flags.append("gap_only_risk")
        if grade == "fading":
            adjusted -= fading_penalty
            components["fading_penalty"] = round(-fading_penalty, 3)
            risk_flags.append("fading_into_close")

    if chart:
        if str(chart.get("recent_trend") or "") == "falling":
            risk_flags.append("recent_trend_falling")
        if str(chart.get("volume_trend") or "") == "rising":
            components["late_volume_confirmation"] = 0.025
            adjusted += 0.025
        if chart.get("gap_only_risk") and "gap_only_risk" not in risk_flags:
            adjusted -= gap_only_penalty
            components["gap_only_penalty"] = round(-gap_only_penalty, 3)
            risk_flags.append("gap_only_risk")

    if sector_momentum:
        sector_score = _as_float(sector_momentum.get("score"), 0.0)
        adj = sector_weight * _clip(sector_score)
        adjusted += adj
        components["sector_momentum"] = round(adj, 3)

    if earnings_profile:
        earn_adj = _as_float(earnings_profile.get("score_adjustment"), 0.0)
        adjusted += earnings_weight * earn_adj
        components["earnings_profile"] = round(earnings_weight * earn_adj, 3)
        if earnings_profile.get("event_risk_overnight"):
            risk_flags.append("earnings_event_overnight")
        if earnings_profile.get("post_earnings_session"):
            notes.append("post_earnings_drift_candidate")

    if learned_edge:
        learned_adj = _as_float(learned_edge.get("adjustment"), 0.0)
        adjusted += learned_weight * learned_adj
        components["learned_edge"] = round(learned_weight * learned_adj, 3)
        if _as_float(learned_edge.get("gap_down_risk"), 0.0) >= 0.35:
            risk_flags.append("learned_gap_down_risk")

    if atr_pct is not None and float(atr_pct) >= high_atr_pct:
        adjusted -= high_atr_penalty
        components["high_atr_penalty"] = round(-high_atr_penalty, 3)
        risk_flags.append("high_atr_gap_risk")

    adjusted = _clip(adjusted)
    return {
        "symbol": signal.symbol,
        "base_score": round(float(signal.score), 3),
        "adjusted_score": round(adjusted, 3),
        "components": components,
        "sector_momentum": sector_momentum,
        "earnings_profile": earnings_profile,
        "learned_edge": learned_edge,
        "atr_pct": round(float(atr_pct), 4) if atr_pct is not None else None,
        "risk_flags": list(dict.fromkeys(risk_flags)),
        "notes": list(dict.fromkeys(notes)),
    }
