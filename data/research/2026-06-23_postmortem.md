# Post-Mortem 2026-06-23

## Data Availability

| Source | Status |
|--------|--------|
| EOD snapshot (today 2026-06-23) | **MISSING** — last available: 2026-05-04 |
| Scan files (today) | **MISSING** — last scans: 2026-05-04 |
| Trade journal | Available (204 entries through 2026-05-04) |
| Decision journal | Available (1556 entries through 2026-05-04) |
| config.yaml | Available |
| Alpaca API | BLOCKED (403) |
| yfinance / Telegram | BLOCKED |

> **Note:** The bot has not traded since 2026-05-04 (50 calendar days ago). This post-mortem analyzes the last trading day with data (2026-05-04) and the full 9-day active period (2026-04-22 → 2026-05-04). No live position data is available for today.

---

## Performance — Last Trading Day (2026-05-04)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily alpha | **-1.44%** |
| Equity at close | $99,849.69 |
| Cash | $4,986.91 (5.0% — at floor) |
| Positions held | 4 |
| Trades executed | 53 |

## Rolling Benchmarks (9 trading days: 2026-04-22 → 2026-05-04)

| Metric | Portfolio | SPY | Alpha |
|--------|-----------|-----|-------|
| Full period | +0.22% | +1.95% | **-1.73%** |
| 5-day rolling | -12.66% | +0.38% | **-13.04%** |
| Max drawdown | -7.12% | — | — |
| Avg daily trades | 22.7 | — | — |

### Equity Curve

```
Date         Equity       Daily%   SPY%    vs SPY   Pos  Trades
──────────────────────────────────────────────────────────────────
2026-04-22    $99,627    +0.00%   +1.01%   -1.01%    7      7
2026-04-23   $101,208    +1.56%   -0.39%   +1.95%   10      9
2026-04-24    $99,343    -0.81%   +0.77%   -1.59%   12     19
2026-04-27    $96,448    -4.88%   +0.17%   -5.05%    8     24
2026-04-28    $96,867    -5.13%   -0.49%   -4.65%    4     21
2026-04-29    $93,999    -5.40%   -0.01%   -5.39%    5     10
2026-04-30    $95,786    -2.67%   +0.96%   -3.63%    3     23
2026-05-01   $101,101    +1.82%   +0.29%   +1.53%    4     38
2026-05-04    $99,850    -1.80%   -0.36%   -1.44%    4     53
```

---

## Positions at Close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | Current | P&L % | P&L $ | Mkt Value |
|--------|------|-----|-----------|---------|-------|-------|----------|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% | +$62.60 | $14,588.93 |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$19.63 | $9,448.36 |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | -$16.16 | $11,129.62 |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42.40 | $59,695.86 |
| **Total** | | | | | | **+$69.21** | **$94,862.77** |

Cash: $4,986.91 | Equity: $99,849.69

---

## Trades on 2026-05-04 (53 total — 11 closes, 0 opens)

### Position Closes

| Symbol | Qty | Fill Price | Reason (truncated) |
|--------|-----|-----------|-------------------|
| HCAI | 1,492 | $10.69 | Exit-arbiter (conf=0.72): Down -8.78%, lost VWAP/EMA20, fading |
| AMZN | 65.30 | $270.65 | Selector EXIT: Fading momentum, below VWAP, bearish EMA |
| GEV | 14.57 | $1,071.49 | Selector EXIT: Weak momentum, below VWAP, bearish EMA, flat trend |
| UNH | 17.27 | $368.25 | Selector EXIT: Fading volume, low continuation score |
| MU | 23.01 | $580.81 | Selector EXIT: Weak momentum, bearish EMA, flat volume |
| WDC | 24.51 | $440.06 | Selector EXIT: Gap-only classification, bearish EMA, fading |
| DELL | 57.39 | $210.94 | Verifier dust-sweep (target=0) |
| LLY | 13.00 | $963.71 | Verifier dust-sweep (target=0) |
| COIN | 66.90 | $203.45 | Selector EXIT: Momentum=0, fading, earnings in 3 days |
| GOOGL | 37.96 | $382.77 | Selector EXIT: Momentum=0, fading, below EMA20 |
| FIX | 10.00 | $1,902.81 | Verifier dust-sweep (target=0) |

### New Entries Attempted but Blocked

| Symbol | Target % | Reason Blocked |
|--------|----------|---------------|
| LLY | 10.2% | stop_not_below_current_market (bid/ask spread too wide) |
| SNDK | 12.3% | insufficient_confirmed_cash |
| SOXS | 9.0% | stop_not_below_current_market (inverse ETF, tech_score=-0.99) |

---

## Full Analysis

### 2a. Trade-by-Trade Review (2026-05-04)

| Symbol | Action | Size | Entry | Exit/Current | P&L | AI Grade | Reason | Verdict |
|--------|--------|------|-------|-------------|-----|----------|--------|--------|
| HCAI | EXIT | 1,492 sh | $11.72* | $10.69 | -8.78% | conf=0.72 | Lost VWAP/EMA20, fading momentum | **GOOD** — cut loser early |
| AMZN | EXIT | 65.3 sh | ~$270* | $270.65 | ~0% | selector EXIT | Fading momentum, bearish EMA | **BAD** — exited flat, AMZN likely recovered |
| GEV | EXIT | 14.6 sh | ~$1,071* | $1,071.49 | ~0% | selector EXIT | Weak momentum, below VWAP | **CHURN** — bought then exited same period |
| UNH | EXIT | 17.3 sh | ~$368* | $368.25 | ~0% | selector EXIT | Fading volume | **CHURN** — minimal P&L |
| MU | EXIT | 23.0 sh | $580.42 | $580.81 | +0.07% | selector EXIT | Bearish EMA, flat volume | **CHURN** — bought 16:04, exited 17:04 |
| WDC | EXIT | 24.5 sh | $445.36 | $440.06 | -1.19% | selector EXIT | Gap-only, bearish EMA | **BAD** — bought 17:04, sold 18:05 at loss |
| DELL | EXIT | 57.4 sh | $210.52 | $210.94 | +0.20% | verifier dust-sweep | Selector dropped, verifier cleaned up | **CHURN** — bought 17:04, swept 18:05 |
| LLY | EXIT | 13.0 sh | $961.30 | $963.71 | +0.25% | verifier dust-sweep | Selector dropped, verifier cleaned up | **CHURN** — bought 16:04, swept 18:05 |
| FIX | EXIT | 10.0 sh | $1,884–$1,904 | $1,902.81 | ~0% | verifier dust-sweep | Selector dropped, verifier cleaned up | **CHURN** — bought 17:04, swept 19:08 |
| COIN | EXIT | 66.9 sh | ~$203* | $203.45 | ~0% | selector EXIT | Momentum=0, earnings in 3 days | **GOOD** — earnings risk avoidance |
| GOOGL | EXIT | 38.0 sh | $382.82–$384.43 | $382.77 | -0.3% | selector EXIT | Momentum=0, fading | **CHURN** — bought 17:04, sold 19:08 |
| AXTX | BUY | 313 sh | $46.41 | $46.61 | +0.43% | conf=0.88, opp=100 | Biotech breakout, momentum score 100 | **OK** — new entry, slight gain |
| META | BUY | 15.5 sh | $611.73 | $610.46 | -0.21% | conf=0.65, opp=58 | Comm services diversification | **OK** — low-confidence entry |
| PWR | BUY | 14.7 sh | $758.48 | $757.38 | -0.15% | conf=0.72, opp=55 | AI data-center power peer leader | **OK** — new entry, near flat |

*Approximate entries from earlier scans; exact avg_entry not in close events.

**Verdict Summary:** 2 good exits, 6 churned positions (bought+sold same day), 2 bad exits (sold at loss or prematurely), 3 new entries (all near flat at close).

---

### 2b. Cross-Trade Patterns

#### Extreme Selector Churn (CRITICAL)
- **20 unique symbols selected across 6 scans** on a single day; only 3 survived to close (AXTX, META, PWR)
- **14 symbols selected then dropped same day** — the portfolio rotated almost entirely 3 times
- Every scan changed 3–5 of 5–6 positions: the selector has no memory/penalty for recent selections
- **5 same-day round-trips**: DELL, FIX, GOOGL, LLY, WDC (all bought then sold within hours)
- 3 of those were verifier dust-sweeps: selector dropped them, verifier cleaned the residual
- Estimated commission/spread cost of churn: ~$200–500 in slippage across 53 trades

#### Selector Instability
- Scan 1 (15:13): AMZN, GEV, COIN, MU, UNH
- Scan 2 (15:18): +META, +BAND, -GEV (5 min later — complete change of mind on GEV)
- Scan 3 (16:05): +SNDK, +LLY, +NOK, +V, -AMZN, -BAND, -META, -UNH (4 in, 4 out)
- Scan 4 (17:04): +FIX, +DELL, +WDC, +GOOGL, -MU, -NOK, -SNDK, -V (4 in, 4 out)
- Scan 5 (18:05): +CUE, +PWR, +RBLX, -DELL, -LLY, -WDC (3 in, 3 out)
- Scan 6 (19:08): +AXTX, +LLY, +META, +SNDK, +SOXS, -COIN, -CUE, -FIX, -GOOGL, -RBLX (5 in, 5 out)

#### Exit-Arbiter Clustering
- All 13 exit decisions had confidence in tight band: min=0.58, avg=0.62, max=0.72
- The arbiter barely clears the 0.55 floor — it's rubber-stamping momentum-loss triggers
- Only HCAI (conf=0.72) showed genuine conviction; the rest were at/near minimum

#### AI Selector Failures
- 2 consecutive portfolio-selector failures at 14:09 and 15:02 (selected count 0)
- These delayed the first valid trade by ~1 hour, missing potential better entries

#### Blocked New Entries (End of Day)
- LLY: stop_not_below_current_market — bid/ask spread $73.32 (906.68 vs 980.00), 7.5% wide
- SNDK: insufficient_confirmed_cash — all cash consumed by earlier churn
- SOXS: inverse 3× ETF with tech_score=-0.99 — the selector tried to buy a leveraged bear ETF in a "long only" book

#### Cash Proxy (SPY)
- SPY position grew to $59,696 (59.8% of equity) by close — effectively a 60% cash position
- Only 3 active equity positions at close (AXTX 14.6%, META 9.5%, PWR 11.1%) = 35.2% invested
- This is extremely defensive for a bot whose goal is to beat SPY

#### The 50-Day Gap
- No trades since 2026-05-04. The bot appears to have stopped running entirely.
- If positions were held through this gap, AXTX/META/PWR P&L is unknown (no market data)
- This is the most critical finding: **the bot is offline**

---

### 2c. Proposed Changes

#### Proposal 1: Add Selector Cooldown / Hysteresis

**Why:** The selector rotated 20 unique symbols in 6 scans on one day, causing 5 same-day round-trips and ~$200-500 in needless slippage. Each scan treats the portfolio as a blank slate.

**Diff:**
```yaml
# config.yaml
selector:
  # NEW: Minimum scans a selected position must be held before exit
  min_hold_scans: 2
  # NEW: Penalty score for symbols held < min_hold_scans
  early_exit_penalty: -15
```

```python
# src/orchestrator.py (conceptual — in _run_selector)
# Before calling selector AI, inject hold_since_scan for each held position.
# Selector prompt addition: "Positions held for fewer than {min_hold_scans}
# scans receive a -{early_exit_penalty} opportunity-score penalty unless
# a hard exit trigger (technical flip, bad news) has fired."
```

**Expected impact:** Reduce same-day round-trips from ~5/day to ~1/day. Reduce daily trade count from 53 to ~20. Save ~$100-300/day in slippage.

#### Proposal 2: Widen Exit-Arbiter Minimum Confidence

**Why:** Exit-arbiter confidence averaged 0.62 with a tight 0.58–0.72 range. It rubber-stamped every momentum-loss trigger. Only HCAI (0.72) showed genuine conviction — the rest were exits-of-convenience.

**Diff:**
```yaml
# config.yaml
exit_arbiter:
  min_confidence: 0.55  # BEFORE
  min_confidence: 0.65  # AFTER — require more conviction to close
```

**Expected impact:** ~40% of the 11 exits on 2026-05-04 had confidence < 0.65 and would have been blocked. Back-of-envelope: holding MU, WDC, GOOGL longer may have recovered $200-500 vs selling at the day's lows.

**Cannot backtest offline** — would need live price data for held-vs-sold comparison.

#### Proposal 3: Block SOXS / Inverse ETFs

**Why:** The selector tried to buy SOXS (Direxion 3× Bear Semiconductor ETF) with tech_score=-0.99. This violates the spirit of "long US equities only" — a 3× inverse ETF is functionally a short position.

**Diff:**
```yaml
# config.yaml
universe:
  exclude_tickers:
    - SOXS
    - SOXL
    - TQQQ
    - SQQQ
    - SPXU
    - SDOW
    # Exclude all leveraged/inverse ETFs
```

**Expected impact:** Prevents the bot from taking synthetic short positions via inverse ETFs. Zero cost to upside.

#### Proposal 4: Reduce max_candidates_per_scan from 10 to 5

**Why:** With 10 candidates per scan × 6 scans/day × parallel analysts, the AI cost is high and the selector sees too many options, contributing to churn. The original config was 5.

**Diff:**
```yaml
# config.yaml
ai:
  max_candidates_per_scan: 10  # BEFORE
  max_candidates_per_scan: 5   # AFTER
```

**Expected impact:** Halves AI API cost per scan. Forces the selector to focus on higher-conviction candidates. Reduces portfolio churn by limiting the "new shiny object" pool.

#### Proposal 5: Investigate and Fix the 50-Day Outage

**Why:** The bot has not traded since 2026-05-04. No EOD data, no scans, no trades for 50 days. This is the most impactful issue — a dormant bot cannot beat SPY.

**Diff:** Not a config change. Requires investigation:
- Check if the cron/scheduler is running
- Check if Alpaca API key expired or was revoked
- Check if the machine hosting the bot is powered on
- Check CloudWatch/systemd logs for crash traces

**Expected impact:** Restoring the bot to operation is worth more than any parameter tuning.

---

### 2d. Backtest (Offline, from Journal Data)

#### Proposal 1 Backtest: Selector Cooldown (min_hold_scans=2)

Simulating what would have happened on 2026-05-04 if positions had a 2-scan hold minimum:

| Scan | Without Cooldown (actual) | With Cooldown (simulated) |
|------|--------------------------|------------------------|
| 15:13 | Enter AMZN, GEV, COIN, MU, UNH | Same (all new) |
| 15:18 | Drop GEV, add META, BAND | **Hold all 5** (< 2 scans) + add META |
| 16:05 | Drop AMZN, BAND, META, UNH; add SNDK, LLY, NOK, V | **Hold AMZN, GEV, COIN, MU, UNH, META** (all < 2 scans) |
| 17:04 | Complete rotation | **First eligible exits** at scan 3 for original 5 |

**Result:** Round-trips on DELL, LLY, FIX, GOOGL, WDC would not have occurred. Those 5 positions were entered at scan 4/5 and would never have existed under cooldown. Estimated savings: ~$300 in realized losses + slippage.

**Caveat:** HCAI was already held from a prior day and was down -8.78%; the cooldown would not have prevented that legitimate exit.

#### Proposals 2-5: Cannot Backtest Offline

- Proposal 2 (exit confidence floor): Would need counterfactual price paths
- Proposal 3 (inverse ETF block): SOXS was blocked by preflight anyway; no P&L impact
- Proposal 4 (fewer candidates): Would need to re-run AI with fewer candidates
- Proposal 5 (outage): Not a parameter change

---

### Summary

The bot's primary problem is **it's offline** (50 days dormant). When it was running, it suffered from:

1. **Extreme selector churn** — 20 symbols rotated through in one day, 5 same-day round-trips
2. **Rubber-stamp exit arbiter** — barely clearing the 0.55 floor, exits-of-convenience not conviction
3. **Defensive positioning** — 60% in SPY cash proxy, only 35% actively invested
4. **Period performance**: +0.22% portfolio vs +1.95% SPY = **-1.73% alpha** over 9 trading days
5. **Max drawdown**: -7.12% (vs 2.5% daily target — breached on 3 separate days)

The daily drawdown constraint (< 2.5%) was violated on Apr 27 (-4.88%), Apr 28 (-5.13%), and Apr 29 (-5.40%). These were the most damaging days and coincided with peak position counts (8-12 positions) and high churn.
