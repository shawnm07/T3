# Post-Mortem 2026-07-23

> **17th consecutive no-data cycle.** The last live snapshot remains `2026-05-04_eod.json` — ~57 trading days / 80 calendar days of trading silence. Analysis below is based entirely on on-disk artifacts.

---

## Data availability

| Source | Status | Last entry |
|---|---|---|
| `_eod.json` | **Stale** | `2026-05-04_eod.json` |
| `*_scan.json` | **Stale** | `20260504T190848_scan.json` |
| `*_preclose.json` | **Stale** | `20260504T195545_preclose.json` |
| `trades.jsonl` | **Stale** | `2026-05-04T19:55:03Z` (204 lines) |
| `decisions.jsonl` | **Stale** | `2026-05-04T20:15:04Z` (1556 lines) |
| Today's `2026-07-23_eod.json` | **MISSING** | — |
| Market data egress (AV / yfinance / TD) | **BLOCKED** | 403 at proxy for all three |
| Alpaca API | **BLOCKED** | 403 |

No `20260505T*` → `20260723T*` scan, preclose, or EOD files exist. The trading scheduler has been silent for **80 calendar days** since the last live scan (2026-05-04 ~20:00 UTC).

---

## Performance today (portfolio vs SPY, from eod.json)

**No 2026-07-23 data.** Figures below are the last known state (2026-05-04):

| Metric | Value |
|---|---|
| Equity | $99,849.69 |
| Cash | $4,986.91 (~5.0%) |
| Daily return (5/4) | **-1.80%** |
| SPY daily (5/4) | -0.36% |
| Daily vs SPY (5/4) | **-1.43%** |
| SPY 30d (at 5/4) | +10.71% |
| Period return vs SPY (at 5/4) | **-10.71%** |
| Positions | 4 |
| Trades on 5/4 | 53 |

---

## Positions at close (last known — 2026-05-04)

| Symbol | Side | Avg Entry | Price (5/4) | PnL% | Mkt Value | Alloc% |
|---|---|---|---|---|---|---|
| SPY | LONG | $717.52 | $718.03 | +0.07% | $59,695.86 | 59.8% |
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,588.93 | 14.6% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,129.62 | 11.1% |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448.36 | 9.5% |
| **Cash** | — | — | — | — | $4,986.91 | 5.0% |
| **Total** | | | | | $99,862.68 | 100% |

> Note: PnL% computed from `avg_entry` and `current_price` per instructions (Alpaca `unrealized_plpc` not trusted).

---

## Trades today (table)

**No 2026-07-23 trade data.** Last session (2026-05-04) logged 53 trades — dominated by entries/exits across MU, DELL, AXTX, PWR, META, SPY during intraday churn. Detailed table in Phase 2 below.

---

## Rolling performance (all available EOD data)

| Date | Equity | Daily | SPY Daily | vs SPY | Positions | Trades |
|---|---|---|---|---|---|---|
| 2026-04-22 | $99,627 | +0.00% | +1.01% | **-1.01%** | 7 | 7 |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | **+1.95%** | 10 | 9 |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | **-1.59%** | 12 | 19 |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | **-5.05%** | 8 | 24 |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | **-4.65%** | 4 | 21 |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | **-5.39%** | 5 | 10 |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | **-3.63%** | 3 | 23 |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | **+1.53%** | 4 | 38 |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | **-1.43%** | 4 | 53 |

**9-day aggregate (4/22 → 5/4, all available data):**
- Portfolio: $99,627 → $99,850 = **+0.22%**
- SPY proxy: daily returns compound to approximately **+2.96%** over same period
- Net alpha: approximately **-2.74%** over 9 trading days

---

## (Full analysis appending in next commit)
