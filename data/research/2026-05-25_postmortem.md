# Post-Mortem 2026-05-25

> **Memorial Day (market closed).** This post-mortem covers the last live session
> (2026-05-04) and the operational gap that followed, plus structural proposals derived
> from the cumulative data. No new positions opened or closed today.

---

## Data Availability

| Source | Status | Notes |
|---|---|---|
| `2026-05-25_eod.json` | **MISSING** | Market holiday; expected |
| Last `_eod.json` | `2026-05-04_eod.json` | 21 calendar days stale |
| Last intraday scan | `20260504T190848_scan.json` | May 4 ~19:08 UTC |
| Last preclose | `20260504T195545_preclose.json` | May 4 ~19:55 UTC |
| `trades.jsonl` last event | `2026-05-04T19:55:03Z` | exit_learning_metrics (COIN) |
| `decisions.jsonl` last event | `2026-05-04T20:15:04Z` | eod_report |
| Scan files May 5–22 | **NONE** | 14+ trading-day data gap |
| Data gap flagged | 3× no-data reviews | 5/7, 5/13, 5/22 |

**Operational alert**: The bot has produced zero artifacts since May 4. This gap
has been flagged in three consecutive daily reviews (5/7, 5/13, 5/22) with no
resolution visible in the repo. Until the scheduler/pipeline is confirmed live and
writing to this repo, all strategy analysis is based on the last session only.

---

## Performance — Last Session (2026-05-04)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily alpha | **-1.44%** |
| Ending equity | $99,850 |
| Trades today | 53 events (15 buys, 11 closes, 3 wash-trade recoveries) |
| Macro regime | neutral (score 0.27, VIX 27.83) |

---

## Rolling Benchmark (Apr 22 – May 4, all available eod.json)

| Date | Portfolio | SPY | Alpha | Equity |
|---|---|---|---|---|
| 2026-04-22 | +0.00% | +1.01% | -1.01% | $99,627 |
| 2026-04-23 | +1.56% | -0.39% | **+1.95%** | $101,208 |
| 2026-04-24 | -0.81% | +0.77% | -1.58% | $99,343 |
| 2026-04-27 | **-4.88%** | +0.17% | **-5.05%** | $96,448 |
| 2026-04-28 | **-5.13%** | -0.49% | **-4.64%** | $96,867 |
| 2026-04-29 | **-5.40%** | -0.01% | **-5.39%** | $93,999 |
| 2026-04-30 | -2.67% | +0.96% | -3.63% | $95,786 |
| 2026-05-01 | +1.82% | +0.29% | +1.53% | $101,101 |
| 2026-05-04 | -1.80% | -0.36% | -1.44% | $99,850 |
| **Cumulative** | **-16.31%** | **+1.95%** | **-18.26%** | — |

**The bot is -18.26% behind SPY over 9 trading days.** The April 27-29 cluster
(-15.41% combined portfolio return over 3 days vs SPY -0.33%) is the primary driver.
Only two days out of nine generated positive alpha.

---

## Positions at Close (May 4 EOD)

| Symbol | Side | Avg Entry | Current | P&L% | Mkt Value | Weight |
|---|---|---|---|---|---|---|
| SPY (proxy) | LONG | $717.52 | $718.03 | +0.07% | $59,696 | ~60% |
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,589 | ~15% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,130 | ~11% |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448 | ~9% |

P&L computed as `(current - avg_entry) / avg_entry` per project rule.
SPY weight ~60% is correct — cash-proxy parking of idle capital.

---

## Trades — May 4 (Last Session)

| Time (UTC) | Event | Symbol | Side | Qty | Entry Ref | Stop | Outcome |
|---|---|---|---|---|---|---|---|
| 16:04:41 | BUY | LLY | LONG | 9.49 | $961.30 | $951.69 | Exit same session |
| 16:04:44 | BUY | MU | LONG | 25.0 | $583.49 | $577.65 | Exit same session |
| 16:04:50 | BUY | NOK | LONG | 367.2 | $13.38 | $13.24 | Exit same session |
| 16:04:55 | BUY | SNDK | LONG | 10.1 | $1,250.12 | $1,237.62 | Exit same session |
| 17:04:27 | BUY | DELL | LONG | 57.4 | $209.91 | $207.81 | Exit @$210.94 |
| 17:04:29 | BUY | FIX | LONG | 6.3 | $1,884.10 | $1,865.26 | WASH TRADE on stop |
| 17:04:31 | BUY | GOOGL | LONG | 28.7 | $382.82 | $378.99 | WASH TRADE on stop |
| 17:04:35 | BUY | LLY | LONG | 3.51 | $962.24 | $952.61 | WASH TRADE on stop |
| 17:04:39 | BUY | WDC | LONG | 24.5 | $442.28 | $437.86 | Exit @$440.06 |
| 17:04:56 | BUY | COIN | LONG | 5.1 | $204.82 | $202.77 | Exit @$202.68 |
| 18:05:06 | BUY (add) | FIX | LONG | 3.7 | $1,900.24 | $1,881.24 | Verifier dust-swept |
| 18:05:26 | BUY (add) | GOOGL | LONG | 9.3 | $383.94 | $380.10 | Exit same session |
| 19:08:31 | BUY | AXTX | LONG | 313 | $45.80 | $45.34 | **Held overnight** |
| 19:08:34 | BUY | META | LONG | 15.5 | $612.19 | $606.07 | **Held overnight** |
| 19:08:36 | BUY | PWR | LONG | 14.7 | $756.10 | $748.54 | **Held overnight** |

**Also closed**: HCAI (exit-arbiter conf=0.72, down -8.78%), AMZN, GEV, UNH, MU,
WDC, DELL, COIN, GOOGL, FIX (verifier dust), LLY (verifier dust).

---

## Full Analysis

### Per-Trade Quality Assessment

| Symbol | Verdict | Notes |
|---|---|---|
| AXTX | **hold** | Small biotech, +0.43% as of EOD. Still held. Reasonable starter position. |
| META | **ok** | Near flat (-0.21%) at EOD. Held overnight. Sound thesis. |
| PWR | **ok** | Near flat (-0.15%) at EOD. Held overnight. AI power theme. |
| LLY (16:04) | **churn** | Bought, then exit-arbiter closed same session. Net zero signal after fees. |
| MU | **churn** | Bought, exited same session. Bearish EMA on close. |
| NOK | **churn** | Bought, exited same session. Low-conviction name. |
| SNDK | **missed** | Selected (target 12.28%) but execution failed — `insufficient_confirmed_cash`. Would have been held. |
| DELL | **churn** | Bought at 17:04, exited at 18:05 (exit_learning: $210.94 → missed +$0.29/sh). |
| WDC | **premature exit** | Exited at $440.06; 60-min price was $444.14 (+$100 missed). |
| COIN | **ok** | Exited at $202.68; 60-min price $202.45 (avoided -$1.17). Correct. |
| GOOGL | **churn** | Two round-trips (16:00 entry, 17:04 top-up). Exit same session. |
| FIX | **bad** | Bought at $1,884, added at $1,900 (19% weight), arbiter wanted EXIT at 63 min old but `fresh_exit_cooldown` blocked it (conf 0.80 < 0.85 min). Verifier dust-swept at EOD. Net: paid slippage both directions. |
| HCAI | **bad** | Down -8.78% at exit. Exit-arbiter conf 0.72 (≥ 0.55 threshold met). Correct to exit, but this is a -8.78% realized loss — significant single-name damage. |
| SOXS (selected, not filled) | **violation** | AI selected SOXS (3× inverse semiconductor bear ETF) at 9.01% weight. This violates the "Long US equities only" mandate from CLAUDE.md. Execution rejected (stop_not_below_current_market) — lucky save, not a design safeguard. |
| LLY (19:08 scan, not filled) | **stop bug** | Execution preflight rejected: stop ($957.07) above current market ($943.34). Stale quote at AI decision time caused an invalid stop. |

---

### Cross-Trade Patterns

- **Catastrophic April cluster (4/27–4/29, -15.4%)**: Three consecutive sessions of >4.5% loss each while SPY was essentially flat. No macro halt triggered (bearish_halt_score = -0.55; macro score never crossed this threshold per available data). The portfolio was likely concentrated in AI/data-center names (GICS overlap) during a sector rotation event. The `diversification.symbol_overrides` `ai_data_center` bucket was added after this, suggesting it was a post-mortem action.

- **Same-session round trips (FIX, GOOGL, LLY, MU, NOK, DELL)**: 6 of 15 buys were exited within the same session. This contributes slippage cost (~2× spread) with no alpha. The selector chose these names, the AI approved entries, and then subsequent scans reversed those decisions before close.

- **Wash trades (FIX, GOOGL, LLY)**: Three Alpaca wash-trade rejections (error 40310000). Trigger: a new buy order was submitted while the prior session's stop-loss order for the same symbol was still live. The `wash_trade_recovery` mechanism retried and filled, but this adds latency and increases slippage risk.

- **SOXS in selector output**: The portfolio-selector (Opus) chose a 3× leveraged inverse ETF at 9% weight. The mandate says "Long US equities only — no shorts, no crypto." SOXS is technically a long position but is a short-directional instrument. Execution happened to fail (bad stop placement), but the selector should never emit it. No filter exists.

- **FIX fresh_exit_cooldown misfire**: FIX was bought at 17:04 (added to 19% of book) then the arbiter wanted EXIT at 18:05 (conf 0.80). The cooldown (120 min, requires 0.85 min confidence for early exit) blocked it. The position was eventually verifier dust-swept. The cooldown is preventing correct AI judgment on momentum reversals.

- **HCAI -8.78% single-name drawdown**: HCAI is not in the seed watchlist; it entered via discovery. A single position losing -8.78% before exit represents ~$880 at 10% weight — exceeding 0.5% equity risk/trade budget. Stop-loss at 1% should have fired earlier (implies the protective stop was not correctly placed or filled).

- **SPY cash-proxy churn**: SPY was bought and sold across sessions as a cash proxy. On May 4, SPY was not in the EOD held list yet ended up as the dominant position via subsequent scans. This is by design but the 60% weight in SPY proxy effectively makes the bot track SPY with downside drag from the equity picks.

- **52-trade day vs 7-trade days**: May 4 (53 events) vs Apr 22 (7 events). High-turnover days systematically underperform — the selector/arbiter is unstable across hourly scans, generating entry→exit→re-entry patterns with slippage at each turn.

---

### Proposed Changes

#### Proposal 1: Block inverse/leveraged ETFs from selector output

**Why**: The selector chose SOXS (3× bear ETF) at 9% weight on May 4, directly
violating the "Long US equities only" mandate. The execution failure was accidental,
not a designed guardrail.

**Diff** (config.yaml):
```yaml
# Before (no filter exists)
universe:
  exclude_tickers: []

# After
universe:
  exclude_tickers: [SOXS, SOXL, TQQQ, SQQQ, UVXY, SVXY, SPXS, SPXU, SDOW, UDOW]
  # Any ticker whose name contains "Bear", "Bull 3X", "Ultra Short" should also
  # be caught in discovery.py with: if 'bear' in name.lower() or '3x' in name.lower(): skip
```

**Expected impact**: Prevents mandate violation. No alpha cost — the mandate already
prohibits these. The execution preflight will no longer be a lucky catch.

---

#### Proposal 2: Reduce `fresh_exit_cooldown` thresholds

**Why**: The cooldown (120 min, requires conf ≥ 0.85 to override) blocked a correct
AI exit on FIX (conf 0.80) that was later confirmed right. The exit_arbiter floor is
0.55 — the cooldown is over-protecting entries at a higher bar than the general exit
gate, creating asymmetric inertia that favors holding losers.

**Diff** (config.yaml — new key, requires src/orchestrator.py to read it):
```yaml
# Before (hardcoded in orchestrator.py, not in config)
# fresh_exit_cooldown_minutes: 120
# fresh_exit_cooldown_min_confidence: 0.85

# After
exit_arbiter:
  min_confidence: 0.55          # unchanged
  fresh_exit_cooldown_minutes: 60     # reduce 120 → 60 min
  fresh_exit_cooldown_min_confidence: 0.70  # reduce 0.85 → 0.70 (just above general floor)
```

**Expected impact**: Allows AI to exit within 60 min if conviction is ≥ 0.70. Reduces
same-session round-trip losses on momentum reversals like FIX. Estimated savings:
~1-2 trades/day × ~$50 slippage = ~$50-100/day on active sessions.

---

#### Proposal 3: Add intraday turnover cap (max round-trips per session)

**Why**: May 4 had 6 same-session round-trips across 15 buys. Each round-trip costs
~2× spread (buy slippage + sell slippage). With 6 symbols at avg ~$12K notional,
slippage at 0.05% each leg = ~$72 direct cost, plus market impact. A hard cap at
3 round-trips per session would have preserved 3 of those positions or skipped
the entries.

**Diff** (config.yaml — new key):
```yaml
# Before (no limit)
rebalance:
  # ... existing keys ...

# After
rebalance:
  max_same_session_round_trips: 3   # if symbol was opened AND closed this session, count as 1 trip
```

**Expected impact**: Caps churn-driven slippage. Estimated: saves 3-4 unnecessary
trades/session on high-turnover days (~$30-50/session).

---

#### Proposal 4: Portfolio drawdown circuit breaker

**Why**: The April 27-29 cluster lost -15.4% in 3 days while the macro score (0.27)
never triggered the halt (threshold -0.55). The macro module only looks at SPY trend
+ VIX + breadth — it doesn't incorporate portfolio drawdown velocity. A portfolio-aware
circuit breaker would have halted new entries on day 2 of the cluster.

**Diff** (config.yaml — new key):
```yaml
# Before
macro:
  bearish_halt_score: -0.55

# After
macro:
  bearish_halt_score: -0.55
  drawdown_halt_3d_pct: -0.08     # halt new entries if portfolio 3-day return < -8%
  drawdown_halt_resume_days: 2    # resume after 2 sessions without new -3% single-day
```

**Expected impact**: Would have halted new entries on April 28 (after April 27's
-4.88%). Could have prevented ~$5,000 of the April 28-29 losses. Exits still run.

---

#### Proposal 5: Clamp stale-quote stops before preflight reject

**Why**: LLY (19:08 scan) was rejected by execution preflight because the AI-computed
stop ($957.07) was above the current market price ($943.34) — the AI used a stale
quote. The rejection was correct, but the LLY entry was lost entirely. A pre-submit
validation that recomputes stop = `min(ai_stop, current_price * 0.99)` would have
allowed a valid order.

**Diff** (src/executor.py — proposal only, do not implement here):
```python
# Before (in execution_preflight):
# if stop_price >= current_price_reference: reject

# After: clamp stop to 1% below live quote, log a warning, then allow
if stop_price >= current_price_reference:
    clamped_stop = round(current_price_reference * (1 - hard_stop_loss_pct), 2)
    logger.warning(f"stop {stop_price} >= market {current_price_reference}; "
                   f"clamping to {clamped_stop}")
    stop_price = clamped_stop
```

**Expected impact**: Recovers valid entries rejected by stale-quote stop placement.
No additional risk — stop is still at ≤1% below live market. Estimated: recovers
1-2 missed entries per week.

---

#### Proposal 6: Cancel open stops before re-entering same symbol

**Why**: Three wash-trade errors (LLY, FIX, GOOGL) on May 4 occurred because the
bot submitted a new buy order while a prior stop-sell order for the same symbol was
still pending. The `execution.cancel_open_orders_before_sell` flag already cancels
before sells — the same logic is needed before re-buys.

**Diff** (config.yaml — extend existing flag):
```yaml
# Before
execution:
  cancel_open_orders_before_sell: true

# After
execution:
  cancel_open_orders_before_sell: true
  cancel_stop_orders_before_rebuy: true   # cancel open stop-loss orders before re-entering same symbol
```

**Expected impact**: Eliminates wash-trade rejections and the associated
`wash_trade_recovery` retry latency. Ensures stop-loss state is clean before
re-entry. No safety degradation — the new entry places a fresh stop immediately.

---

### Backtests

No offline backtest is feasible for Proposals 1, 3, 4, 5, 6 — they require
intraday fill data (not in the journal files). The journal contains final
positions/exits but not per-scan notional flows needed to replay alternatives.

**Proposal 2 (cooldown)**: from `decisions.jsonl`, `fresh_exit_guard_skipped`
events on May 4: 1 event (FIX, conf 0.80, blocked at 0.85). If the threshold had
been 0.70, this exit would have fired ~63 min into the position. FIX was verifier
dust-swept at EOD anyway — net impact ~0 for May 4. However, the pattern of
buying FIX at 19% weight and then wanting out within an hour is the real signal
(see Proposal 3).

---

### Primary Operational Issue (unchanged from 5/7, 5/13, 5/22)

> **The bot has not written any artifacts to this repo since 2026-05-04.**
> Fourteen-plus trading days of live paper-account activity (if any) are invisible
> from this repo. No strategy analysis can be validated until the pipeline is confirmed
> running and committing to the correct path.

---

*Generated by post-mortem-bot on 2026-05-25 (Memorial Day). Based solely on
`data/research/` and `data/journal/` as committed. No Alpaca / Telegram / yfinance
calls made.*
