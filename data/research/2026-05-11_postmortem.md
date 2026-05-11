# Post-Mortem 2026-05-11

## Data availability

| Source | Status |
|--------|--------|
| `2026-05-11_eod.json` | **MISSING** — no scan ran today (weekend gap or no data written) |
| `2026-05-04_eod.json` | Present — latest available EOD snapshot (Friday 2026-05-04) |
| `data/journal/trades.jsonl` | Present — last entry 2026-05-04 |
| `data/journal/decisions.jsonl` | Present — last entry 2026-05-04 |
| Rolling EOD history | 9 days available: 2026-04-22 → 2026-05-04 |

**Analysis scope:** This post-mortem covers the last full trading day on record — **2026-05-04** — and rolling trends through that date.
Today (2026-05-11) has no data files; a separate post-mortem will be needed once Friday's scan runs.

---

## Performance today (2026-05-04, portfolio vs SPY)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily vs SPY | **-1.43%** |
| Equity EOD | $99,849.69 |
| Cash | $4,986.91 (5.0% — at floor) |
| Trades executed | **53** (extreme churn) |
| Positions at close | 4 (AXTX, META, PWR, SPY) |
| Macro regime | Neutral (score 0.27, VIX 27.3) |

### Rolling benchmark

| Window | Portfolio | SPY | Spread |
|--------|-----------|-----|--------|
| 1 day (05-04) | -1.80% | -0.36% | **-1.43%** |
| 5 day (04-28 → 05-04) | -12.66% | +0.38% | **-13.04%** |
| 9 day (04-22 → 05-04) | -16.31% | +1.95% | **-18.26%** |
| 30 day (from eod.json) | 0.00% | +10.71% | **-10.71%** |

Portfolio is deeply underperforming. The 30-day figure from `period_vs_spy` is -10.71% despite SPY rallying +10.71%.

---

## Positions at close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | EOD Price | PnL% | $ PnL | Mkt Value |
|--------|------|-----|-----------|-----------|------|-------|----------|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% | +$62.6 | $14,589 |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$19.6 | $9,448 |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.14% | -$16.2 | $11,130 |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42.4 | $59,696 |

*Computed from avg_entry and current_price per CLAUDE.md rule; Alpaca unrealized_plpc not trusted.*

SPY cash-proxy represents **59.8% of equity** — the portfolio effectively behaved as a leveraged SPY underperformer all day.

---

## Trades today (2026-05-04) — summary table

53 total events; 11 position closes, 15 entries, 24 exit-learning metrics, 3 wash-trade recoveries.

### Entries (ai_order_submitted)

| Time (UTC) | Symbol | Qty | Entry Px | Stop | Round |
|------------|--------|-----|----------|------|-------|
| 16:04 | LLY | 9.49 | 963.38 | 951.69 | 2 |
| 16:04 | MU | 25.0 | 580.42 | 577.65 | 2 |
| 16:04 | NOK | 367.2 | 13.33 | 13.24 | 2 |
| 16:04 | SNDK | 10.1 | 1246.97 | 1237.62 | 2 |
| 17:04 | DELL | 57.4 | 210.52 | 207.81 | 3 |
| 17:04 | FIX | 6.3 | 1896.5 | 1865.26 | 3 |
| 17:04 | GOOGL | 28.7 | 383.51 | 378.99 | 3 |
| 17:04 | LLY (add) | 3.5 | 962.27 | 952.61 | 3 |
| 17:04 | WDC | 24.5 | 445.36 | 437.86 | 3 |
| 17:04 | COIN | 5.1 | 203.9 | 202.77 | 3 |
| 18:05 | FIX (add)* | 3.7 | 1903.71 | 1881.24 | 4 |
| 18:05 | GOOGL (add)* | 9.3 | 384.43 | 380.10 | 4 |
| 19:08 | AXTX | 313.0 | 46.41 | 45.34 | 5 |
| 19:08 | META | 15.5 | 611.73 | 606.07 | 5 |
| 19:08 | PWR | 14.7 | 758.48 | 748.54 | 5 |

*Wash-trade recovery triggered (see below)*

### Exits (position_closed)

| Time (UTC) | Symbol | Exit Px | Qty | Reason | Est. PnL |
|------------|--------|---------|-----|--------|----------|
| 14:51 | HCAI | 10.69 | 1492 | Exit-arbiter conf=0.72, down -8.78% | **~-$1,400** |
| 16:04 | AMZN | 270.65 | 65.3 | Arbiter: fading below VWAP | ~$0 |
| 16:04 | GEV | 1071.49 | 14.6 | Arbiter: weak momentum | ~$0 |
| 16:04 | UNH | 368.25 | 17.3 | Arbiter: fund LLY | ~$0 |
| 17:04 | MU | 580.81 | 23.0 | Arbiter: peer WDC scores +22 pts | ~+$10 |
| 18:05 | WDC | 440.06 | 24.5 | Arbiter: gap-only, fading | **~-$130** |
| 18:05 | DELL | 210.94 | 57.4 | Verifier dust-sweep | ~+$24 |
| 18:05 | LLY | 963.71 | 13.0 | Verifier dust-sweep | ~+$8 |
| 19:08 | COIN | 203.45 | 66.9 | Arbiter: momentum=0, earnings 3d | ~$0 |
| 19:08 | GOOGL | 382.77 | 38.0 | Arbiter: momentum=0, fading | **~-$36** |
| 19:08 | FIX | 1902.81 | 10.0 | Verifier dust-sweep | ~+$37 |

Dominant loss: HCAI (-8.78%, ~-$1,400) + WDC churn loss (~-$130) + friction across 53 trades.

---

*(Full analysis appending in next commit)*
