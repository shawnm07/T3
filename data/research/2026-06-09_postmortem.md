# Post-Mortem 2026-06-09

## Data Availability

| Source | Status | Notes |
|--------|--------|-------|
| `2026-06-09_eod.json` | **MISSING** | Bot has been dormant since 2026-05-04 |
| `20260609*_scan.json` | **MISSING** | No scans ran today |
| `data/journal/trades.jsonl` | Present | Last entry: 2026-05-04 |
| `data/journal/decisions.jsonl` | Present | Last entry: 2026-05-04 |
| `config.yaml` | Present | Baseline for proposals |
| Historical EOD (9 days) | Present | 2026-04-22 → 2026-05-04 |

**Critical finding:** The bot has been completely dormant for ~26 calendar days (~18 trading days) between 2026-05-04 and 2026-06-09. No trades, no scans, no EOD snapshots exist for this period. All analysis below is based on the last active trading session (2026-05-04) and the available historical window (2026-04-22 → 2026-05-04).

---

## Performance Today (Portfolio vs SPY)

*No data for 2026-06-09. Reporting last-known state from 2026-05-04.*

| Metric | Value |
|--------|-------|
| Last known equity | $99,849.69 |
| Daily return (2026-05-04) | **-1.80%** |
| SPY daily (2026-05-04) | -0.36% |
| Daily vs SPY | **-1.43%** |
| 30-day portfolio return | ~0.22% ($99,627 → $99,850) |
| 30-day SPY return | **+10.71%** (from `spy_30d` field) |
| 30-day alpha | **-10.49%** |
| Cash position | $4,987 (5.0% of equity) |

### Rolling Returns (from EOD history)

| Window | Portfolio | SPY | Alpha |
|--------|-----------|-----|-------|
| 5-day (04-28→05-04) | -12.67% | +0.38% | **-13.05%** |
| 9-day (04-22→05-04) | +0.22% | +10.71% | **-10.49%** |

### Daily Return Series

| Date | Portfolio | SPY | vs SPY |
|------|-----------|-----|--------|
| 2026-04-22 | 0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | **+1.95%** |
| 2026-04-24 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | -4.88% | +0.17% | **-5.05%** |
| 2026-04-28 | -5.13% | -0.49% | -4.65% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.43% |

---

## Positions at Last Close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | Close Price | P&L % | P&L $ | Weight |
|--------|------|-----|-----------|-------------|-------|-------|--------|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** | +$62.60 | 14.6% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$19.63 | 9.5% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | -$16.16 | 11.1% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42.40 | **59.8%** |

*P&L computed as (current_price - avg_entry) / avg_entry per instructions. Alpaca's unrealized_plpc disregarded.*

SPY is 59.8% of portfolio — effectively the bot is running ~60% as a market-tracking cash proxy.

---

## Trades Last Active Day (2026-05-04)

**53 trades executed on 2026-05-04** (highest churn day in the dataset).

Key events from `trades.jsonl` (last active session):

| Event | Symbol | Side | Price | Reason Summary |
|-------|--------|------|-------|----------------|
| EXIT | GEV | SELL | $1,071.49 | Weak momentum, below VWAP, bearish EMA |
| EXIT | UNH | SELL | $368.25 | Fading volume; LLY preferred as healthcare name |
| BUY | LLY | BUY | $963.38 | Strong continuation; healthcare sector leader |
| ROTATION | FIX,CUE,COIN,PWR,GOOGL,RBLX | — | — | Selector rotated 3 in, 3 out (WDC/LLY/DELL exited) |
| EXIT | WDC | SELL | — | Gap-only classification, thesis broken |
| EXIT | LLY | SELL | — | Fading momentum score 53 (entered and exited same session) |

*LLY was entered and then exited within the same scan cycle — a wash trade.*

Trade count per day: 7, 9, 19, 24, 21, 10, 23, 38, 53. Accelerating churn.

---

## (Full analysis appending in next commit)
