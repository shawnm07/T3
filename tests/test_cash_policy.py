from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.cash_policy import (
    build_selector_cash_policy_decision,
    fallback_cash_policy_decision,
    resolve_active_cash_policy,
    save_cash_policy,
    sweep_cash_to_proxy_if_allowed,
)


class _Cfg:
    def __init__(self, raw):
        self.raw = raw

    def get(self, *keys, default=None):
        node = self.raw
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node


def _cfg(tmp_path):
    return _Cfg({
        "risk": {"cash_reserve_pct": 0.05},
        "cash_proxy": {"enabled": True, "symbol": "SPY", "min_rebalance_usd": 500},
        "cash_policy": {
            "state_file": str(tmp_path / "cash_policy.json"),
            "selector_lock_minutes": 55,
            "fallback_min_hold_minutes": 30,
            "cash_preference_margin_pct": 0.03,
            "spy_badness_threshold": 0.08,
            "cash_badness_threshold": 0.20,
        },
        "trailing_stops": {
            "floor_pct": 2.0,
            "converged_pct": 0.5,
            "converge_gain_pct": 10.0,
            "extended_hours": {"tif": "gtc"},
        },
    })


def _tape(label="favorable", badness=0.0, change=0.01, vwap=0.002, has_data=True):
    return {
        "severity_label": label,
        "tape_badness": badness,
        "spy_intraday_change_pct": change,
        "spy_vs_vwap_pct": vwap,
        "has_data": has_data,
    }


def test_selector_cash_policy_locks_bearish_cash_choice(tmp_path):
    cfg = _cfg(tmp_path)
    now = datetime(2026, 5, 8, 16, 0, tzinfo=timezone.utc)
    decision = build_selector_cash_policy_decision(
        cfg,
        {
            "spy_target_pct": 0.10,
            "cash_target_pct": 0.45,
            "spy_vs_cash_reasoning": "SPY tape is risk-off, so true cash is safer.",
        },
        tape_state=_tape("mild_risk_off", 0.3, change=-0.004, vwap=-0.001),
        now=now,
    )

    assert decision["mode"] == "cash"
    assert decision["source"] == "selector"
    assert decision["lock_until"]


def test_selector_high_cash_with_constructive_spy_goes_to_spy(tmp_path):
    cfg = _cfg(tmp_path)
    decision = build_selector_cash_policy_decision(
        cfg,
        {
            "spy_target_pct": 0.05,
            "cash_target_pct": 0.40,
            "spy_vs_cash_reasoning": "No need for defensive cash; SPY is constructive.",
        },
        tape_state=_tape("favorable", 0.0),
    )

    assert decision["mode"] == "spy"


def test_locked_selector_policy_does_not_flip_five_minutes_later(tmp_path):
    cfg = _cfg(tmp_path)
    now = datetime(2026, 5, 8, 16, 0, tzinfo=timezone.utc)
    locked = build_selector_cash_policy_decision(
        cfg,
        {
            "spy_target_pct": 0.0,
            "cash_target_pct": 0.50,
            "spy_vs_cash_reasoning": "SPY is bearish; hold cash.",
        },
        tape_state=_tape("strong_risk_off", 0.7, change=-0.01, vwap=-0.005),
        now=now,
    )
    save_cash_policy(cfg, locked)

    resolved = resolve_active_cash_policy(
        cfg,
        client=None,
        tape_state=_tape("favorable", 0.0, change=0.01, vwap=0.002),
        now=now + timedelta(minutes=5),
        persist_fallback=False,
    )

    assert resolved["mode"] == "cash"
    assert resolved["active_lock_reason"] == "selector_lock"


def test_fallback_hysteresis_keeps_cash_until_spy_is_clearly_favorable(tmp_path):
    cfg = _cfg(tmp_path)
    now = datetime(2026, 5, 8, 16, 0, tzinfo=timezone.utc)
    previous = {
        "mode": "cash",
        "source": "tape_fallback",
        "updated_at": (now - timedelta(minutes=45)).isoformat(),
        "lock_until": None,
    }

    neutral = fallback_cash_policy_decision(
        cfg,
        _tape("neutral", 0.07, change=0.001, vwap=-0.001),
        previous=previous,
        now=now,
    )
    favorable = fallback_cash_policy_decision(
        cfg,
        _tape("favorable", 0.0, change=0.005, vwap=0.001),
        previous=previous,
        now=now,
    )

    assert neutral["mode"] == "cash"
    assert favorable["mode"] == "spy"


class _FakeClient:
    def __init__(self, *, cash=10_000, open_orders=None, market_open=True, filled_qty=0.0):
        self.cash = cash
        self.open_orders = open_orders or []
        self.market_open = market_open
        self.filled_qty = filled_qty
        self.submitted = []
        self.stops = []
        self.cancelled = []

    def get_clock(self):
        return SimpleNamespace(is_open=self.market_open)

    def get_account(self):
        return SimpleNamespace(cash=self.cash, equity=100_000)

    def get_open_orders(self):
        return list(self.open_orders)

    def submit_notional(self, symbol, notional, side, tif="day"):
        self.submitted.append((symbol, notional, side, tif))
        return SimpleNamespace(id="buy-1")

    def wait_for_order_fill(self, _order_id):
        return SimpleNamespace(status="filled", filled_qty=self.filled_qty), True

    def invalidate_snapshot(self):
        pass

    def get_positions_raw(self):
        return [
            SimpleNamespace(
                symbol="SPY",
                qty=10,
                avg_entry_price=700,
                current_price=710,
            )
        ]

    def submit_stop_loss(self, symbol, qty, stop_price, side="sell", tif="day", client_order_id=None):
        self.stops.append((symbol, qty, stop_price, side, tif, client_order_id))
        return SimpleNamespace(id="stop-1")

    def cancel_order(self, order_id):
        self.cancelled.append(order_id)


def test_sweep_respects_cash_policy_cash(tmp_path):
    cfg = _cfg(tmp_path)
    client = _FakeClient()

    action = sweep_cash_to_proxy_if_allowed(
        client,
        cfg,
        100_000,
        policy={"mode": "cash", "reason": "bearish SPY"},
    )

    assert action["skipped"] == "cash_policy_cash"
    assert client.submitted == []


def test_sweep_buys_spy_when_policy_allows(tmp_path):
    cfg = _cfg(tmp_path)
    client = _FakeClient(cash=12_000)

    action = sweep_cash_to_proxy_if_allowed(
        client,
        cfg,
        100_000,
        policy={"mode": "spy", "reason": "constructive SPY"},
    )

    assert action["action"] == "buy_proxy"
    assert client.submitted == [("SPY", 7000.0, "buy", "day")]
    assert client.stops


def test_sweep_rearms_stop_for_at_least_old_plus_filled_qty(tmp_path):
    cfg = _cfg(tmp_path)
    client = _FakeClient(cash=12_000, filled_qty=2.5)

    action = sweep_cash_to_proxy_if_allowed(
        client,
        cfg,
        100_000,
        policy={"mode": "spy", "reason": "constructive SPY"},
    )

    assert action["action"] == "buy_proxy"
    assert client.stops[0][1] == 12.5


def test_sweep_skips_duplicate_spy_buy_order(tmp_path):
    cfg = _cfg(tmp_path)
    order = SimpleNamespace(id="open-buy", symbol="SPY", side="buy", type="market")
    client = _FakeClient(cash=12_000, open_orders=[order])

    action = sweep_cash_to_proxy_if_allowed(
        client,
        cfg,
        100_000,
        policy={"mode": "spy", "reason": "constructive SPY"},
    )

    assert action["skipped"] == "open_proxy_buy_order"
    assert client.submitted == []


def test_sweep_skips_when_market_closed(tmp_path):
    cfg = _cfg(tmp_path)
    client = _FakeClient(cash=12_000, market_open=False)

    action = sweep_cash_to_proxy_if_allowed(
        client,
        cfg,
        100_000,
        policy={"mode": "spy", "reason": "constructive SPY"},
    )

    assert action["skipped"] == "market_closed"
    assert client.submitted == []
