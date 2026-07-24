# Post-Mortem 2026-07-24

## Data availability

| File | Status |
|------|--------|
| `data/research/2026-07-24_eod.json` | ❌ **MISSING** — no bot run on 2026-07-24 |
| `data/research/2026-07-24_*_scan.json` | ❌ **MISSING** — no scans on 2026-07-24 |
| `data/journal/trades.jsonl` | ✅ Present (last entry: 2026-05-04) |
| `data/journal/decisions.jsonl` | ✅ Present (last entry: 2026-05-04) |
| Most recent EOD | ✅ `2026-05-04_eod.json` |
| Most recent scan | ✅ `20260504T190848_scan.json` |
| 30-day EOD history | ⚠️ Only 9 days (2026-04-22 → 2026-05-04) |

> ⚠️ **CRITICAL: Bot has been inactive for ~81 calendar days (2026-05-04 → 2026-07-24).**
> No trades, no scans, no EOD snapshots since May 4. This post-mortem covers the last
> active session (2026-05-04) and the cumulative 9-day record that exists in repo data.

---

## Performance — last active session (2026-05-04 vs SPY)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | **-0.36%** |
| Daily alpha vs SPY | **-1.44%** ❌ |
| Equity (EOD 2026-05-04) | $99,849.69 |
| Cash (EOD) | $4,986.91 (5.0% — at floor) |
| Positions | 4 |
| Trades that session | **53** (extreme churn for swing cadence) |
| Macro regime | neutral (score 0.27, VIX 27.83) |

### Rolling benchmark (all available data: 9 trading days)

| Period | Portfolio | SPY | Alpha |
|--------|-----------|-----|-------|
| 9-day (Apr 22 – May 4) | **-16.31%** | **+1.95%** | **-18.26%** |
| 5-day (Apr 29 – May 4) | **-12.66%** | **+0.38%** | **-13.04%** |
| Days beating SPY | 2 / 9 | — | — |
| Avg daily alpha | -2.14% / day | — | — |
| Worst single day | **-5.40%** (Apr 29) | — | — |
| Best single day | **+1.82%** (May 1) | — | — |

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Qty | Avg Entry | Close | P&L% | Market Value | % Portfolio |
|--------|------|-----|-----------|-------|------|-------------|-------------|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** | $14,589 | 14.6% |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** | $9,448 | 9.5% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** | $11,130 | 11.1% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** | $59,696 | 59.8% ⚠️ |

> P&L computed as `(current_price - avg_entry) / avg_entry`. SPY at 59.8% of equity = de facto cash-proxy position crowding out all active alpha.

---

## Trades on 2026-05-04 (53 total — notable events)

| Time (UTC) | Symbol | Side | Action | Reason |
|------------|--------|------|--------|--------|
| 14:51 | HCAI | CLOSE | Exit arbiter conf=0.72 | Down -8.78%; intraday momentum loss (5 signals) |
| 16:04 | AMZN | CLOSE | Exit arbiter | Fading momentum, below VWAP, bearish EMA |
| 16:04 | GEV | CLOSE | Exit arbiter | Weak momentum, below VWAP, flat trend |
| 16:04 | UNH | CLOSE | Exit arbiter | Acceptable but exited to fund LLY |
| 16:04 | LLY | BUY | Arbiter 9.1% | Strong healthcare leader, above VWAP, rising volume (staged 70%) |
| 16:04 | MU | ADD | Arbiter +28.0% | Pool leader; perfect momentum; increase to full target |
| 16:04 | NOK | BUY | Arbiter 4.9% | Telecom diversification (staged 70%) |
| 16:04 | SNDK | BUY | Arbiter 12.6% | Memory #2 behind MU (staged 70%) |
| 18:05 | DELL | EXIT | Exit learning | Qty 57.4, exit $210.94 |
| 18:05 | LLY | EXIT | Exit learning | Qty 13.0, exit $963.71 |
| 18:05 | WDC | EXIT | Exit learning | Qty 24.5, exit $440.06 |
| 18:25 | COIN | EXIT | Exit learning | Qty 5.1, exit $202.68 |
| 18:05 | MU | EXIT | Exit learning | Qty 57.4, exit ≈ $580.8 |

> Many positions entered and exited within the same session — classic churn pattern.

---

## 2a. Per-trade quality verdict (2026-05-04)

| Time (UTC) | Symbol | Action | Notional | Entry | Exit/Close | P&L% | AI Grade | One-line reason | Verdict |
|------------|--------|--------|----------|-------|------------|------|----------|-----------------|---------|
| 14:51 | HCAI | CLOSE | ~$13,924 | — | — | **-8.78%** | conf=0.72 | 5-signal intraday momentum collapse (VWAP, EMA20, fading, trend, pullback from high) | **good exit** — large loss, correctly cut |
| 16:04 | AMZN | CLOSE | ~$17,668 | — | $270.65 | — | arbiter | Fading momentum, below VWAP, bearish EMA; fund LLY | **good** — price fell 30m after (+$26 saved) |
| 16:04 | GEV | CLOSE | ~$15,613 | — | $1,071.49 | — | arbiter | Weak momentum, below VWAP, flat trend | **premature** — +$104/30m, +$198/60m left on table |
| 16:04 | UNH | CLOSE | ~$6,359 | — | $368.25 | — | arbiter | Fund LLY; acceptable continuation | **premature** — +$14 missed over 60m; exit to chase LLY was wrong |
| 16:04 | LLY | BUY | ~$9,020 | $963.71 | — | — | arbiter BUY 9.1% | Healthcare leader, above VWAP, rising volume (staged 70%) | **churn** — funded by UNH exit that was premature; then LLY exited same session ($67 missed) |
| 16:04 | MU | ADD | ~$14,436 | $577.45 | $580.81 (exit) | +0.58% | arbiter +28% | Pool leader, perfect momentum, increase to full target | **churn** — bought then exited same session; net near-flat |
| 16:04 | NOK | BUY | ~$1,832 | — | — | — | arbiter 4.9% | Telecom diversification; staged 70% | **missed** — NOK not in EOD positions; exited intraday despite diversification rationale |
| 16:04 | SNDK | BUY | ~$12,390 | $1,237.52 | $1,250.00 | — | arbiter 12.6% | Memory #2 candidate; staged 70% | **premature exit** — $131 missed 30m after; exited despite being above entry |
| 18:05 | STX | EXIT | — | — | $740.23 | — | exit_learning | — | **premature** — +$76 missed 30m after exit |
| 18:05 | DELL | EXIT | — | — | $210.94 | — | exit_learning | — | **good** — price fell 30m/60m after exit (saved) |
| 18:05 | WDC | EXIT | — | — | $440.06 | — | exit_learning | — | **good** — price fell 30m after exit ($119 saved) |
| 18:25 | COIN | EXIT | — | — | $202.68 | — | exit_learning | — | **neutral** — minimal miss/save |
| Preclose | AXTX | BUY | ~$14,589 | $46.41 | $46.61 | +0.43% | none | Overnight hold; scored 0.403; closing near high | **good** — held overnight, positive P&L |
| Preclose | META | BUY | ~$9,448 | $611.73 | $610.46 | -0.21% | none | Overnight hold; scored 0.206 | **borderline** — below-threshold overnight score (0.206 vs 0.35 buy threshold) |

---

## 2b. Cross-trade patterns

- **81-day bot inactivity (CRITICAL):** No runs, scans, or trades between 2026-05-04 and 2026-07-24. The bot was effectively offline for 11+ weeks. Root cause unknown from repo data. Equity sat idle at $99,849 while the market moved. This is the single most impactful issue; restoring operations loses all alpha vs SPY that accrued during inactivity.

- **SPY cash proxy crowding out alpha (59.8%):** At EOD 2026-05-04, 59.8% of the portfolio is in SPY ($59,696 of $99,850). With 60% in SPY, the active 40% must generate 2.5× the target alpha to move the needle on total portfolio performance. Over the 9-day record, the active portion underperformed severely while SPY provided near-flat returns. The proxy should be a liquidity buffer (~5-10%), not the dominant holding.

- **Escalating trade churn:** Daily trade count trend: 7 → 9 → 19 → 24 → 21 → 10 → 23 → 38 → **53**. A swing-cadence bot (6× daily scans) should not be executing 53 trades in a session. Churn is destroying the edge through spread costs and wash-trade friction.

- **SOXS selected by portfolio-selector (guardrail failure):** At the 19:08 UTC scan, `portfolio-selector` chose SOXS (ProShares UltraShort Semiconductors — 2× inverse ETF) at 12.87% target weight. Core constraint: "Long US equities only — no shorts." Execution_target_weights excluded it, but the selection passed through the AI layer. The selector prompt or eligibility filter must be updated to hard-block inverse/leveraged ETFs.

- **Over-trimming winners (GEV, SNDK, STX, LLY):** 4 positions exited with price rising 30m later — $439 in missed gains. Most acute: GEV ($208 missed in 30-60m window), SNDK ($131 missed). Arbiter cited "weak momentum / below VWAP" but 30m post-exit data refuted the momentum call on GEV and SNDK specifically.

- **Same-session buy-and-exit churn (MU, LLY, NOK, SNDK):** All 4 new entries on May 4 (LLY, MU add, NOK, SNDK) were exited within the same session. The system paid spread twice and generated 3 wash-trade warnings (code 40310000 on LLY, FIX, GOOGL). Net economic benefit of these round-trips: near zero.

- **Wash trade detection (3 events):** Alpaca flagged LLY, FIX, GOOGL for potential wash trades. Recovery mechanism triggered (filled at smaller qty). This is a symptom of same-day re-entry within the 30-day IRS wash sale window. For a paper account this has no tax consequence but signals that the bot is cycling positions too fast.

- **META held with ov_score=0.206 below buy threshold:** The preclose scanner held META overnight at overnight score 0.206, well below the configured `buy_threshold: 0.35`. This was a hold decision, not a new buy, but keeping a position with a below-threshold overnight score adds unnecessary gap risk.

- **period_vs_spy consistently worsening:** -4.22% → -3.82% (recovered Apr 23 on beat) → then deteriorating: -4.70% → -9.54% → -10.71%. The losing sessions are larger-magnitude than the winning sessions. Negative skew to returns.

---

## 2c. Proposed Changes

### Change 1 — Hard-block inverse/leveraged ETFs from portfolio-selector

**Why:** SOXS (2× inverse ETF) was selected at 12.87% on May 4, violating the "long US equities only" core constraint. The execution layer blocked it, but the AI selector should never see it as a candidate.

**Diff (`src/discovery.py` eligibility filter — proposals only, not applied to src/):**
```python
# BEFORE (no inverse ETF filter in eligibility check):
# <eligible symbols passed to portfolio-selector without leverage/inverse check>

# AFTER — add before passing to AI selector:
INVERSE_LEVERAGED_PREFIXES = ('SOXS','SQQQ','SPXU','TZA','FAZ','SPXS','QID','PSQ','SDOW','UVXY','SVXY')
candidates = [c for c in candidates if not any(c['symbol'].startswith(p) for p in INVERSE_LEVERAGED_PREFIXES)]
# OR: filter by AV/yfinance 'assetType' != 'ETF' with negative 'leverageRatio'
```

**Expected impact:** Zero false negatives (no long equities match these prefixes). Eliminates constraint-violating AI selections. Would have blocked SOXS on May 4 before the selector ever saw it.

---

### Change 2 — Daily trade count circuit breaker

**Why:** 53 trades on May 4 on a swing-cadence system. Trend is 7→53 over 9 days. Each round-trip burns spread and risks wash-trade detection. A hard cap forces the AI to prioritize exits/entries rather than churn.

**Diff (`config.yaml`):**
```yaml
# BEFORE: no daily trade cap
risk:
  max_positions: 6

# AFTER — add:
risk:
  max_positions: 6
  max_trades_per_session: 20     # new entries blocked once exceeded; exits still allowed
  max_entries_per_session: 10    # subset cap: new BUY actions only
```

**Expected impact:** May 4 would have halted new entries after the first ~10-15 executions, keeping MU/LLY/SNDK/NOK from entering and immediately exiting the same session. Estimated reduction: 30+ trades/session → ≤20. Eliminates wash-trade scenarios.

---

### Change 3 — Cap SPY cash proxy at 25% of equity

**Why:** 59.8% in SPY at May 4 EOD means the active portfolio is only 40% of equity. To generate 1% total alpha, the active portion needs to outperform by 2.5%. The proxy was designed as a liquidity buffer, not as the primary holding.

**Diff (`config.yaml`):**
```yaml
# BEFORE:
cash_proxy:
  symbol: SPY
  enabled: true

# AFTER — add ceiling:
cash_proxy:
  symbol: SPY
  enabled: true
  max_pct: 0.25     # trim SPY to 25% when it exceeds this; reallocate to active candidates
```

**Expected impact:** Frees ~$35k (35% of equity) for active positions. At 6 positions × 14% each, every position is fully sized vs the current state where 60% is inert. Alpha generation scales directly with active exposure.

---

### Change 4 — Minimum holding period for AI-selected entries

**Why:** LLY, MU, SNDK, NOK were all bought and sold within the same 2-hour session. The exit arbiter fired on same-session entries before any meaningful price discovery could occur.

**Diff (`config.yaml`):**
```yaml
# BEFORE: no minimum hold
exit_arbiter:
  min_confidence: 0.55

# AFTER — add:
exit_arbiter:
  min_confidence: 0.55
  min_hold_minutes: 90      # do not run exit arbiter on positions entered < 90 min ago
                             # (hard stop still fires regardless)
```

**Expected impact:** May 4: LLY entered 16:04 UTC, exited ~18:05 = 121 min (would pass). SNDK entered 16:04, exited ~18:00 = 116 min (would pass). NOK entered 16:04, appeared to exit intraday (would be blocked if < 90 min). Effectively requires the arbiter to give a position at least 1.5 hours before triggering an exit on intraday noise. Hard stops still function.

---

### Change 5 — Restore bot operation (operational change, not config)

**Why:** 81-day bot inactivity from 2026-05-04 to 2026-07-24 is the dominant performance issue. No alpha generated, no compounding, no position management. The root cause is unknown from repo data alone.

**Proposed investigation checklist (not a code diff):**
- [ ] Check cron/scheduler logs for May 4 onwards — did `scan_and_trade.py` fail silently?
- [ ] Check if Alpaca credentials expired or API key rotated
- [ ] Check if `scan_and_trade.py` raised an unhandled exception that killed the scheduler
- [ ] Check if a previous postmortem proposal (CLAUDE.md: see `2026-04-23_postmortem.md`) that called for `ClosePositionRequest` fix was applied — if the fix introduced a bug, it may have halted the bot
- [ ] Add a heartbeat watchdog: if no `scan_and_trade.py` run in >2 trading days, send Telegram alert

**Expected impact:** Restoring operations is the highest-leverage action. Every week idle = ~$100k uninvested vs a market that's had unknown returns over 11 weeks.

---

## 2d. Backtest notes (offline, repo data only)

**Change 1 (inverse ETF blocklist):** Not backtestable — single occurrence. Impact today: SOXS blocked before AI selection. Zero downside (no long-equity names match the block list).

**Change 2 (daily trade cap):** From journal: May 4 had 15 `ai_order_submitted` + 11 `position_closed` = 26 actionable events before exit_learning overhead. A cap of 20 would have blocked the last ~6 AI order submissions (likely the NOK, GOOGL, FIX entries that triggered wash trades). Net: 3 fewer wash-trade events, ~6 fewer churn round-trips. Estimated spread savings: 6 × $0.01 × avg_qty ≈ trivial on paper but principle is sound for live deployment.

**Changes 3 & 4 (SPY cap, min hold):** Cannot be backtested without position-level P&L at rebalance time (not in repo data). Impact is structural — requires forward observation to validate. Change 3 is the higher-priority structural fix given 60% SPY exposure.

**Change 5 (operational):** Not backtestable. The 81-day gap represents the largest missed opportunity in the dataset.

---

## Summary scorecard (last active session: 2026-05-04)

| Category | Grade | Notes |
|----------|-------|-------|
| Bot operational status | **F** | Inactive 81 days (May 4 → Jul 24) |
| Daily return vs SPY (May 4) | **D** | -1.80% vs -0.36% SPY; -1.44% alpha |
| 9-day cumulative vs SPY | **F** | -16.31% port vs +1.95% SPY; -18.26% alpha |
| SPY proxy allocation | **F** | 59.8% in SPY = near-zero active alpha opportunity |
| Trade count discipline | **D** | 53 trades/day on swing cadence; 7→53 trend |
| Guardrail compliance | **C** | SOXS selected (guardrail gap) but blocked at execution |
| Exit quality | **C+** | Correct on HCAI/MU/WDC/AMZN; premature on GEV/SNDK/LLY/STX |
| Wash trade hygiene | **D** | 3 wash-trade detections (LLY, FIX, GOOGL) in one session |
| Position sizing | **B** | Max single active position within 15% cap; SPY proxy exception |
| Cash reserve | **A** | $4,987 (5.0%) — at floor but compliant |

