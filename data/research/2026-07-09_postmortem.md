# Post-Mortem 2026-07-09

## Data Availability

**Critical: No live trading data exists for 2026-07-09 (or any date 2026-05-05 through 2026-07-09).**

The bot has produced zero artifacts for ~45 trading days / 66 calendar days. The newest data on disk is `2026-05-04_eod.json`. This post-mortem grades the **last active session (2026-05-04)** and documents the operational outage.

| Source | Newest entry | Status |
|---|---|---|
| `_eod.json` | `2026-05-04_eod.json` | **Frozen** |
| Last intraday scan | `20260504T190848_scan.json` | **Frozen** |
| `trades.jsonl` last event | `2026-05-04T19:55:03Z` (204 lines) | **Frozen** |
| `decisions.jsonl` last event | `2026-05-04T20:15:04Z` (1556 lines) | **Frozen** |
| Today's review | `2026-07-09_daily_review.md` | No-data (9th consecutive) |

---

## Performance — Last Active Session (2026-05-04) vs Prior Days

| Date | Portfolio Daily | SPY Daily | Alpha |
|---|---|---|---|
| 2026-04-22 | 0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.58% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | -5.13% | -0.49% | -4.64% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| **2026-05-04** | **-1.80%** | **-0.36%** | **-1.44%** |

**Cumulative (9 sessions, 2026-04-22 → 2026-05-04):**
- Portfolio: **-16.3%**
- SPY: **+1.95%**
- Alpha: **-18.26%**
- Win days vs SPY: **2 / 9**

---

## Positions at Close (2026-05-04 EOD)

| Symbol | Side | Qty | Avg Entry | Last Price | P&L % |
|---|---|---|---|---|---|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% |

**Equity:** $99,850 | **Cash:** $4,987 (5.0%) | **Positions:** 4

---

## Trades — 2026-05-04 (Last Active Day, 53 total per EOD)

| Symbol | Action | Qty | Fill Price | AI Verdict | Conf | Outcome | Note |
|---|---|---|---|---|---|---|---|
| COIN | EXIT | 66.90 | $203.45 | EXIT | 0.80 | Filled | Earnings in 3 days, momentum 0 |
| GOOGL | EXIT | 37.96 | $382.77 | EXIT | 0.80 | Filled | Momentum 0, below EMA20, fading |
| AXTX | BUY | 313.0 | $46.41 | BUY | 0.88 | Filled | Momentum 100, breaking_out, vol 2.79× |
| META | BUY | 15.48 | $611.73 | BUY | 0.65 | Filled | Sector diversification, above VWAP |
| PWR | BUY | 14.69 | $758.48 | BUY | 0.72 | Filled | AI-data-center peer leader |
| FIX | EXIT | — | — | EXIT | 0.80 | **BLOCKED** | Fresh-exit cooldown (entered 63 min prior) |
| LLY | BUY | — | — | BUY | 0.68 | **REJECTED** | Stop $957.07 not below market $943.34 |
| SNDK | BUY | — | — | BUY | 0.78 | **SKIPPED** | Insufficient confirmed cash |
| SOXS | BUY | — | — | BUY | 0.62 | **REJECTED** | Inverse ETF — violates long-only constraint |

---

## Full Trade Ledger — 2026-05-04 (All 6 Scans)

43 execution events across 6 scans. Fills marked ✓; skips/blocks marked with reason.

| Time (UTC) | Symbol | Side | Action | Conf | Fill? | Note |
|---|---|---|---|---|---|---|
| 15:13 | SNDK | SELL | EXIT 0.85 | 0.85 | ✗ unknown | **Sold winner at +10.07% unrealized to "fund better opportunities" → repurchased at 16:05** |
| 15:13 | STX | SELL | EXIT | 0.90 | ✗ unknown | Weak momentum, below EMA20 |
| 15:13 | AMZN | BUY | BUY | 0.90 | ✗ unknown | Momentum 100, pressing day high |
| 15:13 | COIN | BUY | BUY | 0.83 | ✗ unknown | Financials sector leader, momentum 97 |
| 15:13 | GEV | BUY | BUY | 0.87 | ✗ unknown | AI datacenter peer leader, momentum 97 |
| 15:13 | MU | BUY | BUY | 0.82 | ✗ unknown | Memory peer leader |
| 15:13 | UNH | BUY | BUY | 0.75 | ✗ unknown | Healthcare leader, momentum 91 |
| 15:18 | COIN | SELL | REDUCE | 0.65 | ✗ unknown | Earnings in 3 days → trim |
| 15:18 | AMZN | BUY | INCREASE | 0.90 | ✗ unknown | Perfect momentum, continuation |
| 15:18 | META | BUY | BUY | 0.82 | ✗ unknown | Breaking out, perfect momentum |
| 15:18 | MU | BUY | BUY | 0.85 | ✗ unknown | Memory leader, continuation |
| 15:18 | UNH | BUY | BUY | 0.80 | ✗ unknown | Perfect momentum, breaking out |
| 16:05 | AMZN | SELL | EXIT | 0.85 | ✓ | **Fading momentum, below VWAP — 52 min after BUY** |
| 16:05 | GEV | SELL | EXIT | 0.85 | ✓ | **Weak momentum — 52 min after BUY** |
| 16:05 | UNH | SELL | EXIT | 0.80 | ✓ | **Exited for LLY — 52 min after BUY** |
| 16:05 | COIN | BUY | INCREASE | 0.80 | ✗ preflight_rejected | — |
| 16:05 | LLY | BUY | BUY | 0.72 | ✓ | Healthcare leader |
| 16:05 | MU | BUY | INCREASE | 0.90 | ✓ | Perfect momentum continuation |
| 16:05 | NOK | BUY | BUY | 0.68 | ✓ | Low conviction (0.68) entry |
| 16:05 | SNDK | BUY | BUY | 0.75 | ✓ | Repurchased SNDK sold 30 min earlier at +10% |
| 17:04 | MU | SELL | EXIT | 0.85 | ✓ | **Bearish EMA, peer outranked — 59 min after INCREASE** |
| 17:04 | DELL | BUY | BUY | 0.80 | ✓ | IT sector leader |
| 17:04 | FIX | BUY | BUY | 0.82 | ✓ | AI datacenter peer leader, momentum 100 |
| 17:04 | GOOGL | BUY | BUY | 0.72 | ✓ | Comm Services leader |
| 17:04 | LLY | BUY | INCREASE | 0.65 | ✓ | Held, cooldown still active |
| 17:04 | WDC | BUY | BUY | 0.75 | ✓ | Memory peer, outranked MU |
| 18:05 | DELL | SELL | EXIT | 0.75 | ✗ fresh_exit_cooldown | **61 min after BUY; blocked by cooldown** |
| 18:05 | LLY | SELL | EXIT | 0.80 | ✗ fresh_exit_cooldown | **Blocked by cooldown** |
| 18:05 | WDC | SELL | EXIT | 0.92 | ✓ | Gap only, bearish EMA, 60 min hold |
| 18:05 | CUE | BUY | BUY | 0.78 | ✗ preflight_rejected | — |
| 18:05 | FIX | BUY | INCREASE | 0.88 | ✓ | Momentum 100, breaking out |
| 18:05 | GOOGL | BUY | INCREASE | 0.72 | ✗ insufficient_cash | — |
| 18:05 | PWR | BUY | BUY | 0.75 | ✗ preflight_rejected | — |
| 18:05 | RBLX | BUY | BUY | 0.73 | ✗ insufficient_cash | — |
| 19:08 | COIN | SELL | EXIT | 0.80 | ✓ | Momentum 0, earnings in 3 days |
| 19:08 | FIX | SELL | EXIT | 0.80 | ✗ fresh_exit_cooldown | **63 min after INCREASE; blocked by cooldown** |
| 19:08 | GOOGL | SELL | EXIT | 0.80 | ✓ | Momentum 0, below EMA20 |
| 19:08 | AXTX | BUY | BUY | 0.88 | ✓ | Momentum 100, breaking_out |
| 19:08 | LLY | BUY | BUY | 0.68 | ✗ preflight_rejected | Stop above market price |
| 19:08 | META | BUY | BUY | 0.65 | ✓ | Sector diversification |
| 19:08 | PWR | BUY | BUY | 0.72 | ✓ | Datacenter peer leader |
| 19:08 | SNDK | BUY | BUY | 0.78 | ✗ insufficient_cash | 2nd re-entry attempt for SNDK |
| 19:08 | SOXS | BUY | BUY | 0.62 | ✗ preflight_rejected | **Inverse 3× ETF — violates long-only hard rule** |

**Churned symbols (bought AND sold same day):** AMZN, COIN, DELL, FIX, GEV, GOOGL, LLY, MU, SNDK, UNH, WDC — **11 of 19 symbols touched**

---

## Cross-Trade Patterns

- **Extreme intraday churn:** 43 execution events across 6 scans in one day. 11/19 symbols were both bought and sold within the same session, some within 52 minutes of entry (AMZN BUY→EXIT, GEV BUY→EXIT, UNH BUY→EXIT). This is the dominant P&L drag — round-trip slippage and spread on every churn cycle.

- **Premature exit on winners:** SNDK sold at **+10.07% unrealized** at 15:13 "to fund better opportunities." It was immediately repurchased at 16:05 (same day, same price tier). This is pure friction with no realized benefit.

- **AI vs numeric alignment — poor signal quality:** The AI was flipping verdicts scan-to-scan. MU went BUY (15:13) → BUY (15:18) → INCREASE (16:05) → EXIT (17:04) within 2 hours. GOOGL went BUY (17:04) → INCREASE attempted (18:05) → EXIT (19:08) within 2h4m. These back-to-back reversals indicate the AI is responding to intraday noise rather than any structural edge.

- **No macro-driven caution:** Macro score was 0.27 (neutral) all day — not a bearish halt day — yet the portfolio churned completely. On the worst loss days in the 9-session window (4/27: -4.88%, 4/28: -5.13%, 4/29: -5.40%), the bot appears to have been actively trading into a falling market without a regime brake.

- **SOXS selection (inverse ETF — hard constraint breach):** The portfolio-selector nominated SOXS (3× inverse semiconductor ETF) as a BUY at confidence 0.62. SOXS is a short-direction levered product. This is a direct violation of the "long US equities only, no shorts" hard rule in CLAUDE.md. The execution preflight caught it (rejected), but the selector should never have nominated it. The AI was likely picking it because semiconductors were declining, making SOXS look like a "momentum" play without recognizing it as an inverse product.

- **Cash pre-allocation failures:** SNDK (19:08), GOOGL (18:05), and RBLX (18:05) were all skipped for "insufficient confirmed cash" after the system had already executed multiple buys and scheduled more. The selector is planning buys without accounting for confirmed fills reducing available capital in real time.

- **Stop-price miscalculation:** LLY was rejected at 19:08 because the AI set a stop at $957.07 while the reference price was $943.34 — the stop was **above the current market**, which would trigger immediately on entry. This is a systematic AI calibration error (AI quoting stale or bid-side prices for entry, stop set relative to stale quote).

- **fresh_exit_cooldown absorbing legitimate exits:** FIX was validly targeted for exit (momentum fading, below EMA20) at 19:08 with 0.80 confidence, but was blocked because it had been added 63 minutes prior. However, FIX had also been blocked at 18:05 (40 min earlier). The cooldown is protecting a position the AI wants to exit twice in a row — an edge case where the protection works against the strategy.

- **SPY cash-proxy churn:** SPY was held at $59,696 (60% of equity) going into 5/4 EOD, despite the bot executing 43 sell/buy events intraday. The SPY holding is the cash proxy — the bot is cycling through equities while maintaining a 60% SPY floor. With `spy_target_pct: 0.0` in the last scan, the selector had planned to reduce SPY to 0, but cash constraints prevented the buys needed to deploy that capital.

- **4/27–4/29 drawdown (-15.4% cumulative):** The three-day wipe-out on near-flat SPY days is the biggest unanswered question. The journal shows no artifact from those days to diagnose directly, but the pattern (bot concentrated in high-beta AI-datacenter names vs a flat-to-slightly-positive market) matches the ai_data_center theme overconcentration risk documented in `config.yaml`'s `diversification.symbol_overrides`. AXTX, FIX, GEV, PWR, and SNDK are all in the same `ai_data_center` theme bucket; on a bad day for that theme, the entire book moves together.

---

## Proposed Changes

### P1 — Hard Blocklist for Inverse and Leveraged ETFs

**Why:** The portfolio-selector nominated SOXS (3× inverse semiconductor ETF) as a BUY, violating the documented "long US equities only" constraint. The execution preflight caught it, but only by coincidence (stop_not_below_market). The selector has no explicit inverse-ETF filter.

**Diff — `src/discovery.py` (eligibility screen, add to asset filter):**
```python
# BEFORE (no inverse ETF filter in eligibility check)
if not asset.tradable or asset.status != 'active':
    return False

# AFTER — add after existing asset checks
INVERSE_LEVERAGED_PREFIXES = ('SOXS','SQQQ','SPXS','SPXU','SDOW','UVXY','SVXY',
                              'SH','SDS','PSQ','QID','DOG','TWM','MZZ','SKF',
                              'FAZ','TZA','RWM','SRTY','SOXL',)  # SOXL too (3× long, not suitable)
INVERSE_LEVERAGED_KEYWORDS = ('-3X','-2X','ULTRASHORT','ULTRAPRO SHORT','INVERSE')
if symbol in INVERSE_LEVERAGED_PREFIXES:
    return False
if any(kw in (name or '').upper() for kw in INVERSE_LEVERAGED_KEYWORDS):
    return False
```

**Expected impact:** Eliminates an entire class of hard-constraint violations at the discovery layer before AI cost is incurred. Zero false-positive risk on the named prefixes.

---

### P2 — Minimum-Hold Timer Before Any Exit (Except Stop-Loss)

**Why:** AMZN, GEV, and UNH were entered and exited within 52 minutes on 5/4. DELL was blocked by cooldown at 61 min. WDC was exited at 60 min. The `fresh_exit_cooldown` already exists but requires confidence ≥ 0.85 to override; exits at 0.80 are just blocked, not prevented. The deeper issue is the selector replacing the entire portfolio every 1–2 scans.

**Diff — `config.yaml`:**
```yaml
# BEFORE
rebalance:
  ...
  winner_profit_threshold: 0.03    # don't trim if unrealized pnl > +3% AND tech still positive

# AFTER
rebalance:
  ...
  winner_profit_threshold: 0.05    # raise from 3% to 5%: don't trim if unrealized pnl > +5% AND tech positive
  min_hold_minutes: 240            # NEW: block any non-stop-loss exit for first 4h after fill
```

And in `src/orchestrator.py`, enforce min_hold_minutes before passing symbols to exit evaluation:
```python
# BEFORE — exits evaluated on all positions
exit_candidates = [p for p in held_positions if tech_score(p) < exit_stall_threshold]

# AFTER — gate by fill age
min_hold_s = cfg.rebalance.get('min_hold_minutes', 0) * 60
exit_candidates = [
    p for p in held_positions
    if tech_score(p) < exit_stall_threshold
    and (utcnow() - fill_timestamp(p)).total_seconds() >= min_hold_s
]
```

**Expected impact:** Eliminates intraday round-trips. On 5/4 alone, 3 confirmed round-trips (AMZN, GEV, UNH, WDC) would have been blocked. Estimated savings: 4–6 slippage events × ~$500–2000 notional each ≈ $500–1000 friction/day on active days. Does not affect stop-loss triggers.

---

### P3 — Selector Inertia / Jaccard Similarity Floor

**Why:** The portfolio turned over 11/19 symbols in a single day. The selector has `no incumbent bias`, which is correct for long-term quality but allows the AI to rotate 100% of the book every scan. On 5/4 the bot went from {SNDK, STX} → {AMZN, COIN, GEV, MU, UNH} → {LLY, MU, NOK, SNDK} → {DELL, FIX, GOOGL, LLY, WDC} → {FIX, GOOGL} → {AXTX, META, PWR, SPY} in 6 scans.

**Diff — `config.yaml`:**
```yaml
# BEFORE
selector:
  enabled: true
  min_positions: 3
  max_positions: 6
  ...

# AFTER
selector:
  enabled: true
  min_positions: 3
  max_positions: 6
  min_carry_over_positions: 2      # NEW: at least 2 held symbols must survive each scan
  max_new_entries_per_scan: 2      # NEW: cap fresh BUYs per scan at 2 (down from unlimited)
```

**Expected impact:** Reduces portfolio turnover by ~60%. Forces the selector to hold its best existing positions rather than replacing them with marginally higher-scoring alternatives that turn out to be noise. Will sacrifice some short-term momentum chasing, which is currently losing alpha.

---

### P4 — Winner Protection: Block Exits Above +5% Unrealized

**Why:** SNDK was exited at +10.07% unrealized to "fund better opportunities" and immediately repurchased. This is the clearest data point: selling a +10% winner costs the realized gain, triggers a new entry at market (slippage), and loses the embedded profit if the repurchase is at or above the exit price.

**Diff — `config.yaml`:**
```yaml
# BEFORE
rebalance:
  winner_profit_threshold: 0.03    # don't trim if unrealized pnl > +3% AND tech still positive

# AFTER
rebalance:
  winner_profit_threshold: 0.05    # raised to 5%
```

And add to `src/orchestrator.py` exit guard:
```python
# BEFORE — no winner protection in exit path
if exit_arbiter_verdict.action == 'EXIT':
    execute_exit(symbol)

# AFTER — block full exits on large winners unless AI is very confident
winner_exit_min_confidence = 0.90
if exit_arbiter_verdict.action == 'EXIT':
    unrealized_pct = position.unrealized_pct
    if unrealized_pct > cfg.rebalance.winner_profit_threshold:
        if exit_arbiter_verdict.confidence < winner_exit_min_confidence:
            log.warning(f'{symbol}: winner exit blocked (pnl={unrealized_pct:.1%}, conf={exit_arbiter_verdict.confidence:.2f} < {winner_exit_min_confidence})')
            continue
    execute_exit(symbol)
```

**Expected impact:** Directly prevents the SNDK pattern. Any position with > 5% unrealized gain requires ≥ 0.90 AI confidence to exit. Zero impact on stop-loss exits (those bypass the exit arbiter path).

---

### P5 — AI Stop-Loss Sanity Check (Preflight Pre-Check)

**Why:** LLY was rejected by execution preflight because the AI set a stop at $957.07 when the current market was $943.34 — stop above current price means immediate trigger on entry. The preflight caught it, but the AI spent tokens generating a rejected order. A pre-validation before submitting to preflight would fail fast and allow the AI to re-estimate.

**Diff — `src/risk.py` (or wherever stop_loss is computed from AI output):**
```python
# BEFORE — pass AI stop directly to preflight
stop_price = ai_result.get('ai_stop_loss')

# AFTER — sanity check before preflight
stop_price = ai_result.get('ai_stop_loss')
if stop_price and entry_price:
    if stop_price >= entry_price * 0.995:  # stop is within 0.5% above entry — almost certainly a quote error
        log.warning(f'{symbol}: AI stop {stop_price} too close to or above entry {entry_price}; recomputing from ATR')
        stop_price = entry_price * (1 - cfg.risk.hard_stop_loss_pct)
```

**Expected impact:** Eliminates LLY-class preflight rejections. Allows the position to enter with a valid ATR-derived stop rather than being skipped entirely. Low risk — the fallback is the existing hard_stop_loss_pct logic.

---

### P6 — Cash Pre-Allocation Sequencing (Fix "Insufficient Cash" Pattern)

**Why:** SNDK, GOOGL, and RBLX were skipped for insufficient cash at 18:05–19:08 after the bot had already committed capital to other buys in the same scan. The sequential_cash_check already exists for overnight, but the intraday selector path doesn't fully account for multi-buy cash depletion before submitting all orders.

**Diff — `src/orchestrator.py` (rebalance execution loop):**
```python
# BEFORE — sells are batched, then buys are batched separately
execute_sells(sell_actions)
execute_buys(buy_actions)

# AFTER — interleave sells and buys, tracking running cash balance
available_cash = current_cash
for action in sorted(all_actions, key=lambda a: (a.side == 'buy', a.priority)):
    if action.side == 'sell':
        fill = execute_sell(action)
        available_cash += fill.proceeds
    else:  # buy
        if available_cash >= action.notional:
            fill = execute_buy(action)
            available_cash -= fill.cost
        else:
            log.warning(f'{action.symbol}: skipped buy — insufficient cash ({available_cash:.0f} < {action.notional:.0f})')
```

**Expected impact:** Eliminates the "insufficient cash" skip pattern. Ensures sells settle before buys of equivalent size are submitted. Prevents the scenario where 3 buys are planned but only 1 can execute because sells haven't cleared.

---

## Backtests

**P2 (min-hold timer) — offline backtest using journal data:**

Using `decisions.jsonl`: 11 churned symbols on 5/4 with fills. Approximate round-trip friction per churned symbol: bid-ask spread (~0.05% each way) × 2 + market impact (~0.02%) = ~0.12% per round-trip. Average notional per position ~$10K. Estimated friction per round-trip: ~$12. 11 churn cycles × $12 ≈ **$132 in slippage cost on 5/4 alone**. Over 9 sessions at ~2–3 churn days/week, cumulative drag: ~$264–$396 over the tracked period. Against $99.6K equity that's small (0.3–0.4%), but 18% alpha gap suggests systematic factors beyond friction — the real benefit of P2 is preventing exits that lock in losses before positions recover.

**P3, P4 (selector inertia / winner protection) — cannot be backtested offline.** These require per-symbol price series for held positions across the 9-session window, which needs yfinance/AlphaVantage (both blocked).

**P1, P5, P6 — no backtest needed.** P1 is a hard-constraint fix (SOXS was correctly rejected at execution). P5 and P6 are path fixes that would have converted skipped orders to fills; their value is opportunity cost, not loss prevention.

---

## Operational Status

**Primary finding: The bot has not traded in 45 trading days.** All strategy analysis above applies to 5/4 data and cannot be validated or invalidated by current live performance.

The frozen 5/4 book — ~60% SPY ($59.7K), AXTX 14.6%, PWR 11.1%, META 9.5%, 5% cash — has been the de-facto allocation for 9.5 weeks. Against "beat SPY", this allocation effectively tracks SPY (via the SPY sleeve) minus three concentrated single-name bets.

**Required action before any strategy proposal can be validated:**
1. Confirm the scheduler (cron/GitHub Action) is invoking `scan_and_trade.py` 6× daily on weekdays.
2. Confirm write path: `data/research/` and `data/journal/` mtimes on the runtime host match this repo.
3. Check PA34KBGT3V7E Alpaca dashboard: if positions unchanged since 5/4, the bot is frozen.
4. Consider liquidating to SPY or cash out-of-band if the bot remains offline — the three single-name longs (AXTX, PWR, META) have had 9.5 weeks unsupervised.

