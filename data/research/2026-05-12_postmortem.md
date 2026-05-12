# Post-Mortem 2026-05-12

## Data availability

| File | Status |
|------|--------|
| `data/research/2026-05-12_eod.json` | ❌ Missing — bot appears offline since 2026-05-04 |
| `data/research/2026-05-04_eod.json` | ✅ Present (last available trading day) |
| `data/research/20260504T190848_scan.json` | ✅ Present |
| `data/research/20260504T195545_preclose.json` | ✅ Present |
| `data/journal/trades.jsonl` | ✅ Present (last entry: 2026-05-04T19:55) |
| `data/journal/decisions.jsonl` | ✅ Present (1,556 entries) |
| Rolling EOD history | ✅ 9 days (2026-04-22 → 2026-05-04) |

> **Note:** No data files exist for 2026-05-05 through 2026-05-12. The bot has been silent for 6 trading days. This post-mortem covers the last active trading day (2026-05-04) and the cumulative period 2026-04-22 → 2026-05-04.

---

## Performance: last active day (2026-05-04) vs SPY

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | **-0.37%** |
| Alpha vs SPY | **-1.43%** ❌ |
| Equity (EOD) | $99,849.69 |
| Cash (EOD) | $4,986.91 (5.0% ≈ floor) |
| Positions at close | 4 (AXTX, META, PWR, SPY) |
| Trades executed | **53** ⚠️ extreme churn |

**Risk budget status (2026-05-04):**
- `cash_reserve_pct` (5%): ✅ barely met ($4,986 / $99,849)
- `max_position_pct` (15% initial cap): ✅ largest new entry was AXTX ~14.4%
- `daily_drawdown` (2.5% limit): ✅ -1.80% within limit on this day alone

---

## Cumulative period performance (2026-04-22 → 2026-05-04, 9 trading days)

| Date | Port | SPY | Alpha |
|------|------|-----|-------|
| 2026-04-22 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | **+1.56%** | -0.39% | **+1.95%** ✅ |
| 2026-04-24 | -0.81% | +0.78% | -1.59% |
| 2026-04-27 | **-4.88%** | +0.17% | **-5.05%** 🚨 |
| 2026-04-28 | **-5.13%** | -0.48% | **-4.65%** 🚨 |
| 2026-04-29 | **-5.40%** | -0.01% | **-5.39%** 🚨 |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | **+1.82%** | +0.29% | **+1.53%** ✅ |
| 2026-05-04 | -1.80% | -0.37% | -1.43% |
| **Cumulative** | **-17.31%** | **+1.96%** | **-19.27%** 🚨 |

> **Critical finding:** Three consecutive days (Apr 27-29) each exceeded the 2.5% daily drawdown limit. The circuit breaker was not triggered. This must be investigated.

---

## Positions at close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | EOD Price | P&L% | MV ($) | Wt% |
|--------|------|-----|-----------|-----------|------|--------|-----|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% | $14,589 | 14.6% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | $9,448 | 9.5% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | $11,130 | 11.1% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | $59,696 | **59.8%** ⚠️ |

> SPY cash-proxy weight of 59.8% is the dominant exposure — a portfolio designed to *beat* SPY is ~60% *in* SPY.

---

## Trades 2026-05-04 (full analysis in Phase 2)

| Symbol | Dir | Qty | Entry | Exit/EOD | P&L% | Note |
|--------|-----|-----|-------|----------|------|------|
| HCAI | SELL | 1,492 | $11.84¹ | $10.69 | **-9.71%** | Exit-arbiter conf=0.72 |
| AMZN | SELL | 65.3 | unknown² | $270.65 | n/a | Arbiter EXIT fading |
| GEV | SELL | 14.6 | $1,140.45¹ | $1,071.49 | **-6.05%** | Arbiter EXIT weak momentum |
| UNH | SELL | 17.3 | $371.09¹ | $368.25 | **-0.77%** | Arbiter EXIT fading vol |
| MU | BUY→SELL | 23.0 | $580.42 | $580.81 | +0.07% | Same-day churn |
| WDC | BUY→SELL | 24.5 | $445.36 | $440.06 | **-1.19%** | Same-day churn |
| DELL | BUY→SELL | 57.4 | $210.52 | $210.94 | +0.20% | Verifier dust-sweep |
| LLY | BUY→SELL | 13.0 | $963.08 | $963.71 | +0.07% | Verifier dust-sweep |
| GOOGL | BUY→SELL | 38.0 | $383.73 | $382.77 | **-0.25%** | Same-day round trip |
| COIN | BUY→SELL | 66.9 | $203.90 | $203.45 | **-0.22%** | Same-day round trip |
| FIX | BUY→SELL | 10.0 | $1,899.17 | $1,902.81 | +0.19% | Verifier dust-sweep |
| AXTX | BUY | 313.0 | $46.41 | $46.61 | +0.43% | HELD |
| META | BUY | 15.5 | $611.73 | $610.46 | -0.21% | HELD |
| PWR | BUY | 14.7 | $758.48 | $757.38 | -0.15% | HELD |

¹ From prior-day EOD; ² No buy record in journal (pre-journal position)

> **(Full analysis appending in next commit)**
