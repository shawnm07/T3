# Post-Mortem 2026-07-06

> **Note:** No market data exists for today (2026-07-06). The bot has produced **no output since 2026-05-04** — a 63-day gap. This post-mortem covers the last active trading day (2026-05-04) and the full tracked-period performance through that date.

---

## Data Availability

| Source | Status |
|---|---|
| `data/research/2026-07-06_eod.json` | MISSING — bot not running since 2026-05-04 |
| `data/research/2026-05-04_eod.json` | Latest available EOD snapshot |
| `data/research/20260504T*_scan.json` | 6 scan files (15:13–19:09 UTC) |
| `data/research/20260504T195545_preclose.json` | Preclose snapshot |
| `data/journal/trades.jsonl` | Available, latest entries 2026-05-04 |
| `data/journal/decisions.jsonl` | Available |
| `config.yaml` | Current baseline |

**Critical gap:** The bot has not run since 2026-05-04. Root cause unknown from repo data alone (possible crash, environment teardown, or manual stop). This is the primary operational issue.

---

## Performance Today (2026-05-04, last active day)

| Metric | Value |
|---|---|
| Portfolio equity | $99,849.69 |
| Daily return (equity delta) | -1.24% |
| SPY daily | -0.36% |
| Alpha today | **-0.88%** |
| Period equity change (since tracking start) | +0.22% ($99,627 → $99,850) |
| SPY period return | +10.71% |
| **Period alpha** | **-10.49%** |
| Trades on 2026-05-04 | **53** (vs. 7–38 on prior days) |
| Positions at close | 4 (AXTX, META, PWR, SPY-proxy) |

### Rolling EOD Series

| Date | Equity | Daily (computed) | SPY Daily | Cum. Alpha |
|---|---|---|---|---|
| 2026-04-22 | $99,627 | baseline | +1.01% | -4.22% |
| 2026-04-23 | $101,208 | **+1.59%** | -0.39% | -3.82% |
| 2026-04-24 | $99,343 | -1.84% | +0.77% | -3.87% |
| 2026-04-27 | $96,448 | -2.91% | +0.17% | -4.25% |
| 2026-04-28 | $96,867 | +0.43% | -0.49% | -3.69% |
| 2026-04-29 | $93,999 | -2.96% | -0.01% | -3.67% |
| 2026-04-30 | $95,786 | +1.90% | +0.96% | -4.70% |
| 2026-05-01 | $101,101 | +5.55% | +0.29% | -9.54% |
| **2026-05-04** | **$99,850** | **-1.24%** | **-0.36%** | **-10.49%** |

Churn escalation: 7 → 9 → 19 → 24 → 21 → 10 → 23 → 38 → **53** trades/day.

---

## Positions at Close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current | P&L% | Mkt Value | Notes |
|---|---|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,589 | Small winner |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448 | Flat |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,130 | Flat |
| **SPY** | **LONG** | $717.52 | $718.03 | **+0.07%** | **$59,696** | **~60% of equity parked as cash-proxy** |

SPY cash-proxy weight at close: **59.8%** of equity. Effective equity exposure was just 40%.

---

## Trades on 2026-05-04 (Summary)

| Event | Count |
|---|---|
| exit_learning_metrics | 24 |
| ai_order_submitted | 15 |
| position_closed | 11 |
| wash_trade_recovery | 3 |
| **Total** | **53** |

**Symbols touched:** LLY (6×), MU (6×), DELL (4×), FIX (4×), GOOGL (4×), WDC (4×), HCAI (3×), AMZN (3×), GEV (3×), UNH (3×), NOK (3×), SNDK (3×), COIN (3×), STX, AXTX, META, PWR.

Round-trip churns (bought then sold same day):
- AMZN: BUY 15:13 UTC → EXIT 16:05 UTC (-1.06%)
- WDC: BUY intraday → EXIT 18:05 UTC (-1.07%)
- GEV: BUY held → EXIT 16:05 UTC (-0.38%)
- DELL: BUY 17:05 → attempted EXIT 18:05 (blocked by 120-min cooldown, confidence 0.75 < 0.85 floor)
- FIX: BUY 17:05 → INCREASE 18:05 → attempted EXIT 18:55 (blocked, confidence 0.80 < 0.85 floor)
- LLY: BUY 14:04 → attempted EXIT 18:05 (blocked, confidence 0.80 < 0.85 floor)
- COIN: entered earlier period → EXIT 19:09 at -1.15%
- HCAI: intraday momentum exit at -8.78%

---

## (Full analysis appending in next commit)
