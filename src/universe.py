"""Trading universe construction: S&P 500 + custom watchlist."""
from __future__ import annotations
import io
import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests

from src.config import Config

log = logging.getLogger(__name__)

CACHE = Path(__file__).resolve().parents[1] / "data" / "cache" / "sp500.csv"
R1000_CACHE = Path(__file__).resolve().parents[1] / "data" / "cache" / "russell1000.csv"
SP500_WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
SP500_DATAHUB = "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv"
IWB_HOLDINGS = (
    "https://www.ishares.com/us/products/239707/ishares-russell-1000-etf/"
    "1467271812596.ajax?fileType=csv&fileName=IWB_holdings&dataType=fund"
)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def _fetch_from_wiki() -> pd.DataFrame:
    r = requests.get(SP500_WIKI, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    df = tables[0][["Symbol", "GICS Sector", "GICS Sub-Industry"]].copy()
    df.columns = ["symbol", "sector", "sub_industry"]
    # Alpaca uses dot notation for class shares (BRK.B). Keep as-is.
    df["symbol"] = df["symbol"].astype(str).str.strip()
    return df


def _fetch_from_datahub() -> pd.DataFrame:
    r = requests.get(SP500_DATAHUB, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    cols = {c.lower(): c for c in df.columns}
    sym = cols.get("symbol", "Symbol")
    sec = cols.get("sector", cols.get("gics sector", "Sector"))
    df = df[[sym, sec]].rename(columns={sym: "symbol", sec: "sector"})
    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["sub_industry"] = ""
    return df


def to_yfinance_symbol(symbol: str) -> str:
    """yfinance uses dashes (BRK-B), Alpaca uses dots (BRK.B)."""
    return symbol.replace(".", "-")


@lru_cache(maxsize=1)
def sp500_tickers() -> list[str]:
    if CACHE.exists() and (pd.Timestamp.now() - pd.Timestamp.fromtimestamp(CACHE.stat().st_mtime)).days < 7:
        df = pd.read_csv(CACHE)
        return df["symbol"].tolist()
    df = None
    for fetcher, name in [(_fetch_from_wiki, "wiki"), (_fetch_from_datahub, "datahub")]:
        try:
            df = fetcher()
            log.info("Fetched S&P 500 from %s: %d rows", name, len(df))
            break
        except Exception as e:
            log.warning("S&P 500 fetch via %s failed: %s", name, e)
    if df is None:
        if CACHE.exists():
            log.warning("All fetches failed, using stale cache")
            df = pd.read_csv(CACHE)
        else:
            raise RuntimeError("Could not obtain S&P 500 list from any source")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CACHE, index=False)
    return df["symbol"].tolist()


def sp500_sectors() -> dict[str, str]:
    sp500_tickers()  # ensure cache
    df = pd.read_csv(CACHE)
    return dict(zip(df["symbol"], df["sector"]))


@lru_cache(maxsize=1)
def russell1000_tickers() -> list[str]:
    """Fetch Russell 1000 from iShares IWB holdings CSV. Cached 7 days."""
    if R1000_CACHE.exists() and (pd.Timestamp.now() - pd.Timestamp.fromtimestamp(R1000_CACHE.stat().st_mtime)).days < 7:
        df = pd.read_csv(R1000_CACHE)
        return df["symbol"].tolist()
    try:
        r = requests.get(IWB_HOLDINGS, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        text = r.text
        lines = text.splitlines()
        header_idx = next(
            (i for i, ln in enumerate(lines) if ln.lower().startswith("ticker,")),
            None,
        )
        if header_idx is None:
            raise RuntimeError("IWB CSV: no 'Ticker' header row")
        df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])))
        sym_col = next((c for c in df.columns if c.strip().lower() == "ticker"), None)
        asset_col = next((c for c in df.columns if "asset class" in c.strip().lower()), None)
        if sym_col is None:
            raise RuntimeError("IWB CSV: no ticker column")
        if asset_col:
            df = df[df[asset_col].astype(str).str.lower().str.contains("equity", na=False)]
        df["symbol"] = df[sym_col].astype(str).str.strip()
        # Drop cash/derivative placeholders, convert dashes back to dots for Alpaca (BRK-B -> BRK.B)
        df = df[df["symbol"].str.match(r"^[A-Z][A-Z0-9\.\-]*$")]
        df["symbol"] = df["symbol"].str.replace("-", ".", regex=False)
        df = df[["symbol"]].drop_duplicates()
        R1000_CACHE.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(R1000_CACHE, index=False)
        log.info("Fetched Russell 1000 from iShares IWB: %d rows", len(df))
        return df["symbol"].tolist()
    except Exception as e:
        log.warning("Russell 1000 fetch failed: %s", e)
        if R1000_CACHE.exists():
            log.warning("Falling back to stale Russell 1000 cache")
            return pd.read_csv(R1000_CACHE)["symbol"].tolist()
        log.warning("No Russell 1000 cache; falling back to S&P 500 only")
        return []


def build_stock_universe(config: Config) -> list[str]:
    tickers: list[str] = []
    if config.get("universe", "include_russell_1000", default=False):
        r1k = russell1000_tickers()
        tickers.extend(r1k)
        if not r1k and config.get("universe", "include_sp500", default=True):
            tickers.extend(sp500_tickers())
    elif config.get("universe", "include_sp500", default=True):
        tickers.extend(sp500_tickers())
    watchlist = config.get("universe", "custom_watchlist", default=[]) or []
    tickers.extend(watchlist)
    excluded = set(config.get("universe", "exclude_tickers", default=[]) or [])
    deduped = []
    seen = set()
    for t in tickers:
        if t in excluded or t in seen:
            continue
        seen.add(t)
        deduped.append(t)
    return deduped
