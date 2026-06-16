# Post-Mortem 2026-06-16

## Data availability

| File | Status | Notes |
|------|--------|-------|
| `data/research/2026-06-16_eod.json` | ❌ MISSING | No scan ran today |
| `data/research/20260616T*_scan.json` | ❌ MISSING | No intraday scans |
| Latest EOD on disk | `2026-05-04_eod.json` | 43 calendar days / ~29 trading days stale |
| `data/journal/trades.jsonl` | ✅ Present | 204 lines, last entry `2026-05-04T19:55Z` |
| `data/journal/decisions.jsonl` | ✅ Present | 1,556 lines, last entry `2026-05-04T20:15Z` |
| `data/research/*_daily_review.md` (Jun) | ✅ Present | 2026-06-05, 06-09, 06-11 — all "no-data" |
| Rolling 30d EOD history (for benchmarks) | ⚠️ Partial | 9 days available: 2026-04-22 → 2026-05-04 |

**Critical finding:** The bot has been completely silent for 29 trading days (43 calendar days).
No scans, no trades, no snapshots have been committed since `2026-05-04T20:15Z`.
This is the 7th consecutive "no-data" review.

---

## Performance today (portfolio vs SPY, from eod.json)

> **No data for 2026-06-16.** All metrics below are from the last known EOD: `2026-05-04`.

| Metric | Value | vs Goal |
|--------|-------|----------|
| Last known equity | $99,849.69 | Started ~$99K |
| Last known daily return (5/4) | **-1.80%** | ❌ Below SPY |
| SPY daily return (5/4) | -0.36% | — |
| Portfolio vs SPY (5/4) | **-1.44%** | ❌ underperformed |
| Period return (4/22 → 5/4, 9 days) | **-16.31%** | ❌ far below target |
| SPY same period | **+1.95%** | — |
| Alpha vs SPY (9-day window) | **-18.26%** | ❌ severe underperformance |
| Rolling 5d (4/28 → 5/4) | **-12.66%** | ❌ persistent drawdown |
| SPY rolling 5d | **+0.38%** | — |
| Last known positions | 4 | — |
| Last known trades/day (5/4) | 53 | ⚠️ extremely high |
| Avg trades/day (9-day window) | 22.7 | ⚠️ excessive churn |

**Risk budget status (last known, 2026-05-04):**
- `max_position_pct=0.50`: ✅ SPY=59.8%, AXTX=14.6%, PWR=11.1%, META=9.5%
- `cash_reserve_pct=0.05`: ✅ Cash=$4,987 (5.0% of equity — exactly at floor)
- `daily_drawdown < 2.5%`: ❌ Breached on 4/27 (-4.88%), 4/28 (-5.13%), 4/29 (-5.40%), 4/30 (-2.67%)
- `initial_entry_cap_pct=0.15`: ✅ No single equity position exceeds 15%

---

## Positions at close (last known state: 2026-05-04)

> P&L computed from `avg_entry` and `current_price` per the repo rule. Alpaca `unrealized_plpc` ignored.

| Symbol | Side | Qty | Avg Entry | Last Price | P&L % | Market Value | % Portfolio |
|--------|------|-----|-----------|------------|--------|--------------|-------------|
| AXTX | LONG | 313.00 | $46.41 | $46.61 | **+0.43%** | $14,588.93 | 14.6% |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** | $9,448.36 | 9.5% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** | $11,129.62 | 11.1% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** | $59,695.86 | 59.8% |
| **TOTAL** | | | | | | **$94,862.77** | 95.0% |
| Cash | — | — | — | — | — | $4,986.91 | 5.0% |
| **Equity** | | | | | | **$99,849.69** | |

**Frozen-book exposure (2026-05-04 → 2026-06-16, ~29 trading days):**
The portfolio has been static at this allocation for 29 trading days. Without live prices, P&L since 5/4 cannot be computed from repo data.

---

## Trades today (2026-06-16)

**None — no scan ran.** Last trade activity was 2026-05-04.

| Date | Trades | Events |
|------|--------|--------|
| 2026-04-22 | 7 | 7 order_submitted |
| 2026-04-23 | 9 | 7 rebalance_trade, 2 order_submitted |
| 2026-04-24 | 19 | 13 rebalance, 4 order_submitted, 2 rebalance_failed |
| 2026-04-27 | 24 | 21 rebalance, 3 rebalance_failed |
| 2026-04-28 | 21 | 16 rebalance, 3 rebalance_failed, 2 position_closed |
| 2026-04-29 | 10 | 7 rebalance, 2 order_submitted, 1 position_closed |
| 2026-04-30 | 23 | 4 position_closed, 17 ai_order_failed, 2 order_submitted |
| 2026-05-01 | 38 | 16 ai_order_submitted, 12 position_closed, 9 ai_order_failed, 1 ai_qty_delta |
| 2026-05-04 | 53 | 15 ai_order_submitted, 11 position_closed, 24 exit_learning_metrics, 3 wash_trade_recovery |
| **2026-05-05 → 2026-06-16** | **0** | **Bot silent** |

*(Full analysis appending in next commit)*

---

*Full analysis — section 2a–2d — will be appended in the follow-on commit.*
