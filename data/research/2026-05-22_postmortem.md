# Post-Mortem 2026-05-22

## Data availability

| Source | Status |
|--------|---------|
| `data/research/2026-05-22_eod.json` | **MISSING** — no scan ran today (market closed / scan not triggered) |
| `data/research/*2026052*_scan.json` | **MISSING** — no scans for today |
| `data/journal/decisions.jsonl` (today) | 0 entries for 2026-05-22 |
| `data/journal/trades.jsonl` (today) | 0 entries for 2026-05-22 |

**Analysis uses the most recent available session: 2026-05-04 (Monday).** That session is the last traded day in the journal and is the closest proxy for a current post-mortem. Rolling benchmarks span all 9 available EOD files (2026-04-22 → 2026-05-04).

---

## Performance today (2026-05-04 — last traded session)

| Metric | Value |
|--------|-----------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Alpha (day) | **-1.44%** |
| Closing equity | $99,849.69 |
| Cash at close | $4,986.91 (5.0%) |
| Period vs SPY (since inception) | **-10.71%** |

### Rolling benchmark

| Window | Portfolio | SPY | Alpha |
|--------|-----------|-----|-------|
| 5-day | -12.66% | +0.38% | **-13.04%** |
| 9-day (full history) | -16.31% | +1.95% | **-18.26%** |

Daily alpha series:

| Date | Port | SPY | Alpha |
|------|------|-----|-------|
| 2026-04-22 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.58% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | -5.13% | -0.49% | -4.64% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.44% |

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current | PnL% | Market Value | Weight |
|--------|------|-----------|---------|------|-------------|--------|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,589 | 14.6% |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448 | 9.5% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,130 | 11.1% |
| **SPY** | **LONG** | **$717.52** | **$718.03** | **+0.07%** | **$59,696** | **59.8%** |

**SPY cash-proxy = 59.8% of portfolio.** The portfolio is effectively tracking SPY by design.

---

## Trades today (2026-05-04)

53 total events: **15 buys, 11 sells, 24 exit-learning metrics, 3 wash-trade recoveries.**

### Buys (15 orders)

| Time | Symbol | Qty | Stop | Target% | Source |
|------|--------|-----|------|---------|--------|
| 16:04 | LLY | 9.49 | $951.69 | 9.1% | arbiter |
| 16:04 | MU | 25.00 | $577.65 | 28.0% | arbiter |
| 16:04 | NOK | 367.24 | $13.24 | 4.9% | arbiter |
| 16:04 | SNDK | 10.10 | $1,237.62 | 12.6% | arbiter |
| 17:04 | DELL | 57.39 | $207.81 | 12.1% | arbiter |
| 17:04 | FIX | 6.30 | $1,865.26 | 11.9% | arbiter |
| 17:04 | GOOGL | 28.68 | $378.99 | 11.0% | arbiter |
| 17:04 | LLY | 3.51 | $952.61 | 12.5% | arbiter |
| 17:04 | WDC | 24.51 | $437.86 | 10.9% | arbiter |
| 17:04 | COIN | 5.10 | $202.77 | — | verifier |
| 18:05 | FIX | 3.70 | $1,881.24 | 19.0% | arbiter |
| 18:05 | GOOGL | 9.28 | $380.10 | — | verifier |
| 19:08 | AXTX | 313.00 | $45.34 | 14.4% | arbiter |
| 19:08 | META | 15.48 | $606.07 | 9.5% | arbiter |
| 19:08 | PWR | 14.69 | $748.54 | 11.1% | arbiter |

### Sells (11 positions)

| Time | Symbol | Qty | Filled @ | Source | Reason (truncated) |
|------|--------|-----|----------|--------|---------------------|
| 14:51 | HCAI | 1,492 | $10.69 | exit-arbiter conf=0.72 | Down -8.78%, momentum lost |
| 16:04 | AMZN | 65.3 | $270.65 | arbiter | Fading momentum, below VWAP |
| 16:04 | GEV | 14.6 | $1,071.49 | arbiter | Weak momentum, below VWAP |
| 16:04 | UNH | 17.3 | $368.25 | arbiter | Acceptable but fading — funding LLY |
| 17:04 | MU | 23.0 | $580.81 | arbiter | Weak/flat momentum, peer WDC scores higher |
| 18:05 | WDC | 24.5 | $440.06 | arbiter | Gap-only, bearish EMA, below VWAP |
| 18:05 | DELL | 57.4 | $210.94 | verifier | Dust-sweep target=0 |
| 18:05 | LLY | 13.0 | $963.71 | verifier | Dust-sweep target=0 |
| 19:08 | COIN | 66.9 | $203.45 | arbiter | Momentum 0, earnings in 3 days |
| 19:08 | GOOGL | 38.0 | $382.77 | arbiter | Momentum 0, fading, below EMA20 |
| 19:08 | FIX | 10.0 | $1,902.81 | verifier | Dust-sweep target=0 |

---

## Per-trade quality (2026-05-04)

> PnL computed as `(exit_price - avg_entry) / avg_entry`. Held-from-prior-day entries use prev EOD avg_entry; same-day entries use fill reference from protective_stop block.

| Symbol | Side | Avg Entry | Exit | PnL% | 60m Dir | $Missed@60m | AI Grade | Quality |
|--------|------|-----------|------|------|---------|-------------|----------|---------|
| HCAI | LONG | $11.84 | $10.69 | -9.71% | FELL | -$164 | exit conf=0.72 | **correct** — stop finally hit; exit arbiter right |
| AMZN | LONG | intraday | $270.65 | N/A | ROSE | +$1 | exit conf=0.62 | acceptable — negligible miss |
| GEV | LONG | intraday | $1,071.49 | N/A | ROSE | **+$198** | exit conf=0.62 | **PREMATURE** — rose $14 in 60 min |
| UNH | LONG | intraday | $368.25 | N/A | ROSE | +$8 | exit conf=0.62 | acceptable — funding LLY (marginally premature) |
| MU | LONG | $580.42 | $580.81 | +0.07% | FELL | -$166 | exit conf=0.58 | **correct** — peer leader WDC was right to displace |
| WDC | LONG | $445.36 | $440.06 | -1.19% | ROSE | **+$100** | exit conf=0.62 | **PREMATURE** — bot rotated MU→WDC→exit in 2 hrs |
| DELL | LONG | $210.52 | $210.94 | +0.20% | ROSE | +$17 | verifier dust-sweep | **churn** — fresh_exit_guard bypassed, sold by verifier |
| LLY | LONG | $963.38 | $963.71 | +0.03% | ROSE | **+$70** | verifier dust-sweep | **PREMATURE** — bought 17:04, sold 18:05 via verifier |
| COIN | LONG | $203.90 | $203.45 | -0.22% | FELL | -$1 | exit conf=0.58 | **same-day flip** — earnings risk correct call |
| GOOGL | LONG | $383.51 | $382.77 | -0.19% | N/A | $0 | exit conf=0.58 | **same-day flip** — wash trade recovery; 3hr hold |
| FIX | LONG | $1,896.50 | $1,902.81 | +0.33% | N/A | $0 | verifier dust-sweep | **churn** — fresh_exit_guard bypassed; RSI=71.7 at entry |

**Summary**: 3 correct, 3 premature, 3 same-day flips, 2 acceptable.

---

## Cross-trade patterns

- **Fresh-exit-guard bypassed 3×**: DELL, LLY, and FIX all logged `fresh_exit_guard_skipped` — the selector exited them the same hour they were bought. The cooldown exists in code but is overridable when AI confidence is high. These 3 sells generated ~$43K in unnecessary turnover.

- **Peer-group rotation churn (MU → WDC → exit)**: Scan 3 (16:05) selected MU at 28% weight. Scan 4 (17:04) displaced MU with WDC ("WDC scores 22 points higher"). Scan 5 (18:05) exited WDC ("gap-only, bearish EMA"). Both MU and WDC ended up sold, with neither held at EOD. The peer-displacement trigger has no minimum gap requirement, allowing single-scan opinion swings to drive a full rotation.

- **SPY cash-proxy overweight at close**: EOD weight = **59.8% SPY**. When active picks are churned out, the selector parks capital in SPY. A 60% SPY allocation means the portfolio's active alpha budget is ~40%; beating SPY by even 2% in the active sleeve only yields 0.8% portfolio outperformance. The cash_proxy_max_pct is effectively uncapped.

- **Verifier dust-sweeps overriding live positions**: 3 positions (DELL, LLY, FIX) were bought by the arbiter during scan 4/5 and sold by the verifier as "dust-sweep target=0" in the same or next scan. The verifier is reconciling against an Opus target that was already superseded by the next scan's selector — but it swept real positions.

- **288% same-day turnover**: Total buy notional $137K + sell notional $152K = $289K on a $100K account. Even with zero commissions, bid-ask spread on 26 transactions degrades performance. High turnover correlates with underperformance: only 2/9 sessions beat SPY.

- **Overbought RSI entries**: Preclose scan candidates included FIX (RSI=71.7), AMD (RSI=70.2), TXN (RSI=77.4), FLEX (RSI=72.7). FIX was bought at RSI=71.7 and sold same day. No RSI ceiling on new entries.

- **April drawdown held without exit**: The bot held HCAI from entry ($11.84) through a -9.71% decline over multiple days before the exit arbiter finally acted. During Apr 27–29 the portfolio fell -5.0%/day while SPY was flat. Exit arbiter min_confidence=0.55 was not met until May 4, meaning no exits triggered during the 3-day slide.

---

## Proposed changes

### 1. Hard-enforce fresh-exit cooldown (no bypass on same-scan cycle)

**Why**: DELL, LLY, FIX were all bought and sold within 1–2 hours via a `fresh_exit_guard_skipped` path. These 3 dust-sweeps generated $43K unnecessary turnover with $0–$87 net PnL and +$87 missed upside.

**Config diff**:
```yaml
# config.yaml — under risk:
fresh_exit_cooldown_scans: 3   # was: effectively 0 (bypassed when ai_confidence > threshold)
```
**Src change needed** (proposal only — do not apply to any file):
In `src/orchestrator.py` or the executor, the `fresh_exit_guard_skipped` branch should check `cooldown_scans` instead of allowing AI-confidence override. The verifier should also be blocked from sweeping positions entered in the current scan cycle.

**Expected impact**: Eliminates 3 same-session sweeps per high-churn day. Reduces daily turnover by ~15–25%. Based on May 4 data: $43K less unnecessary selling.

---

### 2. Cap SPY cash-proxy at 30% of portfolio

**Why**: EOD May 4 had 59.8% in SPY. A portfolio that's 60% index-tracking and 40% active picks cannot generate meaningful alpha. The mission is to beat SPY, not to be SPY.

**Config diff**:
```yaml
# config.yaml — under risk: (new key)
cash_proxy_max_pct: 0.30   # was: uncapped (selector.spy_target_pct can go to 1.0)
```
**Expected impact**: Forces the bot to either hold more active picks or leave idle cash (which at least doesn't introduce SPY correlation). If active pick quality is poor, this will increase volatility — that's acceptable; the bot must take differentiated risk to generate alpha.

**Backtest note**: Cannot backtest offline (no hypothetical fill prices). Directional expectation: on days the bot underperforms SPY (-1.44% alpha on May 4), the SPY overweight directly caused the underperformance by locking capital in the benchmark itself.

---

### 3. Require minimum peer-displacement gap of 30 points before rotating

**Why**: Scan 3 displaced MU with WDC at a 22-point gap ("WDC scores 22 points higher"). WDC was then exited the next scan. A 22-point gap represents noise-level momentum differences that invert within 60 minutes.

**Config diff**:
```yaml
# config.yaml — under selector: (new key)
peer_displacement_min_gap: 30   # was: 0 (any positive gap triggers rotation)
```
**Expected impact**: Blocks MU→WDC type rotations when the gap is marginal. Prevents the "rotate peer, then exit peer" pattern (2× transaction costs with 0 net gain). Estimated reduction: ~2–4 fewer peer-group churns per active day.

---

### 4. Add RSI ceiling on new entries (RSI ≤ 68)

**Why**: FIX entered at RSI=71.7 and was sold same day. Preclose scan shows AMD (70.2), TXN (77.4), FLEX (72.7) as candidates. Entering overbought names increases reversal risk and contributes to same-day exits.

**Config diff**:
```yaml
# config.yaml — under universe: (new key)
entry_max_rsi: 68   # was: uncapped
```
**Expected impact**: Would have blocked FIX entry on May 4. Longer-term, reduces the frequency of "enter extended, exit next scan" patterns. Note: this only applies to NEW entries — existing holdings with RSI>68 are unaffected.

**Offline backtest**: Of May 4 exits, only FIX (RSI=71.7) confirmed as same-day churn from overbought entry. Insufficient data for broader backtest — 2 days of trading history.

---

### 5. Lower exit arbiter confidence floor for deepening losses (dynamic threshold)

**Why**: HCAI declined -9.71% over multiple days before exiting. The static `exit_arbiter.min_confidence: 0.55` held even as the position moved further against thesis. A drawdown-conditional floor would allow exits at lower AI confidence when unrealized loss exceeds a threshold.

**Config diff**:
```yaml
# config.yaml — under exit_arbiter: (new key)
loss_triggered_min_confidence: 0.45   # applies when pnl_pct < -0.05 (position down >5%)
# was: min_confidence: 0.55 (static, regardless of loss magnitude)
```
**Expected impact**: Would have triggered HCAI exit earlier (exit arbiter confidence was 0.62 on the final exit — it met the bar; the question is whether a prior scan at 0.50+ should have been actionable). Prevents multi-day silent drawdowns on loss-making positions.

**Offline backtest**: HCAI: entry $11.84, 5% threshold = $11.25. If the bot had a 0.45 floor when HCAI crossed -5%, exit would have been ~$11.25 vs actual $10.69 = saved ~$0.56/share × 1,492 shares ≈ **$835 better exit** on a single position.

---

## Risk budget compliance check (2026-05-04)

| Constraint | Limit | Actual | Status |
|------------|-------|--------|--------|
| max_position_pct | 50% | SPY=59.8% (cash-proxy technically exempt, but capital is locked) | ⚠️ |
| cash_reserve_pct | 5% | $4,986 = 5.0% | ✅ |
| daily drawdown | <2.5% | -1.80% | ✅ |
| max_positions | 6 | Peak 7 (18:05 scan had 7 active) | ⚠️ minor |
| initial_entry_cap_pct | 15% | MU targeted at 28.0% in scan 3 | ⚠️ exceeded |

**MU was targeted at 28% (nearly 2× the initial_entry_cap_pct=0.15).** The config allows arbiter to grow existing positions to max_position_pct=0.50 but new entries should be capped at 15%. If MU was a net-new position that scan, the 28% target may violate `initial_entry_cap_pct`.
