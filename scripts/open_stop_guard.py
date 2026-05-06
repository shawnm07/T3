"""Re-arm protective stops after the opening-stop guard delay."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.alpaca_client import AlpacaClient
from src.config import Config
from src.executor import TradeExecutor
from src.journal import log_decision
from src.logging_setup import setup_logging
from src.opening_stop_guard import rearm_opening_guard_orders
from src.telegram_notifier import send_alert


def main() -> int:
    log = setup_logging("open_stop_guard")
    cfg = Config.load()
    client = AlpacaClient(cfg)
    executor = TradeExecutor(client, cfg)
    try:
        result = rearm_opening_guard_orders(cfg, client, executor=executor)
        log_decision({"event": "opening_stop_guard_rearm", "result": result})
        log.info("Opening-stop guard rearm complete: %s", result)
        return 0
    except Exception as exc:
        log.exception("Opening-stop guard rearm failed")
        send_alert(
            "ERROR",
            "TradingBot_OpenStopGuard",
            f"Exception: {type(exc).__name__}",
            error_details=str(exc),
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
