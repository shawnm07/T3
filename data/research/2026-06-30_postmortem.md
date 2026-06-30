# Post-Mortem 2026-06-30

## Data Availability

**⚠️ EIGHTH CONSECUTIVE NO-DATA REPORT.** No trading data exists for 2026-06-30 or for any date since 2026-05-04 (~57 calendar days / ~40 trading days of silence). All performance analysis below references the **last available snapshot: 2026-05-04 EOD**.

| Source | Newest on disk | Status |
|---|---|---|
| `_eod.json` | `2026-05-04_eod.json` | **57-day gap** |
| `_scan.json` | `20260504T195545_preclose.json` | **57-day gap** |
| `trades.jsonl` | last event `2026-05-04T19:55Z` (204 lines) | **frozen** |
| `decisions.jsonl` | last event `2026-05-04T20:15Z` (1556 lines) | **frozen** |
| `_daily_review.md` | `2026-06-23_daily_review.md` | 7 prior no-data reports |

Root cause (unchanged from prior reviews): `scan_and_trade.py` and related scripts have not run since 2026-05-04. Alpaca account PA34KBGT3V7E likely still holds the 5/4 end-of-day positions frozen for ~40 trading days.

---

## Performance Today (2026-06-30)

**No snapshot available.** Last known equity: **$99,850** (2026-06-30 has no EOD file).

### Last Known Day (2026-05-04)

| Metric | Bot | SPY | Delta |
|---|---|---|---|
| Daily return | **-1.80%** | -0.36% | **-1.44%** |
| Equity | $99,850 | — | — |
| Cash | $4,987 (5.0%) | — | ✓ at floor |
| Positions | 4 | — | — |

### Rolling Benchmark (all 9 tracked days: 2026-04-22 → 2026-05-04)

| Period | Bot | SPY | Alpha |
|---|---|---|---|
| 9-day cumulative | **-16.31%** | +1.95% | **-18.26%** |
| Last 5d (4/28–5/4) | -12.66% | +0.38% | -13.04% |
| SPY 30-day (as of 5/4) | — | +10.71% | — |

> Bot is deeply underwater vs SPY on every measured horizon.

---

## Positions at Close (Last Known: 2026-05-04 EOD)

Computed from `avg_entry` and `current_price` per hard rule (Alpaca `unrealized_plpc` not trusted).

| Symbol | Side | Qty | Avg Entry | Last Price | P&L% | Market Value | Weight |
|---|---|---|---|---|---|---|---|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** | $14,589 | 14.6% |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** | $9,448 | 9.5% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** | $11,130 | 11.1% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** | $59,696 | 59.7% |
| Cash | — | — | — | — | — | $4,987 | 5.0% |

> Book has been **frozen at this allocation for ~40 trading days** with no confirmed activity.

---

## Trades Today (2026-06-30)

**No trades logged.** Last active trading day: 2026-05-04 (53 events across 17 symbols).

### Summary of Last Active Day (2026-05-04)

| Event type | Count |
|---|---|
| `ai_order_submitted` (entries) | 15 |
| `position_closed` (exits) | 11 |
| `wash_trade_recovery` | 3 |
| `exit_learning_metrics` | 24 |
| **Total** | **53** |

Unique symbols touched: AMZN, AXTX, COIN, DELL, FIX, GEV, GOOGL, HCAI, LLY, META, MU, NOK, PWR, SNDK, STX, UNH, WDC (17 names in one session).

---

## (Full analysis appending in next commit)
