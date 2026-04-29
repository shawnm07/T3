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
from src.logging_setup import setup_logging
from src.orchestrator import TradingOrchestrator
from src.telegram_notifier import notify_preclose, send_alert


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Score only, don't trade")
    parser.add_argument("--force", action="store_true", help="Run even if market closed")
    args = parser.parse_args()

    log = setup_logging("preclose_decision")
    cfg = Config.load()
    orch = TradingOrchestrator(cfg)

    try:
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
        if equity <= 0.0:
            try:
                acct, pos = orch.client.get_snapshot()
                equity = float(acct.equity)
                positions_count = len([p for p in pos if "/" not in p.symbol])
            except Exception as e:
                log.warning("Preclose fallback snapshot failed: %s", e)

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
