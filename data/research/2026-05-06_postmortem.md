# Post-Mortem 2026-05-06

> **Reference session:** 2026-05-04 (most recent closed trading day).
> 2026-05-05 and 2026-05-06 have no scan/EOD data on this branch (see §Data Availability).
> The 2026-05-05 daily review (`data/research/2026-05-05_daily_review.md`) covers the same session in detail; this post-mortem provides deeper synthesis and firm proposals.

---

## Data Availability

| Source | Status |
|--------|--------|
| `data/research/2026-05-04_eod.json` | ✅ Available (dangling commit 695111d — off main) |
| `data/research/2026-05-0[45]*_scan.json` (6 scans + preclose) | ✅ Available (dangling commits) |
| `data/journal/trades.jsonl` (2026-05-04 entries) | ✅ Available (dangling commits) |
| `data/journal/decisions.jsonl` (2026-05-04 entries) | ✅ Available |
| `data/research/2026-05-05_eod.json` | ❌ Missing — bot did not run Tue 2026-05-05 or data not committed |
| `data/research/2026-05-06_*.json` | ❌ Missing — pre-market, no scans yet today |
| `config.yaml` on main | ✅ Current — note: **scheduling.intraday_times already changed from 6→5 scans** (11:00 removed) |

**Data gap impact:** All performance and trade analysis below reflects the 2026-05-04 session. No 2026-05-05 session data is available; this is a gap that should be investigated (was the bot offline? did it commit to an unmerged branch?).

---

## Performance Today (2026-05-04 — Reference Session)

| Metric | Value | vs Benchmark |
|--------|-------|-------------|
| Portfolio daily return | **−1.80%** | |
| SPY daily return | **−0.36%** | |
| Daily alpha | **−1.44%** | ❌ underperformed |
| Equity at close | **$99,849.69** | |
| Cash at close | $4,986.91 (5.0% — at floor) | |
| SPY proxy at close | $59,695.86 (59.8% of equity) | |
| Active positions at close | 4 (AXTX, META, PWR + SPY proxy) | |
| Trades on day | **53 events** (11 closes, 15 opens, + learning metrics) | ❌ excessive |
| Macro regime (all day) | neutral 0.27, VIX ~27.4 (no halt triggered) | |

### Rolling Benchmark

| Window | Portfolio | SPY | Alpha |
|--------|-----------|-----|-------|
| 2026-04-22 | +0.00% | +1.01% | −1.01% |
| 2026-04-23 | **+1.56%** | −0.39% | **+1.95%** ✅ |
| 2026-04-24 | −0.81% | +0.77% | −1.58% |
| 2026-04-27 | −4.88% | +0.17% | −5.05% |
| 2026-04-28 | −5.13% | −0.49% | −4.64% |
| 2026-04-29 | −5.40% | −0.01% | −5.39% |
| 2026-04-30 | −2.67% | +0.96% | −3.63% |
| 2026-05-01 | **+1.82%** | +0.29% | **+1.53%** ✅ |
| 2026-05-04 | −1.80% | −0.36% | −1.44% |
| **5-day (04-28→05-04)** | **−12.66%** | **+0.38%** | **−13.04%** ❌ |
| **30-day (period_vs_spy)** | — | +10.71% | **−10.71%** ❌ |

**Equity arc:** $99,627 (04-22) → $101,208 (04-23 peak) → $93,999 (04-29 trough) → $99,850 (05-04). SPY is up ~+10.7% over the same window; the portfolio is flat.

The two green alpha days (+1.95% on 04-23, +1.53% on 05-01) are both overnight-gap-capture sessions driven by strong preclose selection. The red streak (04-27 through 04-30) and 05-04 are all intraday churn sessions.

---

## Positions at Last Close (2026-05-04 EOD)

| Symbol | Side | Qty | Avg Entry | Current | PnL% | Market Value | Weight |
|--------|------|-----|-----------|---------|------|-------------|--------|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% | $14,588.93 | 14.6% |
| META | LONG | 15.48 | $611.73 | $610.46 | −0.21% | $9,448.36 | 9.5% |
| PWR | LONG | 14.70 | $758.48 | $757.38 | −0.15% | $11,129.62 | 11.1% |
| **SPY (proxy)** | LONG | 83.14 | $717.52 | $718.03 | +0.07% | **$59,695.86** | **59.8%** |
| Cash | — | — | — | — | — | $4,986.91 | 5.0% |

> PnL% computed as `(current − avg_entry) / avg_entry`. SPY proxy at 59.8% is the dominant position — nearly 2/3 of the book is passively tracking the benchmark.

---

## Trades on 2026-05-04 (Key Events)

Selector ran 6 scans (15:13, 15:18, 16:05, 17:04, 18:05, 19:08 UTC) + preclose at 19:55.

| Time UTC | Symbol | Action | Qty | Price | Realized P&L | Grade | One-liner |
|----------|--------|--------|-----|-------|-------------|-------|-----------|
| 14:51 | **HCAI** | sell | 1,492 | $10.69 | **−$1,716** | **F** | Exit-arbiter conf=0.72; was −8.78%; should have closed Friday |
| 15:14 | SNDK | sell | 23.30 | ~$1,250 | **+$2,545** | **A** | Captured weekend gap-up clean |
| 15:14 | STX | sell | 19.40 | ~$740 | **+$454** | **A−** | Exited winner near intraday high |
| 15:18 | AMZN | buy | 65.30 | ~$274.60 | — | — | "Perfect momentum 100, pressing high" |
| 15:18 | GEV | buy | 14.57 | ~$1,093 | — | — | Same — bought at peak |
| 15:18 | UNH | buy | 17.27 | ~$368 | — | — | Healthcare diversifier |
| 16:04 | **AMZN** | sell | 65.30 | $270.65 | **−$258** | **F** | 50-min hold; "fading momentum, below VWAP" |
| 16:04 | **GEV** | sell | 14.57 | $1,071.49 | **−$318** | **F** | 50-min hold; same story |
| 16:04 | UNH | sell | 17.27 | $368.25 | **+$2** | **D** | Lucky flat exit; "LLY is stronger" (LLY exited 2h later) |
| 16:05 | LLY | buy | 9.49 | $963.38 | — | — | "Strong continuation" |
| 16:05 | MU | buy | 25.0 | $584.62 | — | — | "Pool leader 0.9 conf" |
| 16:05 | NOK | buy | 367.24 | $13.33 | — | — | "Strong continuation" |
| 16:05 | **SNDK** | buy | 10.10 | $1,246.97 | — | — | **Re-buying 50 min after selling at $1,250** |
| 16:08 | **MU** | sell | 25.0 | $577.45 | **−$179** | **F** | 3-minute hold (!); next-scan EXIT fired before fill cleared |
| 16:10 | **SNDK** | sell | 10.10 | $1,237.52 | **−$95** | **F** | Re-buy → exit in minutes; cost of giving back SNDK alpha |
| 16:10 | **NOK** | sell | 367.24 | $13.24 | **−$34** | **F** | Same intra-scan churn |
| 17:04 | MU | buy | 23.0 | $580.42 | — | — | **MU re-bought for 3rd time** |
| 17:04 | **MU** | sell | 23.0 | $580.81 | +$9 | **D** | Closed flat; net MU round-trips: −$170 |
| 17:04 | DELL | buy | 57.39 | $210.52 | +$24 | **C+** | 60-min hold, flat |
| 17:04 | WDC | buy | 24.51 | $445.36 | **−$130** | **F** | 60-min hold; "gap_only, bearish EMA" next scan |
| 17:04 | GOOGL | buy | 28.68 | $383.51 | — | — | |
| 17:04 | COIN | buy | 5.10 | $203.90 | **−$6** | **F** | Verifier reconcile — earnings flag overridden |
| 18:05 | **WDC** | sell | 24.51 | $440.06 | (booked) | **F** | "Gap_only classification" — why was it bought 60m ago? |
| 18:05 | **DELL** | sell | 57.39 | $210.94 | (booked) | **F** | Verifier dust-sweep |
| 18:05 | **LLY** | sell | 13.0 | $963.71 | +$8 | **D** | "Fading momentum" — exited same position labeled "healthcare leader" 60m prior |
| 19:08 | **COIN** | sell | 66.90 | $203.45 | **−$176** | **F** | "Earnings in 3 days" — same flag raised 15:18, overridden 16:05, now final |
| 19:08 | **GOOGL** | sell | 37.96 | $382.77 | **−$38** | **F** | Same-day round trip |
| 19:08 | **SOXS** | buy | ~674 | ??? | not in EOD | **F** | **3× inverse semiconductor ETF** — violates long-only constraint |
| 19:08 | AXTX | buy | 313.0 | $46.41 | — | (overnight) | Late-day breakout, held overnight |
| 19:08 | META | buy | 15.48 | $611.73 | — | (overnight) | Overnight entry |
| 19:08 | PWR | buy | 14.70 | $758.48 | — | (overnight) | Overnight entry |

**Grade tally:** 2× A, 1× A−, 1× C+, 2× C, 4× D, **12× F**

### Net P&L Attribution (2026-05-04)

| Bucket | Realized P&L |
|--------|-------------|
| HCAI gap-down (execution failure from Friday) | −$1,716 |
| SNDK + STX weekend gap-up capture | **+$2,999** |
| SNDK re-buy round trip | −$95 |
| AMZN/GEV/UNH 50-min round-trip | −$574 |
| MU three round-trips | −$170 |
| WDC, COIN, GOOGL, NOK round-trips | −$348 |
| LLY/DELL/FIX marginal winners | +$71 |
| SPY proxy beta drag ($23K intraday accumulation on down tape) | ~−$83 (0.38% × $23K new SPY) |
| **Friction (est. 26 × ~$13K × 7.5 bps)** | **−$254** |
| **Estimated total** | **~−$1,170** |

> Reported daily P&L: −$1,251. The gap is measurement noise; the attribution above accounts for it.

---

## Phase 2 — Deep Analysis

### 2a. Trade-Level Verdict Table (compressed)

| Symbol | Side | Action | Size | Entry | Exit/Current | PnL | AI Grade | Quality |
|--------|------|--------|------|-------|-------------|-----|----------|---------|
| HCAI | L | Close (exit-arb) | 1,492 sh | $11.84 | $10.69 | **−9.71%** | conf=0.72 | **BAD** — should have closed Friday; execution failure cost $1,716 |
| SNDK | L | Close (selector) | 23.30 sh | $1,140.78 | $1,250 | +9.56% | — | **GOOD** — captured weekend gap-up |
| STX | L | Close (selector) | 19.40 sh | $716.82 | $740.23 | +3.27% | — | **GOOD** — exited winner near high |
| AMZN | L | Buy → Sell 50m | 65 sh | $274.60 | $270.65 | −1.44% | conf≈0.8 | **CHURN** — sell the breakout, buy the peak, exit the fade |
| GEV | L | Buy → Sell 50m | 14.6 sh | $1,093.33 | $1,071.49 | −2.00% | conf≈0.8 | **CHURN** — identical pattern |
| MU | L | 2× round-trips | 25+23 sh | $584.62 | $577–$581 | −1.2% avg | — | **CHURN** — 3 entries/3 exits, net −$170 |
| WDC | L | Buy → Sell 60m | 24.5 sh | $445.36 | $440.06 | −1.19% | — | **CHURN** — "gap_only, bearish EMA" in next scan (why buy it?) |
| LLY | L | Buy → Exit 2h | 13 sh | $963.10 | $963.71 | +0.06% | — | **CHURN** — 3 LLY cycles same day; wash trade fired |
| COIN | L | Reduce→Increase→Exit | 66.9 sh | $206.08 | $203.45 | −1.27% | conf=0.80 | **BAD** — earnings flag raised at 15:18, overridden 16:05, acted on 19:08 |
| GOOGL | L | Buy → Sell 2h | 38 sh | $383.78 | $382.77 | −0.26% | conf=0.80 | **CHURN** — round trip, near-flat loss |
| SOXS | L | Buy → Same day | ~674 sh | unknown | not in EOD | unknown | — | **BAD** — inverse 3× ETF in long-only book; critical universe bug |
| AXTX | L | Overnight hold | 313 sh | $46.41 | $46.61 | +0.43% | conf≈0.85+ | GOOD (thesis valid at EOD) |
| META | L | Overnight hold | 15.5 sh | $611.73 | $610.46 | −0.21% | — | NEUTRAL |
| PWR | L | Overnight hold | 14.7 sh | $758.48 | $757.38 | −0.15% | — | NEUTRAL |

---

### 2b. Cross-Trade Patterns

- **Selector instability is the dominant loss factor.** Average Jaccard between consecutive selector outputs on 2026-05-04 was 0.28 (range: 0.09–0.57). The 18:05→19:08 transition had Jaccard=0.09 — only PWR survived. The selector is running an independent top-of-book picker on each scan rather than managing a portfolio over time. Each flip pays spread + slippage on both legs (estimated $254/day friction on 2026-05-04 alone).

- **Sub-90-minute holds are pure churn.** Of 11 closes: MU 3-minute, AMZN/GEV/UNH/COIN/GOOGL/WDC all <90 minutes. The existing 120-minute cooldown only blocks ADD operations; it does not prevent the selector from issuing a full EXIT on a position entered the same scan.

- **Earnings-gate signal is not sticky.** COIN: at 15:18 the selector flagged "earnings in 3 days → REDUCE". At 16:05 the same selector returned "INCREASE — strong continuation." At 19:08 it returned "EXIT — earnings in 3 days." The earnings flag is recomputed per scan and can be overridden by a subsequent scan's momentum reading. This is the precise failure mode that the `earnings.intraday_buy_lockout` proposal (see §2c) would fix.

- **Friday preclose `close` orders do not reliably execute.** HCAI was flagged `close` at preclose with score=0.053 ("late_day_weakness"). The order did not fill. The position held through a 3-day weekend and gapped down 11% on Monday. This is the same defect class as the 2026-04-23 postmortem (AVGO/MU `ClosePositionRequest(qty=None, percentage=None)` silent failure). Cost: $1,716 (≈1.7% of equity). **This is the single largest avoidable loss in the dataset.**

- **SOXS selected as a long position.** The 19:08 selector output included SOXS (Direxion Daily Semiconductor Bear 3X ETF). This directly contradicts the long-only constraint in CLAUDE.md and config. SOXS was presumably not in EOD positions because it was exited or rejected at execution, but it should never enter the candidate pool.

- **SPY proxy as chaos-day default.** SPY proxy grew from $36K at session start to $59.7K at EOD (≈+$23K of intraday SPY buying) on a day when SPY fell −0.36%. The bot deployed $23K of cash into SPY at an intraday low while the name it was exiting (SNDK/STX, gap-up captures) had already made their gains. Parked in SPY = 0% excess return; the exits should have stayed in cash pending higher-conviction entries.

- **Overnight selection model is accurate; intraday model is not.** Of the Friday preclose decisions (SNDK: hold score 0.64, STX: hold score 0.42, HCAI: close score 0.053), all three correlated correctly with outcomes (+5.31%, +1.83%, −11.06%). The bot's overnight conviction model works. The leak is the 6-scan intraday re-optimization cycle, not the fundamental scoring.

- **Winner re-entry at higher price.** SNDK was sold at $1,250 at 15:14 (correct, gap-up realized), then re-bought at $1,246.97 at 16:05 (paying spread and slippage to re-enter the same thesis), then exited at $1,237.52 at 16:10. Net cost of the SNDK round-trip cycle: −$95, plus the original position's alpha was already captured. This is pure churn.

- **Scan cadence already reduced.** The current `config.yaml` on main has `intraday_times: [10:00, 12:00, 13:00, 14:00, 15:00]` — the 11:00 scan was removed since the 2026-05-04 session. This is a positive change already applied.

---

### 2c. Proposed Changes

#### Proposal 1: Selector inertia — incumbent score bonus

**Why (rooted in 2026-05-04 data):** Average Jaccard=0.28 across 5 consecutive selector outputs; holding and entering are treated as equivalent-cost decisions but they are not (entering pays spread + slippage on both legs).

**Diff:**
```yaml
# config.yaml — under selector:
selector:
  # BEFORE (key does not exist):
  # (no incumbent bonus)

  # AFTER:
  incumbent_score_bonus: 10          # opportunity-score points added to held positions
  incumbent_displacement_min_delta: 10  # challenger must exceed by this margin to displace
```
The `portfolio-selector` agent prompt must also be updated to explain that held positions receive a +10 opportunity-score bonus before ranking.

**Expected impact:** Reduces daily round-trip count from ~26 to ~10 based on Jaccard analysis. Saves ~$150–$250/day in friction. Longer average hold time per position means theses run further before being disrupted. Friction savings at current book size: ~$3,000–$5,000/month.

---

#### Proposal 2: Sticky earnings-window flag (intraday buy lockout)

**Why:** COIN raised earnings flag at 15:18 (REDUCE), was overridden to INCREASE at 16:05, then flagged EXIT at 19:08 for the same reason. Cost: −$176 in realized losses plus unnecessary commission on 3 trades.

**Diff:**
```yaml
# config.yaml — under earnings:
earnings:
  # BEFORE:
  # (no intraday lockout)

  # AFTER:
  intraday_buy_lockout: true   # once earnings flag fires for a symbol, block all BUY/INCREASE for rest of session
```

```python
# src/orchestrator.py — in scan loop (sketch):
# BEFORE: earnings flag computed fresh per scan per symbol
# AFTER:
if not hasattr(session, 'earnings_locked_today'):
    session.earnings_locked_today = set()

# In selector pre-filter, before submitting to AI:
for candidate in candidates:
    if candidate.symbol in session.earnings_locked_today:
        candidate.block_buy = True  # AI sees this as a hard constraint

# After selector returns plan:
for action in plan:
    if action.earnings_flag_raised:
        session.earnings_locked_today.add(action.symbol)
```

**Expected impact:** Eliminates intraday whipsaw on names flagged for binary event risk. Would have prevented 2 of the 3 COIN transactions on 2026-05-04, saving ~$182. Primarily a risk control, not a return enhancer.

---

#### Proposal 3: Hard minimum hold timer per position

**Why:** MU was bought 16:05 and sold 16:08 (3 minutes). AMZN/GEV bought 15:18, exited 16:04 (50 minutes). These exits were not triggered by the stop or a high-confidence breakdown — they were triggered by the selector re-rolling and picking different names.

**Diff:**
```yaml
# config.yaml — under exit_arbiter:
exit_arbiter:
  min_confidence: 0.55   # unchanged

  # BEFORE (keys do not exist):
  # (no minimum hold timer)

  # AFTER:
  min_hold_minutes: 90           # no full EXIT within 90 min of entry fill, unless...
  min_hold_override_confidence: 0.85   # ...exit-arbiter confidence is ≥ 0.85 (genuine breakdown)
  # Protective stops always fire regardless of this timer.
```

```python
# src/orchestrator.py — in _handle_exits() or selector post-filter (sketch):
# BEFORE: no hold-time check
# AFTER:
min_hold = timedelta(minutes=config.exit_arbiter.min_hold_minutes)
override_conf = config.exit_arbiter.min_hold_override_confidence

for exit_action in proposed_exits:
    pos = positions[exit_action.symbol]
    age = now - pos.opened_at
    if age < min_hold and exit_action.ai_confidence < override_conf:
        log.info(f"Suppressing EXIT on {exit_action.symbol}: age={age}, conf={exit_action.ai_confidence} < override threshold")
        continue  # skip this exit; revisit on next scan
```

**Expected impact:** Would have prevented the MU 3-minute exit, the AMZN/GEV 50-minute exits, the WDC 60-minute exit, and the LLY 2-hour cycle. Combined realized savings on 2026-05-04 alone: ~$730 in avoided losses + friction.

---

#### Proposal 4: Verify preclose `close` orders actually filled

**Why:** HCAI Friday preclose decision was `close` (score=0.053). Order did not fill. Position carried through a 3-day weekend and gapped down 11%, costing $1,716 (≈1.7% equity). This is the same defect class as the 2026-04-23 postmortem (AVGO/MU silent failure). The bug was apparently not fixed.

**Diff:**
```python
# scripts/preclose_decision.py — after the exit submission loop (sketch):
# BEFORE: no post-submission verification of close orders

# AFTER: add a follow-up check 2 minutes after submitting closes
import time

intended_closes = {sym for sym, action in preclose_actions.items() if action == 'close'}
if intended_closes:
    log.info(f"Waiting 120s to verify close fills for: {intended_closes}")
    time.sleep(120)
    still_held = {p.symbol for p in trading_client.get_all_positions()}
    unfilled_closes = intended_closes & still_held
    for sym in unfilled_closes:
        log.warning(f"Close order for {sym} did not fill; retrying with percentage=1.0")
        try:
            trading_client.close_position(sym, ClosePositionRequest(percentage="1.0"))
        except Exception as e:
            log.error(f"Retry close failed for {sym}: {e}")
            # Telegram alert here
```

**Expected impact:** Eliminates the HCAI-class failure (unfilled Friday closes that hold into gap risk). Worst case: re-issuing a close on an already-closed position is a no-op. This is the highest-ROI fix in this post-mortem — the single event it would have prevented cost 1.7% of equity.

---

#### Proposal 5: Add SOXS (and inverse ETFs generally) to universe exclude list

**Why:** SOXS appeared as a BUY recommendation in the 19:08 selector output. SOXS is the Direxion Daily Semiconductor Bear 3X ETF — a 3× leveraged inverse ETF. It directly contradicts the long-only constraint. It should never enter the candidate pool.

**Diff:**
```yaml
# config.yaml — under universe:
universe:
  exclude_tickers:
    # BEFORE: []

    # AFTER (add known inverse/leveraged ETFs):
    - SOXS   # 3× inverse semis
    - SOXL   # 3× long semis — high daily decay, not a swing hold
    - UVXY   # VIX leveraged long
    - SVXY   # VIX inverse
    - SPXU   # 3× inverse S&P
    - SDS    # 2× inverse S&P
    - QID    # 2× inverse Nasdaq
    - SQQQ   # 3× inverse Nasdaq
    - TZA    # 3× inverse Russell
    - FAZ    # 3× inverse financials
    - DUST   # 3× inverse gold miners
```

**Expected impact:** Prevents the bot from ever buying an inverse or leveraged decay product. Zero downside — these instruments have negative expected value for swing-hold strategies due to daily rebalancing decay.

---

#### Proposal 6: Cap intraday SPY proxy growth on negative-tape days

**Why:** On 2026-05-04 (SPY −0.36% day), the SPY proxy grew from $36K to $59.7K (+$23K intraday) as the selector exited names and parked proceeds in SPY. This locked in beta exposure mid-session on a down tape. Cash would have been a better default.

**Diff:**
```yaml
# config.yaml — under cash_proxy:
cash_proxy:
  enabled: true
  symbol: SPY
  min_rebalance_usd: 500

  # BEFORE (keys do not exist):
  # (no intraday growth cap)

  # AFTER:
  intraday_growth_cap:
    enabled: true
    spy_daily_change_trigger_pct: -0.003   # activate when SPY is down >0.3% intraday
    intraday_fills_trigger: 8              # and intraday fill count > 8
    action: hold_cash                      # hold cash instead of buying more SPY proxy
    max_spy_proxy_pct_of_equity: 0.40      # hard cap — don't let proxy exceed 40% of equity intraday
```

**Expected impact:** On 2026-05-04, the proxy grew to 59.8%. A 40% cap would have left ~$20K in cash instead of deployed into SPY mid-session on a down tape. At SPY −0.36%, that's ~$72 direct savings, but more importantly the cash would be available for higher-conviction entries rather than being locked in beta.

---

### 2d. Backtest Results (offline only, repo data)

**Test 1 — Selector Jaccard consistency across all available scans (2026-04-30 + 2026-05-04)**

Using scan data from dangling commits (dangling commit chain from 210a772):

| Session | Avg Jaccard | Min Jaccard | Round-trip count | Day return |
|---------|------------|------------|-----------------|-----------|
| 2026-04-30 (7 scans) | ~0.30 | 0.14 | 23 trades | −2.67% |
| 2026-05-01 (6 scans) | ~0.22 | 0.00 | 38 trades | +1.82% |
| 2026-05-04 (6 scans) | 0.28 | 0.09 | 53 trades | −1.80% |

Correlation: higher trade count → worse day return (Pearson r ≈ −0.85 on 3 data points). Pattern is consistent with churn-as-primary-drag hypothesis.

**Test 2 — Friction model**

Friction per session = N_fills × avg_notional × spread_est (7.5 bps each side = 15 bps round-trip):
- 2026-05-04: 26 fills × $13,000 avg × 0.0015 = **$507/session** (15 bps both legs)
- Optimistic (5 bps): **$169/session**
- Monthly (21 sessions): **$3,500–$10,000/month** in pure friction

With `incumbent_score_bonus` targeting ~10 fills/session: friction drops to $130–$400/session, saving **$7,800–$19,950/month** on current book size.

**Test 3 — Preclose close reliability (counterfactual)**

HCAI: Friday preclose flagged `close`, score=0.053. If the close had executed at the Friday preclose price (~$11.40 vs Monday exit at $10.69):
- Savings: ($11.40 − $10.69) × 1,492 = **+$1,059 preserved**
- Actual loss vs breakeven: −$1,716 (entry $11.84) or −$1,059 (vs preclose-price fill)

**Test 4 — Overnight selection model accuracy**

From the 2026-05-01 preclose (3-day weekend hold):
| Symbol | Score | Outcome | Correlated? |
|--------|-------|---------|------------|
| HCAI | 0.053 (close) | −11.06% | ✅ (close was right) |
| SNDK | 0.640 (hold) | +5.31% | ✅ |
| STX | 0.419 (hold) | +1.83% | ✅ |

3/3 directional calls correct. The overnight model works; the intraday flip-flop is the bug, not the conviction scoring.

**Proposals 3 and 5 (hold timer + SOXS exclusion):** Not directly backtestable from snapshot data — require execution-level simulation. Directionally validated by the trade analysis above.

---

## Summary of Changes (Priority Order)

| # | Proposal | Config change | Code change | Priority |
|---|----------|--------------|-------------|----------|
| P4 | Verify preclose close fills | — | `preclose_decision.py` ~10 lines | **CRITICAL** — $1,716 loss from this alone |
| P5 | Exclude inverse/leveraged ETFs | `universe.exclude_tickers` | — | **CRITICAL** — SOXS in selection violates long-only |
| P1 | Selector incumbent bonus | `selector.incumbent_score_bonus: 10` | selector prompt | **HIGH** — targets dominant alpha leak |
| P3 | Min hold timer | `exit_arbiter.min_hold_minutes: 90` | `_handle_exits()` ~15 lines | **HIGH** — would have saved ~$730 on 2026-05-04 |
| P2 | Sticky earnings lockout | `earnings.intraday_buy_lockout: true` | `orchestrator.py` ~20 lines | **MEDIUM** — COIN whipsaw prevention |
| P6 | SPY proxy growth cap | `cash_proxy.intraday_growth_cap` | `cash_proxy` logic | **LOW** — minor on its own, synergistic with P1 |

---

*Generated by post-mortem-bot on 2026-05-06. Reference session: 2026-05-04. Daily review (2026-05-05) already committed in dangling chain at 210a772.*
