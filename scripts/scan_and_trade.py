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
from src.daily_pnl import get_daily_pnl, get_spy_daily_pct
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

        log.info(
            "Summary: evaluated=%d actionable=%d exits=%d executions=%d",
            result.get("candidates_evaluated", 0),
            result.get("actionable", 0),
            len(result.get("exits", [])),
            len(result.get("executions", [])),
        )

        # Fetch P&L data for notification. Equity comes from independent
        # valuation (see src/valuation.py) — Alpaca's equity field is
        # unreliable. We compute it locally and pass it explicitly so
        # we never depend on `result.get("equity", 0)` which can be
        # missing from the orchestrator's early-exit return paths.
        client = AlpacaClient(cfg)
        current_account, current_positions = client.get_snapshot()
        current_equity = float(current_account.equity)

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

        # SPY benchmark: Twelve Data → yfinance → Alpha Vantage → Alpaca.
        try:
            spy_daily_pct, spy_src = get_spy_daily_pct(alpaca_client=client)
            log.info("SPY daily: %.2f%% [src=%s]", spy_daily_pct * 100, spy_src)
        except Exception as e:
            log.warning("SPY fetch failed: %s", e)
            spy_daily_pct = 0.0

        # Use locally-computed equity, not `result.get("equity")` — the
        # orchestrator omits that key on some early-exit paths.
        notify_scan_execution(
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
        )
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
