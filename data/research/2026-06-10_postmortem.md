# Post-Mortem 2026-06-10

> **Sixth consecutive no-data report.** Today is Wed 2026-06-10 (America/Phoenix). The most recent artifacts in `data/research/` are still from **Mon 2026-05-04** — a gap of **~26 trading days / 37 calendar days**. No `2026-06-10_eod.json`, no intraday scans for today. Per standing rules ("do NOT invent data"), performance sections are bounded to the last available session.

---

## Data Availability

| Source | Newest entry | Path |
|---|---|---|
| `_eod.json` | `2026-05-04_eod.json` | `data/research/2026-05-04_eod.json` |
| Last preclose snapshot | `20260504T195545_preclose.json` | `data/research/` |
| Last intraday scan | `20260504T190848_scan.json` | `data/research/` |
| `trades.jsonl` last event | `2026-05-04T19:55:03Z` exit_learning_metrics (COIN) — 204 lines | `data/journal/trades.jsonl` |
| `decisions.jsonl` last event | `2026-05-04T20:15:04Z` eod_report — 1556 lines | `data/journal/decisions.jsonl` |
| Prior no-data reviews | 5/5, 5/7, 5/13, 5/22, 6/5, **6/9** | `data/research/*_daily_review.md` |

**This is the sixth consecutive session with zero new artifacts.** The 6/9 review was the fifth; 6/10 is the sixth.

---

## Performance Today (from eod.json)

**No 2026-06-10 data.** Most recent known figures from **2026-05-04**:

| Metric | Value |
|---|---|
| Equity (2026-05-04 EOD) | $99,849.69 |
| Cash | $4,986.91 (5.0% — at floor) |
| Bot daily return (5/4) | **−1.80%** |
| SPY daily return (5/4) | **−0.36%** |
| Delta vs SPY (5/4) | **−1.43%** |
| Cumulative period vs SPY | **−10.71%** (SPY +10.71% over same window) |
| Open positions | 4 (AXTX, META, PWR, SPY proxy) |
| SPY proxy share | **59.8% of equity** |

---

## Rolling Performance (last 9 sessions — all available eod.json)

| Date | Equity | Daily Ret | SPY Daily | Delta | Trades |
|---|---|---|---|---|---|
| 2026-04-22 | $99,627 | 0.00% | +1.01% | **−1.01%** | 7 |
| 2026-04-23 | $101,208 | +1.56% | −0.39% | **+1.95%** | 9 |
| 2026-04-24 | $99,343 | −0.81% | +0.77% | **−1.58%** | 19 |
| 2026-04-27 | $96,448 | −4.88% | +0.17% | **−5.05%** ❌ | 24 |
| 2026-04-28 | $96,867 | −5.13% | −0.49% | **−4.64%** ❌ | 21 |
| 2026-04-29 | $93,999 | −5.40% | −0.01% | **−5.39%** ❌ | 10 |
| 2026-04-30 | $95,786 | −2.67% | +0.96% | **−3.63%** ❌ | 23 |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | **+1.53%** ✅ | 38 |
| 2026-05-04 | $99,850 | −1.80% | −0.36% | **−1.43%** ❌ | 53 |

**Win/loss (delta vs SPY):** 2 ✅ / 7 ❌ over available history.
**Cumulative portfolio return (4/22 → 5/4):** −0.15% vs SPY +10.71% = **−10.86% underperformance over 9 sessions**.

---

## Positions at Close (2026-05-04 EOD — last known state)

| Symbol | Side | Avg Entry | Current Price | P&L% | Mkt Value |
|---|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | **+0.43%** | $14,589 |
| META | LONG | $611.73 | $610.46 | **−0.21%** | $9,448 |
| PWR | LONG | $758.48 | $757.38 | **−0.15%** | $11,130 |
| SPY (proxy) | LONG | $717.52 | $718.03 | **+0.07%** | $59,696 |

> P&L computed from `avg_entry` and `current_price` per protocol (Alpaca unrealized_plpc not trusted).

**Note:** SPY at 59.8% of equity has been the de-facto strategy for 26+ trading days. This is no longer a bot decision — it is what the market did to the last frozen allocation.

---

## Trades Today (2026-06-10)

**None.** No intraday scan files or eod.json exist for 2026-06-10.

---

*(Full analysis appending in next commit)*
