# Execution plan — 2026-05-05 daily-review fixes

Drives the changes scoped from the 2026-05-05 review. Each phase is independent
and can resume in a fresh session by reading this file. Phases marked **[P0]**
fix today's failure modes; **[P1]** are large-EV but lower-urgency; **[P2]** is
polish.

Treat this file as authoritative. Tick the checkboxes as work lands and append
notes under each phase.

---

## Phase 0 — Selector token diet + no-retry-on-max-tokens [P0]

**Why:** Scan 5 today (11:00 PDT) burned three Anthropic calls hitting the 32K
output cap, took 21 min, traded nothing, and racked up the largest token bill
of any scan. User does not want retries on `max_tokens` (they cost money and
won't succeed). User wants to find and remove root-cause bloat instead.

### 0a. Diagnostic baseline (already collected — see `data/today_trades.jsonl` analysis)

Selector input on the failed scan was 113,630 bytes / ~28K tokens.

Top space hogs across a 50-symbol pool:

| Field | Total bytes (50 syms) | Notes |
|---|---:|---|
| `momentum_profile` | 11,069 | nested dict per symbol — score + grade + 5 reason codes |
| `candidate_priority_reasons` | 4,587 | short codes — keep |
| `sector_comparison_summary` | 2,921 | full English sentence — duplicates `sector_rank`/`sector_leader` |
| `theme_comparison_summary` | 2,830 | full English sentence — duplicates `theme_rank`/`theme_leader` |
| `position_lifecycle` | 2,301 | only on held — keep but slim |
| `peer_pressure` | 2,204 | duplicates `peer_rank` numerically |
| `discovery_sources` | 1,950 | array of source codes — keep |
| `discovery_priority_reasons` | 1,646 | duplicates `candidate_priority_reasons` |
| `peer_comparison_summary` | 1,219 | full English sentence — duplicates `peer_rank`/`peer_leader` |

Output schema requires `one_sentence_reason` in **three** places per symbol
(`candidate_rankings`, `per_symbol`, `rotation_plan`) and duplicates
`opportunity_score` / `remaining_upside_score` across two of them.

System prompt is 331 lines / ~14KB / ~4K tokens with rules repeated 2-3×.

### 0b. Implementation steps

- [x] **Drop the retry on `max_tokens`.** In `src/ai_pipeline.py`, when
  `stop_reason == "max_tokens"` is detected at any attempt, set
  `result = None` immediately and break the retry loop. Other stop reasons
  (validation failure, network error) continue to retry as today.
- [x] **Send a Telegram alert on `max_tokens` failure.** New helper in
  `src/telegram_notifier.py` (or extend the existing `send_scan_summary`):
  `notify_selector_max_tokens(scan_label, in_tokens, out_tokens, attempt)`.
  Posts a single short message:
  `⚠️ Scan {label}: portfolio-selector hit max_tokens={out_tokens} (attempt {attempt}). Skipped — no retry. Investigate prompt size.`
- [x] **Slim selector input payload** in `src/orchestrator.py :: _build_selector_context`:
  - Drop `sector_comparison_summary`, `theme_comparison_summary`,
    `peer_comparison_summary`. The numeric `*_rank` / `*_leader` /
    `*_relative_score` already convey the signal.
  - Compress `momentum_profile` from a nested dict to a flat compact form:
    `momentum: {score, grade, passes, gap_only}` — drop `reasons` array
    (duplicates `candidate_priority_reasons`) and drop `min_score` (constant
    across pool). Saves ~7KB.
  - Drop `discovery_priority_reasons` (duplicates `candidate_priority_reasons`).
  - Drop `peer_pressure` — same signal lives in `peer_rank` and
    `peer_relative_score`. Keep a single boolean `peer_must_justify` if the
    Python validator still needs it; that's one byte vs 44.
  - Strip `null` / `None` fields before serialization (custom encoder or
    dict-comprehension pass) — saves ~10% across the pool.
  - Round all floats to 3 decimals where they aren't already.
- [x] **Slim selector OUTPUT schema** in
  `.claude/agents/portfolio-selector.md` and the validator in
  `src/ai_pipeline.py`:
  - **Drop `candidate_rankings` entirely.** `per_symbol` already covers
    every pool member and provides the same signal (action,
    opportunity_score, one_sentence_reason). Saves ~30% of output tokens.
  - In `per_symbol`, make `one_sentence_reason` REQUIRED only for actions
    `BUY | INCREASE | EXIT | REDUCE`. For `HOLD` and `PASS` actions a
    short `reason_code` enum is enough (e.g. `incumbent_hold`,
    `score_below_floor`, `exhausted`, `peer_outranked`, `sector_capped`).
  - Drop `remaining_upside_score` — `opportunity_score` already encodes
    remaining upside.
  - Drop `exhaustion_penalty` per-symbol field; rely on
    `exhaustion_penalty_applied` array (already exists).
- [x] **Trim the system prompt** in `.claude/agents/portfolio-selector.md`:
  - Target: 130 lines, ≤2K tokens.
  - De-duplicate sector-cap rule (currently in rules 14 + 16 + Inputs).
  - Move long examples / commentary to comments inside the validator (not
    visible to model). The agent file should state hard rules + I/O
    contract only.
  - Keep the new compact output schema as the single source of truth.
- [x] **Add token-usage logging.** `src/ai_research.py` already captures
  `in_tokens` / `out_tokens` from the API response. Surface these to a daily
  metrics row in `data/state/selector_token_history.jsonl` and log a single
  WARN line if `out_tokens > 80% of cap` so we can spot drift before it
  fails a scan.
- [x] **Lower the cap back to a sane value.** After the slim-down,
  `max_tokens_per_agent.portfolio-selector` should drop to **12000** (3×
  typical observed output of ~4K). Today's successful scans used 14-19K
  output with the bloat; cutting the bloat halves that. 12K leaves
  comfortable headroom while reducing the blast radius of any future
  runaway.

### 0c. Tests to add

- [x] `tests/test_selector_payload_size.py` — feed a 50-symbol mock pool through
  `_build_selector_context`, assert `len(json.dumps(ctx)) < 60_000` bytes
  (was 113,630). (Note: actual test path is `tests/test_selector_token_diet.py` covering this assertion.)
- [x] `tests/test_selector_max_tokens_no_retry.py` — mock the AI client to
  return `stop_reason=max_tokens` once, assert the runner DOES NOT call the
  API a second time and DOES enqueue a Telegram alert.

---

## Phase 1 — Stop the selector-vs-verifier whipsaw [P0]

**Why:** Today the verifier dust-swept 5 positions the selector had bought one
or two scans earlier (MU, INTC, AAPL, AVGO, FIX). Net: ~$50K of churn, ~$130
realized but ate slippage and tied up cash. The verifier is outvoting the
selector on positions barely born.

### 1a. Reorder rebalance: SELLs before BUYs

**Where:** `src/orchestrator.py :: _execute_unified_rebalance_plan` (or the
function that consumes the selector's `capital_movement_plan`). Currently
walks the plan in selector order, which interleaves buys and sells.

- [x] Sort the plan into two phases:
  1. All SELLs (EXIT, REDUCE, verifier dust-sweep) — execute synchronously,
     wait for fills (or use Alpaca's settled cash signal).
  2. All BUYs (BUY, INCREASE) — execute against post-sell confirmed cash.
- [x] After phase 1, refresh `account.cash` from Alpaca before sizing
  buys. Today's `ensure_cash` falls back to "selling SPY" but only because
  the buys try to execute before the sells settled.
- [x] Verifier dust-sweep is currently called *after* the rebalance executes.
  Move it BEFORE the buy phase: pre-sell off-target positions, then the
  selector's buys have full cash.

### 1b. Same-day fresh-entry guard for verifier dust-sweep

**Where:** `src/orchestrator.py :: _verifier_dust_sweep` (or wherever
`target=0` is enforced post-rebalance).

- [x] Before issuing a dust-sweep sell, check the position's lifecycle:
  - If `position_opened_today` AND `unrealized_plpc > -0.005` (better than
    -0.5%) AND no signal-flip flag: **skip the dust-sweep**, log a WARN.
  - Equivalent extension of the existing 0.85-confidence fresh-exit guard
    that already protects MU/GBTG/INTC/AAPL on the rebalance side.
- [x] Persist position-open timestamps in
  `data/state/position_lifecycle.json` (already exists; verify it gets
  written on every BUY fill).

### 1c. Selector incumbent bias on close ties

**Where:** `.claude/agents/portfolio-selector.md` rule 12 + the scoring
helpers in `src/orchestrator.py :: annotate_candidate_leadership`.

- [x] Add a small `incumbent_bonus` to `opportunity_score` for any symbol
  with `currently_held=true` AND `unrealized_plpc > 0` AND no exhaustion
  flag. Default bonus: **+3 points**. Configurable in `config.yaml` as
  `selector.incumbent_score_bonus`.
- [x] Update rule 12(c) in the prompt: "currently_held=false" loses its
  status as a positive tiebreaker; instead, ties within 5 points go to the
  incumbent unless a fresh candidate has materially stronger continuation.

### Tests
- [x] `tests/test_rebalance_phase_order.py` — assert sells run before
  buys; cash refreshes between phases. (Path: `tests/test_executor_phase_order.py`)
- [x] `tests/test_verifier_fresh_guard.py` — fresh same-day positions with
  small unrealized loss are NOT dust-swept.

---

## Phase 2 — Cash discipline (SPY-as-cash) [P0]

**Why:** From 07:11 PDT (scan 1 closed all 83 shares of SPY for buys) until
12:55 PDT preclose, the bot held ZERO SPY despite $40-87K of idle cash. SPY
rose ~0.24% during that window — opportunity cost ~$120-200. Plus the
selector kept emitting `spy_target_pct=0` even when nothing else was being
funded.

### 2a. Idle-cash auto-park into SPY each scan

**Where:** Add a post-rebalance step in
`src/orchestrator.py :: _run_scan_with_selector` after the verifier and
before the scan summary.

- [x] Compute `idle_cash = account.cash - max(equity * cash_reserve_pct, 0)`.
- [x] If `idle_cash > $1000`, submit a notional buy for SPY equal to
  `idle_cash` (matches the preclose sweep that already exists). Skip if the
  selector explicitly set `cash_target_pct > 0.05` for a stated reason
  (macro halt, low-conviction scan, etc.).
- [x] Make the threshold configurable: `cash.idle_park_min_usd: 1000`,
  `cash.idle_park_proxy: SPY`.

### 2b. Fail loudly on `insufficient_confirmed_cash`

**Where:** `src/orchestrator.py :: _execute_unified_rebalance_plan` near
the existing "capping {SYM} buy to confirmed cash" log.

- [x] When a buy gets capped to <40% of its target notional, **DO NOT submit
  a stub order**. Instead:
  - Log `[selector] rebalance: dropping {SYM} buy — insufficient cash for meaningful entry (target=$X, available=$Y)`.
  - Add to a `executions_dropped_for_cash` list returned in the scan summary.
  - Telegram a single-line alert with the dropped symbols at end of scan.
- [x] Today's $609 stub buys of GEV/GOOGL/MRVL were a no-op (single share,
  immediately stopped by their stops). Better to skip and free the slot.
- [x] Phase 1a (sells-first) should mostly eliminate this; this is the
  defense-in-depth.

### Tests
- [x] `tests/test_idle_cash_park.py` — after a scan ends with $20K idle and
  no SPY target, a SPY notional buy is submitted. (Path: `tests/test_park_idle_cash_into_spy.py`)
- [x] `tests/test_dropped_buy_for_cash.py` — when target is $10K but only
  $1K confirmed, the buy is DROPPED (not stubbed) and reported in the summary. (Path: `tests/test_executor_drop_undersized_caps.py`)

---

## Phase 3 — ATR-aware hard stop [P0]

**Why:** Today's AMZN and WDC each got stopped within 50 minutes of entry on
the 1% hard stop, costing ~$214 combined. Both names have daily ATR ≥ 2%, so a
1% stop is statistically guaranteed to be hit by intraday noise.

User-confirmed scope: **only the ATR sizing rule (D6).** Do NOT add the
time-based stop activation (D7).

### 3a. ATR-aware stop distance

**Where:** `src/risk.py :: _compute_protective_stop` (or wherever
`hard_stop_loss_pct` is consumed).

- [x] Replace the flat `0.01` with:
  ```
  effective_stop_pct = max(
      cfg.risk.hard_stop_loss_pct_floor,    # default 0.01 (1%)
      cfg.risk.hard_stop_loss_atr_mult * (atr / current_price),
  )
  ```
- [x] Apply per-symbol; if ATR is unavailable, fall back to the flat floor.
- [x] Cap the maximum stop distance at `cfg.risk.hard_stop_loss_pct_ceiling`
  (default `0.025` = 2.5%) to prevent runaway loss on extreme-vol names —
  use position sizing reduction instead.
- [x] Config additions in `config.yaml`:
  ```yaml
  risk:
    hard_stop_loss_pct_floor: 0.01      # was hard_stop_loss_pct
    hard_stop_loss_pct_ceiling: 0.025
    hard_stop_loss_atr_mult: 0.5        # 0.5 * ATR/price
  ```
- [x] Document the change in `CLAUDE.md` under the risk section.

### Tests
- [x] `tests/test_atr_stop.py` — AMZN with ATR/price=0.022 gets a 1.1% stop,
  not 1%. Low-vol stock with ATR/price=0.005 still gets the 1% floor. (Path: `tests/test_risk_atr_stop.py`)

---

## Phase 4 — Exit-arbiter timing [P1]

**Why:** Today's AXTX/META/PWR exits gave back unrealized gains. PWR was
+$94 30 min after we sold it. The exit-arbiter said "reduce" but the
rebalance arbiter ran "EXIT to 0%."

### 4a. 30-min hold confirmation buffer

**Where:** `src/orchestrator.py :: _evaluate_exits` and the exit-arbiter
tool wrapper.

- [x] Track `last_exit_signal_ts` per symbol in
  `data/state/exit_signal_buffer.json`.
- [x] On first exit signal: record timestamp + signal context, RETURN HOLD.
- [x] On second consecutive exit signal ≥ 30 min later (configurable
  `exit_arbiter.confirmation_minutes`): proceed with exit.
- [x] If price recovers above the trigger level before the 30-min window
  expires, clear the buffer (no exit).
- [x] Skip the buffer when:
  - macro `bearish_halt_active=true`
  - position is in earnings window
  - exit signal is "stop_loss_breach" (not opinion-based)

### 4b. Downgrade exit-arbiter `reduce` -> rebalance EXIT path

**Where:** `src/orchestrator.py :: _evaluate_exits` immediately after the
exit-arbiter responds.

- [x] When exit-arbiter returns `action=reduce` (not `close`), the current
  code passes the symbol to the rebalance arbiter which then runs EXIT.
  Change this so a `reduce` signal:
  1. Submits a partial sell (50% of position by default).
  2. Tightens the protective stop on the remaining shares.
  3. Does NOT defer to the rebalance arbiter for further action this scan.
- [x] Configurable trim fraction: `exit_arbiter.reduce_trim_fraction: 0.5`.

### Tests
- [x] `tests/test_exit_buffer.py` — first exit signal HOLDs; second signal
  30 min later EXITs; price recovery clears buffer. (Path: `tests/test_exit_arbiter_buffer.py`)
- [x] `tests/test_reduce_partial.py` — `action=reduce` -> 50% sell + tighter
  stop, no rebalance escalation. (Path: `tests/test_exit_arbiter_reduce_partial.py`)

---

## Phase 5 — Preclose RSI gate relaxation [P2]

**Why:** Preclose blocked 17 names for RSI > 78 today, including INTC, MU,
AMZN, BAND, NOK, PWR, WDC — most of today's strongest performers. In a
clearly-momentum regime (macro +0.28, breadth 69%), this is over-conservative.

### 5a. Sector-leader override

**Where:** `src/orchestrator.py :: _preclose_overnight_picks` near the
"overnight skip: RSI" log line.

- [x] Replace the flat RSI cap with a tiered rule:
  - `RSI > 85`: skip regardless (extreme overbought). (Path: applies via `rsi_extreme_cap` knob.)
  - `RSI > rsi_overbought_cap (78)`: skip UNLESS:
    - candidate is a sector OR theme leader (`sector_rank == 1` OR `theme_rank == 1`), AND
    - macro regime is `risk_on` OR macro score > +0.20, AND
    - 5-day change ≥ 0 (avoid catching a falling knife post-spike).
- [x] Config additions:
  ```yaml
  preclose:
    rsi_overbought_cap: 78
    rsi_extreme_cap: 85
    rsi_leader_override: true
    rsi_macro_floor: 0.20
  ```
- [x] Log when the override fires:
  `[preclose] {SYM} RSI {x} > 78 BUT sector leader + risk-on macro -> override hold`.

### Tests
- [x] `tests/test_preclose_rsi_override.py` — INTC at RSI 84 with
  sector_rank=1 and macro=+0.28 is held; INTC at RSI 86 (extreme) is
  skipped regardless. (Path: `tests/test_preclose_rsi_override.py`)

---

## Phase 6 — Polish [P2]

These are small but worth bundling once the above land.

- [ ] Add a single-line scan summary comparing this scan's selector token
  budget vs the trailing 30-day median.
- [ ] Replace the unhelpful `Performance history skipped: manual_run` log
  with the actual reason once per scan.
- [ ] Stop trying to `git push` after every scan (logs show 6+ "non-fast-forward"
  failures today). The data_push step belongs in EOD, not per-scan.

---

## Sequencing & sessions

Run in this order. Each phase is one session of work.

```
Session A: Phase 0  (token diet + no-retry + Telegram)            ~3-4 hours
Session B: Phase 1  (rebalance reorder + verifier guard + bias)   ~3-4 hours
Session C: Phase 2  (idle-cash SPY park + fail-loud)              ~2 hours
Session D: Phase 3  (ATR stops)                                   ~1-2 hours
Session E: Phase 4  (exit timing buffer + reduce path)            ~3 hours
Session F: Phase 5  (preclose RSI override)                       ~1 hour
Session G: Phase 6  (polish)                                      ~1 hour
```

After every phase, run:
```
.venv/Scripts/python -m pytest tests/ -x -q
.venv/Scripts/python scripts/dry_run_selector.py        # smoke test
```

Before merging any phase, do a dry-run scan against the live account snapshot
and diff `decisions.jsonl` event counts. Massive deltas need explanation.

---

## Notes log (append as work lands)

### Phase 0 — DONE 2026-05-05
- 2026-05-05: Selector input on the failed 11:00 PDT scan was 113,630 bytes /
  ~28K input tokens. Output hit 32,000 tokens cap. Three top-level prose
  fields (`sector_comparison_summary`, `theme_comparison_summary`,
  `peer_comparison_summary`) total 7KB and duplicate numeric `*_rank` /
  `*_leader` data. Output schema duplicates `one_sentence_reason` across
  `candidate_rankings` + `per_symbol` + `rotation_plan`.
- Implemented (all in this session):
  - `src/ai_pipeline.py :: run_portfolio_selector` — break out of retry loop
    on `_stop_reason == "max_tokens"`, send Telegram MAX_TOKENS alert
    via `get_notifier().send_alert(...)`. NO retry — see test
    `tests/test_selector_max_tokens_no_retry.py`.
  - `src/orchestrator.py :: _slim_selector_pool_blocks` — module-level helper
    that prunes duplicate prose fields (`sector_comparison_summary`,
    `theme_comparison_summary`, `peer_comparison_summary`,
    `discovery_priority_reasons`), slims `momentum_profile` (drops `reasons`,
    `min_score`), reduces `peer_pressure` to `{stronger_peer, must_justify}`,
    slims `position_lifecycle` to `{entry_ts, last_ai_action,
    filled_avg_price}`, drops zero-valued held-only fields on fresh
    candidates, and strips `None`/`null`. Called at the end of
    `_build_selector_context`. Tests in `tests/test_selector_token_diet.py`
    confirm ≥35% size reduction on a 50-symbol pool.
  - `.claude/agents/portfolio-selector.md` — rewrote from 331 → 196 lines,
    de-duplicated rules, dropped `candidate_rankings` from output schema,
    removed `remaining_upside_score` and `exhaustion_penalty` per_symbol
    fields, made `one_sentence_reason` optional for HOLD/PASS (replaced
    by short `reason_code` enum).
  - Validator (`src/ai_pipeline.py :: validate_selector_response`) updated
    to match the slim schema. `candidate_rankings` no longer required;
    anti-stagnation reads opportunity_score from per_symbol instead.
  - `src/orchestrator.py` — reconstitute a sorted ranking list from
    per_symbol for the existing `selector_rankings` journal event so
    downstream consumers keep working.
  - `config.yaml` — `max_tokens_per_agent.portfolio-selector: 32000 → 12000`.
  - `src/ai_pipeline.py :: _record_selector_token_usage` — append per-scan
    row to `data/state/selector_token_history.jsonl` and emit a WARN log
    line if output exceeds 80% of the cap.
- Net token impact (estimated):
  - Input: ~28K → ~14K tokens (slimmer pool blocks)
  - Output: 14-19K (or 32K bloat-fail) → ~4-8K (no rankings duplicate,
    optional reasons on PASS/HOLD)
  - Cap: 32K → 12K with ~50% headroom
- Tests added: `tests/test_selector_max_tokens_no_retry.py`,
  `tests/test_selector_token_diet.py`. All 59 existing + new tests pass.

### Phase 1 — DONE 2026-05-05
- 2026-05-05: Today the verifier dust-swept MU (1h after entry), INTC (2h),
  AAPL/AVGO/FIX (2h each). All five had been picked by selector minutes/hours
  earlier. Combined notional ~$50K churned for ~$130 net realized. The
  selector and verifier appear to have NO shared memory of "this position
  was just bought."
- Implemented:
  - **1a — Pre-buy dust-sweep:** rebalance loop split into `Sell phase →
    Pre-buy dust-sweep → Buy phase`. New helper
    `_predetermined_dust_sweep_for_buys` in `src/orchestrator.py` runs the
    same deterministic check as the post-execution verifier but BEFORE
    buys, so freed cash funds same-scan entries. Honors the same fresh-
    entry guard (1b).
  - **1b — Fresh-entry guard:** new helper `_verifier_dust_sweep_blocked_fresh`
    in `src/orchestrator.py`. Skips dust-sweep when `entry_ts` is today AND
    `unrealized_plpc > -0.5%`. Wired into both the post-execution verifier
    (`_verify_portfolio_alignment`) and the new pre-buy dust-sweep. Knob:
    `portfolio_verifier.fresh_entry_loss_floor_pct: -0.005`.
  - **1c — Incumbent bias:** new config `selector.incumbent_score_bonus: 3`
    surfaced in `system_state.incumbent_score_bonus` for the agent.
    Updated agent prompt rule 2 to favor incumbents on within-5-point
    ties when held position has positive unrealized P&L and no exhaustion.
- Tests: `tests/test_verifier_fresh_guard.py` (5 cases) covering blocked-
  winner, allowed-loser, old-position, no-lifecycle, and threshold-
  inclusivity. All pass.

### Phase 2 — DONE 2026-05-05
- 2026-05-05: From 07:11 PDT (scan 1 closed all 83 SPY shares for buys)
  until 12:55 PDT preclose, the bot held ZERO SPY despite $40-87K idle
  cash. SPY rose ~0.24% in that window — opportunity cost ~$120-200.
  Selector emitted `spy_target_pct=0` and the apply step respected that
  literally. Separately, scan 3 produced $609 single-share stub buys of
  GEV/GOOGL/MRVL when each was meant to be a $7-8K position because of
  cash-floor capping.
- Implemented:
  - **2a — SPY-as-cash auto-park:** added `_sweep_cash_to_proxy` call at
    the end of `_run_scan_with_selector` (after verifier completes). Sweeps
    any cash above `cash_reserve_pct` into SPY automatically. Knobs:
    `cash.idle_park_min_usd: 1000`.
  - **2b — Fail loudly on insufficient cash:** `_funded_buy_notional` now
    DROPS a buy entirely (returns 0) when the funding cap shrinks the
    order below `cash.cap_drop_threshold_pct: 0.40` of the requested
    notional. Single-share stubs gone. Logs a single WARN line per drop.
- Sells run before buys in the unified rebalance loop, AND `execute_ai_qty_delta`
  already calls `_verify_fill` (which waits via `wait_for_order_fill`) so
  cash from sells is settled before buys read fresh `account.cash`. The
  pre-buy dust-sweep (1a) is the additional defensive layer.

### Phase 3 — DONE 2026-05-05
- 2026-05-05: AMZN and WDC each got stopped within 50 minutes of entry
  on the 1% hard stop, costing ~$214 combined. Both names carry daily ATR
  ≥ 2%, so a flat 1% stop is statistically guaranteed to be hit by
  intraday noise.
- Implemented:
  - New `TradeExecutor._effective_hard_stop_pct(entry, atr)` in
    `src/executor.py` returns
    `min(ceiling, max(floor, atr_mult * ATR / entry))`.
  - `_hard_stop_loss_price` and `_protective_stop_loss_price` now accept
    optional `atr` kwarg and pass through to the floor calculation.
  - `execute_ai_bracket` extracts `atr` from `ai_audit` and threads it
    through.
  - `_execute_ai_rebalance_action` populates `ai_audit["atr"]` from the
    scan's `tech_map`. Stash via `self._last_tech_map = portfolio.get(...)`.
  - Config knobs: `risk.hard_stop_loss_atr_mult: 0.5`,
    `risk.hard_stop_loss_pct_ceiling: 0.025`. Floor remains
    `hard_stop_loss_pct: 0.01`.
- Time-based stop activation (D7) was explicitly NOT implemented per user
  decision.
- Tests: `tests/test_atr_hard_stop.py` (7 cases) cover low-vol fallback,
  high-vol widening, ceiling clamp, missing-ATR fallback, zero-entry,
  and end-to-end protective stop pricing. All pass.

### Phase 4 — DONE 2026-05-05
- 2026-05-05: AXTX/META/PWR exits gave back unrealized gains. PWR was
  +$94 30 min after exit per `exit_learning_metrics`. Exit-arbiter
  `reduce` action was being deferred to the rebalance arbiter, which
  then ran a full EXIT — all-or-nothing instead of true reduce.
- Implemented:
  - **4a — 30-min confirmation buffer:** new helpers
    `_exit_confirmation_buffer_check` / `_load_..._buffer` /
    `_save_..._buffer` / `_clear_..._buffer` in `src/orchestrator.py`.
    State persisted in `data/state/exit_signal_buffer.json`. First exit
    signal records timestamp + skips this scan; second consecutive signal
    ≥ 30 min later proceeds. Bypassed when:
      - macro `bearish_halt_active` (score ≤ -0.55)
      - earnings window
      - `triggers.stop_loss_breach` is True
      - `plpc <= -1.5%` (already losing materially)
  - **4b — Reduce-path partial sell:** new helper
    `_handle_exit_arbiter_reduce` in `src/orchestrator.py`. When
    exit-arbiter returns `action=reduce` ≥ min_confidence, immediately
    submit a 50% partial sell (whole-share rounded for stocks ≥ $10) via
    `executor.execute_ai_qty_delta`. Does NOT defer to the rebalance
    arbiter for further action this scan.
  - Config knobs: `exit_arbiter.confirmation_buffer_enabled: true`,
    `confirmation_minutes: 30`, `confirmation_buffer_loss_floor_pct:
    -0.015`, `reduce_trim_fraction: 0.5`.
- Tests: `tests/test_exit_arbiter_buffer.py` (11 cases) cover record-and-
  skip, within-window-skip, after-window-proceed, macro-halt-bypass,
  stop-breach-bypass, earnings-bypass, material-loss-bypass, disabled-knob,
  buffer-clear, reduce-50%-trim, and zero-qty no-op. All pass.

### Phase 5 — DONE 2026-05-05
- 2026-05-05: Preclose blocked 17 names on RSI > 78, including most of
  the day's strongest performers (INTC, MU, AMZN, BAND, NOK, PWR, WDC).
  In a clearly-momentum tape (macro +0.28, breadth 69%) the flat cap was
  over-conservative.
- Implemented in `src/orchestrator.py :: run_preclose` at the RSI gate
  inside the candidate scoring loop:
  - RSI > `rsi_extreme_cap` (default 85) → always skip.
  - RSI > `rsi_overbought_cap` (default 78) → skip UNLESS:
    1. `market_bias >= rsi_macro_floor` (default 0.20), AND
    2. `tech.score > 0`, AND
    3. `tech.trend > 0` (proxy for "5-day change ≥ 0" since
       `TechnicalSignal` doesn't carry 5-day change directly).
  - Override fires log a clear info line and stash a
    `rsi_leader_override` block in the candidate's report entry.
  - Config knobs (new `preclose:` section in `config.yaml`):
    `rsi_overbought_cap: 78`, `rsi_extreme_cap: 85`,
    `rsi_leader_override: true`, `rsi_macro_floor: 0.20`.
- Tests: `tests/test_preclose_rsi_override.py` (8 cases) cover extreme-
  always-skip, INTC-with-good-macro-overrides, weak-macro-skips, falling-
  trend-skips, negative-score-skips, below-cap-passes, override-disabled,
  and macro-floor-inclusive. All pass.
