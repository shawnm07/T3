"""Weekly review: performance vs SPY, win rate, strategy adjustments suggested."""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.adaptive_config import evaluate_and_update as adaptive_evaluate
from src.alpaca_client import AlpacaClient
from src.config import Config
from src.daily_pnl import get_spy_period_pct
from src.journal import log_decision, read_recent_trades
from src.logging_setup import setup_logging
from src.postmortem import exit_arbiter_accuracy, read_recent as read_postmortems
from src.telegram_notifier import notify_weekly, send_alert


def main() -> int:
    log = setup_logging("weekly_review")

    try:
        cfg = Config.load()
        client = AlpacaClient(cfg)
        account = client.get_account()
        hist = client.get_portfolio_history(period="3M", timeframe="1D")
        equity = hist.equity or []
        week_ret = 0
        if len(equity) >= 6:
            week_ret = (equity[-1] / equity[-6]) - 1 if equity[-6] else 0
        month_ret = 0
        if len(equity) >= 22:
            month_ret = (equity[-1] / equity[-22]) - 1 if equity[-22] else 0

        try:
            spy_week, spy_week_src = get_spy_period_pct(5)
            spy_month, spy_month_src = get_spy_period_pct(21)
            log.info("SPY week %.2f%% [%s], month %.2f%% [%s]",
                     spy_week * 100, spy_week_src,
                     spy_month * 100, spy_month_src)
        except Exception as e:
            log.warning("SPY fetch failed: %s", e)
            spy_week = spy_month = 0

        trades = read_recent_trades(limit=1000)
        submitted = [t for t in trades if t.get("event") == "order_submitted"]
        wins = losses = 0
        # Placeholder: real P&L attribution would need matching buys/sells. Use closed positions for now.
        positions = client.get_positions()

        # 2026-05-11 overhaul: weekly retrospective + adaptive tuning.
        try:
            pms = read_postmortems(cfg, days=7)
        except Exception as e:
            log.warning("postmortem read failed: %s", e)
            pms = []
        winners = [r for r in pms if float(r.get("realized_pl_pct", 0.0) or 0.0) > 0]
        losers = [r for r in pms if float(r.get("realized_pl_pct", 0.0) or 0.0) < 0]
        avg_winner_hold = (
            sum(float(r.get("hold_minutes", 0.0) or 0.0) for r in winners) / len(winners)
            if winners else 0.0
        )
        avg_loser_hold = (
            sum(float(r.get("hold_minutes", 0.0) or 0.0) for r in losers) / len(losers)
            if losers else 0.0
        )
        arbiter_diag = exit_arbiter_accuracy(pms) if pms else {"sample": 0, "accuracy": None}
        # Adaptive config: may write to data/state/config_overrides.yaml.
        try:
            adaptive_summary = adaptive_evaluate(cfg)
        except Exception as e:
            log.warning("adaptive_config failed: %s", e)
            adaptive_summary = {"status": "error", "error": str(e)}

        # 2026-05-12 overhaul: missed-sector + sector-rotation diagnostics.
        # Pull the most recent cached sector regime if available.
        sector_diag: dict = {"status": "no_data"}
        try:
            from pathlib import Path as _P
            cached = _P(__file__).resolve().parents[1] / "data" / "cache" / "sector_etfs" / "snapshot.json"
            if cached.exists():
                d = json.loads(cached.read_text())
                snaps = d.get("snapshots") or []
                if snaps:
                    leaders = sorted(
                        snaps, key=lambda s: float(s.get("ret_5d", 0) or 0), reverse=True,
                    )[:3]
                    laggards = sorted(
                        snaps, key=lambda s: float(s.get("ret_5d", 0) or 0),
                    )[:3]
                    sector_diag = {
                        "status": "ok",
                        "as_of": d.get("_ts"),
                        "top_5d": [{"sym": s["symbol"], "ret_5d": s.get("ret_5d")} for s in leaders],
                        "bottom_5d": [{"sym": s["symbol"], "ret_5d": s.get("ret_5d")} for s in laggards],
                    }
        except Exception as e:
            log.warning("sector diag failed: %s", e)

        report = {
            "date": datetime.now(timezone.utc).date().isoformat(),
            "equity": float(account.equity),
            "week_return": round(week_ret, 4),
            "week_vs_spy": round(week_ret - spy_week, 4),
            "month_return": round(month_ret, 4),
            "month_vs_spy": round(month_ret - spy_month, 4),
            "spy_week": round(spy_week, 4),
            "spy_month": round(spy_month, 4),
            "trades_count": len(submitted),
            "current_positions": len(positions),
            "retrospective": {
                "closes_examined": len(pms),
                "winners": len(winners),
                "losers": len(losers),
                "win_rate": round(len(winners) / len(pms), 3) if pms else None,
                "avg_winner_hold_minutes": round(avg_winner_hold, 1),
                "avg_loser_hold_minutes": round(avg_loser_hold, 1),
                "exit_arbiter_diag": arbiter_diag,
            },
            "adaptive_config": adaptive_summary,
            "sector_diagnostics": sector_diag,
        }
        log.info("Week: %+.2f%% vs SPY %+.2f%% (diff %+.2f%%)", week_ret * 100, spy_week * 100, (week_ret - spy_week) * 100)
        log.info("Month: %+.2f%% vs SPY %+.2f%% (diff %+.2f%%)", month_ret * 100, spy_month * 100, (month_ret - spy_month) * 100)
        log_decision({"event": "weekly_review", **report})

        out = Path(__file__).resolve().parents[1] / "data" / "research" / f"{report['date']}_weekly.json"
        out.write_text(json.dumps(report, indent=2, default=str))

        # Send weekly review notification
        notify_weekly(
            weekly_return=week_ret,
            weekly_vs_spy=week_ret - spy_week,
            monthly_return=month_ret,
            monthly_vs_spy=month_ret - spy_month,
            trades_week=len(submitted),
            trades_month=len(submitted),
            best_performer="",  # Could be enhanced to find best performer
            worst_performer="",  # Could be enhanced to find worst performer
            win_rate=0.0,  # Could be enhanced to calculate actual win rate
        )
        return 0

    except Exception as e:
        log.exception("Weekly review failed")
        send_alert("ERROR", "TradingBot_WeeklyReview", f"Exception: {type(e).__name__}", error_details=str(e))
        return 1


if __name__ == "__main__":
    rc = main()
    try:
        from src.data_push import push_data
        push_data("weekly")
    except Exception:
        pass
    sys.exit(rc)
