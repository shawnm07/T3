"""Pre-close overnight decision: run ~5 min before the bell.

For each currently-held equity position, score the likelihood of a favorable
overnight gap and close any that look unlikely to open green tomorrow. Then
search for fresh long candidates that look likely to gap up at the open and
size conservatively into them.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import Config
from src.daily_pnl import get_daily_pnl, get_spy_daily_pct
from src.logging_setup import setup_logging
from src.orchestrator import TradingOrchestrator
from src.telegram_notifier import notify_preclose, send_alert


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Score only, don't trade")
    parser.add_argument("--force", action="store_true", help="Run even if market closed")
    args = parser.parse_args()

    log = setup_logging("preclose_decision")

    try:
        cfg = Config.load()
        orch = TradingOrchestrator(cfg)
        clock = orch.client.get_clock()
        if not clock.is_open and not args.force:
            log.info("Market closed (next_open=%s). Skipping preclose.", clock.next_open)
            return 0

        result = orch.run_preclose(dry_run=args.dry_run)

        closes = len(result.get("exits", []))
        buys = len(result.get("new_executions", []))
        held = len([r for r in result.get("hold_reports", []) if r.get("decision") == "hold"])
        market_bias = float(result.get("market_bias", 0.0))
        halt_threshold = float(cfg.get("macro", "bearish_halt_score", default=-0.55))
        bearish_halt = market_bias <= halt_threshold
        log.info("Preclose summary: held=%d closed=%d new_buys=%d market_bias=%+.2f",
                 held, closes, buys, market_bias)

        # Defensive: if the orchestrator's preclose path failed early, equity
        # may be missing. Pull a fresh snapshot ourselves rather than showing
        # $0 in the Telegram message.
        equity = float(result.get("equity", 0.0) or 0.0)
        positions_count = int(result.get("positions_count", 0) or 0)
        account = None
        positions = []
        try:
            account, positions = orch.client.get_snapshot(force_refresh=True, log_detail=False)
            equity = float(account.equity)
            positions_count = len([p for p in positions if "/" not in p.symbol])
        except Exception as e:
            log.warning("Preclose notification snapshot failed: %s", e)

        pnl = get_daily_pnl(equity) if equity > 0 else None
        try:
            spy_daily_pct, spy_src = get_spy_daily_pct()
            log.info("SPY daily: %.2f%% [src=%s]", spy_daily_pct * 100, spy_src)
        except Exception as e:
            log.warning("SPY fetch failed: %s", e)
            spy_daily_pct = 0.0

        notify_preclose(
            equity=equity,
            positions_count=positions_count,
            market_bias=market_bias,
            hold_reports=result.get("hold_reports", []),
            exits=result.get("exits", []),
            new_executions=result.get("new_executions", []),
            bearish_halt=bearish_halt,
            halt_threshold=halt_threshold,
            dry_run=args.dry_run,
            cash=float(account.cash) if account else None,
            positions=positions,
            daily_pnl=pnl.pnl_dollars if pnl else 0.0,
            daily_pnl_pct=pnl.pnl_pct if pnl else 0.0,
            spy_daily_pct=spy_daily_pct,
        )
        return 0

    except Exception as e:
        log.exception("Preclose decision failed")
        send_alert("ERROR", "TradingBot_PreClose",
                   f"Exception: {type(e).__name__}", error_details=str(e))
        return 1


if __name__ == "__main__":
    rc = main()
    try:
        from src.data_push import push_data
        push_data("preclose")
    except Exception:
        pass
    sys.exit(rc)
