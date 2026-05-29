# Post-Mortem 2026-05-29

## Data Availability

| Source | Status |
|--------|--------|
| `data/research/2026-05-29_eod.json` | **MISSING** — bot has not written EOD snapshot for today |
| `data/research/20260529*_scan.json` | **MISSING** — no scan files found for today |
| Latest EOD snapshot | `2026-05-04_eod.json` (25-day data gap: May 5 – May 29) |
| `data/journal/trades.jsonl` | Available; last entry 2026-05-04 |
| `data/journal/decisions.jsonl` | Available; last entry 2026-05-04 |
| `config.yaml` | Available |

**Root cause of data gap:** The bot appears to have stopped generating output after 2026-05-04. Either the scheduler stopped, or commits have not been pushed since then. This post-mortem covers the last known trading session (2026-05-04) as the primary subject, with rolling benchmarks from all available EOD files (2026-04-22 through 2026-05-04).

---

## Performance Today (2026-05-04, last known session)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Portfolio vs SPY | **-1.44%** (underperformed) |
| Equity at close | $99,849.69 |
| Cash | $4,986.91 (5.0% — at floor) |
| Trades executed | **53** (extremely high churn) |
| Positions at close | 4 |
| Macro regime | neutral (score 0.27, VIX 27.3) |

---

## Rolling Benchmark (all available EOD data)

| Date | Portfolio | SPY | vs SPY | Equity | Trades |
|------|-----------|-----|--------|--------|--------|
| 2026-04-22 | +0.00% | +1.01% | **-1.01%** | $99,627 | 7 |
| 2026-04-23 | +1.56% | -0.39% | **+1.95%** | $101,208 | 9 |
| 2026-04-24 | -0.81% | +0.77% | **-1.58%** | $99,343 | 19 |
| 2026-04-27 | -4.88% | +0.17% | **-5.05%** | $96,448 | 24 |
| 2026-04-28 | -5.13% | -0.49% | **-4.64%** | $96,867 | 21 |
| 2026-04-29 | -5.40% | -0.01% | **-5.39%** | $93,999 | 10 |
| 2026-04-30 | -2.67% | +0.96% | **-3.63%** | $95,786 | 23 |
| 2026-05-01 | +1.82% | +0.29% | **+1.53%** | $101,101 | 38 |
| 2026-05-04 | -1.80% | -0.36% | **-1.44%** | $99,850 | 53 |

**9-day cumulative**: portfolio +0.22% vs SPY 30d +10.71% (from eod.json field). **Win rate vs SPY: 2/9 days (22%).**

---

## Positions at Close (2026-05-04 EOD snapshot)

| Symbol | Side | Avg Entry | Current | PnL% | Market Value |
|--------|------|-----------|---------|------|--------------|
| AXTX | LONG | $46.41 | $46.61 | **+0.43%** | $14,589 |
| META | LONG | $611.73 | $610.46 | **-0.21%** | $9,448 |
| PWR | LONG | $758.48 | $757.38 | **-0.15%** | $11,130 |
| SPY | LONG | $717.52 | $718.03 | **+0.07%** | $59,696 |

> Note: SPY as a held position represents ~60% of the portfolio — the bot defaulted to cash-proxy SPY as active positions churned out.

---

## Trades Executed 2026-05-04

### Positions Closed (11 closures)

| Symbol | Exit Price | Est. Entry | Est. PnL% | Est. PnL$ | Reason |
|--------|-----------|------------|-----------|-----------|--------|
| HCAI | $10.69 | $11.84 | **-9.71%** | -$1,716 | AI exit-arbiter conf=0.72: momentum loss 5-signal |
| AMZN | $270.65 | unknown | — | — | Arbiter EXIT: fading momentum, below VWAP |
| GEV | $1,071.49 | unknown | — | — | Arbiter EXIT: weak momentum, below VWAP |
| UNH | $368.25 | $371.09 | **-0.77%** | -$49 | Arbiter EXIT: UNH→LLY rotation |
| MU | $580.81 | $580.42 | **+0.07%** | +$9 | Arbiter EXIT: WDC favoured as peer leader |
| WDC | $440.06 | $445.36 | **-1.19%** | -$130 | Arbiter EXIT: gap_only classification |
| DELL | $210.94 | $210.52 | **+0.20%** | +$24 | Verifier dust-sweep target=0 |
| LLY | $963.71 | $962.27 | **+0.15%** | +$19 | Verifier dust-sweep target=0 |
| COIN | $203.45 | $203.90 | **-0.22%** | -$30 | Arbiter EXIT: earnings 3 days, momentum gone |
| GOOGL | $382.77 | $384.43 | **-0.43%** | -$63 | Arbiter EXIT: momentum 0, fading |
| FIX | $1,902.81 | $1,903.71 | **-0.05%** | -$9 | Verifier dust-sweep target=0 |

### AI Orders Submitted (15 buys/adds)

| Symbol | Action | Qty | Fill Price | Stop | Confidence |
|--------|--------|-----|-----------|------|------------|
| LLY | BUY | 9.49 | $963.38 | $951.69 | 0.72 |
| MU | ADD | 25.0 | $580.42 | $577.65 | 0.90 |
| NOK | BUY | 367.2 | $13.33 | $13.24 | — |
| SNDK | BUY | 10.1 | $1,246.97 | $1,237.62 | — |
| DELL | BUY | 57.4 | $210.52 | $207.81 | — |
| FIX | BUY | 6.3 | $1,896.50 | $1,865.26 | — |
| GOOGL | BUY | 28.7 | $383.51 | $378.99 | — |
| LLY | ADD | 3.51 | $962.27 | $952.61 | — |
| WDC | BUY | 24.5 | $445.36 | $437.86 | — |
| COIN | BUY | 5.1 | $203.90 | $202.77 | verifier reconcile |
| FIX | ADD | 3.7 | $1,903.71 | $1,881.24 | — |
| GOOGL | ADD | 9.28 | $384.43 | $380.10 | verifier reconcile |
| AXTX | BUY | 313.0 | $46.41 | $45.34 | — |
| META | BUY | 15.48 | $611.73 | $606.07 | — |
| PWR | BUY | 14.69 | $758.48 | $748.54 | — |

---

*(Full analysis — patterns, proposals, backtests — appending in next commit)*
