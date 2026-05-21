"""Intraday SPY tape filter (Phase A).

Computes a real-time "tape badness" score from SPY intraday bars and converts
it into a proportional minimum-opportunity-score floor for new entries.

Unlike the daily ``macro.bearish_halt_score`` (binary halt at -0.55), this
filter NEVER hard-blocks entries. It raises the bar smoothly: the worse SPY
is doing intraday, the higher the opportunity-score a fresh BUY needs to
clear. Any number of names that clear the bar are allowed.

Inputs are SPY 5-minute bars for the current session. Outputs are surfaced
to the portfolio-selector via ``system_state.tape_state``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)


@dataclass
class TapeSignal:
    spy_intraday_change_pct: float          # % change vs today's open (e.g. -0.012 = -1.2%)
    spy_vs_vwap_pct: float                  # % above/below session VWAP
    spy_intraday_low_break_pct: float       # how far below the prior 30-min low (0 if not broken)
    tape_badness: float                     # 0.0 (favorable) .. 1.0 (severe risk-off)
    min_opportunity_score_floor: float      # the entry floor selector must enforce
    severity_label: str                     # favorable | neutral | mild_risk_off | strong_risk_off
    notes: list[str]
    has_data: bool                          # False when SPY intraday is unavailable

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["spy_intraday_change_pct"] = round(self.spy_intraday_change_pct, 4)
        d["spy_vs_vwap_pct"] = round(self.spy_vs_vwap_pct, 4)
        d["spy_intraday_low_break_pct"] = round(self.spy_intraday_low_break_pct, 4)
        d["tape_badness"] = round(self.tape_badness, 3)
        d["min_opportunity_score_floor"] = round(self.min_opportunity_score_floor, 1)
        return d


def _filter_today(df: pd.DataFrame) -> pd.DataFrame:
    """Slice to today's regular-hours bars in US/Eastern."""
    if df is None or df.empty:
        return df
    try:
        idx = df.index
        if "timestamp" in df.index.names:
            ts = idx.get_level_values("timestamp")
        else:
            ts = idx
        ts_et = pd.to_datetime(ts, utc=True).tz_convert("America/New_York")
        # take the most recent session date present in the data
        last_date = ts_et[-1].date()
        mask = (ts_et.date == last_date)
        return df[mask]
    except Exception:
        return df


def _vwap(df: pd.DataFrame) -> float | None:
    if df is None or df.empty or "close" not in df.columns or "volume" not in df.columns:
        return None
    try:
        typical = (df["high"] + df["low"] + df["close"]) / 3.0 if "high" in df.columns and "low" in df.columns else df["close"]
        v = df["volume"].fillna(0)
        if float(v.sum()) <= 0:
            return float(df["close"].mean())
        return float((typical * v).sum() / v.sum())
    except Exception:
        return None


def compute_tape_signal(
    spy_intraday: pd.DataFrame | None,
    cfg: dict[str, Any] | None = None,
) -> TapeSignal:
    """Compute the proportional tape filter from SPY 5-minute bars.

    ``cfg`` is the ``intraday_tape_filter`` section of config.yaml. Knobs:
      - base_min_opportunity_score: floor for a favorable tape (default 65)
      - max_min_opportunity_score: ceiling for a severe risk-off tape (default 92)
      - mild_change_pct / severe_change_pct: SPY intraday % anchors for scaling
      - mild_below_vwap_pct / severe_below_vwap_pct: SPY-vs-VWAP anchors
      - vwap_weight / change_weight / low_break_weight: composite weighting
      - low_break_lookback_bars: how many bars back for the "broke recent low" check
    """
    cfg = cfg or {}
    base_floor = float(cfg.get("base_min_opportunity_score", 65) or 65)
    max_floor = float(cfg.get("max_min_opportunity_score", 92) or 92)
    # SPY change anchors: 0% = no penalty, severe = full penalty
    mild_change = float(cfg.get("mild_change_pct", -0.20) or -0.20)        # -0.2%
    severe_change = float(cfg.get("severe_change_pct", -1.20) or -1.20)    # -1.2%
    mild_vwap = float(cfg.get("mild_below_vwap_pct", -0.05) or -0.05)      # -0.05%
    severe_vwap = float(cfg.get("severe_below_vwap_pct", -0.50) or -0.50)  # -0.5%
    w_change = float(cfg.get("change_weight", 0.50) or 0.50)
    w_vwap = float(cfg.get("vwap_weight", 0.35) or 0.35)
    w_low = float(cfg.get("low_break_weight", 0.15) or 0.15)
    low_break_lookback = int(cfg.get("low_break_lookback_bars", 6) or 6)
    mild_label_cutoff = float(cfg.get("mild_label_cutoff", 0.20) or 0.20)
    strong_label_cutoff = float(cfg.get("strong_label_cutoff", 0.55) or 0.55)

    notes: list[str] = []

    if spy_intraday is None or (hasattr(spy_intraday, "empty") and spy_intraday.empty):
        notes.append("spy_intraday_unavailable")
        return TapeSignal(
            spy_intraday_change_pct=0.0,
            spy_vs_vwap_pct=0.0,
            spy_intraday_low_break_pct=0.0,
            tape_badness=0.0,
            min_opportunity_score_floor=base_floor,
            severity_label="favorable",
            notes=notes,
            has_data=False,
        )

    today = _filter_today(spy_intraday)
    if today is None or today.empty or len(today) < 2:
        notes.append("insufficient_intraday_bars")
        return TapeSignal(
            spy_intraday_change_pct=0.0,
            spy_vs_vwap_pct=0.0,
            spy_intraday_low_break_pct=0.0,
            tape_badness=0.0,
            min_opportunity_score_floor=base_floor,
            severity_label="favorable",
            notes=notes,
            has_data=False,
        )

    try:
        open_px = float(today["open"].iloc[0])
        last_px = float(today["close"].iloc[-1])
    except Exception as e:
        log.warning("tape: open/close read failed: %s", e)
        return TapeSignal(0.0, 0.0, 0.0, 0.0, base_floor, "favorable", ["read_error"], False)

    spy_change_pct = ((last_px / open_px) - 1.0) * 100.0 if open_px > 0 else 0.0
    vwap = _vwap(today)
    spy_vs_vwap_pct = ((last_px / vwap) - 1.0) * 100.0 if vwap and vwap > 0 else 0.0

    # Low-break check: how far below the prior N-bar rolling low is the latest close
    low_break_pct = 0.0
    if len(today) >= low_break_lookback + 1:
        try:
            prior_low = float(today["low"].iloc[-(low_break_lookback + 1):-1].min())
            if prior_low > 0:
                low_break_pct = min(0.0, ((last_px / prior_low) - 1.0) * 100.0)
        except Exception:
            low_break_pct = 0.0

    # Component scores: 0 (favorable) → 1 (severe). Clamp into [0,1].
    def _scale(value: float, mild: float, severe: float) -> float:
        # value, mild, severe are negative in risk-off (e.g. -0.5, -0.05, -0.5)
        if severe == mild:
            return 0.0
        if value >= mild:
            return 0.0
        if value <= severe:
            return 1.0
        return (mild - value) / (mild - severe)

    change_score = _scale(spy_change_pct, mild_change, severe_change)
    vwap_score = _scale(spy_vs_vwap_pct, mild_vwap, severe_vwap)
    low_score = _scale(low_break_pct, -0.05, -0.40)

    badness = (
        change_score * w_change
        + vwap_score * w_vwap
        + low_score * w_low
    )
    badness = max(0.0, min(1.0, badness))

    floor = base_floor + badness * (max_floor - base_floor)
    floor = max(base_floor, min(max_floor, floor))

    if badness >= strong_label_cutoff:
        label = "strong_risk_off"
    elif badness >= mild_label_cutoff:
        label = "mild_risk_off"
    elif badness > 0.05:
        label = "neutral"
    else:
        label = "favorable"

    if change_score > 0:
        notes.append(f"spy_intraday_red:{spy_change_pct:+.2f}%")
    if vwap_score > 0:
        notes.append(f"below_vwap:{spy_vs_vwap_pct:+.3f}%")
    if low_score > 0:
        notes.append(f"broke_recent_low:{low_break_pct:+.2f}%")

    return TapeSignal(
        spy_intraday_change_pct=spy_change_pct / 100.0,  # store as fraction
        spy_vs_vwap_pct=spy_vs_vwap_pct / 100.0,
        spy_intraday_low_break_pct=low_break_pct / 100.0,
        tape_badness=badness,
        min_opportunity_score_floor=floor,
        severity_label=label,
        notes=notes,
        has_data=True,
    )


def sector_tape_adjustment(
    base_signal: TapeSignal,
    candidate_sector: str | None,
    sector_regime: dict[str, Any] | None,
    cfg: dict[str, Any] | None = None,
) -> tuple[float, dict[str, Any]]:
    """Return (effective_floor, audit). Adjusts the SPY-based opportunity-score
    floor by the candidate sector's intraday relative strength vs SPY.

    A tech candidate on a -1.8% XLK / -0.4% SPY day sees a *higher* floor
    than a healthcare candidate on the same day. This is the fix for the
    2026-05-12 failure mode where every candidate saw the same SPY-only
    tape regardless of sector.
    """
    cfg = cfg or {}
    base_floor = float(base_signal.min_opportunity_score_floor)
    if not candidate_sector or not sector_regime:
        return base_floor, {"reason": "no_sector_data", "floor": base_floor}
    snapshots = sector_regime.get("snapshots") or []
    target = None
    for snap in snapshots:
        if str(snap.get("sector_name", "")).strip().lower() == str(candidate_sector).strip().lower():
            target = snap
            break
    if target is None:
        return base_floor, {"reason": "sector_etf_not_found", "floor": base_floor}
    rs = float(target.get("intraday_rs_vs_spy", 0.0) or 0.0)
    # Convert RS pct to additional floor points. -0.5% rs -> +5 floor; +0.5% rs -> -5 floor.
    # Clamp the adjustment so a 2% divergence doesn't blow the floor past max.
    adjust = max(-10.0, min(20.0, -rs * 1000.0))
    effective = max(0.0, base_floor + adjust)
    return effective, {
        "candidate_sector": candidate_sector,
        "sector_etf": target.get("symbol"),
        "intraday_rs_vs_spy_pct": round(rs, 4),
        "floor_adjustment_points": round(adjust, 2),
        "effective_floor": round(effective, 1),
        "base_floor": round(base_floor, 1),
    }
