"""Intraday scan: evaluate candidates, execute high-confidence trades.

Runs at 10:00, 12:00, 14:00, 15:30 ET during market hours.
"""
from __future__ import annotations
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.alpaca_client import AlpacaClient
from src.config import Config
from src.logging_setup import setup_logging
from src.orchestrator import TradingOrchestrator
from src.telegram_notifier import notify_scan_execution, send_alert


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Evaluate only, do not place orders")
    parser.add_argument("--max-candidates", type=int, default=25)
    parser.add_argument("--force", action="store_true", help="Run even if market closed")
    args = parser.parse_args()

    log = setup_logging("scan_and_trade")
    cfg = Config.load()
    orch = TradingOrchestrator(cfg)

    try:
        clock = orch.client.get_clock()
        if not clock.is_open and not args.force:
            log.info("Market closed (next_open=%s). Skipping.", clock.next_open)
            return 0

        result = orch.run_scan(max_candidates=args.max_candidates, dry_run=args.dry_run)
        if result.get("halted"):
            log.warning("Halted by kill switch: %s", result["kill_switch"])
            # Send immediate halt alert
            reasons = result["kill_switch"].get("reasons", [])
            send_alert("HALT", "scan_and_trade", f"Kill switch triggered: {', '.join(reasons)}")
            return 2

        log.info(
            "Summary: evaluated=%d actionable=%d exits=%d executions=%d",
            result.get("candidates_evaluated", 0),
            result.get("actionable", 0),
            len(result.get("exits", [])),
            len(result.get("executions", [])),
        )

        # Fetch P&L data for notification
        client = AlpacaClient(cfg)
        current_account = client.get_account()
        current_equity = float(current_account.equity)

        # Get open P&L from positions (current unrealized gains/losses)
        current_positions = client.get_positions()
        daily_pnl = sum(float(p.unrealized_pl) for p in current_positions) if current_positions else 0.0

        # Calculate daily return % using open P&L
        # Intraday: daily_return % = open_pnl / (current_equity - open_pnl)
        prev_equity = current_equity - daily_pnl if daily_pnl else current_equity
        daily_pnl_pct = (daily_pnl / prev_equity) if prev_equity > 0 else 0.0

        # Get SPY daily return for comparison
        spy_daily_pct = 0.0
        try:
            spy_bars = client.get_stock_bars(["SPY"], lookback_days=30)
            spy = spy_bars.xs("SPY", level="symbol") if "symbol" in spy_bars.index.names else spy_bars
            if len(spy) >= 2:
                spy_close_prev = float(spy["close"].iloc[-2])
                spy_close_curr = float(spy["close"].iloc[-1])
                if spy_close_prev > 0:
                    spy_daily_pct = (spy_close_curr / spy_close_prev) - 1
        except Exception as e:
            log.warning("SPY fetch failed: %s", e)
            spy_daily_pct = 0.0

        # Send detailed scan notification
        notify_scan_execution(
            scan_name=f"@ {datetime.now().strftime('%H:%M')} ET",
            macro=result.get("macro", {}),
            decisions=result.get("decisions", []),
            executions=result.get("executions", []),
            exits=result.get("exits", []),
            kill_switch=result.get("kill_switch"),
            equity=result.get("equity", 0),
            positions_count=result.get("positions_count", 0),
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            spy_daily_pct=spy_daily_pct,
            ai_verdicts=result.get("ai_verdicts", {}),
            ai_active=result.get("ai_active", False),
        )
        return 0

    except Exception as e:
        log.exception("Scan execution failed")
        send_alert("ERROR", "TradingBot_Scan", f"Exception: {type(e).__name__}", error_details=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
