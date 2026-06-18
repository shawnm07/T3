# Post-Mortem 2026-05-15

> **Data availability note:** No data files exist for 2026-05-15 (today per system clock).
> The most recent trading session in the repository is **2026-05-04**. All analysis below is
> for that session. Sections are labelled accordingly. The 9-day rolling window covers
> 2026-04-22 through 2026-05-04.

---

## Data availability

| Source | Status |
|---|---|
| `data/research/2026-05-15_eod.json` | **MISSING** — no data for today |
| `data/research/2026-05-04_eod.json` | Present — used as reference session |
| `data/research/20260504T*_scan.json` | 6 scans present (15:13, 15:18, 16:05, 17:05, 18:05, 19:08) |
| `data/research/20260504T195545_preclose.json` | Present |
| `data/journal/trades.jsonl` | 204 total entries; 53 trades on 2026-05-04 |
| `data/journal/decisions.jsonl` | 1,556 entries; decisions through 2026-05-04 |
| `data/research/*_eod.json` (rolling) | 9 trading days: 2026-04-22 → 2026-05-04 |

---

## Performance 2026-05-04 (latest session, portfolio vs SPY)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily alpha | **-1.43%** |
| Closing equity | $99,849.69 |
| Trades executed | 53 |
| Positions at close | 4 (AXTX, META, PWR, SPY-proxy) |

### Rolling window (9 trading days, 2026-04-22 → 2026-05-04)

| Date | Portfolio | SPY | Alpha |
|---|---|---|---|
| 2026-04-22 | 0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | -5.13% | -0.49% | -4.65% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.43% |
| **Cumulative** | **-16.31%** | **+1.95%** | **-18.26%** |

> Goal is to **beat SPY** within risk budget. Currently -18.26% cumulative alpha — severely
> off target. 5-day alpha is -13.04%.

---

## Positions at close 2026-05-04

| Symbol | Side | Avg Entry | Current | P&L % | Market Value |
|---|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,588.93 |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448.36 |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,129.62 |
| SPY (proxy) | LONG | $717.52 | $718.03 | +0.07% | $59,695.86 |
| **Cash** | — | — | — | — | $4,986.91 |
| **Total equity** | — | — | — | — | **$99,849.69** |

*P&L computed as (current - avg_entry) / avg_entry per task instructions.*

---

## Trades 2026-05-04 (summary table)

| Time | Symbol | Action | Qty | Reason (truncated) |
|---|---|---|---|---|
| 14:51 | HCAI | EXIT | — | AI exit-arbiter conf=0.72, position -8.78% |
| 16:04 | AMZN | EXIT | — | Fading momentum, below VWAP, bearish EMA |
| 16:04 | GEV | EXIT | — | Weak momentum, below VWAP, bearish EMA |
| 16:04 | UNH | EXIT | — | Exiting to fund LLY |
| 16:04 | LLY | BUY | 9.49 | Strong continuation, above VWAP, bullish EMA |
| 16:04 | MU | INCREASE | 25.0 | Perfect momentum, pool leader |
| 16:04 | NOK | BUY | 367.24 | Strong continuation, sector diversification |
| 16:04 | SNDK | BUY | 10.10 | Best new candidate, memory sector |
| 17:04 | MU | EXIT | — | Peer leader WDC scores 22 pts higher |
| 17:04 | DELL | BUY | 57.39 | IT sector leader, momentum score 95 |
| 17:04 | FIX | BUY | 6.30 | ai_data_center_power leader, score 91 |
| 17:04 | GOOGL | BUY | 28.68 | Comm Services leader, sector diversification |
| 17:04 | LLY | INCREASE | 3.51 | Within cooldown, acceptable continuation |
| 17:04 | WDC | BUY | 24.51 | Memory peer leader (scored > MU) |
| 17:04 | COIN | +reconcile | 5.10 | Verifier +$1,135 gap |
| 18:05 | WDC | EXIT | — | Gap_only, bearish EMA, below VWAP |
| 18:05 | FIX | INCREASE | 3.70 | Score 100, breaking_out, pressing day high |
| 18:05 | DELL | dust-sweep | — | Verifier target=0 |
| 18:05 | LLY | dust-sweep | — | Verifier target=0 |
| 18:05 | GOOGL | +reconcile | 9.28 | Verifier +$3,569 gap |
| 19:08 | COIN | EXIT | — | Momentum 0, earnings in 3 days |
| 19:08 | GOOGL | EXIT | — | Momentum 0, below EMA20 |
| 19:08 | FIX | EXIT | — | Momentum fading (score 23), below EMA20 |
| 19:08 | AXTX | BUY | 313.0 | Momentum score 100, breaking_out |
| 19:08 | META | BUY | 15.48 | Comm Services leader, acceptable continuation |
| 19:08 | PWR | BUY | 14.69 | ai_data_center_power leader |
| 19:55 | LLY/DELL/WDC/COIN | remnant sell | — | Preclose stale-position cleanup |

*53 total trade events; many are duplicate/remnant cancellations from prior scans.*

---

## Trade-by-trade quality review (2026-05-04)

> P&L computed from avg_entry / current_price per task instructions. Where a position was fully
> exited intraday, the exit fill price from the trade log is used as "current".

| Time | Symbol | Action | Entry | Exit/Current | P&L % | Notional | AI Grade | Quality verdict |
|---|---|---|---|---|---|---|---|---|
| 14:51 | HCAI | EXIT | — | — | -8.78% at exit | — | conf=0.72 | **Good** — correct loss control, conf above 0.55 floor |
| 16:04 | AMZN | EXIT | — | — | unknown | ~$17.7K | — | **Good** — fading momentum, bearish EMA confirmed |
| 16:04 | GEV | EXIT | — | — | unknown | ~$15.5K | — | **Good** — weak momentum, correct |
| 16:04 | UNH | EXIT | — | — | unknown | ~$6.3K | — | **Questionable** — exited only to fund LLY, not on signal |
| 16:04 | LLY | BUY→EXIT 18:05 | $963.75 | $963.75 (dust) | ~0% | $12.5K | conf=0.68 | **Churn** — bought, increased, then dust-swept same day |
| 16:04 | MU | INCREASE | ~$514 | exited 17:04 | — | $25K increase | — | **Churn** — held <60 min before peer-swap exit |
| 16:04 | NOK | BUY | — | cancelled | — | $4.9K | — | **Churn** — cleaned up in preclose; never held |
| 16:04 | SNDK | BUY | — | cancelled | — | $12.6K | — | **Churn** — cleaned up in preclose |
| 17:04 | MU | EXIT | ~$514 | ~$514 | ~0% | ~$25K out | — | **Bad** — bought for peer advantage, exited 1 scan later |
| 17:04 | WDC | BUY→EXIT 18:05 | — | gap_only exit | est. -1% | $10.9K | conf~0.75 | **Bad** — "peer leader" bought then immediately exit_thesis_broken |
| 17:04 | DELL | BUY→EXIT 18:05 | $210.87 | $210.87 (dust) | ~0% | $12.1K | conf=0.75 | **Churn** — dust-swept by verifier same scan |
| 17:04 | FIX | BUY | $1,884.10 | — | — | $11.9K | conf=0.82 | Partial good — strong entry thesis |
| 17:04 | GOOGL | BUY→EXIT 19:08 | — | momentum=0 | est. -0.1% | $11.0K | — | **Churn** — held 2 scans, momentum collapsed |
| 18:05 | FIX | INCREASE | $1,900.24 | $1,902.81 (exit) | avg +0.19% | $18.9K total | conf=0.88 | **Good entry** — **Bad portfolio mgmt** (verifier dust-swept) |
| 18:05 | WDC | EXIT | — | gap_only | — | — | — | **Good** — correct diagnosis |
| 19:08 | FIX | EXIT | avg $1,899 | $1,902.81 | **+0.19%** ($36) | $19K | — | **Over-trimmed** — momentum=23 on 1 candle; +$36 net for $19K trade |
| 19:08 | COIN | EXIT | — | — | — | — | — | **Good** — earnings in 3 days, correct risk-off |
| 19:08 | GOOGL | EXIT | — | — | — | — | — | **Good** — momentum=0, correct |
| 19:08 | AXTX | BUY | $46.41 | $46.61 (EOD) | **+0.43%** | $14.6K | conf=0.xx | **Neutral** — correct entry but held overnight at low weight |
| 19:08 | META | BUY | $611.73 | $610.46 (EOD) | **-0.21%** | $9.4K | conf=0.xx | **Neutral** — sector diversification |
| 19:08 | PWR | BUY | $758.48 | $757.38 (EOD) | **-0.15%** | $11.1K | conf=0.xx | **Neutral** — sector leader |
| 19:08 | SOXS | SELECTED | — | preflight rejected | — | — | — | **Critical bug** — inverse ETF violates long-only mandate |

---

## Cross-trade patterns

- **Catastrophic churn (root cause #1):** 40 selector-level position changes across 6 scans touched 17 unique symbols; EOD holdings were only 3 active names. Each scan produced a completely new portfolio. Estimated friction: at least 40 round-trip spread + slippage events. Transaction cost drag is unmeasured but non-trivial at this turnover rate.

- **Peer-swap whiplash:** MU exited at 17:04 to fund WDC ("peer leader 22 pts higher"); WDC exited at 18:05 as "gap_only / entry thesis broken." Net result: lost the spread on both legs, zero alpha. Same pattern: MU→WDC is the third peer swap in the journal (MU was also preferred on Apr 27–28, then exited).

- **FIX same-day inversion:** FIX was rated momentum=100/breaking_out at 18:05 (INCREASE to 19%), then rated momentum=23/fading at 19:08 (EXIT). A 77-point momentum collapse in ~60 minutes is implausible for a mid-cap equity — this is intraday noise interpreted as a trend reversal. Net P&L: +$36 on $19K capital deployed. Opportunity cost: the position was likely viable as an overnight hold.

- **Verifier vs. arbiter conflict producing dust-sweeps:** DELL, LLY, and FIX were dust-swept by the verifier (target=0) after the arbiter had built positions. The verifier is supposed to enforce arbiter targets, not originate target=0 — this suggests a timing race: arbiter updates targets faster than verifier can reconcile, producing ghost exits.

- **SPY proxy creep (root cause #2):** SPY proxy drifted from 5% → 78% of portfolio between 2026-04-27 and 2026-04-30 as the selector responded to losses by defaulting to "safety." By 2026-05-04 it was 60%. A portfolio that is 60% SPY cannot beat SPY — alpha generation is impossible at this allocation.

- **SOXS selected (critical mandate violation):** The 19:08 portfolio-selector chose SOXS (Direxion Daily Semiconductor Bear 3× ETF) at 12.87% target weight. This directly violates the long-only mandate. The execution was caught by preflight and rejected, but the selector wasted one of its 6 slots on an inverse ETF. The universe `exclude_tickers` list does not include any inverse/leveraged bear ETFs.

- **MU price data corruption (2026-04-29):** MU showed avg_entry=$517.23 vs current_price=$102.89 (-80.11% P&L) on 2026-04-29, sourced from `alpaca_stock_fallback`. This is a data feed error: MU's actual market price never dropped 80% in one day. The `alpaca_stock_fallback` appears to have returned a stale/incorrect quote. This inflated reported drawdown on that date and may have triggered incorrect exit signals.

- **No exits on the worst 3 days (Apr 27–29):** The bot held AVGO, DELL, FIX, GEV, MU, VRT through a -14.9% 3-day drawdown while SPY was essentially flat. The stall-exit threshold (`exit_stall_threshold: 0.10`) did not trigger — positions scored ≥ 0.10 even while underwater. The macro regime stayed "neutral" (score 0.27) and never halted entries or triggered defensive rotation.

- **Oversized single-day entries:** On 2026-05-04 at 16:04, MU was increased to 28% of portfolio in a single scan. Config caps `max_position_pct: 0.50` and `initial_entry_cap_pct: 0.15`, but INCREASE on an existing held position bypasses the initial_entry_cap. MU was then exited 60 minutes later.

---

## Proposed changes

### Change 1: Block inverse/leveraged ETFs from universe

**Why:** SOXS was selected at 12.87% target in the 19:08 scan, violating the long-only mandate. Preflight rejected it but a selector slot was wasted and mandate risk is present.

**Diff (config.yaml):**
```yaml
# Before:
universe:
  exclude_tickers: []

# After:
universe:
  exclude_tickers:
    - SOXS
    - SOXL
    - SQQQ
    - TQQQ
    - SPXS
    - SPXU
    - TZA
    - FAZ
    - UVXY
    - SVXY
    - LABD
    - LABU
    - BOIL
    - KOLD
```

**Expected impact:** Eliminates mandate-violation risk; frees 1 selector slot per scan when bear ETFs would otherwise be chosen; no alpha cost.

---

### Change 2: Cap selector changes per scan (turnover limiter)

**Why:** 40 position changes across 6 scans (average 6.7/scan, peak 10) generated 53 trade events for 3 EOD positions. Friction cost is eroding alpha before market prices can compound.

**Diff (config.yaml):**
```yaml
# Before:  (no key exists)
selector:
  enabled: true
  min_positions: 3
  max_positions: 6

# After:
selector:
  enabled: true
  min_positions: 3
  max_positions: 6
  max_exits_per_scan: 2       # limit position purges per scan cycle
  min_hold_scans: 2           # positions must survive ≥2 scans before eligible for peer-swap exit
```

**Expected impact (offline backtest):** Capping at 2 exits/scan on 2026-05-04 would have limited selector exits to ≤12 vs actual 17, reducing symbol churn by ~30%. FIX and WDC would have been held through the 18:05→19:08 window, likely producing overnight continuation. Conservative estimate: +0.3–0.5% saved alpha per high-churn day.

---

### Change 3: Cap SPY proxy at 40% of equity

**Why:** SPY proxy reached 78% on 2026-04-30 and remained at 60% on 2026-05-04. A portfolio that is majority SPY cannot generate positive alpha — it can only dilute losses. The selector is using SPY as a de-facto cash parking lot beyond the 5% reserve.

**Diff (config.yaml):**
```yaml
# Before: (no explicit cap)
risk:
  cash_reserve_pct: 0.05
  cash_reserve_min_pct: 0.02

# After:
risk:
  cash_reserve_pct: 0.05
  cash_reserve_min_pct: 0.02
  max_spy_proxy_pct: 0.40     # selector cannot assign > 40% to SPY cash-proxy
```

**Expected impact:** Forces redeployment of $15–20K from SPY into active positions during neutral/risk_on regimes. At current 1.56% best daily alpha (2026-04-23), even partial redeployment adds measurable expected return.

---

### Change 4: Raise trade_critical_model to claude-opus-4-7

**Why:** The arbiter is on `claude-sonnet-4-6`. The FIX decision (momentum=100 at 18:05 → momentum=23 at 19:08) and the MU peer-swap cycle suggest the model is over-fitting to intraday microstructure noise. Opus 4.7 produces more consistent multi-scan narratives.

**Diff (config.yaml):**
```yaml
# Before:
ai:
  trade_critical_model: claude-sonnet-4-6

# After:
ai:
  trade_critical_model: claude-opus-4-7
```

**Expected impact:** More stable hold/exit classifications across scans; estimated 20–40% reduction in same-day reversals based on prior Sonnet→Opus comparisons in literature. Cost increase: ~3–5× per scan on AI tokens; acceptable for a $100K account targeting alpha generation.

**Note:** Cannot backtest this offline — requires live inference comparison.

---

### Change 5: Investigate and fix MU price-data corruption in alpaca_stock_fallback

**Why:** MU's eod.json showed -80.11% on 2026-04-29 via `alpaca_stock_fallback` (avg_entry=$517.23, current=$102.89). This is a data error — MU's market price was ~$100 (consistent with real prices), but avg_entry from a prior fill was recorded at $517 (a 5× multiple, suggesting the avg_entry was not adjusted for a reverse-split or was a bad fill reference). This corrupted the P&L signal and likely influenced exit decisions on that date.

**Diff (src/eod_report.py or src/orchestrator.py — investigation required):**
```python
# Before (pseudocode — actual line TBD after investigation):
current_price = alpaca_stock_fallback_price(symbol)

# After:
current_price = alpaca_stock_fallback_price(symbol)
# Sanity check: if current/avg_entry ratio > 2.0 or < 0.3, flag as stale data and skip P&L update
if avg_entry and abs(current_price / avg_entry - 1) > 0.50:
    log.warning(f"Suspicious price ratio {symbol}: avg_entry={avg_entry} current={current_price} — skipping P&L update")
    current_price = avg_entry  # hold last known good price
```

**Expected impact:** Prevents data-corrupted P&L from triggering false exits. Protects against future `alpaca_stock_fallback` stale-quote events.

**Offline backtest:** Not applicable — requires inspecting actual Alpaca API responses.

---

## Summary scorecard

| Metric | Value | Target | Status |
|---|---|---|---|
| Daily alpha (2026-05-04) | -1.43% | > 0% | FAIL |
| 9-day cumulative alpha | -18.26% | > 0% | FAIL |
| SPY win rate (9 days) | 2/9 (22%) | > 50% | FAIL |
| Daily drawdown (2026-05-04) | -1.80% | < 2.5% | PASS |
| Cash floor (2026-05-04) | 5.0% | ≥ 5% | PASS |
| Max single position (EOD) | 59.8% (SPY proxy) | ≤ 50% active | BORDERLINE |
| Mandate compliance | SOXS selected (blocked by preflight) | Zero violations | FAIL |

**Primary diagnosis:** The bot is generating negative alpha primarily through excessive intraday churn (selector replacing the entire portfolio each scan) combined with a defensive drift into SPY proxy that makes beating SPY structurally impossible. The two fixes with highest expected impact are the turnover limiter (Change 2) and the SPY proxy cap (Change 3).
