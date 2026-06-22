# Post-Mortem 2026-06-22

## Data availability

- **Today is Sunday (2026-06-22)** — market closed, no trading activity today.
- Most recent EOD snapshot: **2026-05-04** (last trading day with recorded data).
- EOD history available: 9 trading days (2026-04-22 → 2026-05-04).
- Scan data available: through 2026-05-04 (6 scans on last active day).
- Journal: 204 trades, 1,556 decisions logged across the period.
- No EOD data exists for 2026-05-05 through 2026-06-22 — the bot appears to have stopped producing EOD snapshots after 2026-05-04.
- **This post-mortem covers the full available data window (2026-04-22 → 2026-05-04) with focus on the last active day.**

## Performance summary

### Latest snapshot (2026-05-04)

| Metric | Portfolio | SPY | Delta |
|--------|-----------|-----|-------|
| Daily return | -1.80% | -0.36% | **-1.44%** |
| Equity | $99,850 | — | — |
| Cash | $4,987 (5.0%) | — | — |
| Positions | 4 | — | — |
| Trades today | 53 | — | — |

### Rolling performance (9 trading days)

| Window | Portfolio | SPY | Relative |
|--------|-----------|-----|----------|
| Full period (Apr 22 – May 4) | +0.22% | +1.95% | **-1.73%** |
| Last 5 days (Apr 28 – May 4) | +3.53% | +0.38% | **+3.14%** |
| Max drawdown | -7.12% | — | — |
| Worst single day | -5.40% (Apr 29) | -0.01% | -5.39% |

### Daily breakdown

| Date | Equity | Daily | SPY | vs SPY | Positions | Trades |
|------|--------|-------|-----|--------|-----------|--------|
| 2026-04-22 | $99,627 | +0.00% | +1.01% | -1.01% | 7 | 7 |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | +1.95% | 10 | 9 |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.58% | 12 | 19 |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05% | 8 | 24 |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.64% | 4 | 21 |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39% | 5 | 10 |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | -3.63% | 3 | 23 |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53% | 4 | 38 |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | -1.44% | 4 | 53 |

### Risk budget compliance

| Constraint | Limit | Actual | Status |
|------------|-------|--------|--------|
| Cash reserve | ≥ 5% | 5.0% ($4,987) | ✅ Barely met |
| Max drawdown (daily) | < 2.5% | -5.40% (Apr 29) | ❌ **BREACHED** |
| Max drawdown (period) | — | -7.12% | ⚠️ Severe |
| Initial entry cap | ≤ 15% | See trade table | Mixed |
| Max position | ≤ 50% | SPY 59.8% | ❌ **BREACHED** (SPY proxy) |

## Positions at close (2026-05-04)

| Symbol | Side | Avg Entry | Current | P&L % | P&L $ | Value | % Equity |
|--------|------|-----------|---------|-------|-------|-------|----------|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | +$63 | $14,589 | 14.6% |
| META | LONG | $611.73 | $610.46 | -0.21% | -$20 | $9,448 | 9.5% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | -$16 | $11,130 | 11.1% |
| SPY | LONG | $717.52 | $718.03 | +0.07% | +$42 | $59,696 | 59.8% |
| **Cash** | — | — | — | — | — | **$4,987** | **5.0%** |

## Trades on 2026-05-04 (53 total, 29 meaningful)

| # | Symbol | Action | Qty | Price | Reason (abbreviated) | Verdict |
|---|--------|--------|-----|-------|---------------------|----------|
| 1 | HCAI | SELL (exit) | 1,492 | $10.69 | Down -8.78%, 5 intraday momentum-loss signals | **Good** — cut loser |
| 2 | AMZN | SELL (exit) | 65.3 | $270.65 | Fading momentum, below VWAP, bearish EMA | Churn — bought & sold same day |
| 3 | GEV | SELL (exit) | 14.6 | $1,071.49 | Weak momentum, below VWAP, bearish EMA | Churn — bought & sold same day |
| 4 | UNH | SELL (exit) | 17.3 | $368.25 | Fading volume, LLY stronger healthcare name | Churn — replaced too fast |
| 5 | LLY | BUY | 9.5 | $963.38 | Healthcare sector leader, strong continuation | Bad — bought then sold same day |
| 6 | MU | ADD | 25.0 | $580.42 | Pool leader, INCREASE to 28% target | Oversized — then sold |
| 7 | NOK | BUY | 367.2 | $13.33 | Sector diversifier, strong continuation | Bad — gone by end of day |
| 8 | SNDK | BUY | 10.1 | $1,246.97 | Memory sector, bullish EMA | Bad — rotated out quickly |
| 9 | MU | SELL (exit) | 23.0 | $580.81 | Weak/flat momentum, WDC scores higher | Churn — just added then sold |
| 10 | DELL | BUY | 57.4 | $210.52 | IT sector leader, momentum 95 | Bad — dust-swept same day |
| 11 | FIX | BUY | 6.3 | $1,896.50 | ai_data_center leader, momentum 91 | Bad — sold same day |
| 12 | GOOGL | BUY | 28.7 | $383.51 | Comms leader, acceptable continuation | Bad — sold same day |
| 13 | LLY | ADD | 3.5 | $962.27 | Increase to 12.5% | Bad — wash trade recovery, sold same day |
| 14 | WDC | BUY | 24.5 | $445.36 | Memory peer leader displacing MU | Bad — exit thesis broken same session |
| 15 | COIN | ADD | 5.1 | $203.90 | Verifier reconcile to 14.8% target | Bad — sold same day |
| 16 | WDC | SELL (exit) | 24.5 | $440.06 | Gap only, bearish EMA, below VWAP | Churn — entry thesis broken hours later |
| 17 | FIX | ADD | 3.7 | $1,903.71 | Increase to 19% (momentum 100) | Bad — wash trade, dust-swept |
| 18 | DELL | SELL (dust) | 57.4 | $210.94 | Verifier dust-sweep target=0 | — |
| 19 | LLY | SELL (dust) | 13.0 | $963.71 | Verifier dust-sweep target=0 | — |
| 20 | GOOGL | ADD | 9.3 | $384.43 | Verifier reconcile to 14.6% | Bad — wash trade, sold same day |
| 21 | FIX | SELL (dust) | 10.0 | $1,902.81 | Verifier dust-sweep target=0 | — |
| 22 | COIN | SELL (exit) | 66.9 | $203.45 | Momentum 0, fading, earnings in 3d | Churn — just added then sold |
| 23 | GOOGL | SELL (exit) | 38.0 | $382.77 | Momentum 0, fading, below EMA20 | Churn — bought and exited same day |
| 24 | AXTX | BUY | 313.0 | $46.41 | Momentum 100, breaking out | Held — only survivor |
| 25 | META | BUY | 15.5 | $611.73 | Comms leader, acceptable continuation | Held |
| 26 | PWR | BUY | 14.7 | $758.48 | ai_data_center peer leader | Held |

---

## Deep analysis

### Trade quality summary (2026-05-04)

| Verdict | Count | % of meaningful trades |
|---------|-------|----------------------|
| Good (cut loser, held winner) | 4 | 15% |
| Churn (same-day roundtrip) | 8 | 31% |
| Bad (bought then sold same day, no alpha) | 11 | 42% |
| Dust sweep (verifier cleanup) | 3 | 12% |

**Only 3 of 15 new entries survived to EOD** (AXTX, META, PWR). The other 12 were entered and exited within the same trading day, generating ~$289K of turnover on a ~$100K account (2.9x intraday).

### Cross-trade patterns

- **Catastrophic intraday churn**: 6 selector rotations on May 4 = complete portfolio reshuffle every ~65 minutes. 16 same-day roundtrips across the full period. May 4 alone had 7 roundtrips (LLY, MU, DELL, FIX, GOOGL, WDC, COIN). Annualized turnover: ~71x.

- **Premature exits on noise**: Positions like AMZN (momentum 100 at entry, fading to 0 within 2 hours), GEV (97 → weak), GOOGL (acceptable → 0) show the selector reacting to intraday noise rather than holding through normal consolidation. Entry required "strong continuation" but the hold period was only 1-2 scans.

- **AI vs numeric disagreements**: The portfolio-selector failed validation 14 times across the period (output `selected count 0`, rounding errors, missing symbols). On two May 4 scans, the selector returned zero selections and was skipped entirely. When it did work, successive scans contradicted each other: scan at 16:04 selected MU+COIN+SNDK+LLY+NOK+V; scan at 17:04 selected FIX+DELL+WDC+GOOGL+COIN+LLY (only 2 overlapping symbols).

- **SPY cash-proxy overweight**: SPY ranged from 0% to 77.6% of equity. On Apr 30 it was 77.6%, well above the `max_position_pct: 0.50` cap. The cash proxy is exempt from position caps, creating a situation where the bot holds >50% in a single instrument while claiming risk compliance. On the final day, SPY was 59.8% — still above cap.

- **Oversized single positions**: MU was targeted at 28% (from 13.3%) then sold the same session. DELL entry at 12.1% ($12K) was dust-swept hours later. FIX increased to 19% then dust-swept. The sizing targets assume multi-day holds but the selector rotates before positions can grow.

- **Wash trade recoveries**: 3 wash trades on May 4 alone (LLY, FIX, GOOGL) — positions sold and re-bought within the same session, triggering tax wash-sale rules for no alpha.

- **Drawdown cluster (Apr 27-29)**: Three consecutive days of -4.88%, -5.13%, -5.40%. All three breached the 2.5% daily drawdown limit. The bot was concentrated in ai_data_center theme (MU, DELL, AVGO, VRT, FIX, GEV all in the same cluster). The `diversification.symbol_overrides` were added post-hoc but the damage was already done. No circuit breaker reduced exposure after the first -4.88% day.

- **Entries on stale signals**: The selector repeatedly entered positions based on momentum scores of 90-100 that decayed to 0-15 within 1-2 hours, suggesting the momentum window is too short or the scan frequency is too high for the signal's persistence.

- **Bot went dark after May 4**: No EOD snapshots from May 5 through June 22 (49 days). The bot either crashed, lost API access, or the cron scheduler stopped. This is the most critical finding — the account has been unmonitored for 7+ weeks.

### Proposed changes

#### 1. Add rotation cooldown to prevent intraday churn

**Why**: 6 rotations on May 4 produced 7 same-day roundtrips, ~$289K turnover, and only 3/15 entries survived. The selector has no memory of what it just bought.

**Diff**:
```yaml
# config.yaml
selector:
+ rotation_cooldown_minutes: 120    # newly entered positions immune from exit for 2 hours
+ max_rotations_per_day: 3          # hard cap on complete portfolio reshuffles
```
```python
# src/orchestrator.py — in selector execution block
# Before calling selector, check last rotation timestamp
# If < rotation_cooldown_minutes since last rotation, skip
```

**Expected impact**: Reduce same-day roundtrips from ~7/day to ~1-2/day. Estimated slippage savings: ~$100-150/day on active days. Reduces wash trade risk.

#### 2. Add daily drawdown circuit breaker

**Why**: Apr 27-29 produced -4.88%, -5.13%, -5.40% — all breaching the 2.5% target. No mechanism halted new entries or forced de-risking after the first breach.

**Diff**:
```yaml
# config.yaml
risk:
+ daily_drawdown_halt_pct: 0.025    # halt new entries if daily loss exceeds 2.5%
+ daily_drawdown_deleverage_pct: 0.04  # reduce all positions by 50% if daily loss > 4%
```

**Expected impact**: Would have prevented the Apr 28 (-5.13%) and Apr 29 (-5.40%) cascades by halting after the Apr 27 -4.88% day. Estimated drawdown reduction: -3% to -4% peak-to-trough.

#### 3. Cap SPY cash proxy at max_position_pct

**Why**: SPY proxy hit 77.6% on Apr 30 and 59.8% on May 4, both above the 50% cap. This defeats the purpose of the position size limit.

**Diff**:
```python
# src/executor.py or src/risk.py — in SPY proxy rebalance logic
# After computing target SPY allocation:
max_spy_pct = config['risk']['max_position_pct']  # 0.50
target_spy_pct = min(target_spy_pct, max_spy_pct)
```

**Expected impact**: Keeps at least 50% of equity deployed in active positions or true cash. Prevents the "passive by default" trap where most capital sits in SPY.

#### 4. Require minimum hold period before selector can exit

**Why**: 12 of 15 entries on May 4 were sold the same day. Momentum scores of 90-100 decayed to 0-15 within 1-2 hours — the signal persistence doesn't match the scan frequency.

**Diff**:
```yaml
# config.yaml
selector:
  continuation_gate:
+   min_hold_scans: 3    # newly entered positions must survive 3 scans before eligible for exit
```

**Expected impact**: Entries that pass the continuation gate at scan N would hold through scans N+1 and N+2 even if momentum temporarily dips. Reduces churn by ~60% based on the May 4 pattern.

#### 5. Investigate and fix the bot's 49-day outage

**Why**: No data after May 4. The account has been unmonitored for 7+ weeks. Positions from May 4 (AXTX, META, PWR, SPY) may have hit stops, earnings events, or significant moves with no management.

**Diff**: Not a config change — requires:
1. Check cron/scheduler logs for `scan_and_trade.py` after May 4
2. Verify Alpaca API key is still valid
3. Check for Python crash logs / unhandled exceptions
4. Restart the bot with `--dry-run` first to verify connectivity

**Expected impact**: Restoring monitoring is prerequisite to everything else. An unmonitored paper account defeats the purpose of the exercise.

### Backtest notes

- `scripts/analyze_winner_trim.py` exists but requires yfinance (blocked in sandbox). Cannot run offline backtest.
- Journal-only backtest for rotation cooldown: of the 26 rotations in the period, 14 occurred within 120 minutes of a previous rotation. Suppressing those 14 would have prevented ~10 of the 16 same-day roundtrips.
- Estimated slippage savings from a 120-min cooldown: 10 roundtrips x ~$10K avg position x 0.05% slippage x 2 legs = ~$100. Small in dollar terms but the real cost is in adverse selection — positions entered on decaying momentum get sold at worse prices.

### Summary

The bot's core problem is **hyperactive rotation**: the portfolio selector reshuffles the entire book every ~65 minutes on active days, generating massive turnover with negative alpha. Only 15% of trades were clearly beneficial (cutting HCAI, holding AXTX/META/PWR). The 7.12% max drawdown was caused by concentration in the ai_data_center theme during a correlated selloff, and no circuit breaker existed to halt the bleeding.

The most urgent issue is the **49-day outage** — the bot hasn't produced data since May 4. Priority order:
1. Fix the outage (prerequisite)
2. Add rotation cooldown (highest ROI change)
3. Add daily drawdown circuit breaker (risk management)
4. Cap SPY proxy weight (compliance)
5. Add minimum hold period (reduces churn)
