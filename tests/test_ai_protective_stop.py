from src.config import AlpacaConfig, Config
from src.risk import RiskManager


def _config() -> Config:
    return Config(
        alpaca=AlpacaConfig(
            api_key="test",
            api_secret="test",
            base_url="",
            data_url="",
            mode="paper",
        ),
        raw={
            "risk": {
                "hard_stop_loss_pct": 0.01,
                "max_risk_per_trade_pct": 0.005,
                "max_position_pct": 0.50,
                "max_positions": 6,
                "min_trade_usd": 500,
            },
            "cash_proxy": {"enabled": False, "symbol": "SPY"},
        },
    )


def test_ai_sizing_defaults_to_hard_stop_when_stop_missing():
    risk = RiskManager(_config())

    ok, audit = risk.validate_ai_sizing(
        symbol="NVDA",
        qty=10,
        entry=100,
        stop_loss=None,
        take_profit=None,
        equity=100_000,
        existing_positions=[],
    )

    assert ok
    assert audit["stop_loss"] == 99.0
    assert audit["stop_loss_source"] == "hard_stop"


def test_ai_sizing_honors_tighter_ai_stop():
    risk = RiskManager(_config())

    ok, audit = risk.validate_ai_sizing(
        symbol="NVDA",
        qty=10,
        entry=100,
        stop_loss=99.5,
        take_profit=105,
        equity=100_000,
        existing_positions=[],
    )
    sizing = risk.build_sizing_from_ai(
        symbol="NVDA",
        qty=10,
        entry=100,
        stop_loss=99.5,
        take_profit=105,
    )

    assert ok
    assert audit["stop_loss"] == 99.5
    assert audit["stop_loss_source"] == "ai_tighter_stop"
    assert sizing.stop_loss == 99.5
    assert sizing.risk_usd == 5.0


def test_ai_sizing_rejects_stop_wider_than_one_percent():
    risk = RiskManager(_config())

    ok, audit = risk.validate_ai_sizing(
        symbol="NVDA",
        qty=10,
        entry=100,
        stop_loss=98.9,
        take_profit=105,
        equity=100_000,
        existing_positions=[],
    )

    assert not ok
    assert audit["reject_reason"] == "stop_loss_wider_than_hard_stop_floor_99.0"


def test_ai_sizing_rejects_invalid_take_profit():
    risk = RiskManager(_config())

    ok, audit = risk.validate_ai_sizing(
        symbol="NVDA",
        qty=10,
        entry=100,
        stop_loss=99.5,
        take_profit=99,
        equity=100_000,
        existing_positions=[],
    )

    assert not ok
    assert audit["reject_reason"] == "target_not_above_entry"
