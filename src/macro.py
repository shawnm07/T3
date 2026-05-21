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
    # 2026-05-12 overhaul: sector-rotation awareness.
    sector_regime: dict[str, Any] | None = None

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
            "sector_regime": self.sector_regime,
        }


def _build_sector_regime_via_client(client: AlpacaClient, cfg: Any = None) -> dict[str, Any] | None:
    """Build a sector_regime dict using the AlpacaClient as the bar source.

    Treated as best-effort: any failure returns None and the macro signal
    proceeds without sector data (degraded but functional).
    """
    if cfg is None:
        return None
    try:
        if not bool(cfg.get("sector_rotation", "enabled", default=False)):
            return None
        from src.sector_etfs import (
            SectorSnapshot,
            compute_sector_regime,
            _save_cached,
        )
    except Exception:
        return None
    etfs_map = cfg.get("sector_rotation", "etfs", default={}) or {}
    if not etfs_map:
        return None
    symbols = list(etfs_map.keys()) + ["SPY"]
    try:
        bars = client.get_stock_bars(symbols, lookback_days=30)
    except Exception as e:
        log.info("sector_etfs bar fetch failed: %s", e)
        return None
    try:
        spy_df = bars.xs("SPY", level="symbol") if "symbol" in bars.index.names else bars
        spy_open = float(spy_df["close"].iloc[-2]) if len(spy_df) >= 2 else 0.0
        spy_last = float(spy_df["close"].iloc[-1]) if len(spy_df) else 0.0
        spy_intra = (spy_last / spy_open - 1.0) if spy_open else 0.0
    except Exception:
        spy_intra = 0.0
    snaps: list = []
    for sym, sector_name in etfs_map.items():
        try:
            df = bars.xs(sym, level="symbol")
            if len(df) < 2:
                continue
            close = df["close"]
            last = float(close.iloc[-1])
            prev = float(close.iloc[-2])
            def _ret(n: int) -> float:
                if len(close) > n:
                    base = float(close.iloc[-(n + 1)])
                    return (last / base - 1.0) if base else 0.0
                return 0.0
            intra = (last / prev - 1.0) if prev else 0.0
            snaps.append(SectorSnapshot(
                symbol=sym,
                sector_name=str(sector_name),
                price=last,
                ret_1d=_ret(1),
                ret_5d=_ret(5),
                ret_20d=_ret(20),
                intraday_change_pct=intra,
                intraday_rs_vs_spy=intra - spy_intra,
            ))
        except Exception:
            continue
    if not snaps:
        return None
    regime = compute_sector_regime(cfg, snaps)
    try:
        _save_cached(cfg, {"snapshots": [s.to_dict() for s in snaps]})
    except Exception:
        pass
    return regime.to_dict()


def compute_macro(
    client: AlpacaClient,
    breadth_symbols: list[str] | None = None,
    cfg: Any = None,
) -> MacroSignal:
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

    sector_regime: dict[str, Any] | None = None
    try:
        sector_regime = _build_sector_regime_via_client(client, cfg=cfg)
        if sector_regime:
            notes.append(
                f"sector_regime={sector_regime.get('rotation_regime', '?')}_"
                f"leading={','.join(sector_regime.get('leading') or [])}"
            )
            # Sector rotation can attenuate the headline macro score: a
            # technically-flat market that is rotating defensives→leadership
            # should not read as cleanly "risk-on". Subtract up to 0.10 when
            # cyclicals are clearly lagging.
            if sector_regime.get("cyclicals_lagging") and sector_regime.get("defensives_leading"):
                score = max(-1.0, score - 0.10)
                if score > 0.35:
                    regime = "risk_on"
                elif score < -0.35:
                    regime = "risk_off"
                else:
                    regime = "neutral"
                notes.append("defensive_rotation_attenuation")
    except Exception as e:
        log.info("sector_regime computation skipped: %s", e)
        sector_regime = None

    return MacroSignal(
        regime=regime,
        score=score,
        spy_trend=float(spy_trend),
        spy_vs_200ema=float(spy_vs_200),
        vix_level=vix_level,
        vix_regime=vix_regime,
        breadth_pct_above_50=breadth_pct,
        notes=notes,
        sector_regime=sector_regime,
    )
