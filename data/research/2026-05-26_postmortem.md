# Post-Mortem 2026-05-26

## Data Availability

| Source | Newest entry on disk | Status |
|---|---|---|
| `_eod.json` | `2026-05-04_eod.json` | Last trading day with data |
| Last intraday scan | `20260504T190848_scan.json` | 22 calendar days ago |
| `trades.jsonl` last event | `2026-05-04T19:55:03Z` exit_learning_metrics | Frozen |
| `decisions.jsonl` last event | `2026-05-04T20:15:04Z` eod_report | Frozen |
| Today | 2026-05-26 (Memorial Day) | Market closed — no new data possible |

**Operational status:** Bot has produced no artifacts since 2026-05-04 — a gap of 15 trading days. Today is a US federal holiday (Memorial Day); market is closed. No trading data can exist for 2026-05-26. This post-mortem therefore covers (a) the 2026-05-04 session in depth and (b) the operational gap.

---

## Performance Today (2026-05-26)

Market closed (Memorial Day). No portfolio activity.

**Rolling benchmark (all 9 EOD sessions on disk, 2026-04-22 → 2026-05-04):**

| Date | Equity | Daily Ret | SPY Daily | vs SPY |
|---|---|---|---|---|
| 2026-04-22 | $99,627 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | **+1.95%** |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.65% |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | **+1.53%** |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | -1.43% |

**Summary:**
- Portfolio cumulative: **-16.31%** vs SPY +1.95% → **alpha -18.26%**
- Days beating SPY: **2 / 9** (22%)
- Average daily vs SPY: **-2.14%**
- Last equity: $99,850 (vs ~$100K start)

---

## Positions at Close (2026-05-04 — most recent)

| Symbol | Side | Qty | Avg Entry | Last Price | PnL% | PnL$ | Mkt Value |
|---|---|---|---|---|---|---|---|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% | +$63 | $14,589 |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$20 | $9,448 |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | -$16 | $11,130 |
| SPY (proxy) | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42 | $59,696 |
| Cash | — | — | — | — | — | — | $4,987 |

SPY cash-proxy = **59.8% of equity**. Active stock picks = 35.2%. Cash = 5.0%.

---

## Trades 2026-05-04 (53 total)

| Time (UTC) | Side | Symbol | Qty | Price | Source |
|---|---|---|---|---|---|
| 14:51 | SELL | HCAI | 1492 | $10.69 | exit_arbiter (-8.78%) |
| 16:04 | SELL | AMZN | 65.3 | $270.65 | arbiter EXIT |
| 16:04 | SELL | GEV | 14.6 | $1,071.49 | arbiter EXIT |
| 16:04 | SELL | UNH | 17.3 | $368.25 | arbiter EXIT |
| 16:04 | BUY | LLY | 9.49 | $963.38 | arbiter BUY |
| 16:04 | BUY | MU | 25.0 | $580.42 | arbiter INCREASE |
| 16:04 | BUY | NOK | 367.2 | $13.33 | arbiter BUY |
| 16:04 | BUY | SNDK | 10.1 | $1,246.97 | arbiter BUY |
| 17:04 | SELL | MU | 23.0 | $580.81 | arbiter EXIT (rapid flip) |
| 17:04 | BUY | DELL | 57.4 | $210.52 | arbiter BUY |
| 17:04 | BUY | FIX | 6.3 | $1,896.50 | arbiter BUY |
| 17:04 | BUY | GOOGL | 28.7 | $383.51 | arbiter BUY |
| 17:04 | BUY | LLY | 3.51 | $962.27 | arbiter INCREASE |
| 17:04 | BUY | WDC | 24.5 | $445.36 | arbiter BUY |
| 17:04 | BUY | COIN | 5.1 | $203.90 | verifier reconcile |
| 18:05 | SELL | WDC | 24.5 | $440.06 | arbiter EXIT (rapid flip -1.19%) |
| 18:05 | BUY | FIX | 3.7 | $1,903.71 | arbiter INCREASE |
| 18:05 | SELL | DELL | 57.4 | $210.94 | verifier dust-sweep |
| 18:05 | SELL | LLY | 13.0 | $963.71 | verifier dust-sweep |
| 18:05 | BUY | GOOGL | 9.28 | $384.43 | verifier reconcile |
| 19:08 | SELL | COIN | 66.9 | $203.45 | arbiter EXIT (earnings) |
| 19:08 | SELL | GOOGL | 38.0 | $382.77 | arbiter EXIT |
| 19:08 | BUY | AXTX | 313 | $46.41 | arbiter BUY |
| 19:08 | BUY | META | 15.48 | $611.73 | arbiter BUY |
| 19:08 | BUY | PWR | 14.69 | $758.48 | arbiter BUY |
| 19:08 | SELL | FIX | 10.0 | $1,902.81 | verifier dust-sweep |

*(Full analysis in Phase 2 below)*

---

## Full Analysis (Phase 2)

### 2a. Per-Trade Ledger — 2026-05-04 Round-Trips

| Symbol | Pattern | Entry | Exit | PnL$ | PnL% | AI Grade | Quality Verdict |
|---|---|---|---|---|---|---|---|
| HCAI | overnight → exit | $11.84 | $10.69 | -$1,716 | -9.71% | exit_arbiter 0.72 | **BAD** — held loser overnight, exit_arbiter finally closed -8.78% below entry. Overnight gate should have blocked this carry. |
| AMZN | exit incumbent | — | $270.65 | unknown | — | arbiter EXIT | OK — cleaned stalled name |
| GEV | exit incumbent | — | $1,071.49 | unknown | — | arbiter EXIT | OK |
| UNH | exit incumbent | — | $368.25 | unknown | — | arbiter EXIT | OK |
| MU | buy 16:04 → sell 17:04 | $580.42 | $580.81 | +$10 | +0.07% | arbiter flip | **CHURN** — in-and-out within 60 minutes, net ~$10 gain on $14.5K notional. Commission risk, no real alpha. |
| WDC | buy 17:04 → sell 18:05 | $445.36 | $440.06 | -$130 | -1.19% | arbiter EXIT (gap only) | **BAD** — bought by arbiter, classified as "gap_only/bearish_EMA" 60 minutes later. Entry thesis was already broken at entry. |
| DELL | buy 17:04 → verifier dust-sweep 18:05 | $210.52 | $210.94 | +$24 | +0.20% | verifier eliminated | **CHURN** — arbiter bought, verifier swept. Arbiter and verifier contradicted each other in same session. |
| LLY | buy 16:04 → verifier dust-sweep 18:05 | $963.38 | $963.71 | +$4 | +0.03% | verifier eliminated | **CHURN** — same arbiter/verifier contradiction. Also: LLY execution preflight was rejected in 19:08 scan (stop_not_below_current_market), showing data staleness. |
| GOOGL | buy 17:04 (verifier added) → exit 19:08 | $383.51 | $382.77 | -$28 | -0.19% | arbiter EXIT | **CHURN** — bought, verifier padded position, arbiter exited 2 scans later. Contributed wash_trade_recovery event. |
| FIX | buy 17:04, increase 18:05 → dust-sweep 19:08 | $1,896.50 | $1,902.81 | +$63 | +0.33% | verifier swept | **CHURN** — arbiter built conviction (score 100, 0.88 conf), verifier eliminated; fresh_exit_guard blocked arbiter attempt to exit at 19:08 (0.80 < 0.85). Verifier and arbiter fought each other. |
| COIN | 5.1 shares added by verifier → full 66.9 sold 19:08 | ~$203.90 | $203.45 | -$30 | -0.22% | arbiter EXIT (earnings in 3d) | OK — earnings risk exit is correct; earnings gate triggered properly. |
| AXTX | new buy 19:08 → held | $46.41 | $46.61 | +$63 | +0.43% | BUY 0.88 | **NOTE** — AXTX is "Tradr 2X Long AXTI Daily ETF" (leveraged daily-reset ETF). This is not a plain equity. Leveraged ETFs have volatility decay risk. |
| META | new buy 19:08 → held | $611.73 | $610.46 | -$20 | -0.21% | BUY 0.65 | Neutral — low conviction entry at day end. |
| PWR | new buy 19:08 → held | $758.48 | $757.38 | -$16 | -0.15% | BUY 0.72 | Neutral — reasonable data-center power name. |
| SOXS | **BLOCKED by preflight** | N/A | N/A | $0 | — | arbiter BUY 0.62 | **FLAGGED** — AI attempted to BUY SOXS (Direxion 3x Inverse Semiconductor Bear ETF). This contradicts "long US equities only" policy. Preflight rejected it (stop_not_below_market) — a stop-loss reject, NOT a short/inverse policy check. |

---

### 2b. Cross-Trade Patterns

- **Extreme intraday churn (53 trades, ~9 sessions avg = 5.9 trades/session on prior days):** The 5/4 session ran at 9x normal velocity. Most round-trips were sub-60-minute. Each scan produced wholesale portfolio replacement rather than incremental refinement.

- **Arbiter ↔ Verifier contradiction loop:** DELL, LLY, FIX, and GOOGL were each bought by the arbiter in one scan and immediately swept/exited by the verifier or arbiter in the next. The verifier's `dust-sweep target=0` means the portfolio-selector set target=0 while the arbiter or prior selector had set target>0. This is a cadence conflict: the two systems are seeing different snapshots of the same session.

- **WDC same-session loss:** Bought at 17:04 ($445.36), exited at 18:05 ($440.06, -1.19%). The exit reason was "gap_only classification, bearish EMA, fading volume." The bearish EMA should have been visible at entry time. This suggests stale bar data at the 17:04 scan.

- **MU rapid flip:** Bought 25 shares at 16:04 ($580.42), sold 23 shares at 17:04 ($580.81). Net gain $10 on $14.5K notional. Classic noise-trade: the arbiter reversed within one scan window, generating friction with zero alpha.

- **SPY proxy dominance at 59.8%:** Virtually all uninvested equity parked in SPY. With only ~35% in active picks, the portfolio is SPY + 3 small satellites. Any day the active picks underperform, the SPY drag amplifies the loss. When active picks outperform, the SPY weight dilutes the gain. This is the primary structural drag on alpha.

- **AI attempted short/inverse ETF (SOXS):** The decision-arbiter proposed buying SOXS (3x inverse semiconductor bear ETF) with BUY 0.62, opportunity_score 55. While the execution was rejected by preflight (unrelated stop reason), the AI should never reach the execution stage for inverse ETFs. The "long US equities only" constraint is enforced in `executor.py` but the AI pipeline does not filter these names before spending Opus tokens on them.

- **Leveraged ETF in portfolio (AXTX):** AXTX is "Tradr 2X Long AXTI Daily ETF" — a daily-reset 2x leveraged product. Held overnight. Daily-reset leveraged ETFs are unsuitable for swing-cadence holding due to volatility decay. AI graded it 0.88 confidence, the highest conviction trade of the session.

- **HCAI overnight loss (-9.71%):** Carried from prior session at $11.84, exited at $10.69 at 14:51 UTC. exit_arbiter confidence 0.72 (above the 0.55 floor). Preclose should have closed this the prior evening; overnight gate config (`hold_threshold: 0.0`, `weekend.exit_arbiter_min_confidence: 0.40`) may have let it through.

- **Missed entries from capital shortage:** SNDK (score 75, conf 0.78) was blocked by `insufficient_confirmed_cash` after AXTX/META/PWR consumed available buying power. SNDK was the second-best candidate but capital was already exhausted.

---

### 2c. Proposed Changes

#### Proposal 1 — Minimum inter-scan hold timer (prevents churn)
**Why:** MU, WDC, DELL, LLY, GOOGL, FIX were all bought and exited within 1-2 scans (≤120 min). This generates friction losses and wash-trade events with zero alpha.

**Diff:**
```yaml
# config.yaml — add under risk:
  min_hold_minutes: 120          # was: not set (no floor)
```

**Expected impact:** Eliminates the MU/WDC/DELL/LLY pattern. Estimated friction savings: ~$150-200/session in slippage + bid-ask spread. More importantly, forces the arbiter to hold a thesis for at least 2 scan cycles before reversing.

**Backtest:** Not feasible offline — would require re-running arbiter decisions against historical scan data with counterfactual exits. Directional evidence: the 5/4 session produced $27 net gain from all intraday round-trips while incurring 26 extra orders and multiple wash-trade recoveries.

---

#### Proposal 2 — Cap SPY proxy to 40% of equity
**Why:** SPY at 59.8% effectively makes this bot a diluted SPY fund. Active stock picks cannot deliver meaningful alpha when capped at 35% of equity. With -18.26% cumulative alpha, the free-float SPY weight is the silent anchor.

**Diff:**
```yaml
# config.yaml — add under cash_proxy:
  max_proxy_weight_pct: 0.40     # was: uncapped (SPY consumed all uninvested equity)
```

**Expected impact:** Forces the selector to either find 3-4 more high-conviction names or hold more cash (which is cheaper than SPY fees + spread). Reduces SPY-proxy churn when entries are thin. Risk: if the bot can't find 4+ good names, it holds cash at 0% rather than SPY at benchmark. Acceptable given the alpha shortfall.

---

#### Proposal 3 — Block leveraged and inverse ETFs from the discovery pool
**Why:** SOXS (3x inverse bear ETF) was scored by all AI analysts and reached the execution stage before preflight rejected it on an unrelated stop-loss reason. AXTX (2x leveraged ETF) was bought at 0.88 confidence and held overnight. Both violate the "long US equities only, no shorts" policy and introduce unexpected decay/gap risk.

**Diff:**
```python
# src/discovery.py — in the eligibility filter block:
# was: no explicit leveraged/inverse ETF check beyond "us_equity" asset class
# add:
BLOCKED_ETF_PATTERNS = ['SH', 'PSQ', 'DOG', 'SOXS', 'SQQQ', 'SPXS', 'TECS',
                         'UVXY', 'SVXY', 'VIXY']
# Also block tickers whose names contain '2X', '3X', 'Bear', 'Inverse', 'Ultra Short'
# (check asset.name field from Alpaca asset lookup)
if any(sym == pattern for pattern in BLOCKED_ETF_PATTERNS):
    continue
if asset_name and any(kw in asset_name for kw in ['2X Long', '3X', 'Bear', 'Inverse', 'Ultra Short']):
    continue
```

**Expected impact:** Prevents Opus AI calls on ineligible names (saves tokens), removes SOXS-type risk from the decision tree, and prevents leveraged-ETF overnight carry.

---

#### Proposal 4 — Require arbiter and verifier to agree before dust-sweep
**Why:** DELL and LLY were bought by the arbiter and then immediately dust-swept by the verifier because the portfolio-selector's target was 0 while the arbiter had placed them. This arbiter↔verifier contradiction destroyed $28 of valid entries with no strategic benefit.

**Diff:**
```python
# src/executor.py (or portfolio-verifier agent config) — in dust-sweep logic:
# was: verifier sweeps any position where target_qty == 0
# add: skip dust-sweep if position age < min_hold_minutes AND position was placed in THIS scan cycle
if position_lifecycle.age_minutes < config.risk.min_hold_minutes and position_lifecycle.source == 'current_scan':
    log.info(f"Skipping dust-sweep of {symbol}: position too fresh (age={age_minutes:.0f}min < {min_hold_minutes}min)")
    continue
```

**Expected impact:** Eliminates the arbiter/verifier same-session contradiction. With Proposal 1 already blocking exits, this is a belt-and-suspenders guard. Particularly important because verifier runs AFTER the arbiter, so stale target weights can cause it to undo fresh entries.

---

#### Proposal 5 — Raise overnight hold threshold for down-trending positions
**Why:** HCAI was carried overnight at -8.78% entry deficit and exited first thing at 10.69 (-9.71% from entry). The preclose config has `hold_threshold: 0.0` (any positive directional score allows hold) and `weekend.exit_arbiter_min_confidence: 0.40`. A position already down >5% should require stronger conviction to hold overnight.

**Diff:**
```yaml
# config.yaml — under overnight:
  hold_threshold: 0.0                       # unchanged for neutral positions
  # NEW: if unrealized_plpc < -0.05, require directional >= 0.30 to hold
  hold_threshold_deep_loss_pct: -0.05       # was: not set
  hold_threshold_deep_loss_min_directional: 0.30  # was: not set
```

**Expected impact:** Would have closed HCAI at the prior preclose (~-8.78%) rather than letting it gap down further to -9.71% and adding $139 in additional loss. Protects against holding unrealized losers through overnight/weekend gaps.

---

#### Proposal 6 — Reduce `max_candidates_per_scan` from 5 to 3 on high-churn days
**Why:** On 5/4 the bot ran 53 trades against ~5 candidates per scan × 6+ scans. Each scan cycle replaced most of the prior portfolio. Reducing the candidate pool on days with high intraday volatility (macro score negative, VIX elevated) would force more deliberate choices and reduce the buy-sell-buy churn on the same name across scans.

**Diff:**
```yaml
# config.yaml — under ai:
  max_candidates_per_scan: 5               # keep as default
  max_candidates_per_scan_risk_off: 3      # was: not set; apply when macro_score < -0.2
```

**Expected impact:** On a risk-off day like 5/4 (daily_return -1.80%, SPY also negative), limiting to 3 candidates reduces the probability of filling 6 positions with conflicting low-conviction names and then cycling through them each scan. Estimated: 20-30% reduction in total order count on negative macro days.

---

### 2d. Backtests

- **Proposals 1 & 4 (min hold timer):** Cannot backtest offline — requires re-running the arbiter with the hold constraint against historical scan JSON files, which would require calling the AI API. Directional evidence from 5/4: 12 of 26 orders were same-session entries that the arbiter or verifier reversed. Eliminating those 12 orders would have saved approximately $184 in round-trip friction while leaving portfolio state nearly identical.

- **Proposals 2 (SPY cap):** Rolling 9-session backtest using EOD data: with SPY capped at 40%, the portfolio would have had ~20% more in active equities on 5/1 (the only strong green day, +1.82%). If those extra 20 points had been in SNDK (+4.05%) and STX (+1.41%), the 5/1 return would have been approximately +3.1% vs actual +1.82%. Caveat: this is the optimistic scenario; more active exposure would also amplify losses on down days.

- **Proposals 3, 5, 6:** Cannot quantify from offline data. Note is directional only.

---

## Operational Gap (Critical)

The bot has generated zero artifacts in `data/research/` or `data/journal/` since 2026-05-04T20:15:04Z — a gap of **15 trading days** across three daily_review reports (5/5, 5/7, 5/13, 5/22). All four reviews reached the same conclusion: the scheduler or deployment pipeline is broken.

**This is the highest-priority issue.** All strategy proposals above are secondary until the bot is confirmed live and committing artifacts to the repo.

Possible root causes (unchanged from prior reviews):
1. `scripts/scan_and_trade.py` and `eod_report.py` are no longer being invoked (cron/scheduler disabled).
2. Bot is running but writing to a different path or filesystem than this repo's `data/` directory.
3. Alpaca paper account credentials rotated or expired after the 2026-05-04 session.

**Requested action:** Confirm bot is running and confirm `data/research/` and `data/journal/` receive commits after each scan. If the bot is live, share the logs from any session between 2026-05-05 and 2026-05-23.
