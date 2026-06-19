# Post-Mortem 2026-06-19

## Data Availability

| Source | Status | Latest Entry |
|---|---|---|
| `_eod.json` | **STALE** — 46 calendar days old | `2026-05-04_eod.json` |
| Intraday scans | **STALE** | `20260504T190848_scan.json` |
| Preclose | **STALE** | `20260504T195545_preclose.json` |
| `trades.jsonl` | 204 lines, last entry 2026-05-04 | `position_closed COIN 19:55 UTC` |
| `decisions.jsonl` | 1,556 lines, last entry 2026-05-04 | `eod_report 20:15 UTC` |
| **Today (2026-06-19)** | **NO DATA** | — |

**Critical:** The bot has produced zero artifacts for ~33 trading days. This post-mortem uses the last known state (2026-05-04) as the reference point.

## Performance (last known period: 2026-04-22 → 2026-05-04, 9 trading days)

| Metric | Portfolio | SPY | vs SPY |
|---|---|---|---|
| **Full period return** (equity-based) | +0.22% | +1.95% | **-1.73%** |
| **Last 5 trading days** (4/28→5/4, equity-based) | +3.08% | +0.38% | +2.70% |
| **Last day** (5/4) | -1.24% | -0.36% | **-0.88%** |
| Equity (start → end) | $99,627 → $99,850 | — | — |
| SPY 30d benchmark (per 5/4 snapshot) | — | +10.71% | **-10.49% vs SPY 30d** |

### Equity Curve (daily)

| Date | Equity | Day Δ | SPY Day | vs SPY | Positions | Trades |
|---|---|---|---|---|---|---|
| 2026-04-22 | $99,627 | — | +1.01% | -1.01% | 7 | 7 |
| 2026-04-23 | $101,208 | +1.59% | -0.39% | +1.98% | 10 | 9 |
| 2026-04-24 | $99,343 | -1.84% | +0.77% | -2.61% | 12 | 19 |
| 2026-04-27 | $96,448 | -2.91% | +0.17% | -3.08% | 8 | 24 |
| 2026-04-28 | $96,867 | +0.43% | -0.49% | +0.92% | 4 | 21 |
| 2026-04-29 | $93,999 | -2.96% | -0.01% | -2.95% | 5 | 10 |
| 2026-04-30 | $95,786 | +1.90% | +0.96% | +0.94% | 3 | 23 |
| 2026-05-01 | $101,101 | +5.55% | +0.29% | +5.26% | 4 | 38 |
| 2026-05-04 | $99,850 | -1.24% | -0.36% | -0.88% | 4 | 53 |

**Daily drawdown breaches:** 4/27 (-2.91%), 4/29 (-2.96%) exceed the 2.5% daily_drawdown target.

## Positions at Close (2026-05-04, last known)

| Symbol | Side | Qty | Avg Entry | Current | P&L % | P&L $ | Mkt Value | Weight |
|---|---|---|---|---|---|---|---|---|
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42 | $59,696 | 59.8% |
| AXTX | LONG | 313 | $46.41 | $46.61 | +0.43% | +$63 | $14,589 | 14.6% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | -$16 | $11,130 | 11.1% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$20 | $9,448 | 9.5% |
| **Cash** | — | — | — | — | — | — | $4,987 | 5.0% |

**Concentration:** 59.8% in SPY proxy (idle capital). Three active longs total 35.2% of equity. Cash at 5.0% (at floor).

## Trades on 2026-05-04 (last active day)

53 trade events. Summary of meaningful actions:

| Time (UTC) | Symbol | Action | Qty | Entry/Stop | Outcome |
|---|---|---|---|---|---|
| 14:51 | HCAI | EXIT | 1,492 | — | Closed (was -8.78%) |
| 16:04 | AMZN | EXIT | — | — | Closed (bought earlier by selector) |
| 16:04 | GEV | EXIT | — | — | Closed (bought earlier by selector) |
| 16:04 | UNH | EXIT | — | — | Closed (bought earlier by selector) |
| 16:04 | LLY | BUY | 9.49 | $961.30 / $951.69 | Closed same day |
| 16:04 | MU | ADD | 25.0 | $583.49 / $577.65 | Closed 17:04 |
| 16:04 | NOK | BUY | 367.24 | $13.38 / $13.24 | Closed 17:04 |
| 16:04 | SNDK | BUY | 10.10 | $1250.12 / $1237.62 | Held → EOD position |
| 17:04 | DELL | BUY | 57.39 | $209.91 / $207.81 | Closed 18:05 |
| 17:04 | FIX | BUY | 6.30 | $1884.10 / $1865.26 | Closed 19:08 |
| 17:04 | GOOGL | BUY | 28.68 | $382.82 / $378.99 | Closed 19:08 |
| 17:04 | LLY | ADD | 3.51 | $962.24 / $952.61 | Closed 18:05 (wash trade) |
| 17:04 | WDC | BUY | 24.51 | $442.28 / $437.86 | Closed 18:05 |
| 17:04 | COIN | BUY | 5.10 | — | Closed 19:08 |
| 19:08 | AXTX | BUY | 313.0 | $45.80 / $45.34 | **Held** → EOD |
| 19:08 | META | BUY | 15.48 | $612.19 / $606.07 | **Held** → EOD |
| 19:08 | PWR | BUY | 14.69 | $756.10 / $748.54 | **Held** → EOD |

**11 symbols bought and exited same day.** Only AXTX, META, PWR survived to EOD.

*(Full analysis appending in next commit)*
