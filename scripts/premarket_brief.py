"""Pre-market brief: macro snapshot, watchlist setup, cancel stale orders.

Runs ~08:30 ET, before the 09:30 open.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.alpaca_client import AlpacaClient
from src.config import Config
from src.journal import log_decision
from src.logging_setup import setup_logging
from src.orchestrator import TradingOrchestrator
from src.telegram_notifier import notify_premarket, send_alert


def main() -> int:
    log = setup_logging("premarket")
    cfg = Config.load()
    orch = TradingOrchestrator(cfg)

    try:
        client = orch.client
        clock = client.get_clock()
        log.info("Clock: is_open=%s next_open=%s", clock.is_open, clock.next_open)

        # Cancel leftover open orders from yesterday
        cancelled_count = 0
        try:
            open_orders = client.get_open_orders()
            if open_orders:
                log.info("Canceling %d stale open orders", len(open_orders))
                client.cancel_all_orders()
                cancelled_count = len(open_orders)
        except Exception as e:
            log.warning("Cancel stale orders failed: %s", e)

        macro = orch.macro_brief()
        account = client.get_account()
        positions = client.get_positions()
        log.info(
            "Pre-market: equity=$%s cash=$%s positions=%d regime=%s",
            account.equity, account.cash, len(positions), macro.regime,
        )

        # Calculate total P&L
        total_pnl = sum(float(p.unrealized_plpc) for p in positions)

        # Format positions for notification
        positions_list = [
            {
                "symbol": p.symbol,
                "side": str(p.side),
                "qty": str(p.qty),
                "unrealized_pnl": float(p.unrealized_plpc),
            }
            for p in positions
        ]

        for p in positions:
            log.info(
                "  %s %s qty=%s avg_entry=$%s unrealized=%s%% mkt_val=$%s",
                p.symbol, p.side, p.qty, p.avg_entry_price,
                round(float(p.unrealized_plpc) * 100, 2),
                p.market_value,
            )
        log_decision({"event": "premarket_brief", "macro": macro.to_dict(), "positions": len(positions)})

        # Send premarket notification
        notify_premarket(
            macro=macro.to_dict(),
            positions_count=len(positions),
            total_pnl=total_pnl,
            cancelled_orders=cancelled_count,
            positions_list=positions_list,
        )
        return 0

    except Exception as e:
        log.exception("Premarket brief failed")
        send_alert("ERROR", "TradingBot_PreMarket", f"Exception: {type(e).__name__}", error_details=str(e))
        return 1


if __name__ == "__main__":
    rc = main()
    try:
        from src.data_push import push_data
        push_data("premarket")
    except Exception:
        pass
    sys.exit(rc)
