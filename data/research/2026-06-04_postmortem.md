# Post-Mortem 2026-06-04

## Data availability

| File | Status |
|------|--------|
| `data/research/2026-06-04_eod.json` | **MISSING** — no scan ran today |
| `data/research/2026-05-04_eod.json` | Present — last available EOD snapshot |
| `data/research/20260504T*_scan.json` | Present — 5 scan files (last run 2026-05-04) |
| `data/journal/trades.jsonl` | Present |
| `data/journal/decisions.jsonl` | Present |
| `config.yaml` | Present |

> **Context:** No bot activity detected between 2026-05-05 and 2026-06-04 (30 calendar days). This report covers the full trading period for which data exists (2026-04-22 → 2026-05-04) with emphasis on the final day (2026-05-04), which showed the most dysfunctional behaviour.

---

## Performance today (last EOD: 2026-05-04)

| Metric | Value |
|--------|-------|
| Equity at close | $99,849.69 |
| Daily return (2026-05-04) | **-1.80%** |
| SPY daily | -0.36% |
| Daily vs SPY | **-1.44%** |
| Trades executed (2026-05-04) | **53** (extremely high) |
| Positions at close | 4 |

### Rolling benchmark comparison

| Window | Portfolio | SPY | Alpha |
|--------|-----------|-----|-------|
| 1d (2026-05-04) | -1.80% | -0.36% | **-1.44%** |
| 5d (Apr 28 – May 4) | -12.66% | +0.38% | **-13.04%** |
| 30d (all available: Apr 22 – May 4) | -16.31% | +1.95% | **-18.26%** |

*SPY series from `spy_daily` fields in `*_eod.json`. Portfolio returns compounded from `daily_return` fields.*

Daily breakdown:

| Date | Portfolio | SPY | vs SPY |
|------|-----------|-----|--------|
| 2026-04-22 | 0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | **-4.88%** | +0.17% | **-5.05%** |
| 2026-04-28 | **-5.13%** | -0.49% | **-4.64%** |
| 2026-04-29 | **-5.40%** | -0.01% | **-5.39%** |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.44% |

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Qty | Avg Entry | Current | PnL% | Notional |
|--------|------|-----|-----------|---------|------|----------|
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** | $59,695 (59.8%) |
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** | $14,589 (14.6%) |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** | $11,130 (11.1%) |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** | $9,448 (9.5%) |
| Cash | — | — | — | — | — | $4,987 (5.0%) |

> PnL% computed as (current_price - avg_entry) / avg_entry per sandbox constraint.
> SPY at 59.8% of equity is far above the `initial_entry_cap_pct: 0.15` guard — it entered as a proxy hold, not a new entry.

---

## Trades today (2026-05-04 — 53 total)

| Time (UTC) | Event | Symbol | Qty | Price | Note |
|------------|-------|---------|-----|-------|------|
| 14:51 | EXIT | HCAI | 1492 | $10.69 | -8.78% loss, AI conf=0.72 |
| 16:04 | EXIT | AMZN | 65.3 | $270.65 | arbiter: fading momentum |
| 16:04 | EXIT | GEV | 14.6 | $1,071.49 | arbiter: weak momentum |
| 16:04 | EXIT | UNH | 17.3 | $368.25 | arbiter: to fund LLY |
| 16:04 | BUY | LLY | 9.5 | $963.38 | arbiter: healthcare leader |
| 16:04 | BUY | MU | 25.0 | $580.42 | arbiter: pool leader |
| 16:04 | BUY | NOK | 367.2 | $13.33 | arbiter: BUY |
| 16:04 | BUY | SNDK | 10.1 | $1,246.97 | arbiter: best candidate |
| 17:04 | EXIT | MU | 23.0 | $580.81 | ~+0.07% — sold 1 hr after buy |
| 17:04 | BUY | DELL | 57.4 | $210.52 | arbiter |
| 17:04 | BUY | FIX | 6.3 | $1,896.50 | arbiter |
| 17:04 | BUY | GOOGL | 28.7 | $383.51 | arbiter |
| 17:04 | BUY | WDC | 24.5 | $445.36 | arbiter: MU memory peer |
| 17:04 | BUY | COIN | 5.1 | $203.90 | verifier reconcile |
| 18:05 | EXIT | WDC | 24.5 | $440.06 | **-1.19%** — sold 1 hr after buy |
| 18:05 | INCREASE | FIX | 3.7 | $1,903.71 | arbiter |
| 18:05 | EXIT | DELL | 57.4 | $210.94 | verifier dust-sweep (target=0) |
| 18:05 | EXIT | LLY | 13.0 | $963.71 | verifier dust-sweep (target=0) |
| 18:05 | BUY | GOOGL | 9.28 | $384.43 | verifier reconcile |
| 19:08 | EXIT | COIN | 66.9 | $203.45 | arbiter: earnings proximity |
| 19:08 | EXIT | GOOGL | 37.96 | $382.77 | arbiter: momentum=0 |
| 19:08 | BUY | AXTX | 313.0 | $46.41 | arbiter: momentum=100, breaking_out |
| 19:08 | BUY | META | 15.5 | $611.73 | arbiter |
| 19:08 | BUY | PWR | 14.7 | $758.48 | arbiter |
| 19:08 | EXIT | FIX | 10.0 | $1,902.81 | verifier dust-sweep (target=0) |

*(Full analysis appending in next commit)*
