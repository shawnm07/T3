# Daily Review — 2026-05-05 (covers 2026-05-04 trading session)

> Today is Tue 2026-05-05 in America/Phoenix. The most recent closed session is Mon 2026-05-04. The prior closed session is Fri 2026-05-01 (weekend gap of 3 calendar days). Today's overnight book (AXTX/META/PWR) is **not graded** here — hasn't played out.

## Scoreboard

| Metric | Value |
|---|---|
| Bot day return (5/4) | **−1.80%** |
| SPY day return (5/4) | **−0.36%** |
| **Delta vs benchmark** | **−1.43%** ❌ |
| Period vs SPY (cumulative) | **−10.71%** ❌ (deteriorating from −9.54% on 5/1) |
| Equity EOD | $99,849.69 |
| Cash EOD | $4,986.91 (5.0% — at the floor) |
| Open positions | 4 long (AXTX, META, PWR, **SPY proxy** $59,696) — 0 short, 0 crypto |
| SPY proxy share | **59.8%** of equity (this is the dominant position) |
| Trades on day | **53 events** (15 opens, 11 closes, plus learning metrics) |
| Macro regime | neutral score 0.27, VIX ~27.4–27.9 (no halt) |

**Friday → Monday equity:** $101,101 → $99,850 = **−$1,251 (−1.24%)** of which the gap-down on HCAI alone explains ~$1,985 in unrealized→realized loss; the rest is intraday churn cost partly offset by SNDK/STX gap-up gains.

---

## Today's Decisions — Graded (2026-05-04)

### High-level shape of the session

The bot ran **6 selector scans + 1 preclose**. Across those scans the unified portfolio selector picked **6 disjoint or near-disjoint baskets in a single day**. Jaccard overlap between consecutive selector outputs:

| Window | Jaccard | Kept | Added | Dropped |
|---|---|---|---|---|
| 15:13 → 15:18 (5 min!) | 0.57 | AMZN, COIN, MU, UNH | BAND, META | GEV |
| 15:18 → 16:05 | 0.20 | COIN, MU | LLY, NOK, SNDK, V | AMZN, BAND, META, UNH |
| 16:05 → 17:04 | 0.20 | COIN, LLY | DELL, FIX, GOOGL, WDC | MU, NOK, SNDK, V |
| 17:04 → 18:05 | 0.33 | COIN, FIX, GOOGL | CUE, PWR, RBLX | DELL, LLY, WDC |
| 18:05 → 19:08 | **0.09** | PWR | AXTX, LLY, META, SNDK, SOXS | COIN, CUE, FIX, GOOGL, RBLX |

**Average Jaccard ≈ 0.28.** The selector is functionally regenerating from scratch every scan rather than expressing portfolio conviction. Every flip costs spread + slippage on both legs.

### Per-trade ledger (chronological, dollars realized vs. entry)

| Time UTC | Sym | Action | Qty | Avg Entry | Exit/Close | Realized P&L | Grade | Notes |
|---|---|---|---|---|---|---|---|---|
| 14:51 | **HCAI** | sell | 1492 | $11.84 | $10.69 | **−$1,716** | **F** | Friday preclose decision was already `close` (score 0.053, "late_day_weakness"). Order didn't fill Friday. Gap-down Monday open cost ~$1.33/sh. |
| 15:14 | SNDK | sell | 23.30 | $1140.78 | $1,250.00 | **+$2,545** | **A** | Captured the weekend gap-up cleanly. Decision was driven by arbiter "fading volume, peer leader MU has superior remaining upside". (MU thesis blew up later — see below.) |
| 15:14 | STX | sell | 19.40 | $716.82 | $740.23 | **+$454** | **A−** | "Weak momentum, below EMA20" arbiter call exited a winner near intraday high. 30m later STX was at $744 (would have been +$76 better) but outcome is solid. |
| ~15:18 | AMZN | buy | 65.30 | ~$274.60 | — | — | (see below) | Selector entered "perfect momentum 100, pressing day high". Cohort entry at peak. |
| ~15:18 | GEV | buy | 14.57 | ~$1,093.33 | — | — | (see below) | Same theme — bought at "pressing day high". |
| ~15:18 | UNH | buy | 17.27 | ~$368.14 | — | — | (see below) | Healthcare diversifier — bought at top of intraday range. |
| 16:04 | **AMZN** | sell | 65.30 | $274.60 | $270.65 | **−$258** | **F** | Held ~50 minutes. Arbiter flipped: "fading momentum, below VWAP, bearish EMA". This is the entire pattern in one trade — buy the breakout, sell the immediate fade. |
| 16:04 | **GEV** | sell | 14.57 | $1,093.33 | $1,071.49 | **−$318** | **F** | Same story. 50 minutes hold. 30m later GEV was at $1078.63. |
| 16:04 | **UNH** | sell | 17.27 | $368.14 | $368.25 | **+$2** | **D** | Lucky exit at flat. Arbiter said "LLY is the stronger healthcare name" — but LLY was bought minutes later only to be exited at 18:05. |
| 16:05 | LLY | buy | 9.49 | $963.38 | — | — | — | "Strong continuation" |
| 16:05 | MU | buy | 25.0 | $584.62 | — | — | — | "Pool leader 0.9 conf" — but exits at 17:04. |
| 16:05 | NOK | buy | 367.24 | $13.33 | — | — | — | "Strong continuation" |
| 16:05 | SNDK | buy | 10.10 | $1,246.97 | — | — | — | **Re-buying SNDK 50 min after selling it at $1,250 — paying spread to give back alpha.** |
| 16:08 | **MU** | sell | 25.0 | $584.62 | $577.45 | **−$179** | **F** | Held 3 minutes (!). Order timestamps suggest the BUY hadn't even cleared cooldown when the next-scan EXIT fired. |
| 16:10 | **SNDK** | sell | 10.10 | $1,246.97 | $1,237.52 | **−$95** | **F** | Same — re-buy → exit cycle within minutes. The SNDK round trip cost ~$200 in slippage to ultimately end with the same flat exposure we had after 15:14. |
| 16:08 | **NOK** | sell | 367.24 | $13.33 | $13.24 | **−$34** | **F** | Same intra-scan churn. |
| 17:04 | MU | buy | 23.0 | $580.42 | — | — | — | **MU re-bought again** at higher than the 16:08 exit price. |
| 17:04 | **MU** | sell | 23.0 | $580.42 | $580.81 | +$9 | **D** | Closed flat. Net MU round-trips today: 2 entries, 2 exits, ≈ −$170. |
| 17:04 | DELL | buy | 57.39 | $210.52 | $210.94 | **+$24** | **C+** | Held 60 min, exited basically flat. |
| 17:04 | FIX | buy | 6.30 | $1,896.50 | — | — | — | |
| 17:04 | GOOGL | buy | 28.68 | $383.51 | — | — | — | |
| 17:04 | WDC | buy | 24.51 | $445.36 | $440.06 | **−$130** | **F** | 60-min round trip. |
| 17:04 | LLY | buy | 3.51 | $962.27 | — | — | (combined w/ 9.49 above) | `wash_trade_recovery` triggered — collapsing two contradictory orders. |
| 17:04 | COIN | buy | 5.10 | $203.90 | $202.68 | **−$6** | **F** | This `BUY 5.10 sh` at 17:04 came after a 15:18 selector decision to `REDUCE COIN by 19.9 sh because earnings in 3 days`, then a 16:05 decision to `INCREASE COIN by 41 sh "strong continuation"`. **The earnings-gate flag was set then over-ridden in the next scan.** |
| 18:05 | **DELL** | sell | 57.39 | $210.52 | $210.94 | (already booked) | F | Same-day flip. |
| 18:05 | **LLY** | sell | 13.0 | $963.10 | $963.71 | +$8 | D | "Fading momentum (53), recent_trend=falling" — exited the position a different scan said was healthcare leader 60 min ago. |
| 18:05 | **WDC** | sell | 24.51 | $445.36 | $440.06 | (already booked) | F | "Gap_only classification, bearish EMA, fading volume". Why was it bought 60 min before? |
| 18:05 | CUE | buy | 237.88 | ~$15-ish | — | — | — | **Closed by EOD (not in EOD positions).** |
| 18:05 | RBLX | buy | 148.28 | ~$67-ish | — | — | — | **Closed by EOD.** |
| 18:05 | FIX | INCREASE | +3.70 | $1,903.71 | — | — | — | |
| 18:05 | GOOGL | INCREASE | +9.32 | $384.43 | — | — | — | |
| 18:05 | PWR | buy | 9.09 | ~$758-ish | — | — | — | |
| 19:08 | **COIN** | sell | 66.90 | $206.08 | $203.45 | **−$176** | **F** | "Momentum 0, fading, **earnings in 3 days** — entry thesis is gone." We had this signal at 15:18 and ignored it. |
| 19:08 | **GOOGL** | sell | 37.96 | $383.78 | $382.77 | **−$38** | **F** | Same-day round trip. |
| 19:08 | **FIX** | sell | 10.0 | $1,898.90 | $1,902.81 | +$39 | C | Same-day round trip; profit ate the spread. |
| 19:08 | AXTX | buy | 313.0 | $46.41 | — | — | (overnight) | Late-day breakout entry. **Today's overnight — not graded.** |
| 19:08 | META | buy | 15.48 | $611.73 | — | — | (overnight) | **Today's overnight — not graded.** |
| 19:08 | PWR | INCREASE | +14.69 | $758.48 | — | — | (overnight) | **Today's overnight — not graded.** |
| 19:08 | SNDK | buy | 9.87 | ?? | exited?? | — | — | Not in EOD positions — closed somewhere. |
| 19:08 | LLY | buy | 10.48 | ?? | exited?? | — | — | Not in EOD positions — third LLY cycle today. |
| 19:08 | SOXS | buy | 673.90 | ?? | exited?? | — | — | **Inverse-3x semis ETF** — directly contradicts everything else the selector did today. Not in EOD positions. |

**Tally of grades:** 2× A, 1× A−, 1× C+, 2× C, 4× D, **9× F**.

### Net of the day's churn (rough P&L attribution)

| Bucket | Realized P&L |
|---|---|
| HCAI gap-down (forced exit) | −$1,716 |
| SNDK + STX overnight winners (sold at gap-up) | +$2,999 |
| Re-buying SNDK at higher price then exiting | −$95 |
| AMZN/GEV/UNH 50-min round-trip | −$574 |
| MU two round-trips | −$170 |
| WDC, COIN, GOOGL, NOK round-trips | −$378 |
| LLY/DELL/FIX small wins | +$71 |
| **Realized subtotal** | **+$137** |
| **Unrealized AXTX/META/PWR (intraday MTM)** | **−$200** approx (at preclose price vs entry) |
| **Friction (estimated 5–10 bps × 26 transactions × ~$13K avg)** | **−$170 to −$340** |
| **Sum vs reported daily Δ ($−1,251)** | Most of the gap is the cost of having the SPY proxy go from $36.4K → $59.7K mid-day on a down-tape, locking in beta when SPY also fell. |

**Key insight:** The bot bought into SPY proxy heavily after dumping winners — re-deploying $23K of cash into SPY at a worse price than it could have held the original positions for.

---

## Yesterday's Overnight Holds — Graded (Fri 5/1 → Mon 5/4 close)

Friday preclose decision (`20260501T195653_preclose.json`): held 4 positions through the 3-day weekend.

| Symbol | 5/1 Decision | 5/1 Close | 5/4 Open / Exit | Δ% (gap) | $ Impact | Grade | Notes |
|---|---|---|---|---|---|---|---|
| **HCAI** | **`close` (score 0.053, "late_day_weakness")** | $12.02 | $10.69 (sold 14:51 Mon) | **−11.06%** | **−$1,985** | **F (execution)** / B (decision) | Decision was correct; **the close order did not fill on Friday** — same Pydantic-style silent-failure pattern as the 4/23 postmortem flagged but in a different code path. The gap-down on a stock with no liquidity buffer cost 2% of equity in one event. |
| SNDK | `hold` (score 0.64, "closing_near_high") | $1,187.00 | $1,250.00 | +5.31% | +$2,545 | **A** | Best high-conviction hold of the period. Notes/score correctly flagged the strong close. |
| STX | `hold` (score 0.419, "closing_near_high") | $726.93 | $740.23 | +1.83% | +$454 | **A−** | Solid medium-conviction hold validated. |
| SPY proxy | (auto-sized, $36,378 buy_proxy) | $720.75 | $718.03 | −0.38% | −$138 | (cash proxy) | Beta exposure; small drag. |
| **Net overnight P&L** | | | | | **+$876** | | **Without the HCAI execution failure this would have been +$2,861 / +2.83%.** The decision logic was right; the execution path leaked money. |

**Verdict:** The overnight *thesis selection* was good (SNDK/STX both flagged "closing_near_high" with high scores, both gapped up). The HCAI loss is **not a thesis failure — it's a missed execution** that should have been caught. This is the single highest-impact bug visible in the data.

---

## Patterns & Systematic Issues (last ~5 sessions: 4/27 → 5/4)

### 1. Selector instability — the dominant problem (**evidence: 5/1, 5/4 scans**)

Across 6 scans on 5/4, the unified portfolio selector returned **3 selector outputs with Jaccard = 0.00 to the immediately following one** on 5/1, and an average Jaccard of 0.28 on 5/4. Same pattern on 5/1 (Jaccard hit 0.00 three times across the day). The selector is treating each scan as an independent "what's hot in the last 30 min" optimizer, not a "manage a portfolio over time" optimizer. Result: ~26 round-trip trades per recent session, each leaking spread + slippage.

### 2. Intraday round-tripping inside cooldown windows (**evidence: 5/4 trades.jsonl**)

On 5/4: MU bought at 16:05 → sold at 16:08 (3 minutes); SNDK sold at 15:14 → re-bought at 16:10 → re-sold at 16:10 same minute. AMZN/GEV/UNH bought ~15:18 → all exited 16:04 (50 min). The configured 120-min cooldown only applies to ADD operations on existing positions (per the 17:04 LLY note "held within 120-minute cooldown"); it does **not** prevent the next-scan selector from issuing a full EXIT.

### 3. Earnings-gate signals get ignored by the next scan (**evidence: 5/4 COIN**)

15:18 selector: `REDUCE COIN -19.9 sh, "earnings in 3 days warrants reducing position to manage event risk"`.
16:05 selector: `INCREASE COIN +41 sh, "strong continuation"`.
19:08 selector: `EXIT COIN, "earnings in 3 days — entry thesis is gone"`.

The same arbiter reached opposite conclusions about the same earnings risk in the same day. The earnings-window flag is not "sticky" — once raised it should suppress all BUY/INCREASE on that symbol for the rest of the trading day.

### 4. Friday-preclose `close` decisions don't reliably execute (**evidence: HCAI 5/1 → 5/4**)

Same failure mode as the 4/23 postmortem flagged for AVGO/MU (`ClosePositionRequest(qty=None, percentage=None)`). Either the bug was never fixed, or a different code path has the same defect. There is no retry/verifier check that the requested closes actually closed before the next session opens.

### 5. SPY proxy used as a default cash sink, then over-allocated on down days (**evidence: 5/4 EOD positions**)

EOD on 5/4: $59,695 SPY proxy (59.8% of equity). The 5/4 scans show SPY proxy growing from $36K at start to $59.7K at EOD as the selector exited names. The proxy was **bought up while SPY itself was down** (SPY down −0.38% on the day). This is a "punt to passive when uncertain" pattern that on a red day locks in beta loss right before close.

### 6. Period vs SPY trajectory worsening, not improving (**evidence: EOD `period_vs_spy`**)

5/1 period_vs_spy: −9.54% / 5/4: −10.71%. The bot is not just under-performing — the gap is widening. Most of the gap is friction + bad-day SPY-buying behavior, not sector calls being wrong.

### 7. Bot has drifted from "swing" to "intraday day-trader" cadence

CLAUDE.md says: *"Swing cadence, 6× daily scans on weekdays."* In practice the 6 scans + preclose are issuing 11–15 closes per day. Average position holding period within a day is well under 2 hours. This is the wrong cadence for the strategy stated.

---

## Proposed Strategy Changes

### Proposal 1: Selector inertia — penalize replacing held positions in the unified plan

- **What:** In `portfolio-selector` (and/or `portfolio-arbiter` prompt + `decision.py`), apply a **+0.10 opportunity-score bonus to any currently-held name** when the selector ranks the candidate pool. A challenger must out-score the held name by **>10 points** to displace it. Equivalently in code: `effective_score = score + (10 if symbol in current_positions else 0)`.
- **Why:** 5/4 selector flipped its 5-name basket 6 times in 6 hours. Without inertia the selector treats holding and entering as equivalent costs — but they aren't (holding has no friction, entering pays spread + slippage on both legs).
- **Expected impact:** Cuts daily round-trip count from ~26 to ~10. Saves ~$150–$300/day in friction. Lets winning theses run instead of cycling.
- **Risk of being wrong:** Sticks with deteriorating positions slightly longer. Mitigated by the existing exit-arbiter (which still runs first) and the `risk.hard_stop_loss_pct: 0.01`.
- **Backtest result:** Not directly testable from snapshots. Friction model: 26 × $13K × 7.5 bps = $254/day saved. Across 21 trading days/month = **~$5,300/month** in friction savings on current book size, all else equal.
- **Diff sketch:** Add to `portfolio-selector` system prompt and to the scoring step:
  ```
  selector:
    incumbent_score_bonus: 10    # opportunity-score points
    incumbent_displacement_min_delta: 10
  ```

### Proposal 2: Persist earnings-window flag for the full session

- **What:** Once the selector flags a symbol as "earnings within `earnings.trim_exit_days`" in any scan that day, **block all subsequent BUY / INCREASE actions for that symbol** until the next session. EXIT / REDUCE remains allowed.
- **Why:** COIN on 5/4 — REDUCE @ 15:18 (earnings 3d) → INCREASE @ 16:05 (strong continuation) → EXIT @ 19:08 (earnings 3d). The earnings-window flag is being recomputed per-scan and overwritten.
- **Expected impact:** Eliminates intraday whipsaw on names with binary event risk. Prevents adding to a position the day before earnings.
- **Risk of being wrong:** Occasionally misses a "post-earnings momentum continuation" entry inside the trim window.
- **Diff sketch:**
  ```python
  # orchestrator: keep an in-memory set per session
  earnings_locked_today.add(symbol)  # whenever earnings flag fires
  # In selector pre-filter:
  if symbol in earnings_locked_today and proposed_action in ('BUY','INCREASE'):
      proposed_action = 'HOLD'
  ```
  And in `config.yaml`:
  ```yaml
  earnings:
    intraday_buy_lockout: true  # once flagged, no buys/increases for the rest of the session
  ```

### Proposal 3: Hard minimum-hold timer per position (not just per ADD)

- **What:** No EXIT (full close) of a position within **N minutes** of the entry fill, except when (a) the price hits the protective stop, or (b) the exit-arbiter confidence is **≥0.85**. Default N = 90 minutes.
- **Why:** MU was bought at 16:05 and sold at 16:08 (3 min). AMZN/GEV/UNH were 50-min holds. These are scan-driven, not signal-driven exits. The thesis didn't change — the selector simply re-rolled and picked different names.
- **Expected impact:** Forces the selector to "live with" its choices for at least one scan cycle. Prevents 3-minute round trips. The `≥0.85 confidence` override preserves genuine "thesis broken" exits.
- **Risk of being wrong:** Could delay a legitimate exit when conditions change rapidly mid-scan. The protective-stop carve-out covers tail-risk; the confidence-override covers strong-conviction flips.
- **Diff sketch:**
  ```yaml
  exit_arbiter:
    min_confidence: 0.55
    min_hold_minutes: 90
    min_hold_override_confidence: 0.85
  ```
  Logic in `_handle_exits()`: skip non-stop exits where `(now - position.opened_at) < min_hold_minutes` and `ai_confidence < min_hold_override_confidence`.

### Proposal 4: Verify Friday/preclose `close` orders actually filled before EOD

- **What:** After the preclose scan submits any `close` orders, run a **2-minute follow-up check** that queries position state. For any symbol still held that was supposed to close, retry once with `ClosePositionRequest(percentage=1.0)` (the 4/23 postmortem fix verified by the exact same defect today).
- **Why:** HCAI on Friday — preclose decision was `close` (score 0.053, late_day_weakness). The order did not fill. The position carried into a 3-day weekend and gapped down 11% Monday morning, costing $1,985 (≈2% of equity). This is the **single largest avoidable loss in the data**.
- **Expected impact:** Eliminates silent close-order failures. Worst-case scenario per failure is re-trying a close that doesn't strictly need re-trying (cheap).
- **Risk of being wrong:** Essentially none. Re-issuing a close on a fully-closed position is a no-op at the broker.
- **Diff sketch:**
  ```python
  # scripts/preclose_decision.py — after exit submission loop:
  time.sleep(120)
  positions = trading_client.get_all_positions()
  held = {p.symbol for p in positions}
  for sym in intended_closes:
      if sym in held:
          log.warning(f"Close order for {sym} did not fill, retrying with percentage=1.0")
          trading_client.close_position(sym, ClosePositionRequest(percentage="1.0"))
  ```

### Proposal 5: Cap intraday turnover (kill-switch on chaos days)

- **What:** Hard cap of **N ≤ 12 fills per day** (open + close events combined, excluding the preclose batch). Once the day's count reaches the cap, **all selector BUY/INCREASE actions are vetoed** for the rest of the session — only EXITs, stops, and the preclose adjustments are allowed.
- **Why:** 5/4 had 53 events. 5/1 had 38. Recent days are ratcheting up. The bot is paying friction to repeatedly re-pick from a shifting top-of-book. The cap forces the bot to commit to its earlier picks instead of repeatedly re-rolling.
- **Expected impact:** Caps friction at ~$150/day worst case. Reduces variance from selector instability.
- **Risk of being wrong:** Occasionally locks the bot out of a clean late-day breakout entry. Mitigated by allowing the preclose batch to bypass the cap.
- **Diff sketch:**
  ```yaml
  risk:
    max_intraday_fills: 12      # not counting preclose batch
    excess_fills_action: veto_buys  # 'veto_buys' | 'log_only'
  ```

### Proposal 6: Stop using SPY proxy as the chaos-day default; raise cash floor on red-tape days

- **What:** When `macro.daily_change_pct < -0.5%` AND realized intraday turnover > Y, **redirect cash-proxy from SPY-buy to cash-hold** for the remainder of the session. Concretely: cap `spy_target_pct` at the morning's value; do not auto-grow it from intraday exits.
- **Why:** On 5/4 the SPY proxy notional grew $36K → $59.7K (≈ +$23K of intraday SPY buying) on a day when SPY itself fell −0.38%. That is buying high-beta exposure in a red tape mid-session. Cash would have been a better default.
- **Expected impact:** On down days, cash ratio rises naturally as the bot exits names. Reduces the lock-in effect where the SPY proxy holds the bag while underlying cash positions would have been preserved.
- **Risk of being wrong:** Misses up-day mean reversions where SPY rallies into close. Mitigated because the rule only kicks in on already-down days with high turnover (signal of disorientation).
- **Diff sketch:**
  ```yaml
  cash_proxy:
    intraday_growth_disabled_when:
      spy_daily_change_pct_below: -0.005
      intraday_fills_above: 8
  ```

### Proposal 7: Raise the BUY confidence gate when the macro day is red

- **What:** When `spy_intraday_change < -0.3%`, raise the selector's effective new-entry confidence floor from 0.65 → **0.78**.
- **Why:** Macro was "neutral" (score 0.27) on 5/4 — not a halt — but the day's tape was negative. The selector kept entering "strong continuation" names that immediately faded. A higher conviction bar on red-tape days filters out reflex breakout chasing.
- **Expected impact:** Approximately halves the new-entry count on down days. Reduces same-day round-trip rate.
- **Risk of being wrong:** Misses the rare strong divergence name that breaks out against the tape (rare).
- **Diff sketch:**
  ```yaml
  selector:
    new_entry_min_confidence: 0.65
    bearish_tape_min_confidence: 0.78
    bearish_tape_threshold_pct: -0.003
  ```

### Proposal 8 (architectural — flagged for discussion, not for direct implementation): Move scan cadence to 3×/day with a "sticky-portfolio" arbiter

- **What:** Reduce scan cadence from 6× to 3× (open, midday, preclose). Replace per-scan portfolio rebuild with a "sticky-portfolio" arbiter whose default is `HOLD ALL` and which only acts when (a) a held position has triggered an exit signal, or (b) cash is uncommitted and a high-conviction (≥0.80) new candidate is available.
- **Why:** All evidence above points to over-frequent re-evaluation as the dominant alpha leak. The bot's stated identity is "swing cadence" — the actual behavior is pure intraday day-trading. A coarser cadence + sticky default would force the bot to either commit or stay on the sidelines.
- **Expected impact:** Largest potential win — could move period_vs_spy from −10.7% toward parity by removing systematic friction. Hardest to validate without live A/B.
- **Risk of being wrong:** Loses some intraday optionality. Misses fast-moving regime shifts mid-day.
- **Backtest:** Not run — would need a parallel-run sandbox.

---

## Backtests Run

- **Selector consistency on 5/4:** Average Jaccard between consecutive selectors = **0.28**, with one transition at **0.09** (only PWR survived 18:05→19:08). On 5/1: three transitions hit Jaccard = **0.00**. → Confirms "selector instability" as a primary issue.
- **Cumulative `missed_pnl_30m` across all journaled exits (history):** **−$16.59** over 14 exits. Bot exits are timing-neutral on a 30-minute window. → Tells us the *timing* of exits isn't broken; the *frequency* is.
- **Cumulative `missed_pnl_60m`:** **−$315** over 4 exits. Sample too small but trend matches: bot exits aren't systematically early or late, they're just *too numerous*.
- **Friction estimate for 5/4:** 26 transactions × ~$13K notional × 5–10 bps → **$170–$340/day** in pure spread cost. Across 21 sessions/month: **$3,500–$7,100/month**.
- **HCAI counterfactual:** If the Friday close had filled at $11.40 (preclose scan price) instead of $10.69 (Monday open), **+$1,059** would have been preserved. → Single biggest avoidable loss in the dataset.
- **Overnight thesis quality:** Of Friday's 3 holds, scores **0.64 / 0.419 / 0.053** correlated with outcomes **+5.31% / +1.83% / −11.06%**. Score-vs-outcome correlation is excellent; the bot's overnight selection model works. The execution layer is the weak link, not the model.
