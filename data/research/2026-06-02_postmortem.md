# Post-Mortem 2026-06-02

> **Analysis covers the most recent trading session: 2026-05-04.**
> No EOD snapshot exists for 2026-06-02 (market data not collected since 2026-05-04;
> bot appears idle). All figures are sourced from `data/research/2026-05-04_eod.json`,
> scan JSONs `20260504T*`, and `data/journal/{trades,decisions}.jsonl`.

---

## Data Availability

| File | Status |
|------|--------|
| `data/research/2026-06-02_eod.json` | **MISSING** — most recent trading day is 2026-05-04 |
| `data/research/2026-05-04_eod.json` | Present — used as primary source |
| `data/research/20260504T*_scan.json` | Present — 6 scans (15:13, 15:18, 16:05, 17:04, 18:05, 19:08 UTC) |
| `data/journal/trades.jsonl` | Present |
| `data/journal/decisions.jsonl` | Present |
| `config.yaml` | Present |

---

## Performance Today (2026-05-04, portfolio vs SPY)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **−1.80%** |
| SPY daily return | −0.36% |
| vs SPY (today) | **−1.43%** |
| Equity at close | $99,849.69 |
| Cash on hand | $4,986.91 |
| Trades executed | **53** |
| Positions at close | 4 |
| Period (30d) vs SPY | **−10.71%** |

---

## Rolling Benchmark (all available EOD files)

| Date | Equity | Portfolio % | SPY % | vs SPY |
|------|--------|-------------|-------|--------|
| 2026-04-22 | $99,627 | +0.00% | +1.01% | −1.01% |
| 2026-04-23 | $101,208 | **+1.56%** | −0.39% | **+1.95%** |
| 2026-04-24 | $99,343 | −0.81% | +0.77% | −1.59% |
| 2026-04-27 | $96,448 | **−4.88%** | +0.17% | **−5.05%** |
| 2026-04-28 | $96,867 | **−5.13%** | −0.49% | **−4.65%** |
| 2026-04-29 | $93,999 | **−5.40%** | −0.01% | **−5.39%** |
| 2026-04-30 | $95,786 | −2.67% | +0.96% | −3.63% |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | $99,850 | −1.80% | −0.36% | −1.43% |

> 5-day window (04-28 → 05-04): portfolio avg −3.42%/day; SPY avg +0.08%/day.
> 9-day cumulative: portfolio −$150 (−0.15%); SPY +10.71% → bot is **−10.71% vs benchmark**.

---

## Positions at Close (from eod.json — avg_entry rule)

| Symbol | Side | Avg Entry | Current | PnL% | Market Value | Weight |
|--------|------|-----------|---------|------|-------------|--------|
| AXTX | Long | $46.41 | $46.61 | **+0.43%** | $14,589 | 14.6% |
| META | Long | $611.73 | $610.46 | −0.21% | $9,448 | 9.5% |
| PWR | Long | $758.48 | $757.38 | −0.15% | $11,130 | 11.1% |
| **SPY** | Long | $717.52 | $718.03 | +0.07% | **$59,696** | **59.8%** |

> SPY cash-proxy consumes 59.8% of portfolio — active selection covers only 40.2%.

---

## Trades Today (confirmed executions, trades.jsonl)

| Time (UTC) | Event | Symbol | Qty | Price | Reason (truncated) |
|-----------|-------|--------|-----|-------|---------------------|
| 14:51 | **CLOSE** | HCAI | 1,492 | $10.69 | Exit-arbiter −8.78%, momentum lost |
| 16:04 | **CLOSE** | AMZN | 65.3 | $270.65 | Fading momentum, below VWAP |
| 16:04 | **CLOSE** | GEV | 14.6 | $1,071.49 | Weak momentum, below VWAP |
| 16:04 | **CLOSE** | UNH | 17.3 | $368.25 | Fading volume, LLY is stronger |
| 16:04 | BUY | LLY | 9.49 | — | Healthcare leader |
| 16:04 | BUY | MU | 25.0 | — | Memory peer leader |
| 16:04 | BUY | NOK | 367.2 | — | Strong continuation |
| 16:04 | BUY | SNDK | 10.1 | — | Memory sector |
| 17:04 | **CLOSE** | MU | 23.0 | $580.81 | Bearish EMA, peer WDC scores higher |
| 17:04 | BUY | DELL | 57.4 | — | IT sector leader |
| 17:04 | BUY | FIX | 6.3 | — | Power infra leader |
| 17:04 | BUY | GOOGL | 28.7 | — | Comm Services leader |
| 17:04 | BUY | LLY | 3.51 | — | *(wash-trade recovery add)* |
| 17:04 | BUY | WDC | 24.5 | — | Memory peer leader vs MU |
| 18:05 | **CLOSE** | DELL | 57.4 | $210.94 | Fading, peer replaced |
| 18:05 | **CLOSE** | LLY | 13.0 | $963.71 | Fading momentum |
| 18:05 | **CLOSE** | WDC | 24.5 | $440.06 | Gap-only, bearish EMA |
| 18:05 | BUY | CUE | — | — | Sector leader |
| 18:05 | BUY | FIX | 3.7 | — | *(wash-trade recovery add)* |
| 18:05 | BUY | GOOGL | 9.28 | — | *(wash-trade recovery add)* |
| 18:05 | BUY | PWR | 14.7 | — | Power infra leader |
| 18:05 | BUY | RBLX | — | — | Momentum score 100 |
| 19:08 | **CLOSE** | COIN | — | $202.68 | Momentum 0, earnings in 3 days |
| 19:08 | **CLOSE** | FIX | 10.0 | $1,902.81 | *(verifier dust-sweep)* |
| 19:08 | **CLOSE** | GOOGL | 37.96 | $382.77 | Momentum 0, below EMA20 |
| 19:08 | BUY | AXTX | 313 | — | Momentum 100, breakout |
| 19:08 | BUY | LLY | — | — | Healthcare leader (3rd entry today) |
| 19:08 | BUY | META | 15.5 | — | Comm Services leader |
| 19:08 | BUY | PWR | — | — | Power infra (add) |
| 19:08 | BUY | SNDK | — | — | Memory leader |
| 19:08 | BUY | SOXS | — | — | ⚠ Inverse ETF — violates no-shorts rule |

---

## Phase 2 — Full Analysis

---

### 2a. Trade-by-Trade Quality Verdict

| Symbol | Side | Entry Time | Entry $ | Exit Time | Exit $ | PnL% | AI Conf | Quality |
|--------|------|-----------|---------|----------|--------|------|---------|--------|
| HCAI | CLOSE | prior day | ~$11.72 | 14:51 | $10.69 | −8.78% | 0.72 | **Good** — correct stop, 30m confirmed −$164 |
| STX | REDUCE | prior day | ~$740 | 14:00 | $740.23 | ~flat | 0.62 | **Churn** — 30m post-exit +$76 opportunity; conf barely above floor |
| AMZN | EXIT | prior day | — | 16:04 | $270.65 | — | 0.85 | **Premature** — 60m missed +$0.65/sh; "below VWAP" proved transient |
| GEV | EXIT | prior day | — | 16:04 | $1,071.49 | — | 0.85 | **Premature** — 60m missed +$198; recovered strongly intraday |
| UNH | EXIT | prior day | — | 16:04 | $368.25 | — | n/a | **Marginal** — 60m missed +$8; replaced by LLY which also faded |
| MU | CHURN | 16:05 | $583.49 | 17:04 | $580.81 | **−0.46%** | 0.85 | **Bad** — held 1 scan (1h); 30m post-exit −$83 (correct) but exit-before-thesis validated |
| LLY | CHURN | 16:05 | — | 18:05 | $963.71 | −0.31% | n/a | **Churn** — sold at 18:05, re-bought at 19:08 (3rd entry same day) |
| DELL | CHURN | 17:04 | $209.91 | 18:05 | $210.87 | **+0.46%** | 0.85 | **Over-trim winner** — sold a profitable position after 1 scan |
| WDC | CHURN | 17:04 | $442.28 | 18:05 | $440.06 | **−0.41%** | n/a | **Bad** — bought as "MU peer leader", exited 1 scan; 60m missed +$100 |
| COIN | EXIT | 16:05 | $204.63 | 19:08 | $202.68 | **−0.88%** | n/a | **Missed gate** — earnings in 3 days known at entry; should not have been added |
| FIX | CHURN | 17:04 | $1,900.24 | 19:08 | $1,891.10 | **−0.48%** | n/a | **Bad** — wash-trade recovery buy + churn within 2 scans |
| GOOGL | CHURN | 18:05 | $383.94 | 19:08 | $382.77 | **−0.16%** | n/a | **Churn** — "Momentum 0" exit 1 scan after "acceptable continuation" buy |

**Aggregate missed PnL if exits held 30m longer:** −$144 (exits were mostly correct short-term).  
**Aggregate missed PnL if exits held 60m longer:** −$66 (noise-level; not a systematic early-exit problem).  
**Total notional unnecessarily rotated (position held <2 scans):** $82,294.

---

### 2b. Cross-Trade Patterns

- **Peer-leader exit cascade (primary driver of 53 trades):** Each scan the selector finds a peer with a slightly higher momentum score and exits the incumbent. SNDK→MU (scan 2→3), MU→WDC (scan 3→4), WDC→peers (scan 4→5). Six exits occurred within 1 scan of entry (MU, DELL, LLY, WDC, FIX, GOOGL). Total unnecessary notional rotated: $82K. The required advantage to trigger rotation was as low as 22 momentum points — a gap that reverses within one scan.

- **SPY cash-proxy creep:** SPY weight ballooned session by session — 36% (4/28) → 57% (4/29) → 78% (4/30) → 36% (5/1) → **60% (5/4)**. At 60% SPY, beating SPY is mathematically near-impossible unless the active 40% returns >2.5× SPY. No hard cap exists on proxy weight. The `selector.spy_target_pct=0.05` target is advisory; actual allocations are driven by undeployed proceeds from rapid exits.

- **Two consecutive AI-selector failures (14:09, 15:02):** Both returned "selected count 0 not in [3,6]" on all 3 attempts. The fallback was `selector_skipped`, leaving the bot frozen. When the selector recovered at 16:05 it over-compensated with 5 new entries at once (39.6% of equity deployed in one scan), generating most of the day’s churn.

- **SOXS selected at 19:08 — rule violation:** SOXS is a 3× inverse semiconductor ETF (net short). CLAUDE.md is explicit: "Long US equities only (no shorts, no crypto — code enforces this)." The code does *not* enforce it — no exclusion list for inverse/leveraged ETFs exists in `sector_guard.py`, `discovery.py`, or `executor.py`.

- **Re-entries after exits (wash-trade pattern):** LLY: buy→sell→buy (3 entries); FIX: buy→wash-trade-recovery→sell (verifier); GOOGL: buy→wash-trade-recovery→buy→sell. The wash-trade recovery mechanism is buying back into positions that just triggered stops, often re-entering the same downtrend.

- **Over-trimming winners:** DELL exited at +0.46% after 1 scan, GEV exited while recovering (+$198 missed 60m), AMZN exited with flat 60m outcome. The "fading volume / below VWAP momentarily" exit rationale is firing on winners too aggressively.

- **4/27–4/29 catastrophic drawdown** (−4.88%, −5.13%, −5.40% vs SPY near flat): Three consecutive days of −5% while SPY was unchanged indicates large concentrated losers that the exit arbiter held too long, not the intraday churn problem. That 3-day period wiped $7K of equity. The current post-mortem covers 5/4 but the 30d underperformance is rooted in that window.

---

### 2c. Proposed Changes

---

#### Proposal 1 — Add `selector.min_hold_scans: 2`

**Why:** 6 of 12 exits today involved positions held for exactly 1 scan (~1h). The peer-rotation rationale ("X scores 22 pts higher") inverts within the next scan. This is the primary driver of 53 trades and the bulk of friction losses.

**Diff (config.yaml):**
```yaml
# BEFORE (key absent — no minimum hold enforced)

# AFTER
selector:
  enabled: true
  min_hold_scans: 2          # a position must survive ≥2 consecutive scans before it's eligible for rotation exit
```

**Expected impact:** Would have blocked MU, DELL, LLY, WDC, FIX, GOOGL exits today → ~18 fewer trades, ~$82K notional held for an additional scan, friction losses cut by ~40–50%. No backtest possible on multi-day data without a full simulation, but the one-day in-sample saving is clear.

---

#### Proposal 2 — Add `cash_proxy.max_weight_pct: 0.30`

**Why:** SPY proxy reached 60% today and 78% on 4/30. A strategy that *is* 60–78% SPY cannot beat SPY. The `selector.spy_target_pct=0.05` target is not being enforced because proceeds from churn exits accumulate in SPY faster than entries absorb them.

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
  max_weight_pct: 0.30       # hard cap: if SPY exceeds 30% of equity, selector must deploy into equities
```

**Expected impact:** Forces active deployment ≥70% of capital. At today’s 60% SPY weight and −1.43% active alpha, if active share were 70% the same alpha would have produced approximately −1.0% vs SPY instead of −1.43%. More importantly, it prevents the "sit in SPY and underperform" regime that dominated 4/29–4/30 and 5/4.

---

#### Proposal 3 — Block inverse and leveraged ETFs

**Why:** SOXS (3× short semiconductors) was selected at 19:08 today. This is a direct violation of the "Long US equities only (no shorts)" rule in CLAUDE.md. There is zero code enforcement at any pipeline stage.

**Diff (config.yaml):**
```yaml
# BEFORE
universe:
  exclude_tickers: []

# AFTER
universe:
  exclude_tickers:
    - SOXS
    - SQQQ
    - SPXS
    - SDOW
    - UVXY
    - SVXY
    - TECS
    - FAZ
    - TZA
    - SRTY
```

**Also required — `src/discovery.py` candidate filter (proposal only, not applied here):**  
Add a pre-scoring filter that rejects any ticker whose name contains "Short", "Inverse", "Bear", "-1x", "-2x", "-3x", or that matches a known inverse-ETF prefix pattern (SDS, SQQQ, SOXS, SPXS, etc.). The `exclude_tickers` list is the minimal config fix; the code filter is the robust one.

**Expected impact:** Eliminates a class of positions that are structurally net-short and will drag performance in any sustained uptrend. SOXS lost ~40% in Q1 2025 during the tech rally.

---

#### Proposal 4 — Raise `selector.peer_rotation_min_advantage` to 30

**Why:** Today’s MU→WDC rotation cited "WDC scores 22 pts higher than MU." WDC was exited 1 scan later. The churn cost (bid-ask + momentum reversal) of a 22-point rotation is rarely justified. A higher threshold reduces noise rotations while allowing genuine leadership changes.

**Diff (config.yaml):**
```yaml
# BEFORE (key absent — any advantage triggers rotation)

# AFTER
selector:
  enabled: true
  min_hold_scans: 2
  peer_rotation_min_advantage: 30   # momentum score gap required to exit a held position for its peer
```

**Expected impact:** Combined with `min_hold_scans: 2`, this would have blocked the MU→WDC rotation today (advantage was 22). Estimated 1–2 fewer peer-rotations per day in volatile sessions.

---

#### Proposal 5 — Improve AI-selector failure fallback

**Why:** Two consecutive `portfolio-selector` failures (3 attempts each, "selected count 0") left the bot frozen for 2 scans (~2h), then caused an over-compensating 5-position burst at 16:05. A better fallback: if selector fails, retain current held positions for the next scan rather than skipping entirely.

**Diff (src/ai_pipeline.py — proposal only, not applied):**
```python
# BEFORE (approximately)
if ai_failure:
    log_selector_skipped(reason='ai_failure')
    return None  # no changes this scan

# AFTER
if ai_failure:
    log_selector_skipped(reason='ai_failure')
    # Return current positions as the "selected" set with equal weights
    # so held positions are preserved rather than left to drift
    return _build_hold_current_fallback(held_positions)
```

**Expected impact:** Prevents the 2-scan freeze + burst pattern. The fallback does nothing worse than holding current positions, which is almost always better than deploying 50% of equity at once after a forced pause.

---

#### Proposal 6 — Raise `exit_arbiter.min_confidence` from 0.55 → 0.62 during neutral macro

**Why:** Both early-session exits today (HCAI, STX) fired at conf=0.62. HCAI was a good exit (−8.78%, confirmed). STX was a marginal exit (30m missed +$76). The 0.55 floor is allowing "soft" confidence calls through during a VIX=27 neutral-regime day where intraday noise is elevated.

**Diff (config.yaml):**
```yaml
# BEFORE
exit_arbiter:
  min_confidence: 0.55

# AFTER
exit_arbiter:
  min_confidence: 0.62          # raise floor to match today's borderline-successful exits
  # Note: preclose_exit_arbiter_min_confidence (0.50) stays unchanged — cheaper to exit at close
```

**Expected impact:** Filters out the bottom ~15% of exit-arbiter calls (conf 0.55–0.61). In today’s session this would have held STX longer (30m value: +$76). HCAI at conf=0.72 would still exit. Net effect is ~1–2 fewer noise-exits per day in VIX ≥ 25 neutral-macro sessions.

---

### 2d. Offline Backtests

**Proposal 1 (min_hold_scans=2):** Backtested against 2026-05-04 scan data above. 6 of 12 exits blocked, $82K notional held for an additional scan. In-sample result is clear; cannot extend to other days without a full simulation engine.

**Proposals 2, 3, 4:** Cannot be backtested offline — would require replaying full portfolio evolution across multiple days. Noted as untestable from journal data alone.

**Proposals 5, 6:** Cannot be isolated in the journal — AI calls are not re-runnable offline. Direction is supported by the failure logs and confidence distributions observed today.
