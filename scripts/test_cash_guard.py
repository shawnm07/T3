"""Smoke tests for selector cash gating.

Runnable directly:

    python scripts/test_cash_guard.py

No pytest dependency. Exits non-zero if any assertion fails.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.orchestrator import TradingOrchestrator  # noqa: E402


class FakeCfg:
    def __init__(self) -> None:
        self.raw = {
            "execution": {"fill_timeout_s": 0, "fill_poll_s": 0},
            "risk": {"min_trade_usd": 500},
        }

    def get(self, *path, default=None):
        cur = self.raw
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return default
            cur = cur[p]
        return cur


class FakeRisk:
    cash_reserve_pct = 0.05
    cash_reserve_min_pct = 0.02


class FakeAccount:
    def __init__(self, cash: float) -> None:
        self.cash = cash


class FakePosition:
    symbol = "SPY"
    market_value = 2960.47
    qty = 4.162178235


class FailingProxyClient:
    def __init__(self, cash: float) -> None:
        self.cash = cash
        self.close_calls = []

    def get_account(self):
        return FakeAccount(self.cash)

    def get_positions(self):
        return [FakePosition()]

    def close_position(self, symbol, qty=None, percentage=None):
        self.close_calls.append((symbol, qty, percentage))
        raise RuntimeError("insufficient qty available for order")

    def wait_for_order_fill(self, *args, **kwargs):
        return None, False

    def invalidate_snapshot(self):
        pass


def make_bot(client):
    bot = object.__new__(TradingOrchestrator)
    bot.cfg = FakeCfg()
    bot.risk = FakeRisk()
    bot.client = client
    bot.cash_proxy_enabled = True
    bot.cash_proxy_symbol = "SPY"
    bot.cash_proxy_min = 500.0
    return bot


def case_failed_proxy_sale_caps_buy_to_cash_floor():
    """Replay the 2026-04-28 failure shape: SPY funding fails, buy is capped."""
    equity = 96647.28209293477
    cash_after_confirmed_trades = 13249.00
    floor_pct = 0.05
    requested_ceco_buy = 21262.40
    bot = make_bot(FailingProxyClient(cash_after_confirmed_trades))

    allowed = bot._funded_buy_notional(
        "CECO",
        requested_ceco_buy,
        equity,
        floor_pct,
        "regression",
    )

    expected = round(cash_after_confirmed_trades - (equity * floor_pct), 2)
    assert allowed == expected, f"allowed ${allowed} != expected ${expected}"
    assert allowed < requested_ceco_buy, "buy should be capped below requested size"
    assert bot.client.close_calls, "funding should have attempted to sell SPY"
    print("[PASS] failed SPY funding caps buy to confirmed cash floor")


def case_ensure_cash_false_when_shortfall_remains():
    bot = make_bot(FailingProxyClient(1000.0))
    ok = bot._ensure_cash_for(5000.0, 100000.0, floor_pct=0.05)
    assert not ok, "ensure_cash_for must be a hard false when funding fails"
    print("[PASS] ensure_cash_for returns false after failed funding")


def main():
    cases = [
        case_failed_proxy_sale_caps_buy_to_cash_floor,
        case_ensure_cash_false_when_shortfall_remains,
    ]
    failed = 0
    for case in cases:
        try:
            case()
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {case.__name__}: {e}")
    if failed:
        print(f"\n{failed}/{len(cases)} test(s) failed")
        sys.exit(1)
    print(f"\nAll {len(cases)} tests passed")


if __name__ == "__main__":
    main()
