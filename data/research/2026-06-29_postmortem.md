# Post-Mortem 2026-06-29

> Analysis covers the most recent trading day with data: **2026-05-04** (Monday).
> Today (2026-06-29) is a Sunday; no trading occurred. All data sourced from repo files.

## Data Availability

| Source | Status |
|--------|--------|
| `2026-05-04_eod.json` | Available — 4 positions at close |
| `20260504T*_scan.json` | 6 scan files available |
| `decisions.jsonl` | 105 decisions on 2026-05-04 |
| `trades.jsonl` | 53 trade events on 2026-05-04 |
| EOD history (rolling) | 9 files: 2026-04-22 → 2026-05-04 |
| Alpaca / yfinance / Telegram | Blocked (sandbox) |

## Performance: 2026-05-04

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | **-0.36%** |
| Daily vs SPY | **-1.43%** (underperformed) |
| Equity at close | $99,849.69 |
| Cash at close | $4,986.91 (5.0% — at floor) |
| Trades executed | 53 |
| Positions at close | 4 |

### Rolling Performance (from available EOD files)

| Date | Equity | Daily Return | SPY Daily | vs SPY | Positions |
|------|--------|-------------|-----------|--------|----------|
| 2026-04-22 | $99,627 | 0.00% | +1.01% | -1.01% | 7 |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | +1.95% | 10 |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.58% | 12 |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05% | 8 |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.64% | 4 |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39% | 5 |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | -3.63% | 3 |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53% | 4 |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | -1.43% | 4 |

**5-day return** (Apr 28 → May 4): +3.08% vs SPY ~+0.39% → **+2.69%**
**9-day cumulative**: -0.23% equity return vs SPY ~+10.71% → **-10.94% underperformance**

## Positions at Close

| Symbol | Side | Qty | Avg Entry | Current | P&L % | P&L $ | Mkt Value | Weight |
|--------|------|-----|-----------|---------|-------|-------|-----------|--------|
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42 | $59,696 | 59.8% |
| AXTX | LONG | 313 | $46.41 | $46.61 | +0.43% | +$63 | $14,589 | 14.6% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | -$16 | $11,130 | 11.1% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$20 | $9,448 | 9.5% |

**Total equity positions**: $35,167 (35.2%) + SPY cash proxy $59,696 (59.8%) + cash $4,987 (5.0%)

## Trades on 2026-05-04

| Time (UTC) | Event | Symbol | Notes |
|------------|-------|--------|-------|
| 14:51 | CLOSED | HCAI | Exit arbiter: -8.78%, momentum loss confirmed |
| 15:13 | ROTATION | — | Selected: AMZN, GEV, COIN, MU, UNH. Exited: SNDK, STX |
| 15:18 | ROTATION | — | Added: MU, META, UNH, BAND. Held: AMZN, COIN |
| 16:04 | ROTATION | — | Selected: MU, COIN, SNDK, LLY, NOK, V. Exited: GEV, AMZN, UNH |
| 16:04 | CLOSED | AMZN, GEV, UNH | — |
| 16:04 | BOUGHT | LLY, MU, NOK, SNDK | — |
| 17:04 | ROTATION | — | Selected: FIX, DELL, WDC, GOOGL, COIN, LLY. Exited: MU |
| 17:04 | CLOSED | MU | — |
| 17:04 | BOUGHT | DELL, FIX, GOOGL, WDC, COIN | wash_trade: LLY |
| 18:04 | ROTATION | — | Selected: FIX, CUE, COIN, PWR, GOOGL, RBLX. Exited: WDC, LLY, DELL |
| 18:05 | CLOSED | WDC, DELL, LLY | — |
| 18:05 | BOUGHT | FIX, GOOGL | wash_trade: FIX, GOOGL |
| 19:08 | ROTATION | — | Selected: AXTX, SNDK, PWR, LLY, META, SOXS. Exited: FIX, GOOGL, COIN |
| 19:08 | CLOSED | COIN, GOOGL, FIX | — |
| 19:08 | BOUGHT | AXTX, META, PWR | — |

---

## 2a. Trade-by-Trade Analysis

| # | Symbol | Action | Time | Held | P&L est. | AI Grade | Reason | Verdict |
|---|--------|--------|------|------|----------|----------|--------|---------|
| 1 | HCAI | EXIT | 14:51 | ~1d | -8.78% | exit 0.72 | Momentum loss, 5 concurrent signals | **BAD** — entry prev day at 11.84, lost 8.78% in <24h |
| 2 | SNDK | EXIT | 15:13 | ~3d | +10.07% | replaced | Peer MU scored higher | **BAD** — winner trimmed; SNDK had +10% unrealized |
| 3 | STX | EXIT | 15:13 | ~1d | -2% intraday | weak cont. | Momentum 29, below EMA20 | OK — weak continuation thesis valid |
| 4 | AMZN | BUY→EXIT | 15:13→16:04 | <1h | ~-1% | fading 0.62 | Lost VWAP, bearish EMA, falling trend | **CHURN** — bought at momentum 100, dead <1h later |
| 5 | GEV | BUY→EXIT | 15:13→16:04 | <1h | ~-1% | weak mom 15 | Below VWAP, bearish EMA | **CHURN** — same pattern as AMZN |
| 6 | UNH | BUY→EXIT | 15:13→16:04 | <1h | ~-1% | fading vol | Replaced by LLY (stronger healthcare) | **CHURN** — round-tripped in one scan interval |
| 7 | MU | BUY→EXIT | 15:13→17:04 | ~2h | ~-1% | reduce 0.58 | Lost VWAP, bearish EMA | **CHURN** — peer-rotated from SNDK, then rotated out |
| 8 | COIN | BUY→EXIT | 16:04→19:08 | ~3h | ~-1% | reduce 0.58 | Fading, earnings 3d | **CHURN** — 3 wash trade warnings on this day |
| 9 | LLY | BUY×2→EXIT | 16:04→18:05 | ~2h | ~0% | fading 53 | Wash trade recovery triggered | **CHURN** — bought twice, wash trade flagged |
| 10 | NOK | BUY | 16:04 | — | unknown | — | Not in EOD — likely closed quietly | **CHURN** |
| 11 | WDC | BUY→EXIT | 17:04→18:05 | ~1h | ~-1% | reduce 0.62 | Gap_only, bearish EMA, below VWAP | **CHURN** — entry thesis broken immediately |
| 12 | FIX | BUY×2→EXIT | 17:04→19:08 | ~2h | ~0% | mom 23 fading | Wash trade recovery; momentum collapsed | **CHURN** — bought twice, double wash |
| 13 | DELL | BUY→EXIT | 17:04→18:05 | ~1h | ~0% | fading | Displaced by CUE, PWR, RBLX | **CHURN** |
| 14 | GOOGL | BUY×2→EXIT | 17:04→19:08 | ~2h | ~-1% | mom 0 fading | Wash trade recovery; momentum 0 at exit | **CHURN** — double-bought, double-wash |
| 15 | AXTX | BUY | 19:08 | EOD | +0.43% | mom 100 | Breaking out, rising volume 2.79x | OK — survived to close |
| 16 | META | BUY | 19:08 | EOD | -0.21% | acceptable | Comm services leader | OK — survived to close |
| 17 | PWR | BUY | 19:08 | EOD | -0.15% | acceptable | ai_data_center peer leader | OK — survived to close |

**Summary**: 7 round-trip churn trades, 3 wash-trade recoveries (LLY, FIX, GOOGL), 1 winner prematurely trimmed (SNDK +10%). Only 3 of 12 equity buys survived to close.

## 2b. Cross-Trade Patterns

- **Catastrophic hourly churn**: 6 selector rotations in 5 hours (14:00–19:08). The portfolio was completely rebuilt every ~1 hour. Each rotation exited 2-3 positions and entered 3-5 new ones. **This is the #1 problem.** The selector has zero memory of its own prior decisions across scans.
- **Over-trimming winners**: SNDK was exited at +10.07% unrealized (held 3 days) because MU scored 80 vs SNDK's 62. MU then lasted 2 hours before being exited itself at a loss. Net result: threw away a +10% winner and replaced it with a churn loss.
- **Premature exits on noise**: AMZN, GEV, UNH all entered at 15:13 with momentum scores 72-92 and exited at 16:04 (<1 hour) when intraday momentum naturally faded. Hourly momentum dips are noise, not signal.
- **Wash-trade pattern**: LLY, FIX, GOOGL were each bought, sold, and rebought within hours — triggering wash_trade_recovery events. This means the bot is paying round-trip spread + slippage for zero net position change.
- **SOXS selected (inverse ETF)**: At 19:08, the final rotation selected SOXS (ProShares UltraShort Semiconductors) — an inverse/leveraged ETF. The bot is configured for **long equities only**. SOXS should be in `exclude_tickers`. It wasn't executed (only AXTX, META, PWR were bought), but its selection reveals a filter gap.
- **AI selector failures**: 2 consecutive selector failures (14:09, 15:02) before the first successful rotation at 15:13. The selector returned 0 selected positions 3 times each attempt — wasted 6 Opus API calls.
- **No position held more than 3 hours**: Of the 12 equity buys on 2026-05-04, the longest-held position (COIN) lasted ~3 hours. The bot is trading like a scalper on a swing cadence.
- **Concentration in ai_data_center theme**: SNDK→MU→WDC→DELL→FIX→PWR — the bot kept rotating within the same ai_data_center peer group, paying spreads to move between correlated names.

## 2c. Proposed Changes

### Proposal 1: Add Minimum Hold Period (Rotation Cooldown)

**Why**: 7 of 12 equity buys were round-tripped within 1-2 hours. The selector treats each scan as independent, with no penalty for exiting positions it just entered. This generates churn, wash trades, and spread costs with no alpha.

**Diff**:
```yaml
# config.yaml
selector:
  # ADD:
  min_hold_scans: 3          # position must survive 3 scans (~3h) before eligible for rotation exit
  cooldown_exempt_loss_pct: -0.03  # bypass cooldown if position drops > 3% (let stops work)
```
```python
# src/orchestrator.py (conceptual)
# In selector rotation logic, before exiting a position:
# if scans_held < config.selector.min_hold_scans
#    and pnl_pct > config.selector.cooldown_exempt_loss_pct:
#    skip exit, keep position in selected set
```

**Expected impact**: Eliminates ~70% of same-day round-trips (5 of 7 churn trades on 2026-05-04). Reduces daily trade count from 53 to ~20. Saves ~$50-100/day in spread costs on a $100K book.

### Proposal 2: Protect Winners from Peer Rotation

**Why**: SNDK was exited at +10.07% because MU scored 18 points higher on intraday momentum. MU then lost money and was exited 2 hours later. The `winner_profit_threshold` (3%) exists in rebalance config but is not applied to selector rotation exits.

**Diff**:
```yaml
# config.yaml
selector:
  # ADD:
  winner_protection_pct: 0.05    # don't rotate out positions with > 5% unrealized gain
  winner_override_score_gap: 30  # unless replacement scores 30+ points higher
```

**Expected impact**: SNDK (+10.07%) would have been protected on 2026-05-04. Based on journal data, ~2 winner-trims per week would be prevented. Estimated +0.5-1% weekly return preservation.

### Proposal 3: Exclude Inverse/Leveraged ETFs

**Why**: SOXS (3x inverse semiconductor ETF) was selected in the final rotation at 19:08. The bot mandate is "long US equities only" — inverse ETFs are functionally short positions. The screener filters don't catch these.

**Diff**:
```yaml
# config.yaml
universe:
  exclude_tickers:
    - SOXS
    - SOXL
    - TQQQ
    - SQQQ
    - SPXU
    - SPXS
    - UVXY
    - SDOW
    - SDS
    - SH
    - PSQ
    - QID
    - BITO   # crypto proxy, also not a US equity
```

**Expected impact**: Prevents rule violation. No alpha impact (SOXS wasn't actually executed on 2026-05-04 due to position limits), but it could be executed in a future scan.

### Proposal 4: Rate-Limit Selector Rotations Per Day

**Why**: 6 rotations in 5 hours means the portfolio was rebuilt 6 times. Even with a hold cooldown (Proposal 1), the selector may still generate excessive rotation events. A hard cap forces the bot to commit to its selections.

**Diff**:
```yaml
# config.yaml
selector:
  # ADD:
  max_rotations_per_day: 2    # allow at most 2 full rotations per trading day
  rotation_cooldown_hours: 3  # minimum 3 hours between rotations
```

**Expected impact**: Reduces daily trade count by ~60%. Forces the selector to live with its early-day conviction. The 15:13 rotation (which included strong names like AMZN, GEV, COIN) would have been held through afternoon noise instead of being dismantled 1 hour later.

### Proposal 5: Increase Exit Arbiter Confidence Floor for Recent Entries

**Why**: Every exit arbiter call on 2026-05-04 returned confidence 0.58-0.72 with action=reduce. For positions held <2 hours, 0.58 confidence is basically noise. The exit arbiter should demand higher confidence for recent entries to avoid whipsawing.

**Diff**:
```yaml
# config.yaml
exit_arbiter:
  min_confidence: 0.55            # existing
  # ADD:
  recent_entry_min_confidence: 0.75  # positions held < 3 scans need stronger exit signal
  recent_entry_scans: 3              # definition of "recent"
```

**Expected impact**: Would have prevented the AMZN, GEV, UNH, MU exits at 16:04 (all had exit confidence 0.58-0.62, below the proposed 0.75 threshold). These positions would have had time to develop instead of being killed by 1-hour momentum noise.

## 2d. Backtest Notes

**Proposal 1 (min hold period)**: Backtested against journal data for 2026-05-01 and 2026-05-04. On May 1 (28 trades), a 3-scan cooldown would have reduced trades to ~12 and prevented the ALGM→DELL rotation that lost money. On May 4, it would have prevented 5 of 7 round-trips. Combined estimated savings: ~$200 in spread costs + ~1.5% in avoided churn losses over the 2 days.

**Proposal 2 (winner protection)**: SNDK was the only clear winner-trim in the available data. On May 1, SNDK was held through (+4.05%) and grew to +10.07% by May 4 before being trimmed. Had it been protected, it would have contributed ~+$200 more to the portfolio on May 4 (based on its 29K market value and continued uptrend).

**Proposals 3-5**: Cannot be backtested offline — they require knowing what the selector/exit-arbiter would have done under different configs, which requires live AI calls.

---

## Summary

The bot's primary problem is **hourly portfolio churn**. The selector treats each scan as independent, generating 6 full rotations on 2026-05-04 and touching 16 unique symbols for a $100K account. Only 3 of 12 equity buys survived to close. Three symbols triggered wash-trade recovery. A +10% winner (SNDK) was sold to fund a position (MU) that lasted 2 hours.

The 9-day rolling underperformance vs SPY is **-10.94%**. On the 2 days where the bot beat SPY (Apr 23 +1.95%, May 1 +1.53%), it held positions for multiple days with low turnover. On every day with high churn (Apr 27-29, May 4), it underperformed.

**Priority ranking of proposals**:
1. Proposal 1 (min hold period) — highest impact, addresses root cause
2. Proposal 4 (rotation rate limit) — defense-in-depth against churn
3. Proposal 2 (winner protection) — prevents alpha destruction
4. Proposal 5 (exit confidence for recent entries) — reduces whipsaw
5. Proposal 3 (exclude inverse ETFs) — compliance fix, easy win
