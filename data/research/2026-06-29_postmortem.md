# Post-Mortem 2026-06-29

> Analysis covers the most recent trading day with data: **2026-05-04** (Monday).
> Today (2026-06-29) is a Sunday; no trading occurred. All data sourced from repo files.

## Data Availability

| Source | Status |
|--------|--------|
| `2026-05-04_eod.json` | Available — 4 positions at close |
| `20260504T*_scan.json` | 6 scan files available |
| `decisions.jsonl` | 105 decisions on 2026-05-04 |
| `trades.jsonl` | 53 trade events on 2026-05-04 |
| EOD history (rolling) | 9 files: 2026-04-22 → 2026-05-04 |
| Alpaca / yfinance / Telegram | Blocked (sandbox) |

## Performance: 2026-05-04

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | **-0.36%** |
| Daily vs SPY | **-1.43%** (underperformed) |
| Equity at close | $99,849.69 |
| Cash at close | $4,986.91 (5.0% — at floor) |
| Trades executed | 53 |
| Positions at close | 4 |

### Rolling Performance (from available EOD files)

| Date | Equity | Daily Return | SPY Daily | vs SPY | Positions |
|------|--------|-------------|-----------|--------|----------|
| 2026-04-22 | $99,627 | 0.00% | +1.01% | -1.01% | 7 |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | +1.95% | 10 |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.58% | 12 |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05% | 8 |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.64% | 4 |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39% | 5 |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | -3.63% | 3 |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53% | 4 |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | -1.43% | 4 |

**5-day return** (Apr 28 → May 4): +3.08% vs SPY ~+0.39% → **+2.69%**
**9-day cumulative**: -0.23% equity return vs SPY ~+10.71% → **-10.94% underperformance**

## Positions at Close

| Symbol | Side | Qty | Avg Entry | Current | P&L % | P&L $ | Mkt Value | Weight |
|--------|------|-----|-----------|---------|-------|-------|-----------|--------|
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42 | $59,696 | 59.8% |
| AXTX | LONG | 313 | $46.41 | $46.61 | +0.43% | +$63 | $14,589 | 14.6% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | -$16 | $11,130 | 11.1% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$20 | $9,448 | 9.5% |

**Total equity positions**: $35,167 (35.2%) + SPY cash proxy $59,696 (59.8%) + cash $4,987 (5.0%)

## Trades on 2026-05-04

| Time (UTC) | Event | Symbol | Notes |
|------------|-------|--------|-------|
| 14:51 | CLOSED | HCAI | Exit arbiter: -8.78%, momentum loss confirmed |
| 15:13 | ROTATION | — | Selected: AMZN, GEV, COIN, MU, UNH. Exited: SNDK, STX |
| 15:18 | ROTATION | — | Added: MU, META, UNH, BAND. Held: AMZN, COIN |
| 16:04 | ROTATION | — | Selected: MU, COIN, SNDK, LLY, NOK, V. Exited: GEV, AMZN, UNH |
| 16:04 | CLOSED | AMZN, GEV, UNH | — |
| 16:04 | BOUGHT | LLY, MU, NOK, SNDK | — |
| 17:04 | ROTATION | — | Selected: FIX, DELL, WDC, GOOGL, COIN, LLY. Exited: MU |
| 17:04 | CLOSED | MU | — |
| 17:04 | BOUGHT | DELL, FIX, GOOGL, WDC, COIN | wash_trade: LLY |
| 18:04 | ROTATION | — | Selected: FIX, CUE, COIN, PWR, GOOGL, RBLX. Exited: WDC, LLY, DELL |
| 18:05 | CLOSED | WDC, DELL, LLY | — |
| 18:05 | BOUGHT | FIX, GOOGL | wash_trade: FIX, GOOGL |
| 19:08 | ROTATION | — | Selected: AXTX, SNDK, PWR, LLY, META, SOXS. Exited: FIX, GOOGL, COIN |
| 19:08 | CLOSED | COIN, GOOGL, FIX | — |
| 19:08 | BOUGHT | AXTX, META, PWR | — |

*(Full analysis appending in next commit)*
