# Daily Review — 2026-04-24

## Scoreboard
- Bot day return: **not available** (today_eod snapshot missing)
- SPY day return: **not available** for today; yesterday SPY was -0.39%
- Delta vs benchmark: **unknown** for today
- Open positions (per yesterday's EOD): 10 long (AMD, APLS, ARW, AVGO, FIX, GEV, IRDM, MU, VRT) + SPY cash proxy
- Cash / cash-proxy (yesterday EOD): **-$935 cash (slightly negative)** / $1,677 SPY proxy
- Period return vs SPY: **-3.82%** — bot is lagging benchmark since inception

> ⚠️ **Data caveat:** Today's EOD snapshot is absent. All "today" decisions below are graded on the scan-level evidence (sizing/confidence/signal quality) rather than realized P&L. Yesterday's overnight holds can be partially validated against today's scan-time prices where available.

---

## Today's Decisions — Graded

Today's executions were **dry_run: true** — no capital was committed. These are scoring decisions.

| Symbol | Action | Entry (scan) | Signal Quality | Grade | Notes |
|---|---|---|---|---|---|
| MRVL | buy (dry) | $165.56 | tech 0.87, **RSI 89.2** | **D** | RSI 89 is nosebleed. Price is ~82% above 200-EMA ($90.79). Chasing. Sentiment 0.0 (no positive hits). |
| WDC | buy (dry) | $403.12 | tech 0.84, RSI 76.9, **earnings in 7d** | **D+** | Up 95% above 200-EMA. Earnings 2026-04-30 — this should have triggered the 7-day earnings guardrail but sizing still proceeded. |
| TXN | buy (dry) | $282.23 | tech 0.83, fundamental 0.24 | **B-** | Cleanest of the three — RSI less stretched, steadier trend. Reasonable entry if size kept small. |
| FIX exits (×3) | close_dry | earnings 2026-04-23 | conf 0.60–0.66 | **A** | Correct — earnings guardrail fired and closed before event. |
| IRDM exits (×3) | close_dry | earnings 2026-04-23 | conf 0.39–0.53 | **A** | Same — correct close. |
| **APLS rebalance add** | buy (dry) to 14.9% | — | conf 0.77, tech 0.92 | **C** | **No AI used** (`ai_used: false`) despite crossing high-conviction threshold 0.75. Adding 2× to an existing position purely on tech momentum is aggressive. |
| **IRDM rebalance add** | buy (dry) to 13.5% | — | conf 0.73, tech 0.83 | **F** | **Critical bug**: rebalance is adding to IRDM in the *same day* exits said "close ahead of earnings". Directly contradictory actions in the same session. |

**Key red flag:** IRDM had 3 earnings-exit signals AND 3 rebalance-add signals in the same day. One subsystem wants to close it, another wants to double it. No arbiter resolved the conflict.

---

## Yesterday's Overnight Holds — Graded

Comparing yesterday's preclose decision → today's scan-time/rebalance-time price where observable.

| Symbol | Decision | Yday close | Today observed | Outcome | Grade |
|---|---|---|---|---|---|
| AMD | hold (score 0.15) | $303.19 | $305.33 (yday EOD) | slight + | **B** — low-conviction hold, paid marginally |
| ARW | hold (0.043) | $185.98 | $187.50 | small + | **B-** — score barely positive, "late_day_weakness" flag; lucky |
| AVGO | **close** (-0.034) | $418.74 | $419.94 | would have been ~flat | **C** — closed on weak signal; missed nothing but no alpha from decision |
| FIX | hold (0.079) | $1,760.79 | $1,773.91 | + then forced-closed today on earnings | **B** |
| GEV | hold (0.241) | $1,149.55 | $1,149.53 | flat | **B** |
| MU | **close** (-0.102) | $475.36 | $481.72 (yday) → closed? | close call missed small bounce | **C-** |
| SPY | hold (0.097) | $707.58 | $708.45 | flat | — (cash proxy) |
| VRT | hold (0.303) | $316.40 | $321.75 | **+1.7%** | **A** — highest-conviction hold paid off most |

**Pattern:** Conviction score correlated with overnight payoff direction this cycle. That's a good sign for the overnight model. Sample size too small to be statistically meaningful.

---

## Patterns & Systematic Issues

1. **Rebalance bypasses the AI arbiter even on high-conviction adds.** Both APLS (conf 0.77) and IRDM (conf 0.73) triggered `ai_used: false`. Config says `high_conviction_threshold: 0.75`; APLS crossed it. We're making 13–15% position sizing decisions on rule-based scoring alone.

2. **Rebalance and earnings-exit subsystems are not coordinated.** IRDM today: 3 close-for-earnings signals AND 3 add-to-position signals in the same day. This is a **logical race condition** — whichever runs last "wins", which is non-deterministic in live execution.

3. **Screener keeps surfacing hyper-extended momentum names as new-entry candidates.** MRVL (RSI 89, 82% above 200-EMA), WDC (RSI 77, 95% above 200-EMA). The `technical` signal rewards trend+momentum monotonically but has no "too late to enter" penalty. In a VIX-28 environment, these are the worst setups to buy.

4. **Rebalance keeps scaling into losing longs.** APLS is down -0.83% and the system adds twice in one day (7.5% → 12.9% → 14.9%). No PnL-based dampener on adding to underwater positions.

5. **7-day earnings guardrail appears weak or missing for new entries.** WDC has earnings in 7 days and passed through to dry-run sizing. We have the guardrail for *existing* positions (FIX/IRDM closes worked) but not for *new* entries.

6. **Cash is slightly negative** (-$935) while SPY proxy holds only $1,677. Book is essentially fully deployed with zero operational buffer. `cash_reserve_pct: 0.05` is being ignored in practice.

---

## Proposed Strategy Changes

### Proposal 1: Block rebalance-adds when earnings-exit fired for same symbol same day
- **What:** Maintain an in-memory set of symbols flagged for earnings-close. Rebalance must check this set and skip those symbols.
- **Why:** IRDM today got 3 close + 3 add signals on the same day. This is a correctness bug, not a tuning issue.
- **Expected impact:** Eliminates self-contradictory execution; prevents accidentally doubling a position we intended to close.
- **Risk of being wrong:** None meaningful — earnings-close should always win.
- **Diff sketch** (logical):
  ```
  # engine/scan.py or wherever rebalance runs after exits
  exiting_symbols = {a["symbol"] for a in exit_actions
                     if "earnings" in a.get("reason","")}
  rebalance_candidates = [c for c in rebalance_candidates
                          if c.symbol not in exiting_symbols]
  ```

### Proposal 2: Route high-conviction rebalance adds through the AI arbiter
- **What:** When `blended_confidence >= high_conviction_threshold` (0.75) OR `delta_notional > 5000`, require AI grading before executing the rebalance add.
- **Why:** APLS add went from 7.5% → 14.9% of book in one day on rule scores alone. That's a meaningful sizing decision with no LLM sanity check. Config advertises AI gating at 0.75 but rebalance skips it.
- **Expected impact:** Catches momentum-trap adds (e.g., MRVL-style RSI 89 scenarios) before they double into the book. Marginal AI cost: ~5-10 extra calls/day.
- **Risk of being wrong:** Adds latency to rebalance; AI may block good adds in fast trends.
- **Diff sketch:**
  ```yaml
  rebalance:
    require_ai_above_confidence: 0.75
    require_ai_above_delta_usd: 5000
  ```

### Proposal 3: Add "overbought entry" penalty to technical signal
- **What:** Penalize new-entry technical score when RSI > 75 AND price > 1.5× 200-EMA. Not a hard block — a dampener.
- **Why:** MRVL, WDC, and (yesterday's journal shows) AVGO all keep surfacing with RSI 76–89 and price 80–95% above 200-EMA. The scorer has `rsi_overbought` as a *note* but doesn't reduce the score. We need entries, not blowoffs.
- **Expected impact:** Shifts new-entry selection toward pullback setups in the same trend. Should improve win rate on new entries modestly.
- **Risk of being wrong:** Could miss genuine breakouts in strong regimes. Penalty should be small (-0.15 to score, not a disqualifier).
- **Diff sketch:**
  ```python
  # signals/technical.py
  if rsi > 75 and price > 1.5 * ema200:
      score -= 0.20
      notes.append("chase_penalty")
  elif rsi > 80:
      score -= 0.10
  ```

### Proposal 4: Extend earnings guardrail to new-entry candidates
- **What:** Block or down-rank new buys where `days_until_earnings <= 7` unless `ai_confidence >= 0.85`.
- **Why:** WDC passed through today with earnings in 7 days. Binary event risk on a name we have no position in yet is pure gamble. The exit-side guardrail is correct; mirror it on entries.
- **Expected impact:** Removes 1–3 candidates/week; avoids earnings-gap losses on fresh positions without conviction.
- **Risk of being wrong:** Occasionally misses a post-earnings momentum continuation entry window.
- **Diff sketch:**
  ```yaml
  risk:
    new_entry_earnings_blackout_days: 7
    new_entry_earnings_override_confidence: 0.85
  ```

### Proposal 5: Dampen rebalance adds to underwater positions
- **What:** If `unrealized_plpc < -0.005`, cap rebalance target growth to +25% of current notional per session (not 2×).
- **Why:** APLS (-0.83% PnL) got targeted at 14.9% from 7.5% in one day — nearly doubling an underwater position. Classic "averaging down on a momentum signal" failure mode.
- **Expected impact:** Slower capital concentration into positions the market is rejecting; preserves scaling for winners (which still get full adds).
- **Risk of being wrong:** May cap additions during legitimate consolidations right before a breakout.
- **Diff sketch:**
  ```yaml
  rebalance:
    underwater_add_cap_multiplier: 1.25  # vs current uncapped
    underwater_plpc_threshold: -0.005
  ```

### Proposal 6: Enforce cash reserve floor against SPY proxy first
- **What:** When cash goes below `cash_reserve_min_pct` (2%), auto-sell SPY proxy to restore floor before the next scan. Currently cash is -$935 with SPY proxy $1,677 untouched.
- **Why:** The whole point of cash_proxy is to be auto-sold for operations. Going negative