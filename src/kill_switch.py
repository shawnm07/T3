"""Circuit breakers: weekly drawdown, daily drawdown, trade count, approval gate."""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.alpaca_client import AlpacaClient
from src.config import Config

log = logging.getLogger(__name__)

STATE_DIR = Path(__file__).resolve().parents[1] / "data" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
KILL_FILE = STATE_DIR / "kill_switch.json"
TRADE_COUNTER = STATE_DIR / "trade_counter.json"


@dataclass
class KillCheck:
    halted: bool
    reasons: list[str]
    weekly_return: float | None
    daily_return: float | None
    trades_today: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "halted": self.halted,
            "reasons": self.reasons,
            "weekly_return": self.weekly_return,
            "daily_return": self.daily_return,
            "trades_today": self.trades_today,
        }


def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, default=str))


def manual_halt(reason: str) -> None:
    _save(KILL_FILE, {"halted": True, "reason": reason, "at": datetime.now(timezone.utc).isoformat()})


def manual_resume() -> None:
    _save(KILL_FILE, {"halted": False, "at": datetime.now(timezone.utc).isoformat()})


def is_manually_halted() -> tuple[bool, str]:
    d = _load(KILL_FILE)
    return bool(d.get("halted")), d.get("reason", "")


def increment_trade_counter() -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    d = _load(TRADE_COUNTER)
    if d.get("date") != today:
        d = {"date": today, "count": 0}
    d["count"] = d.get("count", 0) + 1
    _save(TRADE_COUNTER, d)
    return d["count"]


def trades_today() -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    d = _load(TRADE_COUNTER)
    return d.get("count", 0) if d.get("date") == today else 0


def check_kill_switch(client: AlpacaClient, config: Config) -> KillCheck:
    reasons: list[str] = []
    halted = False

    manual, manual_reason = is_manually_halted()
    if manual:
        halted = True
        reasons.append(f"manual_halt: {manual_reason}")

    weekly_limit = config.get("kill_switch", "weekly_drawdown_pct", default=0.05)
    daily_limit = config.get("kill_switch", "daily_drawdown_pct", default=0.04)
    max_trades = config.get("kill_switch", "max_daily_trades", default=10)

    weekly_ret = None
    daily_ret = None
    try:
        hist = client.get_portfolio_history(period="1M", timeframe="1D")
        equity = hist.equity
        ts = hist.timestamp
        if equity and len(equity) >= 2:
            latest = equity[-1]
            prev_day = equity[-2] if len(equity) >= 2 else latest
            daily_ret = (latest / prev_day) - 1 if prev_day else 0
            # Weekly: compare to 5 trading days ago (or earliest available)
            idx = -6 if len(equity) >= 6 else 0
            weekly_start = equity[idx]
            weekly_ret = (latest / weekly_start) - 1 if weekly_start else 0
            if daily_ret is not None and daily_ret < -daily_limit:
                halted = True
                reasons.append(f"daily_dd {daily_ret:.2%} < -{daily_limit:.0%}")
            if weekly_ret is not None and weekly_ret < -weekly_limit:
                halted = True
                reasons.append(f"weekly_dd {weekly_ret:.2%} < -{weekly_limit:.0%}")
    except Exception as e:
        log.warning("Portfolio history check failed: %s", e)

    trades_done = trades_today()
    if trades_done >= max_trades:
        halted = True
        reasons.append(f"max_daily_trades {trades_done}/{max_trades}")

    return KillCheck(
        halted=halted,
        reasons=reasons,
        weekly_return=weekly_ret,
        daily_return=daily_ret,
        trades_today=trades_done,
    )
