# Post-Mortem 2026-06-11

## Data availability

| Source | Status | Notes |
|---|---|---|
| `2026-06-11_eod.json` | **MISSING** | Bot offline — no data written since 2026-05-04 |
| Last `_eod.json` | `2026-05-04_eod.json` | Last known equity $99,849.69 |
| Last scan | `20260504T190848_scan.json` | 6th scan of 5/4 |
| Last preclose | `20260504T195545_preclose.json` | |
| `trades.jsonl` | 204 lines; last event `2026-05-04T19:55:03Z` | Unchanged 38 calendar days |
| `decisions.jsonl` | 1556 lines; last event `2026-05-04T20:15:04Z` | Unchanged 38 calendar days |

**Bot status: OFFLINE.** No scans, no trades, no EOD snapshots since 2026-05-04 (~27 trading days, 38 calendar days). All analysis below is drawn from the last active trading day (2026-05-04) and the rolling EOD archive. This is the seventh consecutive no-live-data review.

---

## Performance today (portfolio vs SPY — last known state)

| Metric | Value |
|---|---|
| Last known equity | $99,849.69 (2026-05-04 EOD) |
| Daily return (5/4) | **-1.80%** vs SPY **-0.36%** → **-1.44pp miss** |
| 5-day return (4/28–5/4) | **-14.64%** vs SPY **-0.40%** → **-14.24pp miss** |
| Full-period return (4/23–5/4) | **-14.01%** vs SPY **-0.03%** → **-13.98pp miss** |
| Trades on 5/4 | **53** (extreme churn day) |
| Positions at 5/4 EOD | 4 (AXTX, META, PWR, SPY) |

Equity curve (all available EOD data):

| Date | Equity | Daily Ret | SPY Daily | vs SPY |
|---|---|---|---|---|
| 2026-04-22 | $99,627 | 0.00% | +1.01% | -1.01pp |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | +1.95pp |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.58pp |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05pp |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.64pp |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39pp |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53pp |
| 2026-05-04 | $99,850 | **-1.80%** | -0.36% | **-1.44pp** |

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Close Price | PnL% | Market Value | Notes |
|---|---|---|---|---|---|---|
| AXTX | Long | $46.41 | $46.61 | +0.43% | $14,589 | Small-cap biotech |
| META | Long | $611.73 | $610.46 | -0.21% | $9,448 | Communication Svcs |
| PWR | Long | $758.48 | $757.38 | -0.15% | $11,130 | AI data center power |
| SPY | Long | $717.52 | $718.03 | +0.07% | $59,696 | Cash proxy (~60% of book) |

Cash: $4,987 (5.0% — at floor).

---

## Trades 2026-05-04 (all 53 events)

Selected executed trades only (entries + exits with price data):

| Time (UTC) | Event | Symbol | Entry | Exit | PnL% | Reason (truncated) |
|---|---|---|---|---|---|---|
| 14:51 | position_closed | HCAI | $11.84 | $10.69 | **-9.71%** | Exit-arbiter conf=0.72: down -8.78% |
| 16:04 | position_closed | AMZN | (held) | $270.65 | N/A | Fading momentum, below VWAP, bearish EMA |
| 16:04 | position_closed | GEV | (held) | $1,071.49 | N/A | Weak momentum, below VWAP |
| 16:04 | position_closed | UNH | $371.09 | $368.25 | -0.77% | Replaced by LLY |
| 16:04 | ai_order_submitted | LLY | | | | BUY 9.1% strong continuation |
| 16:04 | ai_order_submitted | MU | | | | INCREASE 28% pool leader |
| 16:04 | ai_order_submitted | NOK | | | | BUY 4.9% |
| 16:04 | ai_order_submitted | SNDK | | | | BUY 12.6% best new candidate |
| 17:04 | position_closed | MU | $580.42 | $580.81 | +0.07% | "Weak_or_flat momentum" — 1h after entry |
| 17:04 | ai_order_submitted | DELL | | | | BUY 12.1% |
| 17:04 | ai_order_submitted | FIX | | | | BUY 11.9% |
| 17:04 | ai_order_submitted | GOOGL | | | | BUY 11.0% |
| 17:04 | ai_order_submitted | LLY | | | | INCREASE 12.5% |
| 17:04 | ai_order_submitted | WDC | | | | BUY 10.9% |
| 18:05 | position_closed | WDC | $445.36 | $440.06 | **-1.19%** | "Gap_only classification" — 1h after entry |
| 18:05 | position_closed | DELL | $210.52 | $210.94 | +0.20% | **Verifier dust-sweep** (target=0) — 1h after entry |
| 18:05 | position_closed | LLY | $962.27 | $963.71 | +0.15% | **Verifier dust-sweep** (target=0) — 1h after entry |
| 18:05 | ai_order_submitted | FIX | | | | INCREASE 19.0% |
| 18:05 | ai_order_submitted | GOOGL | | | | Verifier reconcile +$3,569 |
| 19:08 | position_closed | COIN | $203.90 | $203.45 | -0.22% | Earnings risk, momentum=0 |
| 19:08 | position_closed | GOOGL | $384.43 | $382.77 | -0.43% | Momentum=0, fading |
| 19:08 | position_closed | FIX | $1,903.71 | $1,902.81 | **-0.05%** | **Verifier dust-sweep** (target=0) |
| 19:08 | ai_order_submitted | AXTX | | | | BUY 14.4% momentum=100 |
| 19:08 | ai_order_submitted | META | | | | BUY 9.5% |
| 19:08 | ai_order_submitted | PWR | | | | BUY 11.1% |

---

## Phase 2 — Full Analysis

---

### 2a. Per-trade quality ledger (last active day: 2026-05-04)

| Symbol | Side | Entry | Exit | PnL% | Hold | AI conf | Verdict |
|---|---|---|---|---|---|---|---|
| HCAI | Long | $11.84 | $10.69 | **-9.71%** | 3 days | 0.72 (exit) | **BAD** — oversized (17.7% > 15% cap); small-cap biotech stop-out |
| AMZN | Long | (held) | $270.65 | N/A | unknown | 0.75 | BAD — held from prior sessions; no entry price in log |
| GEV | Long | (held) | $1,071.49 | N/A | unknown | n/a | NEUTRAL — valid exit, prior-session carry |
| UNH | Long | $371.09 | $368.25 | -0.77% | ~2h | n/a | BAD — displaced by LLY 1h later; LLY also swept same day |
| MU | Long | $580.42 | $580.81 | +0.07% | **1h** | n/a | **CHURN** — entered scan 16:04, exited scan 17:04 as "weak_or_flat" |
| WDC | Long | $445.36 | $440.06 | **-1.19%** | **1h** | n/a | **CHURN** — entered scan 17:04, exited scan 18:05 "gap_only" |
| DELL | Long | $210.52 | $210.94 | +0.20% | **1h** | n/a | **CHURN** — entered scan 17:04, verifier dust-swept scan 18:05 |
| LLY | Long | $962.27 | $963.71 | +0.15% | **1h** | n/a | **CHURN** — entered scan 17:04, verifier dust-swept scan 18:05 |
| FIX | Long | $1,903.71 | $1,902.81 | -0.05% | **2h** | n/a | **CHURN** — entered+increased scan 17-18:04, verifier dust-swept scan 19:08 |
| COIN | Long | $203.90 | $203.45 | -0.22% | **2h** | n/a | **BAD** — earnings risk should have blocked entry entirely |
| GOOGL | Long | $384.43 | $382.77 | -0.43% | **2h** | n/a | **CHURN** — entered scan 18:05, exited scan 19:08 "momentum=0" |
| AXTX | Long | $46.41 | $46.61 | +0.43% | overnight | n/a | GOOD — final surviving position |
| META | Long | $611.73 | $610.46 | -0.21% | overnight | n/a | NEUTRAL — slight loss, valid overnight hold |
| PWR | Long | $758.48 | $757.38 | -0.15% | overnight | n/a | NEUTRAL — slight loss, valid overnight hold |

**Summary**: 7 of 14 positions were churn (entered and exited same day). 1 was a stop-loss. 3 valid overnight survivors. Net result: -1.80% on 53 trade events.

---

### 2b. Cross-trade patterns

- **Extreme same-day churn (primary failure mode):** 15 positions across 5/1 and 5/4 were entered and exited within the same trading day. On 5/4 alone: MU (1h), WDC (1h), DELL (1h), LLY (1h), FIX (2h), COIN (2h), GOOGL (2h). Portfolio turnover approached 200% in a single session. Each round-trip pays spread + slippage; at $500–$2k per name, this consumed an estimated $3k–$5k in unnecessary friction.

- **Verifier sabotaging arbiter decisions (same-scan conflict):** DELL, LLY, and FIX were explicitly opened by the portfolio-arbiter at 17:04 (BUY verdicts). The portfolio-verifier ran at 18:05 (one scan later) and dust-swept all three with `target=0`. This means the verifier was reconciling toward a different Opus target than the one that had just been set — most likely a stale or rolled-back selector state. The verifier should never dust-sweep positions that were opened by the arbiter in the immediately preceding scan.

- **Gap_only entries not blocked upstream:** WDC was classified "gap_only" (no continuation) at exit, but was still admitted by discovery and selected by the arbiter. A stock only up on gap with fading volume and no continuation should be filtered at the discovery stage, not discovered and then immediately exited.

- **HCAI oversized above initial_entry_cap_pct:** The arbiter proposed 18.2% for HCAI (1492 shares × $11.84 = $17,665 on a $99.6k book = 17.7%). `initial_entry_cap_pct: 0.15` is in config but was not enforced at execution. When it stopped out -9.71%, the oversized position cost ~$1,716 vs ~$1,455 if capped at 15%.

- **SOXS (inverse ETF) proposed by portfolio-selector:** The final scan's selector output included SOXS ("ProShares UltraShort Semiconductors") as one of 6 selected positions with a 12.87% target weight. SOXS is an inverse/leveraged ETF — it violates the hard "Long US equities only" constraint. It did not execute (execution_target_weights omitted it), but the selector should never propose it. This is a code-level filtering gap.

- **SPY proxy execution gap:** At the same final scan, the selector set `spy_target_pct: 0.0` and targeted 6 equity positions at ~94% combined weight. Execution only deployed ~35% (AXTX 14.4%, PWR 11.1%, META 9.5%), leaving SPY at ~60% of the book. The large SPY cash-proxy position was effectively ignored by the rebalancer — the bot finished the day 60% SPY despite explicitly targeting 0%.

- **AI confidence inconsistency scan-to-scan:** INTC was BUY (conf=0.78) at 15:30 and exited at 17:03 same day. TSLA was BUY (conf=0.88) at 15:30, exited at 17:04. AMD BUY at 17:04, exited at 19:03 same day. The model is generating high-confidence BUY signals and then high-confidence EXIT signals on the same positions within 60–90 minutes. This points to intraday signal noise being over-weighted relative to the position's entry thesis.

- **26 order failures (13% failure rate):** 26 of ~200 submitted orders returned `ai_order_failed`. Failure reasons not captured in trades.jsonl but likely include Alpaca fractional-share validation errors or wash-trade rejections. Each failure represents a missed execution on a position the arbiter intended to open/close.

---

### 2c. Proposed Changes

#### P1 — Add minimum hold period before arbiter can exit a newly-opened position
**Why:** On both 5/1 and 5/4, the bot opened positions and the arbiter exited them 1–2 scans (60–120 minutes) later citing "momentum=0" or "fading" — the same signals that would have been visible at entry. A 2-scan (120-minute) cooling-off window for exits on fresh positions would eliminate at least 7 of the 15 same-day churn events and save the round-trip friction.

**Proposed config diff:**
```yaml
# config.yaml — under exit_arbiter:
exit_arbiter:
  min_confidence: 0.55
+ min_hold_scans: 2        # arbiter cannot exit a position opened < 2 scans ago (unless stop hit)
```

**Expected impact:** Eliminates ~7–8 same-day flip exits per active trading day. At $200–$500 friction each, saves $1.5k–$4k/day on churn days. Eliminates the 5/4 pattern entirely.

---

#### P2 — Verifier must not dust-sweep positions entered in the current scan session
**Why:** DELL, LLY, and FIX were entered by the arbiter at 17:04 and dust-swept by the verifier at 18:05. The verifier reconciled against a stale target set, overriding the live arbiter decision. This is a coherence failure: the arbiter and verifier are operating on different state.

**Proposed config diff:**
```yaml
# config.yaml — under portfolio_verifier:
portfolio_verifier:
  enabled: true
  tolerance_pct_of_equity: 0.005
  min_corrective_usd: 50
+ skip_dust_sweep_min_age_scans: 1   # never dust-sweep a position entered in the preceding scan
```

**Expected impact:** Prevents 3 of 5/4's churn events (DELL, LLY, FIX). Ensures verifier only corrects drift, not valid new entries.

---

#### P3 — Block inverse/leveraged ETFs from selector universe (code fix)
**Why:** SOXS appeared in the portfolio-selector's `selected_positions` output with a 12.87% target weight, directly violating "Long US equities only". Although execution omitted it, the selector should never propose it — the AI prompt cannot reliably self-filter.

**Proposed config change:**
```yaml
# config.yaml — under universe:
universe:
  exclude_tickers: []
  # Add hard exclusion list for inverse and leveraged short ETFs
+ exclude_tickers:
+   - SOXS
+   - SPXS
+   - SQQQ
+   - SH
+   - PSQ
+   - UVXY
+   - SVXY
```

Additionally, `src/discovery.py` should filter candidates with ETF name containing "Short", "UltraShort", "Inverse", or "Bear" before adding to the pool.

**Expected impact:** Eliminates inverse ETF proposals from selector. No performance trade-off — these instruments cannot legally be selected by the current strategy.

---

#### P4 — Enforce `initial_entry_cap_pct` hard limit in executor for all AI-submitted orders
**Why:** HCAI was submitted at 18.2% of book ($17,665) when `initial_entry_cap_pct: 0.15` (15% = ~$14,900 max). The executor did not cap it. The 17.7% position stopped out at -9.71%, costing $1,716. At 15% it would have cost $1,449 — a $267 overexposure. More importantly, the gap between arbiter-requested and executor-enforced sizing is undefined and untested.

**Proposed code check in `src/executor.py`:**
The executor should, for every `ai_order_submitted` where `is_new_entry=True`, verify that `requested_notional / equity <= initial_entry_cap_pct`. If exceeded, silently cap qty to `floor(equity * initial_entry_cap_pct / price)` and log the override.

**Proposed config change (tighten cap to add enforcement buffer):**
```yaml
# config.yaml — under risk:
risk:
- initial_entry_cap_pct: 0.15
+ initial_entry_cap_pct: 0.13    # tighter to absorb pricing rounding; AI arbiter still free to stage below this
```

**Expected impact:** Reduces maximum new-entry loss per position by ~13%. Closes the enforcement gap so the stated config actually binds.

---

#### P5 — Block discovery of gap_only candidates with no continuation confirmation
**Why:** WDC was classified "gap_only" at the time of its exit (1h after entry). The gap-only classification — a stock up purely on an opening gap with fading volume and no subsequent trend — should filter candidates out at discovery, not serve as an exit trigger after money is deployed. The discovery/screener already has `continuation_gate.min_score: 55`; a gap_only override should hard-block any stock whose TV screener or AV intraday pattern is gap_only with no continuation.

**Proposed config diff:**
```yaml
# config.yaml — under selector.continuation_gate:
selector:
  continuation_gate:
    enabled: true
    min_score: 55
    allow_missing_intraday: false
+   block_gap_only: true          # reject candidates classified gap_only with volume fading
```

**Expected impact:** Prevents WDC-style entries. Reduces false-positive BUY gates triggered by morning-gap momentum that dissipates within one scan.

---

#### P6 (Operational) — Fix scheduler / confirm bot is running
**Why:** 27 trading days (~38 calendar days) with zero scans, trades, or EOD snapshots since 2026-05-04. This is the single highest-priority issue. The account is frozen at the 5/4 EOD state: ~60% SPY, AXTX 14.6%, PWR 11.1%, META 9.5%, 5% cash. Without active scanning, no proposals in P1–P5 can be validated or corrected.

**Action checklist (operational, not a code/config change):**
1. Confirm cron/scheduler on the runtime host fired after 2026-05-04 (check `systemctl status`, `crontab -l`, or GitHub Actions logs).
2. If scheduler fired but artifacts not committed — check `data/research/` and `data/journal/` mtimes on the runtime host vs. this checkout.
3. Check Alpaca dashboard for PA34KBGT3V7E: if positions are still AXTX/META/PWR/SPY from 5/4, the bot is fully frozen.
4. Check for API key expiry: ALPHA_VANTAGE_API_KEY, ANTHROPIC_API_KEY, Alpaca credentials.
5. Once scheduler is restored, run `py scripts/scan_and_trade.py --dry-run` first to confirm pipeline integrity before live execution.

---

### 2d. Backtests

**P1 (min-hold timer):** Offline backtest on journal data. Same-day flips on 5/1 and 5/4 contributed an estimated **-0.4% to -0.8%** in round-trip losses and friction across the two days, assuming $300–$600 spread/slippage per round-trip × 15 events. Full backtest requires live intraday bar data (blocked). **Cannot quantify precisely offline.**

**P2 (verifier coherence):** The 5/4 verifier swept DELL/LLY/FIX within one scan of entry. Had they been held, each would have survived ~1h until the 19:08 scan (where FIX was swept again). Net impact: negligible on P&L (all three showed tiny gains before sweep). Value is avoiding unnecessary churn overhead and preventing the arbiter/verifier deadlock pattern. **Cannot backtest without multi-scan replay.**

**P3–P5 (filter fixes):** These are correctness fixes, not parameter tuning. No backtest applicable — they prevent specific failure modes that already occurred.

---

## Open items carried forward (from prior reviews, still untested)

8 proposals from the 2026-05-05 review (selector inertia / Jaccard floor, earnings-flag stickiness, min-hold timer — partially addressed by P1 above, preclose close-fill verifier, intraday turnover cap, SPY-proxy chaos-day rule, red-tape BUY gate, sticky-portfolio cadence) remain open and unvalidated due to the scheduler outage. Reference: `data/research/2026-05-05_daily_review.md`.

**Operational priority overrides all strategy proposals.** Until the scheduler is restored and data is flowing again, none of these proposals can be validated or have meaningful expected impact estimates.
