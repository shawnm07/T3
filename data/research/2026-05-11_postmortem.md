# Post-Mortem 2026-05-11

## Data availability

| Source | Status |
|--------|--------|
| `2026-05-11_eod.json` | **MISSING** — no scan ran today (weekend gap or no data written) |
| `2026-05-04_eod.json` | Present — latest available EOD snapshot (Friday 2026-05-04) |
| `data/journal/trades.jsonl` | Present — last entry 2026-05-04 |
| `data/journal/decisions.jsonl` | Present — last entry 2026-05-04 |
| Rolling EOD history | 9 days available: 2026-04-22 → 2026-05-04 |

**Analysis scope:** This post-mortem covers the last full trading day on record — **2026-05-04** — and rolling trends through that date.
Today (2026-05-11) has no data files; a separate post-mortem will be needed once Friday's scan runs.

---

## Performance today (2026-05-04, portfolio vs SPY)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily vs SPY | **-1.43%** |
| Equity EOD | $99,849.69 |
| Cash | $4,986.91 (5.0% — at floor) |
| Trades executed | **53** (extreme churn) |
| Positions at close | 4 (AXTX, META, PWR, SPY) |
| Macro regime | Neutral (score 0.27, VIX 27.3) |

### Rolling benchmark

| Window | Portfolio | SPY | Spread |
|--------|-----------|-----|--------|
| 1 day (05-04) | -1.80% | -0.36% | **-1.43%** |
| 5 day (04-28 → 05-04) | -12.66% | +0.38% | **-13.04%** |
| 9 day (04-22 → 05-04) | -16.31% | +1.95% | **-18.26%** |
| 30 day (from eod.json) | 0.00% | +10.71% | **-10.71%** |

Portfolio is deeply underperforming. The 30-day figure from `period_vs_spy` is -10.71% despite SPY rallying +10.71%.

---

## Positions at close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | EOD Price | PnL% | $ PnL | Mkt Value |
|--------|------|-----|-----------|-----------|------|-------|----------|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% | +$62.6 | $14,589 |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$19.6 | $9,448 |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.14% | -$16.2 | $11,130 |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42.4 | $59,696 |

*Computed from avg_entry and current_price per CLAUDE.md rule; Alpaca unrealized_plpc not trusted.*

SPY cash-proxy represents **59.8% of equity** — the portfolio effectively behaved as a leveraged SPY underperformer all day.

---

## Trades today (2026-05-04) — summary table

53 total events; 11 position closes, 15 entries, 24 exit-learning metrics, 3 wash-trade recoveries.

### Entries (ai_order_submitted)

| Time (UTC) | Symbol | Qty | Entry Px | Stop | Round |
|------------|--------|-----|----------|------|-------|
| 16:04 | LLY | 9.49 | 963.38 | 951.69 | 2 |
| 16:04 | MU | 25.0 | 580.42 | 577.65 | 2 |
| 16:04 | NOK | 367.2 | 13.33 | 13.24 | 2 |
| 16:04 | SNDK | 10.1 | 1246.97 | 1237.62 | 2 |
| 17:04 | DELL | 57.4 | 210.52 | 207.81 | 3 |
| 17:04 | FIX | 6.3 | 1896.5 | 1865.26 | 3 |
| 17:04 | GOOGL | 28.7 | 383.51 | 378.99 | 3 |
| 17:04 | LLY (add) | 3.5 | 962.27 | 952.61 | 3 |
| 17:04 | WDC | 24.5 | 445.36 | 437.86 | 3 |
| 17:04 | COIN | 5.1 | 203.9 | 202.77 | 3 |
| 18:05 | FIX (add)* | 3.7 | 1903.71 | 1881.24 | 4 |
| 18:05 | GOOGL (add)* | 9.3 | 384.43 | 380.10 | 4 |
| 19:08 | AXTX | 313.0 | 46.41 | 45.34 | 5 |
| 19:08 | META | 15.5 | 611.73 | 606.07 | 5 |
| 19:08 | PWR | 14.7 | 758.48 | 748.54 | 5 |

*Wash-trade recovery triggered (see below)*

### Exits (position_closed)

| Time (UTC) | Symbol | Exit Px | Qty | Reason | Est. PnL |
|------------|--------|---------|-----|--------|----------|
| 14:51 | HCAI | 10.69 | 1492 | Exit-arbiter conf=0.72, down -8.78% | **~-$1,400** |
| 16:04 | AMZN | 270.65 | 65.3 | Arbiter: fading below VWAP | ~$0 |
| 16:04 | GEV | 1071.49 | 14.6 | Arbiter: weak momentum | ~$0 |
| 16:04 | UNH | 368.25 | 17.3 | Arbiter: fund LLY | ~$0 |
| 17:04 | MU | 580.81 | 23.0 | Arbiter: peer WDC scores +22 pts | ~+$10 |
| 18:05 | WDC | 440.06 | 24.5 | Arbiter: gap-only, fading | **~-$130** |
| 18:05 | DELL | 210.94 | 57.4 | Verifier dust-sweep | ~+$24 |
| 18:05 | LLY | 963.71 | 13.0 | Verifier dust-sweep | ~+$8 |
| 19:08 | COIN | 203.45 | 66.9 | Arbiter: momentum=0, earnings 3d | ~$0 |
| 19:08 | GOOGL | 382.77 | 38.0 | Arbiter: momentum=0, fading | **~-$36** |
| 19:08 | FIX | 1902.81 | 10.0 | Verifier dust-sweep | ~+$37 |

Dominant loss: HCAI (-8.78%, ~-$1,400) + WDC churn loss (~-$130) + friction across 53 trades.

---

## Phase 2 — Deep Analysis

### 2a. Per-trade quality verdict (2026-05-04)

| Symbol | Side | Qty | Entry | Exit/EOD | PnL% | Hold | AI Grade | Quality |
|--------|------|-----|-------|----------|------|------|----------|---------|
| HCAI | LONG | 1492 | 11.72* | 10.69 | **-8.78%** | ~2h | conf=0.72 exit | **BAD — dominant loss; micro-cap biotech oversize (~$17k = 16.6%)** |
| AMZN | LONG | 65.3 | 270.65 | 270.65 | ~0% | <60m | conf=0.62 reduce | CHURN — entered and exited same scan window at near-zero P&L |
| GEV | LONG | 14.6 | 1071.49 | 1071.49 | ~0% | <60m | conf=0.62 hold then exit | CHURN — GEV +0.67% in 30m after exit (missed $104) |
| UNH | LONG | 17.3 | 368.25 | 368.25 | ~0% | <60m | conf=0.62 exit | CHURN — flat entry, exited to "fund LLY" |
| MU | LONG | 25.0 | 580.42 | 580.81 | +0.07% | 74m | conf=0.58 reduce | NEUTRAL — correct rotation to WDC superior peer |
| NOK | LONG | 367.2 | 13.33 | 13.24 | -0.69% | ~60m | conf=0.62 implicit | BAD — low-conviction name, gapped down, $-34 loss |
| SNDK | LONG | 10.1 | 1246.97 | 1237.52 | -0.76% | <60m | exit | BAD — exited then 30m price was $1254 (+$107 missed) |
| WDC | LONG | 24.5 | 445.36 | 440.06 | **-1.19%** | 57m | conf=0.62 exit | BAD — "gap-only" thesis, entered intraday then immediately fading; **$-130 loss** |
| DELL | LONG | 57.4 | 210.52 | 210.94 | +0.20% | 67m | verifier dust | NEUTRAL — tiny gain, swept by verifier |
| LLY | LONG | 13.0 | 963.38 | 963.71 | +0.03% | 130m | verifier dust | CHURN — held→add→dust-swept, net +$11 on $12.5k position |
| FIX | LONG | 10.0 | avg 1898 | 1902.81 | +0.25% | 156m | conf=0.62 hold | GOOD — technical stayed strong; verifier swept a residual lot |
| GOOGL | LONG | 38.0 | avg 383.7 | 382.77 | -0.24% | 140m | conf=0.58 reduce | BAD — entered, added (wash-trade recovery), then exited; net $-36 loss |
| COIN | LONG | 66.9 | pre-held | 203.45 | ~0% | full day | conf=0.58 exit | NEUTRAL — earnings risk correctly flagged, clean exit |
| AXTX | LONG | 313.0 | 46.41 | **46.61** | **+0.43%** | EOD | conf high | GOOD — biotech breakout, momentum 100, held through close |
| META | LONG | 15.5 | 611.73 | 610.46 | -0.21% | EOD | arbiter entry | NEUTRAL — small drag, kept as diversifier |
| PWR | LONG | 14.7 | 758.48 | 757.38 | -0.14% | EOD | arbiter entry | NEUTRAL — ai_data_center_power leader, slight lag |

*HCAI avg_entry back-calculated from exit price ÷ (1 − 0.0878) = ~$11.72*

**Summary:** 5 churn trades (entered/exited at near-zero), 4 bad trades (HCAI, WDC, SNDK, GOOGL/NOK), 3 neutral, 2 good (FIX, AXTX). Dominant loss is HCAI; secondary is execution friction across 53 events.

---

### 2b. Cross-trade patterns

**Extreme intra-day rotation (primary problem)**
- 5 full scan cycles replaced 4–5 of 6 positions each time (16:04 replaced 4, 17:04 replaced 4, 18:04 replaced 3, 19:08 replaced 5).
- 6 of 15 entries were exited within 65 minutes — pure churn with no net gain.
- The selector's rule "currently_held flag carries ZERO weight" combined with no minimum-hold constraint means each scan can discard the entire book with equal probability as keeping it.

**AI selector failures → cascade effect**
- 2 consecutive `ai_failure` events at 14:01 and 15:02 (`portfolio-selector` returning empty selections after 3 attempts; 50-symbol pool exceeds reliable output length).
- 12 total selector failures in full journal history — a systemic reliability issue.
- The fallback on failure deferred to a third scan at 15:13, meaning the bot held SNDK/HCAI/STX without arbiter oversight for ~75 extra minutes during HCAI's -8.78% move.

**Premature exits on winners**
- GEV: exited at 16:04 ("weak momentum"), 30m-after price +0.67% = $104 missed.
- SNDK: exited at ~16:04 (held pre-existing), 30m-after price $1254 vs exit $1237 = $107 missed.
- STX: 2× reduce verdicts (conf=0.62 each), 30m-after price +$76 missed.
- LLY: exited by verifier dust-sweep, 30m-after +$34 missed.
- Total premature exit cost: **~$322** across 4 symbols.

**Wash-trade loop on same-day re-entries**
- LLY, FIX, GOOGL all triggered Alpaca error code 40310000 ("potential wash trade detected") on re-entry because prior stop-limit orders were still live.
- Stop-cancel delay before re-entry caused rejected orders that required recovery logic; adds latency and split-second price slippage on each affected entry.
- All 3 recoveries succeeded, but each one is a fragile execution step.

**SOXS selected by portfolio-selector at 19:08 (inverse ETF policy breach)**
- SOXS is a 3× inverse SOXX ETF — explicitly a bearish, non-long instrument. It was assigned 12.87% target weight by the selector.
- The bot is long-only by design (`CLAUDE.md`: "Long US equities only (no shorts, no crypto — code enforces this)").
- `execution_target_weights` was empty for the 19:08 scan, so **no order was placed** — the executor or staging logic silently dropped it. But the root cause (selector choosing inverse ETFs) is unfixed.

**Peer-churn: MU → WDC → back-to-SNDK within 3 hours**
- MU (memory sector): entered 16:04, exited 17:04 ("WDC scores +22 pts").
- WDC: entered 17:04, exited 18:05 ("gap-only, fading") at -1.19%.
- SNDK back in at 19:08. Three sequential memory picks, two of which lost money.
- SPY cash-proxy held 60%+ throughout, meaning the active equity was thrashing while the largest holding sat static.

**No-gap between reduce and close verdicts**
- HCAI: exit-arbiter first returned `reduce` (conf=0.62 at ~14:30), then `exit` (conf=0.72 at ~14:51) — two full arbiter calls within 20 minutes for the same deteriorating position.
- STX: two `reduce` verdicts (conf=0.62) at different scans; unclear if partial fills even occurred before position was eventually closed.
- This pattern burns AI call budget and adds 20-minute latency to full exits on rapidly declining positions.

**SPY cash-proxy drag**
- SPY held at 59.8% of equity at close. For a neutral macro regime (score 0.27) where the bot aspires to beat SPY, holding 60% of the book AS SPY by construction cannot outperform it net of 40% active equity friction.
- The selector set `spy_target_pct: 5%` but `execution_cash_target_pct: 28.5%` at the 15:13 scan (staged entries), meaning ~33% was implicitly in SPY proxy all day.

**Overall churn cost (9-day history)**
- High-churn days (≥20 trades): avg vs SPY = **-2.65%** (5 days).
- Low-churn days (<20 trades): avg vs SPY = **-1.51%** (4 days).
- Neither category beats SPY; churn adds ~1.14% extra drag per day.
- 9-day win rate vs SPY: **2 of 9 days (22%)**.

---

### 2c. Proposed Changes

---

**Change 1: Reduce selector pool_size_max from 50 → 30**

*Why:* Both AI selector failures today cited "per_symbol missing 50 symbols" — the 50-symbol pool exceeds the model's reliable output window, causing empty responses after 3 attempts. 12 total failures in journal history confirm this is systemic.

*Diff (config.yaml):*
```yaml
# Before
selector:
  pool_size_target: 40
  pool_size_max: 50

# After
selector:
  pool_size_target: 25
  pool_size_max: 30
```

*Expected impact:* Eliminates the primary cause of AI selector failures; reduces prompt length ~40%, cutting per-scan latency and token cost. Smaller pool still covers all held positions + top movers + seed watchlist leaders. Estimated: reduces selector failure rate from ~12 in 9 days to near-zero.

*Offline backtest:* Not applicable (requires live AI calls). Pool-size reduction has no P&L history to replay.

---

**Change 2: Cap new entries per scan to 2 (via selector.max_new_entries_per_scan)**

*Why:* Every scan today replaced 4–5 positions simultaneously (16:04: +4 new, 17:04: +4 new, 19:08: +5 new). Replacing more than 2 positions per scan means the portfolio never reaches conviction depth on any single name before the next rotation. 6 of 15 entries were exited within 65 minutes.

*Diff (config.yaml):*
```yaml
# Before
selector:
  enabled: true

# After
selector:
  enabled: true
  max_new_entries_per_scan: 2   # hard cap; held positions rotate out freely, but only 2 new names per cycle
```

*src/ai_pipeline.py change (prompt injection):*
```python
# Before (in selector system prompt):
# "You are the SOLE authority on which 3-6 positions the bot holds."

# After: add constraint line:
# "You may select at most {max_new_entries} symbols not currently held. Held positions
#  may be freely exited, but new-entry slots are capped at {max_new_entries} per scan."
```

*Expected impact:* Limits churn to at most 2 new names per hourly scan; positions accumulate hold time and allow stop-loss guardrails to breathe. Estimated friction reduction: ~60% fewer trades on high-rotation days.

---

**Change 3: Add 90-minute re-entry cooldown for same-day exits**

*Why:* LLY, FIX, GOOGL were all re-entered within 60–90 minutes of being exited, triggering Alpaca wash-trade errors (code 40310000). The `fresh_exit_guard_skipped` events confirm the guard ran but was bypassed. Wash-trade recovery adds order latency and partial-fill risk on each re-entry.

*Diff (config.yaml):*
```yaml
# Before (implicit — no same-day re-entry window)
rebalance:
  enabled: true

# After
rebalance:
  enabled: true
  same_day_reentry_cooldown_minutes: 90  # block re-entry on any symbol exited in last 90 min
```

*src/executor.py / src/orchestrator.py:* Check exit timestamp in `data/journal/trades.jsonl` before placing any entry order; reject if `now - exit_ts < 90 minutes`.

*Expected impact:* Eliminates wash-trade broker rejections entirely; also prevents the MU→WDC→SNDK same-sector ping-pong within 3 hours. Estimated: removes 3 wash-trade recovery events per high-churn day.

---

**Change 4: Add SOXS and other inverse/leveraged-bear ETFs to exclude_tickers**

*Why:* The portfolio-selector assigned 12.87% target weight to SOXS (3× inverse SOXX) at 19:08, violating the bot's "Long US equities only" constraint. The execution layer silently dropped it (execution_target_weights was empty), but the selector will keep making this mistake until the symbol is explicitly blocked.

*Diff (config.yaml):*
```yaml
# Before
universe:
  exclude_tickers: []

# After
universe:
  exclude_tickers:
    - SOXS   # 3x inverse SOXX
    - SQQQ   # 3x inverse QQQ
    - SPXS   # 3x inverse SPX
    - SDOW   # 3x inverse DJIA
    - UVXY   # 1.5x long VIX (not a stock)
    - SVXY   # short VIX
    - SRTY   # 3x inverse Russell 2000
```

*Expected impact:* Prevents inverse ETF selection without any execution-layer reliance; clean upstream block. Zero performance cost.

---

**Change 5: Escalate exit-arbiter: skip reduce-then-close two-step when position down >5%**

*Why:* HCAI went through reduce (conf=0.62) then close (conf=0.72) within 20 minutes. Two AI arbiter calls on a rapidly declining position adds 20-minute latency and costs extra tokens. If the position is already down >5% intraday AND the exit-arbiter returns `reduce` with conf ≥ 0.60, escalate directly to `close`.

*Diff (config.yaml):*
```yaml
# Before
exit_arbiter:
  min_confidence: 0.55

# After
exit_arbiter:
  min_confidence: 0.55
  auto_escalate_close_pct: -0.05   # if position pnl < -5% intraday, treat reduce(conf>=0.60) as close
```

*src/orchestrator.py:* In `_handle_exits()`, after receiving `reduce` verdict, check `intraday_pnl_pct < config.exit_arbiter.auto_escalate_close_pct AND verdict.confidence >= 0.60` → override to close.

*Expected impact:* Faster exits on clearly-broken positions; saves one full arbiter call per incident. On HCAI today: would have saved ~20 minutes and ~$30 in additional slippage from continued decline during the gap.

---

**Change 6: Lower `initial_entry_cap_pct` from 0.15 → 0.10 for micro/small-cap entries**

*Why:* HCAI opened at ~$11.72, ~1,492 shares = **~$17,500 = 17.2% of equity** — above the 15% initial cap. Either the cap was not enforced or HCAI was classified as a larger instrument. A $17k position in a sub-$15 biotech stock with a 1% hard stop generates outsized loss on an -8.78% move. Reducing the cap to 10% for stocks with price < $50 limits per-trade dollar risk.

*Diff (config.yaml):*
```yaml
# Before
risk:
  initial_entry_cap_pct: 0.15

# After
risk:
  initial_entry_cap_pct: 0.15          # large-cap default (price > $100)
  initial_entry_cap_pct_smallcap: 0.10  # stocks with price < $50 or market_cap < $2B
```

*Expected impact:* HCAI would have been capped at ~$10,000 (10% of equity), limiting today's loss from ~$1,400 to ~$800. Broader: reduces tail risk on biotech/micro-cap breakouts that frequently fail after initial momentum spike.

*Offline backtest:* Applied to HCAI trade: 313 shares × $46.41 entry in today's EOD session (AXTX, the successful biotech) is at 14.6% — marginally above the 10% small-cap cap. Would have reduced size to ~214 shares, cutting upside from +$62 to +$43 but also cutting downside proportionally. Net risk-adjusted outcome: positive.

---

### 2d. Backtest summary (offline, journal data only)

**Proposal 2 (max_new_entries_per_scan: 2) — retroactive simulation on 2026-05-04:**

If capped at 2 new names per scan:
- 15:13 scan: 2 new entries (AMZN, GEV), keep COIN, MU from held pool. UNH blocked.
- 16:04 scan: 2 new entries (LLY, SNDK), exit AMZN/GEV; MU and COIN continue.
- 17:04 scan: 2 new entries (DELL, WDC), exit SNDK/NOK.
- 18:04 scan: 2 new entries (FIX, GOOGL add), exit WDC/DELL.
- 19:08 scan: 2 new entries (AXTX, META), exit COIN/GOOGL, keep FIX/PWR.

Estimated trades avoided: ~15 (from 53 down to ~38). Given avg slippage per round-trip ~$5–10, saves **$75–$150** in friction. Does not fix the HCAI loss (pre-existing position). Eliminates the MU→WDC→SNDK triple rotation, saving ~$120 (WDC round-trip loss + NOK loss).

**Proposal 3 (90-min re-entry cooldown) — retroactive:**

LLY, FIX, GOOGL re-entries all blocked. LLY: missed +$8 gain; FIX: missed +$37 gain; GOOGL: missed -$36 loss. Net: -$8 -$37 +$36 = **-$9 cost** for the cooldown (slightly negative, but eliminates 3 wash-trade recovery events and associated execution risk). Acceptable trade-off.

*All other proposals cannot be meaningfully backtested offline (require live AI responses or market price data).*
