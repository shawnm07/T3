"""Earnings calendar lookups with a disk cache.

Fetches next earnings date via yfinance and caches per-symbol on disk so we
don't hammer the network on every scan. Cache entry TTL is configurable
(default 24h). Failures degrade gracefully to None — the bot should never
block on an earnings lookup.
"""
from __future__ import annotations
import csv
import io
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import requests

try:
    import yfinance as yf
except ImportError:
    yf = None

log = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "state"
CACHE_FILE = CACHE_DIR / "earnings_cache.json"


@dataclass(frozen=True)
class EarningsInfo:
    symbol: str
    next_date: str | None          # ISO yyyy-mm-dd
    days_until: int | None         # calendar days, negative = past
    time_of_day: str | None = None # bmo|amc|dmh|unknown when known
    source: str | None = None

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "next_earnings_date": self.next_date,
            "days_until_earnings": self.days_until,
            "time_of_day": self.time_of_day,
            "source": self.source,
        }


def _load_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except OSError as e:
        log.warning("earnings cache save failed: %s", e)


def _normalize_time_of_day(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    raw = str(value).strip().lower()
    if raw in {"bmo", "before", "before market", "before_market", "premarket"}:
        return "bmo"
    if raw in {"amc", "after", "after market", "after_market", "postmarket"}:
        return "amc"
    if raw in {"dmh", "during", "during market", "during_market"}:
        return "dmh"
    if raw in {"unknown", "none", "n/a", "na"}:
        return "unknown"
    return raw


def _infer_time_of_day(value) -> str | None:
    """Infer earnings timing from a timestamp-like value when available."""
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return None
    try:
        dt = value
        if not isinstance(dt, datetime):
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        # yfinance often supplies exchange-local timestamps. We only need a
        # coarse bucket: before open, after close, or during market hours.
        hour = int(dt.hour)
        minute = int(dt.minute)
        if hour < 12:
            return "bmo"
        if hour > 15 or (hour == 15 and minute >= 45):
            return "amc"
        return "dmh"
    except Exception:
        return None


def _extract_next_event(ticker) -> tuple[str | None, str | None]:
    """Pull the next upcoming earnings date and coarse timing from yfinance.

    Prefers `earnings_dates` (future rows) and falls back to `calendar`.
    Returns ``(ISO yyyy-mm-dd, time_of_day)`` where time_of_day is one of
    ``bmo|amc|dmh|unknown`` when it can be inferred.
    """
    today = date.today()

    try:
        ed = ticker.earnings_dates
        if ed is not None and not ed.empty:
            idx = ed.index
            future = [d for d in idx if d.date() >= today]
            if future:
                nxt = min(future)
                return nxt.date().isoformat(), _infer_time_of_day(nxt)
    except Exception:
        pass

    try:
        cal = ticker.calendar
        if cal is not None:
            if hasattr(cal, "get"):
                val = cal.get("Earnings Date") or cal.get("earnings_date")
                if isinstance(val, list) and val:
                    d = val[0]
                    if hasattr(d, "isoformat"):
                        dd = d.date() if hasattr(d, "date") else d
                        return (dd.isoformat(), _infer_time_of_day(d)) if dd >= today else (None, None)
                elif hasattr(val, "isoformat"):
                    dd = val.date() if hasattr(val, "date") else val
                    return (dd.isoformat(), _infer_time_of_day(val)) if dd >= today else (None, None)
            elif hasattr(cal, "loc"):
                row = cal.loc["Earnings Date"] if "Earnings Date" in cal.index else None
                if row is not None:
                    d = row.iloc[0] if hasattr(row, "iloc") else row
                    raw = d
                    if hasattr(d, "date"):
                        d = d.date()
                    if hasattr(d, "isoformat") and d >= today:
                        return d.isoformat(), _infer_time_of_day(raw)
    except Exception:
        pass

    return None, None


def _extract_next_date(ticker) -> str | None:
    next_date, _time_of_day = _extract_next_event(ticker)
    return next_date


def fetch_earnings(symbol: str, ttl_hours: float = 24) -> EarningsInfo:
    """Return EarningsInfo for symbol, using disk cache. Never raises."""
    if not symbol or "/" in symbol:
        return EarningsInfo(symbol=symbol, next_date=None, days_until=None)

    cache = _load_cache()
    entry = cache.get(symbol)
    now = time.time()
    if entry and (now - entry.get("fetched_at", 0)) < ttl_hours * 3600:
        return _build_info(
            symbol,
            entry.get("next_date"),
            time_of_day=entry.get("time_of_day"),
            source=entry.get("source"),
        )

    next_date: str | None = None
    time_of_day: str | None = None
    source: str | None = None
    if yf is not None:
        try:
            t = yf.Ticker(symbol.replace(".", "-"))
            next_date, time_of_day = _extract_next_event(t)
            source = "yfinance"
        except Exception as e:
            log.debug("yfinance earnings lookup for %s failed: %s", symbol, e)

    cache[symbol] = {
        "next_date": next_date,
        "time_of_day": _normalize_time_of_day(time_of_day),
        "source": source,
        "fetched_at": now,
    }
    _save_cache(cache)
    return _build_info(symbol, next_date, time_of_day=time_of_day, source=source)


def _build_info(
    symbol: str,
    next_date: str | None,
    *,
    time_of_day: str | None = None,
    source: str | None = None,
) -> EarningsInfo:
    if not next_date:
        return EarningsInfo(
            symbol=symbol, next_date=None, days_until=None,
            time_of_day=_normalize_time_of_day(time_of_day),
            source=source,
        )
    try:
        d = datetime.fromisoformat(next_date).date()
    except ValueError:
        return EarningsInfo(
            symbol=symbol, next_date=None, days_until=None,
            time_of_day=_normalize_time_of_day(time_of_day),
            source=source,
        )
    delta = (d - date.today()).days
    return EarningsInfo(
        symbol=symbol,
        next_date=next_date,
        days_until=delta,
        time_of_day=_normalize_time_of_day(time_of_day) or "unknown",
        source=source,
    )


def batch_earnings(symbols: list[str], ttl_hours: float = 24) -> dict[str, EarningsInfo]:
    return {s: fetch_earnings(s, ttl_hours=ttl_hours) for s in symbols}


def within_window(info: EarningsInfo, days: int) -> bool:
    """True if earnings is within `days` calendar days in the future (inclusive)."""
    if info.days_until is None:
        return False
    return 0 <= info.days_until <= days


# --------------------------------------------------------------------------- #
#  Phase 7 (2026-05-07): earnings research score                              #
# --------------------------------------------------------------------------- #

RESEARCH_CACHE_FILE = CACHE_DIR / "earnings_research_cache.json"
RESEARCH_WEIGHTS = {
    "beat_history": 0.40,
    "pt_trend": 0.30,
    "implied_move": 0.20,
    "sentiment": 0.10,
}


def _load_research_cache() -> dict:
    if not RESEARCH_CACHE_FILE.exists():
        return {}
    try:
        return json.loads(RESEARCH_CACHE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_research_cache(cache: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        RESEARCH_CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except OSError as e:
        log.warning("earnings research cache save failed: %s", e)


def _research_payload_from_components(components: dict[str, float | None]) -> dict:
    available = [k for k, v in components.items() if v is not None]
    if not available:
        score = 0.0
    else:
        weight_sum = sum(RESEARCH_WEIGHTS[k] for k in available)
        score = sum(
            RESEARCH_WEIGHTS[k] * float(components[k] or 0)
            for k in available
        ) / max(weight_sum, 1e-6)
    return {
        "score": round(score, 3),
        "components": {
            k: round(v, 3) if v is not None else None
            for k, v in components.items()
        },
        "available_components": available,
    }


def _beat_history_score(ticker) -> float | None:
    """Ratio of last-N quarters where actualEarnings > estimatedEarnings,
    rescaled to [-1, +1]. Returns None when history unavailable.
    """
    try:
        eh = getattr(ticker, "earnings_history", None)
        if eh is None or (hasattr(eh, "empty") and eh.empty):
            return None
        # yfinance earnings_history columns vary by version; try common names.
        actual_col = None
        est_col = None
        for c in eh.columns:
            cl = str(c).lower()
            if cl in {"epsactual", "actualearnings", "epsactualeps"}:
                actual_col = c
            elif cl in {"epsestimate", "estimatedearnings", "epsestimateeps"}:
                est_col = c
        if actual_col is None or est_col is None:
            return None
        recent = eh.tail(8)
        beats = 0
        total = 0
        for _, row in recent.iterrows():
            a = row.get(actual_col)
            e = row.get(est_col)
            if a is None or e is None:
                continue
            try:
                if float(a) > float(e):
                    beats += 1
                total += 1
            except (TypeError, ValueError):
                continue
        if total == 0:
            return None
        # rescale [0,1] beat-rate to [-1,+1]
        return 2.0 * (beats / total) - 1.0
    except Exception:
        return None


def _analyst_pt_trend_score(ticker) -> float | None:
    """% change in mean target price over the last 30 days, tanh-scaled.
    Returns None when targets unavailable.
    """
    try:
        info = getattr(ticker, "info", None)
        if not info:
            return None
        cur = info.get("targetMeanPrice") or info.get("targetMedianPrice")
        prev = info.get("targetMeanPriceChange") or None
        # Most yfinance versions don't expose a PT delta directly, so we
        # approximate using current mean vs current price as a heuristic
        # when no time-series is available.
        if cur is None:
            return None
        cur = float(cur or 0)
        spot = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0)
        if cur <= 0 or spot <= 0:
            return None
        upside = (cur - spot) / spot
        # tanh-scale: ±10% upside maps to ±0.76, ±20% to ±0.96.
        import math
        return math.tanh(upside * 5.0)
    except Exception:
        return None


def _implied_move_score(ticker) -> float | None:
    """Implied move from front-week ATM straddle / spot. Positive = tight
    (cheap volatility, low binary risk premium); negative = wide (event
    priced as risky). Returns None when options unavailable.
    """
    try:
        opts = getattr(ticker, "options", None)
        if not opts:
            return None
        expiry = opts[0]
        chain = ticker.option_chain(expiry)
        info = getattr(ticker, "info", None) or {}
        spot = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0)
        if spot <= 0:
            return None
        # Find ATM call+put
        calls = chain.calls
        puts = chain.puts
        call = calls.iloc[(calls["strike"] - spot).abs().argsort()].iloc[0]
        put = puts.iloc[(puts["strike"] - spot).abs().argsort()].iloc[0]
        straddle = float(call.get("lastPrice") or 0) + float(put.get("lastPrice") or 0)
        if straddle <= 0:
            return None
        implied_pct = straddle / spot
        # 3% implied move ~ neutral; <2% strongly bullish setup; >5% expensive.
        # Map to roughly [-1, +1]: pos when implied small, neg when large.
        return max(-1.0, min(1.0, (0.03 - implied_pct) / 0.03))
    except Exception:
        return None


def compute_earnings_research_score(
    symbol: str,
    sentiment_score: float | None = None,
    ttl_hours: float = 12,
) -> dict:
    """Phase 7 (2026-05-07): research score blending pre-earnings signals.

    Returns a dict with components and the blended score in [-1, +1].
    Weights: 0.40 beat_history, 0.30 pt_trend, 0.20 implied_move, 0.10 sentiment.
    Components default to 0.0 when None (so a single missing input doesn't
    null the whole score). The dict has key "available_components" listing
    which inputs were real.
    """
    if not symbol or "/" in symbol:
        return {"score": 0.0, "components": {}, "available_components": []}
    cache = _load_research_cache()
    entry = cache.get(symbol)
    now = time.time()
    if entry and (now - entry.get("fetched_at", 0)) < ttl_hours * 3600:
        payload = entry.get("payload") or {"score": 0.0, "components": {}, "available_components": []}
        if sentiment_score is not None:
            components = dict(payload.get("components") or {})
            for key in RESEARCH_WEIGHTS:
                components.setdefault(key, None)
            components["sentiment"] = float(sentiment_score)
            return _research_payload_from_components(components)
        return payload

    components: dict[str, float | None] = {
        "beat_history": None,
        "pt_trend": None,
        "implied_move": None,
        "sentiment": (
            float(sentiment_score) if sentiment_score is not None else None
        ),
    }
    if yf is not None:
        try:
            t = yf.Ticker(symbol.replace(".", "-"))
            components["beat_history"] = _beat_history_score(t)
            components["pt_trend"] = _analyst_pt_trend_score(t)
            components["implied_move"] = _implied_move_score(t)
        except Exception as e:
            log.debug("earnings research lookup for %s failed: %s", symbol, e)

    payload = _research_payload_from_components(components)
    cache[symbol] = {"fetched_at": now, "payload": payload}
    _save_research_cache(cache)
    return payload


# --------------------------------------------------------------------------- #
#  Phase 7b (2026-05-07): earnings calendar discovery source                  #
# --------------------------------------------------------------------------- #

CALENDAR_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache" / "av" / "earnings_calendar"
AV_QUERY_URL = "https://www.alphavantage.co/query"


def _alpha_vantage_key() -> str:
    key = os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    if key:
        return key
    keys = os.environ.get("ALPHA_VANTAGE_API_KEYS", "")
    for item in keys.split(","):
        item = item.strip()
        if item:
            return item
    return ""


def _calendar_cache_path(today: date, window_days: int, horizon: str) -> Path:
    safe_horizon = str(horizon or "3month").replace("/", "_")
    return CALENDAR_CACHE_DIR / f"{today.isoformat()}_{window_days}d_{safe_horizon}.json"


def _parse_report_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).strip()).date()
    except ValueError:
        return None


def _fetch_av_earnings_calendar(window_days: int, horizon: str) -> list[dict] | None:
    """Fetch Alpha Vantage's full-market earnings calendar CSV.

    Official AV docs note that ``EARNINGS_CALENDAR`` returns CSV and, when
    called without ``symbol``, returns the full scheduled calendar. The CSV
    does not provide BMO/AMC timing, so per-symbol yfinance timing remains the
    higher-fidelity source when the bot evaluates a concrete ticker.
    """
    api_key = _alpha_vantage_key()
    if not api_key:
        return None
    try:
        resp = requests.get(
            AV_QUERY_URL,
            params={
                "function": "EARNINGS_CALENDAR",
                "horizon": horizon,
                "apikey": api_key,
            },
            timeout=20,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.warning("Alpha Vantage earnings calendar fetch failed: %s", exc)
        return None

    text = resp.text or ""
    if "Thank you for using Alpha Vantage" in text or "Our standard API rate limit" in text:
        log.warning("Alpha Vantage earnings calendar throttled")
        return None
    if text.lstrip().startswith("{"):
        try:
            payload = json.loads(text)
            if payload.get("Note") or payload.get("Information") or payload.get("Error Message"):
                log.warning("Alpha Vantage earnings calendar error: %s", str(payload)[:180])
                return None
        except json.JSONDecodeError:
            return None

    today = date.today()
    out: list[dict] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        sym = str(row.get("symbol") or row.get("Symbol") or "").strip().upper()
        report_date = _parse_report_date(row.get("reportDate") or row.get("report_date"))
        if not sym or report_date is None:
            continue
        days_until = (report_date - today).days
        if days_until < 0 or days_until > window_days:
            continue
        out.append({
            "symbol": sym,
            "name": row.get("name") or row.get("Name"),
            "report_date": report_date.isoformat(),
            "days_until": days_until,
            "time_of_day": None,
            "fiscal_date_ending": row.get("fiscalDateEnding") or row.get("fiscal_date_ending"),
            "estimate": row.get("estimate"),
            "currency": row.get("currency"),
            "source": "alpha_vantage",
        })
    out.sort(key=lambda r: (int(r.get("days_until") or 0), str(r.get("symbol") or "")))
    return out


def _fetch_seeded_yfinance_calendar(window_days: int) -> list[dict]:
    """Fallback calendar using symbols already present in the earnings cache."""
    out: list[dict] = []
    earnings_cache = _load_cache()
    seeds = list(earnings_cache.keys())
    seen: set[str] = set()
    for sym in seeds:
        if sym in seen:
            continue
        seen.add(sym)
        info = fetch_earnings(sym, ttl_hours=24)
        if info.next_date is None or info.days_until is None:
            continue
        if 0 <= info.days_until <= window_days:
            out.append({
                "symbol": sym,
                "report_date": info.next_date,
                "days_until": info.days_until,
                "time_of_day": info.time_of_day,
                "source": "yfinance_seeded_cache",
            })
    return out


def fetch_upcoming_earnings_calendar(window_days: int = 2, horizon: str = "3month") -> list[dict]:
    """Return symbols reporting within ``window_days`` calendar days.

    Primary source is Alpha Vantage's full-market ``EARNINGS_CALENDAR`` CSV.
    If AV is unavailable or throttled, fall back to yfinance lookups for the
    existing earnings cache. Cached daily under
    ``data/cache/av/earnings_calendar/YYYY-MM-DD_<window>d_<horizon>.json``.
    """
    today = date.today()
    cache_path = _calendar_cache_path(today, window_days, horizon)
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    out = _fetch_av_earnings_calendar(window_days, horizon) or []
    if not out:
        out = _fetch_seeded_yfinance_calendar(window_days)
    try:
        CALENDAR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(out, indent=2))
    except OSError as e:
        log.warning("earnings calendar cache save failed: %s", e)
    return out


# --------------------------------------------------------------------------- #
#  Phase 8: preclose earnings entry profile                                   #
# --------------------------------------------------------------------------- #


def classify_earnings_timing(
    info: EarningsInfo | None,
    *,
    unknown_time_is_event_risk: bool = True,
) -> dict:
    """Classify whether the next overnight crosses an earnings event.

    The distinction matters:
    - day 0 AMC and day 1 BMO cross the binary event before the next open.
    - day 0 BMO is already post-earnings by the preclose run and can be a
      post-earnings-drift setup instead of a blind pre-event gamble.
    """
    if info is None or info.days_until is None:
        return {
            "days_until_earnings": None,
            "time_of_day": None,
            "event_risk_overnight": False,
            "post_earnings_session": False,
            "timing_class": "none",
        }
    days = int(info.days_until)
    tod = _normalize_time_of_day(info.time_of_day) or "unknown"
    event_risk = False
    post_session = False
    timing_class = "future"

    if days < 0:
        timing_class = "past"
    elif days == 0:
        if tod in {"bmo", "dmh"}:
            post_session = True
            timing_class = "post_earnings_same_day"
        else:
            event_risk = tod == "amc" or (tod == "unknown" and unknown_time_is_event_risk)
            timing_class = "tonight_event" if event_risk else "same_day_unknown"
    elif days == 1:
        event_risk = tod == "bmo" or (tod == "unknown" and unknown_time_is_event_risk)
        timing_class = "tomorrow_bmo_event" if event_risk else "tomorrow_after_close"
    else:
        timing_class = "future"

    return {
        "days_until_earnings": days,
        "time_of_day": tod,
        "event_risk_overnight": bool(event_risk),
        "post_earnings_session": bool(post_session),
        "timing_class": timing_class,
    }


def build_preclose_earnings_profile(
    info: EarningsInfo | None,
    research: dict | None,
    *,
    sentiment_score: float | None = None,
    catalyst_source: bool = False,
    lookahead_days: int = 1,
    min_sentiment: float = 0.05,
    min_research_score: float = 0.25,
    neutral_research_score: float = 0.0,
    event_risk_buy_threshold: float = 0.65,
    post_earnings_buy_threshold: float = 0.50,
    non_event_buy_threshold: float = 0.58,
    event_risk_size_multiplier: float = 0.30,
    post_earnings_size_multiplier: float = 0.50,
    unknown_time_is_event_risk: bool = True,
) -> dict:
    """Research-gated profile for new preclose entries near earnings.

    This is deliberately a gate/profile, not an order decision. The caller
    still requires the overnight edge threshold, AI entry arbiter approval, and
    risk sizing. The profile tells that caller whether an earnings-adjacent
    setup is crossing the event before next open, and whether the research is
    strong enough to justify carrying that event risk.
    """
    timing = classify_earnings_timing(
        info,
        unknown_time_is_event_risk=unknown_time_is_event_risk,
    )
    days_until = timing.get("days_until_earnings")
    research = research or {"score": 0.0, "components": {}, "available_components": []}
    try:
        research_score = float(research.get("score") or 0.0)
    except (TypeError, ValueError):
        research_score = 0.0
    try:
        sent = float(sentiment_score) if sentiment_score is not None else 0.0
    except (TypeError, ValueError):
        sent = 0.0
    sentiment_ok = sent >= float(min_sentiment)
    active_catalyst = bool(catalyst_source or sentiment_ok)
    near = bool(days_until is not None and 0 <= int(days_until) <= int(lookahead_days))

    reasons: list[str] = []
    entry_allowed = True
    threshold_floor: float | None = None
    size_multiplier: float | None = None
    score_adjustment = 0.0

    if not near:
        reasons.append("outside_preclose_earnings_window")
    elif timing.get("event_risk_overnight"):
        threshold_floor = float(event_risk_buy_threshold)
        size_multiplier = float(event_risk_size_multiplier)
        entry_allowed = bool(active_catalyst and research_score >= float(min_research_score))
        score_adjustment = max(
            -0.14,
            min(0.10, 0.12 * research_score - 0.06 + (0.03 if sentiment_ok else 0.0)),
        )
        reasons.append("overnight_crosses_earnings_event")
        if not active_catalyst:
            reasons.append("missing_live_catalyst_source_or_sentiment")
        if research_score < float(min_research_score):
            reasons.append("research_score_below_event_minimum")
    elif timing.get("post_earnings_session"):
        threshold_floor = float(post_earnings_buy_threshold)
        size_multiplier = float(post_earnings_size_multiplier)
        entry_allowed = bool(active_catalyst or research_score >= float(neutral_research_score))
        score_adjustment = max(
            -0.04,
            min(0.14, 0.08 * max(research_score, 0.0) + (0.04 if sentiment_ok else 0.0)),
        )
        reasons.append("post_earnings_same_day_drift_candidate")
    else:
        threshold_floor = float(non_event_buy_threshold)
        entry_allowed = bool(active_catalyst or research_score >= float(min_research_score))
        score_adjustment = max(-0.06, min(0.08, 0.06 * research_score))
        reasons.append("near_earnings_but_not_overnight_event")
        if not entry_allowed:
            reasons.append("no_catalyst_or_research_edge")

    return {
        **timing,
        "near_earnings": near,
        "entry_allowed": bool(entry_allowed),
        "research_score": round(research_score, 3),
        "research": research,
        "sentiment_score": round(sent, 3),
        "sentiment_ok": bool(sentiment_ok),
        "catalyst_source": bool(catalyst_source),
        "active_catalyst": bool(active_catalyst),
        "threshold_floor": threshold_floor,
        "size_multiplier": size_multiplier,
        "score_adjustment": round(score_adjustment, 3),
        "reasons": reasons,
    }
