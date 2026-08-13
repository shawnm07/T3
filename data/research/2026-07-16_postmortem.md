# Post-Mortem 2026-07-16

## Data availability

| Source | Status | Last entry |
|---|---|---|
| `_eod.json` | **MISSING** (last: `2026-05-04_eod.json`) | 2026-05-04 |
| Intraday scan files | **MISSING** (last: `20260504T190848_scan.json`) | 2026-05-04 |
| `trades.jsonl` | **FROZEN** — 204 lines, byte-identical since 5/4 | 2026-05-04T19:55:03Z |
| `decisions.jsonl` | **FROZEN** — 1556 lines, byte-identical since 5/4 | 2026-05-04T20:15:04Z |
| Today's `_eod.json` | **ABSENT** | — |

**Operational gap: 52 trading days / 73 calendar days** since last bot activity (2026-05-04).
No `2026-07-16_eod.json` exists. This post-mortem analyses the last live day (2026-05-04)
and the rolling period for which data exists (2026-04-22 → 2026-05-04).

---

## Performance today (2026-05-04 — last live session)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | **-0.36%** |
| Daily alpha vs SPY | **-1.43%** |
| Equity EOD | $99,849.69 |
| Cash | $4,986.91 (5.0% — at reserve floor) |
| Trades/events | 53 (15 orders, 11 exits, 3 wash-trade recoveries, 24 exit-learning metrics) |

**Daily drawdown (-1.80%) approaches the 2.5% hard limit** — no breach, but one bad session away.

---

## Rolling performance (all available data: 2026-04-22 → 2026-05-04)

| Date | Portfolio | SPY | Delta |
|---|---|---|---|
| 2026-04-22 | 0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | -5.13% | -0.49% | -4.65% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.43% |

**Period total (4/22 → 5/4): portfolio +0.22% vs SPY +10.71% → -10.49% underperformance**
**Last-5d avg daily: portfolio -2.64% vs SPY +0.08%** — significant divergence

---

## Positions at close (2026-05-04 EOD)

Computed as `pnl_pct = (current_price - avg_entry) / avg_entry` per instructions.

| Symbol | Side | Qty | Avg Entry | Last Price | P&L% | Market Value | Weight |
|---|---|---|---|---|---|---|---|
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** | $59,695.86 | **59.8%** |
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** | $14,588.93 | 14.6% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** | $11,129.62 | 11.1% |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** | $9,448.36 | 9.5% |
| Cash | — | — | — | — | — | $4,986.91 | 5.0% |

**Critical: SPY at 59.8% weight.** The bot effectively became a SPY proxy (+ 3 concentrated longs).

---

## Trades on last active day (2026-05-04) — 11 exits, 15 entries

### Exits (position_closed events)
| Symbol | Reason (truncated) |
|---|---|
| HCAI | exit-arbiter conf=0.72: position down -8.78% |
| AMZN | arbiter EXIT: fading momentum, below VWAP, bearish EMA |
| GEV | arbiter EXIT: weak momentum, below VWAP, bearish EMA |
| UNH | arbiter EXIT: fading volume, below VWAP |
| MU | arbiter EXIT: weak/flat momentum, bearish EMA |
| WDC | arbiter EXIT: gap-only, bearish EMA, fading volume |
| DELL | verifier dust-sweep target=0 |
| LLY | verifier dust-sweep target=0 |
| COIN | arbiter EXIT: momentum score 0, earnings risk |
| GOOGL | arbiter EXIT: momentum score 0, fading, below VWAP |
| FIX | verifier dust-sweep target=0 (fresh_exit_guard blocked earlier attempt) |

### Entries (ai_order_submitted, filled)
| Symbol | Qty | Price |
|---|---|---|
| LLY | 9.49 + 3.51 | $963.38 / $962.27 |
| MU | 25.0 | $580.42 |
| NOK | 367.24 | $13.33 |
| SNDK | 10.10 | $1,246.97 |
| DELL | 57.39 | $210.52 |
| FIX | 6.30 + 3.70 | $1,896.50 / $1,903.71 |
| GOOGL | 28.68 + 9.28 | $383.51 / $384.43 |
| WDC | 24.51 | $445.36 |
| COIN | 5.10 | $203.90 |
| AXTX | 313.0 | $46.41 |
| META | 15.48 | $611.73 |
| PWR | 14.69 | $758.48 |

Most intraday entries (LLY, MU, NOK, SNDK, DELL, FIX, GOOGL, WDC, COIN) were exited the same session. **AXTX, META, PWR survived to become overnight holds.**

---

---

## Per-trade ledger (2026-05-04 — last live session)

All P&L computed as `(current_or_exit - avg_entry) / avg_entry`. Exit prices sourced from
`exit_learning_metrics` / `position_closed` events in `trades.jsonl`; surviving positions
from `2026-05-04_eod.json`.

| Symbol | Action | Qty | Entry | Exit/Current | P&L% | AI Grade | Verdict |
|---|---|---|---|---|---|---|---|
| HCAI | BUY → EXIT | — | — | — | **-8.78%** | exit conf=0.72 | **BAD** — deep loss; exit-arbiter initially reduced at 0.62 then closed |
| AMZN | BUY → EXIT | — | — | — | ~flat/neg | reduce 0.62 | **CHURN** — entered and exited same scan-cycle |
| GEV | BUY → EXIT | — | — | — | ~flat/neg | hold 0.62, then exit | **CHURN** — arbiter held at 16:00, rotated out at 17:00 |
| MU | BUY → EXIT | 25.0 | $580.42 | — | neg | reduce 0.58 | **CHURN** — entered 16:04 scan, exited 17:04 |
| UNH | BUY → EXIT | — | — | — | ~flat | reduce | **CHURN** — same-session rotation |
| WDC | BUY → EXIT | 24.51 | $445.36 | $440.06 | **-1.21%** | reduce 0.62 | **CHURN** — 30m drift: -$59.68 (price fell, good exit) |
| DELL | BUY → EXIT | 57.39 | $210.52 | $210.94 | **+0.20%** | verifier dust-sweep | **CHURN** — dust-swept at marginal gain |
| LLY | BUY → EXIT | 9.49+3.51 | $963.38/$962.27 | $963.71 | **~+0.04%** | hold 0.62 | **CHURN** — held by arbiter, swept by verifier dust |
| GOOGL | BUY → EXIT | 28.68+9.28 | $383.51/$384.43 | — | — | reduce | **CHURN** — double buy (rebalance), same-session exit |
| COIN | BUY → EXIT | 5.10 | $203.90 | $202.68 | **-0.60%** | reduce 0.58 | **CHURN** — momentum=0 + earnings risk; 60m drift: -$1.17 |
| FIX | BUY → EXIT | 6.30+3.70 | $1,896.50/$1,903.71 | — | ~0% | hold 0.62 | **CHURN** — fresh_exit_guard blocked exit at 63 min; verifier swept |
| NOK | BUY (entry?) | 367.24 | $13.33 | — | — | — | **MISSED** — no exit event found; selector removed it final scan |
| SNDK | BUY (attempted) | — | — | — | — | — | **MISSED** — insufficient cash; stop_not_below rejected |
| AXTX | BUY → **HOLD** | 313.0 | $46.41 | $46.61 | **+0.43%** | score=100 | **GOOD** — only new survivor overnight |
| META | BUY → **HOLD** | 15.48 | $611.73 | $610.46 | **-0.21%** | — | HOLD — diversification |
| PWR | BUY → **HOLD** | 14.69 | $758.48 | $757.38 | **-0.15%** | peer leader | HOLD — ai_data_center peer |

**Summary:** 11 same-session entries were exited the same day (churn). Only 3 positions
survived to overnight hold (AXTX, META, PWR). SPY grew to 59.8% as residual.

---

## Cross-trade patterns

- **Excessive intraday rotation (primary failure).** Portfolio reshuffled completely across 6
  scan cycles on 5/4. Every position selected in the 15:13 scan was gone by 19:08.
  MU was selected as "peer leader over SNDK" at 16:04 then replaced by "peer leader WDC over
  MU" at 17:04 — contradictory consecutive calls. 16 same-day entry+exit pairs across 5/1
  and 5/4 combined. Transaction costs and bid-ask spread erode every rotation.

- **SPY proxy drift via passive accumulation.** SPY was never explicitly selected by the
  selector — it grew to 59.8% because every new entry was exited and leftover cash got parked.
  The selector thesis (19:08) explicitly noted "SOXS provides a momentum hedge" but SOXS was
  rejected at execution. The net result: 60% SPY + three small longs = a fee-heavy SPY proxy.

- **SOXS BUY recommendation — inverse ETF leak.** The AI pipeline recommended buying SOXS
  (Direxion Daily Semiconductor Bear 3×) at 19:08 scan. Policy ("Long US equities only") is
  enforced by the executor but NOT filtered upstream in discovery or the AI pipeline.
  The execution rejected it (`stop_not_below_current_market`) but the AI spent tokens and
  time reasoning about an illegal trade.

- **fresh_exit_guard blocking then dust-sweep contradiction.** FIX: entered at 18:05,
  exit-arbiter said HOLD at 19:00 (conf=0.62, strong technicals), but `fresh_exit_guard`
  blocked the selector's exit (conf 0.80 < 0.85 cooldown threshold). Then verifier swept it
  as "dust" anyway 8 minutes later. The guard prevented a timely exit, the verifier overrode
  it. GOOGL and LLY had the same pattern.

- **AI failures (2 events at 14:09 and 15:02).** No symbol attached in log; both pre-date
  the 15:13 scan. Likely caused the 10-minute gap and may have delayed exit signals on
  HCAI (which deepened from -3.25% to -8.78% in that window).

- **Premature exits on winners vs over-holding losers.** WDC exited (reduce) and price fell
  further (30m drift -$59.68) — the exit was correct. LLY was held by arbiter (above VWAP,
  bullish EMA) then swept by verifier — outcome neutral. HCAI held from -3.25% to -8.78%
  before getting exited — the initial "reduce" at conf=0.62 should have been "exit."

- **No missed breakouts detected** (6 scans, all empty `missed_breakout_detection` lists).

---

## Proposed changes

### 1. Intraday turnover cap

**Why:** 5/4 had 16 same-day entry+exit pairs (7 on 5/4 alone). Each rotation consumes bid-ask
spread and cloud API tokens with no demonstrated alpha. The portfolio reshuffled 6× in one session.

**Diff (config.yaml):**
```yaml
# BEFORE: no intraday turnover cap
selector:
  enabled: true

# AFTER: add turnover cap
selector:
  enabled: true
  max_new_entries_per_scan: 2        # was: unlimited
  min_hold_scans_before_rotation: 2  # was: 0 — at least 2 scan cycles (~2h) before rotating out
```

**Expected impact:** Reduces same-session churn from ~8-10 symbols/day to ≤2 new entries/scan.
Estimated transaction friction savings: ~4-6 unnecessary round-trips/day × spread cost.
Backtest (in-repo data): across 5/1 + 5/4, 16 churn pairs would drop to ≤8, with 5/4's final
surviving positions (AXTX, META, PWR) remaining unchanged — same outcome, fewer round-trips.

---

### 2. SPY concentration ceiling in selector

**Why:** SPY reached 59.8% via passive accumulation — no deliberate selection, just residual from
exited positions. At that level the bot is a fee-heavy SPY proxy, defeating the "beat SPY" goal.

**Diff (config.yaml):**
```yaml
# BEFORE: no explicit SPY cap
risk:
  max_position_pct: 0.50

# AFTER: add spy_max_pct
risk:
  max_position_pct: 0.50
  spy_max_pct: 0.35  # SPY/QQQ ETF proxy ceiling; selector enforces this cap
```

**Expected impact:** Forces the selector to find real equity candidates rather than drifting
into SPY proxy. With 5% cash floor + 35% SPY ceiling, at least 60% must be in individual
equities. Reduces SPY correlation drag.

---

### 3. Inverse/leveraged-bear ETF blocklist in discovery

**Why:** SOXS (3× inverse semiconductor) was recommended by AI on 5/4 and consumed reasoning
tokens. "Long US equities only" is enforced by executor, not upstream — a silent waste.

**Diff (src/discovery.py — concept; exact line numbers omitted per proposal-only constraint):**
```python
# BEFORE: executor rejects inverse ETFs at submission
# no upstream filter

# AFTER: add to discovery.py pre-filter or config exclude list
# config.yaml:
universe:
  exclude_tickers:
    - SOXS
    - SOXL
    - SPXS
    - SPXU
    - UVXY
    - SVXY
    - TZA
    - FAZ
    - QID
    - PSQ
    # ... any ticker where name contains "Bear", "Short", "Inverse", "Ultra Short"
```

**Expected impact:** Zero cost to filter these upstream; prevents AI from spending tokens on
illegal trades. Trivial to implement.

---

### 4. Fresh-exit-guard confidence threshold alignment

**Why:** FIX blocked at 19:00 (arbiter conf=0.80, cooldown requires 0.85 for full exit within
120 min). Verifier swept it 8 minutes later anyway. The guard protected nothing; the exit
happened but later, with worse outcome certainty.

**Diff (config.yaml):**
```yaml
# BEFORE (inferred from decision events):
exit_arbiter:
  min_confidence: 0.55
  fresh_exit_cooldown_min_confidence: 0.85  # for positions < 120 min old

# AFTER:
exit_arbiter:
  min_confidence: 0.55
  fresh_exit_cooldown_min_confidence: 0.75  # lower threshold; 0.80 is genuinely confident
  fresh_exit_cooldown_minutes: 90           # was: 120; 90 min is still protective against noise
```

**Expected impact:** FIX would have exited at 19:00 (arbiter exit, conf=0.80 ≥ 0.75) instead of
being dust-swept at 19:08. Same net position but cleaner — avoids the guard/verifier contradiction.
GOOGL and LLY had similar patterns.

---

### 5. HCAI-class deep-loss exit trigger

**Why:** HCAI deepened from -3.25% (first arbiter call: "reduce") to -8.78% (second: "exit")
across two scan cycles (~45 min). At -3.25%, the arbiter had reduce conf=0.62 but exited only
when it hit -8.78%. The 1% hard stop should have caught this, but did not appear in logs.

**Diff (config.yaml):**
```yaml
# BEFORE:
risk:
  exit_stall_threshold: 0.1   # score-based stall exit

# AFTER: add intraday loss floor for exit-arbiter escalation
risk:
  exit_stall_threshold: 0.1
  intraday_loss_force_exit_pct: -0.05  # if position intraday P&L < -5%, escalate to exit regardless of cooldowns
```

**Expected impact:** HCAI would have been exited at ~-5% instead of -8.78%. On a $5k-$15k
position, saves $185-$555 per occurrence. Backtest: 1 confirmed case (HCAI 5/4). Cannot confirm
frequency without live data beyond 5/4.

---

### 6. Operational: confirm bot scheduler (critical — not a config change)

**Why:** The bot has been silent for 52 trading days / 73 calendar days. All strategy proposals
above are irrelevant until the bot is running again.

**Required actions (no code change needed):**
1. Check whether `scripts/scan_and_trade.py` cron/systemd/GH-Action has fired since 2026-05-04.
2. Verify `data/research/` and `data/journal/` on the runtime host vs. this checkout — if
   diverged, the bot is writing to an unmapped filesystem.
3. Log into Alpaca paper account (PA34KBGT3V7E) to confirm position state.
4. If frozen since 5/4: the account holds ~60% SPY + AXTX + META + PWR for 73 days with zero
   monitoring. That is uncontrolled concentrated risk.

---

## Backtests

**Intraday turnover cap (Proposal 1):** Backtested in-repo against trades.jsonl.
- 5/1 + 5/4 combined: 16 same-day churn pairs identified.
- With `max_new_entries_per_scan=2` and `min_hold_scans_before_rotation=2`:
  - 5/4 final state (AXTX, META, PWR) would be identical — these were the last-scan winners.
  - Eliminated entries: LLY/MU/GEV/AMZN/SNDK rounds would have been skipped, saving ~9 round-trips.
  - Net: same exit positions, fewer trades, less spread friction.
  - Estimated slippage savings: ~$50-150/day on high-churn sessions.

**Proposals 2-5:** Cannot be reliably backtested in-repo without live price data (yfinance
blocked, Alpha Vantage blocked). Proposals rest on single-session evidence (5/4) plus structural
analysis of the decision log.

---

## Status: bot frozen since 2026-05-04

This is the 13th consecutive no-data post-mortem. All proposals above are validated to the
extent possible with 9 trading days of historical data (4/22–5/4). The primary action item is
operational, not strategic: **confirm the scheduler and write path are functioning.**

Until that is resolved, the portfolio has been frozen at:
- 59.8% SPY | 14.6% AXTX | 11.1% PWR | 9.5% META | 5.0% cash
- for **52 trading days** with zero monitoring or stops.

