import sys
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.macro import MacroSignal
from src.orchestrator import TradingOrchestrator


class _Config:
    def get(self, *_keys, default=None):
        return default


class _Client:
    def get_account(self):
        return SimpleNamespace(cash=1000, buying_power=1000)

    def get_positions(self):
        return [
            SimpleNamespace(
                symbol="spy",
                qty="107.2313",
                market_value="77600",
                avg_entry_price="700",
                current_price="723.7",
                unrealized_pl="0",
                unrealized_plpc="0",
            )
        ]

    def get_stock_bars(self, *_args, **_kwargs):
        raise RuntimeError("skip bars")

    def get_stock_quote(self, _symbol):
        return SimpleNamespace(ask_price=723.7, bid_price=723.6)


def _orchestrator():
    orch = TradingOrchestrator.__new__(TradingOrchestrator)
    orch.cfg = _Config()
    orch.client = _Client()
    orch.risk = SimpleNamespace(
        max_position_pct=0.5,
        max_sector_pct=0.3,
        max_positions=6,
        cash_reserve_pct=0.2,
        cash_reserve_min_pct=0.1,
        high_conviction_threshold=0.75,
    )
    orch.cash_proxy_enabled = True
    orch.cash_proxy_symbol = "SPY"
    orch.cash_proxy_min = 500
    orch.rebalance_use_ai_arbiter = True
    orch._fetch_intraday = lambda *_args, **_kwargs: None
    return orch


def test_cash_proxy_symbol_case_insensitive():
    orch = _orchestrator()

    assert orch._is_cash_proxy("spy")
    assert orch._is_cash_proxy(" SPY ")


def test_spy_block_uses_snapshot_positions_when_holdings_exclude_cash_proxy():
    orch = _orchestrator()
    macro = MacroSignal("neutral", 0, 0.1, 0.02, None, "normal", None, [])

    ctx = orch._build_arbiter_context(
        holdings=[],
        tech_map={},
        sent_map={},
        numeric={},
        earnings_map={},
        macro=macro,
        equity=100_000,
    )

    assert ctx["spy_block"]["held"] is True
    assert ctx["spy_block"]["qty"] == 107.2313
    assert ctx["spy_block"]["current_value_usd"] == 77600.0


if __name__ == "__main__":
    test_cash_proxy_symbol_case_insensitive()
    test_spy_block_uses_snapshot_positions_when_holdings_exclude_cash_proxy()
    print("cash proxy context tests passed")
