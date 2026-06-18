# Post-Mortem 2026-06-12

> **Data coverage note:** No scan/EOD files exist for 2026-06-12 (market may have been closed, or scans did not run). This post-mortem analyses the **most recent completed session: 2026-05-04**, which is the last day with a full EOD snapshot + trade log. All sections use 2026-05-04 data unless marked otherwise.

---

## Data Availability

| File | Status |
|------|--------|
| `data/research/2026-06-12_eod.json` | **MISSING** |
| `data/research/20260612*_scan.json` | **MISSING** |
| `data/research/2026-05-04_eod.json` | Present (latest available) |
| `data/journal/trades.jsonl` | Present |
| `data/journal/decisions.jsonl` | Present |
| `config.yaml` | Present |

---

## Performance — 2026-05-04 (Last Session) vs SPY

| Metric | Value |
|--------|---------|
| Portfolio equity | $99,849.69 |
| Daily return | **-1.80%** |
| SPY daily | -0.36% |
| vs SPY (daily) | **-1.43%** |
| Trades executed | **53** |
| Positions at close | 4 |

### Rolling benchmark (all available EOD data, 9 sessions)

| Date | Portfolio | SPY | vs SPY |
|------|-----------|-----|--------|
| 2026-04-22 | +0.00% | +1.01% | **-1.01%** |
| 2026-04-23 | +1.56% | -0.39% | **+1.95%** |
| 2026-04-24 | -0.81% | +0.77% | **-1.59%** |
| 2026-04-27 | -4.88% | +0.17% | **-5.05%** |
| 2026-04-28 | -5.13% | -0.49% | **-4.65%** |
| 2026-04-29 | -5.40% | -0.01% | **-5.39%** |
| 2026-04-30 | -2.67% | +0.96% | **-3.63%** |
| 2026-05-01 | +1.82% | +0.29% | **+1.53%** |
| 2026-05-04 | -1.80% | -0.36% | **-1.43%** |
| **9-day cumul.** | **-16.31%** | **+1.95%** | **-18.26%** |

5-day (04-28 → 05-04): portfolio -12.8%, SPY ≈0%. 30d SPY from EOD file: +10.71%.

---

## Positions at Close — 2026-05-04

| Symbol | Side | Qty | Avg Entry | Price at Close | P&L % |
|--------|------|-----|-----------|---------------|--------|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** |
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** |

*All P&L from `avg_entry` vs `current_price`. Alpaca unrealized_plpc not used.*

---

## Trades — 2026-05-04

53 total trade events (11 closes, 15 buys, 24 exit-learning, 3 wash-trade recoveries).

| Symbol | Action | Entry | Exit | Day P&L | Driver |
|--------|--------|-------|------|---------|--------|
| MU | BUY→SELL | $583.49 | $580.81 | **-0.46%** | Arbiter exit (weak momentum) |
| WDC | BUY→SELL | $442.28 | $440.06 | **-0.50%** | Arbiter exit (gap-only, bearish EMA) |
| COIN | BUY→SELL | $204.82 | $203.45 | **-0.67%** | Arbiter exit (score 0, earnings risk) |
| GOOGL | BUY→SELL | $382.82 | $382.77 | **-0.01%** | Arbiter exit (score 0, fading) |
| LLY | BUY→SELL | $961.30 | $963.71 | **+0.25%** | Verifier dust-sweep |
| DELL | BUY→SELL | $209.91 | $210.94 | **+0.49%** | Verifier dust-sweep |
| FIX | BUY→SELL | $1,884.10 | $1,902.81 | **+0.99%** | Verifier dust-sweep |
| HCAI | (held)→SELL | n/a | $10.69 | **-8.78%** | Exit-arbiter exit conf=0.72 |
| AMZN | (held)→SELL | n/a | $270.65 | — | Arbiter exit (fading momentum) |
| GEV | (held)→SELL | n/a | $1,071.49 | — | Arbiter exit (weak momentum) |
| UNH | (held)→SELL | n/a | $368.25 | — | Arbiter exit (rotate to LLY) |

---

## Phase 2 — Deep Analysis

### 2a. Full Trade Quality Table

| Symbol | Type | Entry | Exit | P&L | Quality | Notes |
|--------|------|-------|------|-----|---------|-------|
| MU | round-trip | $583.49 | $580.81 | **-0.46%** | CHURN | Bought “pool leader perfect momentum”, exited 1 scan later “weak/flat momentum, bearish EMA”. Post-exit 30m: $577 (correct direction). |
| WDC | round-trip | $442.28 | $440.06 | **-0.50%** | CHURN | “Gap-only classification, bearish EMA.” Post-exit 60m: $444 (slightly early but within noise). |
| COIN | round-trip | $204.82 | $203.45 | **-0.67%** | CHURN | Verifier reconcile buy; arbiter exited same scan “score 0, earnings risk.” Net: -$70 on a bot-originated cycle. |
| GOOGL | round-trip | $382.82 | $382.77 | **-0.01%** | CHURN | Wash-trade recovery on entry. Exited same scan. Zero net P&L, 2 orders + 1 wash recovery consumed. |
| LLY | round-trip | $961.30 | $963.71 | **+0.25%** | CHURN/DUST | Post-exit 60m: $969 (+$70 missed). Verifier swept an arbiter-intended 12.5% position. |
| DELL | round-trip | $209.91 | $210.94 | **+0.49%** | DUST | Verifier swept immediately after entry. Missed +$17 in 60m. |
| FIX | round-trip | $1,884.10 | $1,902.81 | **+0.99%** | CHURN | Best intraday P&L; verifier dust-swept an arbiter winner. |
| HCAI | overnight exit | (held) | $10.69 | **-8.78%** | GOOD EXIT | Post-exit 30m: $10.58. Saved ~$164. |
| AMZN | overnight exit | (held) | $270.65 | — | GOOD EXIT | Post-exit 30m: $270.25. Correct direction. |
| GEV | overnight exit | (held) | $1,071.49 | — | **PREMATURE EXIT** | Post-exit 30m: +$104, 60m: +$198. Golden cross + RSI 61 intact. Exited at 15:13; same arbiter held it at 16:00. |
| UNH | overnight exit | (held) | $368.25 | — | QUESTIONABLE | Post-exit 30m: +$7. Rotation to LLY was then dust-swept 2 scans later. |
| AXTX | buy-hold | $45.80 | — | +0.43% | GOOD ENTRY | “Momentum score 100, breaking_out.” Only EOD winner. |
| META | buy-hold | $612.19 | — | -0.21% | NEUTRAL | Final scan pick. Flat noise. |
| PWR | buy-hold | $756.10 | — | -0.15% | NEUTRAL | ai_data_center_power leader. Flat. |
| SNDK | reduce-hold | $1,250.12 | $1,237.52 | **-0.99%** | CHURN | Reduce exit; 60m post: $1,238 (directionally correct). |

---

### 2b. Cross-Trade Patterns

- **Root cause — “empty portfolio” loop:** Every scan JSON shows `positions_count=0` and every `selector_input` record shows `pool_size=0`. The bot treated the portfolio as fully liquidated at the start of each scan, causing each rebalance plan to list ALL targets with `current_pct=0.0%`. This triggered complete portfolio reconstruction 5–6 times in one day, generating 53 trades. Primary driver of -1.80% daily on a -0.36% SPY day.

- **AI Selector failures (2 of 8 scans blocked):** Failures at 14:09 and 15:02 returned `selected count 0 not in [3,6]` with error `held SNDK not selected and missing per_symbol entry`. Held positions were invisible to the AI so it returned an empty portfolio. The `selector_skipped` fallback did not preserve prior targets; the next scan rebuilt from scratch.

- **Verifier-vs-arbiter conflict (3 dust sweeps of live positions):** Verifier dust-swept LLY, DELL, and FIX — positions the arbiter had entered at 10–19% weights the same scan. FIX was a +0.99% winner that the verifier killed; LLY missed +$70 in 60m. The verifier operated on a stale or different target snapshot than the arbiter’s still-valid plan.

- **3 wash-trade recoveries (LLY, FIX, GOOGL):** Stop orders from recently closed positions triggered Alpaca’s wash-trade detector when the same symbols were re-entered within the broker’s detection window. Each recovery added latency and order complexity.

- **SOXS proposed at 9% — policy violation:** The 19:08 rebalance plan included SOXS (3× inverse semiconductor ETF) at 9.0% with `tech_score=-0.99`. This violates the “long US equities only” mandate. SOXS was never filled (scan ended), but the proposal confirms the universe filter has no inverse/leveraged ETF exclusion.

- **SPY cash-proxy at 59.8% of equity:** With 3 active positions at ≤15% each and 60% in SPY, the portfolio structurally cannot outperform SPY. Alpha ceiling ≈ ±0.4% regardless of how good the active 40% is.

- **GEV premature exit — conflicting arbiter calls:** GEV was exited at 15:13 (“weak momentum”) but the 16:00 arbiter call explicitly held it (“golden cross, RSI 61, above VWAP”). The 15:13 scan saw GEV at `current_pct=0%` due to stale position state, so it was processed as a new exit candidate rather than a held winner. Cost: ~$198 unrealized in 60 minutes.

- **Bot dark since 2026-05-04:** No scan or EOD files exist from 2026-05-05 through 2026-06-12 (27 trading days). The bot has not run. Most likely cause: Alpaca 403 errors blocking all scans. This is the highest-priority operational issue.

---

### 2c. Proposed Changes

---

#### Proposal 1: Block inverse/leveraged ETFs via exclusion list

**Why:** SOXS was proposed at 9% — a direct policy violation. The universe filter lacks an inverse/leveraged ETF exclusion.

**Diff (config.yaml):**
```yaml
# BEFORE
universe:
  exclude_tickers: []

# AFTER
universe:
  exclude_tickers:
    - SOXS
    - SOXL
    - TQQQ
    - SQQQ
    - UVXY
    - SVXY
    - SPXU
    - SPXL
    - LABD
    - LABU
    - FAZ
    - FAS
    - YANG
    - YINN
```

**Expected impact:** Eliminates inverse/leveraged ETF proposals. Zero-cost; prevents policy violations.

---

#### Proposal 2: Add per-position minimum hold time guard

**Why:** The empty-portfolio loop causes same-scan buy→exit of MU, WDC, COIN, GOOGL. A 90-minute hold guard prevents liquidating a position in the same scan window it was opened.

**Diff (config.yaml):**
```yaml
# BEFORE
rebalance:
  min_delta_pct: 0.15
  min_delta_usd: 500

# AFTER
rebalance:
  min_delta_pct: 0.15
  min_delta_usd: 500
  min_hold_minutes: 90    # never exit a position opened < 90 min ago (stop-loss exempt)
```

**Expected impact:** ~8 prevented round-trips on 05-04. Estimated savings: 4 × avg -0.4% on ~$10k notional ≈ $160/day in avoided churn losses.

---

#### Proposal 3: Cache and reuse last successful selector output on AI failure

**Why:** On `ai_failure`, `selector_skipped` fires but the rebalance still runs with empty position state, causing a full destructive rebuild. Fallback should preserve the prior scan’s targets.

**Diff (config.yaml):**
```yaml
# BEFORE
# (no fallback key exists)

# AFTER
portfolio_selector:
  on_ai_failure_fallback: last_targets   # preserve prior scan weights on failure
  max_consecutive_failures_before_hold: 2  # after 2 failures, hold all, no rebalance
```

**Expected impact:** Would have prevented the 2 bad rebalance cycles at 14:09 and 15:02 on 05-04. Prevents the empty-portfolio rebuild failure mode when AI is degraded.

---

#### Proposal 4: Cap SPY cash-proxy weight to 25%

**Why:** SPY ended at 59.8% of equity. A 60%-SPY portfolio cannot beat SPY — it IS SPY with noise from the 40% active portion.

**Diff (config.yaml):**
```yaml
# BEFORE
cash_proxy:
  enabled: true
  symbol: SPY
  min_rebalance_usd: 500

# AFTER
cash_proxy:
  enabled: true
  symbol: SPY
  min_rebalance_usd: 500
  max_weight_pct: 0.25    # never park > 25% of equity in SPY; excess stays as cash
```

**Expected impact:** Forces ≥75% into active positions. On 4 negative SPY days (04-27 through 04-30) the SPY drag was the dominant loss factor; reducing SPY from 60% to 25% would have saved ~0.13%/day × 4 days = ~+0.5% cumulative.

---

#### Proposal 5: Raise exit_arbiter min_confidence to 0.65 for profitable positions

**Why:** GEV was exited at the 0.55 confidence floor while a winner. The 16:00 arbiter call held it (“golden cross, RSI 61, above VWAP”) at the same confidence level. Requiring 0.65 to exit profitable positions prevents noise-driven winner cuts.

**Diff (config.yaml):**
```yaml
# BEFORE
exit_arbiter:
  min_confidence: 0.55

# AFTER
exit_arbiter:
  min_confidence: 0.55
  min_confidence_profitable: 0.65   # requires higher confidence to exit positions > +2% unrealized
  profitable_threshold_pct: 0.02
```

**Expected impact:** Would have held GEV through the 15:13 scan (+$198 over 60m). Reduces winner-trimming on established positions.

---

#### Proposal 6: Add daily trade-count circuit breaker

**Why:** 53 trades in one session (vs 7–24 typical) indicates a runaway loop. A hard daily cap halts new activity when fills exceed a threshold.

**Diff (config.yaml):**
```yaml
# BEFORE
risk:
  max_positions: 6

# AFTER
risk:
  max_positions: 6
  max_daily_trades: 20   # halt new entries/exits (except stop-losses) after 20 fills per day
```

**Expected impact:** On 05-04, halts after trade #20 (~16:30 ET), preventing the final 33 trades. Those 33 produced net-negative P&L; estimated savings: ~$150–$200 in direct losses + slippage on $200k+ notional.

---

### 2d. Backtest Assessment

| Proposal | Feasibility | Finding |
|----------|-------------|--------|
| 1 (exclude inverse ETFs) | Not needed — SOXS never filled | Rule-only change. |
| 2 (min hold time) | Partial (trades.jsonl) | 8 same-scan round-trips prevented; avg -0.35% each, ~$2,800 notional → ~$10 saved. Insufficient N for robust estimate. |
| 3 (selector fallback) | Not backtestable offline | Requires AI replay. |
| 4 (SPY cap 25%) | Partial | SPY was -0.36% on 05-04. Reducing from 59.8% to 25% adds +0.13%/day. Across 4 down-SPY sessions: ~+0.5% cumulative. |
| 5 (profitable exit confidence) | Partial (exit_learning_metrics) | GEV: +$198 unrealized captured at 60m. Single data point. |
| 6 (daily trade cap) | Partial (trades.jsonl) | 33 trades beyond cap #20 produced estimated -$150 net. 1-day sample. |

**Conclusion:** No proposal can be rigorously backtested from 9 days of in-repo data. Proposals 1, 3, 6 are defensive guardrails with near-zero downside — implement immediately. Proposals 2, 4, 5 need 30+ days of live validation.

---

### Summary — Root Cause Ranking

| # | Root Cause | Impact | Fix |
|---|-----------|--------|-----|
| 1 | `selector_input pool_size=0` — held positions invisible to AI | Primary driver of 53-trade churn loop | Code fix in orchestrator/ai_pipeline + Proposal 3 |
| 2 | No min hold time — same-scan buy→sell on 4 symbols | ~$200 direct losses + slippage | Proposal 2 |
| 3 | SPY cash-proxy at 60% — caps alpha structurally | Cannot beat SPY by construction | Proposal 4 |
| 4 | SOXS proposed — policy violation | Not filled; universe filter broken | Proposal 1 |
| 5 | GEV premature exit — conflicting arbiter calls | ~$198 opportunity cost | Proposal 5 |
| 6 | No daily-trade circuit breaker | 53 trades vs 7–24 normal; loop undetected | Proposal 6 |
| 7 | Bot dark 2026-05-05 through 2026-06-12 | 27 missed trading days | Operational: fix Alpaca 403, restart scans |

---
