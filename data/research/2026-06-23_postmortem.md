# Post-Mortem 2026-06-23

## Data Availability

| Source | Status |
|--------|--------|
| EOD snapshot (today 2026-06-23) | **MISSING** — last available: 2026-05-04 |
| Scan files (today) | **MISSING** — last scans: 2026-05-04 |
| Trade journal | Available (204 entries through 2026-05-04) |
| Decision journal | Available (1556 entries through 2026-05-04) |
| config.yaml | Available |
| Alpaca API | BLOCKED (403) |
| yfinance / Telegram | BLOCKED |

> **Note:** The bot has not traded since 2026-05-04 (50 calendar days ago). This post-mortem analyzes the last trading day with data (2026-05-04) and the full 9-day active period (2026-04-22 → 2026-05-04). No live position data is available for today.

---

## Performance — Last Trading Day (2026-05-04)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily alpha | **-1.44%** |
| Equity at close | $99,849.69 |
| Cash | $4,986.91 (5.0% — at floor) |
| Positions held | 4 |
| Trades executed | 53 |

## Rolling Benchmarks (9 trading days: 2026-04-22 → 2026-05-04)

| Metric | Portfolio | SPY | Alpha |
|--------|-----------|-----|-------|
| Full period | +0.22% | +1.95% | **-1.73%** |
| 5-day rolling | -12.66% | +0.38% | **-13.04%** |
| Max drawdown | -7.12% | — | — |
| Avg daily trades | 22.7 | — | — |

### Equity Curve

```
Date         Equity       Daily%   SPY%    vs SPY   Pos  Trades
──────────────────────────────────────────────────────────────────
2026-04-22    $99,627    +0.00%   +1.01%   -1.01%    7      7
2026-04-23   $101,208    +1.56%   -0.39%   +1.95%   10      9
2026-04-24    $99,343    -0.81%   +0.77%   -1.59%   12     19
2026-04-27    $96,448    -4.88%   +0.17%   -5.05%    8     24
2026-04-28    $96,867    -5.13%   -0.49%   -4.65%    4     21
2026-04-29    $93,999    -5.40%   -0.01%   -5.39%    5     10
2026-04-30    $95,786    -2.67%   +0.96%   -3.63%    3     23
2026-05-01   $101,101    +1.82%   +0.29%   +1.53%    4     38
2026-05-04    $99,850    -1.80%   -0.36%   -1.44%    4     53
```

---

## Positions at Close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | Current | P&L % | P&L $ | Mkt Value |
|--------|------|-----|-----------|---------|-------|-------|----------|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% | +$62.60 | $14,588.93 |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$19.63 | $9,448.36 |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | -$16.16 | $11,129.62 |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42.40 | $59,695.86 |
| **Total** | | | | | | **+$69.21** | **$94,862.77** |

Cash: $4,986.91 | Equity: $99,849.69

---

## Trades on 2026-05-04 (53 total — 11 closes, 0 opens)

### Position Closes

| Symbol | Qty | Fill Price | Reason (truncated) |
|--------|-----|-----------|-------------------|
| HCAI | 1,492 | $10.69 | Exit-arbiter (conf=0.72): Down -8.78%, lost VWAP/EMA20, fading |
| AMZN | 65.30 | $270.65 | Selector EXIT: Fading momentum, below VWAP, bearish EMA |
| GEV | 14.57 | $1,071.49 | Selector EXIT: Weak momentum, below VWAP, bearish EMA, flat trend |
| UNH | 17.27 | $368.25 | Selector EXIT: Fading volume, low continuation score |
| MU | 23.01 | $580.81 | Selector EXIT: Weak momentum, bearish EMA, flat volume |
| WDC | 24.51 | $440.06 | Selector EXIT: Gap-only classification, bearish EMA, fading |
| DELL | 57.39 | $210.94 | Verifier dust-sweep (target=0) |
| LLY | 13.00 | $963.71 | Verifier dust-sweep (target=0) |
| COIN | 66.90 | $203.45 | Selector EXIT: Momentum=0, fading, earnings in 3 days |
| GOOGL | 37.96 | $382.77 | Selector EXIT: Momentum=0, fading, below EMA20 |
| FIX | 10.00 | $1,902.81 | Verifier dust-sweep (target=0) |

### New Entries Attempted but Blocked

| Symbol | Target % | Reason Blocked |
|--------|----------|---------------|
| LLY | 10.2% | stop_not_below_current_market (bid/ask spread too wide) |
| SNDK | 12.3% | insufficient_confirmed_cash |
| SOXS | 9.0% | stop_not_below_current_market (inverse ETF, tech_score=-0.99) |

---

## Full Analysis

*(Appended in next commit)*
