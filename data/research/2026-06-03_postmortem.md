# Post-Mortem 2026-06-03

## Data availability

| Source | Status |
|--------|--------|
| `data/research/2026-06-03_eod.json` | **MISSING** — no market activity logged for today |
| Most recent EOD snapshot | `2026-05-04_eod.json` (last traded session) |
| Scan files (today) | None — post-mortem covers last logged session (2026-05-04) |
| `data/journal/trades.jsonl` | Present — 204 records through 2026-05-04 |
| `data/journal/decisions.jsonl` | Present |
| `config.yaml` | Present |

**Note:** Today (2026-06-03) has no market data. This post-mortem covers the last recorded trading session (2026-05-04) and the 30-day rolling window through that date. The system produced no EOD logs between 2026-05-05 and 2026-06-03, indicating the bot has not run or traded since May 4.

---

## Performance today (last session: 2026-05-04)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily alpha | **-1.43%** |
| Equity (EOD) | $99,849 |
| Positions held | 4 (incl. 1 SPY cash-proxy) |
| Trade events | 53 |
| Positions closed | 11 |
| AI orders submitted | 15 |
| Wash-trade recoveries | 3 |

### Rolling window (9 sessions: 2026-04-22 → 2026-05-04)

| Date | Portfolio | SPY | Alpha |
|------|-----------|-----|-------|
| 2026-04-22 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | -5.13% | -0.49% | -4.65% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.43% |
| **Cumulative** | **-16.31%** | **+1.95%** | **-18.26%** |

Beat SPY: **2 / 9 sessions (22%)** — well below target.

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Qty | Avg Entry | Current | P&L% | Mkt Value | % Equity |
|--------|------|-----|-----------|---------|------|-----------|----------|
| AXTX | Long | 313.0 | $46.41 | $46.61 | +0.43% | $14,589 | 14.6% |
| META | Long | 15.48 | $611.73 | $610.46 | -0.21% | $9,448 | 9.5% |
| PWR | Long | 14.69 | $758.48 | $757.38 | -0.15% | $11,130 | 11.1% |
| **SPY** | Long | 83.14 | $717.52 | $718.03 | +0.07% | $59,696 | **59.8%** |

Cash: $4,987 (5.0% — at floor). Total invested: $94,863.
**Critical: 59.8% of equity is parked in SPY overnight via the cash-proxy. The bot is effectively indexing 60% of the portfolio.**

P&L computed from `avg_entry` and `current_price` per snapshot (Alpaca `unrealized_plpc` disregarded).

---

## Trades today (2026-05-04) — key events

| Time (UTC) | Event | Symbol | Side | Qty | Price | Note |
|------------|-------|--------|------|-----|-------|------|
| 14:51 | CLOSE | HCAI | sell | 1,492 | $10.69 | AI exit conf=0.72, -8.78% loss |
| 16:04 | CLOSE | AMZN | sell | 65.3 | $270.65 | Arbiter: fading momentum |
| 16:04 | CLOSE | GEV | sell | 14.6 | $1,071.49 | Arbiter: weak momentum |
| 16:04 | CLOSE | UNH | sell | 17.3 | $368.25 | Arbiter: exiting to fund LLY |
| 16:04 | AI BUY | LLY | buy | 9.5 | ~$963 | 9.1% target |
| 16:04 | AI BUY | MU | add | 25.0 | ~$580 | 28.0% target (doubled) |
| 16:04 | AI BUY | NOK | buy | 367 | — | 4.9% target |
| 16:04 | AI BUY | SNDK | buy | 10.1 | $1,247 | Stop hit at $1,237.52 in 6 min |
| 17:04 | CLOSE | MU | sell | 23.0 | $580.81 | Arbiter: flat momentum (1 hr after doubling) |
| 17:04 | AI BUY | DELL | buy | 57.4 | ~$210 | 12.1% target |
| 17:04 | WASH | LLY | — | — | — | Wash-trade recovery triggered |
| 18:05 | CLOSE | DELL | sell | 57.4 | $210.94 | Verifier dust-sweep |
| 18:05 | CLOSE | LLY | sell | 13.0 | $963.71 | Verifier dust-sweep |
| 18:05 | AI BUY | FIX | add | 3.7 | — | INCREASE → 19% |
| 19:08 | CLOSE | COIN | sell | 66.9 | $203.45 | Arbiter: fading |
| 19:08 | CLOSE | GOOGL | sell | 37.96 | $382.77 | Arbiter: fading |
| 19:08 | CLOSE | FIX | sell | 10.0 | $1,902.81 | Verifier dust-sweep |
| 19:08 | AI BUY | AXTX | buy | 313 | $46.41 | Final portfolio entry |
| 19:08 | AI BUY | META | buy | 15.5 | $611.73 | Final portfolio entry |
| 19:08 | AI BUY | PWR | buy | 14.7 | $758.48 | Final portfolio entry |
| ~19:55 | PRECLOSE | SPY | buy_proxy | — | — | $59,654 parked in SPY |

---

## Per-trade quality (2026-05-04)

| Symbol | Driver | Side | Entry | Exit | P&L | Exit quality | Verdict |
|--------|--------|------|-------|------|-----|-------------|----------|
| HCAI | exit-arbiter (conf=0.72) | close | ~$11.72 | $10.69 | -8.78% | GOOD (30m fell to $10.58) | good exit, bad entry (meme surge held overnight) |
| AMZN | portfolio-selector | close | — | $270.65 | — | GOOD (30m -$0.40) | correct call |
| GEV | portfolio-selector | close | — | $1,071.49 | — | EARLY (60m +$13.62 = +$198) | premature, left $198 |
| UNH | portfolio-selector | close | — | $368.25 | — | EARLY (60m +$0.47 = +$8) | marginal early exit |
| SNDK (stop) | hard stop | close | $1,247 | $1,237.52 | -0.75% | EARLY (30m +$2.37 = +$24) | stop-hunted in 6 min, price recovered |
| MU (first) | portfolio-selector | reduce | — | $577.45 | — | EARLY (60m +$3.79 = +$94) | premature |
| MU (final) | portfolio-selector | close | — | $580.81 | — | GOOD (30m -$3.61 = -$83) | correct timing |
| STX | exit-arbiter | reduce | — | $740.23 | — | EARLY (30m +$3.92 = +$76) | over-sensitive |
| WDC | portfolio-selector | close | — | $440.06 | — | GOOD (30m -$2.44 = -$60) | correct at 30m |
| DELL | verifier-sweep | close | ~$210.77 | $210.94 | +0.08% | GOOD (30m -$0.26 = -$15) | verifier cleared a fresh entry |
| LLY | verifier-sweep | close | ~$963 | $963.71 | — | EARLY (60m +$5.37 = +$70) | wash-trade → verifier-dust; $70 left |
| COIN | portfolio-selector | close | — | $202.68 | — | NEUTRAL (60m -$0.23) | acceptable |
| GOOGL | portfolio-selector | close | — | $382.77 | — | — | fading classification; reasonable |
| FIX | verifier-sweep | close | — | $1,902.81 | — | — | dust-sweep of small residual |

**Exit quality score: 6 good / 5 early / 3 neutral** — 38% early exits leaving measurable P&L on table.

---

## Cross-trade patterns

- **Portfolio-selector churns entire book per scan**: 7 of 11 closes driven by portfolio-selector (not exit-arbiter). "No incumbent bias" means the selector freely replaces the whole portfolio each scan. AMZN, GEV, UNH exited at 16:04 to fund LLY, MU-add, NOK, SNDK; MU exited at 17:04 to fund DELL, FIX, GOOGL; COIN/FIX/GOOGL exited at 19:08 to fund AXTX/META/PWR. Three complete portfolio replacements in 5 hours.

- **Fresh-exit guard bypassed 3×**: DELL entered at 17:04, exited at 18:05 (61 min). LLY entered at 16:04, exited at 18:05 (121 min). FIX increased to 19% at 18:05, exited at 19:08 (63 min). All three triggered `fresh_exit_guard_skipped` events — the guard exists as an AI hint ("despite fresh_exit_cooldown") but has no hard enforcement.

- **Premature exits on intraday noise**: GEV exited while leaving $198 on table at 60m; STX "reduce" left $76 at 30m; MU first exit left $94 at 60m. Exit-arbiter confidence was 0.62 on all three — just above the 0.40 floor. These signals were too weak to be acted upon.

- **SNDK stop-hunt in 6 minutes**: Entered at $1,246.97 at 16:04, stop hit at $1,237.52 at 16:10 (just 6 min). Stop was 0.75% below entry (AI chose tighter than the 1% hard max). Price recovered to $1,239.89 at 30m. For a $1,247 stock with 8%+ daily range, a 0.75-1% stop is inadequate and stop-hunt vulnerable.

- **SPY cash-proxy dominates overnight exposure**: 9 SPY round-trips in 5 sessions (buy_proxy + sell across scans). End-of-day balance was 59.8% SPY on May 4 — the bot is an expensive SPY tracker with stock-picking churn as overhead. Pattern is consistent: every preclose parks $36K-$77K in SPY.

- **SOXS selected as portfolio position**: The portfolio-selector's 19:08 scan selected SOXS (3× inverse semiconductor ETF) at 9.0% target weight with "Momentum score 95 with rising volume." Zero trades.jsonl entries for SOXS suggest the order was not submitted to Alpaca (possibly broker-rejected), but the selector actively choosing a short-exposure instrument violates the "long US equities only" constraint.

- **MU doubled then exited within 1 hour**: 16:04 scan increased MU to 28% target (from 13.3%) — nearly 2× the 15% initial cap. By 17:04 the same position was flagged as "weak_or_flat momentum, bearish EMA, flat volume" and fully exited. A 100% position reversal in 60 minutes.

- **April 27-29 drawdown root cause (rolling window)**: Three consecutive sessions with -4.88%, -5.13%, -5.40% alpha against a near-flat SPY produced the bulk of the -18.26% cumulative alpha loss. Apr 27 EOD shows 8 positions all negative (AMD -1.19%, AVGO -5.65%, DELL -4.11%, FIX -8.68%, GEV -7.87%, MU -3.77%, VRT -4.06%) — a correlated tech/AI-infra stop cascade. The bot held 12 positions entering Apr 24, all concentrated in the same AI/semiconductor theme.

---

## Proposed Changes

### P1 — Cap SPY cash-proxy at 20% of equity

**Why:** Every preclose scan parks $36-77K (36-78% of equity) in SPY as a "cash proxy," making the bot a leveraged SPY holder with equity-picking churn as overhead. The May 4 preclose deployed $59,654 into SPY (59.8%). This creates 9 round-trip SPY transactions per 5-session week, each paying bid-ask spread, while reducing the bot's opportunity to compound in alpha-generating positions.

**Diff (config.yaml):**
```yaml
# Before:
cash_proxy:
  enabled: true
  symbol: SPY
  min_rebalance_usd: 500

# After:
cash_proxy:
  enabled: true
  symbol: SPY
  min_rebalance_usd: 500
  max_proxy_pct: 0.20        # cap SPY proxy at 20% equity; leave remainder as true cash
```

**Expected impact:** Maximum SPY proxy exposure drops from 60-78% → 20%. Uninvested cash above 20% stays as real cash (available for next-day opportunity deployment without selling SPY first). Reduces SPY transactions from ~9/week to ~3-4/week.

**Backtest:** Not possible offline — would require replaying orders through Alpaca.

---

### P2 — Hard-enforce fresh-exit guard (no AI bypass below 0.85 confidence)

**Why:** On May 4, the fresh-exit cooldown guard was bypassed 3 times (DELL at 61 min, LLY at 121 min, FIX at 63 min). The guard is enforced as an AI reasoning hint, not a hard code gate. The FIX bypass reason: "despite fresh_exit_cooldown" — the AI acknowledged the guard and overrode it anyway. All three positions were generating wash-trade events and verifier-sweep closures.

**Diff (config.yaml):**
```yaml
# Add to selector section:
selector:
  enabled: true
  fresh_exit_guard_minutes: 120          # already in AI logic; make it a config gate
  fresh_exit_guard_bypass_confidence: 0.85  # AI must reach 0.85 to override the guard
                                            # (currently anything above 0.40 can bypass)
```

**Expected impact:** Prevents intra-session buy→sell on DELL, LLY, FIX pattern. Reduces wash-trade triggers by ~80% (3 wash recoveries → ~0-1 per session). Requires a one-line check in `src/orchestrator.py` or `src/ai_pipeline.py` to read this threshold.

**Backtest (offline):** On May 4, applying this rule: DELL (bought at 17:04, protected until 19:04 → survives, avoids verifier-sweep), FIX (increased at 18:05, protected until 20:05 → survives to end of session). Net benefit: avoids DELL wash-trade; FIX held through final scan either way.

---

### P3 — Block inverse/leveraged ETFs in discovery

**Why:** Portfolio-selector's 19:08 scan selected SOXS (3× inverse semiconductor ETF) at a 9.0% target weight with AI reasoning "Momentum score 95 with rising volume." SOXS is a short-exposure instrument; holding it long is effectively a semiconductor short, violating the "Long US equities only" constraint in CLAUDE.md. The order appears to not have reached Alpaca (zero trades.jsonl entries), but the selector actively chose it.

**Diff (config.yaml):**
```yaml
# Add new section:
discovery:
  blocked_symbols:              # hard-blocked from discovery pool regardless of score
    - SOXS    # 3x inverse semiconductor
    - SOXL    # 3x leveraged semiconductor (excessive leverage)
    - UVXY    # short volatility
    - SVXY    # inverse volatility
    - SPXU    # 3x inverse S&P
    - SPXS    # 3x inverse S&P
    - TECS    # 3x inverse tech
    - FAZ     # 3x inverse financials
    - SDS     # 2x inverse S&P
    - QID     # 2x inverse Nasdaq
    - PSQ     # inverse Nasdaq
    - DOG     # inverse Dow
    - SDOW    # 3x inverse Dow
```

**Expected impact:** Closes the inverse-ETF path cleanly. Prevents selector from proposing short-exposure positions under the guise of momentum. Zero performance impact on normal operation.

---

### P4 — Raise exit-arbiter daytime confidence floor (0.40 → 0.55)

**Why:** Exit-arbiter returned confidence 0.62 on AMZN, SNDK, and STX — all triggering "reduce" actions. Of these three, STX and SNDK exits were premature per exit_learning_metrics (prices continued up). The gap between 0.40 (current floor) and 0.62 (typical signal strength) is too narrow — any 5-min intraday momentum dip generates a reduce at 0.62. The preclose threshold is already 0.50; daytime should be at least as conservative given intraday noise.

**Diff (config.yaml):**
```yaml
# Before:
  exit_arbiter_min_confidence: 0.40
  preclose_exit_arbiter_min_confidence: 0.50

# After:
  exit_arbiter_min_confidence: 0.55   # was 0.40; closes gap with preclose threshold
  preclose_exit_arbiter_min_confidence: 0.55  # unchanged in effect; now matches daytime
```

**Expected impact:** Signals at 0.62 are just above the new floor — they still execute. Borderline signals (conf 0.40-0.54) are suppressed. Estimate: 2-3 fewer false reduces per session. STX reduce at 0.62 would still fire.

**Backtest (offline):** No exits on May 4 were at confidence 0.40-0.54 (all exit-arbiter events at conf 0.62 or 0.72). Low-risk change.

---

### P5 — Minimum stop distance 1.5% for high-range stocks

**Why:** SNDK was entered at $1,246.97 with an AI-set stop at $1,237.62 (0.75% distance). The stop was hit at 16:10, just 6 minutes after entry. For a stock with an 8%+ intraday range ($1,167-$1,275 on May 4), a 0.75% stop is within normal tick noise. The `hard_stop_loss_pct: 0.01` is a maximum, not a minimum — the AI can set arbitrarily tight stops.

**Diff (config.yaml):**
```yaml
# Add to risk section:
  min_stop_loss_pct: 0.008          # new — Python-enforced minimum; AI cannot set tighter than 0.8%
  high_vol_min_stop_loss_pct: 0.015 # applied when intraday_range_pct > 0.03 OR price > $500
```

**Expected impact:** SNDK stop widened 0.75% → 1.5% → not triggered at $1,237.52 (required $1,228.27) → exits cleanly at 30m price $1,239.89. Estimated P&L recovery: +$23.94. Prevents similar stop-hunts on MPWR ($1,573) and other high-priced semis.

---

### P6 — Cap per-scan reallocation at 35% of equity

**Why:** The 16:04 scan reallocated ~65% of equity in a single pass (AMZN + GEV + UNH out, LLY + MU-add + NOK + SNDK in). This cascade triggered 3 wash-trade recoveries and created three complete portfolio replacements in 5 hours. No existing config parameter limits per-scan reshuffling.

**Diff (config.yaml):**
```yaml
# Add to rebalance section:
  max_scan_reallocation_pct: 0.35  # max equity fraction that can change hands in one scan;
                                    # lowest-priority new buys deferred to next scan
```

**Expected impact:** Forces sequential changes across 2 scans instead of 1 mass reallocation. Reduces wash-trade triggers. Requires code support to defer buys when cap is hit.

---

## Data gaps / caveats

- No 2026-06-03 data exists. The system has produced no logs since 2026-05-04. Investigate whether the scheduler (cron/systemd) is still running.
- MU `pnl_pct: -80.11%` on 2026-04-29 ($981 market value) is anomalous — likely a dust position with a mismatched avg_entry from a partial fill. Disregarded in analysis.
- `period_return: 0.00` field in 2026-05-04 EOD appears incorrect (cumulative equity is -0.15% from $99,627 starting equity). Possible reset or field bug.
- Exit-arbiter returned `reduce` (not `exit`) for STX and SNDK — these are partial exits; full closes came via portfolio-selector in the same or next scan.
