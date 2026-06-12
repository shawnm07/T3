# Post-Mortem 2026-06-12

> **Data coverage note:** No scan/EOD files exist for 2026-06-12 (market may have been closed, or scans did not run). This post-mortem analyses the **most recent completed session: 2026-05-04**, which is the last day with a full EOD snapshot + trade log. All sections use 2026-05-04 data unless marked otherwise.

---

## Data Availability

| File | Status |
|------|--------|
| `data/research/2026-06-12_eod.json` | **MISSING** |
| `data/research/20260612*_scan.json` | **MISSING** |
| `data/research/2026-05-04_eod.json` | Present (latest available) |
| `data/journal/trades.jsonl` | Present |
| `data/journal/decisions.jsonl` | Present |
| `config.yaml` | Present |

---

## Performance — 2026-05-04 (Last Session) vs SPY

| Metric | Value |
|--------|---------|
| Portfolio equity | $99,849.69 |
| Daily return | **-1.80%** |
| SPY daily | -0.36% |
| vs SPY (daily) | **-1.43%** |
| Trades executed | **53** |
| Positions at close | 4 |

### Rolling benchmark (all available EOD data)

| Date | Portfolio | SPY | vs SPY |
|------|-----------|-----|--------|
| 2026-04-22 | +0.00% | +1.01% | **-1.01%** |
| 2026-04-23 | +1.56% | -0.39% | **+1.95%** |
| 2026-04-24 | -0.81% | +0.77% | **-1.59%** |
| 2026-04-27 | -4.88% | +0.17% | **-5.05%** |
| 2026-04-28 | -5.13% | -0.49% | **-4.65%** |
| 2026-04-29 | -5.40% | -0.01% | **-5.39%** |
| 2026-04-30 | -2.67% | +0.96% | **-3.63%** |
| 2026-05-01 | +1.82% | +0.29% | **+1.53%** |
| 2026-05-04 | -1.80% | -0.36% | **-1.43%** |
| **9-day cumul.** | **≈ -16.8%** | **≈ +2.1%** | **≈ -18.9%** |

5-day (04-28 → 05-04): portfolio -12.8%, SPY -0.0%. 30d SPY figure from EOD: +10.71%.

---

## Positions at Close — 2026-05-04

| Symbol | Side | Qty | Avg Entry | Price at Close | P&L % |
|--------|------|-----|-----------|---------------|--------|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** |
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** |

*All P&L computed from `avg_entry` vs `current_price` (Alpaca unrealized_plpc ignored per data note).*

---

## Trades — 2026-05-04 (Full Analysis in Phase 2)

53 events total. Key round-trips:

| Symbol | Action | Entry | Exit | Day P&L | Driver |
|--------|--------|-------|------|---------|--------|
| MU | BUY→SELL | $583.49 | $580.81 | **-0.46%** | Arbiter exit (weak momentum) |
| WDC | BUY→SELL | $442.28 | $440.06 | **-0.50%** | Arbiter exit (gap-only, bearish EMA) |
| COIN | BUY→SELL | $204.82 | $203.45 | **-0.67%** | Arbiter exit (score 0, earnings risk) |
| GOOGL | BUY→SELL | $382.82 | $382.77 | **-0.01%** | Arbiter exit (score 0, fading) |
| LLY | BUY→SELL | $961.30 | $963.71 | **+0.25%** | Verifier dust-sweep |
| DELL | BUY→SELL | $209.91 | $210.94 | **+0.49%** | Verifier dust-sweep |
| FIX | BUY→SELL | $1,884.10 | $1,902.81 | **+0.99%** | Verifier dust-sweep |
| HCAI | (held) | n/a | $10.69 | **-8.78%** | Exit-arbiter exit |
| AMZN | (held) | n/a | $270.65 | — | Arbiter exit |
| GEV | (held) | n/a | $1,071.49 | — | Arbiter exit |
| UNH | (held) | n/a | $368.25 | — | Arbiter exit (rotate to LLY) |

*(Full analysis appending in next commit)*

---
