# Post-Mortem 2026-05-28

## Data availability

| Source | Status |
|--------|--------|
| `data/research/2026-05-28_eod.json` | **MISSING** — bot has not run since 2026-05-04 (24 calendar days, ~16 trading days gap) |
| `data/research/2026-05-04_eod.json` | Present — most recent EOD snapshot |
| `data/research/2026050[4-1]T*_scan.json` | 6 scan files on 2026-05-04 |
| `data/journal/trades.jsonl` | 204 total trades; 53 on 2026-05-04 |
| `data/journal/decisions.jsonl` | 1556 entries through 2026-05-04 |
| `config.yaml` | Present — baseline for proposals |
| `scripts/analyze_winner_trim.py` | Present (requires yfinance — network-blocked; offline only) |

**Critical gap:** The bot has not produced an EOD snapshot or executed any trades since 2026-05-04. This post-mortem covers the last recorded trading day (2026-05-04) and the full rolling period (2026-04-22 → 2026-05-04). The 24-day inactivity gap is itself a finding requiring investigation.

---

## Performance today (2026-05-04 — last recorded trading day)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| **vs SPY (today)** | **-1.43%** |
| Equity at close | $99,849.69 |
| Cash | $4,986.91 |
| Positions | 4 |
| Trades executed | **53** (abnormally high) |

### Rolling period (2026-04-22 → 2026-05-04)

| Date | Portfolio | SPY | vs SPY | Trades | Positions |
|------|-----------|-----|--------|--------|-----------|
| 2026-04-22 | +0.00% | +1.01% | **-1.01%** | 7 | 7 |
| 2026-04-23 | +1.56% | -0.39% | **+1.95%** | 9 | 10 |
| 2026-04-24 | -0.81% | +0.77% | **-1.59%** | 19 | 12 |
| 2026-04-27 | -4.88% | +0.17% | **-5.05%** | 24 | 8 |
| 2026-04-28 | -5.13% | -0.49% | **-4.65%** | 21 | 4 |
| 2026-04-29 | -5.40% | -0.01% | **-5.39%** | 10 | 5 |
| 2026-04-30 | -2.67% | +0.96% | **-3.63%** | 23 | 3 |
| 2026-05-01 | +1.82% | +0.29% | **+1.53%** | 38 | 4 |
| 2026-05-04 | -1.80% | -0.36% | **-1.43%** | 53 | 4 |

**Cumulative portfolio return (Apr 22 → May 4): +0.22%**  
**SPY 30-day return (per eod.json): +10.71%**  
**Total underperformance: -10.49%**  
SPY beat days: 2/9 (Apr 23, May 1)

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current Price | P&L% | Market Value |
|--------|------|-----------|---------------|------|--------------|
| AXTX | LONG | $46.41 | $46.61 | **+0.43%** | $14,588.93 |
| META | LONG | $611.73 | $610.46 | **-0.21%** | $9,448.36 |
| PWR | LONG | $758.48 | $757.38 | **-0.15%** | $11,129.62 |
| SPY | LONG | $717.52 | $718.03 | **+0.07%** | $59,695.86 |

*P&L computed as (current − avg_entry) / avg_entry per data policy.*  
*SPY position ($59.7K = 59.8% of equity) represents the cash-proxy; real equity exposure is ~40%.*

---

## Trades today (2026-05-04, 53 total)

| Time (UTC) | Event | Symbol | Qty | Reason (truncated) |
|-----------|-------|--------|-----|--------------------|
| 14:51 | EXIT (exit-arbiter) | HCAI | 1492 | AI conf=0.72: down -8.78%, 5 momentum signals lost |
| 16:04 | EXIT (arbiter) | AMZN | — | Fading momentum, below VWAP, bearish EMA |
| 16:04 | EXIT (arbiter) | GEV | — | Weak momentum, below VWAP, bearish EMA |
| 16:04 | EXIT (arbiter) | UNH | — | Fading volume; LLY stronger healthcare name |
| 16:04 | BUY (arbiter) | LLY | 9.49 | Strong continuation, above VWAP, bullish EMA |
| 16:04 | ADD (arbiter) | MU | 25.0 | Pool leader, perfect momentum continuation |
| 16:04 | BUY (arbiter) | NOK | 367.2 | Strong continuation, above VWAP, bullish EMA |
| 16:04 | BUY (arbiter) | SNDK | 10.1 | Best new candidate, strong continuation |
| 17:04 | EXIT (arbiter) | MU | — | Weak/flat momentum, bearish EMA, flat volume |
| 17:04 | BUY (arbiter) | DELL | 57.4 | IT sector leader, momentum score 95 |
| 17:04 | BUY (arbiter) | FIX | 6.3 | ai_data_center_power sector leader |
| 17:04 | BUY (arbiter) | GOOGL | 28.7 | Communication Services leader |
| 17:04 | ADD (arbiter) | LLY | 3.51 | INCREASE to 12.5% |
| 17:04 | BUY (arbiter) | WDC | 24.5 | Memory peer, higher score than MU |
| 17:04 | ADD (verifier) | COIN | 5.1 | Reconcile to Opus target 14.8% |
| 18:05 | EXIT (arbiter) | WDC | — | Gap_only classification, bearish EMA |
| 18:05 | ADD (arbiter) | FIX | 3.7 | Perfect momentum, increase to 19% |
| 18:05 | EXIT (verifier dust) | DELL | — | verifier dust-sweep target=0 |
| 18:05 | EXIT (verifier dust) | LLY | — | verifier dust-sweep target=0 |
| 18:05 | ADD (verifier) | GOOGL | 9.28 | Reconcile to Opus target 14.6% |
| 19:08 | EXIT (arbiter) | COIN | — | Momentum score 0, fading, earnings risk |
| 19:08 | EXIT (arbiter) | GOOGL | — | Momentum score 0, fading, below VWAP |
| 19:08 | BUY (arbiter) | AXTX | 313.0 | Momentum score 100, breaking_out |
| 19:08 | BUY (arbiter) | META | 15.48 | Communication services leader |
| 19:08 | BUY (arbiter) | PWR | 14.69 | ai_data_center_power peer leader |
| 19:08 | EXIT (verifier dust) | FIX | — | verifier dust-sweep target=0 |

*53 raw trade events include multiple exit_learning_metrics, wash_trade_recovery, and order submissions counted separately.*

---

*(Full analysis appending in next commit)*
