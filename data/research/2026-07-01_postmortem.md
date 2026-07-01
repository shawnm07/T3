# Post-Mortem 2026-07-01

## Data Availability

Scheduled run date: **2026-07-01**. No eod.json or scan files exist for today — the bot appears to have been dormant or disconnected since **2026-05-04** (most recent snapshot). This postmortem covers **2026-05-04**, the last active trading day, plus rolling performance since 2026-04-22.

Sources used:
- `data/research/2026-05-04_eod.json` — EOD snapshot (positions, equity, returns)
- `data/research/20260504T*_scan.json` — 6 intraday scans
- `data/journal/trades.jsonl` — all buy/sell events (chronological)
- `data/journal/decisions.jsonl` — 105 decision entries for 2026-05-04
- `data/research/2026-04-22_eod.json` … `2026-05-04_eod.json` — 9-day rolling history

---

## Performance Today (2026-05-04)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily alpha | **-1.44%** |
| Closing equity | $99,849.69 |
| Cash | $4,986.91 |
| Positions at close | 4 (AXTX, META, PWR, SPY) |
| Trades executed | **53** |

### Rolling Benchmark

| Date | Equity | Port% | SPY% | Alpha |
|---|---|---|---|---|
| 2026-04-22 | $99,627 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.58% |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.64% |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | -1.44% |

**9-day cumulative:** Portfolio -17.31% vs SPY +1.95% → **alpha -19.26%**
**5-day cumulative:** Portfolio -13.18% vs SPY +0.39% → **alpha -13.57%**

> Goal is to beat SPY. The bot is underperforming by ~19% over 9 trading days. This is critical.

---

## Positions at Close (2026-05-04 EOD)

| Symbol | Side | Qty | Avg Entry | Current | PnL% | Market Value |
|---|---|---|---|---|---|---|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% | $14,589 |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | $9,448 |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | $11,130 |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | $59,696 |

> **SPY cash proxy = 59.7% of portfolio.** All three active equity positions are tiny stubs with negligible P&L. Nearly all capital is parked in SPY, limiting any alpha generation.

---

## Trades Today (2026-05-04, Chronological)

| Time (UTC) | Side | Symbol | Qty | Price | Reason (truncated) |
|---|---|---|---|---|---|
| 14:51 | SELL | HCAI | 1492 | $10.69 | exit-arbiter conf=0.72: down -8.78% intraday momentum |
| 16:04 | SELL | AMZN | 65.3 | $270.65 | fading momentum, below VWAP, bearish EMA |
| 16:04 | SELL | GEV | 14.57 | $1,071.49 | weak momentum, below VWAP, bearish EMA |
| 16:04 | SELL | UNH | 17.27 | $368.25 | fading volume, LLY is stronger |
| 16:04 | BUY | LLY | 9.49 | $963.38 | strong continuation, above VWAP |
| 16:04 | BUY | MU | 25.0 | $580.42 | INCREASE → 28% — pool leader, perfect momentum |
| 16:04 | BUY | NOK | 367.2 | $13.33 | continuation, above VWAP |
| 16:04 | BUY | SNDK | 10.1 | $1,246.97 | strong continuation (prev SNDK position sold earlier at $1,237) |
| 17:04 | SELL | MU | 23.0 | $580.81 | weak_or_flat momentum, bearish EMA 1 hr after buying |
| 17:04 | BUY | DELL | 57.4 | $210.52 | IT sector leader, momentum 95 |
| 17:04 | BUY | FIX | 6.3 | $1,896.50 | ai_data_center_power leader |
| 17:04 | BUY | GOOGL | 28.7 | $383.51 | Comm Services leader |
| 17:04 | BUY | LLY | 3.51 | $962.27 | INCREASE — within cooldown |
| 17:04 | BUY | WDC | 24.51 | $445.36 | memory peer, scored > MU |
| 17:04 | BUY | COIN | 5.1 | $203.90 | verifier gap-fill |
| 18:05 | SELL | WDC | 24.51 | $440.06 | gap_only classification, bearish EMA 1 hr after buying |
| 18:05 | BUY | FIX | 3.7 | $1,903.71 | INCREASE → 19% — perfect momentum |
| 18:05 | SELL | DELL | 57.4 | $210.94 | verifier dust-sweep |
| 18:05 | SELL | LLY | 13.0 | $963.71 | verifier dust-sweep |
| 18:05 | BUY | GOOGL | 9.28 | $384.43 | verifier gap-fill |
| 19:08 | SELL | COIN | 66.9 | $203.45 | earnings in 3 days, momentum 0 |
| 19:08 | SELL | GOOGL | 37.96 | $382.77 | momentum 0, fading |
| 19:08 | BUY | AXTX | 313.0 | $46.41 | momentum 100, breaking_out |
| 19:08 | BUY | META | 15.48 | $611.73 | comm services, above VWAP |
| 19:08 | BUY | PWR | 14.69 | $758.48 | ai_data_center_power leader |
| 19:08 | SELL | FIX | 10.0 | $1,902.81 | verifier dust-sweep |

---

## Trade-by-Trade Analysis (2026-05-04)

| Symbol | Type | Qty | Entry | Exit | PnL% | PnL$ | Verdict |
|---|---|---|---|---|---|---|---|
| HCAI | carry | 1492 | $11.84 | $10.69 | -9.71% | **-$1,716** | BAD — held too long, no stop triggered at -8.78% before exit-arbiter fired |
| GEV | carry | 14.57 | $1,140.45 | $1,071.49 | -6.05% | **-$1,005** | BAD — 12-day carry loss; position was rebuilt on May 4 then immediately exited |
| AMZN | intraday | 65.3 | ~$273.90 | $270.65 | -1.19% | -$212 | BAD — opened and closed same day (<1h hold); entry thesis broke immediately |
| UNH | intraday | 17.27 | ~$374.50 | $368.25 | -1.67% | -$108 | CHURN — replaced by LLY at same scan; diversification-swap loss |
| WDC | intraday | 24.51 | $445.36 | $440.06 | -1.19% | **-$130** | BAD — "memory peer" framing entered at 10.9%, exited 1h later as gap_only |
| SNDK | churn | 10.10 | $1,246.97 | $1,237.52 | -0.76% | -$95 | BAD — sold prior SNDK at $1,237 then re-bought at $1,247 (+$9.45/share churn cost) |
| GOOGL | intraday | 37.96 | ~$383.77 | $382.77 | -0.26% | -$38 | CHURN — bought by arbiter, verifier added gap-fill, then exited 2h later |
| COIN | intraday | 66.9 | ~$203.90 | $203.45 | -0.22% | -$30 | CHURN — earnings gate fired after verifier added to position same scan |
| MU | intraday | 23.0 | $580.42 | $580.81 | +0.07% | +$9 | CHURN — INCREASE to 28% then exit 1h later; flat P&L on $13K deployed |
| DELL | intraday | 57.4 | $210.52 | $210.94 | +0.20% | +$24 | CHURN — bought arbiter scan 4, verifier dust-swept scan 5 |
| FIX | intraday | 10.0 | ~$1,900 | $1,902.81 | +0.14% | +$26 | CHURN — bought+increased, then verifier dust-swept same cycle |
| LLY | intraday | 13.0 | ~$963.14 | $963.71 | +0.06% | +$7 | CHURN — bought+increased, verifier dust-swept same cycle |

**Closed P&L: -$3,268 (approx)**
**Floating (AXTX/META/PWR/SPY): +$69**
**Net realized+floating day P&L: ~-$3,200** (EOD equity drop from $101,101 to $99,850 = -$1,251; remainder from prior-day unrealized shifts)

---

## Cross-Trade Patterns

- **SPY proxy bloat (critical).** SPY as "cash proxy" grew from 0% (Apr 22) → 77.6% (Apr 30) → 59.8% (May 4). When the selector can't fill 6 equity slots, it parks remaining capital in SPY. At 60% SPY, the bot can generate at most ±40% of any alpha move. This is the primary structural drag: the active book is too thin to beat SPY.

- **ai_data_center theme concentration breach.** On May 4, the arbiter simultaneously targeted MU (28%), SNDK (12.6%), WDC (10.9%), DELL (12.1%), FIX (19%), GEV (15.6%), PWR (11.1%) — all tagged `ai_data_center`. Combined target: **109%** vs the 50% theme cap. `sector_guard.py` runs post-execution but doesn't gate the selector's targeting phase, so the selector kept producing breaching allocations.

- **Verifier vs. arbiter conflict (same scan cycle).** Three positions were bought by the arbiter then dust-swept by the verifier in the **same 19:08 UTC scan**: DELL, LLY, FIX. The verifier interpreted the prior arbiter's `target=0` from an earlier scan and overwrote the new arbiter's fresh targets. This is a race condition — the verifier's reference state is stale by the time it runs.

- **MU oversizing.** The arbiter targeted MU at 28% (INCREASE from 13.3%). `initial_entry_cap_pct=0.15` only applies to new entries; existing positions can grow to `max_position_pct=0.50`. A 28% single-name swing position in an intraday cycle is inconsistent with a swing-cadence, diversified mandate.

- **Same-day round-trips.** 10 buy-then-sell pairs executed on May 4. Net round-trip P&L: -$91. Friction and spread alone cost more than the strategy recovered. The MU round-trip deployed $13.4K for +$9 return; WDC deployed $10.9K for -$130.

- **SNDK sell-low/buy-high churn.** Prior SNDK position (23.3 shares at $1,140.78) was exited, then 10.1 new SNDK shares bought at $1,246.97 (+9.3% higher) the same day. The arbiter scored SNDK as "best new candidate" without recognizing it had just been sold out of. Estimated churn cost: ~$95 direct + opportunity cost of selling the larger prior position.

- **Carry losses on GEV/HCAI.** GEV was held from Apr 22 at $1,140.45 for 12 trading days, drifting -6.05% while SPY gained +1.95%. HCAI accumulated a -9.71% loss before the exit-arbiter fired. Both positions lacked intraday momentum signals that triggered exit — the technical flip / stall threshold (`exit_stall_threshold: 0.10`) should have caught them sooner.

- **Missed bearish halt signal.** The macro score on May 4 was 0.27 (neutral) with VIX at 27.3. The `bearish_halt_score` is -0.55, so no halt triggered. But VIX at 27 is elevated (historical neutral is ~17-20). The halt threshold doesn't account for absolute VIX level, only the composite score. All 12+ new entries on a high-VIX day increased risk exposure.

---

## Proposed Changes

### 1. Cap SPY cash proxy at 35% (`selector.max_cash_proxy_pct`)

**Why:** SPY ended May 4 at 59.8% of equity. At that level the bot cannot generate meaningful alpha over SPY regardless of how well the active book performs. If the selector can't find 6 good equity names, it should hold cash rather than index exposure.

**Diff (config.yaml):**
```yaml
# Before (not set; defaults to uncapped)
selector:
  enabled: true

# After
selector:
  enabled: true
  max_cash_proxy_pct: 0.35   # SPY proxy hard cap; excess parks as idle cash
```

**Expected impact:** Forces active equity allocation ≥65% when the selector has any qualifying candidates. Estimated +0.3–0.8% daily alpha on active days vs current SPY-dominated state. Requires `selector.py` enforcement.

**Backtest:** SPY proxy exceeded 35% on 5 of 9 trading days (Apr 28–May 4 except May 1). Alpha was negative on all 5 of those days (-0.81% to -5.40%).

---

### 2. Enforce theme weight cap in selector pre-targeting (`diversification.enforce_in_selector: true`)

**Why:** `sector_guard.py` runs post-execution and can only adjust fills, not prevent the selector from allocating 109% to one theme. On May 4, seven ai_data_center names were targeted simultaneously, all entered within one scan cycle, all contributing to churn when sector_guard trimmed them.

**Diff (config.yaml):**
```yaml
# Before
diversification:
  max_theme_weight_pct: 0.50

# After
diversification:
  max_theme_weight_pct: 0.50
  enforce_in_selector: true    # selector respects cap before targeting, not after
```

**Expected impact:** Prevents 7-name ai_data_center pile-ons. Forces the selector to spread across sectors even when one theme dominates the momentum screen. Estimated -2 to -3 intraday trades per scan on concentrated days.

**Backtest offline:** Not fully backtestable from journal alone — would require replaying selector targets per scan. Qualitative: the May 4 ai_data_center breach (109% target) accounts for most of the day's churn.

---

### 3. Reduce `risk.max_position_pct` from 0.50 to 0.20 for rebalance growth

**Why:** The arbiter targeted MU at 28% (an INCREASE from 13.3%) in a single scan. `initial_entry_cap_pct=0.15` controls new entries but `max_position_pct=0.50` allows the arbiter to grow any existing position to 50% of equity. A 28% single-name position on a swing-cadence strategy with 6× daily scans is oversized: at -1% stop, 28% weight = 0.28% equity risk per stop, close to the 0.5% max but leaves room for two more to stack.

**Diff (config.yaml):**
```yaml
# Before
risk:
  max_position_pct: 0.50

# After
risk:
  max_position_pct: 0.20      # rebalance growth cap; prevents oversized single bets
```

**Expected impact:** Prevents the MU-class 28% INCREASE. Distributes capital across more names. Given max_positions=6 and min_per_position_pct=0.04, a 0.20 cap allows the selector to reach 5 full-sized + 1 smaller position. Estimated reduction in per-scan notional churn on INCREASE cycles: ~30%.

**Backtest:** MU was targeted at 28% once (May 4). The prior MU position at 13.3% → 28% deployed $14K in a single scan, then was fully exited 1 hour later at break-even. No gain, ~$100 in spread/slippage.

---

### 4. Add `selector.min_hold_scans: 2` to prevent single-scan round-trips

**Why:** WDC was bought in the 17:04 scan and exited in the 18:05 scan (1 scan later) for -$130. GOOGL: bought 17:04, exited 19:08 (2 scans, marginal). The selector has no minimum hold constraint — the exit-arbiter can flip a fresh entry after a single scan. A 2-scan minimum hold (≈2 hours) matches the swing cadence intent and prevents noise-driven exits.

**Diff (config.yaml):**
```yaml
# Before
selector:
  enabled: true

# After
selector:
  enabled: true
  min_hold_scans: 2            # must hold a new position for at least 2 scans before exiting
```

**Expected impact:** Would have blocked the WDC exit at scan 5 after buying at scan 4. Estimated blocking of 4–6 churn exits per day on high-activity days. Requires enforcement in `exit-arbiter` or `orchestrator.py` (check position age in scans vs. min_hold_scans).

**Backtest:** Of the 10 same-day round-trips on May 4, net P&L was -$91. At least 3 (WDC, GOOGL, COIN) would have been blocked by a 2-scan hold. Conservative estimate: +$170 saved on May 4 alone.

---

### 5. Add absolute VIX floor to entry gate (`macro.vix_entry_gate_floor: 30`)

**Why:** The macro bearish halt fires at composite score < -0.55, but VIX at 27.3 on May 4 is historically elevated. The composite score was +0.27 (neutral), so no halt triggered despite VIX well above neutral levels. At VIX > 30, intraday momentum signals are less reliable (rapid mean-reversion), and the bot entered 12+ new positions in a high-VIX environment, all of which were churned out the same day.

**Diff (config.yaml):**
```yaml
# Before
macro:
  bearish_halt_score: -0.55
  bearish_halt_on_vix_spike: true

# After
macro:
  bearish_halt_score: -0.55
  bearish_halt_on_vix_spike: true
  vix_entry_gate_floor: 30.0   # halt new entries when VIX >= this regardless of composite score
```

**Expected impact:** Would not have triggered on May 4 (VIX=27.3 < 30). But on Apr 27 (equity -4.88%, worst day) VIX was likely elevated — this gate would reduce entry frequency on those days. Conservative setting at 30 vs aggressive at 25.

**Backtest:** May 4 VIX=27.3 (below floor of 30); would not have affected that day. Apr 27's -4.88% loss day had VIX data unavailable in local files; skipping quantitative backtest.

---

## Summary: Largest Alpha Destroyers (2026-04-22 → 2026-05-04)

1. **Carry losses on stale positions** (GEV -6.05%, HCAI -9.71%) = -$2,721 realized
2. **ai_data_center theme concentration** (109% targeted May 4) = systemic churn
3. **SPY proxy bloat** (60–78% of equity on 5 of 9 days) = active book too thin to generate alpha
4. **Same-day round-trips** (10 on May 4 alone) = -$91 direct + spread friction
5. **Verifier/arbiter race condition** (3 dust-sweeps of fresh arbiter buys) = wasted execution cost

**9-day total alpha: -19.26% vs SPY.** The combination of carry losses + SPY bloat + churn is structural, not random. The proposed changes target the root causes rather than tuning individual thresholds.
