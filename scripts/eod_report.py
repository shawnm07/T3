"""End-of-day report: P&L, trades, vs SPY benchmark, lessons for journal."""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.alpaca_client import AlpacaClient
from src.config import Config
from src.daily_pnl import get_daily_pnl, get_spy_daily_pct, get_spy_period_pct
from src.journal import log_decision, read_recent_trades
from src.logging_setup import setup_logging
from src.telegram_notifier import notify_eod, send_alert


def main() -> int:
    log = setup_logging("eod_report")

    try:
        cfg = Config.load()
        client = AlpacaClient(cfg)
        # get_account() / get_positions() return independently-valued views —
        # equity, market_value, unrealized_pl[pc], current_price are recomputed
        # from independently fetched prices (not Alpaca's unreliable fields).
        account, positions = client.get_snapshot()
        hist = client.get_portfolio_history(period="1M", timeframe="1D")

        # Daily return: anchored to today's cached open-of-day equity baseline
        # (set by the first scan of the trading day). This matches the Daily%
        # shown in scan messages, and doesn't depend on Alpaca's last_equity.
        current_equity = float(account.equity)
        pnl = get_daily_pnl(current_equity)
        daily_ret = pnl.pnl_pct
        log.info("EOD daily return: %.2f%% vs baseline $%.2f set %s",
                 daily_ret * 100, pnl.baseline_equity, pnl.baseline_date)

        equity_series = hist.equity or []
        if len(equity_series) >= 2:
            period_start = equity_series[0]
            period_ret = (equity_series[-1] / period_start) - 1 if period_start else 0
        else:
            period_ret = 0

        # SPY benchmark via Twelve Data -> yfinance -> Alpha Vantage.
        try:
            spy_daily, spy_src = get_spy_daily_pct(alpaca_client=client)
            log.info("SPY daily: %.2f%% [src=%s]", spy_daily * 100, spy_src)
        except Exception as e:
            log.warning("SPY benchmark fetch failed: %s", e)
            spy_daily = 0
        try:
            spy_30d, spy_30d_src = get_spy_period_pct(30)
            log.info("SPY 30d: %.2f%% [src=%s]", spy_30d * 100, spy_30d_src)
        except Exception as e:
            log.warning("SPY 30d fetch failed: %s", e)
            spy_30d = 0

        trades = read_recent_trades(limit=200)
        today = datetime.now(timezone.utc).date().isoformat()
        today_trades = [t for t in trades if t["ts"].startswith(today)]

        # All P/L comes from the independent valuation (see src/valuation.py).
        def _pos_record(p):
            return {
                "symbol": p.symbol,
                "side": str(p.side),
                "qty": float(p.qty),
                "avg_entry": round(float(p.avg_entry_price), 4),
                "current_price": round(float(p.current_price), 4),
                "pnl_pct": round(float(p.unrealized_plpc), 4),
                "pnl_dollars": round(float(p.unrealized_pl), 2),
                "market_value": round(float(p.market_value), 2),
                "price_source": getattr(p, "price_source", ""),
            }

        report = {
            "date": today,
            "equity": float(account.equity),
            "cash": float(account.cash),
            "daily_return": round(daily_ret, 4),
            "daily_vs_spy": round(daily_ret - spy_daily, 4),
            "period_return": round(period_ret, 4),
            "period_vs_spy": round(period_ret - spy_30d, 4),
            "spy_daily": round(spy_daily, 4),
            "spy_30d": round(spy_30d, 4),
            "positions_count": len(positions),
            "trades_today": len(today_trades),
            "positions": [_pos_record(p) for p in positions],
        }
        log.info("EOD: daily=%+.2f%% (vs SPY %+.2f%%) period=%+.2f%% (vs SPY %+.2f%%)",
                 daily_ret * 100, (daily_ret - spy_daily) * 100,
                 period_ret * 100, (period_ret - spy_30d) * 100)
        log.info("Positions: %d, trades today: %d", len(positions), len(today_trades))
        log_decision({"event": "eod_report", **report})

        out = Path(__file__).resolve().parents[1] / "data" / "research" / f"{today}_eod.json"
        out.write_text(json.dumps(report, indent=2, default=str))

        # Send EOD notification. The value passed as `equity` is the total
        # account balance (cash + externally-priced positions); the Telegram
        # text never relies on Alpaca market values.
        notify_eod(
            daily_return=daily_ret,
            daily_vs_spy=daily_ret - spy_daily,
            spy_daily=spy_daily,
            daily_pnl=pnl.pnl_dollars,
            trades_today=len(today_trades),
            positions_count=len(positions),
            equity=float(account.equity),
            cash=float(account.cash),
            positions=positions,
        )
        return 0

    except Exception as e:
        log.exception("EOD report failed")
        send_alert("ERROR", "TradingBot_EOD", f"Exception: {type(e).__name__}", error_details=str(e))
        return 1


if __name__ == "__main__":
    rc = main()
    try:
        from src.data_push import push_data
        push_data("eod")
    except Exception:
        pass
    sys.exit(rc)
