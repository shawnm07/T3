# Trading Bot — Multi-Agent, Alpaca Paper

Autonomous trading bot that tries to beat the S&P 500. Runs research multiple
times a day, trades only on high-conviction multi-signal consensus, risk-sized
with ATR stops, paper mode against Alpaca.

## Status snapshot

| Field | Value |
| --- | --- |
| Mode | paper (Alpaca) |
| Benchmark | SPY |
| Risk profile | balanced (max 20% drawdown, max 6 positions) |
| Assets | US long + short + crypto (BTC/ETH/SOL) |
| Cadence | swing — research 2-4× weekdays, crypto every 4h |
| Kill switch | weekly dd ≥ 5% pauses new entries; trades > $10K need approval |

## Quick commands

All commands assume working dir = this folder.

```
py dashboard.py                               # status: positions, P&L, kill switch, pending approvals
py scripts/scan_and_trade.py --dry-run        # what would we trade right now?
py scripts/scan_and_trade.py --force          # run it (force = ignore market-hours check)
py scripts/premarket_brief.py                 # macro brief + cancel stale orders
py scripts/eod_report.py                      # today's P&L vs SPY
py scripts/weekly_review.py                   # weekly P&L vs SPY
py scripts/crypto_check.py --dry-run          # crypto scan (24/7)

py scripts/approve.py                         # list pending large-trade approvals
py scripts/approve.py --id <ID> yes           # approve + execute
py scripts/approve.py --id <ID> no            # reject

py scripts/halt.py pause "reason"             # emergency stop new entries
py scripts/halt.py resume                     # re-enable
py scripts/halt.py                            # show current halt status
```

## Autonomous schedule (Windows Task Scheduler)

1. Right-click PowerShell → **Run as Administrator**.
2. `cd C:\Users\shawn\OneDrive\Documents\Tim\trading-bot`
3. `.\scripts\setup_schedule.ps1`

Registers these at **local time** (adjust if not US/Eastern — see top of
`setup_schedule.ps1`):

| Task | When | Script |
| --- | --- | --- |
| TradingBot_PreMarket | Mon-Fri 08:30 | `premarket_brief.py` |
| TradingBot_Scan_1000 | Mon-Fri 10:00 | `scan_and_trade.py` |
| TradingBot_Scan_1200 | Mon-Fri 12:00 | `scan_and_trade.py` |
| TradingBot_Scan_1400 | Mon-Fri 14:00 | `scan_and_trade.py` |
| TradingBot_Scan_1530 | Mon-Fri 15:30 | `scan_and_trade.py` |
| TradingBot_EOD | Mon-Fri 16:15 | `eod_report.py` |
| TradingBot_WeeklyReview | Fri 17:00 | `weekly_review.py` |
| TradingBot_Crypto | every 4h, 24/7 | `crypto_check.py` |

Scripts call `clock.is_open` and no-op when market is closed, so the scan tasks
are safe to miss a few minutes either side.

To remove: `.\scripts\remove_schedule.ps1`

**The PC must be on for scheduled tasks to run.** Tasks wake the system when
needed, but sleep/hibernate interrupts. For 24/7 reliability eventually move to
a cloud VM.

## How it decides

Each scan runs this pipeline:

1. **Kill switch check** — daily dd, weekly dd, trade count, manual halt.
2. **Macro regime** (`src/macro.py`) — SPY trend, VIXY, S&P-500 breadth →
   `risk_on` / `neutral` / `risk_off` with score in [-1, 1].
3. **Technical screen** (`src/technicals.py`) — compute trend + momentum +
   volatility for the entire S&P 500 + custom watchlist, keep top-N by
   |score|.
4. **Per-symbol deep dive** for those candidates:
   - Fundamentals via yfinance — PE/PEG, rev+eps growth, ROE, debt/equity
   - Sentiment — Alpaca news lexical scoring
   - Risk alignment — penalize longs in risk_off, shorts in risk_on
5. **Decision engine** (`src/decision.py`) — weighted consensus. Action = BUY
   only if `|combined| ≥ min_confidence` (0.40) **and** ≥ 2 agents agree on
   direction **and** technical agrees.
6. **Position sizing** (`src/risk.py`) — confidence-scaled up to 7% of equity,
   ATR-based stop (2× ATR) and target (4× ATR), capped at 0.5% risk per
   trade, sector cap 30%.
7. **Approval gate** — any trade > $10K → `data/journal/pending_approvals.jsonl`
   for manual approval.
8. **Execution** — bracket order (entry + stop + target) via Alpaca.

Exits run first in the same scan: existing positions with a technical flip or
deeply negative sentiment get closed.

## Claude subagents (deep research on demand)

`.claude/agents/` has six narrative-reasoning agents that Claude Code can
invoke for deep research beyond the numeric pipeline:

- **macro-analyst** — top-down market regime, Fed, catalysts
- **technical-analyst** — A–D graded chart read with structural S/R
- **fundamental-analyst** — quality/valuation/growth synthesis
- **sentiment-analyst** — news flow, analyst revisions, narrative shifts
- **risk-manager** — portfolio-level veto / reduce / approve
- **decision-arbiter** — integrates the other five into a final call

Use these interactively (ask Claude to "run technical-analyst on NVDA", etc.)
— they are not yet wired into the Python autonomous loop.

## Config

Edit `config.yaml` to tune. Reloaded on every script run.

Key knobs:
- `risk.min_confidence` — higher = stricter, fewer trades (current: 0.40)
- `risk.max_position_pct` — max single-position exposure (current: 7%)
- `kill_switch.weekly_drawdown_pct` — auto-pause threshold
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
│   ├── executor.py                # Order submission + approval gate
│   ├── fundamentals.py            # yfinance-based fundamentals
│   ├── journal.py                 # Decision / trade / approval logs
│   ├── kill_switch.py             # Circuit breakers
│   ├── logging_setup.py
│   ├── macro.py                   # Regime (SPY / VIXY / breadth)
│   ├── orchestrator.py            # End-to-end pipeline
│   ├── risk.py                    # Sizing + stops + sector caps
│   ├── sentiment.py               # News sentiment
│   ├── technicals.py              # RSI / MACD / ATR / EMA signals
│   └── universe.py                # S&P 500 + watchlist
├── scripts/
│   ├── approve.py                 # Approve pending trades
│   ├── crypto_check.py            # Crypto scan (24/7)
│   ├── eod_report.py              # End-of-day P&L report
│   ├── halt.py                    # Manual kill switch
│   ├── premarket_brief.py         # 08:30 macro brief
│   ├── remove_schedule.ps1        # Uninstall Windows tasks
│   ├── scan_and_trade.py          # Intraday scan + execute
│   ├── setup_schedule.ps1         # Install Windows tasks
│   └── weekly_review.py           # Friday wrap-up
├── .claude/agents/                # Deep-research subagents for Claude Code
├── data/
│   ├── cache/                     # S&P 500 constituents
│   ├── journal/                   # decisions.jsonl, trades.jsonl, approvals
│   ├── research/                  # Saved scan reports
│   └── state/                     # Kill switch + trade counter
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
