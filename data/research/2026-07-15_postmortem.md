# Post-Mortem 2026-07-15

## Data availability

**CRITICAL: No data exists for 2026-07-15 in this repo.**

The most recent EOD snapshot is `2026-05-04_eod.json` (10+ weeks ago). Git commit history shows daily review commits since then all include the note "no new data; latest snapshot is still 5/4". This post-mortem therefore covers the **last active trading session (2026-05-04)** and the full recorded period **2026-04-22 → 2026-05-04**.

**Bot operational status is unknown.** The data gap from 2026-05-05 to present may indicate the bot stopped running, Alpaca paper account was reset, or the eod_report.py script stopped writing files. This is the highest-priority finding.

Scan files present for 2026-05-04: 6 intraday + 1 preclose.  
Journal entries for 2026-05-04: 53 trades, 105 decisions.

---

## Performance today (2026-05-04, most recent session)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily | **-0.36%** |
| Daily alpha | **-1.44%** |
| Equity at close | $99,850 |
| Trades executed | 53 |
| Open positions EOD | 4 |
| Macro regime | neutral (score 0.27, VIX ~27.3) |

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Close Price | PnL % | Market Value | % Portfolio |
|--------|------|-----------|-------------|--------|--------------|-------------|
| SPY    | LONG | $717.52   | $718.03     | +0.07% | $59,696      | 59.7% |
| PWR    | LONG | $758.48   | $757.38     | -0.15% | $11,130      | 11.1% |
| AXTX   | LONG | $46.41    | $46.61      | +0.43% | $14,589      | 14.6% |
| META   | LONG | $611.73   | $610.46     | -0.21% | $9,448       | 9.5%  |

> Note: 59.7% SPY cash-proxy weight means the bot had ~60% parked in its benchmark. This is not alpha-generating positioning.

---

## Trades today (2026-05-04, complete round-trip summary)

| Time (UTC) | Symbol | Action | Reason (truncated) |
|------------|--------|--------|---------------------|
| 14:51 | HCAI | EXIT (full) | AI exit-arbiter: down -8.78%, thesis broken |
| 16:04 | AMZN | EXIT (full) | Fading momentum, below VWAP, bearish EMA (was 17.7%) |
| 16:04 | GEV  | EXIT (full) | Weak momentum, below VWAP, flat trend (was 15.6%) |
| 16:04 | UNH  | EXIT (full) | Exiting to fund LLY entry |
| 16:04 | LLY  | BUY 9.1% | Strong continuation, bullish EMA |
| 16:04 | MU   | INCREASE →28% | Pool leader with perfect momentum |
| 16:04 | NOK  | BUY 4.9% | Strong continuation |
| 16:04 | SNDK | BUY 12.6% | Best new candidate |
| 17:04 | MU   | EXIT (full) | Weak/flat momentum, bearish EMA — **bought at 16:04, sold at 17:04** |
| 17:04 | DELL | BUY 12.1% | IT sector leader |
| 17:04 | FIX  | BUY 11.9% | ai_data_center_power peer leader |
| 17:04 | GOOGL| BUY 11.0% | Communication Services leader |
| 17:04 | LLY  | INCREASE →12.5% | Within 120-min cooldown |
| 17:04 | WDC  | BUY 10.9% | Memory peer leader |
| 17:04 | COIN | verifier reconcile 14.8% | Gap fill |
| 18:05 | WDC  | EXIT (full) | Gap-only classification, bearish EMA — **bought at 17:04, sold at 18:05** |
| 18:05 | FIX  | INCREASE →19% | Perfect momentum |
| 18:05 | DELL | dust-sweep →0% | Verifier closed position just opened at 17:04 |
| 18:05 | LLY  | dust-sweep →0% | Verifier closed position just opened at 17:04/16:04 |
| 18:05 | GOOGL| verifier reconcile 14.6% | Gap fill |
| 19:08 | COIN | EXIT (full) | Momentum score 0, earnings risk (was 13.7%) |
| 19:08 | GOOGL| EXIT (full) | Momentum score 0, fading (was 14.6%) |
| 19:08 | FIX  | dust-sweep →0% | Verifier closed the 19% position opened this scan |
| 19:08 | AXTX | BUY 14.4% | Momentum score 100, breaking out |
| 19:08 | META | BUY 9.5% | Communication Services leader |
| 19:08 | PWR  | BUY 11.1% | ai_data_center_power peer leader |

*53 total order events; at least 6 round-trips completed within the same trading day.*

---

## (Full analysis appending in next commit)
