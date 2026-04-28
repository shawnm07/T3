"""Phase 4 verification: exercise the unified portfolio-selector end-to-end.

Temporarily flips `selector.enabled` in memory, runs a single dry-run scan,
prints the selector decision, then restores the original config flag. Does
NOT modify config.yaml on disk and does NOT trigger Telegram notifications.

Usage: .venv/Scripts/python.exe -m scripts.dry_run_selector [--force]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import Config
from src.logging_setup import setup_logging
from src.orchestrator import TradingOrchestrator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Run even if market is closed (uses delayed/last bars)")
    args = parser.parse_args()

    log = setup_logging("dry_run_selector")
    cfg = Config.load()

    # Flip the feature flag in memory only — config.yaml stays unchanged.
    cfg.raw.setdefault("selector", {})["enabled"] = True
    log.info("=== Dry-run selector flag flipped to TRUE in memory ===")

    orch = TradingOrchestrator(cfg)

    try:
        clock = orch.client.get_clock()
        if not clock.is_open and not args.force:
            log.warning("Market closed (next_open=%s). Use --force to test anyway.",
                        clock.next_open)
            return 0
    except Exception as e:
        log.warning("Clock check failed: %s — proceeding with --force semantics", e)

    log.info("Running orch.run_scan(dry_run=True) — selector path will execute")
    result = orch.run_scan(max_candidates=25, dry_run=True)

    print()
    print("=" * 78)
    print("DRY-RUN SELECTOR RESULT")
    print("=" * 78)
    status = result.get("status", "ok")
    print(f"Status: {status}")
    print(f"Equity: ${result.get('equity', 0):,.2f}")
    print(f"Positions count: {result.get('positions_count', 0)}")

    sel = result.get("selector") or {}
    if sel:
        print()
        print(f"Pool size: {sel.get('pool_size')}")
        print(f"Sources breakdown: {json.dumps(sel.get('sources_breakdown', {}))}")
        print(f"Allow floor breach: {sel.get('allow_floor_breach')}")
        print(f"Selected positions: {sel.get('selected_positions')}")
        print(f"Target weights: {json.dumps(sel.get('target_weights', {}), indent=2)}")
        print(f"SPY target pct: {sel.get('spy_target_pct')}")
        print(f"Cash target pct: {sel.get('cash_target_pct')}")
        print(f"Exhaustion penalized: {sel.get('exhaustion_penalty_applied')}")
        print(f"New candidates selected: {sel.get('new_candidates_selected')}")

    exits = result.get("exits") or []
    executions = result.get("executions") or []
    print()
    print(f"Exits: {len(exits)}")
    for e in exits[:5]:
        print(f"  - {e}")
    print(f"Executions (dry-run): {len(executions)}")
    for ex in executions[:8]:
        sym = ex.get("symbol", "?")
        side = ex.get("side", "?")
        notional = ex.get("delta_notional", 0)
        is_new = ex.get("is_new_entry", False)
        reason = (ex.get("reason") or "")[:80]
        tag = " NEW" if is_new else ""
        print(f"  - {sym:6s} {side:4s} ${notional:,.0f}{tag}  {reason}")

    print()
    print("Output saved under data/research/ and data/journal/decisions.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
