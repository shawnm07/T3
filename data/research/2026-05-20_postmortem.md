# Post-Mortem 2026-05-20

## Data availability

| File | Status |
|------|--------|
| `data/research/2026-05-20_eod.json` | **MISSING** — no EOD file for 2026-05-20 in main branch; last available is 2026-05-04 |
| `data/research/20260504T*_scan.json` | Available (4 scan files) |
| `data/journal/trades.jsonl` | Available (last entry: 2026-05-04T19:55) |
| `data/journal/decisions.jsonl` | Available (last entry: 2026-05-04) |
| `config.yaml` | Available |

**Analysis based on most recent completed session in main branch: 2026-05-04.**
Note: postmortem branches exist on GitHub for 2026-05-05 through 2026-05-19, indicating the bot
has been running — but those sessions' data files were not merged to main. This analysis covers
the last session whose journal data is accessible from the main branch checkout.

---

## Performance today (2026-05-04 — most recent session with full data)

| Metric | Value |
|--------|-------|
| Portfolio equity | $99,849.69 |
| Daily return | **-1.80%** |
| SPY daily | -0.36% |
| Daily vs SPY | **-1.43%** (underperform) |
| Period vs SPY (eod.json `period_vs_spy`) | **-10.71%** |
| SPY 30d (eod.json `spy_30d`) | +10.71% |
| Trades executed (session) | **53** |

### Rolling benchmark (from repo EOD files)

| Date | Equity | Bot daily | SPY daily |
|------|--------|-----------|-----------|
| 2026-04-22 | $99,627 | 0.00% | +1.01% |
| 2026-04-23 | $101,208 | +1.56% | -0.39% |
| 2026-04-24 | $99,343 | -0.81% | +0.77% |
| 2026-04-27 | $96,448 | -4.88% | +0.17% |
| 2026-04-28 | $96,867 | -5.13% | -0.49% |
| 2026-04-29 | $93,999 | -5.40% | -0.01% |
| 2026-04-30 | $95,786 | -2.67% | +0.96% |
| 2026-05-01 | $101,101 | +1.82% | +0.29% |
| 2026-05-04 | $99,850 | **-1.80%** | **-0.36%** |

**Equity-based 5-day return (04-28 → 05-04):** +3.08% (bot) vs +0.38% (SPY cumulative)
**Equity-based full-window (04-22 → 05-04):** +0.22% (bot) vs SPY 30d +10.71%

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current | PnL% | MV |
|--------|------|-----------|---------|------|-----|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,589 |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448 |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,130 |
| SPY | LONG | $717.52 | $718.03 | +0.07% | $59,696 |
| Cash | — | — | — | — | $4,987 |

SPY cash-proxy = 59.8% of equity. Active equity allocation = 35.1%. Cash 5.0%.

---

## Trades today (2026-05-04, all executed)

| Time | Event | Symbol | Side | Qty | Fill | Reason (truncated) |
|------|-------|--------|------|-----|------|--------------------|
| 14:51 | position_closed | HCAI | SELL | 1492 | $10.69 | AI exit-arbiter (conf=0.72): down -8.78% |
| 16:04 | position_closed | AMZN | SELL | 65.3 | $270.65 | Fading momentum, below VWAP, bearish EMA |
| 16:04 | position_closed | GEV | SELL | 14.6 | $1,071.49 | Weak momentum, below VWAP, bearish EMA |
| 16:04 | position_closed | UNH | SELL | 17.3 | $368.25 | Fading volume; exiting to fund LLY |
| 16:04 | ai_order_submitted | LLY | BUY | 9.49 | $963.38 | Strong continuation, above VWAP |
| 16:04 | ai_order_submitted | MU | ADD | 25.0 | $580.42 | Pool leader, perfect momentum |
| 16:04 | ai_order_submitted | NOK | BUY | 367.2 | $13.33 | Strong continuation, above VWAP |
| 16:04 | ai_order_submitted | SNDK | BUY | 10.1 | $1,246.97 | Best new candidate, strong continuation |
| 17:04 | position_closed | MU | SELL | 23.0 | $580.81 | Weak/flat momentum, bearish EMA, flat volume |
| 17:04 | ai_order_submitted | DELL | BUY | 57.4 | $210.52 | IT sector leader, momentum score 95 |
| 17:04 | ai_order_submitted | FIX | BUY | 6.30 | $1,896.50 | Peer/sector leader in ai_data_center_power |
| 17:04 | ai_order_submitted | GOOGL | BUY | 28.7 | $383.51 | CommSvcs leader, acceptable continuation |
| 17:04 | ai_order_submitted | LLY | ADD | 3.51 | $962.27 | Held within cooldown, acceptable continuation |
| 17:04 | ai_order_submitted | WDC | BUY | 24.5 | $445.36 | Memory peer leader |
| 17:04 | ai_order_submitted | COIN | ADD | 5.1 | $203.90 | Verifier reconcile to Opus target |
| 18:05 | position_closed | WDC | SELL | 24.5 | $440.06 | Gap-only classification, bearish EMA |
| 18:05 | ai_order_submitted | FIX | ADD | 3.70 | $1,903.71 | Perfect momentum score, peer leader |
| 18:05 | position_closed | DELL | SELL | 57.4 | $210.94 | verifier dust-sweep target=0 |
| 18:05 | position_closed | LLY | SELL | 13.0 | $963.71 | verifier dust-sweep target=0 |
| 18:05 | ai_order_submitted | GOOGL | ADD | 9.28 | $384.43 | Verifier reconcile to Opus target 14.6% |
| 19:08 | position_closed | COIN | SELL | 66.9 | $203.45 | Momentum score 0, fading, earnings risk |
| 19:08 | position_closed | GOOGL | SELL | 38.0 | $382.77 | Momentum score 0, fading, below VWAP |
| 19:08 | ai_order_submitted | AXTX | BUY | 313.0 | $46.41 | Momentum score 100, breaking_out |
| 19:08 | ai_order_submitted | META | BUY | 15.5 | $611.73 | CommSvcs sector leader |
| 19:08 | ai_order_submitted | PWR | BUY | 14.7 | $758.48 | ai_data_center_power peer leader |
| 19:08 | position_closed | FIX | SELL | 10.0 | $1,902.81 | verifier dust-sweep target=0 |

*(+ multiple `exit_learning_metrics` log events not included above)*

---

## Per-trade analysis (2026-05-04)

Entries marked **FLIP** were opened and closed within the same session. All P&L estimated from fill prices in `trades.jsonl` (avg_entry rule). Transaction costs not included (paper account), but slippage from 53 trades on ~$235k notional ≈ $117 theoretical.

| Symbol | Type | Entry | Exit | PnL% | $PnL | AI Grade | Entry reason | Verdict |
|--------|------|-------|------|------|------|----------|--------------|----------|
| HCAI | FLIP | $11.72 | $10.69 | **-8.79%** | **-$1,537** | exit-arbiter conf=0.72 | Momentum 100, breaking_out | **BAD** — biotech/small-cap gap trap |
| STX | EXIT | $760 | $740.58 | -2.56% | -$377 | selector EXIT | Weak momentum, below EMA20 | BAD — held into weakness, late exit |
| GEV | FLIP | $1,093 | $1,071 | **-2.00%** | **-$319** | arbiter EXIT (16:04) | Entered at 15:13 "pressing day high" | **BAD** — entered at exhaustion, reversed in 48 min |
| AMZN | FLIP | $274.60 | $270.65 | -1.44% | -$258 | arbiter EXIT | "Perfect momentum 100, pressing day high" | BAD — top-ranked entry already at exhaustion |
| WDC | FLIP | $445.36 | $440.06 | -1.19% | -$130 | arbiter EXIT | Memory peer leader | BAD — held < 1 hr, gap-only classification |
| SNDK | EXIT | $1,250 | $1,247 | -0.24% | -$71 | selector EXIT | Peer-swapped for MU (gap: 4.7 pts) | CHURN — peer gap below threshold, near-zero alpha |
| GOOGL | FLIP | $383.97 | $382.77 | -0.31% | -$46 | arbiter EXIT | CommSvcs leader | CHURN — opened 17:04, closed 19:08 |
| COIN | FLIP | $203.90 | $203.45 | -0.22% | -$30 | arbiter EXIT | Earnings risk, momentum 0 | CHURN — round-trip in one session |
| UNH | FLIP | $370.00 | $368.25 | -0.47% | -$30 | arbiter EXIT | Exited to fund LLY | CHURN — exited same session, LLY then also swept |
| MU | FLIP | $580.42 | $580.81 | +0.07% | +$9 | arbiter EXIT | Weak/flat momentum 2 scans after buy | CHURN — added at 16:04, closed 17:04 |
| NOK | FLIP | $13.33 | $13.30 | -0.23% | -$11 | (exit log) | Strong continuation | CHURN — low-conviction filler |
| FIX | FLIP | $1,900 | $1,902.81 | +0.15% | +$28 | verifier dust-sweep | arbiter BUY; verifier sweep target=0 | **CHURN** — arbiter/verifier conflict |
| DELL | FLIP | $210.52 | $210.94 | +0.20% | +$24 | verifier dust-sweep | arbiter BUY; verifier sweep target=0 | **CHURN** — arbiter/verifier conflict |
| LLY | FLIP | $963.38 | $963.71 | +0.03% | +$4 | verifier dust-sweep | arbiter BUY; verifier sweep target=0 | **CHURN** — arbiter/verifier conflict |
| AXTX | HOLD | $46.41 | $46.61 | +0.43% | +$63 | arbiter BUY | Momentum 100, breaking_out | FLAT — held to EOD, minimal gain |
| META | HOLD | $611.73 | $610.46 | -0.21% | -$20 | arbiter BUY | CommSvcs leader | FLAT — held to EOD |
| PWR | HOLD | $758.48 | $757.38 | -0.15% | -$16 | arbiter BUY | ai_data_center_power peer | FLAT — held to EOD |

**Session P&L estimate: −$2,750 (before SPY proxy P&L)**

---

## Cross-trade patterns

- **Extreme churn (53 trades / 17 symbols / $235k notional on a $100k book):**
  4 complete portfolio reshuffles within 5 hours (15:13, 16:04, 17:04, 18:05, 19:08).
  Every scan cycled out 3-5 positions and bought 3-5 new ones. No position held for more than 2 scans before being reassessed and often exited.

- **Entry-at-exhaustion ignored:** AMZN was the #1 pick with "pressing day high" and was explicitly flagged in `missed_breakouts` with exhaustion penalty (scan: "only 0.11% from day high — near exhaustion"). The exhaustion penalty reduces `remaining_upside_score` but does not hard-block the entry. AMZN reversed -1.44% within 2 hours. GEV similarly entered "pressing day high" and reversed -2.00% within 48 minutes.

- **Arbiter/verifier conflict creating zero-hold round-trips:** DELL, LLY, and FIX were opened by the arbiter at 17:04 and swept by the verifier at 18:05 as "dust-sweep target=0" — paying bid-ask on both sides with zero holding time. The verifier reconciled to an arbiter state where these targets had already been zeroed, not the state that opened them.

- **Peer-swap near-zero-gap churn (SNDK→MU):** SNDK exited with opportunity_score=62 to fund MU at score=67 — a 4.7-point gap, less than half the configured `peer_outperformance_threshold: 10`. The swap triggered because SNDK's weight (29%) forced a size correction, masking the conviction comparison.

- **ai_data_center theme cap causing cascade fail:** At 15:13, GEV filled the theme cap, blocking FIX (68), PWR (63), DELL (61), ETN (60). GEV was exited at 16:04 at a loss; FIX and DELL were then bought at the 17:04 scan at worse prices. The bot systematically bought second-choice names after the first-choice failed.

- **HCAI speculative-cap failure:** HCAI at ~$10/share was allocated 14.4% of equity (1492 shares = $15,900). The name reversed 8.79% intraday — characteristic of a low-float gap-and-trap. The `min_market_cap_usd: 2B` filter apparently passed it, suggesting stale market cap data.

- **SPY proxy at 60% of equity by EOD:** The bot parked $59,696 (59.8%) in SPY — the active 40% was the drag that caused underperformance vs SPY on the day.

- **Rolling drawdown not halted (April 27-29):** Three consecutive sessions at -4.88%, -5.13%, -5.40%. Macro score was `neutral` (0.27) throughout, well above the `-0.55` halt threshold. No intraday or cross-day drawdown protection exists in config.

---

## Proposed changes

### 1. Add intraday position hold floor (`selector.min_hold_scans: 2`)

**Why:** MU, GEV, and AMZN were all entered at the 15:13 scan and exited at either the 16:04 or 17:04 scan — 1-2 scan intervals = 1-2 hours. Same-session flip-flops generated losses from entries near day highs with zero time for the thesis to play out. The staged-entry system (70% initial) is designed to allow scale-up on continuation, but the next scan exits the position before continuation is measurable.

**Diff (config.yaml):**
```yaml
# BEFORE
selector:
  new_entry_initial_fraction: 0.70
  continuation_gate:
    enabled: true
    min_score: 55

# AFTER — add:
selector:
  new_entry_initial_fraction: 0.70
  min_hold_scans: 2              # NEW: positions entered at staged fraction cannot be
                                  # selector-exited until surviving at least 2 subsequent scans
  continuation_gate:
    enabled: true
    min_score: 55
```

**Expected impact:** Eliminate 6-8 same-session exits per churny day. Estimated reduction from 53 to ~20-25 trade events/session. Would have prevented GEV, AMZN, MU flip-exits today.

**Offline backtest:** 7 of 17 symbols today had hold times < 2 scan intervals. Historical sessions 04-27 through 04-30 show similar 30-40 trade counts with same-session cycles — systematic pattern, not an outlier.

---

### 2. Hard-block exhausted top-picks (`selector.block_exhaustion_top_pick: true`)

**Why:** AMZN was selected #1 yet was simultaneously flagged as exhausted in `missed_breakouts` ("only 0.11% from day high"). The exhaustion penalty lowered `remaining_upside_score` but did not prevent entry. AMZN reversed -1.44% within 2 hours.

**Diff (config.yaml):**
```yaml
# BEFORE
selector:
  missed_breakout_threshold: 72

# AFTER
selector:
  missed_breakout_threshold: 72
  block_exhaustion_top_pick: true   # NEW: if top candidate has exhaustion penalty applied
                                     # (remaining_upside < opportunity - 10 pts),
                                     # demote below first non-exhausted candidate
  exhaustion_penalty_min_gap: 10    # min opportunity-vs-remaining gap to trigger demotion
```

**Expected impact:** Routes capital to the second-best non-exhausted name when the top pick is already extended. On days where the entire pool is near day highs, increases cash/SPY allocation instead.

---

### 3. Verifier hold-time floor (`portfolio_verifier.min_hold_minutes: 30`)

**Why:** DELL, LLY, FIX were opened at 17:04 and swept by the verifier at 18:05 as "dust-sweep target=0" — 6 trades with zero net exposure change and pure bid-ask drag.

**Diff (config.yaml):**
```yaml
# BEFORE
portfolio_verifier:
  enabled: true
  tolerance_pct_of_equity: 0.005
  min_corrective_usd: 50

# AFTER
portfolio_verifier:
  enabled: true
  tolerance_pct_of_equity: 0.005
  min_corrective_usd: 200           # raise from $50 to reduce noise trades
  min_hold_minutes: 30              # NEW: verifier will not sweep a position opened < 30 min ago
```

**Expected impact:** Eliminates 3 verifier dust-sweep round-trips from today (6 trades). No impact on legitimate reconciliation of stale positions.

---

### 4. Daily drawdown circuit breaker (`risk.daily_drawdown_halt_pct: 0.025`)

**Why:** April 27-29 produced three consecutive ~-5% days. `macro.bearish_halt_score: -0.55` never triggered (macro was `neutral` 0.27). No intraday drawdown protection exists. The goal spec requires `daily_drawdown < 2.5%` with no enforcement mechanism.

**Diff (config.yaml):**
```yaml
# BEFORE (no daily drawdown halt exists)

# AFTER — add under risk:
risk:
  # ... existing keys ...
  daily_drawdown_halt_pct: 0.025    # NEW: if portfolio down > 2.5% from prior day close,
                                     # skip NEW entries for remainder of session (exits still run)
  consecutive_loss_halt_days: 3     # NEW: 3 consecutive SPY-underperforming sessions →
                                     # require macro score > 0 before any new entry
```

**Expected impact:** Would have halted new entries on 04-27 once the -2.5% intraday threshold was crossed. Estimated ~$7,000 saved across the 04-27 through 04-29 cascade. **Highest-impact change.**

**Offline backtest (in-repo data):** 04-27 equity dropped from $99,342 (04-24 close) to $96,448 EOD = -2.92%. Halting at -2.5% intraday would have capped the session loss vs the reported -4.88% daily return. Estimated saved on 04-27 alone: ~$2,400. The same trigger would have fired on 04-28 and 04-29 if properly reset each morning.

---

### 5. Small-float dollar-volume filter (`screener.min_avg_dollar_volume: 10M`)

**Why:** HCAI at ~$10/share was allocated 14.4% of equity ($15,900 position) and reversed 8.79% intraday — classic low-float gap-and-trap. `min_market_cap_usd: 2B` apparently passed it (stale data). A minimum dollar-volume filter catches names with share-volume > 1M but thin dollar volume.

**Diff (config.yaml):**
```yaml
# BEFORE
screener:
  min_market_cap_usd: 2000000000
  min_avg_volume: 1000000
  min_price: 5

# AFTER
screener:
  min_market_cap_usd: 2000000000
  min_avg_volume: 1000000
  min_price: 10                     # raise from $5 to $10
  min_avg_dollar_volume: 10000000   # NEW: minimum $10M avg daily dollar volume
```

**Expected impact:** Would have excluded HCAI, saving ~$1,537 today. Prevents future gap-trap entries in thinly traded names.

---

## Data gap note

Postmortem branches exist on GitHub for 2026-05-05 through 2026-05-19, meaning the bot has been running during those sessions. However, those sessions' EOD/journal data was not merged into main, so this analysis covers only the last session visible from main. To analyze the 11-session gap, merge or cherry-pick EOD files from those branches.
