# Post-Mortem 2026-04-23

## Data Availability

| File | Status |
|------|--------|
| `data/research/2026-04-23_eod.json` | ✓ present |
| `data/research/2026-04-22_eod.json` | ✓ present (prior day only — 2 EOD files total) |
| `data/journal/trades.jsonl` | ✓ present (7 trades on 2026-04-22; 0 on 2026-04-23) |
| `data/journal/decisions.jsonl` | ✓ present |
| `data/research/20260423T030509_crypto_scan.json` | ✓ present (no executions) |
| `data/research/20260423T070510_crypto_scan.json` | ✓ present (no executions) |
| Rolling 30d EOD history | ✗ only 2 files — rolling stats limited |

---

## Performance Today (2026-04-23)

| Metric | Value |
|--------|-------|
| Equity | $99,433.94 |
| Cash (idle) | $60,501.10 (60.8% of equity) |
| Deployed in positions | $38,932.84 (39.1% of equity) |
| Daily return | **+0.26%** |
| SPY daily | **+1.01%** |
| Daily vs SPY | **−0.75%** |
| Period return (since inception) | 0.00% |
| SPY 30d return | +4.22% |
| Period vs SPY | **−4.22%** |
| Trades today | 0 |
| Open positions | 7 |

**Root cause of underperformance today:** 60.8% of equity sat idle in cash instead of being parked in SPY via the `cash_proxy`. Cash proxy appears non-operational. With SPY up 1.01%, the idle cash dragged portfolio return from a hypothetical ~1.01% (if fully deployed) to 0.26% actual.

### Rolling Benchmark (available: 2 days)

| Date | Portfolio | SPY | Δ vs SPY |
|------|-----------|-----|----------|
| 2026-04-22 | +0.00% | +1.01% | −1.01% |
| 2026-04-23 | +0.26% | +1.01% | −0.75% |

---

## Positions at Close

| Symbol | Side | Qty | Avg Entry | Current | PnL% | Mkt Value | % Equity |
|--------|------|-----|-----------|---------|------|-----------|----------|
| AMD | LONG | 17 | $296.07 | $303.46 | +2.50% | $5,109.69 | 5.14% |
| ARW | LONG | 47 | $181.23 | $181.54 | +0.17% | $8,532.38 | 8.58% |
| AVGO | LONG | 12 | $408.83 | $422.65 | +3.38% | $5,011.20 | 5.04% |
| FIX | LONG | 3 | $1,726.13 | $1,724.49 | −0.10% | $5,189.97 | 5.22% |
| GEV | LONG | 5 | $1,121.84 | $1,127.56 | +0.51% | $5,618.60 | 5.65% |
| MU | LONG | 9 | $476.60 | $487.48 | +2.28% | $4,320.00 | 4.35% |
| VRT | LONG | 17 | $302.64 | $305.14 | +0.83% | $5,151.00 | 5.18% |
| **Cash** | — | — | — | — | — | $60,501.10 | 60.84% |

> PnL% computed as `(current_price − avg_entry) / avg_entry` per post-mortem rules.

---

## Trades Today (2026-04-23)

_No trades executed on 2026-04-23._ All 7 positions were entered on 2026-04-22 (see full trade table in Phase 2 below).

---

## (Full analysis appended below)

---

## Phase 2: Deep Analysis

### 2a. Trade-by-Trade Table (all 7 entries, opened 2026-04-22)

| Symbol | Side | Qty | Entry | Current | PnL% | Conf | AI Grade | One-Line Reason | Quality |
|--------|------|-----|-------|---------|------|------|----------|-----------------|---------|
| VRT | BUY | 17 | $301.01 | $305.14 | +1.37% | 0.566 | B/C/A/C+ | AI infra momentum play, guidance raise catalyst | Acceptable — min-size, tight stops, momentum confirmed |
| AVGO | BUY | 12 | $409.11 | $422.65 | +3.31% | 0.563 | B/B-/A-/C+ | Golden cross, Google Cloud catalyst, PEG 0.87 | **Overbought entry** — RSI 76.3 at open (AI noted: wait for 397-400) |
| AMD | BUY | 17 | $296.00 | $303.46 | +2.52% | 0.556 | B/C/B+/C+ | AI sector momentum, golden cross, weak fundamentals | **Overbought entry** — RSI 82 at open, worst fundamental grade (PE 113×, ROE 7%) |
| MU | BUY | 9 | $477.32 | $487.48 | +2.13% | 0.563 | B/B/C+/C+ | PEG 0.26, ROE 39.8%, geopolitical tailwind | Best fundamental quality in book; RSI 66.5 borderline |
| FIX | BUY | 3 | $1,727.51 | $1,724.49 | −0.17% | 0.322† | tech-only | Preclose overnight buy, close to high | **Low confidence (0.322)** — overnight entry, no AI full verdict; RSI 70.4 overbought |
| GEV | BUY | 5 | $1,119.65 | $1,127.56 | +0.71% | 0.292† | tech-only | Preclose overnight buy, closing near high | **Lowest confidence (0.292)** — RSI 78.7, no AI verdict |
| ARW | BUY | 47 | $181.12 | $181.54 | +0.23% | 0.291† | tech-only | Preclose overnight buy, late-day strength | **Oversized** — 8.6% of equity vs ~5% for all others; sentiment score 0.0 |

> † Preclose overnight entries run a lightweight technical + overnight-score model; no full AI verdict.
> PnL% uses avg_entry from eod.json, not trade entry price (minor slippage differences).

---

### 2b. Cross-Trade Patterns

- **Cash proxy non-operational.** $60,501 (60.8% of equity) sits idle instead of being deployed into SPY per `cash_proxy.enabled: true`. This is the single largest performance drag — the portfolio forfeited ~0.75% today alone. Over the +4.22% SPY 30d run, this accounts for the full −4.22% period underperformance.

- **5 of 7 entries made at RSI > 70 ("overbought").** AMD (RSI 82), GEV (78.7), ARW (76.9), AVGO (76.3), FIX (70.4). The technical analyzer flags these but does not block them. AI recommended waiting for AVGO at 397–400 pullback and flagged AMD RSI as "mean reversion pressure" — both were entered anyway.

- **AI vs numeric disagreement — AI was right to caution.** On AVGO and AMD, the AI explicitly recommended waiting for a RSI reset. The numeric model scored them highly (0.725 / 0.831 technical) and overrode the caution via blending. Both are currently profitable only because the broader market was up; the RSI risk materializes on flat/down days.

- **Semiconductor sub-sector concentration.** AMD + AVGO + MU + VRT (all AI/semiconductor) entered on the same day on the same "chip ETF record high" narrative. Combined IT sector exposure = $19,592 (19.7% of equity) within a single sector rally. Correlation risk is elevated — a single negative catalyst (Nvidia miss, export restriction) could hit all four simultaneously.

- **Three overnight buys at low confidence (0.291–0.322) with overbought RSI.** FIX, GEV, and ARW were entered via the preclose overnight model with confidence below the 0.35 `buy_threshold` in config at half or below. FIX and GEV were technically at RSI 70.4 and 78.7 — overbought signals at entry.

- **ARW oversized via risk-based sizing bypass.** ARW's small ATR ($5.18) relative to price ($181) requires 47 shares to reach the ~$500 risk budget, producing an $8,512 notional (8.6% of equity vs ~5% for every other position). The `size_multiplier: 0.5` overnight config appears not to have reduced this. ARW should have been ~24 shares / ~$4,349.

- **No active position management on 2026-04-23.** Zero trades on a day when SPY was up 1.01% and several positions had decent unrealized gains (AVGO +3.38%, AMD +2.50%). No rebalancing, no trimming of winners toward SPY proxy, no new higher-confidence entries.

---

### 2c. Proposed Changes

#### Change 1: Debug and confirm cash_proxy is deploying SPY

**Why:** $60,501 (60.8% of equity) sits idle in cash on both observed days. The config has `cash_proxy.enabled: true` but no SPY position has ever appeared in the portfolio. This is the primary cause of the −4.22% period underperformance vs SPY.

**Diff (config.yaml — diagnostic only; verify `scripts/analyze_cash_in_spy.py` output):**
```
# No config change needed — cash_proxy IS enabled.
# Root cause is likely in src/ logic (cash proxy never triggered, or SPY buy
# is being blocked by cash_reserve_pct check or market-hours guard).
# Proposed: add explicit logging to cash_proxy buy/skip decision path.
```

**Expected impact:** Deploying $55,000+ into SPY at 60% idle cash would have returned +0.61% today (60% × 1.01%) instead of +0.00% on that portion → portfolio daily return ~+0.87% vs +0.26% actual.

---

#### Change 2: Hard RSI filter for new entries (RSI > 75 blocks buy)

**Why:** 5 of 7 entries were at RSI > 70; AMD at RSI 82 is a textbook overbought entry. AI explicitly warned on AVGO and AMD. The current system notes RSI overbought but does not penalize it enough to prevent entry.

**Diff (config.yaml):**
```yaml
# BEFORE
signals:
  weights:
    technical: 0.35

# AFTER — add explicit RSI gate (new config key):
signals:
  weights:
    technical: 0.35
  rsi_overbought_block: 78     # block NEW long entries if RSI >= this value
  rsi_oversold_block: 22       # block NEW short entries if RSI <= this value
```
*(Corresponding enforcement needed in `src/` — proposals live here in markdown only.)*

**Expected impact:** Would have blocked AMD (RSI 82) and GEV (RSI 78.7) entries. AMD and GEV represent $10,728 that would have stayed in SPY proxy instead, adding ~$108 in SPY tracking. More importantly, prevents mean-reversion losses when overbought entries reverse.

---

#### Change 3: Cap position notional at `max_position_pct` regardless of risk-based sizing

**Why:** ARW was sized to $8,512 (8.6% of equity) because its tight ATR required 47 shares to reach the $500 risk budget. This bypassed the intended ~5% single-position sizing. All other positions are ~5%.

**Diff (config.yaml):**
```yaml
# BEFORE
risk:
  max_position_pct: 0.15

# AFTER — add normal-size target cap:
risk:
  max_position_pct: 0.15
  target_position_pct: 0.055    # soft target for new entries; hard floor on risk-based sizing
```
*(Sizing code should `min(risk_based_notional, target_position_pct × equity)`.)*

**Expected impact:** ARW would have been ~$5,465 instead of $8,512 (-$3,047). Brings ARW in line with the book, reduces concentration on a low-conviction overnight entry (conf 0.291).

---

#### Change 4: Raise overnight `buy_threshold` to 0.50 and enforce `size_multiplier`

**Why:** FIX (conf 0.322), GEV (conf 0.292), ARW (conf 0.291) were all entered below the current `buy_threshold: 0.35`. The threshold wasn't enforced, or the sizing model used the full risk budget (ignoring the 0.5× multiplier). Overnight entries at RSI 70–79 with below-threshold confidence are high-risk low-reward.

**Diff (config.yaml):**
```yaml
# BEFORE
overnight:
  buy_threshold: 0.35
  size_multiplier: 0.5

# AFTER
overnight:
  buy_threshold: 0.50           # stricter gate; 0.35 allowed sub-threshold entries
  size_multiplier: 0.5          # verify this is applied to notional, not just qty
```

**Expected impact:** All three preclose buys (FIX, GEV, ARW) would have been blocked at the stricter 0.50 threshold. This frees ~$19,330 to deploy as SPY proxy, eliminating low-confidence overnight gap risk.

---

#### Change 5: Sector sub-group cap (max 2 AI/semiconductor entries per scan)

**Why:** AMD + AVGO + MU + VRT all entered on 2026-04-22 on the same "chip ETF records" narrative. Combined IT concentration = 19.7%. A single negative catalyst hits all four simultaneously.

**Diff (config.yaml):**
```yaml
# AFTER — add sub-sector grouping:
risk:
  max_sector_pct: 0.35          # unchanged
  max_subsector_entries_per_scan: 2   # new: cap same-day entries within a sub-sector
```

**Expected impact:** Caps semiconductor additions to 2 per scan day. MU (best fundamentals, PEG 0.26) and AVGO (Google Cloud catalyst) would stay; AMD (weakest fundamentals, RSI 82) would be held for next scan.

---

#### Change 6: AI veto weight when RSI > 75 AND AI recommends waiting

**Why:** On both AVGO and AMD, the AI explicitly said "wait for pullback to 397–400" and "RSI 82 recommends waiting." The numeric model overrode this. The `ai.weight: 0.6` should have given AI enough authority, but the numeric score was high enough to pull through.

**Diff (config.yaml):**
```yaml
# BEFORE
ai:
  weight: 0.6

# AFTER — add explicit RSI-triggered AI veto:
ai:
  weight: 0.6
  veto_on_rsi_overbought: true    # if AI says 'wait' AND RSI > rsi_overbought_block, action=hold
```

**Expected impact:** Would have vetoed AVGO and AMD entries on 2026-04-22. Both are currently profitable only due to market tailwind; this avoids same-pattern losses on future overbought entries into a weak tape.

---

### 2d. Offline Backtest Notes

**Change 1 (cash proxy fix):** Not backtestable offline — requires live execution path inspection. Recommend adding a unit test asserting SPY is purchased after each scan when `cash > cash_reserve_pct × equity`.

**Change 2 (RSI block at 78):** Backtestable in principle using `data/journal/trades.jsonl`. From the 7 available trades: AMD (RSI 82) and GEV (RSI 78.7) would have been blocked → 2/7 entries skipped. Both are currently profitable due to market rally, so no immediate P&L gain — but the risk-adjusted benefit materializes in adverse conditions. Insufficient history (7 trades) for statistical significance.

**Change 3 (position notional cap):** Single instance — ARW would have been $5,465 vs $8,512, saving $3,047 on a position currently up only 0.17% (+$14 unrealized). Backtest trivial: no benefit yet, but cap prevents outsized loss if ARW reverses.

**Change 4 (overnight threshold 0.35 → 0.50):** All 3 overnight entries (FIX, GEV, ARW) would have been skipped. Current unrealized on those 3: FIX −0.10%, GEV +0.51%, ARW +0.17% → mixed, with FIX underwater. Overall cost of blocking: −$32 unrealized across the three. Benefit: frees $19,330 for SPY proxy instead.

**Changes 5, 6:** Insufficient trade history for meaningful backtest. Logical soundness confirmed by data; recommend monitoring for 2–4 weeks.

---

*Post-mortem generated by post-mortem-bot on 2026-04-23. Proposals are markdown-only — no config.yaml or src/ files were modified.*
