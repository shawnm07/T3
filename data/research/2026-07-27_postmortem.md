# Post-Mortem 2026-07-27

## Data Availability

**Critical: No trading data for 2026-07-27.**

The bot has been silent since **2026-05-04T19:55Z** (~83 calendar days / ~58 trading days). All analysis in this report covers the **last live session: 2026-05-04**, which is also the focus of this post-mortem given it was the final active trading day before the outage.

| Source | Status | Last Entry |
|---|---|---|
| `_eod.json` | ✓ Available | `2026-05-04_eod.json` |
| Intraday scans | ✓ Available | `20260504T190848_scan.json` |
| `trades.jsonl` | ✓ Available | `2026-05-04T19:55:03Z` (204 lines) |
| `decisions.jsonl` | ✓ Available | `2026-05-04T20:15:04Z` (1556 lines) |
| Today's EOD (`2026-07-27_eod.json`) | ✗ MISSING | — |
| Any scan post 2026-05-04 | ✗ MISSING | — |
| Alpaca API | BLOCKED (403) | — |
| yfinance / Alpha Vantage / Twelve Data | BLOCKED (403) | — |

**Root cause candidates (from prior daily reviews):**
1. Trading scheduler (`scripts/scan_and_trade.py`) disabled or silently failing since 2026-05-04.
2. Bot running but writing to a different filesystem / branch not committed to this repo.
3. Alpaca paper account PA34KBGT3V7E may be frozen at the 2026-05-04 state.

---

## Performance — 2026-05-04 (Last Active Session)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| vs SPY (daily) | **-1.43%** |
| Closing equity | $99,849.69 |
| Trades executed | **53** (extremely high for swing cadence) |
| Positions at close | 4 |

### Rolling Context

| Date | Portfolio | SPY | vs SPY | Equity |
|---|---|---|---|---|
| 2026-04-22 | +0.00% | +1.01% | -1.01% | $99,627 |
| 2026-04-23 | +1.56% | -0.39% | +1.95% | $101,208 |
| 2026-04-24 | -0.81% | +0.77% | -1.59% | $99,343 |
| 2026-04-27 | -4.88% | +0.17% | -5.05% | $96,448 |
| 2026-04-28 | -5.13% | -0.49% | -4.65% | $96,867 |
| 2026-04-29 | -5.40% | -0.01% | -5.39% | $93,999 |
| 2026-04-30 | -2.67% | +0.96% | -3.63% | $95,786 |
| 2026-05-01 | +1.82% | +0.29% | +1.53% | $101,101 |
| **2026-05-04** | **-1.80%** | **-0.36%** | **-1.43%** | **$99,850** |

**5-day summary (Apr 28 → May 4):** Portfolio +3.1% vs SPY estimated +0.4% → +2.7% outperformance.
**Period vs SPY (from eod.json):** -10.71% (portfolio significantly underperformed SPY over the measured period).

---

## Positions at Close — 2026-05-04

| Symbol | Side | Qty | Avg Entry | Close Price | P&L % | Market Value | Notes |
|---|---|---|---|---|---|---|---|
| AXTX | LONG | 313 | $46.41 | $46.61 | **+0.43%** | $14,589 | Tradr 2X Long AXTI ETF; entered same session |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** | $9,448 | New entry, starter (70% of target) |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** | $11,130 | New entry, starter (70% of target) |
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** | $59,696 | Cash proxy ~59.8% of portfolio |

**Positions frozen since 2026-05-04.** If Alpaca account shows the same state today (2026-07-27), these four positions have been held unmonitored for 83 days.

---

## Trades — 2026-05-04

53 events logged (11 closes, 15 AI buys/increases, 3 wash-trade recoveries, 24 exit-learning metrics).

### Closes

| Symbol | Qty | Fill Price | Reason |
|---|---|---|---|
| HCAI | 1,492 | $10.69 | Exit-arbiter: down -8.78% |
| AMZN | 65.30 | $270.65 | Arbiter: fading momentum, below VWAP |
| GEV | 14.57 | $1,071.49 | Arbiter: weak momentum, below VWAP |
| UNH | 17.27 | $368.25 | Arbiter: fading volume |
| MU | 23.01 | $580.81 | Arbiter: weak/flat momentum, bearish EMA |
| WDC | 24.51 | $440.06 | Arbiter: gap-only classification, bearish EMA |
| COIN | 66.90 | $203.45 | Arbiter: momentum=0, earnings in 3 days |
| GOOGL | 37.96 | $382.77 | Arbiter: momentum=0, fading, below EMA20 |
| DELL | 57.39 | $210.94 | Verifier dust-sweep (target=0) |
| LLY | 13.00 | $963.71 | Verifier dust-sweep (target=0) |
| FIX | 10.00 | $1,902.81 | Verifier dust-sweep (target=0) |

### Buys / Increases

| Symbol | Action | Qty | Fill Price | Target % | Reason |
|---|---|---|---|---|---|
| LLY | BUY | 9.49 | $963.38 | 9.1% | Strong continuation, bullish EMA |
| MU | INCREASE | 25.00 | $580.42 | 28.0% | Pool leader, perfect momentum |
| NOK | BUY | 367.24 | $13.33 | 4.9% | Strong continuation (later exited same scan) |
| SNDK | BUY | 10.10 | $1,246.97 | 12.6% | Best new candidate |
| DELL | BUY | 57.39 | $210.52 | 12.1% | IT sector leader, score 95 |
| FIX | BUY | 6.30 | $1,896.50 | 11.9% | ai_data_center_power peer leader |
| GOOGL | BUY | 28.68 | $383.51 | 11.0% | Comm Services leader |
| LLY | INCREASE | 3.51 | $962.27 | 12.5% | 120-min cooldown with acceptable cont. |
| WDC | BUY | 24.51 | $445.36 | 10.9% | Memory peer leader vs MU |
| COIN | BUY (verifier) | 5.10 | $203.90 | 14.8% target reconcile | Verifier gap fill |
| FIX | INCREASE | 3.70 | $1,903.71 | 19.0% | Perfect momentum, breaking out |
| GOOGL | BUY (verifier) | 9.28 | $384.43 | 14.6% target reconcile | Verifier gap fill |
| AXTX | BUY | 313.00 | $46.41 | 14.4% | Momentum score 100, breaking_out |
| META | BUY | 15.48 | $611.73 | 9.5% | Comm services, acceptable continuation |
| PWR | BUY | 14.69 | $758.48 | 11.1% | ai_data_center_power, bullish EMA |

---

## (Full analysis appending in next commit)
