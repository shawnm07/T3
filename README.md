# Trading Bot — Multi-Agent, Alpaca Paper

Autonomous trading bot that tries to beat the S&P 500. Runs research multiple
times a day, trades only on high-conviction multi-signal consensus, risk-sized
with Python-enforced protective stops no wider than 1%, paper mode against
Alpaca.

## Status snapshot

| Field | Value |
| --- | --- |
| Mode | paper (Alpaca) |
| Benchmark | SPY |
| Risk profile | balanced (max 20% drawdown, max 6 positions) |
| Assets | US long equities |
| Cadence | swing — research 6× weekdays |

## Quick commands

All commands assume working dir = this folder.

```
py dashboard.py                               # status: positions, P&L, recent trades
py scripts/scan_and_trade.py --dry-run        # what would we trade right now?
py scripts/scan_and_trade.py --force          # run it (force = ignore market-hours check)
py scripts/premarket_brief.py                 # macro brief + cancel stale orders
py scripts/eod_report.py                      # today's P&L vs SPY
py scripts/weekly_review.py                   # weekly P&L vs SPY
```

## Autonomous schedule (Windows Task Scheduler)

1. Right-click PowerShell → **Run as Administrator**.
2. `cd C:\Users\shawn\OneDrive\Documents\Tim\trading-bot`
3. `.\scripts\setup_schedule.ps1`

Registers these at **Phoenix local time** for the current EDT market-hours
offset; see the top of `setup_schedule.ps1` when the East Coast switches to EST:

| Task | When | Script |
| --- | --- | --- |
| TradingBot_PreMarket | Mon-Fri 05:30 Phoenix | `premarket_brief.py` |
| TradingBot_Scan_0700 | Mon-Fri 07:00 Phoenix | `scan_and_trade.py` |
| TradingBot_Scan_0800 | Mon-Fri 08:00 Phoenix | `scan_and_trade.py` |
| TradingBot_Scan_0900 | Mon-Fri 09:00 Phoenix | `scan_and_trade.py` |
| TradingBot_Scan_1000 | Mon-Fri 10:00 Phoenix | `scan_and_trade.py` |
| TradingBot_Scan_1100 | Mon-Fri 11:00 Phoenix | `scan_and_trade.py` |
| TradingBot_Scan_1200 | Mon-Fri 12:00 Phoenix | `scan_and_trade.py` |
| TradingBot_PreClose | Mon-Fri 12:55 Phoenix | `preclose_decision.py` |
| TradingBot_EOD | Mon-Fri 13:15 Phoenix | `eod_report.py` |
| TradingBot_WeeklyReview | Fri 14:00 Phoenix | `weekly_review.py` |

Scripts call `clock.is_open` and no-op when market is closed, so the scan tasks
are safe to miss a few minutes either side.

To remove: `.\scripts\remove_schedule.ps1`

**The PC must be on for scheduled tasks to run.** Tasks wake the system when
needed, but sleep/hibernate interrupts. For 24/7 reliability eventually move to
a cloud VM.

## How it decides

Each scan runs this pipeline:

1. **Macro regime** (`src/macro.py`) — SPY trend, VIXY, S&P-500 breadth →
   `risk_on` / `neutral` / `risk_off` with score in [-1, 1].
2. **Technical screen** (`src/technicals.py`) — compute trend + momentum +
   volatility for the broad universe plus seed/dynamic eligibility lists, keep top-N by
   |score|.
3. **Per-symbol deep dive** for those candidates:
   - Fundamentals via yfinance — PE/PEG, rev+eps growth, ROE, debt/equity
   - Sentiment — Alpaca news lexical scoring
   - Risk alignment — penalize long entries in risk_off
4. **Decision engine** (`src/decision.py`) — weighted consensus. Action = BUY
   only if `|combined| ≥ min_confidence` (0.40) **and** ≥ 2 agents agree on
   direction **and** technical agrees.
5. **Position sizing** (`src/risk.py`) — confidence-scaled by entry cap,
   protective-stop risk capped at 0.5% risk per trade, with sector and
   cash-reserve caps.
6. **Execution** — protected order via Alpaca: AI owns the trade decision and
   exact sizing; Python's 1% maximum stop-loss distance is a fixed guardrail,
   not a contradiction. AI may supply a tighter stop or take-profit.

Exits run first in the same scan: existing positions with a technical flip or
deeply negative sentiment get closed.

## Claude subagents (deep research on demand)

`.claude/agents/` has six narrative-reasoning agents that Claude Code can
invoke for deep research beyond the numeric pipeline:

- **macro-analyst** — top-down market regime, Fed, catalysts
- **technical-analyst** — A–D graded chart read with structural S/R
- **fundamental-analyst** — quality/valuation/growth synthesis
- **sentiment-analyst** — news flow, analyst revisions, narrative shifts
- **risk-manager** — portfolio-level accept / reduce / reject
- **decision-arbiter** — integrates the other five into a final call

Use these interactively (ask Claude to "run technical-analyst on NVDA", etc.)
— they are not yet wired into the Python autonomous loop.

## Config

Edit `config.yaml` to tune. Reloaded on every script run.

Key knobs:
- `risk.min_confidence` — higher = stricter, fewer trades (current: 0.40)
- `risk.max_position_pct` — max single-position exposure
- `signals.weights` — rebalance which signal dominates

## Files

```
trading-bot/
├── .env                           # Alpaca creds (gitignored)
├── config.yaml                    # Strategy config
├── dashboard.py                   # CLI status view
├── requirements.txt
├── src/
│   ├── alpaca_client.py           # Wrapped Alpaca SDK
│   ├── config.py                  # .env + config.yaml loader
│   ├── decision.py                # Consensus decision engine
│   ├── executor.py                # Order submission
│   ├── fundamentals.py            # yfinance-based fundamentals
│   ├── journal.py                 # Decision / trade logs
│   ├── logging_setup.py
│   ├── macro.py                   # Regime (SPY / VIXY / breadth)
│   ├── orchestrator.py            # End-to-end pipeline
│   ├── risk.py                    # Sizing + stops + sector caps
│   ├── sentiment.py               # News sentiment
│   ├── technicals.py              # RSI / MACD / ATR / EMA signals
│   └── universe.py                # indexes + seed/dynamic watchlists
├── scripts/
│   ├── eod_report.py              # End-of-day P&L report
│   ├── premarket_brief.py         # 08:30 macro brief
│   ├── remove_schedule.ps1        # Uninstall Windows tasks
│   ├── scan_and_trade.py          # Intraday scan + execute
│   ├── setup_schedule.ps1         # Install Windows tasks
│   └── weekly_review.py           # Friday wrap-up
├── .claude/agents/                # Deep-research subagents for Claude Code
├── data/
│   ├── cache/                     # S&P 500 constituents
│   ├── journal/                   # decisions.jsonl, trades.jsonl
│   ├── research/                  # Saved scan reports
│   └── state/                     # Runtime state
└── logs/                          # Rotating per-script logs
```

## Going from paper → live

When paper proves profitable:
1. Move from Alpaca paper keys to live keys in `.env` (`ALPACA_MODE=live`,
   `ALPACA_BASE_URL=https://api.alpaca.markets`).
2. Re-verify: `py scripts/premarket_brief.py` should show live account
   details.
3. Start with a reduced `risk.max_position_pct` (e.g. 3%) for the first week.

## Security note

The Alpaca keys I was given were pasted in chat. Paper-only, so the blast
radius is one simulated account — but rotate them at
[alpaca.markets/account](https://alpaca.markets/) once you've confirmed
everything works, and I'll update `.env`.
