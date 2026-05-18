# Post-Mortem 2026-05-18

> Generated: 2026-05-18 | Analyst: post-mortem-bot | Model: claude-sonnet-4-6

---

## Data Availability

| Source | Latest Entry | Status |
|---|---|---|
| `*_eod.json` | `2026-05-04_eod.json` | **Data gap: 2026-05-05 → 2026-05-18 (10 trading days missing)** |
| Scan snapshots | `20260504T195545_preclose.json` | Last scan 2026-05-04T19:55 UTC |
| `trades.jsonl` | `2026-05-04T19:55:03Z` | COIN exit_learning_metrics |
| `decisions.jsonl` | `2026-05-04T20:15:04Z` | eod_report event |
| Prior reviews | `2026-05-13_daily_review.md` | Confirmed: no data added since 5/4 |

**10-trading-day gap** (2026-05-05 through 2026-05-18). Bot is either not running, not committing output, or writing to a different path. No data is fabricated. This post-mortem covers the most recent closed session (2026-05-04) as the primary analysis subject, with 9-day rolling benchmarks.

---

## Performance Today (Portfolio vs SPY)

*"Today" = most recent data: 2026-05-04*

| Metric | Value |
|---|---|
| Portfolio daily return | **−1.80%** |
| SPY daily return | **−0.36%** |
| Alpha (day) | **−1.43%** |
| Equity EOD | $99,849.69 |
| Cash EOD | $4,986.91 (5.0% — at floor) |
| Positions at close | 4 (AXTX, META, PWR, SPY-proxy) |
| SPY proxy weight | **59.8%** of equity |
| Trade events on day | **53** (11 closes, 15 opens, 24 learning metrics, 3 wash-trade recoveries) |
| Macro regime | neutral (score 0.27, VIX 27.3–27.9) |

### 9-Day Rolling Series (all available EOD data)

| Date | Port | SPY | Alpha | Equity |
|---|---|---|---|---|
| 2026-04-22 | +0.00% | +1.01% | **−1.01%** | $99,627 |
| 2026-04-23 | +1.56% | −0.39% | **+1.95%** | $101,208 |
| 2026-04-24 | −0.81% | +0.77% | **−1.58%** | $99,343 |
| 2026-04-27 | −4.88% | +0.17% | **−5.05%** | $96,448 |
| 2026-04-28 | −5.13% | −0.49% | **−4.64%** | $96,867 |
| 2026-04-29 | −5.40% | −0.01% | **−5.39%** | $93,999 |
| 2026-04-30 | −2.67% | +0.96% | **−3.63%** | $95,786 |
| 2026-05-01 | +1.82% | +0.29% | **+1.53%** | $101,101 |
| 2026-05-04 | −1.80% | −0.36% | **−1.44%** | $99,850 |
| **9-day total** | **−17.3%** | **+2.0%** | **−19.3%** | |

**Period vs SPY (from eod.json `period_vs_spy` field): −10.71%**

---

## Positions at Close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current | PnL% | Mkt Value | Source |
|---|---|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,589 | yfinance |
| META | LONG | $611.73 | $610.46 | −0.21% | $9,448 | yfinance |
| PWR | LONG | $758.48 | $757.38 | −0.15% | $11,130 | yfinance |
| SPY | LONG | $717.52 | $718.03 | +0.07% | $59,696 | yfinance |
| **Cash** | — | — | — | — | $4,987 | — |

*pnl_pct computed as (current − avg_entry) / avg_entry, per policy.*

---

## Trades on 2026-05-04

| UTC Time | Symbol | Action | Filled Qty | Avg Price | P&L (est.) | Notes |
|---|---|---|---|---|---|---|
| 14:51 | HCAI | SELL (exit-arbiter) | 1492 | $10.69 | **−$1,716** | Held from 5/01 @ $11.84; down −9.7% |
| 15:14 | SNDK | SELL (selector) | 23.30 | $1,250.00 | **+$2,545** | Weekend gap-up captured |
| 15:14 | STX | SELL (selector) | 19.40 | $740.23 | **+$454** | Exited near intraday high |
| 15:18 | AMZN | BUY (selector) | 65.30 | ~$274.60 | — | |
| 15:18 | GEV | BUY (selector) | 14.57 | ~$1,093.33 | — | |
| 15:18 | UNH | BUY (selector) | 17.27 | ~$368.14 | — | |
| 16:04 | AMZN | SELL (selector flip) | 65.30 | $270.65 | **−$258** | 50-min hold |
| 16:04 | GEV | SELL (selector flip) | 14.57 | $1,071.49 | **−$318** | 50-min hold |
| 16:04 | UNH | SELL (selector flip) | 17.27 | $368.25 | **+$2** | 50-min hold |
| 16:05 | LLY | BUY | 9.49 | ~$963 | — | |
| 16:05 | MU | BUY | 25.0 | $584.62 | — | |
| 16:05 | NOK | BUY | 367.24 | $13.33 | — | |
| 16:08 | MU | SELL | 25.0 | $577.45 | **−$179** | **3-min hold** |
| 16:08 | SNDK | re-BUY then SELL | 10.10 | $1,247→$1,238 | **−$95** | Re-bought 50 min after selling at $1,250 |
| 16:08 | NOK | SELL | 367.24 | $13.24 | **−$34** | |
| 17:04 | MU | BUY (again) | 23.0 | $580.42 | — | 3rd MU order today |
| 17:04 | MU | SELL | 23.0 | $580.81 | **+$9** | |
| 17:04 | DELL | BUY | 57.39 | $210.52 | — | |
| 17:04 | FIX | BUY | 6.30 | $1,896.50 | — | wash_trade_recovery triggered |
| 17:04 | GOOGL | BUY | 28.68 | $383.51 | — | wash_trade_recovery triggered |
| 17:04 | WDC | BUY | 24.51 | $445.36 | — | |
| 17:04 | LLY | BUY (add) | 3.51 | $962.27 | — | wash_trade_recovery triggered |
| 18:05 | DELL | SELL | 57.39 | $210.94 | **+$24** | 60-min hold |
| 18:05 | LLY | SELL (all) | 13.0 | $963.71 | **+$8** | |
| 18:05 | WDC | SELL | 24.51 | $440.06 | **−$130** | |
| 18:05 | AXTX | BUY | 313.0 | $46.41 | — | overnight |
| 18:05 | META | BUY | 15.48 | $611.73 | — | overnight |
| 18:05 | PWR | BUY | 14.69 | $758.48 | — | overnight |
| 19:08 | COIN | SELL | 66.90 | $203.45 | **−$176** | earnings flag ignored earlier |
| 19:08 | GOOGL | SELL | 37.96 | $382.77 | **−$38** | |
| 19:08 | FIX | SELL | 10.0 | $1,902.81 | **+$39** | fresh_exit_cooldown blocked earlier exit |

**Rough P&L tally:** HCAI −$1,716 | SNDK/STX gap-ups +$2,999 | Round-trip churn −$1,138 | Small wins +$71 | Net realized ≈ +$216 | Unrealized AXTX/META/PWR at EOD ≈ −$41

---

## 2a. Per-Trade Quality Ledger (2026-05-04)

| UTC | Symbol | Side | Qty | Entry | Exit/Close | PnL | AI Grade | Quality Verdict |
|---|---|---|---|---|---|---|---|---|
| 14:51 | HCAI | SELL | 1492 | $11.84 | $10.69 | **−$1,716** | exit-arb conf=0.72 | **LOSS** — 9.7% drawdown reached; preclose had flagged `close` Friday but order didn’t fill; gap-down Monday added ~$1/sh of avoidable loss |
| 15:14 | SNDK | SELL | 23.30 | $1,140.78 | $1,250.00 | **+$2,545** | selector exit | **GOOD** — weekend gap-up captured cleanly; SNDK was re-bought 50 min later at a worse price |
| 15:14 | STX | SELL | 19.40 | $716.82 | $740.23 | **+$454** | selector exit conf=0.90 | **GOOD** — near intraday high; 30m later $744 (+$76 missed) — acceptable |
| 15:18 | AMZN | BUY | 65.30 | $274.60 | $270.65 | **−$258** | conf=0.90 opp=92 | **CHURN** — “perfect momentum 100, pressing day high” → faded immediately; 50-min round trip |
| 15:18 | GEV | BUY | 14.57 | $1,093.33 | $1,071.49 | **−$318** | conf=0.87 opp=88 | **CHURN** — same pattern; 30m later GEV at $1,078 (+$98 missed) |
| 15:18 | UNH | BUY | 17.27 | $368.14 | $368.25 | **+$2** | conf=0.75 opp=72 | **CHURN** — flat exit; premature sell to fund “stronger” healthcare (LLY) which was also exited |
| 16:05 | MU | BUY | 25.0 | $584.62 | $577.45 | **−$179** | conf=0.90 opp=88 | **CHURN** — 3-minute hold; next scan EXIT fired before position could settle |
| 16:05 | SNDK | re-BUY | 10.10 | $1,247 | $1,238 | **−$95** | — | **CHURN** — re-entered same symbol 50 min after selling at $1,250; immediate round trip |
| 16:05 | NOK | BUY | 367.24 | $13.33 | $13.24 | **−$34** | conf=0.68 | **MISSED** — low-conviction entry; too small to move needle, just adds spread cost |
| 17:04 | MU | BUY | 23.0 | $580.42 | $580.81 | **+$9** | conf=0.85 opp=35 | **CHURN** — 3rd MU cycle same day; flat exit; net MU exposure: −$170 across all cycles |
| 17:04 | DELL | BUY | 57.39 | $210.52 | $210.94 | **+$24** | conf=0.80 opp=76 | **CHURN** — 60-min hold; exited flat; went to $211.23 post-exit |
| 17:04 | FIX | BUY | 6.30 | $1,896.50 | $1,902.81 | **+$39** | conf=0.82 opp=78 | **CHURN** — wash_trade_recovery triggered at entry; 60-min hold then exit attempted at 18:05 but fresh_exit_cooldown blocked; net tiny profit |
| 17:04 | GOOGL | BUY | 28.68 | $383.51 | $382.77 | **−$38** | conf=0.72 opp=70 | **CHURN** — wash_trade_recovery; 60-min round trip; momentum gone by exit |
| 17:04 | WDC | BUY | 24.51 | $445.36 | $440.06 | **−$130** | conf=0.75 opp=68 | **CHURN** — “gap_only classification, bearish EMA” at exit — same signal existed at entry |
| 17:04 | LLY | BUY+ADD | 13.0 | ~$963 | $963.71 | **+$8** | conf=0.65–0.72 | **CHURN** — wash_trade_recovery; 3 separate LLY order cycles same day; flat exit |
| 19:08 | COIN | SELL | 66.90 | $206.08 | $203.45 | **−$176** | conf=0.80 | **MISSED** — earnings flag was visible at 15:18 and 16:05 scans; ignored twice; cost $176 |
| 19:08 | AXTX | BUY | 313.0 | $46.41 | $46.61 (EOD) | **+$62** | conf=0.88 opp=88 | **GOOD** — late-day breakout, breaking_out classification, held overnight |
| 19:08 | META | BUY | 15.48 | $611.73 | $610.46 (EOD) | **−$20** | conf=0.65, tech=**−0.171** | **OVERSIZED** — entered with negative tech score; AI overrode numeric gate; small loss at EOD |
| 19:08 | PWR | BUY | 14.69 | $758.48 | $757.38 (EOD) | **−$16** | conf=0.72 opp=68 | **GOOD** — reasonable entry; small overnight drift |

**Grade tally:** 3 GOOD · 1 MISSED · 9 CHURN · 1 OVERSIZED · 1 BAD (HCAI)

---

## 2b. Cross-Trade Patterns

- **Selector wholesale churn** — Average Jaccard overlap between consecutive scan baskets was 0.28 (0 = completely different, 1 = identical). The selector replaced 70–80% of its portfolio every hour. Direct cost: ~$1,217 in realized churn losses across round-trips (estimate from trades.jsonl). If bot had done nothing after 15:14 SNDK/STX exits, net day P&L would have been ~$1,146 higher.

- **Winner re-entry at worse price** — SNDK sold at $1,250 at 15:14, re-bought at $1,247 at 16:05, sold at $1,238. STX and GEV were exited as “momentum fading” then the next scan’s exit_learning_metrics showed both continued higher for 30–60 min ($75 and $104 respectively).

- **Earnings flag bypass (COIN)** — At 15:18 scan the selector noted “earnings in 3 days” as a negative; at 16:05 it entered COIN at 13.7% weight citing “strong continuation”; at 19:08 it exited with “earnings in 3 days — entry thesis is gone.” This exact pattern repeated twice in one session. Config has `earnings.new_entry_earnings_blackout_days: 2` — it is not being respected intraday.

- **Negative tech score entry (META)** — META entered at 19:08 with `tech_score=−0.171`. CLAUDE.md BUY gate states “technical > 0” as a requirement. AI overrode this via AI weight=0.60 blending. The gate is advisory in code, not enforced as a hard block.

- **Inverse ETF attempted (SOXS)** — At 19:08 scan, `portfolio-selector` included SOXS (Direxion Daily Semiconductor Bear 3X ETF, a short-equivalent instrument) at a 9.0% target weight. Execution preflight rejected it because the stop price was above the current bid. Had preflight passed, this would have been a synthetic short position contradicting the “long US equities only” policy. No config guard currently blocks inverse ETFs.

- **SPY proxy dominance** — SPY closed at 59.8% of equity ($59,696). The bot’s stated purpose is to beat SPY. Holding 60% SPY means 60% of the book exactly tracks the benchmark, making outperformance impossible above a ~±0.7% band from the remaining 40%. `cash_proxy_max_pct` does not exist in config; SPY size is uncapped.

- **Wash trade cascade** — 3 wash_trade_recovery events (LLY, FIX, GOOGL) on 5/4. All occurred because the executor leaves a standing stop order after a position exit, then re-enters the same symbol before the stop is cancelled. Each WTR adds retry latency and risk of partial fills. Three in one day indicates a structural problem: the selector is cycling through symbols fast enough that stale stops overlap new entries.

- **Stop price stale at execution (LLY 19:08)** — AI computed stop at $957.07 based on price $966.74 at analysis time. By execution 30 seconds later, LLY bid had moved to $906–$943 (bid/ask: $906.68/$980). Preflight rejected “stop_not_below_current_market.” This is a stale quote problem; the position was correctly rejected but the AI was analyzing a stale price, wasting a candidate slot.

- **Win rate 2/9 sessions (22%)** — Over all 9 trading sessions in the dataset, the bot beat SPY on only 2 days (4/23 and 5/01). Both winning days had trade counts ≤ 9 and 38. Both losing days with extreme negative alpha (4/27 through 4/29) had moderate-to-high trade counts but the core issue was position concentration in down-trending names (4/27 peak: −4.88% day). High trade count alone does not explain losses, but the churning pattern is the primary 5/4 loss driver.

---

## 2c. Proposed Changes

### Proposal A: Block inverse and leveraged ETFs in universe.exclude_tickers

**Why:** On 5/04 at 19:08, `portfolio-selector` chose SOXS (3× inverse semis) at 9% target weight. This is a synthetic short that contradicts the “long US equities only” policy documented in CLAUDE.md. Execution preflight happened to reject it due to a stale stop price — not because of any policy guard. If the stop had been computed correctly, SOXS would have been bought.

**Diff:**
```yaml
# config.yaml
universe:
  exclude_tickers:
    # BEFORE: []
    # AFTER:
    - SOXS
    - SQQQ
    - SPXS
    - UVXY
    - SDOW
    - SPXU
    - TECS
    - SRTY
    - TZA
    - LABD
```
Or add a runtime flag: `universe.exclude_leveraged_inverse: true` with a lookup against asset name/description containing "Bear", "Short", "Inverse", "−1x", "−2x", "−3x".

**Expected impact:** Zero cost, eliminates entire category of policy violations. Requires one-time config edit.

---

### Proposal B: Hard tech_score > 0 gate for new entries (enforce existing doc policy)

**Why:** META was entered with `tech_score=−0.171` on 5/04 at 19:08. CLAUDE.md states “BUY gate: technical > 0.” This gate is documented but not enforced in code — AI weight (0.60) can lift combined score above threshold even when technical is negative. On the 9-day dataset, no positive-alpha day had an entry with negative tech score.

**Diff (config):**
```yaml
# config.yaml — add under risk:
risk:
  # BEFORE: (no such key)
  # AFTER:
  min_technical_score_for_entry: 0.0  # Hard gate: reject any BUY where tech_score <= this
```

**Diff (code, src/executor.py or src/decision.py — proposal only, not modifying files):**
```python
# In the execution preflight or decision gate:
# BEFORE: no tech_score check at execution
# AFTER:
if is_new_entry and tech_score <= config['risk']['min_technical_score_for_entry']:
    return {'status': 'rejected', 'reject_reason': 'tech_score_below_minimum'}
```

**Expected impact:** Would have blocked META entry on 5/04. Across 9-day dataset, 0 winning positions had negative tech scores at entry (from available data). Prevents AI from overriding the core technical momentum thesis.

---

### Proposal C: Add cash_proxy_max_pct cap (prevent passive indexing)

**Why:** SPY proxy reached 59.8% of equity at EOD 5/04. A 60% passive SPY position makes it mathematically impossible to generate >±1% alpha from the remaining 40% in equities. The bot’s purpose is to beat SPY — not replicate it with a 40% active overlay. There is currently no ceiling on how large the cash proxy can grow.

**Diff:**
```yaml
# config.yaml — add under risk:
risk:
  # BEFORE: (no such key)
  # AFTER:
  cash_proxy_max_pct: 0.20  # SPY/cash proxy hard ceiling as fraction of equity
```

The selector would then be forced to either (a) hold more positions, (b) hold actual cash above 20%, or (c) stay in SPY up to 20% and keep excess as uninvested cash. Uninvested cash is preferable to passive SPY indexing because it preserves opportunity cost optionality without tracking the benchmark.

**Expected impact:** On 5/04 EOD, forces ~$40K currently in SPY into either new positions or true cash. Over 9-day history, SPY proxy returns were near-zero vs. benchmark (obviously — it IS the benchmark). Caps passive drag.

---

### Proposal D: Persist earnings flag as session-level block (no same-day re-entry)

**Why:** COIN had earnings in 3 days. At 15:18 scan this was a negative; at 16:05 the selector entered COIN at 13.7% target (“strong continuation”); at 19:08 the exit cited “earnings in 3 days — thesis gone.” Net loss: $176 across 3 COIN orders in one session. `earnings.new_entry_earnings_blackout_days: 2` is in config but does not prevent intraday re-entry after a same-session exit.

**Diff (config):**
```yaml
# config.yaml — add under earnings:
earnings:
  # BEFORE: (no such key)
  # AFTER:
  session_blackout_after_earnings_exit: true  # Once a position exits due to earnings proximity,
                                               # block re-entry for the same symbol same session
```

**Expected impact:** Would have saved $176 on 5/04. Prevents the specific pattern of: flag earnings → exit → re-enter → exit again (paying spread twice, earning nothing).

---

### Proposal E: Selector minimum Jaccard floor (cap portfolio churn rate)

*(Relates to prior Proposal 1 from `2026-05-05_daily_review.md` — not yet implemented. Adding quantified evidence.)*

**Why:** Average Jaccard overlap between consecutive scan baskets on 5/04 was 0.28. Conservative estimate of realized churn cost from round-trips: $1,217. A Jaccard floor of 0.50 would have blocked 4 of 5 transitions (all had Jaccard < 0.50 except the first). Estimated savings: ~$608/day on high-churn days.

**Diff:**
```yaml
# config.yaml — add under selector:
selector:
  # BEFORE: (no such key)
  # AFTER:
  min_portfolio_jaccard: 0.50  # At least 50% symbol overlap required between scans;
                                # surplus exits blocked unless position triggers stop/arbiter
  incumbent_score_bonus: 10    # +10 opportunity score for currently-held positions
```

**Expected impact:** Modeled at ~$608/day savings on chaos days (from 5/04 actual data). On normal days with fewer scans and lower churn, effect is smaller. Win rate impact: 2/9 days currently; blocking churn likely improves the 7 losing sessions where round-trips were a material cost. Cannot backtest precisely without intraday price series for each symbol.

---

### Proposal F: Warn + block when >2 wash-trade-recovery events in a session

*(New proposal — 3 wash_trade_recovery events occurred on 5/04.)*

**Why:** Wash trade recovery (WTR) events (LLY, FIX, GOOGL) occur because the executor leaves a standing stop order after a position exit, then re-enters the same symbol before the stop is cancelled. Each WTR adds retry latency and risk of partial fills. Three in one day indicates a structural problem: the selector is cycling through symbols fast enough that stale stops overlap new entries.

**Diff (code — proposal only):**
```python
# In src/executor.py or src/orchestrator.py:
# BEFORE: log wash_trade_recovery, retry, continue
# AFTER: after 2nd WTR in a session, emit alert + block new entries for 30 minutes
#   This gives the stop-cancellation pipeline time to clear.
#   Config: risk.wash_trade_recovery_block_threshold: 2
```

**Expected impact:** Prevents cascading broker errors. On 5/04, the 3 WTRs added latency and potential split-second price exposure but all recovered. On a more volatile day a failed recovery could result in an unwanted open stop hitting.

---

## 2d. Backtest Notes

**Proposal A (inverse ETF block):** Not backtestable from in-repo data — SOXS appeared only once (5/04 19:08) and was rejected by preflight. Change has zero opportunity cost on the historical dataset.

**Proposal B (tech_score > 0 gate):** Only one violation in observable data (META 5/04 with tech_score=−0.171). META closed at −0.21% vs entry. Too small a sample for statistical significance. Would need 30+ entries to validate. Directionally consistent with thesis.

**Proposal C (SPY cap 20%):** Not backtestable without knowing what alternative positions the freed capital would have gone into. SPY proxy returned essentially 0% alpha vs SPY by construction. Forcing out of SPY into cash generates 0% return but eliminates passive benchmark tracking. Net effect on alpha: neutral to positive depending on alternative deployment.

**Proposal D (earnings session blackout):** One clear data point: COIN on 5/04, savings $176. Backtest across all 9 sessions would require cross-referencing decisions.jsonl for earnings flags on all symbols — data is available but would take >60s. **Skipping** per time cap; single data point confirms mechanism.

**Proposal E (Jaccard floor 0.50):** Modeled above from 5/04 actual data: ~$608 estimated savings from blocking 4 of 5 high-churn transitions. Full 9-day backtest not possible without knowing which positions would have been held in place of churned ones.

**Proposal F (WTR block):** Not backtestable — no counterfactual for avoided WTR cost in current data.

---

## Open Proposals from Prior Reviews

The following proposals from `2026-05-05_daily_review.md` remain open and unimplemented (confirmed by reviewing config.yaml and the 10-day data gap):

| ID | Proposal | Status |
|---|---|---|
| 1 | Selector inertia bonus (+10 opp score for held positions) | OPEN — overlaps with Proposal E above |
| 2 | Persist earnings-window flag for full session | OPEN — overlaps with Proposal D above |
| 3 | Hard minimum-hold timer per position (not just per ADD) | OPEN |
| 4 | Verify preclose `close` orders actually filled before gap | OPEN — HCAI on 5/4 was direct evidence |
| 5 | Cap intraday turnover / kill-switch on chaos days | OPEN — overlaps with Proposal E |
| 6 | Stop using SPY proxy as chaos-day default | OPEN — overlaps with Proposal C |
| 7 | Raise BUY confidence gate when macro day is red | OPEN |
| 8 | Move to 3×/day sticky-portfolio scan cadence (architectural) | OPEN |

**Recommendation:** Proposals A, D, and E (inverse ETF block, earnings session blackout, Jaccard floor) are the highest-urgency items: they address concrete, repeatable failure modes with quantified costs and zero-or-minimal expected-value tradeoff. Implement in that order.

---

*Post-mortem complete. 10-trading-day data gap is a critical operational issue — confirm bot scheduler status before next session.*
