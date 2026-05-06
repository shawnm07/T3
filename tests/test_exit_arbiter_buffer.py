"""Phase 4: 30-min exit confirmation buffer + reduce-path partial sell."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.orchestrator import TradingOrchestrator


class _FakeCfg:
    def __init__(self, kv):
        self._kv = dict(kv)

    def get(self, *path, default=None):
        return self._kv.get(path, default)


def _orch(tmp_path: Path, overrides: dict | None = None) -> TradingOrchestrator:
    base = {
        ("selector", "fresh_exit_cooldown_minutes"): 120,
        ("portfolio_verifier", "fresh_entry_loss_floor_pct"): -0.005,
        ("exit_arbiter", "confirmation_buffer_enabled"): True,
        ("exit_arbiter", "confirmation_minutes"): 30,
        ("exit_arbiter", "confirmation_buffer_loss_floor_pct"): -0.015,
        ("exit_arbiter", "reduce_trim_fraction"): 0.5,
        ("macro", "bearish_halt_score"): -0.55,
    }
    if overrides:
        base.update(overrides)
    cfg = _FakeCfg(base)
    o = TradingOrchestrator.__new__(TradingOrchestrator)
    o.cfg = cfg
    # Patch the buffer path into a tmp dir so tests don't share state.
    state_file = tmp_path / "exit_signal_buffer.json"
    o._exit_confirmation_buffer_path = lambda: state_file
    return o


def test_first_signal_records_and_skips(tmp_path):
    o = _orch(tmp_path)
    macro = SimpleNamespace(score=0.1)

    decision = o._exit_confirmation_buffer_check(
        symbol="PWR", macro=macro, triggers={}, plpc=0.005,
    )
    assert decision == "skip", "first exit signal should ask for confirmation"

    state = json.loads((tmp_path / "exit_signal_buffer.json").read_text())
    assert "PWR" in state
    assert "first_signal_ts" in state["PWR"]


def test_second_signal_within_window_still_skips(tmp_path):
    o = _orch(tmp_path)
    macro = SimpleNamespace(score=0.1)

    # Pre-populate with a 5-minute-old signal.
    five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    (tmp_path / "exit_signal_buffer.json").write_text(json.dumps({
        "PWR": {"first_signal_ts": five_min_ago.isoformat(), "plpc_at_signal": 0.003},
    }))

    decision = o._exit_confirmation_buffer_check(
        symbol="PWR", macro=macro, triggers={}, plpc=0.004,
    )
    assert decision == "skip", "still inside the 30-min buffer"


def test_second_signal_after_window_proceeds(tmp_path):
    o = _orch(tmp_path)
    macro = SimpleNamespace(score=0.1)

    forty_min_ago = datetime.now(timezone.utc) - timedelta(minutes=40)
    (tmp_path / "exit_signal_buffer.json").write_text(json.dumps({
        "PWR": {"first_signal_ts": forty_min_ago.isoformat(), "plpc_at_signal": 0.003},
    }))

    decision = o._exit_confirmation_buffer_check(
        symbol="PWR", macro=macro, triggers={}, plpc=0.001,
    )
    assert decision == "proceed", "buffer window expired — exit confirmed"


def test_macro_halt_bypasses_buffer(tmp_path):
    o = _orch(tmp_path)
    bear_macro = SimpleNamespace(score=-0.7)  # below -0.55 halt floor

    decision = o._exit_confirmation_buffer_check(
        symbol="ANY", macro=bear_macro, triggers={}, plpc=0.0,
    )
    assert decision == "proceed", "macro halt overrides the buffer"


def test_stop_loss_breach_bypasses_buffer(tmp_path):
    o = _orch(tmp_path)
    macro = SimpleNamespace(score=0.0)
    decision = o._exit_confirmation_buffer_check(
        symbol="ANY", macro=macro,
        triggers={"stop_loss_breach": True},
        plpc=-0.012,
    )
    assert decision == "proceed", "deterministic stop breach bypasses buffer"


def test_earnings_window_bypasses_buffer(tmp_path):
    o = _orch(tmp_path)
    macro = SimpleNamespace(score=0.0)
    decision = o._exit_confirmation_buffer_check(
        symbol="ANY", macro=macro,
        triggers={"earnings_window": True},
        plpc=0.0,
    )
    assert decision == "proceed"


def test_material_loss_bypasses_buffer(tmp_path):
    """If the position is already underwater more than 1.5%, don't make
    the user wait another 30 min before cutting it."""
    o = _orch(tmp_path)
    macro = SimpleNamespace(score=0.0)
    decision = o._exit_confirmation_buffer_check(
        symbol="ANY", macro=macro, triggers={}, plpc=-0.020,
    )
    assert decision == "proceed", "material loss should bypass buffer"


def test_buffer_can_be_disabled(tmp_path):
    o = _orch(tmp_path, overrides={
        ("exit_arbiter", "confirmation_buffer_enabled"): False,
    })
    macro = SimpleNamespace(score=0.0)
    decision = o._exit_confirmation_buffer_check(
        symbol="ANY", macro=macro, triggers={}, plpc=0.0,
    )
    assert decision == "proceed", "buffer disabled → no holdup"


def test_clear_buffer_removes_record(tmp_path):
    o = _orch(tmp_path)
    macro = SimpleNamespace(score=0.0)
    o._exit_confirmation_buffer_check(symbol="MU", macro=macro, triggers={}, plpc=0.0)
    assert "MU" in json.loads((tmp_path / "exit_signal_buffer.json").read_text())
    o._exit_confirmation_buffer_clear("MU")
    assert "MU" not in json.loads((tmp_path / "exit_signal_buffer.json").read_text())


def test_reduce_path_trims_50_percent_by_default(tmp_path):
    """Phase 4b: AI says reduce -> partial sell at the configured fraction."""
    o = _orch(tmp_path)
    o.executor = MagicMock()
    o.executor.execute_ai_qty_delta.return_value = SimpleNamespace(
        ok=True, final_status="filled",
    )

    pos = SimpleNamespace(symbol="PWR", qty=14.0, current_price=766.0)
    o._handle_exit_arbiter_reduce(pos, plpc=0.01, conf=0.7, reasoning="momentum fading")

    o.executor.execute_ai_qty_delta.assert_called_once()
    call = o.executor.execute_ai_qty_delta.call_args
    # Whole-share rounded for sub-$10+ stock: 14 * 0.5 = 7.0 → -7.0
    delta = call.kwargs.get("delta_qty")
    assert delta == -7.0, f"expected -7.0 share trim, got {delta}"


def test_reduce_path_no_op_on_zero_qty(tmp_path):
    o = _orch(tmp_path)
    o.executor = MagicMock()
    pos = SimpleNamespace(symbol="ANY", qty=0.0, current_price=100.0)
    o._handle_exit_arbiter_reduce(pos, plpc=0.0, conf=0.7, reasoning="")
    o.executor.execute_ai_qty_delta.assert_not_called()
