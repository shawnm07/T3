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
from src.journal import log_decision, read_recent_trades
from src.logging_setup import setup_logging
from src.telegram_notifier import notify_eod, send_alert


def main() -> int:
    log = setup_logging("eod_report")
    cfg = Config.load()
    client = AlpacaClient(cfg)

    try:
        account = client.get_account()
        positions = client.get_positions()
        hist = client.get_portfolio_history(period="1M", timeframe="1D")

        # Daily return: use account.equity / account.last_equity (prior day's close).
        # More reliable than portfolio_history, which may not have today's bar yet
        # when EOD runs right after the bell.
        current_equity = float(account.equity)
        last_equity = float(getattr(account, "last_equity", 0) or 0)
        if last_equity > 0:
            daily_ret = (current_equity / last_equity) - 1
        else:
            daily_ret = 0

        equity_series = hist.equity or []
        # Fallback: if account.last_equity was unavailable, try portfolio history.
        if daily_ret == 0 and len(equity_series) >= 2 and equity_series[-2]:
            daily_ret = (equity_series[-1] / equity_series[-2]) - 1

        if len(equity_series) >= 2:
            period_start = equity_series[0]
            period_ret = (equity_series[-1] / period_start) - 1 if period_start else 0
        else:
            period_ret = 0

        # SPY benchmark
        try:
            spy_bars = client.get_stock_bars(["SPY"], lookback_days=30)
            spy = spy_bars.xs("SPY", level="symbol") if "symbol" in spy_bars.index.names else spy_bars
            if len(spy) >= 2:
                spy_daily = (float(spy["close"].iloc[-1]) / float(spy["close"].iloc[-2])) - 1
                spy_30d = (float(spy["close"].iloc[-1]) / float(spy["close"].iloc[0])) - 1
            else:
                spy_daily = spy_30d = 0
        except Exception as e:
            log.warning("SPY benchmark fetch failed: %s", e)
            spy_daily = spy_30d = 0

        trades = read_recent_trades(limit=200)
        today = datetime.now(timezone.utc).date().isoformat()
        today_trades = [t for t in trades if t["ts"].startswith(today)]

        # Alpaca paper's unrealized_plpc is unreliable — compute pnl from
        # avg_entry_price vs latest close bar instead.
        equity_syms = [p.symbol for p in positions if "/" not in p.symbol]
        current_prices: dict[str, float] = {}
        if equity_syms:
            try:
                bars = client.get_stock_bars(equity_syms, lookback_days=5)
                for s in equity_syms:
                    try:
                        sbars = bars.xs(s, level="symbol") if "symbol" in bars.index.names else bars
                        current_prices[s] = float(sbars["close"].iloc[-1])
                    except (KeyError, IndexError):
                        pass
            except Exception as e:
                log.warning("current-price fetch failed: %s", e)

        def _pos_record(p):
            sym = p.symbol
            avg_entry = float(p.avg_entry_price) if getattr(p, "avg_entry_price", None) else 0.0
            curr = current_prices.get(sym, 0.0)
            is_long = (str(p.side).lower().endswith("long"))
            if avg_entry > 0 and curr > 0:
                raw = (curr - avg_entry) / avg_entry
                pnl_pct = raw if is_long else -raw
            else:
                pnl_pct = 0.0
            return {
                "symbol": sym,
                "side": str(p.side),
                "qty": float(p.qty),
                "avg_entry": round(avg_entry, 4),
                "current_price": round(curr, 4),
                "pnl_pct": round(pnl_pct, 4),
                "market_value": float(p.market_value) if getattr(p, "market_value", None) else 0.0,
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

        # Send EOD notification
        notify_eod(
            daily_return=daily_ret,
            daily_vs_spy=daily_ret - spy_daily,
            spy_daily=spy_daily,
            trades_today=len(today_trades),
            positions_count=len(positions),
            equity=float(account.equity),
            cash=float(account.cash),
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
