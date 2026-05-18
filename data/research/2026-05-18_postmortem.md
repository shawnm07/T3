# Post-Mortem 2026-05-18

> Generated: 2026-05-18 | Analyst: post-mortem-bot | Model: claude-sonnet-4-6

---

## Data Availability

| Source | Latest Entry | Status |
|---|---|---|
| `*_eod.json` | `2026-05-04_eod.json` | **Data gap: 2026-05-05 → 2026-05-18 (10 trading days missing)** |
| Scan snapshots | `20260504T195545_preclose.json` | Last scan 2026-05-04T19:55 UTC |
| `trades.jsonl` | `2026-05-04T19:55:03Z` | COIN exit_learning_metrics |
| `decisions.jsonl` | `2026-05-04T20:15:04Z` | eod_report event |
| Prior reviews | `2026-05-13_daily_review.md` | Confirmed: no data added since 5/4 |

**10-trading-day gap** (2026-05-05 through 2026-05-18). Bot is either not running, not committing output, or writing to a different path. No data is fabricated. This post-mortem covers the most recent closed session (2026-05-04) as the primary analysis subject, with 9-day rolling benchmarks.

---

## Performance Today (Portfolio vs SPY)

*"Today" = most recent data: 2026-05-04*

| Metric | Value |
|---|---|
| Portfolio daily return | **−1.80%** |
| SPY daily return | **−0.36%** |
| Alpha (day) | **−1.43%** |
| Equity EOD | $99,849.69 |
| Cash EOD | $4,986.91 (5.0% — at floor) |
| Positions at close | 4 (AXTX, META, PWR, SPY-proxy) |
| SPY proxy weight | **59.8%** of equity |
| Trade events on day | **53** (11 closes, 15 opens, 24 learning metrics, 3 wash-trade recoveries) |
| Macro regime | neutral (score 0.27, VIX 27.3–27.9) |

### 9-Day Rolling Series (all available EOD data)

| Date | Port | SPY | Alpha | Equity |
|---|---|---|---|---|
| 2026-04-22 | +0.00% | +1.01% | **−1.01%** | $99,627 |
| 2026-04-23 | +1.56% | −0.39% | **+1.95%** | $101,208 |
| 2026-04-24 | −0.81% | +0.77% | **−1.58%** | $99,343 |
| 2026-04-27 | −4.88% | +0.17% | **−5.05%** | $96,448 |
| 2026-04-28 | −5.13% | −0.49% | **−4.64%** | $96,867 |
| 2026-04-29 | −5.40% | −0.01% | **−5.39%** | $93,999 |
| 2026-04-30 | −2.67% | +0.96% | **−3.63%** | $95,786 |
| 2026-05-01 | +1.82% | +0.29% | **+1.53%** | $101,101 |
| 2026-05-04 | −1.80% | −0.36% | **−1.44%** | $99,850 |
| **9-day total** | **−17.3%** | **+2.0%** | **−19.3%** | |

**Period vs SPY (from eod.json `period_vs_spy` field): −10.71%**

---

## Positions at Close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current | PnL% | Mkt Value | Source |
|---|---|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,589 | yfinance |
| META | LONG | $611.73 | $610.46 | −0.21% | $9,448 | yfinance |
| PWR | LONG | $758.48 | $757.38 | −0.15% | $11,130 | yfinance |
| SPY | LONG | $717.52 | $718.03 | +0.07% | $59,696 | yfinance |
| **Cash** | — | — | — | — | $4,987 | — |

*pnl_pct computed as (current − avg_entry) / avg_entry, per policy.*

---

## Trades on 2026-05-04

| UTC Time | Symbol | Action | Filled Qty | Avg Price | P&L (est.) | Notes |
|---|---|---|---|---|---|---|
| 14:51 | HCAI | SELL (exit-arbiter) | 1492 | $10.69 | **−$1,716** | Held from 5/01 @ $11.84; down −9.7% |
| 15:14 | SNDK | SELL (selector) | 23.30 | $1,250.00 | **+$2,545** | Weekend gap-up captured |
| 15:14 | STX | SELL (selector) | 19.40 | $740.23 | **+$454** | Exited near intraday high |
| 15:18 | AMZN | BUY (selector) | 65.30 | ~$274.60 | — | |
| 15:18 | GEV | BUY (selector) | 14.57 | ~$1,093.33 | — | |
| 15:18 | UNH | BUY (selector) | 17.27 | ~$368.14 | — | |
| 16:04 | AMZN | SELL (selector flip) | 65.30 | $270.65 | **−$258** | 50-min hold |
| 16:04 | GEV | SELL (selector flip) | 14.57 | $1,071.49 | **−$318** | 50-min hold |
| 16:04 | UNH | SELL (selector flip) | 17.27 | $368.25 | **+$2** | 50-min hold |
| 16:05 | LLY | BUY | 9.49 | ~$963 | — | |
| 16:05 | MU | BUY | 25.0 | $584.62 | — | |
| 16:05 | NOK | BUY | 367.24 | $13.33 | — | |
| 16:08 | MU | SELL | 25.0 | $577.45 | **−$179** | **3-min hold** |
| 16:08 | SNDK | re-BUY then SELL | 10.10 | $1,247→$1,238 | **−$95** | Re-bought 50 min after selling at $1,250 |
| 16:08 | NOK | SELL | 367.24 | $13.24 | **−$34** | |
| 17:04 | MU | BUY (again) | 23.0 | $580.42 | — | 3rd MU order today |
| 17:04 | MU | SELL | 23.0 | $580.81 | **+$9** | |
| 17:04 | DELL | BUY | 57.39 | $210.52 | — | |
| 17:04 | FIX | BUY | 6.30 | $1,896.50 | — | wash_trade_recovery triggered |
| 17:04 | GOOGL | BUY | 28.68 | $383.51 | — | wash_trade_recovery triggered |
| 17:04 | WDC | BUY | 24.51 | $445.36 | — | |
| 17:04 | LLY | BUY (add) | 3.51 | $962.27 | — | wash_trade_recovery triggered |
| 18:05 | DELL | SELL | 57.39 | $210.94 | **+$24** | 60-min hold |
| 18:05 | LLY | SELL (all) | 13.0 | $963.71 | **+$8** | |
| 18:05 | WDC | SELL | 24.51 | $440.06 | **−$130** | |
| 18:05 | AXTX | BUY | 313.0 | $46.41 | — | overnight |
| 18:05 | META | BUY | 15.48 | $611.73 | — | overnight |
| 18:05 | PWR | BUY | 14.69 | $758.48 | — | overnight |
| 19:08 | COIN | SELL | 66.90 | $203.45 | **−$176** | earnings flag ignored earlier |
| 19:08 | GOOGL | SELL | 37.96 | $382.77 | **−$38** | |
| 19:08 | FIX | SELL | 10.0 | $1,902.81 | **+$39** | fresh_exit_cooldown blocked earlier exit |

**Rough P&L tally:** HCAI −$1,716 | SNDK/STX gap-ups +$2,999 | Round-trip churn −$1,138 | Small wins +$71 | Net realized ≈ +$216 | Unrealized AXTX/META/PWR at EOD ≈ −$41

*Full analysis appending in next commit.*

---
