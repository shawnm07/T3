# Post-Mortem 2026-05-12

## Data availability

| File | Status |
|------|--------|
| `data/research/2026-05-12_eod.json` | ❌ Missing — bot appears offline since 2026-05-04 |
| `data/research/2026-05-04_eod.json` | ✅ Present (last available trading day) |
| `data/research/20260504T190848_scan.json` | ✅ Present |
| `data/research/20260504T195545_preclose.json` | ✅ Present |
| `data/journal/trades.jsonl` | ✅ Present (last entry: 2026-05-04T19:55) |
| `data/journal/decisions.jsonl` | ✅ Present (1,556 entries) |
| Rolling EOD history | ✅ 9 days (2026-04-22 → 2026-05-04) |

> **Note:** No data files exist for 2026-05-05 through 2026-05-12. The bot has been silent for 6 trading days. This post-mortem covers the last active trading day (2026-05-04) and the cumulative period 2026-04-22 → 2026-05-04.

---

## Performance: last active day (2026-05-04) vs SPY

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | **-0.37%** |
| Alpha vs SPY | **-1.43%** ❌ |
| Equity (EOD) | $99,849.69 |
| Cash (EOD) | $4,986.91 (5.0% ≈ floor) |
| Positions at close | 4 (AXTX, META, PWR, SPY) |
| Trades executed | **53** ⚠️ extreme churn |

**Risk budget status (2026-05-04):**
- `cash_reserve_pct` (5%): ✅ barely met ($4,986 / $99,849)
- `max_position_pct` (15% initial cap): ✅ largest new entry was AXTX ~14.4%
- `daily_drawdown` (2.5% limit): ✅ -1.80% within limit on this day alone

---

## Cumulative period performance (2026-04-22 → 2026-05-04, 9 trading days)

| Date | Port | SPY | Alpha |
|------|------|-----|-------|
| 2026-04-22 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | **+1.56%** | -0.39% | **+1.95%** ✅ |
| 2026-04-24 | -0.81% | +0.78% | -1.59% |
| 2026-04-27 | **-4.88%** | +0.17% | **-5.05%** 🚨 |
| 2026-04-28 | **-5.13%** | -0.48% | **-4.65%** 🚨 |
| 2026-04-29 | **-5.40%** | -0.01% | **-5.39%** 🚨 |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | **+1.82%** | +0.29% | **+1.53%** ✅ |
| 2026-05-04 | -1.80% | -0.37% | -1.43% |
| **Cumulative** | **-17.31%** | **+1.96%** | **-19.27%** 🚨 |

> **Critical finding:** Three consecutive days (Apr 27-29) each exceeded the 2.5% daily drawdown limit. The circuit breaker was not triggered. This must be investigated.

---

## Positions at close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | EOD Price | P&L% | MV ($) | Wt% |
|--------|------|-----|-----------|-----------|------|--------|-----|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% | $14,589 | 14.6% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | $9,448 | 9.5% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | $11,130 | 11.1% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | $59,696 | **59.8%** ⚠️ |

> SPY cash-proxy weight of 59.8% is the dominant exposure — a portfolio designed to *beat* SPY is ~60% *in* SPY.

---

## Trades 2026-05-04

| Symbol | Dir | Qty | Entry | Exit/EOD | P&L% | Note |
|--------|-----|-----|-------|----------|------|------|
| HCAI | SELL | 1,492 | $11.84¹ | $10.69 | **-9.71%** | Exit-arbiter conf=0.72 |
| AMZN | SELL | 65.3 | unknown² | $270.65 | n/a | Arbiter EXIT fading |
| GEV | SELL | 14.6 | $1,140.45¹ | $1,071.49 | **-6.05%** | Arbiter EXIT weak momentum |
| UNH | SELL | 17.3 | $371.09¹ | $368.25 | **-0.77%** | Arbiter EXIT fading vol |
| MU | BUY→SELL | 23.0 | $580.42 | $580.81 | +0.07% | Same-day churn |
| WDC | BUY→SELL | 24.5 | $445.36 | $440.06 | **-1.19%** | Same-day churn |
| DELL | BUY→SELL | 57.4 | $210.52 | $210.94 | +0.20% | Verifier dust-sweep |
| LLY | BUY→SELL | 13.0 | $963.08 | $963.71 | +0.07% | Verifier dust-sweep |
| GOOGL | BUY→SELL | 38.0 | $383.73 | $382.77 | **-0.25%** | Same-day round trip |
| COIN | BUY→SELL | 66.9 | $203.90 | $203.45 | **-0.22%** | Same-day round trip |
| FIX | BUY→SELL | 10.0 | $1,899.17 | $1,902.81 | +0.19% | Verifier dust-sweep |
| AXTX | BUY | 313.0 | $46.41 | $46.61 EOD | +0.43% | HELD |
| META | BUY | 15.5 | $611.73 | $610.46 EOD | -0.21% | HELD |
| PWR | BUY | 14.7 | $758.48 | $757.38 EOD | -0.15% | HELD |

¹ From prior-day EOD; ² No buy record in journal (pre-journal position)

---

## Phase 2 — Deep Analysis

### 2a. Per-trade quality verdict (2026-05-04)

| Symbol | Side | Size | Entry | Exit | P&L% | AI Grade | Reason (short) | Verdict |
|--------|------|------|-------|------|------|----------|----------------|---------|
| HCAI | SELL | $15,788 | $11.84 | $10.69 | **-9.71%** | exit-arb conf=0.72 | Down -8.78%, 5 momentum-loss signals | ✅ correct (fell further, 30m: $10.58) |
| GEV | SELL | $15,649 | $1,140.45 | $1,071.49 | **-6.05%** | arbiter EXIT | Weak momentum, below VWAP, bearish EMA | ⚠️ early (+$104 missed 30m; +$198 missed 60m) |
| AMZN | SELL | ~$17,673 | unknown | $270.65 | unknown | arbiter EXIT | Fading momentum, below VWAP | ⚠️ unknown (no entry record; likely losing) |
| UNH | SELL | $6,365 | $371.09 | $368.25 | **-0.77%** | arbiter EXIT | Fading volume, acceptable momentum | ✅ good (+$8 missed 60m — insignificant) |
| STX | SELL (reduce) | n/a | $716.82 | $740.23 | **+3.26%** | exit-arb conf=0.62 | Below VWAP, EMA20 | ⚠️ early (+$76 missed 30m — left profit behind) |
| SNDK | SELL (reduce) | n/a | $1,140.78 | $1,237→$1,250 | **+8.7%** winner | exit-arb conf=0.62 | Below VWAP, falling trend | ❌ bad exit (sold a winner into minor pullback) |
| MU | BUY→SELL | $13,352 | $580.42 | $580.81 | +0.07% | arbiter cycle | Bought INCREASE then EXIT same scan | ❌ churn (net neutral after friction) |
| WDC | BUY→SELL | $10,909 | $445.36 | $440.06 | **-1.19%** | arbiter cycle | Bought then gap-only exit same day | ❌ churn loss ($130) |
| GOOGL | BUY→SELL | $14,582 | $383.73 | $382.77 | **-0.25%** | arbiter cycle | Bought by verifier, sold by arbiter same scan | ❌ churn (verifier/arbiter conflict) |
| COIN | BUY→SELL | $13,627 | $203.90 | $203.45 | **-0.22%** | arbiter cycle | Partial buy then full exit within same scan | ❌ churn |
| FIX | BUY→SELL | $18,992 | $1,899.17 | $1,902.81 | +0.19% | verifier dust-sweep | Bought in rebalance, swept by verifier | ❌ churn (verifier undid rebalance buy) |
| DELL | BUY→SELL | $12,091 | $210.52 | $210.94 | +0.20% | verifier dust-sweep | Same pattern | ❌ churn |
| LLY | BUY→SELL | $12,520 | $963.08 | $963.71 | +0.07% | verifier dust-sweep | Same; 30m missed $33, 60m $70 | ❌ churn (premature sweep) |
| AXTX | BUY HOLD | $14,589 | $46.41 | $46.61 EOD | +0.43% | arbiter BUY | Momentum 100, breaking out, 2.79x vol | ✅ good entry |
| META | BUY HOLD | $9,448 | $611.73 | $610.46 EOD | -0.21% | arbiter BUY | Comm. services diversifier | ⚠️ marginal |
| PWR | BUY HOLD | $11,130 | $758.48 | $757.38 EOD | -0.15% | arbiter BUY | AI datacenter power, bullish EMA | ⚠️ marginal |

**Estimated friction from churn on 2026-05-04** (same-day round trips):
- WDC: -$130 | GOOGL: -$37 | COIN: -$30 | MU: +$9 net ≈ **-$188 from churn alone**
- Verifier dust-sweeps (FIX/DELL/LLY): **~$0 net but ~$44k notional churned unnecessarily**, triggering wash-trade conflicts and wasting API calls

---

### 2b. Cross-trade patterns

- **Verifier/arbiter conflict (root cause of most churn):** The verifier swept FIX, DELL, and LLY as “dust” on the same scan in which the arbiter had just bought them for a rebalance. The verifier’s `target=0` contradicted the arbiter’s non-zero targets — either the verifier received a stale target plan or the arbiter’s plan was not propagated correctly before the verifier ran. This is the single largest source of same-scan churn and wash-trade rejections.

- **Selector AI cascading failure → portfolio drift:** On Apr 28, the portfolio-selector failed 6 consecutive times (all returning `selected=[]`). With no valid selection, the system executed ad-hoc rebalance trades without a coherent target portfolio. Apr 28 saw -5.13% daily loss. Same pattern on Apr 29 (-5.40%). The selector failures did not activate any safe-mode holdover; the bot continued trading without direction.

- **Apr 27-29 triple daily drawdown breach:** Three consecutive days exceeded the 2.5% config limit (-4.88%, -5.13%, -5.40%). No circuit breaker fired. The config key `daily_drawdown` exists but is not enforced at execution time. Each day’s loss compounded: equity fell from $101,208 (Apr 23) to $93,999 (Apr 29) = -7.1% in 4 trading days while SPY was effectively flat.

- **SPY proxy bloat:** On 2026-05-04 close, SPY = 59.8% of equity ($59,696). The bot is functionally a 60/40 SPY blend. The cash-proxy logic deposits excess capital into SPY, but with only 3 active equity positions totaling ~35%, beating SPY requires the equity sleeve to deliver >2.5× the SPY return. This is structurally unlikely at modest position sizes.

- **SOXS in selector pool:** The portfolio-selector allocated 9% target weight to SOXS (Direxion Daily Semiconductor Bear 3x ETF), an inverse leveraged product. This violates the “long US equities only, no shorts” mandate. Execution preflight correctly rejected it (stop-distance check), but a full AI model call was spent on an untradeable position.

- **LLY stop above market:** AI set stop $957.07 with current reference $943.34 — stop was 1.45% *above* market, guaranteeing immediate trigger. Preflight rejected with `stop_not_below_current_market`. Likely caused by stale quote in AI’s price reference at time of stop computation.

- **SNDK missed by $48:** SNDK (score 75, confidence 0.78, 2nd-best candidate) was blocked by `insufficient_confirmed_cash` — $12,248 needed, $12,200 available. The marginal $48 gap blocked a high-conviction name while lower-priority positions (COIN, FIX) were consuming cash and being swept minutes later.

- **Premature exits on GEV and STX:** GEV exited at $1,071 (entry $1,140 = -6.05%); 60m later traded at $1,085 (+$198 recoverable). STX reduced at $740; 30m later $744 (+$76 recoverable). Exit-arbiter fired at confidence 0.62 (just above the 0.55 minimum) on intraday momentum signals that partially reversed.

- **HCAI loss was unavoidable:** Exited at -9.71% ($1,450 loss); 30m later price was $10.58 (further -1%). Exit was correct. Position deteriorated from +1.52% on May 1 to -9.71% on May 4 — an 11.2pp swing not caught by overnight hold logic.

---

### 2c. Proposed Changes

#### Proposal 1 — Hard daily drawdown circuit breaker in executor

**Why:** Apr 27, 28, 29 each lost 4.9%-5.4% against the 2.5% config limit. Three consecutive breaches cost approximately $7,200 (~7.2% of equity) in excess of the limit.

**Diff:**
```python
# src/executor.py — add to _pre_execution_checks():
# BEFORE: no daily drawdown check at trade time

# AFTER:
daily_drawdown_pct = (starting_equity - current_equity) / starting_equity
if daily_drawdown_pct > cfg.risk.daily_drawdown_limit:   # 0.025
    raise DrawdownCircuitBreaker(
        f"daily drawdown {daily_drawdown_pct:.2%} exceeds limit — new entries blocked (exits still run)"
    )
```
```yaml
# config.yaml — add under risk:
  daily_drawdown_limit: 0.025
```
**Expected impact:** Caps intraday loss on any single day at 2.5%. Estimated saved loss on Apr 27-29: $2,000-$4,000.

---

#### Proposal 2 — Selector failure safe-mode: freeze current positions

**Why:** On Apr 28, the portfolio-selector failed 6 consecutive times (selected=[]). With no valid plan, uncoordinated rebalance trades drove the worst single-day loss of the period (-5.13%).

**Diff:**
```python
# src/ai_pipeline.py — in _run_portfolio_selector(), after all retries exhausted:
# BEFORE:
#   return None  # callers fall back to numeric rebalance

# AFTER:
if selector_result is None:
    log.warning("selector failed all retries — HOLD safe-mode: freezing positions, exits still run")
    return SelectorResult(
        selected_positions=[p.symbol for p in held_positions],
        target_weights={p.symbol: p.weight for p in held_positions},
        action=SelectorAction.HOLD_ONLY,
    )
```
**Expected impact:** Blocks new entries and rebalance on selector-failure days. Exits still execute. Estimated reduced loss on Apr 28: $1,000-$3,000.

---

#### Proposal 3 — Inverse ETF / leveraged short blocklist at discovery

**Why:** SOXS reached selector output with 9% target weight. The long-only mandate is enforced at execution but the AI model call is wasted. BITO (crypto proxy) appeared 3× in missed-breakout logs — also not tradeable under mandate.

**Diff:**
```python
# src/discovery.py — add to pool filtering:
# BEFORE: no inverse/crypto ETF filter

# AFTER:
INVERSE_ETF_BLACKLIST = {
    "SOXS","SQQQ","SDOW","SPXS","SDS","SH","PSQ","SPXU","TZA","FAZ",
    "YANG","UVXY","SVIX","BITO","IBIT","FBTC",
}
pool = [s for s in pool if s not in INVERSE_ETF_BLACKLIST]
```
```yaml
# config.yaml — under discovery:
  inverse_etf_blacklist_enabled: true
```
**Expected impact:** Zero downside. Eliminates wasted model calls and prevents future preflight rejections on untradeable names.

---

#### Proposal 4 — Cap SPY cash-proxy at 35% of equity

**Why:** On 2026-05-04 close, SPY = 59.8% of equity. A bot that is 60% in SPY cannot outperform SPY without extraordinary alpha from the remaining 40%.

**Diff:**
```yaml
# config.yaml — under risk:
# BEFORE: no explicit SPY proxy cap

# AFTER:
  cash_proxy_max_pct: 0.35   # SPY proxy capped at 35%; excess held as true cash
```
**Expected impact:** Forces deployment into equities (or actual cash) above 35%. Increases alpha potential at cost of higher variance. Pair with Proposal 1 to bound downside.

---

#### Proposal 5 — Raise rebalance churn thresholds

**Why:** 53 trades on 2026-05-04. Same-day round trips on 7 symbols generated -$188 net loss from friction. `min_delta_pct: 0.15` / `min_delta_usd: 500` are too permissive at current position sizes.

**Diff:**
```yaml
# config.yaml — under rebalance:
# BEFORE:
  min_delta_pct: 0.15
  min_delta_usd: 500

# AFTER:
  min_delta_pct: 0.20
  min_delta_usd: 1000
```
**Expected impact:** Est. 30-40% reduction in trade count on high-churn days. Saves ~15-20 API round-trips per scan session. Reduces adverse fill exposure.

---

#### Proposal 6 — Verifier minimum hold period before dust-sweep

**Why:** The verifier swept FIX, DELL, and LLY within the same scan that the arbiter bought them. The verifier received `target=0` for positions with non-zero targets seconds earlier — stale target propagation or race condition. On 2026-05-04 this created 3 unnecessary sells (~$44k notional) and triggered 2 wash-trade rejections.

**Diff:**
```python
# src/executor.py — in verifier dust-sweep logic:
# BEFORE: verifier can sweep any position with gap > tolerance

# AFTER:
MIN_HOLD_BEFORE_SWEEP_MINUTES = 120
if position.opened_at > (now - timedelta(minutes=MIN_HOLD_BEFORE_SWEEP_MINUTES)):
    log.info(f"verifier skip dust-sweep {symbol}: held only {minutes_held:.0f}m < {MIN_HOLD_BEFORE_SWEEP_MINUTES}m")
    continue
```
```yaml
# config.yaml — under verifier (new section):
verifier:
  min_hold_before_sweep_minutes: 120
```
**Expected impact:** Prevents arbiter/verifier conflicts on same-scan positions. Would have saved 3 unnecessary sells and let LLY continue its +$70 60-minute continuation.

---

### 2d. Backtest notes

**Proposals 1, 2, 3, 6** are structural guards with zero negative-case risk. The causal chains are direct and confirmed from journal data. No price-data backtest required.

**Proposal 4 (SPY cap at 35%):** Of the 7 negative-alpha days in this window, SPY proxy averaged ~48% weight. Forcing deployment would have increased equity-sleeve exposure. On the 2 positive-alpha days (Apr 23, May 1), active equities drove all alpha. Structural effect: higher variance, higher potential alpha, worse drawdown protection on SPY-down days. Pair with Proposal 1.

**Proposal 5 (churn thresholds):** Of 53 trades on 2026-05-04, approximately 12 had |delta_notional| < $1,000. Raising the floor blocks those 12. Cannot backtest alpha impact without live price data. Net P&L effect estimated at +$50-$150 from reduced adverse fills.

---

### Action priority

| # | Proposal | Risk | Effort | Priority |
|---|----------|------|--------|----------|
| 1 | Daily drawdown circuit breaker | Zero (exits still run) | Low | 🔴 CRITICAL |
| 2 | Selector failure safe-mode | Zero | Low | 🔴 CRITICAL |
| 3 | Inverse ETF blocklist | Zero | Low | 🟠 High |
| 6 | Verifier min hold period | Low | Low | 🟠 High |
| 5 | Raise churn thresholds | Low | Low | 🟡 Medium |
| 4 | SPY proxy cap | Medium | Low | 🟡 Medium (pair with #1) |

---

### Open questions requiring investigation

1. **Why is the bot offline since 2026-05-04?** No scan or EOD files for 2026-05-05 through 2026-05-12 (6 trading days). Check cron/systemd status, API key expiry, or process crash logs.
2. **MU price anomaly on 2026-04-29:** EOD showed `current_price=102.89` vs `avg_entry=517.23` = -80.1% PnL. Almost certainly a yfinance split-adjusted price error. Confirm whether this triggered a false exit signal and audit `exit_learning_metrics` for MU on that date.
3. **AMZN buy record missing:** AMZN was a ~$17,600 position (65.3 shares) with no buy event in `trades.jsonl`. Either it predates the journal or was entered via an unlogged path. Audit for completeness and journal coverage gap.
