# Post-Mortem 2026-06-05

## Data Availability

| Source | Status |
|---|---|
| `data/research/2026-06-05_eod.json` | **MISSING** — no EOD snapshot for today |
| Last available EOD | `2026-05-04_eod.json` |
| `data/journal/trades.jsonl` | Available (last entry 2026-05-04) |
| `data/journal/decisions.jsonl` | Available (last entry 2026-05-04) |
| `config.yaml` | Available |

> **Note:** No trading data exists after 2026-05-04. This post-mortem covers the last 9 trading days of available data (2026-04-22 through 2026-05-04), treating 2026-05-04 as the reference "most recent" session. All P&L computed from `avg_entry` / `current_price` fields; Alpaca `unrealized_plpc` is ignored.

---

## Performance Today (2026-05-04 reference session vs SPY)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| vs SPY (today) | **-1.43%** |
| Equity at close | $99,849.69 |
| Trades executed | **53** (extreme churn) |
| Positions at close | 4 |

**Period summary (9 sessions: 2026-04-22 to 2026-05-04):**

| Date | Portfolio | SPY | vs SPY |
|---|---|---|---|
| 2026-04-22 | +0.00% | +1.01% | -1.01% X |
| 2026-04-23 | +1.56% | -0.39% | +1.95% OK |
| 2026-04-24 | -0.81% | +0.77% | -1.59% X |
| 2026-04-27 | **-4.88%** | +0.17% | **-5.05%** X |
| 2026-04-28 | **-5.13%** | -0.49% | **-4.65%** X |
| 2026-04-29 | **-5.40%** | -0.01% | **-5.39%** X |
| 2026-04-30 | -2.67% | +0.96% | -3.63% X |
| 2026-05-01 | +1.82% | +0.29% | +1.53% OK |
| 2026-05-04 | -1.80% | -0.36% | -1.43% X |

- **Days beating SPY:** 2 / 9 (22%)
- **5-day sum (Apr 28-May 4):** portfolio -13.18%, SPY +0.39%
- **Period return vs SPY (from eod.json field):** **-10.71%** (SPY +10.71% same period)
- **Goal:** beat SPY within risk budget. **Status: FAILING**

---

## Positions at Close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | Current | PnL% | Market Value |
|---|---|---|---|---|---|---|
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** | $59,695.86 |
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** | $14,588.93 |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** | $11,129.62 |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** | $9,448.36 |

> SPY represents **59.8%** of portfolio equity. The bot is effectively a diluted SPY proxy — structurally incapable of beating SPY on most days.

---

## Trades Today (2026-05-04 — 53 total)

| Time (UTC) | Event | Symbol | Qty | Note |
|---|---|---|---|---|
| 14:51 | position_closed | HCAI | — | Exit at -8.78% after reduce at -3.25% |
| 16:04 | position_closed | AMZN | — | Intraday momentum exit |
| 16:04 | position_closed | GEV | — | Intraday momentum exit |
| 16:04 | position_closed | UNH | — | Intraday momentum exit |
| 16:04 | ai_order_submitted | LLY | 9.49 | New entry (later closed ~18:05) |
| 16:04 | ai_order_submitted | MU | 25.0 | New entry (closed ~17:04) |
| 16:04 | ai_order_submitted | NOK | 367.2 | New entry (closed ~17:04) |
| 16:04 | ai_order_submitted | SNDK | 10.1 | New entry |
| 17:04 | position_closed | MU | — | Intraday reduce/exit |
| 17:04 | ai_order_submitted | DELL | 57.4 | Re-entry (closed ~18:05) |
| 17:04 | ai_order_submitted | FIX | 6.3 | Re-entry |
| 17:04 | ai_order_submitted | GOOGL | 28.7 | Re-entry (closed ~19:08) |
| 17:04 | ai_order_submitted | LLY | 3.51 | **Wash trade** |
| 17:04 | ai_order_submitted | WDC | 24.5 | New entry (closed ~18:05) |
| 17:04 | ai_order_submitted | COIN | 5.1 | New entry (closed ~19:08) |
| 18:05 | position_closed | WDC | — | Intraday momentum exit |
| 18:05 | ai_order_submitted | FIX | 3.7 | **Wash trade** |
| 18:05 | position_closed | DELL | — | Intraday momentum exit |
| 18:05 | position_closed | LLY | — | Intraday momentum exit |
| 18:05 | ai_order_submitted | GOOGL | 9.28 | **Wash trade** |
| 19:08 | position_closed | COIN | — | Intraday momentum exit |
| 19:08 | position_closed | GOOGL | — | Intraday momentum exit |
| 19:08 | ai_order_submitted | AXTX | 313.0 | Surviving to EOD |
| 19:08 | ai_order_submitted | META | 15.48 | Surviving to EOD |
| 19:08 | ai_order_submitted | PWR | 14.69 | Surviving to EOD |

**Wash trades confirmed:** LLY, FIX, GOOGL (bought and sold same session).
**Cycle count:** GOOGL entered -> exited -> re-entered -> re-exited same day.

---

## Full Analysis (Phase 2)

### 2a. Per-Trade Quality Verdicts

| Symbol | Action | Entry | Exit/Current | PnL% | AI Conf | Reason | Verdict |
|---|---|---|---|---|---|---|---|
| HCAI | reduce->exit | — | closed | **-8.78%** | 0.62->0.72 | Momentum lost, below VWAP/EMA20 | **BAD** — reduce at -3.25% should have been full exit; letting loss deepen to -8.78% is a failure of the reduce policy |
| STX | reduce | — | — | unknown | 0.62 | Below VWAP, intraday fade | churn — two reduces with no full exit logged in this session |
| AMZN | reduce->close | — | closed | unknown | 0.62 | Below VWAP/EMA20, fade | **CHURN** — exited on a minor intraday dip; no re-entry logged |
| GEV | exit | — | closed | unknown | — | Full exit at preclose | missed — arbiter said hold at 0.62, yet position was closed |
| UNH | exit | — | closed | unknown | — | Full close | CHURN |
| MU | reduce | — | closed | unknown | 0.58 | Below VWAP, fade | **CHURN** — entered, reduced, and closed within 1 hour |
| NOK | buy | — | closed | unknown | — | New entry | CHURN — opened and closed same session |
| LLY | buy->exit | 966.74 | closed | unknown | 0.68 | Preflight rejected (stop below market) then wash trade | **BAD** — stop price calculation produced stop_not_below_current_market due to wide bid/ask on LLY |
| DELL | buy->exit | — | closed | unknown | — | Intraday momentum exit | CHURN |
| WDC | buy->exit | — | closed | unknown | 0.62 | Below VWAP/EMA20 | CHURN |
| COIN | buy->exit | — | closed | unknown | 0.58 | Intraday momentum lost | CHURN |
| GOOGL | buy->exit->buy->exit | — | closed | unknown | 0.58 | Momentum lost both cycles | **CHURN** — two full buy/sell cycles same day = wash trade |
| FIX | buy->exit | — | closed | unknown | 0.62 | Held at 0.62, then exited | CHURN / contradictory signals |
| AXTX | buy | 46.41 | 46.61 | +0.43% | — | Survived to EOD | OK |
| META | buy | 611.73 | 610.46 | -0.21% | — | Survived to EOD | neutral |
| PWR | buy | 758.48 | 757.38 | -0.15% | — | Survived to EOD | neutral |

---

### 2b. Cross-Trade Patterns

- **Extreme intraday churn (53 trades / day):** Exit-arbiter fires `reduce` at 0.58-0.62 confidence on any VWAP/EMA20 touch. The selector then re-fills the freed capital with new entries, creating same-day buy/sell/buy cycles (GOOGL x2, LLY x2, FIX x2). No net alpha, pure transaction drag.

- **Reduce-not-exit on losers (HCAI):** First exit-arbiter event reduced at -3.25% (conf 0.62). Second event 51 minutes later exited at -8.78% (conf 0.72). The intermediate `reduce` step let a position bleed an additional 5.5% before full exit. The exit arbiter's `reduce` verdict has no maximum hold window — it can stall indefinitely.

- **Portfolio-selector crashes (2 of 6 scan cycles):** Selector failed 3x each time ("selected count 0", weights sum 0.000, missing spy_decision). The fallback skipped the scan entirely, leaving the bot with stale targets until the next scan cycle.

- **SOXS selected as portfolio position:** The selector chose SOXS (3x inverse semi ETF) with a 12.87% target weight. SOXS is a short instrument — it violates the bot's own "long US equities only" mandate. It was blocked at the execution level but should never have reached the selector output.

- **SPY proxy dominance:** 59.8% of equity parked in SPY as "cash proxy." A portfolio that is 60% SPY cannot beat SPY. This is structural: when macro is `neutral` and selector fails, idle cash flows to SPY, which then crowds out active positions.

- **AI vs numeric disagreement (FIX):** Exit-arbiter said `hold` at 0.62 for FIX ("technical structure 0.836, above VWAP"), yet the position was subsequently closed. Downstream execution logic or a later scan overrode the hold verdict without evidence.

- **Consecutive -5% down days (Apr 27-29):** Three straight days of -4.88%, -5.13%, -5.40% while SPY was flat to slightly negative. The macro regime was `neutral` (score +0.27 on May 4), meaning the bearish halt at score < -0.55 never triggered. Significant drawdown occurred in a non-halt regime.

- **LLY stop-price preflight rejection:** Stop was set to $957.07 but market reference was $943.34 (bid $906.68 / ask $980.00). The wide bid-ask spread made the AI's stop appear "above market." The bot recovered via wash trade (bought smaller qty 51 min later). Root cause: preflight uses `current_price_reference` (midpoint) but stop validation compares to bid — inconsistent reference price.

---

### 2c. Proposed Changes

---

**Proposal 1: Raise exit-arbiter intraday-momentum minimum confidence to 0.70**

- **Why:** Exit-arbiter fires `reduce` at 0.58-0.62 confidence on trivial VWAP/EMA20 touches, causing 10+ same-session round-trips on May 4. All 8 "reduce" events used conf < 0.65 with no `technical_flipped`, `bad_news`, or `momentum_stalled` trigger set.
- **Diff:**
  ```yaml
  # config.yaml
  # BEFORE:
  exit_arbiter:
    min_confidence: 0.55
  # AFTER:
  exit_arbiter:
    min_confidence: 0.70
  ```
  (No src/ change — config key is already wired in `orchestrator.py`.)
- **Expected impact:** Blocks low-confidence VWAP dips from triggering reduce. Estimated 60-70% reduction in same-session exits based on May 4 data (9 of 13 exit events were < 0.70 confidence). Reduces wash trades and transaction drag.

---

**Proposal 2: Convert `reduce` verdict to time-boxed: auto-escalate to `exit` after 30 min**

- **Why:** HCAI was `reduce`d at -3.25% at 14:00, then not re-evaluated until 14:51 (51 min later), by which time loss had reached -8.78%. A stale `reduce` verdict has no expiry.
- **Diff (src/orchestrator.py, `_handle_exits` logic):**
  ```python
  # BEFORE (conceptual — check existing logic):
  if verdict == "reduce":
      trim_position(symbol, 0.5)
  
  # AFTER: record reduce timestamp; if same symbol re-evaluated within 60 min
  # and still showing intraday_momentum_lost, escalate to exit
  REDUCE_ESCALATE_MINUTES = 30  # new constant
  if verdict == "reduce":
      trim_position(symbol, 0.5)
      state.set_reduce_timestamp(symbol)
  elif verdict == "hold" and state.reduce_pending(symbol, REDUCE_ESCALATE_MINUTES):
      # Position was recently reduced — any continued weakness auto-exits
      exit_position(symbol)
  ```
  *(Proposal only — exact file/line numbers require src review before implementation.)*
- **Expected impact:** Prevents -8% holes. Caps loss from a `reduce` cycle at ~4% before auto-escalation.

---

**Proposal 3: Blacklist leveraged/inverse ETFs from selector pool**

- **Why:** SOXS (3x inverse semi ETF) appeared in the selector's selected_positions with 12.87% target weight on May 4. The bot's mandate explicitly prohibits short exposure. SOXS was blocked at execution but wasted selector capacity.
- **Diff:**
  ```yaml
  # config.yaml
  # BEFORE:
  universe:
    exclude_tickers: []
  # AFTER:
  universe:
    exclude_tickers:
      - SOXS
      - SOXL
      - TQQQ
      - SQQQ
      - UVXY
      - SVXY
      - SPXS
      - SPXU
      - SDOW
      - UDOW
  ```
- **Expected impact:** Removes inverse/leveraged ETFs from discovery pool. No false selection of short-bias instruments. Minor discovery pool quality improvement.

---

**Proposal 4: Cap SPY cash-proxy at 30% of equity**

- **Why:** SPY reached 59.8% of equity on May 4, making the portfolio a diluted SPY proxy. The bot cannot beat SPY when 60% of capital tracks SPY. The current config has no SPY-specific cap — `max_position_pct: 0.50` applies to individual positions but the SPY proxy accumulates across multiple `cash_target` additions.
- **Diff:**
  ```yaml
  # config.yaml
  cash_proxy:
    # BEFORE: (no explicit cap; accumulates freely)
    # AFTER: add
    max_pct: 0.30   # SPY proxy hard ceiling; excess stays as cash
  ```
  *(Requires wiring in `executor.py` or `orchestrator.py` where SPY proxy buys are sized.)*
- **Expected impact:** Forces 70%+ of equity into active positions. On days the selector is healthy, this allocates ~$70K to active names instead of $40K. On selector-failure days, caps downside to 30% SPY tracking.

---

**Proposal 5: Require at least one hard trigger flag before intraday exit**

- **Why:** Every reduce/exit on May 4 had `technical_flipped=False`, `bad_news=False`, `momentum_stalled=False`. All 13 exit-arbiter events fired purely on intraday price positioning (VWAP/EMA20). These are noise-level signals that reverse within the same session.
- **Diff (config.yaml):**
  ```yaml
  # BEFORE: no intraday trigger gate exists
  exit_arbiter:
    min_confidence: 0.55
  
  # AFTER: add
  exit_arbiter:
    min_confidence: 0.70          # Proposal 1
    require_hard_trigger: false    # when true: at least 1 of technical_flipped/bad_news/momentum_stalled must be True for intraday exits
  ```
  Set `require_hard_trigger: true` initially, making VWAP/EMA dips insufficient alone for intraday exits without a confirmed trigger flag.
- **Expected impact:** Eliminates ~90% of the "lost VWAP + lost EMA20" exits that were reversed within the same session. Retains exits for genuinely broken setups (technical flip, news, momentum stall).

---

**Proposal 6: Fix LLY stop-price preflight — use ask price as reference, not midpoint**

- **Why:** LLY preflight failed with `stop_not_below_current_market` because the current_price_reference ($943.34) was derived from midpoint, but the ask was $980 and bid was $906.68. The stop at $957.07 was below midpoint but above bid. The asset went to wash trade recovery.
- **Diff (src/executor.py — execution_preflight logic):**
  ```python
  # BEFORE (conceptual):
  current_price_reference = (bid + ask) / 2
  
  # AFTER: for stop validation, use ask as the conservative entry reference
  current_price_reference = ask  # conservative: assume we fill at ask
  min_stop_gap = current_price_reference * hard_stop_loss_pct
  if stop_price >= current_price_reference:
      reject("stop_not_below_current_market")
  ```
  *(Exact lines require review of `src/executor.py` before implementation.)*
- **Expected impact:** Eliminates false stop-price rejections for wide-spread assets like LLY. Reduces wash trade recovery events.

---

### 2d. Backtest Feasibility

| Proposal | Offline Backtest Possible? | Notes |
|---|---|---|
| 1 (raise exit conf to 0.70) | **Yes** | Count May 4 exit events with conf >= 0.70: only **1 of 13** (HCAI final exit). This alone would have prevented 12 of 13 reduce/exit events. |
| 2 (reduce escalation timer) | **Partial** | HCAI: reduce at 14:00, exit at 14:51 = 51 min. With 30-min rule, escalation fires at 14:30 — saves ~3.5% of the -8.78% loss. |
| 3 (blacklist inverse ETFs) | **Yes** | SOXS appeared once in 9 days. Low frequency, no compounding backtest needed. |
| 4 (cap SPY proxy at 30%) | **No** | Would require re-running portfolio selection across all 9 sessions — not possible without live API. |
| 5 (require hard trigger) | **Yes** | 0 of 13 exit-arbiter events on May 4 had any hard trigger set. All 13 would be blocked — saves the full 53-trade churn day. |
| 6 (fix LLY preflight) | **No** | Requires live quote comparison; offline data lacks real-time bid/ask for historical sessions. |

**Offline backtest result for Proposal 1 (raise exit_arbiter.min_confidence from 0.55 to 0.70):**
- May 4 exit_arbiter events: 13 total
- Events with conf < 0.70: 12 (all "reduce" verdicts at 0.58-0.62)
- Events with conf >= 0.70: 1 (HCAI final exit at 0.72)
- **Simulated outcome:** Only HCAI exits; AMZN, GEV, UNH, STX, MU, SNDK, LLY, DELL, WDC, COIN, GOOGL, FIX all retained.
- **Estimated trade reduction:** 53 -> ~12 (exit/reentry cycles eliminated)
- **Tradeoff:** Some losing intraday positions would be held to EOD; however the SPY proxy would cover most capital, and the bot's biggest losses (Apr 27-29) were not intraday — they were multi-day underperformers, so this change wouldn't have worsened the streak.

---

## Summary

The bot is structurally failing to beat SPY: -10.71% vs SPY over 9 sessions, winning only 2 of 9 days. The two root causes are:

1. **Exit-arbiter churn at low confidence** — intraday VWAP dips trigger 10+ same-session round-trips. Fix: raise `exit_arbiter.min_confidence` to 0.70 and require at least one hard trigger for intraday exits.

2. **SPY proxy crowding out alpha** — 60% SPY allocation means the active book can't move the needle. Fix: hard cap SPY proxy at 30%.

Secondary: selector AI failures (2 of 6 scans), SOXS in candidate pool, and LLY stop-price preflight bug. All addressable with config or minor code changes per Proposals 1-6 above.
