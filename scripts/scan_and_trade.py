"""Intraday scan: evaluate candidates, execute high-confidence trades.

Runs at 10:00, 11:00, 12:00, 13:00, 14:00, and 15:00 ET during market hours.
"""
from __future__ import annotations
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.alpaca_client import AlpacaClient
from src.config import Config
from src.daily_pnl import get_daily_pnl, get_spy_daily_pct
from src.logging_setup import setup_logging
from src.orchestrator import TradingOrchestrator
from src.performance_history import record_scan_datapoint, should_record_scan_datapoint
from src.telegram_notifier import notify_scan_execution, send_alert


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Evaluate only, do not place orders")
    parser.add_argument("--max-candidates", type=int, default=25)
    parser.add_argument("--force", action="store_true", help="Run even if market closed")
    parser.add_argument("--scheduled-run", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    scan_started_at = datetime.now(timezone.utc)
    scheduled_run = args.scheduled_run or os.getenv("TRADINGBOT_SCHEDULED_RUN") == "1"

    log = setup_logging("scan_and_trade")
    cfg = Config.load()
    orch = TradingOrchestrator(cfg)

    try:
        clock = orch.client.get_clock()
        if not clock.is_open and not args.force:
            log.info("Market closed (next_open=%s). Skipping.", clock.next_open)
            return 0

        result = orch.run_scan(max_candidates=args.max_candidates, dry_run=args.dry_run)

        log.info(
            "Summary: evaluated=%d actionable=%d exits=%d executions=%d",
            result.get("candidates_evaluated", 0),
            result.get("actionable", 0),
            len(result.get("exits", [])),
            len(result.get("executions", [])),
        )

        # Fetch P&L data for notification. Account balance comes from
        # independent valuation (see src/valuation.py): Alpaca supplies cash
        # and quantities only; non-Alpaca providers supply market prices.
        client = AlpacaClient(cfg)
        current_account, current_positions = client.get_snapshot()
        current_equity = float(current_account.equity)

        should_record, record_reason = should_record_scan_datapoint(
            cfg,
            scheduled_run=scheduled_run,
            dry_run=args.dry_run,
            force=args.force,
            started_at=scan_started_at,
        )
        if should_record:
            try:
                point, history_path = record_scan_datapoint(
                    cfg,
                    account=current_account,
                    positions=current_positions,
                    dry_run=args.dry_run,
                    scheduled_run=scheduled_run,
                    scan_started_at=scan_started_at,
                )
                if point.get("complete"):
                    log.info(
                        "Performance data point saved: portfolio=$%.2f SPY=$%.4f path=%s",
                        point.get("portfolio_value", 0.0),
                        point.get("spy_price", 0.0),
                        history_path,
                    )
                else:
                    log.warning(
                        "Performance data point saved incomplete: missing=%s path=%s",
                        point.get("missing_symbols", []),
                        history_path,
                    )
            except Exception as e:
                log.warning("Performance history save failed: %s", e)
        else:
            log.info("Performance history skipped: %s", record_reason)

        # Daily P&L is anchored to the cached open-of-day equity baseline,
        # not Alpaca's account.last_equity (unreliable for paper). The
        # baseline is set on the first scan of each NY trading day and
        # cached to data/state/daily_baseline.json.
        pnl = get_daily_pnl(current_equity)
        daily_pnl = pnl.pnl_dollars
        daily_pnl_pct = pnl.pnl_pct
        log.info("Daily P&L: $%.2f (%.2f%%) vs baseline $%.2f set %s [src=%s]",
                 daily_pnl, daily_pnl_pct * 100, pnl.baseline_equity,
                 pnl.baseline_date, pnl.source)

        # SPY benchmark: Twelve Data -> yfinance -> Alpha Vantage.
        try:
            spy_daily_pct, spy_src = get_spy_daily_pct(alpaca_client=client)
            log.info("SPY daily: %.2f%% [src=%s]", spy_daily_pct * 100, spy_src)
        except Exception as e:
            log.warning("SPY fetch failed: %s", e)
            spy_daily_pct = 0.0

        # Use locally-computed equity, not `result.get("equity")` — the
        # orchestrator omits that key on some early-exit paths.
        telegram_ok = notify_scan_execution(
            scan_name=f"@ {datetime.now().strftime('%H:%M')} ET",
            macro=result.get("macro", {}),
            decisions=result.get("decisions", []),
            executions=result.get("executions", []),
            exits=result.get("exits", []),
            equity=current_equity,
            positions_count=len([p for p in current_positions if "/" not in p.symbol]),
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            spy_daily_pct=spy_daily_pct,
            ai_verdicts=result.get("ai_verdicts", {}),
            ai_active=result.get("ai_active", False),
            rebalance=result.get("rebalance", []),
            opportunity_ranking=result.get("opportunity_ranking", []),
            ai_arbiter_skipped=result.get("ai_arbiter_skipped"),
            selector=result.get("selector", {}),
            unified_portfolio_plan=result.get("unified_portfolio_plan", {}),
            cash=float(current_account.cash),
            positions=current_positions,
        )
        if telegram_ok:
            log.info("Telegram scan notification sent")
        else:
            log.warning("Telegram scan notification not sent")
        return 0

    except Exception as e:
        log.exception("Scan execution failed")
        send_alert("ERROR", "TradingBot_Scan", f"Exception: {type(e).__name__}", error_details=str(e))
        return 1


if __name__ == "__main__":
    rc = main()
    try:
        from src.data_push import push_data
        push_data("scan")
    except Exception:
        pass
    sys.exit(rc)
