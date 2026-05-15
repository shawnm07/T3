# Post-Mortem 2026-05-15

> **Data availability note:** No data files exist for 2026-05-15 (today per system clock).
> The most recent trading session in the repository is **2026-05-04**. All analysis below is
> for that session. Sections are labelled accordingly. The 9-day rolling window covers
> 2026-04-22 through 2026-05-04.

---

## Data availability

| Source | Status |
|---|---|
| `data/research/2026-05-15_eod.json` | **MISSING** — no data for today |
| `data/research/2026-05-04_eod.json` | Present — used as reference session |
| `data/research/20260504T*_scan.json` | 6 scans present (15:13, 15:18, 16:05, 17:05, 18:05, 19:08) |
| `data/research/20260504T195545_preclose.json` | Present |
| `data/journal/trades.jsonl` | 204 total entries; 53 trades on 2026-05-04 |
| `data/journal/decisions.jsonl` | 1,556 entries; decisions through 2026-05-04 |
| `data/research/*_eod.json` (rolling) | 9 trading days: 2026-04-22 → 2026-05-04 |

---

## Performance 2026-05-04 (latest session, portfolio vs SPY)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily alpha | **-1.43%** |
| Closing equity | $99,849.69 |
| Trades executed | 53 |
| Positions at close | 4 (AXTX, META, PWR, SPY-proxy) |

### Rolling window (9 trading days, 2026-04-22 → 2026-05-04)

| Date | Portfolio | SPY | Alpha |
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
| **Cumulative** | **-16.31%** | **+1.95%** | **-18.26%** |

> Goal is to **beat SPY** within risk budget. Currently -18.26% cumulative alpha — severely
> off target. 5-day alpha is -13.04%.

---

## Positions at close 2026-05-04

| Symbol | Side | Avg Entry | Current | P&L % | Market Value |
|---|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,588.93 |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448.36 |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,129.62 |
| SPY (proxy) | LONG | $717.52 | $718.03 | +0.07% | $59,695.86 |
| **Cash** | — | — | — | — | $4,986.91 |
| **Total equity** | — | — | — | — | **$99,849.69** |

*P&L computed as (current - avg_entry) / avg_entry per task instructions.*

---

## Trades 2026-05-04 (summary table)

| Time | Symbol | Action | Qty | Reason (truncated) |
|---|---|---|---|---|
| 14:51 | HCAI | EXIT | — | AI exit-arbiter conf=0.72, position -8.78% |
| 16:04 | AMZN | EXIT | — | Fading momentum, below VWAP, bearish EMA |
| 16:04 | GEV | EXIT | — | Weak momentum, below VWAP, bearish EMA |
| 16:04 | UNH | EXIT | — | Exiting to fund LLY |
| 16:04 | LLY | BUY | 9.49 | Strong continuation, above VWAP, bullish EMA |
| 16:04 | MU | INCREASE | 25.0 | Perfect momentum, pool leader |
| 16:04 | NOK | BUY | 367.24 | Strong continuation, sector diversification |
| 16:04 | SNDK | BUY | 10.10 | Best new candidate, memory sector |
| 17:04 | MU | EXIT | — | Peer leader WDC scores 22 pts higher |
| 17:04 | DELL | BUY | 57.39 | IT sector leader, momentum score 95 |
| 17:04 | FIX | BUY | 6.30 | ai_data_center_power leader, score 91 |
| 17:04 | GOOGL | BUY | 28.68 | Comm Services leader, sector diversification |
| 17:04 | LLY | INCREASE | 3.51 | Within cooldown, acceptable continuation |
| 17:04 | WDC | BUY | 24.51 | Memory peer leader (scored > MU) |
| 17:04 | COIN | +reconcile | 5.10 | Verifier +$1,135 gap |
| 18:05 | WDC | EXIT | — | Gap_only, bearish EMA, below VWAP |
| 18:05 | FIX | INCREASE | 3.70 | Score 100, breaking_out, pressing day high |
| 18:05 | DELL | dust-sweep | — | Verifier target=0 |
| 18:05 | LLY | dust-sweep | — | Verifier target=0 |
| 18:05 | GOOGL | +reconcile | 9.28 | Verifier +$3,569 gap |
| 19:08 | COIN | EXIT | — | Momentum 0, earnings in 3 days |
| 19:08 | GOOGL | EXIT | — | Momentum 0, below EMA20 |
| 19:08 | FIX | EXIT | — | Momentum fading (score 23), below EMA20 |
| 19:08 | AXTX | BUY | 313.0 | Momentum score 100, breaking_out |
| 19:08 | META | BUY | 15.48 | Comm Services leader, acceptable continuation |
| 19:08 | PWR | BUY | 14.69 | ai_data_center_power leader |
| 19:55 | LLY/DELL/WDC/COIN | remnant sell | — | Preclose stale-position cleanup |

*53 total trade events; many are duplicate/remnant cancellations from prior scans.*

---

## (Full analysis appending in next commit)
