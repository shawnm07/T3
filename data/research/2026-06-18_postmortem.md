# Post-Mortem 2026-06-18

## Data Availability

| Source | Status |
|--------|--------|
| EOD snapshot (2026-06-18) | **MISSING** — no data for today |
| Latest EOD available | 2026-05-04 (45 days stale) |
| Scan files (2026-06-18) | **MISSING** |
| Latest scans available | 2026-05-04 (6 scans + 1 preclose) |
| Trade log (trades.jsonl) | 204 entries through 2026-05-04 |
| Decision log (decisions.jsonl) | 1,556 entries through 2026-05-04 |
| Config baseline | Read successfully |

> **CRITICAL:** The bot has not produced any data since 2026-05-04 — a 45-day gap.
> This post-mortem covers the **most recent trading day with data: 2026-05-04**.
> The data gap itself is the #1 finding requiring investigation.

---

## Performance Summary

### Rolling Benchmark (9 trading days: 2026-04-22 → 2026-05-04)

| Date | Equity | Daily | vs SPY | SPY | Positions | Trades |
|------|--------|-------|--------|-----|-----------|--------|
| 04-22 | $99,627 | +0.00% | -1.01% | +1.01% | 7 | 7 |
| 04-23 | $101,208 | +1.56% | +1.95% | -0.39% | 10 | 9 |
| 04-24 | $99,343 | -0.81% | -1.59% | +0.77% | 12 | 19 |
| 04-27 | $96,448 | -4.88% | -5.05% | +0.17% | 8 | 24 |
| 04-28 | $96,867 | -5.13% | -4.65% | -0.49% | 4 | 21 |
| 04-29 | $93,999 | -5.40% | -5.39% | -0.01% | 5 | 10 |
| 04-30 | $95,786 | -2.67% | -3.63% | +0.96% | 3 | 23 |
| 05-01 | $101,101 | +1.82% | +1.53% | +0.29% | 4 | 38 |
| 05-04 | $99,850 | -1.80% | -1.43% | -0.36% | 4 | 53 |

| Window | Portfolio | SPY | Alpha |
|--------|-----------|-----|-------|
| 5-day (04-28 → 05-04) | -12.66% | +0.38% | **-13.04%** |
| 9-day (04-22 → 05-04) | -16.31% | +1.95% | **-18.26%** |
| Equity change | +$222 | — | — |
| Days underperforming SPY | **7 of 9** | — | — |
| Avg trades/day | **22.7** | — | — |

### Risk Budget Check (2026-05-04)

| Constraint | Limit | Actual | Status |
|------------|-------|--------|--------|
| Daily drawdown | < 2.5% | 1.80% | OK |
| Cash reserve | >= 5% | 5.0% | BORDERLINE |
| Max initial position | <= 15% | 14.6% (AXTX) | OK |
| Max positions | 6 | 4 | OK |
| ai_data_center theme | max 50% | 11.1% | OK (was 89.8% on 04-27) |

---

## Positions at Close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | Current | PnL % | PnL $ | Mkt Value | % of Equity |
|--------|------|-----|-----------|---------|-------|-------|-----------|-------------|
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42 | $59,696 | 59.8% |
| AXTX | LONG | 313.00 | $46.41 | $46.61 | +0.43% | +$63 | $14,589 | 14.6% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | -$16 | $11,130 | 11.1% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$20 | $9,448 | 9.5% |

> Portfolio is 59.8% SPY (cash proxy) + 35.2% active + 5.0% cash. Effectively only 35% active exposure.

---

## Trades on 2026-05-04 (53 orders)

### Exits (5 positions closed)

| Time | Symbol | Qty | Price | Reason | Verdict |
|------|--------|-----|-------|--------|---------|
| 14:51 | HCAI | 1,492 | $10.69 | Exit-arbiter (conf=0.72): -8.78%, lost VWAP | **GOOD** — cut loser early |
| 16:04 | AMZN | 65.30 | $270.65 | Fading momentum, below VWAP | QUESTIONABLE |
| 16:04 | GEV | 14.57 | $1,071.49 | Weak momentum, bearish EMA | OK |
| 16:04 | UNH | 17.27 | $368.25 | Fading volume, LLY stronger pick | OK |
| 17:04 | MU | 23.01 | $580.81 | Weak momentum, peer WDC scored higher | **CHURN** — bought+sold same day |

### Entries / Increases (10 orders)

| Time | Symbol | Action | Qty | Price | Target % | Verdict |
|------|--------|--------|-----|-------|----------|---------|
| 16:04 | LLY | BUY | 9.49 | $963.38 | 9.1% | OK |
| 16:04 | MU | INCREASE | 25.00 | $580.42 | 28.0% | **BAD** — sold 1hr later |
| 16:04 | NOK | BUY | 367.24 | $13.33 | 4.9% | NOT IN EOD |
| 16:04 | SNDK | BUY | 10.10 | $1,246.97 | 12.6% | NOT IN EOD |
| 17:04 | DELL | BUY | 57.39 | $210.52 | 12.1% | NOT IN EOD |
| 17:04 | FIX | BUY | 6.30 | $1,896.50 | 11.9% | NOT IN EOD |
| 17:04 | GOOGL | BUY | 28.68 | $383.51 | 11.0% | NOT IN EOD |
| 17:04 | LLY | INCREASE | 3.51 | $962.27 | 12.5% | OK |
| 17:04 | WDC | BUY | 24.51 | $445.36 | 10.9% | CHURN — replaced MU |
| 17:04 | COIN | BUY | 5.10 | $203.90 | 14.8% | Verifier reconcile |

### Same-Day Churn on 2026-05-04

| Symbol | Bought | Sold | Total Churn |
|--------|--------|------|-------------|
| MU | $14,510 | $13,362 | $27,873 |
| GOOGL | $14,567 | $14,530 | $29,097 |
| FIX | $18,992 | $19,028 | $38,020 |
| DELL | $12,083 | $12,107 | $24,190 |
| LLY | $12,520 | $12,528 | $25,048 |
| WDC | $10,915 | $10,786 | $21,701 |
| **Total** | | | **$180,580** |

> **$180K in round-trip churn in a single day on a $100K account = 1.8x turnover.**
> The 16:04 scan selected {LLY, MU, NOK, SNDK}; the 17:04 scan replaced with {DELL, FIX, GOOGL, WDC, LLY}. Only LLY survived both scans.

---

## Cross-Trade Pattern Analysis

### 1. Extreme Churn — Selector Instability
- 204 trades in 9 days = 22.7 trades/day on a 4-6 position portfolio.
- On 2026-05-04 alone: 53 trades. The selector completely reshuffled between every hourly scan.
- MU was INCREASED to 28% target at 16:04 then EXIT'd at 17:04 — a $28K round-trip in 60 minutes.
- Root cause: the portfolio-selector has no penalty for rotating out a position it just entered. Each scan re-evaluates from scratch with `no incumbent bias`, but this means positions have zero stickiness.

### 2. ai_data_center Theme Over-Concentration (04-23 → 04-27)
- Theme concentration hit **89.8%** on 04-27 (AMD, AVGO, DELL, FIX, GEV, MU, VRT — 7 positions, all ai_data_center).
- Config says `max_theme_weight_pct: 0.50` and `max_per_theme: 3`, but the sector_guard clearly failed.
- This created massive correlated drawdown: portfolio dropped -4.88% on 04-27 while SPY was +0.17%.
- The diversification config was likely added AFTER this failure (comment in config.yaml references "2026-04-28 failure mode").

### 3. MU Catastrophic Loss (04-29)
- MU showed `pnl_pct: -0.8011` on 04-29 (avg_entry=$517.23, current=$102.89).
- This is an **80% loss** on what was a 27% position two days earlier.
- Likely cause: MU underwent a stock split or corporate action that the bot's price source (alpaca_stock_fallback) didn't adjust for. The avg_entry was not rebased.
- The `hard_stop_loss_pct: 0.01` (1% stop) should have triggered long before an 80% loss. Either the stop wasn't placed, or the price gapped through it.
- **This single event likely accounts for ~$4K of the total drawdown.**

### 4. SPY Cash-Proxy Dominance
- SPY (cash proxy) ranged from 0% (04-22) to 77.6% (04-30) of equity.
- On 05-04: 59.8% SPY = the bot is effectively a 60/40 SPY/active fund.
- When the bot underperforms SPY by -1.43% with only 35% active exposure, the active portion is losing ~4% vs benchmark per day.
- The cash proxy is working as intended (parking idle capital), but the active selections are destroying alpha.

### 5. Position Count Instability
- Positions swung from 3 to 12 in the 9-day window.
- 04-22: 7 positions → 04-23: 10 → 04-24: 12 → 04-27: 8 → 04-28: 4.
- The selector is not just rotating WHICH positions, but wildly varying HOW MANY.

### 6. No Evidence of Winner-Trimming
- With 7/9 days negative, there were few winners to trim.
- The one bright spot (SNDK on 05-01: +4.05%) was new that day and gone by 05-04's EOD.
- The bot rotates out of winners before they can compound: SNDK had $27.7K market value on 05-01, not held by 05-04.

### 7. AI vs Numeric Disagreements
- Cannot fully assess without today's decision log entries (May 4 decisions not found in journal).
- However, the pattern of 10 new entries + 5 exits in a single day suggests the AI arbiter is making large conviction swings between scans.
- The `ai.weight: 0.6` means AI overrides numeric 60% of the time — if AI is unstable scan-to-scan, this amplifies churn.

---

## Proposed Changes

### Change 1: Add Minimum Hold Period for New Entries

**Why:** The bot bought MU at 16:04 and sold at 17:04. No legitimate swing strategy enters and exits within 60 minutes. The selector treats each scan as if the portfolio started from zero.

**Diff:**
```yaml
# config.yaml — NEW KEY under selector:
selector:
  min_hold_scans: 3  # position must survive 3 consecutive scans before eligible for exit
```
```python
# src/orchestrator.py — in _handle_exits() or selector logic:
# Skip exit evaluation for positions entered < min_hold_scans ago
# (except hard_stop_loss_pct breach, which always fires)
```

**Expected impact:** Eliminates same-day churn. Based on 05-04 data, would have prevented ~$180K in round-trip trades (saving ~$90-180 in spread/slippage per day at 1-2bp).

### Change 2: Enforce Sector Guard BEFORE AI Selector, Not Just Post-AI

**Why:** On 04-27, the portfolio reached 89.8% ai_data_center concentration despite `max_theme_weight_pct: 0.50`. The sector_guard runs post-AI as a veto but clearly wasn't enforced during portfolio construction.

**Diff:**
```yaml
# config.yaml — already correct (max_theme_weight_pct: 0.50)
# The fix is in code:
```
```python
# src/ai_pipeline.py — in portfolio-selector prompt or pre-filter:
# Add theme concentration as a HARD CONSTRAINT in the selector prompt,
# not just a post-hoc veto. Include current theme weights in the pool
# metadata sent to the AI.
```

**Expected impact:** Would have capped ai_data_center to 3 positions / 50% weight on 04-23 through 04-27. Rough estimate: if the other 40% had been in uncorrelated positions, the 04-27 drawdown (-4.88%) would have been ~-2.5% instead.

### Change 3: Add Position Stickiness Penalty to Selector

**Why:** The selector's "no incumbent bias" design is correct in principle but catastrophic in practice. Each scan re-ranks from scratch, causing daily portfolio revolution. A small stickiness score for held positions would dampen turnover without creating permanent incumbency.

**Diff:**
```yaml
# config.yaml — NEW KEY under selector:
selector:
  incumbent_stickiness_score: 8  # held positions get +8 to opportunity score
  stickiness_decay_scans: 6      # decays linearly over 6 scans to 0
```

**Expected impact:** Based on 9-day data with 204 trades: would reduce trade count by ~40-60% (from 22.7 to ~10-12/day). Lower turnover = lower slippage + more time for winners to compound.

### Change 4: Validate Price Continuity Before Sizing

**Why:** MU showed an 80% overnight loss (04-28: $510 → 04-29: $103). This is almost certainly a data error (stock split, corporate action, or bad price feed). The 1% hard stop should have prevented this, but the gap was instantaneous.

**Diff:**
```python
# src/technicals.py or src/risk.py — add price continuity check:
# If |current_price / prev_close - 1| > 0.20, flag as PRICE_ANOMALY
# and skip all trading for that symbol until manually reviewed.
# Log to Telegram for human verification.
```

**Expected impact:** Would have prevented the MU $3,952 loss. Catches stock splits, bad data feeds, and corporate actions that the bot cannot price correctly.

### Change 5: Reduce Scan Frequency From 6x to 3x Daily

**Why:** 6 hourly scans with a fully re-ranking selector produces portfolio revolution. Each scan makes independent decisions, leading to 53 trades/day. Reducing to 3x (10:00, 13:00, 15:00) gives positions 2+ hours to develop before re-evaluation.

**Diff:**
```yaml
# config.yaml
scheduling:
  intraday_times:
    - "10:00"
    - "13:00"
    - "15:00"
  # was: ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]
```

**Expected impact:** ~50% fewer trades mechanically. Combined with Change 1 (min hold), would reduce daily trades from 22.7 to ~5-8. Cannot backtest offline (no intraday price data in repo).

### Change 6: Investigate and Fix 45-Day Data Gap

**Why:** No data since 2026-05-04. The bot may be crashed, the cron/scheduler may be dead, API keys may have expired, or the Alpaca paper account may be suspended. A bot that isn't running can't beat SPY.

**Diff:** Not a config/code change — operational investigation needed:
- Check if `scan_and_trade.py` cron is still active
- Check Alpaca API key validity
- Check Alpha Vantage API key quota
- Check for crash logs / error state

**Expected impact:** If the bot has been down 45 days with positions still open, unrealized P&L is unknown. This is the highest-priority item.

---

## Backtest: Position Stickiness (Change 3) — Offline Simulation

Using the 9-day journal data, simulating what would have happened if positions required 3 scans to be eligible for exit:

- **Trades prevented:** MU exit on 05-04 (entered same day), GOOGL exit on 05-04 (entered same day), FIX exit on 05-04 (entered same day), DELL exit on 05-04 (entered same day), WDC exit on 05-04 (entered same day) = 5 exits prevented
- **Estimated spread saved:** ~$50-100 per round-trip × 5 = $250-500 on 05-04 alone
- **Risk:** Stickiness could trap positions in drawdowns. Mitigated by hard stop always firing.
- **Cannot fully backtest:** No intraday price data in repo to determine if held positions would have recovered.

---

## Summary

| Finding | Severity | Proposed Fix |
|---------|----------|-------------|
| 45-day data gap — bot may be dead | **CRITICAL** | Investigate immediately (Change 6) |
| Extreme churn: 22.7 trades/day, $180K round-trips | **HIGH** | Min hold period (Change 1) + stickiness (Change 3) |
| ai_data_center 89.8% concentration on 04-27 | **HIGH** | Pre-AI sector guard (Change 2) |
| MU -80% loss from price anomaly | **HIGH** | Price continuity check (Change 4) |
| Selector completely reshuffles every scan | **MEDIUM** | Reduce scan freq (Change 5) + stickiness (Change 3) |
| 7/9 days underperforming SPY | **MEDIUM** | All changes above, plus fundamental review of AI prompts |
| -18.26% alpha over 9 days | — | Systemic — all changes required |

**Bottom line:** The bot is not beating SPY. It's a high-frequency churn machine on a swing-trading chassis. The selector's scan-to-scan instability is the primary alpha destroyer. Fix the data gap first, then implement Changes 1-5 before resuming trading.
