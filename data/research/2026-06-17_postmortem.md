# Post-Mortem 2026-06-17

## Data availability

| Source | Status |
|--------|--------|
| EOD snapshots | 9 files: 2026-04-22 through 2026-05-04 (latest) |
| Scan files | 20 files through 2026-05-04T190848 |
| Trade journal | 204 entries total; 53 trades on 2026-05-04 |
| Decision journal | 1556 entries total; 105 decisions on 2026-05-04 |
| Live market data | UNAVAILABLE (Alpaca/yfinance blocked) |

**Note:** No new data has been generated since 2026-05-04. The bot appears to have stopped running scans after that date. This post-mortem analyzes 2026-05-04 (the last active trading day) and the full 9-day data window.

---

## Performance summary

### Latest day (2026-05-04)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily alpha | **-1.44%** |
| Equity at close | $99,849.69 |
| Cash | $4,986.91 (5.0% — at floor) |
| Positions at close | 4 |
| Trades executed | 53 |

### Rolling performance (2026-04-22 → 2026-05-04, 9 trading days)

| Date | Equity | Daily | SPY | Alpha | Positions | Trades |
|------|--------|-------|-----|-------|-----------|--------|
| 2026-04-22 | $99,627 | +0.00% | +1.01% | -1.01% | 7 | 7 |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | **+1.95%** | 10 | 9 |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.58% | 12 | 19 |
| 2026-04-27 | $96,448 | **-4.88%** | +0.17% | **-5.05%** | 8 | 24 |
| 2026-04-28 | $96,867 | **-5.13%** | -0.49% | **-4.64%** | 4 | 21 |
| 2026-04-29 | $93,999 | **-5.40%** | -0.01% | **-5.39%** | 5 | 10 |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | -3.63% | 3 | 23 |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | **+1.53%** | 4 | 38 |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | -1.44% | 4 | 53 |

**Cumulative equity return:** +0.22% ($99,627 → $99,850)
**SPY cumulative (daily sum):** +1.95%
**SPY 30d (from EOD):** +10.71%
**Net alpha vs SPY:** **-1.73%** over 9 days, **-10.71%** vs SPY 30d

### Risk budget compliance

| Constraint | Limit | Actual | Status |
|------------|-------|--------|--------|
| max_position_pct (new entry) | 15% | Up to 14.4% (AXTX staged) | OK |
| cash_reserve_pct | ≥5% | 5.0% | BORDERLINE |
| Daily drawdown | <2.5% | **-5.40%** (Apr 29) | **VIOLATED** |
| max_positions | 6 | 4 (EOD May 4) | OK |

---

## Positions at close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | Current | P&L % | P&L $ | Weight |
|--------|------|-----|-----------|---------|-------|-------|--------|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% | +$62.60 | 14.6% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$19.63 | 9.5% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | -$16.16 | 11.1% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42.40 | 59.8% |

**Portfolio composition:** 35.2% stock picks + 59.8% SPY proxy + 5.0% cash.
Effective active share is only 35.2% — the portfolio is mostly a SPY tracker with minor tilts.

---

## Trades on 2026-05-04 (53 total)

### Positions closed (11)

| Symbol | Qty | Exit Price | Reason | Verdict |
|--------|-----|------------|--------|--------|
| HCAI | 1,492 | $10.69 | AI exit conf=0.72: -8.78%, momentum lost (5 signals) | **BAD** — stop never triggered at -8.78%? |
| AMZN | 65.30 | $270.65 | Arbiter EXIT: fading momentum, below VWAP, bearish EMA | Acceptable exit |
| GEV | 14.57 | $1,071.49 | Arbiter EXIT: weak momentum, capital redeployed | Questionable — strong daily technicals |
| UNH | 17.27 | $368.25 | Arbiter EXIT: acceptable but fading, LLY preferred | Acceptable rotation |
| MU | 23.01 | $580.81 | Arbiter EXIT: weak momentum, WDC peer preferred | **CHURN** — just added 25 shares same day |
| WDC | 24.51 | $440.06 | Arbiter EXIT: gap_only, bearish EMA, fading volume | **CHURN** — bought and sold same day, lost $130 |
| DELL | 57.39 | $210.94 | Verifier dust-sweep target=0 | **CHURN** — bought $12.1K, swept by verifier |
| LLY | 13.00 | $963.71 | Verifier dust-sweep target=0 | **CHURN** — bought $12.5K, swept by verifier |
| FIX | 10.00 | $1,902.81 | Verifier dust-sweep target=0 | **CHURN** — bought $19K, swept by verifier |
| COIN | 66.90 | $203.45 | Arbiter EXIT: momentum=0, earnings in 3 days | Acceptable — earnings gate |
| GOOGL | 37.96 | $382.77 | Arbiter EXIT: momentum=0, fading, below EMA20 | **CHURN** — bought $14.6K, sold same scan |

### Positions opened/added (15 orders across 12 symbols)

| Symbol | Qty | Entry Price | Target Wt | Reason | Verdict |
|--------|-----|-------------|-----------|--------|---------|
| LLY | 9.49 | $963.38 | 9.1% | Healthcare leader, strong continuation | **CHURN** — closed same day |
| LLY | 3.51 | $962.27 | 12.5% | Increase within cooldown | **CHURN** — closed same day |
| MU | 25.0 | $580.42 | 28.0% | Pool leader, perfect momentum | **CHURN** — closed 1hr later |
| NOK | 367.24 | $13.33 | 4.9% | Sector leader, strong continuation | **MISSING FROM EOD** |
| SNDK | 10.10 | $1,246.97 | 12.6% | Best new candidate, bullish EMA | **MISSING FROM EOD** |
| DELL | 57.39 | $210.52 | 12.1% | IT sector leader, momentum 95 | **CHURN** — dust-swept same day |
| FIX | 6.30+3.70 | $1,897-1,904 | 19.0% | DC power peer leader, breaking out | **CHURN** — dust-swept same day |
| GOOGL | 28.68+9.28 | $383-384 | 14.6% | Comms leader, acceptable continuation | **CHURN** — closed same scan |
| WDC | 24.51 | $445.36 | 10.9% | Memory peer leader | **CHURN** — closed 1hr later, -$130 |
| COIN | 5.10 | $203.90 | 14.8% | Verifier reconcile to Opus target | **CHURN** — position fully closed next scan |
| AXTX | 313.0 | $46.41 | 14.4% | Breaking out, momentum 100, vol 2.79x | **HELD** — +0.43% at EOD |
| META | 15.48 | $611.73 | 9.5% | Comms sector leader, bullish EMA | **HELD** — -0.21% at EOD |
| PWR | 14.69 | $758.48 | 11.1% | DC power peer leader | **HELD** — -0.15% at EOD |

*(Full analysis appending in next commit)*
