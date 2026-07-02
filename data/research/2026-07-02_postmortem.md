# Post-Mortem 2026-07-02

## Data Availability

| Source | Status |
|--------|--------|
| `data/research/2026-07-02_eod.json` | **MISSING** — no scan ran today |
| `data/research/*_scan.json` (today) | **MISSING** |
| `data/journal/trades.jsonl` (today) | **MISSING** (last entry: 2026-05-04) |
| `data/journal/decisions.jsonl` (today) | **MISSING** |
| Latest available EOD snapshot | `2026-05-04_eod.json` |

> **Bot has been inactive since 2026-05-04 (~2 months).** This post-mortem covers the last active trading day (2026-05-04) and rolling performance through that date. The absence of any activity since May 4 is itself the primary finding.

---

## Performance Today (last active: 2026-05-04 vs SPY)

| Metric | Bot | SPY | Delta |
|--------|-----|-----|-------|
| Daily return | -1.80% | -0.36% | **-1.43%** |
| Period return (since 2026-04-22) | **-16.31%** | **+1.95%** | **-18.26%** |
| Trades executed (May 4) | 53 | — | (swing cadence = 6×/day; 53 is ~9× expected) |
| Equity (May 4 close) | $99,850 | — | Started ≈$99,627 on Apr 22 |

---

## Positions at Last Close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current Price | PnL% | Market Value |
|--------|------|-----------|---------------|------|--------------|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,589 |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448 |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,130 |
| SPY | LONG | $717.52 | $718.03 | +0.07% | $59,696 |

> Note: SPY occupies ~60% of the portfolio as a cash proxy. This is not benchmarked against SPY — it IS SPY.

---

## Trades on Last Active Day (2026-05-04, selected)

| Time (UTC) | Event | Symbol | Qty | Price | Reason (truncated) |
|------------|-------|--------|-----|-------|---------------------|
| 14:51 | EXIT | HCAI | 1492 | $10.69 | exit-arbiter conf=0.72, down -8.78% |
| 16:04 | EXIT | AMZN | 65.3 | $270.65 | fading momentum, below VWAP |
| 16:04 | EXIT | GEV | 14.6 | $1071.49 | weak momentum, below VWAP |
| 16:04 | EXIT | UNH | 17.3 | $368.25 | fading volume and continuation |
| 16:04 | BUY | LLY | 9.49 | $963.38 | strong continuation |
| 16:04 | BUY | MU | 25.0 | $580.42 | INCREASE to 28% |
| 16:04 | BUY | NOK | 367 | $13.33 | strong continuation |
| 16:04 | BUY | SNDK | 10.1 | $1246.97 | best new candidate |
| 17:04 | EXIT | MU | 23.0 | $580.81 | exited <1h after buying |
| 17:04 | BUY | DELL | 57.4 | $210.52 | IT sector leader, momentum 95 |
| 17:04 | BUY | FIX | 6.30 | $1896.50 | ai_data_center peer leader |
| 17:04 | BUY | GOOGL | 28.7 | $383.51 | comm services leader |
| 17:04 | BUY | WDC | 24.5 | $445.36 | memory peer leader |
| 18:05 | EXIT | WDC | 24.5 | $440.06 | gap_only classification (bought <1h ago) |
| 18:05 | INCREASE | FIX | 3.70 | $1903.71 | wash-trade recovery triggered |
| 18:05 | CLOSE | DELL | 57.4 | $210.94 | verifier dust-sweep target=0 |
| 18:05 | CLOSE | LLY | 13.0 | $963.71 | verifier dust-sweep target=0 |
| 18:05 | BUY | GOOGL | 9.28 | $384.43 | verifier reconcile to Opus 14.6% |
| 19:08 | EXIT | COIN | 66.9 | $203.45 | momentum 0, earnings in 3 days |
| 19:08 | EXIT | GOOGL | 38.0 | $382.77 | momentum 0, fading (bought 2h ago) |
| 19:08 | BUY | AXTX | 313 | $46.41 | breaking_out, momentum 100 |
| 19:08 | BUY | META | 15.5 | $611.73 | comm services leader |
| 19:08 | BUY | PWR | 14.7 | $758.48 | industrials leader |
| 19:08 | CLOSE | FIX | 10.0 | $1902.81 | verifier dust-sweep target=0 |

*(Full analysis appending in next commit)*

---

## Rolling Performance (2026-04-22 to 2026-05-04)

| Date | Bot Daily | SPY Daily | Alpha | Equity | Trades |
|------|-----------|-----------|-------|--------|--------|
| 2026-04-22 | 0.00% | +1.01% | -1.01% | $99,627 | 7 |
| 2026-04-23 | +1.56% | -0.39% | +1.95% | $101,208 | 9 |
| 2026-04-24 | -0.81% | +0.77% | -1.59% | $99,343 | 19 |
| 2026-04-27 | **-4.88%** | +0.17% | **-5.05%** | $96,448 | 24 |
| 2026-04-28 | **-5.13%** | -0.49% | **-4.65%** | $96,867 | 21 |
| 2026-04-29 | **-5.40%** | -0.01% | **-5.39%** | $93,999 | 10 |
| 2026-04-30 | -2.67% | +0.96% | -3.63% | $95,786 | 23 |
| 2026-05-01 | +1.82% | +0.29% | +1.53% | $101,101 | 38 |
| 2026-05-04 | -1.80% | -0.36% | -1.43% | $99,850 | **53** |
| **Total** | **-16.31%** | **+1.95%** | **-18.26%** | | **204** |

*(Full analysis appending in next commit)*
