# Post-Mortem 2026-06-02

> **Analysis covers the most recent trading session: 2026-05-04.**
> No EOD snapshot exists for 2026-06-02 (market data not collected since 2026-05-04;
> bot appears idle). All figures are sourced from `data/research/2026-05-04_eod.json`,
> scan JSONs `20260504T*`, and `data/journal/{trades,decisions}.jsonl`.

---

## Data Availability

| File | Status |
|------|--------|
| `data/research/2026-06-02_eod.json` | **MISSING** — most recent trading day is 2026-05-04 |
| `data/research/2026-05-04_eod.json` | Present — used as primary source |
| `data/research/20260504T*_scan.json` | Present — 6 scans (15:13, 15:18, 16:05, 17:04, 18:05, 19:08 UTC) |
| `data/journal/trades.jsonl` | Present |
| `data/journal/decisions.jsonl` | Present |
| `config.yaml` | Present |

---

## Performance Today (2026-05-04, portfolio vs SPY)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **−1.80%** |
| SPY daily return | −0.36% |
| vs SPY (today) | **−1.43%** |
| Equity at close | $99,849.69 |
| Cash on hand | $4,986.91 |
| Trades executed | **53** |
| Positions at close | 4 |
| Period (30d) vs SPY | **−10.71%** |

---

## Rolling Benchmark (all available EOD files)

| Date | Equity | Portfolio % | SPY % | vs SPY |
|------|--------|-------------|-------|--------|
| 2026-04-22 | $99,627 | +0.00% | +1.01% | −1.01% |
| 2026-04-23 | $101,208 | **+1.56%** | −0.39% | **+1.95%** |
| 2026-04-24 | $99,343 | −0.81% | +0.77% | −1.59% |
| 2026-04-27 | $96,448 | **−4.88%** | +0.17% | **−5.05%** |
| 2026-04-28 | $96,867 | **−5.13%** | −0.49% | **−4.65%** |
| 2026-04-29 | $93,999 | **−5.40%** | −0.01% | **−5.39%** |
| 2026-04-30 | $95,786 | −2.67% | +0.96% | −3.63% |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | $99,850 | −1.80% | −0.36% | −1.43% |

> 5-day window (04-28 → 05-04): portfolio avg −3.42%/day; SPY avg +0.08%/day.
> 9-day cumulative: portfolio −$150 (−0.15%); SPY +10.71% → bot is **−10.71% vs benchmark**.

---

## Positions at Close (from eod.json — avg_entry rule)

| Symbol | Side | Avg Entry | Current | PnL% | Market Value | Weight |
|--------|------|-----------|---------|------|-------------|--------|
| AXTX | Long | $46.41 | $46.61 | **+0.43%** | $14,589 | 14.6% |
| META | Long | $611.73 | $610.46 | −0.21% | $9,448 | 9.5% |
| PWR | Long | $758.48 | $757.38 | −0.15% | $11,130 | 11.1% |
| **SPY** | Long | $717.52 | $718.03 | +0.07% | **$59,696** | **59.8%** |

> SPY cash-proxy consumes 59.8% of portfolio — active selection covers only 40.2%.

---

## Trades Today (confirmed executions, trades.jsonl)

| Time (UTC) | Event | Symbol | Qty | Price | Reason (truncated) |
|-----------|-------|--------|-----|-------|---------------------|
| 14:51 | **CLOSE** | HCAI | 1,492 | $10.69 | Exit-arbiter −8.78%, momentum lost |
| 16:04 | **CLOSE** | AMZN | 65.3 | $270.65 | Fading momentum, below VWAP |
| 16:04 | **CLOSE** | GEV | 14.6 | $1,071.49 | Weak momentum, below VWAP |
| 16:04 | **CLOSE** | UNH | 17.3 | $368.25 | Fading volume, LLY is stronger |
| 16:04 | BUY | LLY | 9.49 | — | Healthcare leader |
| 16:04 | BUY | MU | 25.0 | — | Memory peer leader |
| 16:04 | BUY | NOK | 367.2 | — | Strong continuation |
| 16:04 | BUY | SNDK | 10.1 | — | Memory sector |
| 17:04 | **CLOSE** | MU | 23.0 | $580.81 | Bearish EMA, peer WDC scores higher |
| 17:04 | BUY | DELL | 57.4 | — | IT sector leader |
| 17:04 | BUY | FIX | 6.3 | — | Power infra leader |
| 17:04 | BUY | GOOGL | 28.7 | — | Comm Services leader |
| 17:04 | BUY | LLY | 3.51 | — | *(wash-trade recovery add)* |
| 17:04 | BUY | WDC | 24.5 | — | Memory peer leader vs MU |
| 18:05 | **CLOSE** | DELL | 57.4 | $210.94 | Fading, peer replaced |
| 18:05 | **CLOSE** | LLY | 13.0 | $963.71 | Fading momentum |
| 18:05 | **CLOSE** | WDC | 24.5 | $440.06 | Gap-only, bearish EMA |
| 18:05 | BUY | CUE | — | — | Sector leader |
| 18:05 | BUY | FIX | 3.7 | — | *(wash-trade recovery add)* |
| 18:05 | BUY | GOOGL | 9.28 | — | *(wash-trade recovery add)* |
| 18:05 | BUY | PWR | 14.7 | — | Power infra leader |
| 18:05 | BUY | RBLX | — | — | Momentum score 100 |
| 19:08 | **CLOSE** | COIN | — | $202.68 | Momentum 0, earnings in 3 days |
| 19:08 | **CLOSE** | FIX | 10.0 | $1,902.81 | *(verifier dust-sweep)* |
| 19:08 | **CLOSE** | GOOGL | 37.96 | $382.77 | Momentum 0, below EMA20 |
| 19:08 | BUY | AXTX | 313 | — | Momentum 100, breakout |
| 19:08 | BUY | LLY | — | — | Healthcare leader (3rd entry today) |
| 19:08 | BUY | META | 15.5 | — | Comm Services leader |
| 19:08 | BUY | PWR | — | — | Power infra (add) |
| 19:08 | BUY | SNDK | — | — | Memory leader |
| 19:08 | BUY | SOXS | — | — | ⚠ Inverse ETF — violates no-shorts rule |

> (Full analysis appending in next commit)
