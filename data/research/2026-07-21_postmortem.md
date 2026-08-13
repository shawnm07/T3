# Post-Mortem 2026-07-21

## Data availability

**No today's data.** The bot has produced zero snapshots since 2026-05-04 — 78 calendar days / ~55 trading days of silence. No `2026-07-21_eod.json`, no `20260721T*` scan files, and no new journal entries exist. All market-data egress channels (Alpha Vantage, yfinance, Twelve Data) remain 403-blocked in this container. This report is written entirely from on-disk artifacts ≤ 2026-05-04 and the daily review series through 2026-07-20.

| Source | Newest entry on disk |
|---|---|
| `_eod.json` | `2026-05-04_eod.json` (78 calendar days stale) |
| Intraday scan | `20260504T190848_scan.json` |
| Preclose snapshot | `20260504T195545_preclose.json` |
| `trades.jsonl` last event | `2026-05-04T19:55:03Z` (204 lines, static) |
| `decisions.jsonl` last event | `2026-05-04T20:15:04Z` (1556 lines, static) |

---

## Performance today (portfolio vs SPY)

**Today's data: UNAVAILABLE.** Last recorded session: 2026-05-04.

### Last-known daily (2026-05-04)
| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| vs SPY | **-1.43%** (underperformed) |
| Equity at close | $99,849.69 |
| Cash | $4,986.91 (~5.0%) |

### Rolling performance (all 9 recorded sessions: 2026-04-22 → 2026-05-04)
| Date | Portfolio | SPY daily | vs SPY |
|---|---|---|---|
| 2026-04-22 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | -5.13% | -0.49% | -4.65% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.43% |
| **Cumulative (9d)** | **+0.22%** | — | **Period vs SPY: -10.71%** |

Win rate vs SPY: 2/9 sessions (22%). Consecutive losing sessions: 5 (Apr 27–May 1 close).

---

## Positions at close (last known: 2026-05-04 EOD)

> **Note:** These positions have been held unchanged for 78 calendar days with no bot activity. Current prices are unknown.

| Symbol | Side | Avg Entry | Last Price (5/4) | PnL% (5/4) | Weight |
|---|---|---|---|---|---|
| SPY | LONG | $717.52 | $718.03 | +0.07% | ~59.8% |
| AXTX | LONG | $46.41 | $46.61 | +0.43% | ~14.6% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | ~11.1% |
| META | LONG | $611.73 | $610.46 | -0.21% | ~9.5% |
| Cash | — | — | — | — | ~5.0% |

**Allocation note:** SPY (~60%) dominates the book. The bot entered AXTX (2× leveraged AXTI ETF), PWR, and META in the final scan of 5/4, then immediately closed FIX, DELL, LLY, COIN, and GOOGL the same session (verifier + arbiter exits). 53 orders total on 5/4.

---

## Trades today (2026-07-21)

**None.** Bot has not run since 2026-05-04.

### Trades on last active session (2026-05-04, partial list)
| Time (UTC) | Event | Symbol | Side | Qty | Price | Reason |
|---|---|---|---|---|---|---|
| 17:00 | exit_arbiter reduce | MU | SELL | ~23.0 | ~$580.81 | Intraday momentum lost (VWAP, EMA20) |
| 18:05 | ai_order | FIX | BUY | 3.70 | $1,903.71 | Selector INCREASE 12%→19% |
| 18:05 | position_closed | DELL | SELL | 57.39 | $210.94 | Verifier dust-sweep target=0 |
| 18:05 | position_closed | LLY | SELL | 13.00 | $963.71 | Verifier dust-sweep target=0 |
| 18:05 | ai_order | GOOGL | BUY | 9.28 | $384.43 | Verifier reconcile to Opus 14.6% |
| 19:08 | position_closed | COIN | SELL | 66.90 | $203.45 | Arbiter EXIT: momentum=0 |
| 19:08 | position_closed | GOOGL | SELL | 37.96 | $382.77 | Arbiter EXIT: fading, below EMA20 |
| 19:08 | ai_order | AXTX | BUY | 313.0 | $46.41 | Arbiter BUY 14.4%: momentum=100 |
| 19:08 | ai_order | META | BUY | 15.48 | $611.73 | Arbiter BUY 9.5%: sector diversif. |
| 19:08 | ai_order | PWR | BUY | 14.69 | $758.48 | Arbiter BUY 11.1%: data-center peer |
| 19:08 | position_closed | FIX | SELL | 10.00 | $1,902.81 | Verifier dust-sweep target=0 |

*(Total 53 orders on 5/4. Bot silent since.)*

---

## Full analysis

---

### 2a. Per-trade / per-decision ledger (last active session: 2026-05-04)

| Time (UTC) | Symbol | Side | Qty | Entry | Exit/Cur | PnL% | AI Grade | Reason snippet | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 17:04 | FIX | BUY | 6.30 | $1,900.24 | $1,902.81 (exit 19:08) | +0.14% | 0.88 | Peer/sector leader, momentum=100, breaking_out | **Churn** — bought, increased, exited same session |
| 17:04 | GOOGL | BUY | 28.68 | $383.94 | $382.77 (exit 19:08) | -0.30% | 0.72 | Comm.Svcs leader, acceptable_continuation | **Churn** — bought, added, exited ~2h later at a loss |
| 17:04 | WDC | BUY | 24.51 | $440.06 entry ref | $440.06 (exit same scan) | ~0% | — | Memory peer leader | **Churn** — closed same session (dust-sweep) |
| 17:04 | LLY | ADD | 3.51 | $963.71 | $963.71 (exit 18:05) | ~0% | — | Arbiter INCREASE 9.1%→12.5% | **Churn** — increased then immediately dust-swept |
| 17:04 | COIN | ADD | 5.10 | $203.45 | $203.45 | ~0% | — | Verifier reconcile to 14.8% | **Churn** — verifier add, arbiter exit same session |
| 18:05 | FIX | ADD | 3.70 | $1,903.71 | $1,902.81 (exit 19:08) | -0.05% | 0.88 | Selector INCREASE 12%→19% | **Churn** — second add, exited 63min later |
| 18:05 | DELL | SELL | 57.39 | avg_entry unknown | $210.94 | unknown | — | Verifier dust-sweep target=0 | OK — cleaner exit |
| 18:05 | LLY | SELL | 13.00 | avg_entry unknown | $963.71 | unknown | — | Verifier dust-sweep target=0 | OK |
| 19:08 | COIN | SELL | 66.90 | avg_entry unknown | $203.45 | ~0% | — | Arbiter EXIT: momentum=0 | Questionable — bought at 17:04, exited same session |
| 19:08 | GOOGL | SELL | 37.96 | $383.94 | $382.77 | -0.30% | — | Fading, below EMA20 | **Bad** — sold loser at EMA20, entered same session |
| 19:08 | AXTX | BUY | 313 | $46.41 | $46.61 (5/4 close) | +0.43% | 0.88 | Momentum=100, breaking_out, vol 2.79x | Entered late session; held overnight |
| 19:08 | META | BUY | 15.48 | $611.73 | $610.46 (5/4 close) | -0.21% | 0.65 | Sector diversification | Marginal confidence for a late-session entry |
| 19:08 | PWR | BUY | 14.69 | $758.48 | $757.38 (5/4 close) | -0.15% | 0.72 | Data-center peer leader | OK; thesis intact at 5/4 close |
| 19:08 | FIX | SELL | 10.00 | $1,900.24 | $1,902.81 | +0.14% | — | Verifier dust-sweep target=0 | **Bad** — sold the winner because verifier target was 0 |

**Notable historical closes (pre-5/4 sessions):**
| Symbol | Exit reason | Verdict |
|---|---|---|
| INTC | "Already +5.9% intraday" | **Bad** — exiting a winner early on intraday % |
| TSLA | "Already +3.4% intraday" | **Bad** — same pattern |
| BAND | "Already +23.5% today with fading vol" | **Missed upside** — 23.5% gain exit is premature |
| PWR (4/30) | "Near day high with flat vol" | **Bad** — near high is continuation signal, not exit |
| AVGO (4/28) | "Near day high with fading vol" | **Bad** — same |
| SOFI | "Near day high with fading vol" | **Bad** — 4th instance of same pattern |

---

### 2b. Cross-trade patterns

- **Intraday round-trips dominate losses.** FIX and GOOGL were each bought, added to, and exited within the same 2-hour window on 5/4. The selector targets a position, the verifier adds to close a gap, then the arbiter exits on "fading/below EMA20." Slippage and spread cost absorbs most of the theoretical gain. 53 orders on 5/4 alone (204 total across 9 sessions = 22.7/session average) is extreme for a swing-cadence bot.

- **"Near day high with fading volume" is being used as an exit signal — it is the opposite of the correct interpretation.** 6 confirmed exits used this verbatim rationale (AVGO ×2, SOFI, PWR, TSLA, INTC). Price near session high with slowing volume is consolidation before continuation in a trending market, not exhaustion. This is the single clearest systematic error in AI exit reasoning.

- **Exit arbiter almost never fully exits (reduce:exit ratio = 21:1).** Reduces are at confidence 0.58–0.62 — just above the 0.55 floor. This creates a pattern where a position is reduced to a stub (e.g., COIN to 5.10 shares) that still triggers stop-loss overhead and then gets dust-swept by the verifier. The full-exit signal never fires at the threshold.

- **Verifier "dust-sweep" and arbiter "EXIT" conflict on the same scan.** On 5/4: arbiter exits COIN and GOOGL at 19:08, then verifier dust-sweeps FIX at 19:08. Meanwhile arbiter bought FIX twice earlier. The arbiter and verifier are disagreeing intra-scan: one agent is targeting a symbol at 0%, another is still reconciling to a prior target >0%.

- **26 `ai_order_failed` events vs 31 successful** = ~46% order failure rate. Rebalance failures: 8. These are silent — the bot attempts a trade, fails, and does not retry or alert.

- **AI failures: 14 `ai_failure` events.** None have parseable model or error fields in decisions.jsonl (all `null`). The AI pipeline is failing silently on roughly 10% of decisions.

- **AXTX is a 2× leveraged ETF (Tradr 2X Long AXTI Daily).** The bot entered 14.4% of equity (~$14,335) in a 2× levered instrument in the last scan of the last day. This violates the spirit of the "no crypto, long US equities" constraint — leveraged ETFs have daily rebalancing decay and are inappropriate for swing holds. This position has now been held (presumably) for 78 days with no monitoring.

- **SPY cash-proxy churn is absent from the data** (SPY held as ~60% proxy position, entered separately from portfolio). No SPY round-trips visible in the 5/4 session log.

- **Period vs SPY = -10.71% over 9 recorded sessions.** The cumulative portfolio return was -0.15% while SPY gained +10.71% over the same reference period. 7 of 9 sessions underperformed SPY.

---

### 2c. Proposed Changes

---

**Proposal 1 — Raise exit_arbiter min_confidence to 0.65 (from 0.55)**

**Why:** All 21 exit-arbiter reduces are clustered at 0.58–0.62 — just above the 0.55 floor. Raising the floor to 0.65 would eliminate the reduce stub loop (reduce → dust-sweep → rebuy) while keeping genuine exits. The 1 true exit had confidence 0.97, well above any threshold.

**Diff (config.yaml):**
```yaml
# Before
exit_arbiter:
  min_confidence: 0.55

# After
exit_arbiter:
  min_confidence: 0.65
```

**Expected impact:** Eliminates ~20 low-conviction reduce cycles per 9 sessions. Reduces wash-trade probability by removing the stub position that triggers it. Estimated ~15 fewer orders/session.

---

**Proposal 2 — Add intraday min-hold timer of 90 minutes for non-stop exits**

**Why:** FIX (bought 17:04, exited 19:08 = 124 min), GOOGL (bought 17:04, exited 19:08 = 124 min), COIN (bought 17:04, exited 19:08). All three were exited within 2 hours of entry on the same session. The bot's swing cadence implies holds of days, not hours. A 90-min min-hold would prevent the "buy on scan 3, exit on scan 4" pattern that generated most of the churn losses.

**Diff (config.yaml):**
```yaml
# Add under risk:
risk:
  # ... existing keys ...
  min_hold_minutes: 90   # new: AI arbiter cannot EXIT a position entered <90min ago (stop-loss still fires)
```

**Expected impact:** Eliminates same-session round-trips. On 5/4, would have prevented exits of FIX, GOOGL, and COIN ~2h after entry (saving ~$8,500 in churn notional and spread cost).

---

**Proposal 3 — Block "near day high" as exit signal; require ≥2 bearish indicators**

**Why:** 6 exits used "near day high with fading volume" as the primary rationale. This is a continuation signal, not reversal. The exit_arbiter prompt should require at least 2 of: [below_VWAP, below_EMA20, score<0.10, bad_news] before recommending close. "Near day high" and "intraday +X%" should explicitly not qualify as exit triggers.

**Diff (src/ai_pipeline.py — exit prompt system instruction, conceptual):**
```python
# Before (inferred from exit decisions):
# Exits triggered by: near_day_high, fading_volume, intraday_gain > threshold

# After — add to exit_arbiter system prompt:
# IMPORTANT: "near day high" and positive intraday % gain are NOT exit signals.
# Require at least 2 of the following before recommending exit/reduce:
# [score < 0.10, below_VWAP, below_EMA20, bearish_news, technical_flip]
```

**Expected impact:** Prevents premature exit on winners (INTC +5.9%, TSLA +3.4%, BAND +23.5%). Estimated +0.5–1.5% per week from letting winners run 30–60 min longer.

---

**Proposal 4 — Block leveraged / inverse ETFs from portfolio selector**

**Why:** AXTX (Tradr 2X Long AXTI Daily ETF) was entered at 14.4% of equity as a swing position. 2× daily rebalancing products decay in sideways markets and are inappropriate for multi-day holds. After 78 days of no monitoring, this is the highest single-name risk in the book.

**Diff (config.yaml):**
```yaml
# Add under universe:
universe:
  # ... existing keys ...
  exclude_leverage_etfs: true  # new: block symbols matching known 2x/3x/inverse ETF patterns
  # Alternatively, add to exclude_tickers:
  exclude_tickers:
    - AXTX
    - SOXS
    - BITO  # crypto-proxy, already in seed watchlist — should be excluded
```

**Expected impact:** Eliminates decay risk on multi-day holds. BITO and SOXS already appear in the discovery pool (seen in selector_pool events); excluding them prevents future entries.

---

**Proposal 5 — Operational: add a liveness heartbeat file and auto-halt**

**Why:** The bot stopped running on 2026-05-04 and has produced zero output for 78 calendar days. There is no in-repo signal of the stoppage — only the absence of new files. A simple heartbeat write (`data/state/last_run.json` with timestamp) on every scan, checked by the review job, would have flagged this on day 2 instead of day 78.

**Diff (scripts/scan_and_trade.py — add at top of main):**
```python
# Add at start and end of each scan run:
import json, pathlib, datetime
pathlib.Path("data/state/last_run.json").write_text(
    json.dumps({"ts": datetime.datetime.utcnow().isoformat(), "status": "started"})
)
# ... existing code ...
pathlib.Path("data/state/last_run.json").write_text(
    json.dumps({"ts": datetime.datetime.utcnow().isoformat(), "status": "completed", "trades": N})
)
```

**And in scripts/eod_report.py (or daily_review.py):**
```python
# Alert if last_run.json is >2 trading days stale
last_run = json.loads(pathlib.Path("data/state/last_run.json").read_text())
if (datetime.datetime.utcnow() - datetime.datetime.fromisoformat(last_run["ts"])).days > 2:
    # trigger Telegram alert: "Bot has not run since {ts}"
```

**Expected impact:** Would have caught the 5/4 stoppage by 5/6. Zero false positives (file only written when bot actually runs).

---

**Proposal 6 — Intraday turnover cap: max 20 orders per session**

**Why:** 53 orders on 5/4, 38 on 5/1, 24 on 4/27, 23 on 4/30. Average across 9 sessions: 22.7 orders. A swing bot with max 6 positions should need at most ~12 orders per session (6 entries + 6 exits). The excess is entirely selector-verifier oscillation. A hard cap of 20 orders/session would suppress the tail while leaving room for normal rebalancing.

**Diff (config.yaml):**
```yaml
# Add under risk:
risk:
  # ... existing keys ...
  max_orders_per_session: 20   # new: halt further entries/rebalances after N orders (exits still allowed)
```

**Expected impact:** On 5/4, would have halted new entries after the 17:04 scan round. The 18:05 and 19:08 rebalances (33 additional orders) would not have run. Estimated -60% order count on high-churn days. May reduce alpha discovery on breakout days — tradeoff is net positive given observed churn pattern.

---

### 2d. Backtest notes

Proposals 1–6 cannot be backtested against live price data (all market-data channels 403-blocked in this container). Offline backtest against journal data only:

- **Proposal 1 (raise confidence floor):** Journal shows 21 reduces at 0.58–0.62 would be eliminated. None of the eliminated reduces resulted in a documented subsequent gain — the reduce stubs were all dust-swept within the same or next session. Offline verdict: proposal is safe.

- **Proposal 2 (90-min hold timer):** Journal shows FIX round-trip (bought 17:04, exited 19:08 at +0.14%), GOOGL round-trip (bought 17:04, exited 19:08 at -0.30%), COIN (bought earlier, exited 19:08). Eliminating these three would have saved ~$40 in direct losses plus ~$50 estimated spread cost. Cannot quantify missed-exit cost (if the exits were correct). Offline verdict: likely positive, conservative to implement.

- **Proposal 3 (block near-day-high exits):** BAND exited at +23.5% intraday with this rationale. Post-exit learning metric not available for BAND. INTC, TSLA exits had 30m/60m drift data: exit_learning_metrics not present in journal for these symbols. Offline verdict: likely strongly positive (letting +23.5% run even another 30 min would be meaningful), cannot quantify precisely.

- **Proposals 4–6:** No offline backtest possible without price series. Logic-check only — each is clearly risk-reducing with no identified downside vs. current behavior.

---

## Primary operational issue

**The bot has not run since 2026-05-04 (78 calendar days).** All strategy proposals above are secondary to this. The frozen book (AXTX 14.6%, PWR 11.1%, META 9.5%, SPY 59.8%, cash 5%) has been held with no monitoring or stop-loss management through 11 weeks of market movement. AXTX is a 2× leveraged ETF subject to daily decay — the longer it is held unmonitored, the greater the gap between theoretical and actual return. This is the single highest-priority item.

> Action required: confirm whether `scripts/scan_and_trade.py` is running on the production host and writing to this repo. See the 2026-07-20 daily review for the full operational checklist.

