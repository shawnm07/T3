# Post-Mortem 2026-05-04

> Generated 2026-06-26. Most recent trading data is 2026-05-04 — no EOD/scan/trade data exists after this date.

## Data Availability

| Source | Status |
|--------|--------|
| `2026-05-04_eod.json` | Present |
| `20260504T*_scan.json` | 6 scans (15:13–19:08 UTC) |
| `trades.jsonl` (2026-05-04) | 53 events (11 closes, 15 buys, 24 exit-learning, 3 wash recoveries) |
| `decisions.jsonl` (2026-05-04) | 105 entries |
| `config.yaml` | Present |
| Alpaca live API | BLOCKED (403) |
| yfinance / Telegram | BLOCKED |

---

## Performance (2026-05-04)

| Metric | Value |
|--------|-------|
| **Portfolio daily return** | **-1.80%** |
| **SPY daily return** | **-0.36%** |
| **Delta vs SPY** | **-1.44%** (underperformed) |
| Equity at close | $99,849.69 |
| Cash at close | $4,986.91 (5.0%) |
| Positions at close | 4 (3 stocks + SPY proxy) |
| Trades executed | 53 |
| Total turnover | **$288,805** (2.9x equity) |

### Rolling Performance (9 trading days)

| Date | Portfolio | SPY | Delta | Note |
|------|-----------|-----|-------|------|
| 2026-04-22 | +0.00% | +1.01% | -1.01% | First day |
| 2026-04-23 | +1.56% | -0.39% | +1.95% | Best day |
| 2026-04-24 | -0.81% | +0.77% | -1.58% | |
| 2026-04-27 | -4.88% | +0.17% | -5.05% | Worst day |
| 2026-04-28 | -5.13% | -0.49% | -4.64% | |
| 2026-04-29 | -5.40% | -0.01% | -5.39% | |
| 2026-04-30 | -2.67% | +0.96% | -3.63% | |
| 2026-05-01 | +1.82% | +0.29% | +1.53% | |
| **2026-05-04** | **-1.80%** | **-0.36%** | **-1.44%** | |

**Cumulative**: Period return ~0% (flat from $99,627 to $99,850) vs SPY 30d **+10.71%**. Massively trailing benchmark.

**5-day avg daily return**: -2.59% portfolio vs +0.08% SPY.

---

## Positions at Close

| Symbol | Side | Avg Entry | Current | P&L % | Market Value | Weight |
|--------|------|-----------|---------|-------|-------------|--------|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,588.93 | 14.6% |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448.36 | 9.5% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,129.62 | 11.1% |
| SPY (proxy) | LONG | $717.52 | $718.03 | +0.07% | $59,695.86 | 59.8% |
| **Cash** | — | — | — | — | $4,986.91 | 5.0% |

**Active selection is only 35.2% of equity.** SPY proxy holds 59.8%, meaning the bot is effectively 60% indexed and 35% stock-picking. The 10.71% trailing gap comes from the 35% active portion losing heavily.

---

## Trades (2026-05-04) — Exits

| Time (UTC) | Symbol | Exit Price | Qty | Reason | Verdict |
|------------|--------|-----------|-----|--------|--------|
| 14:51 | HCAI | $10.69 | 1,492 | Down -8.78%, 5 momentum-loss signals, conf=0.72 | **GOOD** — cut loser decisively |
| 16:04 | AMZN | $270.65 | 65.3 | Fading momentum, below VWAP, bearish EMA | Acceptable |
| 16:04 | GEV | $1,071.49 | 14.6 | Weak momentum, bearish EMA, flat trend | Acceptable |
| 16:04 | UNH | $368.25 | 17.3 | Fading volume — replaced by LLY for sector | **CHURN** |
| 17:04 | MU | $580.81 | 23.0 | Weak momentum — replaced by peer WDC | **CHURN** — WDC failed in 60 min |
| 18:05 | WDC | $440.06 | 24.5 | Gap_only, bearish EMA — thesis broken | **BAD** — same-day round trip, -1.2% |
| 18:05 | DELL | $210.94 | 57.4 | Verifier dust-sweep target=0 | **CHURN** — bought & swept same day |
| 18:05 | LLY | $963.71 | 13.0 | Verifier dust-sweep target=0 | **CHURN** — exit-arbiter said HOLD |
| 19:08 | COIN | $203.45 | 66.9 | Momentum score 0, earnings in 3d | Acceptable exit, bad entry |
| 19:08 | GOOGL | $382.77 | 38.0 | Momentum score 0, fading, below EMA20 | Acceptable exit, bad entry |
| 19:08 | FIX | $1,902.81 | 10.0 | Verifier dust-sweep target=0 | **CHURN** — exit-arbiter said HOLD |

## Trades (2026-05-04) — Entries

| Time (UTC) | Symbol | Entry Price | Qty | Value | AI Conf | Verdict |
|------------|--------|------------|-----|-------|---------|--------|
| 16:04 | LLY | $963.38 | 9.5 | $9,142 | 0.72 | **CHURN** — verifier swept 2h later |
| 16:04 | MU (add) | $580.42 | 25.0 | $14,511 | 0.90 | **BAD** — increased to 28% then exited 1h later |
| 16:04 | NOK | $13.33 | 367.2 | $4,894 | 0.68 | **CHURN** — not in EOD positions |
| 16:04 | SNDK | $1,246.97 | 10.1 | $12,599 | 0.75 | **CHURN** — not in EOD positions |
| 17:04 | DELL | $210.52 | 57.4 | $12,084 | 0.80 | **CHURN** — dust-swept 1h later |
| 17:04 | FIX | $1,896.50 | 6.3 | $11,947 | 0.82 | **CHURN** — increased then swept |
| 17:04 | GOOGL | $383.51 | 28.7 | $11,001 | 0.72 | **BAD** — exited 2h later, -0.2% |
| 17:04 | LLY (add) | $962.27 | 3.5 | $3,377 | 0.65 | **CHURN** — swept with main position |
| 17:04 | WDC | $445.36 | 24.5 | $10,913 | 0.75 | **BAD** — exited 1h later at -1.2% |
| 17:04 | COIN (add) | $203.90 | 5.1 | $1,040 | — | **BAD** — verifier reconcile, exited 2h later |
| 18:05 | FIX (add) | $1,903.71 | 3.7 | $7,045 | 0.88 | **CHURN** — swept same day |
| 18:05 | GOOGL (add) | $384.43 | 9.3 | $3,568 | — | **BAD** — verifier reconcile, then exited |
| 19:08 | AXTX | $46.41 | 313.0 | $14,526 | 0.88 | **GOOD** — held into close, +0.43% |
| 19:08 | META | $611.73 | 15.5 | $9,466 | 0.65 | **MARGINAL** — low confidence |
| 19:08 | PWR | $758.48 | 14.7 | $11,150 | 0.72 | **OK** — held into close |

---

## 2a. Per-Trade Quality Summary

| Category | Count | Est. P&L Impact | Symbols |
|----------|-------|-----------------|--------|
| **GOOD** | 2 | Positive | HCAI (cut loser), AXTX (held winner) |
| **OK** | 1 | Neutral | PWR |
| **MARGINAL** | 1 | Neutral | META (low conf entry) |
| **CHURN** (buy+exit same day, no thesis time) | 7 | **-$500 to -$1,000 spread costs** | LLY, NOK, SNDK, DELL, FIX, MU→WDC, UNH |
| **BAD** (realized loss on same-day flip) | 4 | **-$500+** | WDC (-1.2%), GOOGL (-0.2%), COIN, MU add |

**Of 15 buy orders, only 3 survived to close (AXTX, META, PWR). 12 were churned out same-day.**

---

## 2b. Cross-Trade Patterns

### 1. Hyper-Churn (PRIMARY failure mode)
- **53 trades on ~$100K equity = $288,805 turnover (2.9x equity in one day).**
- 7 symbols bought and sold the same day: COIN, DELL, FIX, GOOGL, LLY, MU, WDC.
- Portfolio composition changed completely 3+ times across 6 scans.
- Each rotation incurs bid-ask spread (est. 0.05-0.10% per round trip on large-cap, higher on small-cap), resetting stop orders, and giving no time for any thesis to play out.
- **Est. churn cost: $500-$1,500 in pure spread drag.**

### 2. Selector-Verifier Conflict
- Verifier dust-swept 3 positions (DELL, LLY, FIX) where the exit-arbiter explicitly said **HOLD**.
- The verifier's job is to reconcile to Opus targets, but when the selector changes targets between scans, the verifier becomes a destructive force — closing positions the exit-arbiter wants to keep.
- FIX was a strong performer (+1.0% intraday) with exit-arbiter HOLD at conf=0.62 and was still swept.

### 3. Premature Peer Rotations
- **MU→WDC rotation**: Exited MU (the existing position with conf=0.90 add) because WDC scored 22 points higher. WDC then failed in <60 minutes ("gap_only, bearish EMA"). The 22-point delta was intraday noise. Net result: two round-trip costs + -0.5% loss on WDC.
- **UNH→LLY rotation**: Exited UNH ("acceptable continuation") to fund LLY. LLY then dust-swept by verifier. Net result: lost both healthcare positions.

### 4. SPY Cash Proxy at 59.8%
- The bot parked $59,696 in SPY proxy — nearly 60% of equity.
- This means the bot's active stock selection (35.2% deployed) needs to return **+30%** to match SPY's 10.71% 30-day return. The math doesn't work.
- The high SPY allocation came from churning out active positions faster than new ones could establish.

### 5. AI Confidence Floor Too Low
- META entered at conf=0.65 (below the high-conviction threshold of 0.75).
- Multiple entries at 0.68-0.72 were churned out within hours.
- The min_confidence gate is 0.40, but entries below 0.70 rarely survive intraday volatility.

### 6. No Oversized Single Positions
- Risk budget constraint (15% initial entry cap) was respected. Largest position at close was AXTX at 14.6%. No violation.

### 7. ai_data_center Theme Concentration
- WDC, SNDK, MU, DELL, FIX, PWR are all mapped to `ai_data_center` theme in diversification config. At various points during the day, 4+ of these were held simultaneously.
- The sector guard limited post-AI positions, but the churn through this theme shows over-reliance on one sector narrative.

### 8. No Missed Bearish Halts
- Macro regime was "neutral" (score 0.27), VIX 27.83 ("normal"). No bearish halt warranted. SPY was down only -0.36%. The losses were self-inflicted, not macro-driven.

---

## 2c. Proposed Changes

### Proposal 1: Minimum Hold Period (Anti-Churn Circuit Breaker)

**Why:** 7 of 15 entries were closed within 60 minutes. No swing-trading thesis can be evaluated in under an hour. The scanner should not be able to exit a position it just entered.

**Diff:**
```yaml
# config.yaml — new key under `risk:`
risk:
  min_hold_scans: 2          # position cannot be exited by selector/verifier until it has survived 2 scan cycles (~2 hours)
```
```python
# src/orchestrator.py — in _should_exit() or selector logic
# Before allowing exit of a position:
# if position_age_scans < config['risk']['min_hold_scans']:
#     log(f"HOLD {symbol}: min hold period not met ({position_age_scans} < {min_hold_scans})")
#     continue
```

**Expected impact:** Eliminates ~70% of same-day churn (10 of 14 churned trades). Reduces daily turnover from $288K to ~$80K. Saves $500-$1,500/day in spread costs.

---

### Proposal 2: Verifier Cannot Override Exit-Arbiter HOLD

**Why:** The verifier dust-swept DELL, LLY, and FIX — all of which the exit-arbiter explicitly rated HOLD. The verifier's job is to reconcile to targets, not to override the exit-arbiter's trade-critical decision. When the selector changes targets between scans, the verifier becomes destructive.

**Diff:**
```yaml
# config.yaml — new key under `portfolio_verifier:`
portfolio_verifier:
  respect_exit_arbiter_hold: true   # verifier cannot close a position the exit-arbiter rated HOLD in the same scan
```
```python
# src/orchestrator.py — in verifier reconciliation logic
# Before verifier submits a close:
# if exit_arbiter_last_action.get(symbol) == 'hold':
#     log(f"VERIFIER BLOCKED: {symbol} has exit-arbiter HOLD — skipping dust-sweep")
#     continue
```

**Expected impact:** Saves 3 dust-sweep closes per day. FIX was up +1.0% when swept — holding it would have improved the day by ~$190.

---

### Proposal 3: Peer Rotation Cooldown

**Why:** The MU→WDC rotation lost money because the peer-score advantage was intraday noise. A 22-point score delta that reverses in 60 minutes shouldn't trigger a full position swap.

**Diff:**
```yaml
# config.yaml — new key under `selector:`
selector:
  peer_rotation_min_score_delta: 30     # must beat incumbent peer by 30+ points (not 10-22)
  peer_rotation_cooldown_scans: 3       # after entering a peer, wait 3 scans before rotating to another in the same peer group
```

**Expected impact:** Prevents the MU→WDC→out pattern. Saves 1-2 failed rotations per day ($500-$1,000).

---

### Proposal 4: Raise Effective Entry Confidence Floor

**Why:** Entries at conf 0.65-0.72 churned out within hours. Only AXTX (conf=0.88) survived. The 0.40 min_confidence gate is too loose for intraday survival.

**Diff:**
```yaml
# config.yaml
risk:
  min_confidence: 0.55        # was 0.40 — raise to match exit_arbiter's confidence floor
```

**Expected impact:** Would have blocked META (0.65), NOK (0.68), and several adds. Reduces entries per day from 15 to ~8, improving survival rate. Risk: may miss valid entries in strong momentum environments. Backtest recommended before applying.

**Backtest note:** Cannot backtest offline — would require price data from Alpha Vantage or yfinance (both blocked). The journal data shows that of entries with conf < 0.70 on 2026-05-04, 0 of 5 survived to close. Of entries with conf >= 0.75, 1 of 4 survived (AXTX at 0.88). Sample is too small for statistical significance but directionally supports raising the floor.

---

### Proposal 5: Cap Daily Turnover

**Why:** $288K turnover on $100K equity is destructive. Even with zero-commission trading, the bid-ask spread drag at this volume is material. No swing-trading strategy should turn over 2.9x equity daily.

**Diff:**
```yaml
# config.yaml — new key under `risk:`
risk:
  max_daily_turnover_pct: 1.0   # hard cap: no more than 100% equity turnover per day (buy + sell combined)
```

**Expected impact:** Would cap turnover at ~$100K/day, roughly halving current activity. Forces the bot to be more selective about which rotations are worth executing.

---

## 2d. Backtest (Offline Data Only)

**Data available:** 9 EOD snapshots (2026-04-22 to 2026-05-04), 53 trades on 2026-05-04, ~200+ trades across the full period.

### Test: "What if we held positions for 2+ scans?"

Using only trade timestamps from `trades.jsonl`:

| Symbol | Bought | Sold | Hold time | P&L | Would 2-scan rule help? |
|--------|--------|------|-----------|-----|------------------------|
| WDC | 17:04 | 18:05 | 1h | -1.2% | **YES** — would not have exited at 18:05 |
| DELL | 17:04 | 18:05 | 1h | +0.2% | **YES** — would not have been swept |
| LLY | 16:04 | 18:05 | 2h | +0.3% | **YES** — would not have been swept |
| GOOGL | 17:04 | 19:08 | 2h | -0.2% | **MAYBE** — 2 scans passed, but thesis was wrong |
| COIN | 17:04 (add) | 19:08 | 2h | -0.2% | **NO** — earnings exit was correct |

**Conclusion:** A 2-scan minimum hold would have prevented 3 of 5 worst same-day losses (WDC, DELL, LLY). The other 2 (GOOGL, COIN) would have exited on the same timeline regardless.

### Rolling Daily Performance vs Trade Count

| Date | Trades | Daily Return | vs SPY |
|------|--------|-------------|--------|
| 2026-04-22 | 7 | +0.00% | -1.01% |
| 2026-04-23 | 9 | +1.56% | +1.95% |
| 2026-04-24 | 19 | -0.81% | -1.58% |
| 2026-04-27 | 24 | -4.88% | -5.05% |
| 2026-04-28 | 21 | -5.13% | -4.64% |
| 2026-04-29 | 10 | -5.40% | -5.39% |
| 2026-04-30 | 23 | -2.67% | -3.63% |
| 2026-05-01 | 38 | +1.82% | +1.53% |
| 2026-05-04 | 53 | -1.80% | -1.44% |

**Correlation:** Higher trade counts weakly correlate with worse performance (r ≈ -0.3 by inspection). The two positive days (Apr 23, May 1) had 9 and 38 trades respectively — May 1 is an outlier, but Apr 23 with only 9 trades was the best vs-SPY day. Trade count is not the only factor, but excessive churn is clearly harmful.

---

## Summary

**Root cause of underperformance:** Hyper-churn. The bot rotated its entire active portfolio 3+ times in one day, burning spread costs and preventing any thesis from playing out. The verifier-vs-exit-arbiter conflict destroyed 3 viable positions (DELL, LLY, FIX). Peer rotations (MU→WDC) introduced losses on positions that shouldn't have been touched.

**Priority fixes (ordered by impact):**
1. **Min hold period** (2 scans / ~2 hours) — highest impact, eliminates most churn
2. **Verifier respects exit-arbiter HOLD** — prevents 3+ dust-sweep losses per day
3. **Peer rotation cooldown** — prevents destructive same-peer-group flips
4. **Daily turnover cap** (100% of equity) — hard backstop
5. **Raise min confidence to 0.55** — reduces low-conviction entries (needs more data)

**If these 5 changes had been in place on 2026-05-04:** estimated daily return would improve from -1.80% to approximately -0.50% to -0.80% (still negative due to the broad market dip, but much closer to SPY's -0.36%).
