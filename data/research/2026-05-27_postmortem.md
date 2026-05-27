# Post-Mortem 2026-05-27

> **Note:** Today's live market data is unavailable (sandbox constraints — Alpaca, yfinance, Telegram all blocked). This post-mortem analyses the most recent available trading session: **2026-05-04 (Monday)**. All figures are derived solely from in-repo data files.

---

## Data Availability

| File | Status |
|---|---|
| `data/research/2026-05-04_eod.json` | ✅ Found — primary performance source |
| `data/research/20260504T*_scan.json` | ✅ Found — 6 scans (2 dry-run, 4 live) |
| `data/journal/trades.jsonl` | ✅ Found — 53 records on 2026-05-04 |
| `data/journal/decisions.jsonl` | ✅ Found — 144 decision records |
| `data/research/2026-05-27_eod.json` | ❌ Missing (no live data today) |
| Last EOD with data | `2026-05-04` (last trading day in repo) |

---

## Performance Today (2026-05-04, based on eod.json)

| Metric | Value |
|---|---|
| Portfolio return | **-1.80%** |
| SPY daily return | **-0.36%** |
| Portfolio vs SPY | **-1.44%** |
| Equity EOD | $99,849.69 |
| Positions at close | 4 (AXTX, META, PWR, SPY proxy) |
| Trades executed | **53** |

### Rolling Context

| Period | Portfolio | SPY | vs SPY |
|---|---|---|---|
| 1d (2026-05-04) | -1.80% | -0.36% | **-1.44%** |
| 5d (Apr 28 – May 4) | -12.66% | +0.38% | **-13.04%** |
| Available period (Apr 22 – May 4) | -16.31% | +10.71% | **-27.02%** |
| Max drawdown (intraperiod) | -7.12% | — | Apr 23 → Apr 29 |

> Goal is to beat SPY within risk budget. Portfolio is **materially underperforming** across all windows.

---

## Positions at Close (EOD 2026-05-04)

| Symbol | Side | Avg Entry | Current | P&L% | Mkt Value | % Portfolio |
|---|---|---|---|---|---|---|
| AXTX | Long | $46.41 | $46.61 | **+0.43%** | $14,589 | 14.6% |
| META | Long | $611.73 | $610.46 | **-0.21%** | $9,448 | 9.5% |
| PWR | Long | $758.48 | $757.38 | **-0.15%** | $11,130 | 11.1% |
| SPY (proxy) | Long | $717.52 | $718.03 | **+0.07%** | $59,696 | **59.8%** |
| Cash | — | — | — | — | $4,987 | 5.0% |

> ⚠️ **SPY proxy = 59.8% of equity.** Active picks cover only 35.2%. Alpha potential is severely diluted.

---

## Trades Today (2026-05-04, Chronological)

| Time (ET) | Event | Symbol | Qty | Price | Est P&L | Reason (truncated) |
|---|---|---|---|---|---|---|
| 10:51 | EXIT (AI-exit-arbiter) | HCAI | 1,492 | $10.69 | **-9.71% / -$1,716** | Down -8.78%, 5 concurrent momentum signals |
| 11:14 | EXIT (scan sell) | SNDK | 23.30 | $1,250.00 | **+9.57% / +$2,535** | Arbiter EXIT — redeploying capital |
| 11:14 | EXIT (scan sell) | STX | 19.40 | $740.23 | **+3.27% / +$454** | Arbiter EXIT — redeploying capital |
| ~11:30 | BUY | AMZN | 65.30 | ~$273.55† | — | Arbiter BUY 17.7% |
| ~11:30 | BUY | GEV | 14.57 | ~$1,075.5† | — | Arbiter BUY 15.6% |
| ~11:30 | BUY | COIN | 66.93 | ~$205.8† | — | Arbiter BUY 13.6% |
| ~11:30 | BUY | MU | 22.99 | ~$583.2† | — | Arbiter BUY 13.3% |
| ~11:30 | BUY | UNH | 17.27 | ~$368.2† | — | Arbiter BUY 6.4% |
| 12:04 | EXIT | AMZN | 65.30 | $270.65 | **-1.06% / -$188** | Fading momentum, below VWAP |
| 12:04 | EXIT | GEV | 14.57 | $1,071.49 | **-0.38% / -$59** | Weak momentum, below VWAP |
| 12:04 | EXIT | UNH | 17.27 | $368.25 | **+0.02% / +$1** | Fading volume, LLY stronger |
| 12:04 | BUY (increase) | COIN | 8.41 (notional) | ~$204 | — | Arbiter INCREASE 22% |
| 12:04 | BUY | LLY | 9.49 | $963.38 | — | Arbiter BUY 9.1% |
| 12:04 | BUY | SNDK† | 10.10 | $1,246.97 | — | Re-entry — memory sector |
| 12:10 | STOP HIT | SNDK (new) | 10.10 | $1,237.52 | **-0.75% / -$95** | Stop at $1,237.62 triggered |
| 12:04 | BUY | NOK | 367.24 | $13.33 | — | Arbiter BUY 4.9% |
| 13:04 | EXIT | MU | 23.01 | $580.81 | **+0.07% / +$9** | Weak momentum, bearish EMA |
| 13:04 | BUY | DELL | 57.39 | $210.52 | — | IT sector, momentum 95 |
| 13:04 | BUY | FIX | 6.30 | $1,896.50 | — | AI data center, 11.9% |
| 13:04 | BUY | GOOGL | 28.68 | $383.51 | — | Comm. Services leader 11% |
| 13:04 | BUY (increase) | LLY | 3.51 | $962.27 | — | Arbiter INCREASE 12.5% |
| 13:04 | BUY | WDC | 24.51 | $445.36 | — | Memory peer, 10.9% |
| 14:05 | EXIT | WDC | 24.51 | $440.06 | **-1.19% / -$130** | Gap-only, bearish EMA |
| 14:05 | BUY (increase) | FIX | 3.70 | $1,903.71 | — | Arbiter INCREASE 19% |
| 14:05 | EXIT (verifier) | DELL | 57.39 | $210.94 | +0.20% / +$24 | Verifier dust-sweep target=0 |
| 14:05 | EXIT (verifier) | LLY | 13.00 | $963.71 | +0.03% / +$4 | Verifier dust-sweep target=0 |
| 14:05 | BUY (verifier) | GOOGL | 9.28 | $384.43 | — | Verifier reconcile +$3,569 gap |
| 14:05 | BUY (verifier) | COIN | 5.10 | $203.90 | — | Verifier reconcile +$1,135 gap |
| 15:08 | EXIT | COIN | 66.90 | $203.45 | **-0.22% / -$30** | Momentum 0, fading, earnings 3d |
| 15:08 | EXIT | FIX | 10.00 | $1,902.81 | — | Verifier dust-sweep target=0 |
| 15:08 | EXIT | GOOGL | 37.96 | $382.77 | **-0.19% / -$28** | Momentum 0, below EMA20 |
| 15:08 | BUY | AXTX | 313.0 | $46.41 | — | Momentum 100, breaking out |
| 15:08 | BUY | META | 15.48 | $611.73 | — | Comm. Services, 9.5% |
| 15:08 | BUY | PWR | 14.69 | $758.48 | — | AI data center, 11.1% |

> † Entry prices for AMZN/GEV/COIN/MU/UNH (~11:30 ET entries) are reconstructed from `unrealized_plpc` at the 12:04 exit scan; exact fills not in `trades.jsonl`.
> SNDK second entry was immediately stopped out at 12:10 ET.

---

## (Full analysis appending in next commit)
