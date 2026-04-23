"""Crypto scan: runs 24/7 every N hours (default 4h)."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import Config
from src.logging_setup import setup_logging
from src.orchestrator import TradingOrchestrator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log = setup_logging("crypto_check")
    cfg = Config.load()
    orch = TradingOrchestrator(cfg)
    result = orch.run_crypto_scan(dry_run=args.dry_run)
    log.info("Crypto scan result: %s", result)
    return 0


if __name__ == "__main__":
    rc = main()
    try:
        from src.data_push import push_data
        push_data("crypto")
    except Exception:
        pass
    sys.exit(rc)
