"""Fundamentals via yfinance: quality + valuation + growth → [-1, 1] score."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

try:
    import yfinance as yf
except ImportError:
    yf = None

log = logging.getLogger(__name__)


@dataclass
class FundamentalSignal:
    symbol: str
    score: float
    pe: float | None
    peg: float | None
    rev_growth: float | None
    earnings_growth: float | None
    roe: float | None
    debt_to_equity: float | None
    market_cap: float | None
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "score": round(self.score, 3),
            "pe": self.pe,
            "peg": self.peg,
            "rev_growth": self.rev_growth,
            "earnings_growth": self.earnings_growth,
            "roe": self.roe,
            "debt_to_equity": self.debt_to_equity,
            "market_cap": self.market_cap,
            "notes": self.notes,
        }


def _safe(d: dict, key: str) -> float | None:
    v = d.get(key)
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return None
    return float(v)


def compute_fundamentals(symbol: str) -> FundamentalSignal | None:
    if yf is None:
        return None
    yf_sym = symbol.replace(".", "-")
    try:
        info = yf.Ticker(yf_sym).info
    except Exception as e:
        log.warning("yfinance fetch failed for %s: %s", symbol, e)
        return None
    if not info or "symbol" not in info:
        return None

    pe = _safe(info, "trailingPE")
    fpe = _safe(info, "forwardPE")
    peg = _safe(info, "pegRatio") or _safe(info, "trailingPegRatio")
    rev_g = _safe(info, "revenueGrowth")
    earn_g = _safe(info, "earningsGrowth") or _safe(info, "earningsQuarterlyGrowth")
    roe = _safe(info, "returnOnEquity")
    d2e = _safe(info, "debtToEquity")
    mcap = _safe(info, "marketCap")

    notes: list[str] = []
    parts: list[float] = []

    # Valuation: lower PE (reasonable) is positive
    if pe is not None and pe > 0:
        if pe < 15: parts.append(0.6); notes.append("cheap_pe")
        elif pe < 25: parts.append(0.2)
        elif pe < 40: parts.append(-0.1)
        else: parts.append(-0.5); notes.append("expensive_pe")
    # PEG: <1 is attractive
    if peg is not None and peg > 0:
        if peg < 1: parts.append(0.5); notes.append("peg_attractive")
        elif peg < 2: parts.append(0.1)
        else: parts.append(-0.3)
    # Revenue growth
    if rev_g is not None:
        parts.append(float(np.tanh(rev_g * 2.5)))
        if rev_g > 0.20: notes.append("high_rev_growth")
        elif rev_g < 0: notes.append("rev_declining")
    # Earnings growth
    if earn_g is not None:
        parts.append(float(np.tanh(earn_g * 1.5)))
    # ROE quality
    if roe is not None:
        parts.append(float(np.tanh((roe - 0.10) * 5)))
        if roe > 0.25: notes.append("high_roe")
    # Leverage penalty
    if d2e is not None:
        d2e_unit = d2e / 100 if d2e > 5 else d2e  # yfinance inconsistency
        parts.append(float(-np.tanh((d2e_unit - 1) * 0.8)))
        if d2e_unit > 2: notes.append("high_leverage")

    score = float(np.mean(parts)) if parts else 0.0
    score = max(-1.0, min(1.0, score))

    return FundamentalSignal(
        symbol=symbol, score=score,
        pe=pe, peg=peg, rev_growth=rev_g, earnings_growth=earn_g,
        roe=roe, debt_to_equity=d2e, market_cap=mcap, notes=notes,
    )


def batch_fundamentals(symbols: list[str]) -> dict[str, FundamentalSignal]:
    out: dict[str, FundamentalSignal] = {}
    for s in symbols:
        sig = compute_fundamentals(s)
        if sig:
            out[s] = sig
    return out
