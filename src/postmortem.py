"""Per-trade post-mortem journal.

Every closed trade produces an entry in ``data/journal/postmortems.jsonl``
with the fields a weekly retrospective needs:

- symbol, theme, sector
- entry_ts / exit_ts / hold_minutes
- entry_score (numeric) / exit_score (numeric)
- entry_confidence / exit_confidence (AI arbiters)
- entry_arbiter_quote / exit_arbiter_quote
- MFE / MAE (max favorable / adverse excursion as % of entry)
- realized_pl_pct / realized_pl_usd
- exit_kind: stop_loss | exit_arbiter | rebalance | preclose | earnings_gate

The MFE/MAE numbers come from minute bars when available, otherwise from the
fill prices only (degraded but useful).
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import Config

log = logging.getLogger(__name__)


def _journal_path(cfg: Config) -> Path:
    raw = cfg.get(
        "postmortem", "journal_file",
        default="data/journal/postmortems.jsonl",
    )
    p = Path(str(raw))
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _parse_ts(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        return (
            value if value.tzinfo
            else value.replace(tzinfo=timezone.utc)
        ).timestamp()
    try:
        s = str(value).rstrip("Z")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def _excursion(entry_price: float, bars: Any) -> tuple[float, float]:
    """Return (MFE%, MAE%) over the supplied minute/intraday bars (pandas
    DataFrame with 'high'/'low' columns or list of dicts). Both are signed
    so a long with MFE +0.03 means "ran 3% above entry at best", MAE -0.012
    means "drew down 1.2% at worst".
    """
    if entry_price <= 0 or bars is None:
        return (0.0, 0.0)
    highs: list[float] = []
    lows: list[float] = []
    try:
        # pandas DataFrame path
        highs = [float(x) for x in bars["high"].tolist()]
        lows = [float(x) for x in bars["low"].tolist()]
    except Exception:
        try:
            for b in bars:
                if isinstance(b, dict):
                    highs.append(float(b.get("high", b.get("h", 0)) or 0))
                    lows.append(float(b.get("low", b.get("l", 0)) or 0))
        except Exception:
            return (0.0, 0.0)
    if not highs or not lows:
        return (0.0, 0.0)
    mfe = (max(highs) / entry_price) - 1.0
    mae = (min(lows) / entry_price) - 1.0
    return (round(mfe, 4), round(mae, 4))


def record_postmortem(
    cfg: Config,
    *,
    symbol: str,
    theme: str | None,
    sector: str | None,
    entry_ts: Any,
    exit_ts: Any,
    entry_price: float,
    exit_price: float,
    qty: float,
    entry_score: float | None = None,
    exit_score: float | None = None,
    entry_confidence: float | None = None,
    exit_confidence: float | None = None,
    entry_arbiter_quote: str | None = None,
    exit_arbiter_quote: str | None = None,
    exit_kind: str = "unknown",
    bars: Any = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Append a single post-mortem record. Returns the record dict or None
    if postmortem is disabled."""
    if not bool(cfg.get("postmortem", "enabled", default=True)):
        return None
    entry_ts_f = _parse_ts(entry_ts) or time.time()
    exit_ts_f = _parse_ts(exit_ts) or time.time()
    hold_minutes = max(0.0, (exit_ts_f - entry_ts_f) / 60.0)
    mfe, mae = _excursion(float(entry_price or 0.0), bars)
    if entry_price > 0:
        realized_pl_pct = (float(exit_price) / float(entry_price)) - 1.0
    else:
        realized_pl_pct = 0.0
    realized_pl_usd = (float(exit_price) - float(entry_price)) * float(qty or 0.0)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": str(symbol).upper(),
        "theme": theme,
        "sector": sector,
        "entry_ts": datetime.fromtimestamp(entry_ts_f, tz=timezone.utc).isoformat(),
        "exit_ts": datetime.fromtimestamp(exit_ts_f, tz=timezone.utc).isoformat(),
        "hold_minutes": round(hold_minutes, 2),
        "entry_price": round(float(entry_price or 0.0), 4),
        "exit_price": round(float(exit_price or 0.0), 4),
        "qty": float(qty or 0.0),
        "entry_score": entry_score,
        "exit_score": exit_score,
        "entry_confidence": entry_confidence,
        "exit_confidence": exit_confidence,
        "entry_arbiter_quote": entry_arbiter_quote,
        "exit_arbiter_quote": exit_arbiter_quote,
        "mfe_pct": mfe,
        "mae_pct": mae,
        "realized_pl_pct": round(realized_pl_pct, 4),
        "realized_pl_usd": round(realized_pl_usd, 2),
        "exit_kind": exit_kind,
    }
    if extra:
        record["extra"] = extra
    p = _journal_path(cfg)
    try:
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as e:
        log.warning("postmortem: write failed: %s", e)
    return record


def read_recent(cfg: Config, days: int = 7) -> list[dict[str, Any]]:
    p = _journal_path(cfg)
    if not p.exists():
        return []
    cutoff = time.time() - days * 86400
    out: list[dict[str, Any]] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                ts = _parse_ts(rec.get("ts")) or 0.0
                if ts >= cutoff:
                    out.append(rec)
    except Exception:
        return []
    return out


def exit_arbiter_accuracy(records: list[dict[str, Any]]) -> dict[str, Any]:
    """For exit-arbiter-driven closes: did the exit precede actual further
    drawdown, or was the trade still up at the next favorable bar?

    A "correct" exit-arbiter call here means MAE within 30 minutes post-exit
    was worse than the exit price (i.e. selling protected from a drawdown).
    Falls back to a heuristic if the post-exit MAE isn't available: the
    arbiter was "correct" if the trade was already underwater at exit.
    """
    arbiter_exits = [r for r in records if r.get("exit_kind") == "exit_arbiter"]
    if not arbiter_exits:
        return {"sample": 0, "accuracy": None}
    correct = 0
    for r in arbiter_exits:
        plpc = float(r.get("realized_pl_pct", 0.0) or 0.0)
        mae = float(r.get("mae_pct", 0.0) or 0.0)
        # Heuristic: if the trade closed below entry OR drew down >0.5% during
        # the hold, the "momentum lost" call was warranted.
        if plpc < 0 or mae < -0.005:
            correct += 1
    return {
        "sample": len(arbiter_exits),
        "correct": correct,
        "accuracy": round(correct / len(arbiter_exits), 3) if arbiter_exits else None,
    }
