"""Atomic JSON-backed state for the trailing-stop bot.

State shape (one entry per held symbol):

    {
      "AAPL": {
        "avg_fill": 187.42,
        "peak": 195.10,
        "last_stop_id": "abc-123",
        "last_stop_price": 193.15,
        "last_update": "2026-05-05T14:35:00-04:00",
        "first_seen": "2026-05-04T10:02:00-04:00",
        "synthetic_stop_id": null
      }
    }
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class StopState:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self._data = {}
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                self._data = {str(k).upper(): dict(v) for k, v in raw.items() if isinstance(v, dict)}
            else:
                self._data = {}
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def save(self) -> None:
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=".trailing_stops_", suffix=".tmp", dir=str(self.path.parent),
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, sort_keys=True)
            os.replace(tmp_path, self.path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def get(self, symbol: str) -> dict:
        return dict(self._data.get(str(symbol).upper(), {}))

    def upsert(
        self,
        symbol: str,
        *,
        avg_fill: float,
        peak: float,
        last_stop_id: str | None,
        last_stop_price: float | None,
        synthetic_stop_id: str | None = None,
    ) -> None:
        sym = str(symbol).upper()
        existing = self._data.get(sym, {})
        first_seen = existing.get("first_seen") or _now_iso()
        self._data[sym] = {
            "avg_fill": float(avg_fill),
            "peak": float(peak),
            "last_stop_id": last_stop_id,
            "last_stop_price": (float(last_stop_price) if last_stop_price is not None else None),
            "synthetic_stop_id": synthetic_stop_id,
            "first_seen": first_seen,
            "last_update": _now_iso(),
        }

    def prune(self, keep_symbols: Iterable[str]) -> list[str]:
        keep = {str(s).upper() for s in keep_symbols}
        removed = [s for s in self._data if s not in keep]
        for s in removed:
            del self._data[s]
        return removed

    def all_symbols(self) -> list[str]:
        return list(self._data.keys())

    def as_dict(self) -> dict[str, dict]:
        return {k: dict(v) for k, v in self._data.items()}
