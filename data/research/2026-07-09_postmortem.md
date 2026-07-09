# Post-Mortem 2026-07-09

## Data Availability

**Critical: No live trading data exists for 2026-07-09 (or any date 2026-05-05 through 2026-07-09).**

The bot has produced zero artifacts for ~45 trading days / 66 calendar days. The newest data on disk is `2026-05-04_eod.json`. This post-mortem grades the **last active session (2026-05-04)** and documents the operational outage.

| Source | Newest entry | Status |
|---|---|---|
| `_eod.json` | `2026-05-04_eod.json` | **Frozen** |
| Last intraday scan | `20260504T190848_scan.json` | **Frozen** |
| `trades.jsonl` last event | `2026-05-04T19:55:03Z` (204 lines) | **Frozen** |
| `decisions.jsonl` last event | `2026-05-04T20:15:04Z` (1556 lines) | **Frozen** |
| Today's review | `2026-07-09_daily_review.md` | No-data (9th consecutive) |

---

## Performance — Last Active Session (2026-05-04) vs Prior Days

| Date | Portfolio Daily | SPY Daily | Alpha |
|---|---|---|---|
| 2026-04-22 | 0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.58% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | -5.13% | -0.49% | -4.64% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| **2026-05-04** | **-1.80%** | **-0.36%** | **-1.44%** |

**Cumulative (9 sessions, 2026-04-22 → 2026-05-04):**
- Portfolio: **-16.3%**
- SPY: **+1.95%**
- Alpha: **-18.26%**
- Win days vs SPY: **2 / 9**

---

## Positions at Close (2026-05-04 EOD)

| Symbol | Side | Qty | Avg Entry | Last Price | P&L % |
|---|---|---|---|---|---|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% |

**Equity:** $99,850 | **Cash:** $4,987 (5.0%) | **Positions:** 4

---

## Trades — 2026-05-04 (Last Active Day, 53 total per EOD)

| Symbol | Action | Qty | Fill Price | AI Verdict | Conf | Outcome | Note |
|---|---|---|---|---|---|---|---|
| COIN | EXIT | 66.90 | $203.45 | EXIT | 0.80 | Filled | Earnings in 3 days, momentum 0 |
| GOOGL | EXIT | 37.96 | $382.77 | EXIT | 0.80 | Filled | Momentum 0, below EMA20, fading |
| AXTX | BUY | 313.0 | $46.41 | BUY | 0.88 | Filled | Momentum 100, breaking_out, vol 2.79× |
| META | BUY | 15.48 | $611.73 | BUY | 0.65 | Filled | Sector diversification, above VWAP |
| PWR | BUY | 14.69 | $758.48 | BUY | 0.72 | Filled | AI-data-center peer leader |
| FIX | EXIT | — | — | EXIT | 0.80 | **BLOCKED** | Fresh-exit cooldown (entered 63 min prior) |
| LLY | BUY | — | — | BUY | 0.68 | **REJECTED** | Stop $957.07 not below market $943.34 |
| SNDK | BUY | — | — | BUY | 0.78 | **SKIPPED** | Insufficient confirmed cash |
| SOXS | BUY | — | — | BUY | 0.62 | **REJECTED** | Inverse ETF — violates long-only constraint |

---

## (Full Analysis — Appending in Next Commit)
