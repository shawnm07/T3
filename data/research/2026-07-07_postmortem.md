# Post-Mortem 2026-07-07

> **Analysis date:** 2026-07-07 (scheduled run)
> **Last trading day with data:** 2026-05-04
> **Data gap:** No EOD, scan, or journal entries exist between 2026-05-04 and 2026-07-07. All analysis below covers the period ending 2026-05-04.

---

## Data Availability

| Source | Status |
|---|---|
| `data/research/2026-07-07_eod.json` | **MISSING** |
| `data/research/20260707*_scan.json` | **MISSING** |
| `data/research/2026-05-04_eod.json` | Present (most recent) |
| `data/research/*_scan.json` | Present through 2026-05-04T19:55 UTC |
| `data/journal/trades.jsonl` | Present (last entry: 2026-05-04T19:55 UTC) |
| `data/journal/decisions.jsonl` | Present (1556 entries) |
| EOD history | 9 trading days: 2026-04-22 → 2026-05-04 |

All benchmarks and analysis below derive exclusively from on-disk files. No network calls were made.

---

## Performance — Last Trading Day (2026-05-04)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| **vs SPY (day)** | **-1.43%** |
| Equity at close | $99,849.69 |
| Cash | $4,986.91 (4.99%) |
| Positions (excl. SPY proxy) | 4 |
| Trades executed | 53 |

**Period benchmarks (from on-disk EOD files):**

| Window | Portfolio | SPY | vs SPY |
|---|---|---|---|
| 5-day (Apr 28 – May 4) | -13.18% | +0.39% | **-13.57%** |
| 9-day (Apr 22 – May 4) | -17.31% | +1.95% | **-19.27%** |
| Win days vs SPY | 2 / 9 | — | — |
| Peak-to-trough drawdown (9d) | **-7.12%** | — | — |
| Avg trades/day | 22.7 | — | — |

Goal (beat SPY within risk budget): **NOT MET**. Bot underperformed SPY by >13% over the 5-day window and exceeded effective daily drawdown twice (Apr 27: -4.88%, Apr 28: -5.13% cumulative).

---

## Positions at Close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current Price | P&L% | Market Value |
|---|---|---|---|---|---|
| AXTX | LONG | 46.41 | 46.61 | +0.43% | $14,588.93 |
| META | LONG | 611.73 | 610.46 | -0.21% | $9,448.36 |
| PWR | LONG | 758.48 | 757.38 | -0.15% | $11,129.62 |
| SPY (proxy) | LONG | 717.52 | 718.03 | +0.07% | $59,695.86 |

SPY proxy represents **59.7% of portfolio** — the strategy effectively became a beta-1 passive fund by end of session.

---

## Trades on 2026-05-04

### Buys (15)

| Symbol | Qty | Entry | Stop | Reason (truncated) |
|---|---|---|---|---|
| LLY | 9.49 | 963.38 | 951.69 | BUY 9.1% — Strong continuation, above VWAP |
| MU | 25.0 | 580.42 | 577.65 | INCREASE 28.0% — Perfect momentum continuation |
| NOK | 367.2 | 13.33 | 13.24 | BUY 4.9% — Strong continuation, above VWAP |
| SNDK | 10.1 | 1246.97 | 1237.62 | BUY 12.6% — Best new candidate |
| DELL | 57.4 | 210.52 | 207.81 | BUY 12.1% — IT sector leader, momentum 95 |
| FIX | 6.30 | 1896.50 | 1865.26 | BUY 11.9% — ai_data_center_power leader |
| GOOGL | 28.68 | 383.51 | 378.99 | BUY 11.0% — Comm Services leader |
| LLY | 3.51 | 962.27 | 952.61 | INCREASE 12.5% — Within 120-min cooldown |
| WDC | 24.51 | 445.36 | 437.86 | BUY 10.9% — Memory peer leader |
| COIN | 5.10 | 203.90 | 202.77 | Verifier reconcile to 14.8% |
| FIX | 3.70 | 1903.71 | 1881.24 | INCREASE 19.0% — Perfect momentum, breaking_out |
| GOOGL | 9.28 | 384.43 | 380.10 | Verifier reconcile to 14.6% |
| AXTX | 313.0 | 46.41 | 45.34 | BUY 14.4% — Momentum 100, breaking_out |
| META | 15.48 | 611.73 | 606.07 | BUY 9.5% — Comm Services diversification |
| PWR | 14.69 | 758.48 | 748.54 | BUY 11.1% — ai_data_center_power |

### Sells / Closes (11)

| Symbol | Qty | Exit Price | Reason |
|---|---|---|---|
| HCAI | 1492.0 | 10.69 | AI exit-arbiter (conf=0.72) — down -8.78% |
| AMZN | 65.30 | 270.65 | arbiter EXIT — Fading momentum, below VWAP |
| GEV | 14.57 | 1071.49 | arbiter EXIT — Weak momentum, below VWAP |
| UNH | 17.27 | 368.25 | arbiter EXIT — Fading volume |
| MU | 23.01 | 580.81 | arbiter EXIT — Weak/flat momentum, bearish EMA |
| WDC | 24.51 | 440.06 | arbiter EXIT — Gap_only, bearish EMA |
| DELL | 57.39 | 210.94 | verifier dust-sweep (target=0) |
| LLY | 13.0 | 963.71 | verifier dust-sweep (target=0) |
| COIN | 66.90 | 203.45 | arbiter EXIT — Momentum 0, earnings in 3d |
| GOOGL | 37.96 | 382.77 | arbiter EXIT — Momentum 0, below EMA20 |
| FIX | 10.0 | 1902.81 | verifier dust-sweep (target=0) |

---

## (Full analysis appending in next commit)
