# Post-Mortem 2026-07-16

## Data availability

| Source | Status | Last entry |
|---|---|---|
| `_eod.json` | **MISSING** (last: `2026-05-04_eod.json`) | 2026-05-04 |
| Intraday scan files | **MISSING** (last: `20260504T190848_scan.json`) | 2026-05-04 |
| `trades.jsonl` | **FROZEN** — 204 lines, byte-identical since 5/4 | 2026-05-04T19:55:03Z |
| `decisions.jsonl` | **FROZEN** — 1556 lines, byte-identical since 5/4 | 2026-05-04T20:15:04Z |
| Today's `_eod.json` | **ABSENT** | — |

**Operational gap: 52 trading days / 73 calendar days** since last bot activity (2026-05-04).
No `2026-07-16_eod.json` exists. This post-mortem analyses the last live day (2026-05-04)
and the rolling period for which data exists (2026-04-22 → 2026-05-04).

---

## Performance today (2026-05-04 — last live session)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | **-0.36%** |
| Daily alpha vs SPY | **-1.43%** |
| Equity EOD | $99,849.69 |
| Cash | $4,986.91 (5.0% — at reserve floor) |
| Trades/events | 53 (15 orders, 11 exits, 3 wash-trade recoveries, 24 exit-learning metrics) |

**Daily drawdown (-1.80%) approaches the 2.5% hard limit** — no breach, but one bad session away.

---

## Rolling performance (all available data: 2026-04-22 → 2026-05-04)

| Date | Portfolio | SPY | Delta |
|---|---|---|---|
| 2026-04-22 | 0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | -5.13% | -0.49% | -4.65% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.43% |

**Period total (4/22 → 5/4): portfolio +0.22% vs SPY +10.71% → -10.49% underperformance**
**Last-5d avg daily: portfolio -2.64% vs SPY +0.08%** — significant divergence

---

## Positions at close (2026-05-04 EOD)

Computed as `pnl_pct = (current_price - avg_entry) / avg_entry` per instructions.

| Symbol | Side | Qty | Avg Entry | Last Price | P&L% | Market Value | Weight |
|---|---|---|---|---|---|---|---|
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** | $59,695.86 | **59.8%** |
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** | $14,588.93 | 14.6% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** | $11,129.62 | 11.1% |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** | $9,448.36 | 9.5% |
| Cash | — | — | — | — | — | $4,986.91 | 5.0% |

**Critical: SPY at 59.8% weight.** The bot effectively became a SPY proxy (+ 3 concentrated longs).

---

## Trades on last active day (2026-05-04) — 11 exits, 15 entries

### Exits (position_closed events)
| Symbol | Reason (truncated) |
|---|---|
| HCAI | exit-arbiter conf=0.72: position down -8.78% |
| AMZN | arbiter EXIT: fading momentum, below VWAP, bearish EMA |
| GEV | arbiter EXIT: weak momentum, below VWAP, bearish EMA |
| UNH | arbiter EXIT: fading volume, below VWAP |
| MU | arbiter EXIT: weak/flat momentum, bearish EMA |
| WDC | arbiter EXIT: gap-only, bearish EMA, fading volume |
| DELL | verifier dust-sweep target=0 |
| LLY | verifier dust-sweep target=0 |
| COIN | arbiter EXIT: momentum score 0, earnings risk |
| GOOGL | arbiter EXIT: momentum score 0, fading, below VWAP |
| FIX | verifier dust-sweep target=0 (fresh_exit_guard blocked earlier attempt) |

### Entries (ai_order_submitted, filled)
| Symbol | Qty | Price |
|---|---|---|
| LLY | 9.49 + 3.51 | $963.38 / $962.27 |
| MU | 25.0 | $580.42 |
| NOK | 367.24 | $13.33 |
| SNDK | 10.10 | $1,246.97 |
| DELL | 57.39 | $210.52 |
| FIX | 6.30 + 3.70 | $1,896.50 / $1,903.71 |
| GOOGL | 28.68 + 9.28 | $383.51 / $384.43 |
| WDC | 24.51 | $445.36 |
| COIN | 5.10 | $203.90 |
| AXTX | 313.0 | $46.41 |
| META | 15.48 | $611.73 |
| PWR | 14.69 | $758.48 |

Most intraday entries (LLY, MU, NOK, SNDK, DELL, FIX, GOOGL, WDC, COIN) were exited the same session. **AXTX, META, PWR survived to become overnight holds.**

---

## (Full analysis in next commit)
