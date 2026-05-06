"""Phase 1b: verifier dust-sweep skips same-day fresh entries that aren't
materially in the red."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.orchestrator import TradingOrchestrator


class _FakeCfg:
    def __init__(self, kv):
        self._kv = dict(kv)

    def get(self, *path, default=None):
        return self._kv.get(path, default)


def _make_orchestrator(monkeypatch):
    """Build a minimally-stubbed orchestrator with the lifecycle helper
    available — we only test the guard method, not the full pipeline."""
    cfg = _FakeCfg({
        ("selector", "fresh_exit_cooldown_minutes"): 120,
        ("portfolio_verifier", "fresh_entry_loss_floor_pct"): -0.005,
    })
    orch = TradingOrchestrator.__new__(TradingOrchestrator)
    orch.cfg = cfg
    return orch


def test_blocks_dust_sweep_for_fresh_winning_position(monkeypatch, tmp_path):
    orch = _make_orchestrator(monkeypatch)
    now = datetime.now(timezone.utc)
    ten_min_ago = now - timedelta(minutes=10)

    state = {
        "AAPL": {
            "entry_ts": ten_min_ago.isoformat(),
            "source": "[selector] rebalance",
            "filled_qty": 42.0,
            "filled_avg_price": 282.5,
            "ai_action": "BUY",
        }
    }
    monkeypatch.setattr(orch, "_load_position_lifecycle", lambda: state)

    pos = SimpleNamespace(symbol="AAPL", qty=42.0, unrealized_plpc=0.005)  # +0.5%

    blocked = orch._verifier_dust_sweep_blocked_fresh(
        "AAPL", pos, loss_floor_pct=-0.005,
    )
    assert blocked is True, "fresh winning entry should be protected"


def test_allows_dust_sweep_for_fresh_losing_position(monkeypatch):
    orch = _make_orchestrator(monkeypatch)
    now = datetime.now(timezone.utc)
    ten_min_ago = now - timedelta(minutes=10)

    state = {
        "WDC": {
            "entry_ts": ten_min_ago.isoformat(),
            "ai_action": "BUY",
        }
    }
    monkeypatch.setattr(orch, "_load_position_lifecycle", lambda: state)

    pos = SimpleNamespace(symbol="WDC", qty=23.0, unrealized_plpc=-0.012)  # -1.2%

    blocked = orch._verifier_dust_sweep_blocked_fresh(
        "WDC", pos, loss_floor_pct=-0.005,
    )
    assert blocked is False, "fresh losing entry should NOT be protected"


def test_allows_dust_sweep_for_old_position(monkeypatch):
    orch = _make_orchestrator(monkeypatch)
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)

    state = {
        "INTC": {
            "entry_ts": yesterday.isoformat(),
            "ai_action": "BUY",
        }
    }
    monkeypatch.setattr(orch, "_load_position_lifecycle", lambda: state)

    pos = SimpleNamespace(symbol="INTC", qty=272.0, unrealized_plpc=0.008)

    blocked = orch._verifier_dust_sweep_blocked_fresh(
        "INTC", pos, loss_floor_pct=-0.005,
    )
    assert blocked is False, "yesterday's position is not 'fresh today'"


def test_allows_dust_sweep_when_no_lifecycle_record(monkeypatch):
    orch = _make_orchestrator(monkeypatch)
    monkeypatch.setattr(orch, "_load_position_lifecycle", lambda: {})

    pos = SimpleNamespace(symbol="AMZN", qty=29.0, unrealized_plpc=0.01)

    blocked = orch._verifier_dust_sweep_blocked_fresh(
        "AMZN", pos, loss_floor_pct=-0.005,
    )
    assert blocked is False, "missing lifecycle = no protection (legacy / external)"


def test_loss_floor_threshold_is_inclusive(monkeypatch):
    """plpc exactly at the floor should NOT be protected (let the loss cut)."""
    orch = _make_orchestrator(monkeypatch)
    now = datetime.now(timezone.utc)

    state = {
        "MU": {
            "entry_ts": (now - timedelta(minutes=5)).isoformat(),
            "ai_action": "BUY",
        }
    }
    monkeypatch.setattr(orch, "_load_position_lifecycle", lambda: state)

    # Exactly at floor.
    pos = SimpleNamespace(symbol="MU", qty=18.0, unrealized_plpc=-0.005)
    blocked = orch._verifier_dust_sweep_blocked_fresh(
        "MU", pos, loss_floor_pct=-0.005,
    )
    assert blocked is False, "at-the-floor losses are not protected"
