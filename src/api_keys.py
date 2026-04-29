"""Multi-key API rotation pool.

Free-tier API providers (Alpha Vantage 25/day, Twelve Data 800/day, etc.)
let you stack quotas by registering multiple keys. ``KeyPool`` rotates
through a list of keys, marks throttled keys as cooled-down for ~24h, and
persists state to disk so cron-fired processes share the same view.

Env var convention (comma-separated):

* ``ALPHA_VANTAGE_API_KEYS=key1,key2,key3``
* ``TWELVEDATA_API_KEYS=k1,k2``

For backwards compatibility, ``ALPHA_VANTAGE_API_KEY`` (singular) is read
as a one-element list if the plural form is absent.

Typical use:

    pool = KeyPool.from_env("alpha_vantage", "ALPHA_VANTAGE_API_KEYS",
                            singular_env="ALPHA_VANTAGE_API_KEY")
    key = pool.acquire()
    # ... call API with key ...
    if response_was_throttled:
        pool.mark_throttled(key)
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_STATE_DIR = Path(__file__).resolve().parents[1] / "data" / "state"
_STATE_FILE = _STATE_DIR / "api_key_pool.json"
_THROTTLE_COOLDOWN_SEC = 24 * 60 * 60  # AV-style daily limits reset ~24h


@dataclass
class _KeyState:
    throttled_at: float = 0.0   # unix ts; 0 = healthy
    dead: bool = False
    use_count: int = 0


class KeyPool:
    """Round-robin pool of API keys with throttle/dead tracking."""

    _lock = threading.Lock()

    def __init__(self, name: str, keys: list[str], cooldown_sec: float = _THROTTLE_COOLDOWN_SEC):
        self.name = name
        self.cooldown = cooldown_sec
        cleaned = [k.strip() for k in keys if k and k.strip()]
        self._keys: list[str] = list(dict.fromkeys(cleaned))  # dedupe, preserve order
        self._state: dict[str, _KeyState] = {k: _KeyState() for k in self._keys}
        self._cursor = 0
        self._load_state()

    @classmethod
    def from_env(cls, name: str, env_var: str, singular_env: Optional[str] = None) -> "KeyPool":
        raw = os.environ.get(env_var, "")
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        if not keys and singular_env:
            single = os.environ.get(singular_env, "").strip()
            if single:
                keys = [single]
        return cls(name=name, keys=keys)

    # ---------- public ----------
    def has_keys(self) -> bool:
        return any(self._is_healthy(k) for k in self._keys)

    def acquire(self) -> Optional[str]:
        """Return the next healthy key, or None if all are throttled/dead."""
        with self._lock:
            n = len(self._keys)
            for _ in range(n):
                k = self._keys[self._cursor % n]
                self._cursor = (self._cursor + 1) % n
                if self._is_healthy(k):
                    self._state[k].use_count += 1
                    self._save_state()
                    return k
            return None

    def mark_throttled(self, key: str) -> None:
        with self._lock:
            st = self._state.get(key)
            if st is None:
                return
            st.throttled_at = time.time()
            log.warning("[keypool:%s] key %s...%s marked throttled (cooldown %.0fh)",
                        self.name, key[:4], key[-2:], self.cooldown / 3600)
            self._save_state()

    def mark_dead(self, key: str) -> None:
        with self._lock:
            st = self._state.get(key)
            if st is None:
                return
            st.dead = True
            log.warning("[keypool:%s] key %s...%s marked dead (auth failure)",
                        self.name, key[:4], key[-2:])
            self._save_state()

    def stats(self) -> dict:
        return {
            "name": self.name,
            "total": len(self._keys),
            "healthy": sum(1 for k in self._keys if self._is_healthy(k)),
            "throttled": sum(
                1 for k in self._keys
                if self._state[k].throttled_at and not self._cooled_down(self._state[k])
            ),
            "dead": sum(1 for k in self._keys if self._state[k].dead),
        }

    # ---------- internals ----------
    def _is_healthy(self, key: str) -> bool:
        st = self._state.get(key)
        if st is None or st.dead:
            return False
        if st.throttled_at and not self._cooled_down(st):
            return False
        return True

    def _cooled_down(self, st: _KeyState) -> bool:
        if not st.throttled_at:
            return True
        return (time.time() - st.throttled_at) >= self.cooldown

    # ---------- persistence ----------
    def _load_state(self) -> None:
        try:
            if not _STATE_FILE.exists():
                return
            data = json.loads(_STATE_FILE.read_text())
            section = data.get(self.name, {})
            for k, payload in section.items():
                if k in self._state:
                    self._state[k] = _KeyState(
                        throttled_at=float(payload.get("throttled_at", 0) or 0),
                        dead=bool(payload.get("dead", False)),
                        use_count=int(payload.get("use_count", 0) or 0),
                    )
        except Exception as e:
            log.warning("[keypool:%s] load state failed: %s", self.name, e)

    def _save_state(self) -> None:
        try:
            _STATE_DIR.mkdir(parents=True, exist_ok=True)
            try:
                data = json.loads(_STATE_FILE.read_text()) if _STATE_FILE.exists() else {}
            except Exception:
                data = {}
            data[self.name] = {
                k: {"throttled_at": st.throttled_at, "dead": st.dead, "use_count": st.use_count}
                for k, st in self._state.items()
            }
            _STATE_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            log.warning("[keypool:%s] save state failed: %s", self.name, e)
