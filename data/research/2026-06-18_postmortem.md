# Post-Mortem 2026-06-18

## Data Availability

| Source | Status |
|--------|--------|
| EOD snapshot (2026-06-18) | **MISSING** — no data for today |
| Latest EOD available | 2026-05-04 (45 days stale) |
| Scan files (2026-06-18) | **MISSING** |
| Latest scans available | 2026-05-04 (6 scans + 1 preclose) |
| Trade log (trades.jsonl) | 204 entries through 2026-05-04 |
| Decision log (decisions.jsonl) | 1,556 entries through 2026-05-04 |
| Config baseline | Read successfully |

> **NOTE:** The bot has not produced any data since 2026-05-04 — a 45-day gap.
> This post-mortem covers the **most recent trading day with data: 2026-05-04**.
> The data gap itself is the #1 finding.

---

## Performance: 2026-05-04 (Most Recent Day)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | **-0.36%** |
| Daily vs SPY | **-1.43%** (underperformed) |
| Equity at close | $99,849.69 |
| Cash | $4,986.91 (5.0% of equity — at floor) |
| Positions held | 4 |
| Trades executed | 53 |

### Risk Budget Check

| Constraint | Limit | Actual | Status |
|------------|-------|--------|--------|
| Daily drawdown | < 2.5% | 1.80% | OK |
| Cash reserve | >= 5% | 5.0% | BORDERLINE |
| Max position % | <= 15% initial | SPY 59.8% (proxy) | N/A (cash proxy) |
| Max positions | 6 | 4 | OK |

---

## Positions at Close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | Current | PnL % | PnL $ | Mkt Value | % of Equity |
|--------|------|-----|-----------|---------|-------|-------|-----------|-------------|
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42.40 | $59,695.86 | 59.8% |
| AXTX | LONG | 313.00 | $46.41 | $46.61 | +0.43% | +$62.60 | $14,588.93 | 14.6% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | -$16.16 | $11,129.62 | 11.1% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$19.63 | $9,448.36 | 9.5% |
| **Total** | | | | | | **+$69.21** | **$94,862.77** | 95.0% |

---

## Trades on 2026-05-04 (53 orders)

### Exits (5 positions closed)

| Time (UTC) | Symbol | Qty | Price | Reason | Verdict |
|------------|--------|-----|-------|--------|--------|
| 14:51 | HCAI | 1,492 | $10.69 | Exit-arbiter (conf=0.72): down -8.78%, lost VWAP, 5-min EMA20 | **GOOD** — cut a loser |
| 16:04 | AMZN | 65.30 | $270.65 | Arbiter EXIT: fading momentum, below VWAP | QUESTIONABLE — AMZN churned |
| 16:04 | GEV | 14.57 | $1,071.49 | Arbiter EXIT: weak momentum, below VWAP, bearish EMA | OK |
| 16:04 | UNH | 17.27 | $368.25 | Arbiter EXIT: fading volume, LLY stronger pick | OK — replaced w/ peer |
| 17:04 | MU | 23.01 | $580.81 | Arbiter EXIT: weak momentum, bearish EMA, peer WDC scored higher | CHURN — bought + sold same day |

### Entries / Increases (10 orders)

| Time (UTC) | Symbol | Action | Qty | Price | Target % | Reason | Verdict |
|------------|--------|--------|-----|-------|----------|--------|--------|
| 16:04 | LLY | BUY | 9.49 | $963.38 | 9.1% | Strong continuation, above VWAP | OK |
| 16:04 | MU | INCREASE | 25.00 | $580.42 | 28.0% | Pool leader, perfect momentum | **BAD** — sold 1hr later |
| 16:04 | NOK | BUY | 367.24 | $13.33 | 4.9% | Strong continuation, sector leader | UNKNOWN — not in EOD |
| 16:04 | SNDK | BUY | 10.10 | $1,246.97 | 12.6% | Best new candidate, above VWAP | UNKNOWN — not in EOD |
| 17:04 | DELL | BUY | 57.39 | $210.52 | 12.1% | IT sector leader, momentum 95 | UNKNOWN — not in EOD |
| 17:04 | FIX | BUY | 6.30 | $1,896.50 | 11.9% | ai_data_center_power leader | UNKNOWN — not in EOD |
| 17:04 | GOOGL | BUY | 28.68 | $383.51 | 11.0% | Comm Services leader | UNKNOWN — not in EOD |
| 17:04 | LLY | INCREASE | 3.51 | $962.27 | 12.5% | Continuation, cooldown | OK |
| 17:04 | WDC | BUY | 24.51 | $445.36 | 10.9% | Memory peer leader vs MU | CHURN — replaced MU same day |
| 17:04 | COIN | BUY | 5.10 | $203.90 | 14.8% | Verifier reconcile gap | OK |

> **53 trades in one day is extreme churn.** The bot entered and exited MU within the same session.
> Many 16:04 entries were replaced by 17:04 entries, suggesting the selector is unstable scan-to-scan.

---

## (Full analysis follows in next commit)
