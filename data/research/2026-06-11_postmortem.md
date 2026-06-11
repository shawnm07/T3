# Post-Mortem 2026-06-11

## Data availability

| Source | Status | Notes |
|---|---|---|
| `2026-06-11_eod.json` | **MISSING** | Bot offline — no data written since 2026-05-04 |
| Last `_eod.json` | `2026-05-04_eod.json` | Last known equity $99,849.69 |
| Last scan | `20260504T190848_scan.json` | 6th scan of 5/4 |
| Last preclose | `20260504T195545_preclose.json` | |
| `trades.jsonl` | 204 lines; last event `2026-05-04T19:55:03Z` | Unchanged 38 calendar days |
| `decisions.jsonl` | 1556 lines; last event `2026-05-04T20:15:04Z` | Unchanged 38 calendar days |

**Bot status: OFFLINE.** No scans, no trades, no EOD snapshots since 2026-05-04 (~27 trading days, 38 calendar days). All analysis below is drawn from the last active trading day (2026-05-04) and the rolling EOD archive. This is the seventh consecutive no-live-data review.

---

## Performance today (portfolio vs SPY — last known state)

| Metric | Value |
|---|---|
| Last known equity | $99,849.69 (2026-05-04 EOD) |
| Daily return (5/4) | **-1.80%** vs SPY **-0.36%** → **-1.44pp miss** |
| 5-day return (4/28–5/4) | **-14.64%** vs SPY **-0.40%** → **-14.24pp miss** |
| Full-period return (4/23–5/4) | **-14.01%** vs SPY **-0.03%** → **-13.98pp miss** |
| Trades on 5/4 | **53** (extreme churn day) |
| Positions at 5/4 EOD | 4 (AXTX, META, PWR, SPY) |

Equity curve (all available EOD data):

| Date | Equity | Daily Ret | SPY Daily | vs SPY |
|---|---|---|---|---|
| 2026-04-22 | $99,627 | 0.00% | +1.01% | -1.01pp |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | +1.95pp |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.58pp |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05pp |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.64pp |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39pp |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53pp |
| 2026-05-04 | $99,850 | **-1.80%** | -0.36% | **-1.44pp** |

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Close Price | PnL% | Market Value | Notes |
|---|---|---|---|---|---|---|
| AXTX | Long | $46.41 | $46.61 | +0.43% | $14,589 | Small-cap biotech |
| META | Long | $611.73 | $610.46 | -0.21% | $9,448 | Communication Svcs |
| PWR | Long | $758.48 | $757.38 | -0.15% | $11,130 | AI data center power |
| SPY | Long | $717.52 | $718.03 | +0.07% | $59,696 | Cash proxy (~60% of book) |

Cash: $4,987 (5.0% — at floor).

---

## Trades 2026-05-04 (all 53 events)

Selected executed trades only (entries + exits with price data):

| Time (UTC) | Event | Symbol | Entry | Exit | PnL% | Reason (truncated) |
|---|---|---|---|---|---|---|
| 14:51 | position_closed | HCAI | $11.84 | $10.69 | **-9.71%** | Exit-arbiter conf=0.72: down -8.78% |
| 16:04 | position_closed | AMZN | (held) | $270.65 | N/A | Fading momentum, below VWAP, bearish EMA |
| 16:04 | position_closed | GEV | (held) | $1,071.49 | N/A | Weak momentum, below VWAP |
| 16:04 | position_closed | UNH | $371.09 | $368.25 | -0.77% | Replaced by LLY |
| 16:04 | ai_order_submitted | LLY | | | | BUY 9.1% strong continuation |
| 16:04 | ai_order_submitted | MU | | | | INCREASE 28% pool leader |
| 16:04 | ai_order_submitted | NOK | | | | BUY 4.9% |
| 16:04 | ai_order_submitted | SNDK | | | | BUY 12.6% best new candidate |
| 17:04 | position_closed | MU | $580.42 | $580.81 | +0.07% | "Weak_or_flat momentum" — 1h after entry |
| 17:04 | ai_order_submitted | DELL | | | | BUY 12.1% |
| 17:04 | ai_order_submitted | FIX | | | | BUY 11.9% |
| 17:04 | ai_order_submitted | GOOGL | | | | BUY 11.0% |
| 17:04 | ai_order_submitted | LLY | | | | INCREASE 12.5% |
| 17:04 | ai_order_submitted | WDC | | | | BUY 10.9% |
| 18:05 | position_closed | WDC | $445.36 | $440.06 | **-1.19%** | "Gap_only classification" — 1h after entry |
| 18:05 | position_closed | DELL | $210.52 | $210.94 | +0.20% | **Verifier dust-sweep** (target=0) — 1h after entry |
| 18:05 | position_closed | LLY | $962.27 | $963.71 | +0.15% | **Verifier dust-sweep** (target=0) — 1h after entry |
| 18:05 | ai_order_submitted | FIX | | | | INCREASE 19.0% |
| 18:05 | ai_order_submitted | GOOGL | | | | Verifier reconcile +$3,569 |
| 19:08 | position_closed | COIN | $203.90 | $203.45 | -0.22% | Earnings risk, momentum=0 |
| 19:08 | position_closed | GOOGL | $384.43 | $382.77 | -0.43% | Momentum=0, fading |
| 19:08 | position_closed | FIX | $1,903.71 | $1,902.81 | **-0.05%** | **Verifier dust-sweep** (target=0) |
| 19:08 | ai_order_submitted | AXTX | | | | BUY 14.4% momentum=100 |
| 19:08 | ai_order_submitted | META | | | | BUY 9.5% |
| 19:08 | ai_order_submitted | PWR | | | | BUY 11.1% |

---

## (Full analysis appending in next commit)
