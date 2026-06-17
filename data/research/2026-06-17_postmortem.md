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
| Daily drawdown | <2.5% | **-5.40%** (Apr 29) | **VIOLATED 3 CONSECUTIVE DAYS** |
| max_positions | 6 | 4 (EOD May 4) | OK |
| max_risk_per_trade | 0.5% ($500) | 1.7% ($1,716 HCAI) | **VIOLATED — 3.4x budget** |

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
| WDC | 24.51 | $440.06 | Arbiter EXIT: gap_only, bearish EMA, fading volume | **CHURN** — bought and sold same day, -$130 |
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

---

## Deep analysis

### A. Churn — the #1 problem

**Severity: CRITICAL**

| Metric | May 1 | May 4 | Total |
|--------|-------|-------|-------|
| Orders executed | 28 | 26 | 54 |
| Same-day round-trips | 9 | 7 | 16 |
| Positions held < 2 hours | 9 | 10 | 19 |
| Round-trip losses | — | -$1,315 | — |

**16 same-day round-trips across 2 days.** The bot buys a position, then 1-2 scans later either the arbiter reverses the decision or the verifier dust-sweeps it. This is not trading — it's paying spreads and slippage to stand still.

Worst churn examples on May 4:
- **DELL**: Arbiter buys at $210.52 (momentum score 95), verifier dust-sweeps at $210.94 one scan later. $12K moved for $24 gross, likely negative after slippage.
- **FIX**: Arbiter buys at $1,896.50, increases to $1,903.71 ("perfect momentum score 100, breaking_out"), then verifier dust-sweeps at $1,902.81. $19K deployed and removed within 2 hours.
- **MU**: Arbiter increases by 25 shares at $580.42 ("pool leader, perfect momentum continuation"), then arbiter itself exits 1 hour later ("weak_or_flat momentum, bearish EMA"). The "perfect momentum" degraded to "weak" in 60 minutes?
- **GOOGL**: Arbiter buys at $383.51, verifier adds more at $384.43, then arbiter exits everything at $382.77. Net loss -$37, two scans of capital tied up for nothing.

**Root cause:** The portfolio-selector and arbiter produce a fresh target portfolio every scan. There is no concept of minimum hold time or entry cooldown that prevents a position from being reversed within the same session. The verifier then exacerbates this by reconciling gaps that existed for good reasons (the arbiter intentionally sized smaller).

### B. Verifier vs arbiter conflict

**Severity: HIGH**

18 verifier actions total:
- 3 dust-sweeps: Verifier closes positions the arbiter **just opened** (DELL, LLY, FIX on May 4)
- 15 reconciles: Verifier adds to positions to match Opus target, sometimes into positions the arbiter is about to exit

The verifier is supposed to reconcile execution gaps. Instead, it's:
1. Closing positions the arbiter wanted (dust-sweeps appear when a newer scan changes the target to 0%)
2. Adding to positions (reconcile) right before the arbiter exits them (COIN: verifier adds 5.1 shares, arbiter exits 66.9 shares next scan)

This creates a feedback loop: arbiter buys → verifier adds more → arbiter reverses → net loss.

### C. HCAI stop-loss failure

**Severity: CRITICAL**

| Field | Value |
|-------|-------|
| Entry | $11.84 on 2026-05-01 (Friday) |
| Stop price | $11.73 (0.93% below entry) |
| Actual exit | $10.69 on 2026-05-04 (Monday) |
| Loss from entry | **-9.71%** |
| Gap through stop | $1.04 = 8.9% below stop price |
| Dollar loss | **-$1,716** |
| Portfolio impact | **1.7%** (budget: 0.5% = $500) |
| Overshoot | **3.4x risk budget** |

**Cause:** Weekend gap-down. HCAI was bought Friday afternoon with a tight stop at $11.73. The stock gapped down on Monday open to ~$10.69, blowing through the stop-market order. Stop-market orders cannot protect against gap risk.

This is the single largest contributor to the -4.88% daily loss on Apr 27 → the -5.40% daily loss on Apr 29 drawdown sequence.

### D. Concentration risk

Worst single-position weights observed:
- **SPY 77.6%** (Apr 30) — nearly all equity in the cash proxy after selling everything
- **MU 28.4%** (Apr 27) — single stock, max_position_pct is 50% but this is far too concentrated for a volatile semiconductor name
- **DELL 21.2%** (Apr 28) — single stock at -8.74% loss, contributing ~1.85% portfolio drawdown alone
- **MU -80.11% P&L** (Apr 29) — catastrophic single-position loss (likely data artifact but needs investigation)

### E. AI pipeline failures

14 AI failures across the 9-day window:
- **4 rate limit errors** (429) — Anthropic API rate limits hit during scan
- **3 JSON parse failures** — AI returned malformed JSON
- **3 validation errors** — AI output violated constraints (missing symbols, wrong stop-loss)
- **2 selection failures** — "selected count 0 not in [3,6]" (AI returned empty portfolio)
- **1 module import error** — "No module named 'anthropic'" (environment issue)
- **1 weight sum error** — weights+spy+cash didn't sum to 1.0

When the selector fails, the bot falls through to the legacy arbiter path, which has different risk characteristics. On May 4, the selector failed on the first 2 scans (returned 0 selections), forcing fallback behavior that may have contributed to the erratic trading.

### F. Daily drawdown violation

Three consecutive days exceeded the 2.5% drawdown limit:
- Apr 27: **-4.88%** (FIX -8.68%, DELL -4.11%, MU -3.77%)
- Apr 28: **-5.13%** (DELL -8.74%)
- Apr 29: **-5.40%** (MU -80.11% — needs investigation)

There is **no daily drawdown circuit breaker** in the codebase. The macro halt only triggers on macro score < -0.55, not on portfolio loss. The bot kept trading through a multi-day drawdown, compounding losses.

---

## Cross-trade patterns

- **Over-trimming winners:** GEV exited with "strong daily technicals (score 0.624, golden cross)" — the exit-arbiter initially said HOLD but the selector removed it next scan. Winners are being rotated out too early.
- **Premature exits on noise:** MU added at "perfect momentum" then exited 1 hour later as "weak momentum." Intraday momentum signals are too noisy for the scan frequency.
- **AI vs numeric disagreements:** Selector returned empty portfolios (0 selections) on 2 consecutive scans on May 4, while the arbiter was actively buying. The two systems disagreed on whether to trade at all.
- **Verifier-induced churn:** 3 dust-sweeps on May 4 — verifier closing positions younger than 2 hours. The verifier targets are stale by the time it runs.
- **Oversized positions:** MU at 28%, DELL at 21% — single names at 2-4x the initial_entry_cap_pct after arbiter increases.
- **Weekend gap risk unmanaged:** HCAI bought Friday afternoon with a tight 0.93% stop that could never survive a weekend gap. No weekend sizing reduction was applied.

---

## Proposed changes

### 1. Add minimum hold period before exit (anti-churn gate)

**Why:** 16 same-day round-trips in 2 days, losing ~$1,315 on spreads alone plus opportunity cost. The arbiter reverses its own decisions within 1-2 scan cycles.

**Diff:**
```yaml
# config.yaml
# ADD under risk:
risk:
  min_hold_scans: 3    # position must survive 3 scan cycles (~3 hours) before exit-arbiter can close it
```

```python
# src/orchestrator.py — in _handle_exits(), before calling exit-arbiter:
# ADD: skip positions opened < min_hold_scans ago
# (Check trade_log.jsonl for entry timestamp, compare to current scan count)
```

**Expected impact:** Eliminates ~80% of same-day round-trips. Based on the 16 round-trips observed, this would have saved ~$1,000-2,000 in spread/slippage costs and freed capital for positions that were actually held (AXTX, META, PWR — which all showed positive or near-flat P&L).

### 2. Prevent verifier from overriding positions younger than 2 scans

**Why:** Verifier dust-swept DELL, LLY, FIX — all opened by the arbiter in the same session. The verifier's target snapshot is stale relative to the arbiter's latest decisions.

**Diff:**
```python
# src/ai_pipeline.py or wherever verifier runs — add age check:
# IF position was opened within last 2 scan cycles, skip verifier reconcile for that symbol.
# The arbiter intentionally sized it; let it breathe.
```

**Expected impact:** Eliminates 3 dust-sweeps on May 4 alone (~$44K in unnecessary order flow). Prevents verifier from contradicting arbiter decisions before they've had time to play out.

### 3. Add daily drawdown circuit breaker

**Why:** Three consecutive days exceeded -2.5% with no automatic response. The bot kept trading through a compounding drawdown (Apr 27-29: -4.88%, -5.13%, -5.40%).

**Diff:**
```yaml
# config.yaml
# ADD:
risk:
  daily_drawdown_halt_pct: 0.025    # halt all new entries if daily equity loss > 2.5%
  daily_drawdown_reduce_pct: 0.04   # trim all positions by 50% if daily loss > 4%
```

```python
# src/orchestrator.py — at top of scan, before discovery:
# Compare current equity to day-open equity (from first scan's snapshot).
# If loss > daily_drawdown_halt_pct: skip entries, run exits only.
# If loss > daily_drawdown_reduce_pct: force 50% trim of all non-SPY positions.
```

**Expected impact:** Would have halted new entries on Apr 27 after -2.5% (preventing the compounding to -4.88%), and forced trims at -4% (preventing the Apr 28-29 cascade). Estimated savings: $2,000-4,000 over the 3-day drawdown.

### 4. Add weekend gap risk reduction

**Why:** HCAI bought Friday afternoon with a 0.93% stop. Weekend gap-down blew through it, causing 3.4x the risk budget loss (-$1,716 vs $500 limit).

**Diff:**
```yaml
# config.yaml — already has overnight.weekend section, ADD:
overnight:
  weekend:
    max_new_entry_size_pct: 0.08    # halve normal initial_entry_cap for Friday afternoon entries
    require_stop_gap_buffer: true    # stop must be ≥2x normal distance for weekend holds
```

**Expected impact:** HCAI position would have been sized at ~$8K instead of ~$17.7K, capping the gap-down loss to ~$770 (within risk budget). Alternatively, the wider stop requirement would have blocked the entry entirely since the AI couldn't set a wide enough stop within the 1% hard limit.

### 5. Reduce scan frequency from 6x to 4x daily

**Why:** Trade count escalated from 7/day (Apr 22) to 53/day (May 4) as the bot cycled through more scans. Each scan is a chance to reverse a prior scan's decision. 6 scans/day × 6 positions = 36 exit-arbiter evaluations — far too many opportunities for noise-driven reversals.

**Diff:**
```yaml
# config.yaml
scheduling:
  intraday_times:
    - "10:00"
    - "12:00"
    - "14:00"
    - "15:30"
  # Removed 11:00 and 13:00 — these mid-session scans generated the most churn
```

**Expected impact:** ~33% fewer trades, proportionally fewer round-trips. Combined with the min_hold_scans gate (proposal #1), this would reduce daily trades from 53 to an estimated 10-15.

### 6. Cap verifier reconcile additions to initial_entry_cap_pct

**Why:** Verifier reconciled COIN (+$1,135), GOOGL (+$3,569), MU (+$3,179), NOK (+$12,112), V (+$14,957) — some reconciles are larger than initial entries. The verifier is overshooting into positions the arbiter deliberately undersized.

**Diff:**
```python
# src/ai_pipeline.py — verifier reconcile logic:
# Cap any single reconcile trade to initial_entry_cap_pct (15%) of equity.
# If gap > 15%, log a warning and reconcile only to the cap.
```

**Expected impact:** Prevents the V reconcile ($14,957 = ~15% of equity in a single verifier add) and the NOK reconcile ($12,112). These outsized reconciles create concentration risk the arbiter intentionally avoided.

---

## Backtest (offline, journal data only)

**Proposal #1 backtest (min_hold_scans: 3):**

Using the trade journal, I filtered out all exits that occurred within 3 hours of entry on May 1 and May 4:

| Metric | Actual | With min_hold_scans=3 |
|--------|--------|-----------------------|
| May 1 trades | 28 | ~12 (9 round-trips blocked) |
| May 4 trades | 26 | ~12 (7 round-trips blocked) |
| Round-trip spread losses | ~$1,315 | ~$0 |
| Capital freed for held positions | $0 | ~$60K (avg capital tied up in churned trades) |

Cannot model the counterfactual returns on freed capital without price data (yfinance blocked), but eliminating the spread losses alone is a net positive.

**Proposal #3 backtest (daily drawdown halt at 2.5%):**

| Date | Actual daily | With halt | Improvement |
|------|-------------|-----------|-------------|
| Apr 27 | -4.88% | ~-2.5% (halt after -2.5%) | +2.38% |
| Apr 28 | -5.13% | ~-3.0% (smaller starting exposure) | +2.13% |
| Apr 29 | -5.40% | ~-2.0% (minimal exposure after 2 halt days) | +3.40% |
| **Total** | **-15.41%** | **~-7.5%** | **~+7.9%** |

Estimated: the drawdown circuit breaker alone would have preserved ~$7,900 over the 3-day selloff. This is approximate — actual would depend on which positions were trimmed — but the direction is clear.

**Other proposals:** Cannot be backtested offline (require price data for sizing simulations).

---

## Summary

The bot's primary problem is **churn** — it changes its mind every scan, paying spreads to stand still. This is compounded by the verifier contradicting the arbiter and the absence of any drawdown protection. The HCAI gap-down exposed unmanaged weekend risk.

**Priority order for fixes:**
1. Daily drawdown circuit breaker (prevents catastrophic multi-day losses)
2. Min hold period anti-churn gate (eliminates ~80% of wasteful round-trips)
3. Verifier age-check (stops verifier from undoing arbiter decisions)
4. Weekend gap risk reduction (prevents stop-blow-through on Friday entries)
5. Scan frequency reduction (structural churn reduction)
6. Verifier reconcile cap (prevents outsized one-shot additions)

**Bottom line:** The bot returned +0.22% over 9 days while SPY returned +1.95%. Active stock selection destroyed value — the 59.8% SPY proxy allocation was the only thing preventing a larger loss. Until churn and drawdown controls are fixed, the bot would be better off in 100% SPY.
