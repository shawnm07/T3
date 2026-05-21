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
from src.daily_fill_cap import fills_today
from src.journal import log_decision, read_recent_trades
from src.logging_setup import setup_logging
from src.postmortem import exit_arbiter_accuracy, read_recent as read_postmortems
from src.scanning_failure_alert import record_scan_outcome
from src.spy_ballast import force_deploy_failure
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

        # 2026-05-12 EOD overhaul: intraday trough + comeback attribution.
        # We approximate this from cached equity-history JSON and per-position
        # P&L deltas across the day. Best-effort: missing data degrades the
        # section but doesn't fail the report.
        trough_section: dict = {"status": "no_data"}
        try:
            from pathlib import Path as _P
            scans_dir = _P(__file__).resolve().parents[1] / "data" / "research"
            today_scans = sorted([
                f for f in scans_dir.glob(f"*{today.replace('-', '')}*scan*.json")
            ])
            equity_curve: list = []
            for f in today_scans:
                try:
                    d = json.loads(f.read_text())
                    eq = d.get("equity") or d.get("after_snapshot", {}).get("equity")
                    ts = d.get("ts") or d.get("timestamp")
                    if eq and ts:
                        equity_curve.append({"ts": ts, "equity": float(eq)})
                except Exception:
                    continue
            if equity_curve:
                trough = min(equity_curve, key=lambda r: r["equity"])
                close_eq = equity_curve[-1]["equity"]
                comeback_dollars = close_eq - trough["equity"]
                comeback_pct = (close_eq / trough["equity"] - 1.0) if trough["equity"] else 0.0
                trough_section = {
                    "status": "ok",
                    "trough_ts": trough["ts"],
                    "trough_equity": round(trough["equity"], 2),
                    "close_equity": round(close_eq, 2),
                    "comeback_dollars": round(comeback_dollars, 2),
                    "comeback_pct": round(comeback_pct, 4),
                    "samples": len(equity_curve),
                }
        except Exception as e:
            log.warning("trough section build failed: %s", e)

        # Sector breakdown of the book at close. Compared with SPY sector mix
        # so we can see whether we were over/under in lagging sectors.
        sector_breakdown: dict = {}
        try:
            from src.universe import sp500_sectors as _ssecs
            secs = _ssecs()
            total_mv = sum(float(p.market_value) for p in positions if "/" not in p.symbol)
            agg: dict = {}
            for p in positions:
                if "/" in p.symbol:
                    continue
                sec = secs.get(p.symbol, "Other")
                agg.setdefault(sec, 0.0)
                agg[sec] += float(p.market_value)
            if total_mv > 0:
                sector_breakdown = {k: round(v / total_mv, 4) for k, v in agg.items()}
        except Exception:
            pass

        # 2026-05-11 EOD overhaul: post-mortem digest + churn telemetry.
        try:
            pms = read_postmortems(cfg, days=1)
        except Exception as e:
            log.warning("postmortem read failed: %s", e)
            pms = []
        arbiter_diag = exit_arbiter_accuracy(pms) if pms else {"sample": 0, "accuracy": None}
        winners = [r for r in pms if float(r.get("realized_pl_pct", 0.0) or 0.0) > 0]
        losers = [r for r in pms if float(r.get("realized_pl_pct", 0.0) or 0.0) < 0]
        avg_hold_min = (
            sum(float(r.get("hold_minutes", 0.0) or 0.0) for r in pms) / len(pms)
            if pms else 0.0
        )
        # Churn signal: more than the daily fill cap is a smell.
        fills = fills_today()
        # SPY ballast / force-deploy check
        try:
            equity_val = float(account.equity)
            cash_val = float(account.cash)
            cash_pct = cash_val / equity_val if equity_val else 0.0
        except Exception:
            cash_pct = 0.0
        # Pull macro score from cached scan output if available — best effort.
        macro_score = 0.0
        try:
            from pathlib import Path as _P
            scan_log = _P(__file__).resolve().parents[1] / "data" / "research" / f"{today}_macro.json"
            if scan_log.exists():
                import json as _json
                macro_score = float(_json.loads(scan_log.read_text()).get("score", 0.0) or 0.0)
        except Exception:
            pass
        force_deploy = force_deploy_failure(
            cfg, macro_score=macro_score, cash_pct=cash_pct,
            selected_count=len([p for p in positions if "/" not in p.symbol]),
        )

        # Scanning-failure streak — closed/idle days (no candidates evaluated)
        # are intentionally NOT recorded here; the preclose script feeds the
        # streak counter on days a scan actually ran.

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
            "postmortem_digest": {
                "closes_today": len(pms),
                "winners": len(winners),
                "losers": len(losers),
                "avg_hold_minutes": round(avg_hold_min, 1),
                "exit_arbiter_diag": arbiter_diag,
                "details": pms,
            },
            "fills_today_counted": fills,
            "force_deploy_audit": force_deploy,
            "trough_and_comeback": trough_section,
            "sector_breakdown": sector_breakdown,
        }
        if force_deploy:
            log.warning("[eod] force-deploy failure: %s", force_deploy.get("message"))
            try:
                send_alert(
                    "WARN", "TradingBot_EOD",
                    "Force-deploy failure",
                    error_details=force_deploy.get("message", ""),
                )
            except Exception:
                pass
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
