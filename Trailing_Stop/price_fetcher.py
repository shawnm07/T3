"""Price fetcher with provider fallback chain: Twelve Data -> Alpha Vantage -> Alpaca.

Twelve Data supports multiple comma-separated keys via TWELVEDATA_API_KEYS for
round-robin rotation when one is rate-limited.
"""
from __future__ import annotations

import logging
import os
from typing import Callable

import requests

log = logging.getLogger(__name__)

_TIMEOUT_S = 4.0


class PriceFetcher:
    def __init__(
        self,
        *,
        td_keys: list[str] | None = None,
        av_key: str | None = None,
        alpaca_lookup: Callable[[str], float | None] | None = None,
        sources: list[str] | None = None,
    ):
        self.td_keys = [k.strip() for k in (td_keys or []) if k and k.strip()]
        self._td_idx = 0
        self.av_key = (av_key or "").strip()
        self.alpaca_lookup = alpaca_lookup
        self.sources = [s.lower() for s in (sources or ["twelve_data", "alpha_vantage", "alpaca"])]
        self._td_disabled_this_cycle: set[int] = set()

    def reset_cycle(self) -> None:
        """Re-enable all TD keys for a new cycle (called once per cycle)."""
        self._td_disabled_this_cycle.clear()

    def get_quote(self, symbol: str) -> tuple[float | None, str | None]:
        """Return (price, source_tag) — first source that succeeds wins.

        Returns (None, None) if every source fails.
        """
        sym = str(symbol).upper().strip()
        if not sym:
            return None, None
        for source in self.sources:
            try:
                if source == "twelve_data":
                    price = self._twelve_data(sym)
                    if price is not None:
                        return price, "twelve_data"
                elif source == "alpha_vantage":
                    price = self._alpha_vantage(sym)
                    if price is not None:
                        return price, "alpha_vantage"
                elif source == "alpaca":
                    price = self._alpaca(sym)
                    if price is not None:
                        return price, "alpaca"
            except Exception as exc:
                log.warning("price source %s failed for %s: %s", source, sym, exc)
        return None, None

    # --- Twelve Data ---
    def _twelve_data(self, symbol: str) -> float | None:
        if not self.td_keys:
            return None
        n = len(self.td_keys)
        for _ in range(n):
            idx = self._td_idx % n
            self._td_idx = (self._td_idx + 1) % n
            if idx in self._td_disabled_this_cycle:
                continue
            key = self.td_keys[idx]
            try:
                resp = requests.get(
                    "https://api.twelvedata.com/price",
                    params={"symbol": symbol, "apikey": key},
                    timeout=_TIMEOUT_S,
                )
            except requests.RequestException as exc:
                log.warning("Twelve Data key#%d network error for %s: %s", idx, symbol, exc)
                self._td_disabled_this_cycle.add(idx)
                continue
            if resp.status_code == 429:
                log.warning("Twelve Data key#%d rate-limited (429) for %s", idx, symbol)
                self._td_disabled_this_cycle.add(idx)
                continue
            try:
                data = resp.json()
            except ValueError:
                log.warning("Twelve Data key#%d non-JSON response for %s", idx, symbol)
                self._td_disabled_this_cycle.add(idx)
                continue
            if isinstance(data, dict) and "price" in data:
                try:
                    return float(data["price"])
                except (TypeError, ValueError):
                    return None
            # Common error envelope: {"code":429,"message":"...credits..."}
            code = data.get("code") if isinstance(data, dict) else None
            if code in (429, 401, 403):
                log.warning(
                    "Twelve Data key#%d soft-error code=%s for %s msg=%s",
                    idx, code, symbol, data.get("message", ""),
                )
                self._td_disabled_this_cycle.add(idx)
                continue
            log.warning("Twelve Data key#%d unrecognized payload for %s: %s", idx, symbol, data)
            return None
        return None

    # --- Alpha Vantage ---
    def _alpha_vantage(self, symbol: str) -> float | None:
        if not self.av_key:
            return None
        try:
            resp = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": self.av_key,
                },
                timeout=_TIMEOUT_S,
            )
        except requests.RequestException as exc:
            log.warning("Alpha Vantage network error for %s: %s", symbol, exc)
            return None
        if resp.status_code != 200:
            return None
        try:
            data = resp.json()
        except ValueError:
            return None
        quote = data.get("Global Quote") if isinstance(data, dict) else None
        if not quote:
            return None
        raw = quote.get("05. price") or quote.get("price")
        try:
            return float(raw) if raw not in (None, "") else None
        except (TypeError, ValueError):
            return None

    # --- Alpaca (last-resort) ---
    def _alpaca(self, symbol: str) -> float | None:
        if self.alpaca_lookup is None:
            return None
        try:
            value = self.alpaca_lookup(symbol)
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None


def build_default_fetcher(alpaca_lookup: Callable[[str], float | None] | None) -> PriceFetcher:
    """Construct a PriceFetcher from environment variables.

    TWELVEDATA_API_KEYS — comma-separated list of Twelve Data keys.
    ALPHA_VANTAGE_API_KEY — single Alpha Vantage key.
    """
    td_raw = os.environ.get("TWELVEDATA_API_KEYS", "") or os.environ.get("TWELVEDATA_API_KEY", "")
    td_keys = [k.strip() for k in td_raw.split(",") if k.strip()]
    av_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "")
    return PriceFetcher(td_keys=td_keys, av_key=av_key, alpaca_lookup=alpaca_lookup)
