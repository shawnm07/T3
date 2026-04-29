"""Tests for src.api_keys.KeyPool rotation + persistence."""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import api_keys
from src.api_keys import KeyPool


def _isolated_state(tmp_path):
    """Patch the state file location to a temp dir for each test."""
    return patch.object(api_keys, "_STATE_FILE", tmp_path / "pool.json"), \
        patch.object(api_keys, "_STATE_DIR", tmp_path)


def test_acquire_rotates_through_keys(tmp_path):
    p1, p2 = _isolated_state(tmp_path)
    with p1, p2:
        pool = KeyPool("test", ["a", "b", "c"])
        seen = [pool.acquire() for _ in range(6)]
        # Round-robin order, all keys used.
        assert seen == ["a", "b", "c", "a", "b", "c"]


def test_throttled_key_is_skipped(tmp_path):
    p1, p2 = _isolated_state(tmp_path)
    with p1, p2:
        pool = KeyPool("test", ["a", "b", "c"])
        pool.acquire()  # cursor=1
        pool.mark_throttled("b")
        # Next two acquires should yield 'c' then 'a' (skipping b).
        # Since cursor is now at 1 (=b), acquire skips b → c.
        assert pool.acquire() == "c"
        assert pool.acquire() == "a"


def test_dead_key_never_returned(tmp_path):
    p1, p2 = _isolated_state(tmp_path)
    with p1, p2:
        pool = KeyPool("test", ["a", "b"])
        pool.mark_dead("a")
        for _ in range(5):
            assert pool.acquire() == "b"


def test_all_throttled_returns_none(tmp_path):
    p1, p2 = _isolated_state(tmp_path)
    with p1, p2:
        pool = KeyPool("test", ["a", "b"])
        pool.mark_throttled("a")
        pool.mark_throttled("b")
        assert pool.acquire() is None
        assert pool.has_keys() is False


def test_state_persists_across_instances(tmp_path):
    p1, p2 = _isolated_state(tmp_path)
    with p1, p2:
        pool = KeyPool("test", ["a", "b"])
        pool.mark_throttled("a")
        # New instance reads the same state file.
        pool2 = KeyPool("test", ["a", "b"])
        assert pool2.acquire() == "b"
        assert pool2.acquire() == "b"  # 'a' still throttled


def test_cooldown_expires(tmp_path):
    p1, p2 = _isolated_state(tmp_path)
    with p1, p2:
        pool = KeyPool("test", ["a"], cooldown_sec=0.05)
        pool.mark_throttled("a")
        assert pool.acquire() is None
        time.sleep(0.1)
        assert pool.acquire() == "a"


def test_from_env_singular_fallback(tmp_path):
    p1, p2 = _isolated_state(tmp_path)
    with p1, p2, patch.dict(os.environ, {
        "TEST_PLURAL": "",
        "TEST_SINGULAR": "legacy_key",
    }, clear=False):
        pool = KeyPool.from_env("t", "TEST_PLURAL", singular_env="TEST_SINGULAR")
        assert pool.acquire() == "legacy_key"


def test_from_env_plural_takes_precedence(tmp_path):
    p1, p2 = _isolated_state(tmp_path)
    with p1, p2, patch.dict(os.environ, {
        "TEST_PLURAL": "k1,k2",
        "TEST_SINGULAR": "legacy",
    }, clear=False):
        pool = KeyPool.from_env("t2", "TEST_PLURAL", singular_env="TEST_SINGULAR")
        assert {pool.acquire(), pool.acquire()} == {"k1", "k2"}
