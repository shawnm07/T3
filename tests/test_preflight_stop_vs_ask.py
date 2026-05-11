"""Regression: preflight stop validity uses ask, not bid-ask midpoint.

Before 2026-05-11 the preflight compared the protective stop against the
bid-ask midpoint. On wide-spread breakout names (bid $287 / ask $295 for BE),
a stop that was 1.25% below the actual fill price (ask) could sit fractionally
above the midpoint and get rejected — killing the entire allocation. The
check now uses ask (for buys) and auto-tightens marginally-stale stops so
the buy ships and the trailing-stop bot widens later from the real fill.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import yaml

from src.config import Config, AlpacaConfig
from src.executor import TradeExecutor


def _make_executor(quote_bid: float, quote_ask: float) -> TradeExecutor:
    with open("config.yaml", "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    cfg = Config(AlpacaConfig("", "", "", "", "paper"), raw)
    client = MagicMock()
    client.get_stock_quote.return_value = SimpleNamespace(
        bid_price=quote_bid, ask_price=quote_ask, price=None,
    )
    ex = TradeExecutor(client, cfg)
    # Bypass complex asset normalization + protective-stop machinery so the
    # test can focus on the quote-comparison branch.
    ex._normalize_buy_qty_for_asset = lambda symbol, qty: (qty, {"symbol": symbol, "submitted_qty": qty})
    ex._protective_stop_loss_price = lambda entry, stop, atr=None: (float(stop), "ai_volatility_stop")
    ex._take_profit_or_none = lambda target, entry: float(target) if target else None
    return ex


def test_preflight_uses_ask_for_buy_stop_comparison():
    # BE 09:22: bid 287, ask 295, mid 291. Selector stop 291.30 is 1.25% below
    # ask but ~0.10% above mid. Must pass on the ask-based comparison.
    ex = _make_executor(quote_bid=287.0, quote_ask=295.0)
    ok, audit = ex.preflight_buy(
        symbol="BE", qty=109.62, entry_price=294.81,
        stop_loss=291.30, take_profit=324.29,
    )
    assert ok, f"BE should preflight-approve with ask-based stop check, audit={audit}"
    assert audit["current_price_reference_source"] == "ask"
    assert audit["current_price_reference"] == 295.0
    assert audit.get("status") == "approved"


def test_preflight_auto_tightens_stop_well_above_ask():
    # Stop $300 is ~1.7% above ask $295: well beyond the 0.2% slack band.
    # Auto-tighten should fire under the "loud" audit bucket.
    ex = _make_executor(quote_bid=287.0, quote_ask=295.0)
    ok, audit = ex.preflight_buy(
        symbol="BE", qty=10, entry_price=298.0,
        stop_loss=300.0, take_profit=324.29,
    )
    assert ok, f"auto-tighten should rescue this buy, audit={audit}"
    assert audit.get("stop_auto_tightened") is not None
    tightened = audit["stop_auto_tightened"]
    assert tightened["from"] == 300.0
    assert tightened["to"] < 295.0
    assert audit["stop_price"] == tightened["to"]
    # Loud bucket — well outside slack tolerance.
    assert "stop_within_slack_tighten" not in audit


def test_preflight_slack_tolerance_swallows_small_overshoot():
    # Stop $295.10 sits $0.10 ABOVE ask $295 (0.034% — well within 0.2%
    # slack default). Should still ship the buy, but log it in the quieter
    # "within slack" bucket rather than the loud "auto_tightened" one.
    ex = _make_executor(quote_bid=287.0, quote_ask=295.0)
    ok, audit = ex.preflight_buy(
        symbol="BE", qty=10, entry_price=295.0,
        stop_loss=295.10, take_profit=324.29,
    )
    assert ok, f"slack tolerance should swallow this, audit={audit}"
    assert audit.get("stop_within_slack_tighten") is not None
    assert audit.get("stop_auto_tightened") is None  # not the loud bucket
    assert audit["stop_price"] < 295.0
    assert audit["stop_slack_pct"] == 0.002


def test_preflight_gap_scales_with_bid_ask_spread():
    # Wide spread ($287 / $295 = $8 spread). The gap should be at least
    # half the spread ($4.00), not the tiny static gap ($0.295). Without
    # this, the tightened stop sits too close to the ask and gets re-hit
    # by spread noise.
    ex = _make_executor(quote_bid=287.0, quote_ask=295.0)
    ok, audit = ex.preflight_buy(
        symbol="BE", qty=10, entry_price=298.0,
        stop_loss=300.0, take_profit=324.29,
    )
    assert ok
    assert audit.get("half_spread") == 4.0
    # gap should equal max(static, half_spread) = 4.0
    assert audit["min_stop_gap"] == 4.0
    tightened_to = audit["stop_auto_tightened"]["to"]
    # tightened = ref - gap*1.5 = 295 - 6 = 289. Well clear of spread noise.
    assert tightened_to <= 289.5


def test_preflight_skips_quote_check_when_quote_unavailable():
    # No quote (e.g., extended hours, broker hiccup) — preflight should
    # approve based on selector inputs alone rather than rejecting.
    ex = _make_executor(quote_bid=0, quote_ask=0)
    ex._quote_midpoint = staticmethod(lambda _quote: (None, {}))
    ok, audit = ex.preflight_buy(
        symbol="BE", qty=10, entry_price=294.81,
        stop_loss=291.30, take_profit=324.29,
    )
    assert ok
    assert audit.get("status") == "approved"
