# Post-Mortem 2026-06-22

## Data availability

- **Today is Sunday (2026-06-22)** — market closed, no trading activity today.
- Most recent EOD snapshot: **2026-05-04** (last trading day with recorded data).
- EOD history available: 9 trading days (2026-04-22 → 2026-05-04).
- Scan data available: through 2026-05-04 (6 scans on last active day).
- Journal: 204 trades, 1,556 decisions logged across the period.
- No EOD data exists for 2026-05-05 through 2026-06-22 — the bot appears to have stopped producing EOD snapshots after 2026-05-04.
- **This post-mortem covers the full available data window (2026-04-22 → 2026-05-04) with focus on the last active day.**

## Performance summary

### Latest snapshot (2026-05-04)

| Metric | Portfolio | SPY | Delta |
|--------|-----------|-----|-------|
| Daily return | -1.80% | -0.36% | **-1.44%** |
| Equity | $99,850 | — | — |
| Cash | $4,987 (5.0%) | — | — |
| Positions | 4 | — | — |
| Trades today | 53 | — | — |

### Rolling performance (9 trading days)

| Window | Portfolio | SPY | Relative |
|--------|-----------|-----|----------|
| Full period (Apr 22 – May 4) | +0.22% | +1.95% | **-1.73%** |
| Last 5 days (Apr 28 – May 4) | +3.53% | +0.38% | **+3.14%** |
| Max drawdown | -7.12% | — | — |
| Worst single day | -5.40% (Apr 29) | -0.01% | -5.39% |

### Daily breakdown

| Date | Equity | Daily | SPY | vs SPY | Positions | Trades |
|------|--------|-------|-----|--------|-----------|--------|
| 2026-04-22 | $99,627 | +0.00% | +1.01% | -1.01% | 7 | 7 |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | +1.95% | 10 | 9 |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.58% | 12 | 19 |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05% | 8 | 24 |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.64% | 4 | 21 |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39% | 5 | 10 |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | -3.63% | 3 | 23 |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53% | 4 | 38 |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | -1.44% | 4 | 53 |

### Risk budget compliance

| Constraint | Limit | Actual | Status |
|------------|-------|--------|--------|
| Cash reserve | ≥ 5% | 5.0% ($4,987) | ✅ Barely met |
| Max drawdown (daily) | < 2.5% | -5.40% (Apr 29) | ❌ **BREACHED** |
| Max drawdown (period) | — | -7.12% | ⚠️ Severe |
| Initial entry cap | ≤ 15% | See trade table | Mixed |
| Max position | ≤ 50% | SPY 59.8% | ❌ **BREACHED** (SPY proxy) |

## Positions at close (2026-05-04)

| Symbol | Side | Avg Entry | Current | P&L % | P&L $ | Value | % Equity |
|--------|------|-----------|---------|-------|-------|-------|----------|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | +$63 | $14,589 | 14.6% |
| META | LONG | $611.73 | $610.46 | -0.21% | -$20 | $9,448 | 9.5% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | -$16 | $11,130 | 11.1% |
| SPY | LONG | $717.52 | $718.03 | +0.07% | +$42 | $59,696 | 59.8% |
| **Cash** | — | — | — | — | — | **$4,987** | **5.0%** |

## Trades on 2026-05-04 (53 total, 29 meaningful)

| # | Symbol | Action | Qty | Price | Reason (abbreviated) | Verdict |
|---|--------|--------|-----|-------|---------------------|----------|
| 1 | HCAI | SELL (exit) | 1,492 | $10.69 | Down -8.78%, 5 intraday momentum-loss signals | **Good** — cut loser |
| 2 | AMZN | SELL (exit) | 65.3 | $270.65 | Fading momentum, below VWAP, bearish EMA | Churn — bought & sold same day |
| 3 | GEV | SELL (exit) | 14.6 | $1,071.49 | Weak momentum, below VWAP, bearish EMA | Churn — bought & sold same day |
| 4 | UNH | SELL (exit) | 17.3 | $368.25 | Fading volume, LLY stronger healthcare name | Churn — replaced too fast |
| 5 | LLY | BUY | 9.5 | $963.38 | Healthcare sector leader, strong continuation | Bad — bought then sold same day |
| 6 | MU | ADD | 25.0 | $580.42 | Pool leader, INCREASE to 28% target | Oversized — then sold |
| 7 | NOK | BUY | 367.2 | $13.33 | Sector diversifier, strong continuation | Bad — gone by end of day |
| 8 | SNDK | BUY | 10.1 | $1,246.97 | Memory sector, bullish EMA | Bad — rotated out quickly |
| 9 | MU | SELL (exit) | 23.0 | $580.81 | Weak/flat momentum, WDC scores higher | Churn — just added then sold |
| 10 | DELL | BUY | 57.4 | $210.52 | IT sector leader, momentum 95 | Bad — dust-swept same day |
| 11 | FIX | BUY | 6.3 | $1,896.50 | ai_data_center leader, momentum 91 | Bad — sold same day |
| 12 | GOOGL | BUY | 28.7 | $383.51 | Comms leader, acceptable continuation | Bad — sold same day |
| 13 | LLY | ADD | 3.5 | $962.27 | Increase to 12.5% | Bad — wash trade recovery, sold same day |
| 14 | WDC | BUY | 24.5 | $445.36 | Memory peer leader displacing MU | Bad — exit thesis broken same session |
| 15 | COIN | ADD | 5.1 | $203.90 | Verifier reconcile to 14.8% target | Bad — sold same day |
| 16 | WDC | SELL (exit) | 24.5 | $440.06 | Gap only, bearish EMA, below VWAP | Churn — entry thesis broken hours later |
| 17 | FIX | ADD | 3.7 | $1,903.71 | Increase to 19% (momentum 100) | Bad — wash trade, dust-swept |
| 18 | DELL | SELL (dust) | 57.4 | $210.94 | Verifier dust-sweep target=0 | — |
| 19 | LLY | SELL (dust) | 13.0 | $963.71 | Verifier dust-sweep target=0 | — |
| 20 | GOOGL | ADD | 9.3 | $384.43 | Verifier reconcile to 14.6% | Bad — wash trade, sold same day |
| 21 | FIX | SELL (dust) | 10.0 | $1,902.81 | Verifier dust-sweep target=0 | — |
| 22 | COIN | SELL (exit) | 66.9 | $203.45 | Momentum 0, fading, earnings in 3d | Churn — just added then sold |
| 23 | GOOGL | SELL (exit) | 38.0 | $382.77 | Momentum 0, fading, below EMA20 | Churn — bought and exited same day |
| 24 | AXTX | BUY | 313.0 | $46.41 | Momentum 100, breaking out | Held — only survivor |
| 25 | META | BUY | 15.5 | $611.73 | Comms leader, acceptable continuation | Held |
| 26 | PWR | BUY | 14.7 | $758.48 | ai_data_center peer leader | Held |

*(Full analysis appending in next commit)*
