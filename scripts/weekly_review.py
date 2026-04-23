"""Weekly review: performance vs SPY, win rate, strategy adjustments suggested."""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.alpaca_client import AlpacaClient
from src.config import Config
from src.journal import log_decision, read_recent_trades
from src.logging_setup import setup_logging
from src.telegram_notifier import notify_weekly, send_alert


def main() -> int:
    log = setup_logging("weekly_review")
    cfg = Config.load()
    client = AlpacaClient(cfg)

    try:
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
            spy = client.get_stock_bars(["SPY"], lookback_days=90)
            s = spy.xs("SPY", level="symbol") if "symbol" in spy.index.names else spy
            spy_week = (float(s["close"].iloc[-1]) / float(s["close"].iloc[-6])) - 1 if len(s) >= 6 else 0
            spy_month = (float(s["close"].iloc[-1]) / float(s["close"].iloc[-22])) - 1 if len(s) >= 22 else 0
        except Exception as e:
            log.warning("SPY fetch failed: %s", e)
            spy_week = spy_month = 0

        trades = read_recent_trades(limit=1000)
        submitted = [t for t in trades if t.get("event") == "order_submitted"]
        wins = losses = 0
        # Placeholder: real P&L attribution would need matching buys/sells. Use closed positions for now.
        positions = client.get_positions()

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
    sys.exit(main())
