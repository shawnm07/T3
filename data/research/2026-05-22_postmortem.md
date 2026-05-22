# Post-Mortem 2026-05-22

## Data availability

| Source | Status |
|--------|---------|
| `data/research/2026-05-22_eod.json` | **MISSING** — no scan ran today (market closed / scan not triggered) |
| `data/research/*2026052*_scan.json` | **MISSING** — no scans for today |
| `data/journal/decisions.jsonl` (today) | 0 entries for 2026-05-22 |
| `data/journal/trades.jsonl` (today) | 0 entries for 2026-05-22 |

**Analysis uses the most recent available session: 2026-05-04 (Monday).** That session is the last traded day in the journal and is the closest proxy for a current post-mortem. Rolling benchmarks span all 9 available EOD files (2026-04-22 → 2026-05-04).

---

## Performance today (2026-05-04 — last traded session)

| Metric | Value |
|--------|-----------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Alpha (day) | **-1.44%** |
| Closing equity | $99,849.69 |
| Cash at close | $4,986.91 (5.0%) |
| Period vs SPY (since inception) | **-10.71%** |

### Rolling benchmark

| Window | Portfolio | SPY | Alpha |
|--------|-----------|-----|-------|
| 5-day | -12.66% | +0.38% | **-13.04%** |
| 9-day (full history) | -16.31% | +1.95% | **-18.26%** |

Daily alpha series:

| Date | Port | SPY | Alpha |
|------|------|-----|-------|
| 2026-04-22 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.58% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | -5.13% | -0.49% | -4.64% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.44% |

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current | PnL% | Market Value | Weight |
|--------|------|-----------|---------|------|-------------|--------|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,589 | 14.6% |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448 | 9.5% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,130 | 11.1% |
| **SPY** | **LONG** | **$717.52** | **$718.03** | **+0.07%** | **$59,696** | **59.8%** |

**SPY cash-proxy = 59.8% of portfolio.** The portfolio is effectively tracking SPY by design.

---

## Trades today (2026-05-04)

53 total events: **15 buys, 11 sells, 24 exit-learning metrics, 3 wash-trade recoveries.**

### Buys (15 orders)

| Time | Symbol | Qty | Stop | Target% | Source |
|------|--------|-----|------|---------|--------|
| 16:04 | LLY | 9.49 | $951.69 | 9.1% | arbiter |
| 16:04 | MU | 25.00 | $577.65 | 28.0% | arbiter |
| 16:04 | NOK | 367.24 | $13.24 | 4.9% | arbiter |
| 16:04 | SNDK | 10.10 | $1,237.62 | 12.6% | arbiter |
| 17:04 | DELL | 57.39 | $207.81 | 12.1% | arbiter |
| 17:04 | FIX | 6.30 | $1,865.26 | 11.9% | arbiter |
| 17:04 | GOOGL | 28.68 | $378.99 | 11.0% | arbiter |
| 17:04 | LLY | 3.51 | $952.61 | 12.5% | arbiter |
| 17:04 | WDC | 24.51 | $437.86 | 10.9% | arbiter |
| 17:04 | COIN | 5.10 | $202.77 | — | verifier |
| 18:05 | FIX | 3.70 | $1,881.24 | 19.0% | arbiter |
| 18:05 | GOOGL | 9.28 | $380.10 | — | verifier |
| 19:08 | AXTX | 313.00 | $45.34 | 14.4% | arbiter |
| 19:08 | META | 15.48 | $606.07 | 9.5% | arbiter |
| 19:08 | PWR | 14.69 | $748.54 | 11.1% | arbiter |

### Sells (11 positions)

| Time | Symbol | Qty | Filled @ | Source | Reason (truncated) |
|------|--------|-----|----------|--------|---------------------|
| 14:51 | HCAI | 1,492 | $10.69 | exit-arbiter conf=0.72 | Down -8.78%, momentum lost |
| 16:04 | AMZN | 65.3 | $270.65 | arbiter | Fading momentum, below VWAP |
| 16:04 | GEV | 14.6 | $1,071.49 | arbiter | Weak momentum, below VWAP |
| 16:04 | UNH | 17.3 | $368.25 | arbiter | Acceptable but fading — funding LLY |
| 17:04 | MU | 23.0 | $580.81 | arbiter | Weak/flat momentum, peer WDC scores higher |
| 18:05 | WDC | 24.5 | $440.06 | arbiter | Gap-only, bearish EMA, below VWAP |
| 18:05 | DELL | 57.4 | $210.94 | verifier | Dust-sweep target=0 |
| 18:05 | LLY | 13.0 | $963.71 | verifier | Dust-sweep target=0 |
| 19:08 | COIN | 66.9 | $203.45 | arbiter | Momentum 0, earnings in 3 days |
| 19:08 | GOOGL | 38.0 | $382.77 | arbiter | Momentum 0, fading, below EMA20 |
| 19:08 | FIX | 10.0 | $1,902.81 | verifier | Dust-sweep target=0 |

---

## (Full analysis appending in next commit)
