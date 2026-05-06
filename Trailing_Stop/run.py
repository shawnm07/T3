"""Trailing-stop bot entry point — invoked every 5 minutes by Task Scheduler.

Usage:
    py Trailing_Stop/run.py            # live cycle
    py Trailing_Stop/run.py --dry-run  # log actions only, no order changes
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `py Trailing_Stop/run.py` from anywhere; src.* imports need the project
# root on sys.path.
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.alpaca_client import AlpacaClient  # noqa: E402
from src.config import Config  # noqa: E402
from src.logging_setup import setup_logging  # noqa: E402

from Trailing_Stop.trailing_stops import run_trailing_stop_cycle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Converging trailing-stop cycle")
    parser.add_argument("--dry-run", action="store_true",
                        help="log intended actions but do not submit/cancel orders")
    args = parser.parse_args()

    log = setup_logging("trailing_stop_bot")
    try:
        cfg = Config.load()
        client = AlpacaClient(cfg)
        result = run_trailing_stop_cycle(client, cfg, dry_run=args.dry_run)
        log.info(
            "cycle done: positions=%d created=%d adjusted=%d filled=%d "
            "synthetic=%d skipped_tighter=%d errors=%d%s",
            result.positions, result.created, result.adjusted, result.filled,
            result.synthetic_created, result.skipped_tighter, len(result.errors),
            " (DRY RUN)" if args.dry_run else "",
        )
        if result.errors:
            for e in result.errors[:20]:
                log.warning("cycle error: %s", e)
    except Exception as exc:
        log.exception("trailing-stop cycle aborted: %s", exc)
    return 0  # always 0 so Task Scheduler doesn't disable the recurring task


if __name__ == "__main__":
    sys.exit(main())
