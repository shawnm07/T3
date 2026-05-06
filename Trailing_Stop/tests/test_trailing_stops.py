"""Unit tests for Trailing_Stop pure-functions and state.

Run: py -m pytest Trailing_Stop/tests/ -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from Trailing_Stop.state import StopState
from Trailing_Stop.trailing_stops import compute_trail_pct, desired_stop_price


# ---------- compute_trail_pct ----------

def test_trail_pct_at_zero_gain():
    assert compute_trail_pct(0.0) == pytest.approx(2.0)


def test_trail_pct_at_5pct_gain():
    # Linear: 2.0 -> 0.5 over 0..10% gain. At 5% -> 1.25.
    assert compute_trail_pct(0.05) == pytest.approx(1.25)


def test_trail_pct_at_10pct_gain_floor():
    assert compute_trail_pct(0.10) == pytest.approx(0.5)


def test_trail_pct_above_10pct_clamped():
    assert compute_trail_pct(0.15) == pytest.approx(0.5)
    assert compute_trail_pct(1.00) == pytest.approx(0.5)


def test_trail_pct_negative_gain_treated_as_zero():
    assert compute_trail_pct(-0.05) == pytest.approx(2.0)


# ---------- desired_stop_price ----------

def test_desired_stop_at_breakeven():
    # peak == fill -> 2% below fill.
    assert desired_stop_price(10.0, 10.0) == pytest.approx(9.80)


def test_desired_stop_5pct_above_fill():
    # peak 10.50, gain 5%, trail 1.25%, stop = 10.50 * 0.9875 = 10.36875 -> 10.37
    assert desired_stop_price(10.0, 10.50) == pytest.approx(10.37)


def test_desired_stop_10pct_above_fill_converged():
    # peak 11.0, gain 10%, trail 0.5%, stop = 11 * 0.995 = 10.945 -> 10.95
    assert desired_stop_price(10.0, 11.0) == pytest.approx(10.95)


def test_desired_stop_20pct_above_fill_clamped():
    # peak 12.0, trail 0.5%, stop = 12 * 0.995 = 11.94
    assert desired_stop_price(10.0, 12.0) == pytest.approx(11.94)


def test_desired_stop_below_fill_uses_floor():
    # peak 10.0 (no gain) — trail (10 * 0.98 = 9.80) ties floor (9.80). Both equal.
    # If peak were lower than fill (impossible with our logic), floor must win.
    assert desired_stop_price(10.0, 9.50) == pytest.approx(9.80)


def test_desired_stop_zero_avg_fill():
    assert desired_stop_price(0.0, 10.0) == 0.0


# ---------- StopState ----------

def test_state_round_trip(tmp_path):
    p = tmp_path / "state.json"
    s = StopState(p)
    s.upsert("AAPL", avg_fill=187.42, peak=195.10, last_stop_id="abc",
             last_stop_price=193.15)
    s.save()

    s2 = StopState(p)
    entry = s2.get("AAPL")
    assert entry["avg_fill"] == pytest.approx(187.42)
    assert entry["peak"] == pytest.approx(195.10)
    assert entry["last_stop_id"] == "abc"
    assert entry["last_stop_price"] == pytest.approx(193.15)
    assert "first_seen" in entry
    assert "last_update" in entry


def test_state_atomic_write_no_partial(tmp_path):
    p = tmp_path / "state.json"
    s = StopState(p)
    s.upsert("AAPL", avg_fill=100.0, peak=100.0, last_stop_id="x", last_stop_price=98.0)
    s.save()
    # Confirm only the final file exists, no .tmp leftovers.
    leftover = list(tmp_path.glob(".trailing_stops_*.tmp"))
    assert leftover == []
    raw = json.loads(p.read_text())
    assert "AAPL" in raw


def test_state_prune(tmp_path):
    p = tmp_path / "state.json"
    s = StopState(p)
    s.upsert("AAPL", avg_fill=100.0, peak=100.0, last_stop_id="a", last_stop_price=98.0)
    s.upsert("MSFT", avg_fill=300.0, peak=300.0, last_stop_id="b", last_stop_price=294.0)
    removed = s.prune(["AAPL"])
    assert removed == ["MSFT"]
    assert s.all_symbols() == ["AAPL"]


def test_state_first_seen_preserved(tmp_path):
    p = tmp_path / "state.json"
    s = StopState(p)
    s.upsert("AAPL", avg_fill=100.0, peak=100.0, last_stop_id="x", last_stop_price=98.0)
    first = s.get("AAPL")["first_seen"]
    s.upsert("AAPL", avg_fill=100.0, peak=105.0, last_stop_id="y", last_stop_price=102.0)
    assert s.get("AAPL")["first_seen"] == first
    assert s.get("AAPL")["peak"] == pytest.approx(105.0)


def test_state_load_corrupt_file(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{not valid json")
    s = StopState(p)
    assert s.all_symbols() == []
