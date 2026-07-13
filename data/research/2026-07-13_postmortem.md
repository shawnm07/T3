# Post-Mortem 2026-07-13

## Data Availability

| Source | Status |
|---|---|
| `2026-07-13_eod.json` | **MISSING** — no data logged since 2026-05-04 |
| `20260713*_scan.json` | **MISSING** |
| `data/journal/trades.jsonl` | Available (last entry 2026-05-04T19:55) |
| `data/journal/decisions.jsonl` | Available (last entry 2026-05-04) |
| Historical EOD files | 9 dates: 2026-04-22 through 2026-05-04 |

**Critical gap: bot has produced no logged data since 2026-05-04 (70 days).** The bot may have stopped running, lost API access, or stopped persisting data. All analysis below is based on the last active session (2026-05-04).

---

## Performance Today (using last session: 2026-05-04)

No data for 2026-07-13. Last known session metrics:

| Metric | Value |
|---|---|
| Date | 2026-05-04 |
| Portfolio equity | $99,849.69 |
| Cash | $4,986.91 (5.0% — at floor) |
| Daily return | **-1.80%** |
| SPY daily | -0.36% |
| Bot vs SPY (daily) | **-1.43%** (underperformed) |
| Trades executed | **53** |

---

## Rolling Benchmark (all available EOD data)

| Date | Equity | Daily Ret | SPY Daily | Bot vs SPY |
|---|---|---|---|---|
| 2026-04-22 | $99,627 | 0.00% | +1.01% | -1.01% |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.65% |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | -1.43% |

**Period (2026-04-22 → 2026-05-04):** Bot +0.22% vs SPY +10.71% → **-10.49% underperformance**

**5-day (2026-04-28 → 2026-05-04):** Bot +3.08% vs SPY +0.39% → +2.69% excess return

---

## Positions at Close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current | PnL% |
|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | +0.43% |
| META | LONG | $611.73 | $610.46 | -0.21% |
| PWR | LONG | $758.48 | $757.38 | -0.15% |
| SPY | LONG | $717.52 | $718.03 | +0.07% |

SPY cash-proxy = $59,696 (59.8% of equity). Active positions = $35,167 (35.2%). Very high cash allocation.

---

## Trades (2026-05-04 — last session, 53 events)

### Closes (11)

| Time (UTC) | Symbol | Qty | Exit Price | Reason |
|---|---|---|---|---|
| 14:51 | HCAI | 1,492 | $10.69 | exit-arbiter conf=0.72, -8.78% |
| 16:04 | AMZN | 65.30 | $270.65 | arbiter EXIT: fading momentum, below VWAP |
| 16:04 | GEV | 14.57 | $1,071.49 | arbiter EXIT: weak momentum, below VWAP |
| 16:04 | UNH | 17.27 | $368.25 | arbiter EXIT: displaced by LLY |
| 17:04 | MU | 23.01 | $580.81 | arbiter EXIT: weak/flat momentum, bearish EMA |
| 18:05 | WDC | 24.51 | $440.06 | arbiter EXIT: gap_only, bearish EMA, fading |
| 18:05 | DELL | 57.39 | $210.94 | verifier dust-sweep target=0 |
| 18:05 | LLY | 13.00 | $963.71 | verifier dust-sweep target=0 |
| 19:08 | COIN | 66.90 | $203.45 | arbiter EXIT: momentum=0, earnings in 3 days |
| 19:08 | GOOGL | 37.96 | $382.77 | arbiter EXIT: momentum=0, fading, below EMA20 |
| 19:08 | FIX | 10.00 | $1,902.81 | verifier dust-sweep target=0 |

### Buys (15)

| Time (UTC) | Symbol | Qty | Fill Price | Confidence | Reason |
|---|---|---|---|---|---|
| 16:04 | LLY | 9.49 | $963.38 | — | BUY 9.1%: strong continuation |
| 16:04 | MU | 25.00 | $580.42 | — | INCREASE 28.0%: pool leader, perfect momentum |
| 16:04 | NOK | 367.24 | $13.33 | — | BUY 4.9%: strong continuation |
| 16:04 | SNDK | 10.10 | $1,246.97 | — | BUY 12.6%: best new candidate |
| 17:04 | DELL | 57.39 | $210.52 | — | BUY 12.1%: IT leader, momentum 95 |
| 17:04 | FIX | 6.30 | $1,896.50 | — | BUY 11.9%: ai_data_center_power leader |
| 17:04 | GOOGL | 28.68 | $383.51 | 0.72 | BUY 11.0%: acceptable continuation |
| 17:04 | LLY | 3.51 | $962.27 | — | INCREASE 12.5%: within cooldown |
| 17:04 | WDC | 24.51 | $445.36 | — | BUY 10.9%: memory peer, scores higher than MU |
| 17:04 | COIN | 5.10 | $203.90 | — | verifier reconcile to Opus 14.8% |
| 18:05 | FIX | 3.70 | $1,903.71 | 0.88 | INCREASE 19.0%: score 100, breaking_out |
| 18:05 | GOOGL | 9.28 | $384.43 | — | verifier reconcile to Opus 14.6% |
| 19:08 | AXTX | 313 | $46.41 | 0.88 | BUY 14.4%: score 88, momentum=100 |
| 19:08 | META | 15.48 | $611.73 | 0.65 | BUY 9.5%: acceptable continuation |
| 19:08 | PWR | 14.69 | $758.48 | 0.72 | BUY 11.1%: ai_data_center_power leader |

---

*(Full analysis appending in next commit)*
