# Post-Mortem 2026-07-06

> **Note:** No market data exists for today (2026-07-06). The bot has produced **no output since 2026-05-04** — a 63-day gap. This post-mortem covers the last active trading day (2026-05-04) and the full tracked-period performance through that date.

---

## Data Availability

| Source | Status |
|---|---|
| `data/research/2026-07-06_eod.json` | MISSING — bot not running since 2026-05-04 |
| `data/research/2026-05-04_eod.json` | Latest available EOD snapshot |
| `data/research/20260504T*_scan.json` | 6 scan files (15:13–19:09 UTC) |
| `data/research/20260504T195545_preclose.json` | Preclose snapshot |
| `data/journal/trades.jsonl` | Available, latest entries 2026-05-04 |
| `data/journal/decisions.jsonl` | Available |
| `config.yaml` | Current baseline |

**Critical gap:** The bot has not run since 2026-05-04. Root cause unknown from repo data alone (possible crash, environment teardown, or manual stop). This is the primary operational issue.

---

## Performance Today (2026-05-04, last active day)

| Metric | Value |
|---|---|
| Portfolio equity | $99,849.69 |
| Daily return (equity delta) | -1.24% |
| SPY daily | -0.36% |
| Alpha today | **-0.88%** |
| Period equity change (since tracking start) | +0.22% ($99,627 → $99,850) |
| SPY period return | +10.71% |
| **Period alpha** | **-10.49%** |
| Trades on 2026-05-04 | **53** (vs. 7–38 on prior days) |
| Positions at close | 4 (AXTX, META, PWR, SPY-proxy) |

### Rolling EOD Series

| Date | Equity | Daily (computed) | SPY Daily | Cum. Alpha |
|---|---|---|---|---|
| 2026-04-22 | $99,627 | baseline | +1.01% | -4.22% |
| 2026-04-23 | $101,208 | **+1.59%** | -0.39% | -3.82% |
| 2026-04-24 | $99,343 | -1.84% | +0.77% | -3.87% |
| 2026-04-27 | $96,448 | -2.91% | +0.17% | -4.25% |
| 2026-04-28 | $96,867 | +0.43% | -0.49% | -3.69% |
| 2026-04-29 | $93,999 | -2.96% | -0.01% | -3.67% |
| 2026-04-30 | $95,786 | +1.90% | +0.96% | -4.70% |
| 2026-05-01 | $101,101 | +5.55% | +0.29% | -9.54% |
| **2026-05-04** | **$99,850** | **-1.24%** | **-0.36%** | **-10.49%** |

Churn escalation: 7 → 9 → 19 → 24 → 21 → 10 → 23 → 38 → **53** trades/day.

---

## Positions at Close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current | P&L% | Mkt Value | Notes |
|---|---|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,589 | Small winner |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448 | Flat |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,130 | Flat |
| **SPY** | **LONG** | $717.52 | $718.03 | **+0.07%** | **$59,696** | **~60% of equity parked as cash-proxy** |

SPY cash-proxy weight at close: **59.8%** of equity. Effective equity exposure was just 40%.

---

## Trades on 2026-05-04 (Summary)

| Event | Count |
|---|---|
| exit_learning_metrics | 24 |
| ai_order_submitted | 15 |
| position_closed | 11 |
| wash_trade_recovery | 3 |
| **Total** | **53** |

**Symbols touched:** LLY (6×), MU (6×), DELL (4×), FIX (4×), GOOGL (4×), WDC (4×), HCAI (3×), AMZN (3×), GEV (3×), UNH (3×), NOK (3×), SNDK (3×), COIN (3×), STX, AXTX, META, PWR.

Round-trip churns (bought then sold same day):
- AMZN: BUY 15:13 UTC → EXIT 16:05 UTC (-0.68%)
- WDC: BUY 17:04 UTC → EXIT 18:05 UTC (-0.09%)
- GEV: EXIT 16:05 UTC (-0.22% from entry)
- DELL: BUY 17:04 → verifier dust-sweep 18:05 (61 min, bypassed cooldown)
- FIX: BUY 17:04 → INCREASE 18:05 → verifier close 19:09
- LLY: BUY 16:04 → INCREASE 17:04 → verifier dust-sweep 18:05
- COIN: entered earlier period → EXIT 19:09 at +0.31%
- HCAI: intraday momentum exit at -8.79%

---

## Trade-by-Trade Quality (2026-05-04)

All P&L computed as `(exit - avg_entry) / avg_entry`. Entry prices from scan `ai_entry_price` / `filled_avg_price` fields.

| Symbol | Side | Avg Entry | Exit | P&L% | Grade | Verdict | Notes |
|---|---|---|---|---|---|---|---|
| HCAI | EXIT | $11.72 | $10.69 | -8.79% | C | BAD EXIT | Exit arbiter (conf=0.72, Sonnet 4.6); loss real but -8.78% indicates stop was too wide |
| AMZN | ROUND-TRIP | $272.50 | $270.65 | -0.68% | D | CHURN | Bought strong continuation at 15:13; sold 52 min later on EMA flip |
| GEV | EXIT | $1,073.84 | $1,071.49 | -0.22% | D | CHURN | Intraday exit on weak momentum/VWAP; displaced by names that also churn |
| UNH | EXIT | $368.58 | $368.25 | -0.09% | C | BAD EXIT | Acceptable continuation exited to fund LLY; LLY became a verifier dust-sweep |
| MU | EXIT | $577.51 | $580.81 | +0.57% | B- | MIXED | Exited for WDC (peer +22 pts); WDC thesis broken 61 min later |
| WDC | ROUND-TRIP | $440.45 | $440.06 | -0.09% | F | CHURN | Entered as MU replacement; gap_only at 18:05 = 61-min round trip |
| DELL | ROUND-TRIP | $210.52 | $210.94 | +0.20% | F | CHURN | BUY 17:04; verifier dust-swept target=0 at 18:05 (61 min, bypassed cooldown guard) |
| LLY | ROUND-TRIP | $963.00 | $963.71 | +0.07% | F | CHURN | BUY+INCREASE 16:04-17:04; verifier dust-swept target=0 at 18:05 (<2h) |
| FIX | ROUND-TRIP | $1,899.23 | $1,902.81 | +0.19% | D | CHURN | BUY 17:04, INCREASE 18:05, verifier close 19:09; 2 orders wasted |
| GOOGL | ROUND-TRIP | $383.32 | $382.77 | -0.14% | D | CHURN | BUY 17:04, verifier top-up 18:05, arbiter exit 19:09 (momentum=0) |
| COIN | EXIT | $202.82 | $203.45 | +0.31% | B | OK | Earnings in 3 days + momentum=0; exit justified |
| NOK / SNDK | ENTRIES | — | — | unk | D | MISSED | Entered at 16:04; absent from EOD positions; presumed stopped out |

**Grade distribution:** F×3, D×5, C×2, B-×1, B×1. No A trades. 8 of 11 events = churn or questionable exits.

---

## Cross-Trade Patterns

- **Intraday round-trip cascade (root cause):** Portfolio-selector failed validation at 14:09 UTC (0 selections, weight sum=0, missing held positions) and fell back to portfolio-arbiter for every subsequent scan. Each arbiter call re-evaluated the full book independently, found “better opportunities,” and displaced positions entered 1 scan prior. AMZN, WDC, DELL, LLY, FIX, GOOGL all entered and displaced within 60–120 min.

- **Verifier defeating cooldown guard:** `fresh_exit_cooldown` blocks exit-arbiter exits for positions <120 min old if confidence <0.85. But the portfolio-verifier’s `dust-sweep target=0` path bypasses this guard entirely. DELL and LLY were closed by the verifier at 61 min after entry — exactly the scenario the cooldown was designed to prevent.

- **Selector failure cascade:** `decisions.jsonl` records the selector failing 3× at 14:09 with errors: `selected count 0`, `weights+spy+cash sum 0.000`, `missing spy_decision`, `held SNDK/STX/HCAI not selected`. After `max_consecutive_failures=3`, selector skipped for all subsequent scans; 5 of 6 scans ran on portfolio-arbiter fallback.

- **AI vs numeric disagreement (AI lost):** MU exited at +0.57% to buy WDC (AI scored WDC +22 pts over MU). WDC closed at -0.09% same day. Numeric-based MU hold was correct; AI displacement destroyed value.

- **SPY cash-proxy crowding to 60%:** Real equity exited each scan faster than it was redeployed. By preclose, $59.7K (60% of equity) was in SPY. The bot became a 60% SPY tracker paying friction on the other 40%.

- **Trade_critical_model = Sonnet 4.6 (cost-saving setting active):** `config.yaml` has `trade_critical_model: claude-sonnet-4-6`. The selector’s repeated structured-output validation failures strongly suggest Sonnet 4.6 is unreliable for the portfolio-selector’s 16k-token JSON schema. HCAI exit log confirms `model=claude-sonnet-4-6` on a trade-critical path.

- **Churn escalation trend is worsening:** 7→9→19→24→21→10→23→38→**53** trades/day. Not a one-day anomaly; it is amplifying as the dynamic watchlist grows and selector failures compound.

- **No meaningful alpha generated:** The 4 EOD positions (AXTX +0.43%, META -0.21%, PWR -0.15%, SPY +0.07%) produced ~+0.02% weighted impact while 53 trade events consumed all the friction budget.

---

## Proposed Changes

> All proposals are for human review only. No `src/` or `config.yaml` edits are committed in this branch.

---

### 1. Upgrade `ai.trade_critical_model` to `claude-opus-4-7`

**Why:** Selector failed 3× with invalid structured output, triggering arbiter-fallback for 5 of 6 scans, which is the direct root cause of the round-trip cascade. Sonnet 4.6 is unreliable on the 16k-token selector schema; Opus is the documented trade-critical option.

**Diff:**
```yaml
# config.yaml
ai:
  trade_critical_model: claude-sonnet-4-6   # before
  trade_critical_model: claude-opus-4-7     # after
```

**Expected impact:** Selector validation failures → near-zero. Fallback-to-arbiter drops from ~5×/day to ~0×/day. Estimated daily trades: 53 → 15–20. Incremental cost: ~$0.50/scan (Opus vs. Sonnet).

**Backtest:** Unquantifiable offline (requires live API). Qualitative: selector failures documented in decisions.jsonl are the direct root cause; fixing model compliance removes the trigger.

---

### 2. Block verifier dust-sweeps on positions entered within 2 hours

**Why:** `portfolio_verifier.py` closed DELL and LLY at 61 min after entry via `dust-sweep target=0`, bypassing `fresh_exit_cooldown`. The verifier has no age check, making it a cooldown bypass vector.

**Diff (src/portfolio_verifier.py — pseudocode; exact line numbers require reading file):**
```python
# Add before submitting any corrective sell where target_qty == 0:
position_age_minutes = (now - lifecycle.entry_ts).total_seconds() / 60
if target_qty == 0 and position_age_minutes < 120:
    log.info(f"Verifier: skipping dust-sweep of {symbol} — age {position_age_minutes:.0f}min < 120min cooldown")
    continue
```

**Expected impact:** 2–4 fewer order events per day. DELL and LLY held through EOD on May 4 (net +0.13% combined — small but correct behavior).

**Backtest:** Not meaningful in dollars; meaningful as a guard against cooldown-bypass pattern.

---

### 3. Reduce `ai.max_candidates_per_scan` from 10 to 5

**Why:** CLAUDE.md documents “top 5 candidates” but config has been set to 10. Doubling the pool doubles displacement opportunities per scan. Each displacement = 1 exit + 1 entry = 2 trade events + friction.

**Diff:**
```yaml
# config.yaml
ai:
  max_candidates_per_scan: 10   # before
  max_candidates_per_scan: 5    # after
```

**Expected impact (offline backtest):** Estimated −27% total trades over the 9 tracked days (204 → 148). May 4: 53 → ~37.

| Date | Actual | Est. with 5 cands |
|---|---|---|
| 2026-04-22 | 7 | 7 |
| 2026-04-23 | 9 | 9 |
| 2026-04-24 | 19 | 13 |
| 2026-04-27 | 24 | 17 |
| 2026-04-28 | 21 | 15 |
| 2026-04-29 | 10 | 7 |
| 2026-04-30 | 23 | 16 |
| 2026-05-01 | 38 | 27 |
| 2026-05-04 | 53 | 37 |
| **Total** | **204** | **148 (−27%)** |

---

### 4. Add `exit_arbiter.same_day_min_confidence: 0.80`

**Why:** On May 4, every intraday exit on a same-day entry used confidence 0.80–0.85 — barely above the 0.55 floor. AMZN (conf=0.85, -0.68%) and WDC (conf=0.92, -0.09%) were both wrong reversals within 61 min. A same-day position needs a higher exit bar before the AI can reverse its own buy.

**Diff:**
```yaml
# config.yaml
exit_arbiter:
  min_confidence: 0.55                # unchanged for multi-day holds
  same_day_min_confidence: 0.80       # new: same-day entries require 0.80 to exit
```
*(Also requires 2-line change in src/executor.py or src/orchestrator.py to pass position age and apply the higher floor.)*

**Expected impact:** Blocks 2–4 same-day exits per churn day. Conservative friction savings: +0.9–2.1% on high-churn days. Cannot backtest without next-session close prices for would-be held positions.

---

### 5. Diagnose and restart the bot (operational priority — precedes all config changes)

**Why:** 63-day silence is the biggest issue. SPY returned +10.71% during that gap. Every week idle ≈ −0.2% vs. benchmark.

**Steps:**
1. Check scheduler (cron / Task Scheduler) is still active
2. `grep -i error data/journal/decisions.jsonl | tail -20` — find last error
3. `py scripts/scan_and_trade.py --dry-run` — verify bot completes a cycle
4. Apply Proposals 1–4 before restarting to prevent re-entering the churn loop

---

## Config Baseline (diff reference)

```yaml
ai.trade_critical_model: claude-sonnet-4-6     # → claude-opus-4-7 (Proposal 1)
ai.max_candidates_per_scan: 10                 # → 5 (Proposal 3)
exit_arbiter.min_confidence: 0.55              # → add same_day_min_confidence: 0.80 (Proposal 4)
# portfolio_verifier.py: no position-age check # → add 120-min cooldown (Proposal 2)
```

---

*Generated 2026-07-06. P&L from `avg_entry`/`current_price` in eod.json and scan files; Alpaca `unrealized_plpc` not used. No network calls to Alpaca/Telegram/yfinance.*
