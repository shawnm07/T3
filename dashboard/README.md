# Trading Bot Dashboard

Local, read-only dashboard for the trading bot.

## Run

```powershell
cd C:\Users\shawn\OneDrive\Documents\Tim\trading-bot
.\.venv\Scripts\python.exe .\dashboard\server.py --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765
```

## Data Sources

- `data/performance/portfolio_vs_spy.json` powers the Performance vs SPY graph.
- `data/research/*_scan.json` powers selector, decisions, targets, missed breakouts, and capital movement.
- `data/research/*_eod.json` powers account balance history and EOD position history.
- `data/journal/trades.jsonl` and `data/journal/decisions.jsonl` power recent trades and decisions.
- `data/state/dynamic_watchlist.json` powers dynamic watchlist leaders.

The dashboard server only reads these files. A live snapshot can be requested from the page; that imports the bot's existing valuation layer and does not write data or place trades.

Symbol detail drawers embed TradingView's Advanced Chart widget using a 5-minute intraday interval and request the extended session where TradingView supports it. The drawer labels that state explicitly so regular, pre-market, and post-market context is clear.
