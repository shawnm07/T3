# Post-Mortem 2026-07-01

## Data Availability

Scheduled run date: **2026-07-01**. No eod.json or scan files exist for today — the bot appears to have been dormant or disconnected since **2026-05-04** (most recent snapshot). This postmortem covers **2026-05-04**, the last active trading day, plus rolling performance since 2026-04-22.

Sources used:
- `data/research/2026-05-04_eod.json` — EOD snapshot (positions, equity, returns)
- `data/research/20260504T*_scan.json` — 6 intraday scans
- `data/journal/trades.jsonl` — all buy/sell events (chronological)
- `data/journal/decisions.jsonl` — 105 decision entries for 2026-05-04
- `data/research/2026-04-22_eod.json` … `2026-05-04_eod.json` — 9-day rolling history

---

## Performance Today (2026-05-04)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily alpha | **-1.44%** |
| Closing equity | $99,849.69 |
| Cash | $4,986.91 |
| Positions at close | 4 (AXTX, META, PWR, SPY) |
| Trades executed | **53** |

### Rolling Benchmark

| Date | Equity | Port% | SPY% | Alpha |
|---|---|---|---|---|
| 2026-04-22 | $99,627 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.58% |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.64% |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | -1.44% |

**9-day cumulative:** Portfolio -17.31% vs SPY +1.95% → **alpha -19.26%**
**5-day cumulative:** Portfolio -13.18% vs SPY +0.39% → **alpha -13.57%**

> Goal is to beat SPY. The bot is underperforming by ~19% over 9 trading days. This is critical.

---

## Positions at Close (2026-05-04 EOD)

| Symbol | Side | Qty | Avg Entry | Current | PnL% | Market Value |
|---|---|---|---|---|---|---|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% | $14,589 |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | $9,448 |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | $11,130 |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | $59,696 |

> **SPY cash proxy = 59.7% of portfolio.** All three active equity positions are tiny stubs with negligible P&L. Nearly all capital is parked in SPY, limiting any alpha generation.

---

## Trades Today (2026-05-04, Chronological)

| Time (UTC) | Side | Symbol | Qty | Price | Reason (truncated) |
|---|---|---|---|---|---|
| 14:51 | SELL | HCAI | 1492 | $10.69 | exit-arbiter conf=0.72: down -8.78% intraday momentum |
| 16:04 | SELL | AMZN | 65.3 | $270.65 | fading momentum, below VWAP, bearish EMA |
| 16:04 | SELL | GEV | 14.57 | $1,071.49 | weak momentum, below VWAP, bearish EMA |
| 16:04 | SELL | UNH | 17.27 | $368.25 | fading volume, LLY is stronger |
| 16:04 | BUY | LLY | 9.49 | $963.38 | strong continuation, above VWAP |
| 16:04 | BUY | MU | 25.0 | $580.42 | INCREASE → 28% — pool leader, perfect momentum |
| 16:04 | BUY | NOK | 367.2 | $13.33 | continuation, above VWAP |
| 16:04 | BUY | SNDK | 10.1 | $1,246.97 | strong continuation (prev SNDK position sold earlier at $1,237) |
| 17:04 | SELL | MU | 23.0 | $580.81 | weak_or_flat momentum, bearish EMA 1 hr after buying |
| 17:04 | BUY | DELL | 57.4 | $210.52 | IT sector leader, momentum 95 |
| 17:04 | BUY | FIX | 6.3 | $1,896.50 | ai_data_center_power leader |
| 17:04 | BUY | GOOGL | 28.7 | $383.51 | Comm Services leader |
| 17:04 | BUY | LLY | 3.51 | $962.27 | INCREASE — within cooldown |
| 17:04 | BUY | WDC | 24.51 | $445.36 | memory peer, scored > MU |
| 17:04 | BUY | COIN | 5.1 | $203.90 | verifier gap-fill |
| 18:05 | SELL | WDC | 24.51 | $440.06 | gap_only classification, bearish EMA 1 hr after buying |
| 18:05 | BUY | FIX | 3.7 | $1,903.71 | INCREASE → 19% — perfect momentum |
| 18:05 | SELL | DELL | 57.4 | $210.94 | verifier dust-sweep |
| 18:05 | SELL | LLY | 13.0 | $963.71 | verifier dust-sweep |
| 18:05 | BUY | GOOGL | 9.28 | $384.43 | verifier gap-fill |
| 19:08 | SELL | COIN | 66.9 | $203.45 | earnings in 3 days, momentum 0 |
| 19:08 | SELL | GOOGL | 37.96 | $382.77 | momentum 0, fading |
| 19:08 | BUY | AXTX | 313.0 | $46.41 | momentum 100, breaking_out |
| 19:08 | BUY | META | 15.48 | $611.73 | comm services, above VWAP |
| 19:08 | BUY | PWR | 14.69 | $758.48 | ai_data_center_power leader |
| 19:08 | SELL | FIX | 10.0 | $1,902.81 | verifier dust-sweep |

*(Full analysis appending in next commit.)*
