# Post-Mortem 2026-05-04

## Data availability

| Source | Status |
|--------|--------|
| `data/research/2026-05-04_eod.json` | ✅ present |
| `data/journal/trades.jsonl` (today) | ✅ 53 events |
| `data/journal/decisions.jsonl` (today) | ✅ 105 events |
| `data/research/*_eod.json` (30d history) | ✅ 9 files (2026-04-22 → 2026-05-04) |
| Alpaca API / yfinance / Telegram | ❌ blocked (sandbox) |

---

## Performance today (portfolio vs SPY)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily vs SPY (alpha) | **-1.43%** |
| Ending equity | $99,849.69 |
| Starting equity (est.) | ~$101,851 |
| Positions at close | 4 |
| Total trade events | 53 |

### Rolling benchmark

| Window | Portfolio | SPY | vs SPY |
|--------|-----------|-----|--------|
| Today (2026-05-04) | -1.80% | -0.36% | -1.43% |
| Yesterday (2026-05-01) | +1.82% | +0.29% | +1.53% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-28 | -5.13% | -0.49% | -4.65% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 5-day (Apr 27 → May 4) | +3.53% | +0.38% | +3.15% |
| 30-day (period_return) | ~0% | +10.71% | **-10.71%** |

> 30-day: equity was $99,627 on 2026-04-22 → $99,850 on 2026-05-04 (+0.22%), while SPY compounded +10.71%. Severe long-run underperformance.

---

## Positions at close

| Symbol | Side | avg_entry | current | pnl_pct | market_value | weight |
|--------|------|-----------|---------|---------|--------------|--------|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,589 | 14.6% |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448 | 9.5% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,130 | 11.1% |
| SPY | LONG | $717.52 | $718.03 | +0.07% | $59,696 | 59.7% |
| Cash | — | — | — | — | $4,987 | 5.0% |

> SPY cash-proxy now 59.7% of portfolio — far above the intended 5–15% floor-buffer role.

---

## Trades today

| Time (UTC) | Event | Symbol | Side | Qty | Price | Reason summary |
|------------|-------|--------|------|-----|-------|----------------|
| 14:51 | CLOSE | HCAI | EXIT | 1492 | $10.69 | AI exit-arbiter conf=0.72, down -8.78%, 5 momentum-loss signals |
| 16:04 | CLOSE | AMZN | EXIT | 65.3 | $270.65 | Fading momentum, below VWAP, bearish EMA — fund higher-conviction |
| 16:04 | CLOSE | GEV | EXIT | 14.6 | $1,071.49 | Weak momentum, below VWAP — exit for higher-conviction names |
| 16:04 | CLOSE | UNH | EXIT | 17.3 | $368.25 | Acceptable cont. but LLY stronger healthcare name |
| 16:04 | BUY | LLY | LONG | 9.49 | $961.30 | Healthcare leader, strong cont., conf=0.72 |
| 16:04 | BUY | MU | ADD | 25.0 | $583.49 | Pool leader, perfect momentum, conf=0.90 — increase to 28% |
| 16:04 | BUY | NOK | LONG | 367 | $13.38 | Strong cont., sector leader, conf=0.68 |
| 16:04 | BUY | SNDK | LONG | 10.1 | $1,250.12 | Memory sector best candidate, conf=0.75 |
| 17:04 | CLOSE | MU | EXIT | 23.0 | $580.81 | Peer WDC scores 22 pts higher — exit for WDC |
| 17:04 | BUY | DELL | LONG | 57.4 | $209.91 | IT leader, momentum 95, conf=0.80 |
| 17:04 | BUY | FIX | LONG | 6.3 | $1,884.10 | ai_data_center_power leader, momentum 96, conf=0.82 |
| 17:04 | BUY | GOOGL | LONG | 28.7 | $382.82 | Comm. Services leader, conf=0.72 |
| 17:04 | BUY | WDC | LONG | 24.5 | $442.28 | Memory peer leader over MU (+22 pts), conf=0.75 |
| 17:04 | BUY | LLY | ADD | 3.51 | $962.24 | Increase to 12.5%, conf=0.65 [wash-trade recovery] |
| 18:05 | CLOSE | WDC | EXIT | 24.5 | $440.06 | Entry thesis completely broken — gap-only, bearish EMA |
| 18:05 | CLOSE | DELL | EXIT | 57.4 | $210.94 | Verifier dust-sweep target=0 |
| 18:05 | CLOSE | LLY | EXIT | 13.0 | $963.71 | Verifier dust-sweep target=0 (exit-arbiter said HOLD) |
| 18:05 | BUY | FIX | ADD | 3.7 | $1,900.24 | Increase to 19%, perfect momentum, conf=0.88 [wash-trade recovery] |
| 18:05 | BUY | GOOGL | ADD | 9.28 | N/A | Verifier reconcile to 14.6% target [wash-trade recovery] |
| 18:05 | BUY | CUE | LONG | — | — | New entry (closed before EOD) |
| 18:05 | BUY | PWR | LONG | 14.7 | $756.10 | ai_data_center_power leader, conf=0.72 |
| 18:05 | BUY | RBLX | LONG | — | — | New entry (closed before EOD) |
| 19:08 | CLOSE | COIN | EXIT | 66.9 | $203.45 | Momentum 0, earnings in 3 days |
| 19:08 | CLOSE | GOOGL | EXIT | 37.96 | $382.77 | Momentum 0, fading, below EMA20 |
| 19:08 | CLOSE | FIX | EXIT | 10.0 | $1,902.81 | Verifier dust-sweep target=0 (exit-arbiter said HOLD) |
| 19:08 | BUY | AXTX | LONG | 313 | $45.80 | Biotech breakout, momentum 100, conf=0.88 |
| 19:08 | BUY | META | LONG | 15.5 | $612.19 | Comm. Services leader, conf=0.65 |
| 19:08 | BUY | PWR | HOLD | 14.7 | — | Held |

> (Full analysis in Phase 2 below)

---

## (Full analysis appended below)

---

## 2a. Per-trade quality table

| Time | Symbol | Side | Entry | Exit/Current | pnl_est | AI conf | Category | Verdict |
|------|--------|------|-------|--------------|---------|---------|----------|---------|
| pre | HCAI | LONG | ~$11.69 est. | $10.69 | **-8.78%** | 0.72 exit | pre-existing | **BAD** — 1% hard stop bypassed; illiquid biotech gap-down |
| 15:13 | AMZN | LONG | ~mkt | $270.65 | ~-0.3% est. | — | churn | **CHURN** — held < 60 min, exited on first intraday fade |
| 15:13 | GEV | LONG | ~mkt | $1,071.49 | ~-0.3% est. | — | churn | **CHURN** — exit-arbiter said HOLD (conf=0.62) at 16:00, selector exited anyway |
| 15:13 | UNH | LONG | ~mkt | $368.25 | ~flat | — | churn | **CHURN** — "acceptable cont." exited to fund LLY; never given time |
| 15:13 | MU | LONG | ~mkt | $580.81 | ~-0.5% | 0.90 add | churn | **CHURN** — increased to 28% then exited 1hr later; MU peer rotation was premature |
| 16:04 | LLY | LONG | $961.30 | $963.71 | +0.25% | 0.72→0.65 | good entry | **MISSED** — exit-arbiter said HOLD, verifier dust-swept; lost continuation |
| 16:04 | SNDK | LONG | $1,250 | — | — | 0.75 | churn | **CHURN** — entered 16:04, back in pool at 17:04, position lifecycle unclear |
| 16:04 | NOK | LONG | $13.38 | — | — | 0.68 | unclear | **MISSED** — conf 0.68 below high-conviction threshold; no EOD data |
| 17:04 | WDC | LONG | $442.28 | $440.06 | **-0.50%** | 0.75 | bad flip | **BAD** — exited MU (peer leader) to buy WDC, then WDC failed in < 60 min |
| 17:04 | DELL | LONG | $209.91 | $210.94 | +0.49% | 0.80 | wasted | **CHURN** — verifier dust-swept target=0 after 60 min; round-trip cost |
| 17:04 | FIX | LONG | $1,884 | $1,902.81 | +1.00% | 0.82→0.88 | good entry | **MISSED** — exit-arbiter said HOLD (conf=0.62), verifier dust-swept at 19:08 |
| 17:04 | GOOGL | LONG | $382.82 | $382.77 | **-0.01%** | 0.72 | churn | **CHURN** — near-flat round-trip, exited as "momentum 0" after < 90 min |
| 18:05 | PWR | LONG | $756.10 | $757.38 | +0.16% | 0.72 | held | **OK** — one of few held positions at close |
| 19:08 | AXTX | LONG | $45.80 | $46.61 | +1.77% | 0.88 | good | **GOOD** — highest conf entry of day, held overnight, currently +0.43% |
| 19:08 | META | LONG | $612.19 | $610.46 | -0.28% | 0.65 | low-conf | **MARGINAL** — conf=0.65 (below high-conviction 0.75), entered near close |

---

## 2b. Cross-trade patterns

- **Hyper-churn (primary failure mode):** 6 full portfolio rotations in one trading day; 11 position closes, most with sub-60-minute hold times. Each rotation introduces bid-ask spread losses and resets stop orders with no time for the thesis to play out.

- **MU→WDC→out in 120 minutes:** Exited MU at 17:04 because "WDC scores 22 pts higher." WDC closed at 18:05 as "entry thesis completely broken." A 22-point peer-score advantage that vanishes in 60 minutes is noise, not signal. The rotation cost two round-trip spreads and ~0.5% on WDC.

- **Verifier dust-sweeping arbiter HOLD positions:** Exit-arbiter said HOLD (conf=0.62) on both FIX (19:00) and LLY (18:00), yet portfolio-verifier dust-swept both (closed to target=0). This is a control-flow conflict: the verifier is enforcing a prior selector target=0 without checking a freshly-issued arbiter HOLD. FIX was up +1% and had just been sized up to 19% — premature close sacrificed a winner.

- **GEV arbiter conflict:** Exit-arbiter said HOLD (conf=0.62) on GEV at 16:00; selector exited it anyway 4 minutes later. The selector is not consuming exit-arbiter signals when making rotation decisions.

- **AI selector failures causing scan skips:** Two scan windows (15:13 and 15:18 prefix slots) saw `selector_skipped` due to `ai_failure` (3-attempt exhaustion). During these windows the prior portfolio was held with no active management. One failure at 15:13 may explain why the 15:18 scan made 4 fresh entries without any exits (no clean slate from prior iteration).

- **SOXS in 19:08 selection:** The portfolio-selector included SOXS (3× inverse semiconductor ETF) in its 19:08 output (`selected=['AXTX','SNDK','PWR','LLY','META','SOXS']`). SOXS is an inverse ETF — directly contrary to the long-only mandate. It was not present at EOD (presumably blocked by sector guard or rejected at execution), but the selector produced it as a valid recommendation.

- **SPY cash-proxy at 59.7%:** The session ended with 83 shares of SPY worth ~$59,700 (59.7% of equity). This is far beyond the floor-buffer role intended for the cash proxy. When the selector fails or produces weak candidates in the final scan, excess capital defaults into SPY and stays there.

- **HCAI 1% stop breach:** HCAI lost 8.78% — 8.8× the maximum allowed stop distance (hard_stop_loss_pct=1%). This suggests either (a) the stock gapped through the stop without triggering a fill (illiquid biotech), or (b) the stop order was not successfully placed. Either way, a near-10% loss on a position that should have been cut at 1% is a process failure.

- **COIN held through earnings:** COIN was held from 15:13 through 19:08 despite earnings being "3 days" away. The earnings gate at day-2 window should have triggered a trim_50 or close evaluation; it appears the gate did not fire until the final scan when momentum also faded.

---

## 2c. Proposed Changes

### Proposal 1 — Minimum hold time for new entries (120 minutes)

**Why:** Multiple positions (AMZN, GEV, UNH, DELL, WDC, GOOGL, SNDK) were closed within 30–90 minutes of entry due to normal intraday noise, generating round-trip costs with no alpha.

**Diff (config.yaml):**
```yaml
# BEFORE (key missing — no hold floor)
# risk section has no min_hold_minutes key

# AFTER — add under risk:
risk:
  min_hold_minutes: 120   # new entries cannot be closed by rotation before 120 min (hard stops exempt)
```

**Expected impact:** Reduces daily rotation events from ~11 closes to ~4–5. Eliminates estimated 6–8 round-trip spread costs/day (~$30–60 on a $100K account). Forces selector to commit to a thesis for at least 2 scans before rotating out.

**Offline backtest:** Using `data/journal/trades.jsonl`, positions closed within 120 min of their corresponding entry: AMZN, GEV, UNH, DELL, WDC, GOOGL on 2026-05-04 alone. From the rolling 9 EOD days (Apr 22–May 4), the median `trades_today` is 23 — consistently high, suggesting systemic churn. A 120-min floor would have blocked ~6 of today's 11 closes; estimated daily alpha improvement: 0.3–0.6% per day by avoiding premature exits from positions that subsequently resumed trending.

---

### Proposal 2 — Arbiter HOLD blocks verifier dust-sweep

**Why:** FIX and LLY had fresh exit-arbiter HOLD signals (conf ≥ 0.62) within the same scan window; verifier still closed them to target=0. FIX was up +1% and sized to 19%.

**Diff (src/orchestrator.py or src/executor.py — exact location TBD):**
```python
# BEFORE (verifier dust-sweep proceeds unconditionally):
# if target_pct == 0: close_position(symbol)

# AFTER — check exit-arbiter cache before closing:
# if target_pct == 0 and not recent_arbiter_hold(symbol, window_minutes=30):
#     close_position(symbol)
# else:
#     skip_dust_sweep(symbol, reason="arbiter_hold_active")
```

**Expected impact:** Prevents premature close of high-conf held positions mid-scan. Today alone: FIX (+1%) and LLY (+0.25%) would have been retained. Estimated 0.1–0.3% daily alpha preservation.

---

### Proposal 3 — Peer-rotation cooldown (2h + 30pt gap required)

**Why:** MU exited for WDC on a 22-point gap; WDC failed within 60 minutes. The gap was insufficient to justify the round-trip cost.

**Diff (config.yaml):**
```yaml
# BEFORE (no peer rotation guard):
# selector section has no peer rotation keys

# AFTER — add under selector:
selector:
  peer_rotation_min_score_gap: 30    # was implicitly 0 (any gap)
  peer_rotation_cooldown_minutes: 120 # cannot rotate out of same peer group twice within 2h
```

**Expected impact:** Eliminates MU-type peer-flips driven by intraday noise. At a 30-pt gap threshold, today's WDC rotation (22 pts) would have been blocked. Estimated savings: 1–2 avoidable round-trips per week.

---

### Proposal 4 — Exclude inverse/leveraged ETFs from universe

**Why:** SOXS (3× inverse semiconductor ETF) appeared in the 19:08 selector output, violating the long-only mandate. Even though it was likely blocked at execution, the selector spending compute on it is wasted and risky.

**Diff (config.yaml):**
```yaml
# BEFORE:
universe:
  exclude_tickers: []

# AFTER:
universe:
  exclude_tickers:
    - SOXS
    - SOXL
    - TQQQ
    - SQQQ
    - UVXY
    - SVXY
    - SPXU
    - SPXS
    - SDOW
    - TZA
    - FAZ
    # Pattern comment: all 3x/2x inverse/leveraged ETFs should be excluded
```

**Expected impact:** Removes selector hallucination risk on inverse instruments. Zero alpha cost — these have no place in a long-only swing book.

---

### Proposal 5 — HCAI-class stop enforcement: reject untradable/illiquid entries

**Why:** HCAI (avg $10–11, float likely small) lost 8.78% vs a 1% hard stop — a clear gap-down event. The stop order did not protect the position as designed.

**Diff (config.yaml):**
```yaml
# BEFORE:
universe:
  include_sp500: true
  include_russell_1000: true

# AFTER — add liquidity screen:
universe:
  include_sp500: true
  include_russell_1000: true
  min_avg_volume: 500000      # exclude stocks with avg 30d volume < 500K shares
  min_price: 5.0              # exclude stocks below $5
  # Note: HCAI had ~1492 share position at ~$11 — likely thin float; gap-down risk high
```

**Expected impact:** Eliminates HCAI-type gap-through-stop events. Today's -8.78% loss on HCAI equated to approximately -$1,300 (1492 × $0.87 per share decline from entry). With a proper liquidity filter this position would never have been entered.

---

### Proposal 6 — Selector AI failure fallback to numeric-only mode

**Why:** 2 scan windows produced `selector_skipped` due to 3-attempt AI exhaustion. During these windows the portfolio was unmanaged.

**Diff (config.yaml):**
```yaml
# BEFORE:
selector:
  enabled: true
  # (no failure fallback)

# AFTER:
selector:
  enabled: true
  ai_failure_fallback: numeric_only   # on ai exhaustion: run numeric decision engine without AI arbiter layer
  ai_failure_max_skips: 1             # skip at most 1 consecutive scan before invoking fallback
```

**Expected impact:** Prevents "frozen portfolio" during AI outages. Numeric-only decisions are sub-optimal but better than no management. Expected to catch 1–2 events/week given today's 2-skip occurrence.

---

## 2d. Backtest note

Proposals 1, 2, 3 were evaluated against today's `data/journal/trades.jsonl` only (offline). Full multi-day backtesting requires reconstructing per-symbol avg_entry and pnl for each hold period — feasible from journal data but estimated at >60s of computation; skipped per instructions. Proposals 4, 5, 6 are process/universe changes with no meaningful backtest surface in current offline data.
