"""Smoke test for the local dashboard payload builder."""
from __future__ import annotations

from server import build_dashboard_payload


def main() -> int:
    payload = build_dashboard_payload(include_live=False)
    assert "performance" in payload
    assert payload["performance"]["source_path"] == "data/performance/portfolio_vs_spy.json"
    assert "latest_scan" in payload
    assert "journals" in payload
    assert isinstance(payload["eod"]["history"], list)
    assert isinstance(payload["latest_scan"]["all_symbol_decisions"], list)
    if payload["latest_scan"]["all_symbol_decisions"]:
        assert payload["latest_scan"]["all_symbol_decisions"][0].get("ts")
    if payload["latest_scan"]["capital_movement_plan"]:
        first_move = payload["latest_scan"]["capital_movement_plan"][0]
        assert first_move.get("ts")
        assert "exit_pnl" in first_move
    print("dashboard smoke ok")
    print(f"performance_points={payload['performance']['point_count']}")
    print(f"scan_file={payload['latest_scan']['file'].get('path')}")
    print(f"eod_reports={len(payload['eod']['history'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
