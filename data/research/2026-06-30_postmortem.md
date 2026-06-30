# Post-Mortem 2026-06-30

## Data Availability

**⚠️ EIGHTH CONSECUTIVE NO-DATA REPORT.** No trading data exists for 2026-06-30 or for any date since 2026-05-04 (~57 calendar days / ~40 trading days of silence). All performance analysis below references the **last available snapshot: 2026-05-04 EOD**.

| Source | Newest on disk | Status |
|---|---|---|
| `_eod.json` | `2026-05-04_eod.json` | **57-day gap** |
| `_scan.json` | `20260504T195545_preclose.json` | **57-day gap** |
| `trades.jsonl` | last event `2026-05-04T19:55Z` (204 lines) | **frozen** |
| `decisions.jsonl` | last event `2026-05-04T20:15Z` (1556 lines) | **frozen** |
| `_daily_review.md` | `2026-06-23_daily_review.md` | 7 prior no-data reports |

Root cause (unchanged from prior reviews): `scan_and_trade.py` and related scripts have not run since 2026-05-04. Alpaca account PA34KBGT3V7E likely still holds the 5/4 end-of-day positions frozen for ~40 trading days.

---

## Performance Today (2026-06-30)

**No snapshot available.** Last known equity: **$99,850** (2026-06-30 has no EOD file).

### Last Known Day (2026-05-04)

| Metric | Bot | SPY | Delta |
|---|---|---|---|
| Daily return | **-1.80%** | -0.36% | **-1.44%** |
| Equity | $99,850 | — | — |
| Cash | $4,987 (5.0%) | — | ✓ at floor |
| Positions | 4 | — | — |

### Rolling Benchmark (all 9 tracked days: 2026-04-22 → 2026-05-04)

| Period | Bot | SPY | Alpha |
|---|---|---|---|
| 9-day cumulative | **-16.31%** | +1.95% | **-18.26%** |
| Last 5d (4/28–5/4) | -12.66% | +0.38% | -13.04% |
| SPY 30-day (as of 5/4) | — | +10.71% | — |

> Bot is deeply underwater vs SPY on every measured horizon.

---

## Positions at Close (Last Known: 2026-05-04 EOD)

Computed from `avg_entry` and `current_price` per hard rule (Alpaca `unrealized_plpc` not trusted).

| Symbol | Side | Qty | Avg Entry | Last Price | P&L% | Market Value | Weight |
|---|---|---|---|---|---|---|---|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** | $14,589 | 14.6% |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** | $9,448 | 9.5% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** | $11,130 | 11.1% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** | $59,696 | 59.7% |
| Cash | — | — | — | — | — | $4,987 | 5.0% |

> Book has been **frozen at this allocation for ~40 trading days** with no confirmed activity.

---

## Trades Today (2026-06-30)

**No trades logged.** Last active trading day: 2026-05-04 (53 events across 17 symbols).

### Summary of Last Active Day (2026-05-04)

| Event type | Count |
|---|---|
| `ai_order_submitted` (entries) | 15 |
| `position_closed` (exits) | 11 |
| `wash_trade_recovery` | 3 |
| `exit_learning_metrics` | 24 |
| **Total** | **53** |

Unique symbols touched: AMZN, AXTX, COIN, DELL, FIX, GEV, GOOGL, HCAI, LLY, META, MU, NOK, PWR, SNDK, STX, UNH, WDC (17 names in one session).

---

## Per-Trade Ledger (Last Active Session: 2026-05-04)

### Exits

| Symbol | Entry (avg) | Exit | Qty | P&L$ | P&L% | AI Grade | Verdict |
|---|---|---|---|---|---|---|---|
| HCAI | $11.84 | $10.69 | 1492 | -$1,715 | **-9.71%** | exit-arbiter exit conf=0.72 | Bad — bought illiquid micro-cap, -9.71% stop-out |
| SNDK (lot 1) | $1,140.78 | $1,250.00 | 23.3 | +$2,540 | **+9.56%** | selector EXIT (replace by MU) | Good exit, but missed $107 leaving 30m early |
| SNDK (lot 2 — re-entry) | $1,246.97 | $1,237.52 | 10.1 | -$95 | **-0.76%** | selector EXIT within 6 min | **Churn** — re-entered near top, stopped in 6 min |
| AMZN | ~$265 est. | $270.65 | 65.3 | est. +$360 | ~+2.1% | exit-arbiter reduce conf=0.62 | Marginally OK — fading momentum |
| GEV | unknown | $1,071.49 | 14.6 | unknown | unknown | exit-arbiter hold conf=0.62, selector overrode→EXIT | **Bad** — exit_arbiter said hold; selector overrode |
| UNH | $371.09 | $368.25 | 17.3 | -$49 | **-0.77%** | exit-arbiter reduce conf=0.62 | Marginal — "fading volume"; established name |
| MU | $580.42 | $580.81 | 23.0 | +$9 | **+0.07%** | exit-arbiter reduce conf=0.58 | **Churn** — entered and flat-exited same day |
| WDC | $445.36 | $440.06 | 24.5 | -$130 | **-1.19%** | selector EXIT | **Churn** — entered and stopped same day |
| DELL | $210.52 | $210.94 | 57.4 | +$24 | **+0.20%** | verifier dust-sweep | **Churn** — verifier forced close of same-day entry |
| LLY | $962.27 | $963.71 | 13.0 | +$19 | **+0.15%** | exit-arbiter hold conf=0.62, verifier dust-swept | **Churn** — exit-arbiter said hold; verifier dust-swept it anyway |
| COIN | $203.90 | $203.45 | 66.9 | -$30 | **-0.22%** | exit-arbiter reduce conf=0.58 | **Churn** — entered at ~14%, immediately reduced to 0% |
| GOOGL | $384.43 | $382.77 | 9.28 | -$15 | **-0.43%** | exit-arbiter reduce conf=0.58 | **Churn** — verifier reconcile buy, then arbiter exit same session |
| FIX | $1,903.71 | $1,902.81 | 3.7 | -$3 | **-0.05%** | verifier dust-sweep | **Churn** — FIX had 3 wash trade collisions; verifier dust-swept |

### Surviving Positions (5/4 EOD → frozen)

| Symbol | Entry | Last | Qty | P&L% | Grade |
|---|---|---|---|---|---|
| AXTX | $46.41 | $46.61 | 313 | +0.43% | **Risk** — 2x leveraged ETF; violates no-leverage spirit; held frozen for 40 days |
| META | $611.73 | $610.46 | 15.5 | -0.21% | Hold — sector leader, barely off entry |
| PWR | $758.48 | $757.38 | 14.7 | -0.15% | Hold — data-center power; just entered |
| SPY | $717.52 | $718.03 | 83.1 | +0.07% | Cash proxy; ~60% of book |

---

## Cross-Trade Patterns (2026-04-22 → 2026-05-04)

- **Extreme intraday churn.** 5/4: 15 entries + 11 exits in a single session across 17 symbols. 7 confirmed same-day round trips (WDC, DELL, LLY, COIN, GOOGL, FIX, MU) plus SNDK re-entered near top and stopped in 6 minutes. The selector can legally replace the entire portfolio in one scan — there is no friction or inertia requirement.
- **Exit-arbiter model mismatch.** All 13 exit-arbiter decisions on 5/4 ran on `claude-sonnet-4-6` (non-critical), not the trade-critical model. CLAUDE.md specifies Opus 4.7 for exit-arbiter. This is a routing bug or config drift. The model drop may explain the confidence cluster at 0.58–0.62 (barely above the 0.55 min_confidence floor).
- **Exit-arbiter overridden by selector/verifier.** GEV and LLY both received `action=hold` from exit_arbiter (conf=0.62), yet were closed: GEV by the selector's EXIT rotation, LLY by the verifier's dust-sweep. The selector and verifier each have independent veto power over exit_arbiter's hold recommendations — 3-way authority conflict with no tie-breaker.
- **Leveraged ETF entered (AXTX).** `AXTX` = "Tradr 2X Long AXTI Daily ETF" — a 2x daily leveraged product. The bot's constraint is "Long US equities only (no shorts, no crypto)." No explicit check exists for leveraged ETFs. AXTX entered at 14.4% weight, is now frozen at ~14.6% of the book for 40+ trading days, subject to daily compounding decay.
- **SPY proxy destabilized.** On 5/4 15:13 scan, SPY was cut from ~36% to 5% to "fund superior individual equity opportunities." All individual names bought (AMZN, GEV, COIN, MU) were exited within the same session. Net result: ~$30K+ SPY churned round-trip in one day.
- **Wash trade collisions (3 events).** FIX and GOOGL triggered broker wash-trade errors because a standing sell-stop from one scan conflicted with a new buy on the same symbol in the next scan. The bot handles recovery, but 3 collisions in one day signals the lifecycle is cycling faster than stop orders can settle.
- **Cumulative underperformance.** Over 9 tracked days (4/22–5/4): portfolio -16.31%, SPY +1.95%, alpha -18.26%. SPY's trailing 30-day return as of 5/4 was +10.71%. The "beat SPY" objective has been missed on every available horizon.
- **Bot inactive for ~40 trading days.** With AXTX frozen and 2x leveraged daily-rebalancing, compounding decay is accruing with no exit mechanism running.

---

## Proposed Changes

### Proposal 1 — Block leveraged ETFs in config (High priority)

**Why:** AXTX is a 2x daily leveraged product held frozen for ~40 trading days, accruing compounding decay. The "no leverage" policy has no enforcement mechanism.

**Diff (config.yaml):**
```yaml
# BEFORE
universe:
  exclude_tickers: []

# AFTER
universe:
  exclude_tickers:
    - AXTX   # 2x leveraged ETF — violates no-leverage policy; forces exit on next restart
```

**Expected impact:** AXTX closed on next bot restart. Future similar tickers blocked at eligibility scan.

---

### Proposal 2 — Code-level leveraged ETF guard in executor.py

**Why:** Config can be overwritten. A code-level guard blocks leveraged ETFs regardless of config state.

**Diff (src/executor.py — illustrative):**
```python
# BEFORE: no guard exists in _submit_buy

# AFTER: add before order submission
_LEVERAGED_PATTERNS = ['2X', '3X', 'TQQQ', 'SOXL', 'SOXS', 'UVXY', 'LEVERAGED', 'INVERSE']

def _is_leveraged(self, symbol: str, asset_name: str = '') -> bool:
    return any(p in f"{symbol} {asset_name}".upper() for p in _LEVERAGED_PATTERNS)

# In _submit_buy: reject before placing order
if self._is_leveraged(symbol, asset_info.get('name', '')):
    logger.warning(f"[BLOCKED] {symbol} is leveraged ETF — no-leverage policy enforced.")
    return None
```

**Expected impact:** Hard block; no config bypass possible.

---

### Proposal 3 — Min-hold timer (4h) to prevent same-day exits

**Why:** 7 same-day round trips on 5/4 generated ~$273 in combined P&L drag + estimated slippage on $73K notional. More critically, same-day churn means no swing thesis can play out.

**Diff (config.yaml):**
```yaml
# BEFORE
risk:
  exit_stall_threshold: 0.10

# AFTER
risk:
  exit_stall_threshold: 0.10
  min_hold_hours: 4              # NEW: block exits < 4h after entry (stop-loss hits exempt)
  min_hold_exempt_loss_pct: -0.03  # NEW: bypass min_hold if position down >3%
```

**Offline backtest (in-repo journal data only):**
- 5/4: 7 round trips, $73K notional touched. Friction saved: ~$127 P&L + ~$146 slippage = **$273 / 0.27%** of equity.
- 9-day dataset: 5/4 is the only heavy-churn day; upper-bound total savings across all 9 days ≈ $273.
- Limitation: 40-day frozen period not testable without live prices.

---

### Proposal 4 — Intraday new-entry cap (≤3 per scan)

**Why:** 5/4 had 15 new entries across 6 scans (avg 2.5/scan). A swing bot should not be replacing its entire book every 90 minutes.

**Diff (config.yaml):**
```yaml
# BEFORE
ai:
  max_candidates_per_scan: 5

# AFTER
ai:
  max_candidates_per_scan: 5
  max_new_entries_per_scan: 3   # NEW: cap at 3 brand-new positions per scan
```

**Expected impact:** On 5/4 would have capped 15 entries to ≤18 across all 6 scans (vs actual 15 in bursts), forcing the selector to prioritize conviction over breadth. Reduces wash-trade collision rate.

---

### Proposal 5 — Raise exit_arbiter min_confidence to 0.65

**Why:** 8 of 13 exit_arbiter decisions on 5/4 came in at 0.58–0.62 (barely above 0.55 floor). Two of those (GEV=hold, LLY=hold) were correct calls that were overridden. The low-confidence cluster likely reflects the Sonnet model being uncertain — Opus would likely produce cleaner separation.

**Diff (config.yaml):**
```yaml
# BEFORE
exit_arbiter:
  min_confidence: 0.55

# AFTER
exit_arbiter:
  min_confidence: 0.65
```

**Expected impact:** Would have blocked ~8/13 exit actions on 5/4. Combined with the Opus model fix (below), this eliminates a large class of low-conviction churn exits.

---

### Critical: Verify exit-arbiter model routing

**Why:** All 13 exit_arbiter decisions on 5/4 used `claude-sonnet-4-6`. The CLAUDE.md spec says `ai.trade_critical_model` (Opus 4.7) should drive exit_arbiter. Current `config.yaml` shows `trade_critical_model: claude-sonnet-4-6` — this is set to Sonnet, not Opus.

**Action (config.yaml — verify before changing):**
```yaml
# CURRENT (problematic)
ai:
  trade_critical_model: claude-sonnet-4-6

# RECOMMENDED
ai:
  trade_critical_model: claude-opus-4-7
```

This single change upgrades all trade-critical agents simultaneously: exit-arbiter, decision-arbiter, portfolio-selector, portfolio-arbiter, earnings-gate.

---

## Backtests Run

| Proposal | Test | Result | Confidence |
|---|---|---|---|
| Leveraged ETF block (Props 1–2) | AXTX asset name confirmed "Tradr 2X Long" in trades.jsonl | Definitive block | **High** |
| Min-hold timer (Prop 3) | Counted 7 round trips; estimated $127 P&L drag + $146 slippage | $273 / 0.27% on 5/4 | **Low** (1 day; no 40-day data) |
| Entry cap (Prop 4) | 15 entries on 5/4 vs theoretical cap of 18 (3×6 scans) | Would reduce burst churn | **Low** (qualitative only) |
| Confidence floor (Prop 5) | 8/13 decisions at 0.58–0.62 would be blocked | ~62% reduction in exit rate on 5/4 | **Medium** (counterfactual) |
| Opus model fix | Sonnet confirmed in all decisions; Opus config intent mismatch | Affects all 5 trade-critical agents | **Medium** (Opus output not observable offline) |

**Backtest limitation:** yfinance and Alpaca blocked in this container. Frozen-book analysis (AXTX/META/PWR/SPY from 5/4 to now) cannot be computed offline. Requires Yahoo Finance egress allowlist or out-of-band analysis.

---

## Operational Status (Priority 0)

**~57 calendar days / ~40 trading days of silence.** Strategy proposals are moot until the bot is confirmed running.

Unresolved checklist (carried from prior reviews):

1. [ ] Confirm `scripts/scan_and_trade.py` has fired since 2026-05-04 — check cron/launchd/systemd/GitHub Action logs
2. [ ] Confirm write path: `data/research/` and `data/journal/` on runtime host match this repo checkout
3. [ ] `git log -- data/research/` on runtime host — look for unpushed commits
4. [ ] Log into Alpaca PA34KBGT3V7E dashboard — confirm positions and equity vs 5/4 last-known state ($99,850, 4 positions)
5. [ ] **NEW — urgent:** Confirm whether AXTX is still open; if yes, close it manually (2x leveraged, 40-day hold, no stop running)
6. [ ] **NEW:** Verify `ai.trade_critical_model: claude-opus-4-7` in live config (currently set to Sonnet in repo)
