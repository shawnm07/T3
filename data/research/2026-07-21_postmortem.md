# Post-Mortem 2026-07-21

## Data availability

**No today's data.** The bot has produced zero snapshots since 2026-05-04 — 78 calendar days / ~55 trading days of silence. No `2026-07-21_eod.json`, no `20260721T*` scan files, and no new journal entries exist. All market-data egress channels (Alpha Vantage, yfinance, Twelve Data) remain 403-blocked in this container. This report is written entirely from on-disk artifacts ≤ 2026-05-04 and the daily review series through 2026-07-20.

| Source | Newest entry on disk |
|---|---|
| `_eod.json` | `2026-05-04_eod.json` (78 calendar days stale) |
| Intraday scan | `20260504T190848_scan.json` |
| Preclose snapshot | `20260504T195545_preclose.json` |
| `trades.jsonl` last event | `2026-05-04T19:55:03Z` (204 lines, static) |
| `decisions.jsonl` last event | `2026-05-04T20:15:04Z` (1556 lines, static) |

---

## Performance today (portfolio vs SPY)

**Today's data: UNAVAILABLE.** Last recorded session: 2026-05-04.

### Last-known daily (2026-05-04)
| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| vs SPY | **-1.43%** (underperformed) |
| Equity at close | $99,849.69 |
| Cash | $4,986.91 (~5.0%) |

### Rolling performance (all 9 recorded sessions: 2026-04-22 → 2026-05-04)
| Date | Portfolio | SPY daily | vs SPY |
|---|---|---|---|
| 2026-04-22 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | -5.13% | -0.49% | -4.65% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.43% |
| **Cumulative (9d)** | **+0.22%** | — | **Period vs SPY: -10.71%** |

Win rate vs SPY: 2/9 sessions (22%). Consecutive losing sessions: 5 (Apr 27–May 1 close).

---

## Positions at close (last known: 2026-05-04 EOD)

> **Note:** These positions have been held unchanged for 78 calendar days with no bot activity. Current prices are unknown.

| Symbol | Side | Avg Entry | Last Price (5/4) | PnL% (5/4) | Weight |
|---|---|---|---|---|---|
| SPY | LONG | $717.52 | $718.03 | +0.07% | ~59.8% |
| AXTX | LONG | $46.41 | $46.61 | +0.43% | ~14.6% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | ~11.1% |
| META | LONG | $611.73 | $610.46 | -0.21% | ~9.5% |
| Cash | — | — | — | — | ~5.0% |

**Allocation note:** SPY (~60%) dominates the book. The bot entered AXTX (2× leveraged AXTI ETF), PWR, and META in the final scan of 5/4, then immediately closed FIX, DELL, LLY, COIN, and GOOGL the same session (verifier + arbiter exits). 53 orders total on 5/4.

---

## Trades today (2026-07-21)

**None.** Bot has not run since 2026-05-04.

### Trades on last active session (2026-05-04, partial list)
| Time (UTC) | Event | Symbol | Side | Qty | Price | Reason |
|---|---|---|---|---|---|---|
| 17:00 | exit_arbiter reduce | MU | SELL | ~23.0 | ~$580.81 | Intraday momentum lost (VWAP, EMA20) |
| 18:05 | ai_order | FIX | BUY | 3.70 | $1,903.71 | Selector INCREASE 12%→19% |
| 18:05 | position_closed | DELL | SELL | 57.39 | $210.94 | Verifier dust-sweep target=0 |
| 18:05 | position_closed | LLY | SELL | 13.00 | $963.71 | Verifier dust-sweep target=0 |
| 18:05 | ai_order | GOOGL | BUY | 9.28 | $384.43 | Verifier reconcile to Opus 14.6% |
| 19:08 | position_closed | COIN | SELL | 66.90 | $203.45 | Arbiter EXIT: momentum=0 |
| 19:08 | position_closed | GOOGL | SELL | 37.96 | $382.77 | Arbiter EXIT: fading, below EMA20 |
| 19:08 | ai_order | AXTX | BUY | 313.0 | $46.41 | Arbiter BUY 14.4%: momentum=100 |
| 19:08 | ai_order | META | BUY | 15.48 | $611.73 | Arbiter BUY 9.5%: sector diversif. |
| 19:08 | ai_order | PWR | BUY | 14.69 | $758.48 | Arbiter BUY 11.1%: data-center peer |
| 19:08 | position_closed | FIX | SELL | 10.00 | $1,902.81 | Verifier dust-sweep target=0 |

*(Total 53 orders on 5/4. Bot silent since.)*

---

## Full analysis — appending in next commit
