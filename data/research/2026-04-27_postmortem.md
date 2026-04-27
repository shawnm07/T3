# Post-Mortem 2026-04-27

## Data Availability

| Source | Status |
|--------|--------|
| `data/research/2026-04-27_eod.json` | ✅ present |
| `data/research/20260427T*.json` (7 scans) | ✅ present |
| `data/journal/trades.jsonl` (24 today) | ✅ present |
| `data/journal/decisions.jsonl` (240 today) | ✅ present |
| `config.yaml` | ✅ present |
| Rolling EOD (4 dates: 04-22…04-27) | ✅ present |
| `data/research/20260427T195644_preclose.json` | ✅ present |

---

## Performance Today (Portfolio vs SPY, from eod.json)

| Metric | Value |
|--------|-------|
| EOD Equity | $96,447.88 |
| Daily Return | **-4.88%** |
| SPY Daily | +0.17% |
| vs SPY (daily) | **-5.05%** ❌ |
| Cash at EOD | $4,697.68 (4.87%) ⚠️ below 5% floor |
| Positions | 8 |
| Trades Today | 24 |
| Kill Switch | NOT triggered (preclose snapshot showed +1.24%) |

### Risk-Budget Breaches
- `daily_drawdown` = 4.88% > **2.5% limit** — kill switch threshold exceeded
- `cash_reserve_pct` = 4.87% < **5.0% floor**
- `max_position_pct` (goal: 0.15) = MU at **28.4%** of EOD equity

---

## Positions at Close

| Symbol | Side | Avg Entry | Close | PnL% | $ PnL | Wt% |
|--------|------|-----------|-------|------|-------|-----|
| AMD | LONG | $319.29 | $315.50 | -1.19% | -$57.83 | 4.99% |
| AVGO | LONG | $422.52 | $398.65 | -5.65% | -$406.57 | 7.04% |
| DELL | LONG | $214.48 | $205.67 | -4.11% | -$751.65 | 18.19% |
| FIX | LONG | $1,768.58 | $1,615.00 | -8.68% | -$1,218.55 | 13.28% |
| GEV | LONG | $1,140.45 | $1,050.70 | -7.87% | -$321.64 | 3.90% |
| MU | LONG | $514.53 | $495.13 | -3.77% | -$1,071.68 | **28.36%** |
| SPY | LONG | $711.05 | $714.90 | +0.54% | +$27.57 | 5.31% |
| VRT | LONG | $316.00 | $303.16 | -4.06% | -$573.94 | 14.04% |

**All 8 positions red except SPY cash proxy.** Total mark-to-market loss: **-$4,374.29**

---

## Trades Today (24 total)

| Time (UTC) | Symbol | Side | Notional | Fill Px | Reason |
|------------|--------|------|----------|---------|--------|
| 15:00 | AMD | SELL | $2,145 | $335.14 | arbiter REDUCE 12.1% → 10% |
| 15:00 | ARW | SELL | $6,032 | $185.83 | arbiter EXIT 5.9% → 0% |
| 15:00 | FIX | SELL | $2,522 | $1,750.21 | arbiter REDUCE 12.5% → 10% |
| 15:00 | GEV | SELL | $2,205 | $1,107.26 | arbiter REDUCE 12.2% → 10% |
| 15:00 | OGN | SELL | $4,344 | $13.17 | arbiter EXIT, take +16% gain |
| 15:00 | DELL | BUY | $8,245 | $214.06 | arbiter INCREASE 9.9% → 18% |
| 15:00 | MU | BUY | $11,160 | $519.97 | arbiter INCREASE 9% → 20% |
| 16:01 | AMD | SELL | $1,914 | $332.45 | arbiter REDUCE 9.9% → 8% |
| 16:01 | GEV | SELL | $2,758 | $1,110.08 | arbiter REDUCE 9.7% → 7% |
| 16:01 | FIX | BUY | $2,014 | $1,782.44 | arbiter INCREASE 10% → 12% |
| 16:01 | MU | BUY | $3,991 | $528.65 | arbiter INCREASE 20.1% → 24% |
| 16:03 | VRT | BUY | $754 | $319.24 | verifier reconcile → 13% |
| 18:00 | AMD | SELL | $2,074 | $335.03 | arbiter REDUCE 8% → 6% |
| 18:00 | GEV | SELL | $2,290 | $1,121.20 | arbiter REDUCE 7.3% → 5% |
| 18:00 | FIX | BUY | $2,100 | $1,803.74 | arbiter INCREASE 11.9% → 14% |
| 18:03 | AVGO | SELL | $818 | $416.30 | verifier reconcile → 7% |
| 18:03 | MU | BUY | $3,179 | $518.29 | verifier reconcile → 27% |
| 19:30 | AMD | SELL | $1,000 | $336.73 | arbiter REDUCE 6% → 5% |
| 19:30 | GEV | SELL | $983 | $1,115.10 | arbiter REDUCE 5% → 4% |
| 19:33 | MU | BUY | $1,338 | $520.59 | verifier reconcile → 28% |
| 19:33 | VRT | BUY | $1,223 | $322.10 | verifier reconcile → 14% |

*(3 zero-fill events: APLS ×2, IRDM ×1 — apparent order rejections, not included above)*

---

---

## Rolling Benchmark (all available EOD dates)

| Date | Portfolio | SPY | vs SPY |
|------|-----------|-----|--------|
| 2026-04-22 | 0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.58% |
| 2026-04-27 | **-4.88%** | +0.17% | **-5.05%** |
| **4d cumulative** | **-4.19%** | **+1.56%** | **-5.75%** |

> Prior close (04-24 EOD) equity: $99,343. Today's open (first crypto scan): $101,002 (+1.67% intraday gap-up). Session high: $102,171 at 12:03 PM ET. Close: $96,448 — a **-5.61% reversal from intraday high**.

---

## 2a — Per-Trade Quality Table

| Time ET | Symbol | Side | Notional | Entry | Exit/Close | PnL vs Close | AI Grade | Reason | Verdict |
|---------|--------|------|----------|-------|------------|--------------|----------|--------|---------|
| 11:00 | AMD | SELL | $2,145 | $319.29* | $335.14 | +$5.01% realized | — | REDUCE 12.1%→10% fading 3.7% from open | **mixed** — correct direction, but freed capital flowed into worse positions |
| 11:00 | ARW | SELL | $6,032 | $185.33 | $185.83 | +0.03% flat | — | EXIT 5.9%→0%: no edge | **good** — cleaned house, no drag |
| 11:00 | OGN | SELL | $4,344 | ~$11.36 | $13.17 | +16% realized gain | — | EXIT, take +16% | **good** — best exit of the day |
| 11:00 | FIX | SELL | $2,522 | $1,768.58* | $1,750.21 | -1.04% partial | — | REDUCE 12.5%→10% | **bad** — immediately RE-BOUGHT at higher prices (see 12:01, 14:00) |
| 11:00 | GEV | SELL | $2,205 | $1,140.45* | $1,107.26 | -2.92% partial | — | REDUCE 12.2%→10% | **good** — kept trimming; closed -7.87% |
| 11:00 | DELL | BUY | $8,245 | $214.06 | $205.67 | -3.92% | — | INCREASE 9.9%→18%: strongest intraday relative strength | **bad** — concentrated at intraday midpoint; closed -3.92% from this fill |
| 11:00 | MU | BUY | $11,160 | $519.97 | $495.13 | -4.78% | pass×5 in scans | INCREASE 9%→20%: best intraday strength | **bad** — AI scan consistently said PASS but arbiter allocated aggressively; closed -4.78% |
| 12:01 | AMD | SELL | $1,914 | $319.29* | $332.45 | +4.11% realized | — | REDUCE 9.9%→8% fading 4.2% | **churn** — 2nd AMD sell in 60 min; AMD is -1.19% from entry, excessive trimming |
| 12:01 | GEV | SELL | $2,758 | $1,140.45* | $1,110.08 | -2.66% partial | — | REDUCE 9.7%→7% | **good** — continued correct trim |
| 12:01 | FIX | BUY | $2,014 | $1,782.44 | $1,615.00 | -9.40% | — | INCREASE 10%→12%: up 3.5%, near high | **bad** — bought within 12 min of trimming, at higher price than the trim; chased the high |
| 12:01 | MU | BUY | $3,991 | $528.65 | $495.13 | -6.34% | pass | INCREASE 20.1%→24%: breaking out +5.4% | **very bad** — bought at or near intraday HIGH; MU was at its peak, returned -6.34% to close |
| 14:00 | AMD | SELL | $2,074 | $319.29* | $335.03 | +4.93% realized | — | REDUCE 8%→6% fading 3.6% | **churn** — 3rd AMD sell; AMD ended -1.19%, not a severe underperformer |
| 14:00 | GEV | SELL | $2,290 | $1,140.45* | $1,121.20 | -1.69% partial | — | REDUCE 7.3%→5% | **good** |
| 14:00 | FIX | BUY | $2,100 | $1,803.74 | $1,615.00 | -10.46% | — | INCREASE 11.9%→14%: breaking out 4.8% | **very bad** — highest fill of the day; bought FIX at its intraday peak, immediately reversed -10.46% |
| 14:03 | MU | BUY | $3,179 | $518.29 | $495.13 | -4.47% | — | verifier reconcile →27% | **bad** — reconcile pushed MU past 27% on a fading price |
| 15:30 | AMD | SELL | $1,000 | $319.29* | $336.73 | +5.46% realized | — | REDUCE 6%→5% earnings in 8d | **churn** — 4th AMD sell; correct rationale (earnings) but total AMD churn was $7,133 in sells |
| 15:30 | GEV | SELL | $983 | $1,140.45* | $1,115.10 | -2.22% partial | — | REDUCE 5%→4% | **good** |
| 15:33 | MU | BUY | $1,338 | $520.59 | $495.13 | -4.89% | — | verifier reconcile →28% | **bad** — final MU accumulation 4 min before preclose; 28% concentration locked in |

> *\* avg_entry carried from prior days*

---

## 2b — Cross-Trade Patterns

- **Intraday-momentum chasing into position peaks**: MU was added in 5 lots across 11:00→15:33 ET totaling ~$19,668; the 12:01 add hit at $528.65 (intraday high). FIX was added at $1,782 and $1,803 — the two highest prices seen all day. Both reversed hard into the close. Pattern: arbiter reads "breaking out" and immediately scales to maximum, then verifier reconcile locks in the concentration.

- **FIX buy-trim-rebuy cycle (oversized)**: FIX was trimmed at 11:00 @ $1,750.21, re-bought at 12:01 @ $1,782.44 (32pt higher) and again at 14:00 @ $1,803.74. Net effect: sold low, bought high twice. FIX closed at $1,615 (-8.68%). The original trim logic was correct; the re-buy logic was wrong.

- **AMD serial over-trimming**: AMD was sold 4 separate times ($2,145 + $1,914 + $2,074 + $1,000 = $7,133 total) while it moved between $332–$337. AMD closed at -1.19% from avg entry — not a failing position. The capital released funded MU/DELL/FIX adds that performed far worse. AMD trims cost the portfolio an opportunity vs what the released capital bought.

- **AI scan vs arbiter disagreement on MU**: Scan AI gave MU a PASS verdict at every single scan today (7 times, confidence 0.40–0.55). Yet the portfolio arbiter allocated MU from 9% → 28%. The scan-level signal and the portfolio-level allocation were directly contradictory. The scan AI's caution was the right call.

- **AI arbiter failure rate**: 2 of 6 portfolio_arbiter calls returned null (14:06 and 15:25). After the 14:06 null, the fallback rebalance ran but produced no trades. After the 15:25 null, no fallback trades were triggered. The successful 15:00 arbiter ran without constraint on single-name concentration.

- **Kill switch blind spot — final-minutes price action**: Preclose snapshot (15:56 ET) showed portfolio at +1.24% daily return vs kill switch threshold of -2.5%. The actual close at 16:00 ET wiped $5,442 from equity, pushing to -4.88%. The kill switch monitors intraday snapshots and cannot react to price action in the final 4 minutes of the session.

- **Cash floor breach via verifier reconcile**: The 15:33 MU and VRT reconcile buys ($2,561 combined) pushed EOD cash to $4,697 (4.87%) — just below the 5% floor. Verifier reconcile trades should respect the cash floor constraint.

- **DELL concentration via single rebalance jump (9.9%→18%)**: DELL was sized to 18% in one move based on "strongest intraday relative strength." With a 15% goal cap, this alone would have been blocked. DELL closed -4.11% ($751.65 loss).

- **No bearish halt despite neutral+VIX=28 macro**: Macro scored 0.204–0.217 all day (neutral regime), VIX at 28.1–28.4. The `bearish_halt_score: -0.55` threshold was never approached. All new entries and adds were allowed. A VIX-adjusted gate for concentration adds was absent.

---

## 2c — Proposed Changes

### Change 1: Align `max_position_pct` with stated risk budget

**Why:** Config has `max_position_pct: 0.50` but the trading goal is 0.15. MU reached 28.4% of equity today; capping at 15% would have limited MU loss from today's buys to ~$572 instead of $1,072 (estimated), and prevented DELL from being jumped to 18%.

**Diff (config.yaml):**
```yaml
# Before
risk:
  max_position_pct: 0.50

# After
risk:
  max_position_pct: 0.15
```

**Expected impact:** Single-name concentration capped at 15%. Today's MU loss capped at ~$571 (from $1,072); DELL would not have reached 18%. Estimated loss reduction: ~$600–900. Also prevents the verifier reconcile from chasing a target above 15%.

---

### Change 2: Raise overnight hold threshold to filter weak-signal holds

**Why:** At preclose (15:56 ET), AMD directional score was 0.073 and AVGO was 0.056 — barely above the 0.0 hold threshold. Both closed deeply negative. A threshold of 0.15 would have closed AMD and AVGO before end-of-day, reducing overnight exposure by ~$11.6K.

**Diff (config.yaml):**
```yaml
# Before
overnight:
  hold_threshold: 0.0

# After
overnight:
  hold_threshold: 0.15
```

**Expected impact:** AMD (score 0.073) and AVGO (score 0.056) would have been closed at preclose. Combined market value ~$11.6K freed. At today's actual close prices, this would have prevented ~$464 in additional overnight losses on those two names. Broader benefit: less exposure to gap-down risk in weak-signal holds.

---

### Change 3: Add VIX-adjusted size cap for intraday concentration adds

**Why:** At VIX=28 (elevated), the arbiter added MU to 20% then 24% citing "breaking out." With elevated VIX, momentum breakouts have higher reversal risk. A concentration add guard based on intraday gain percent would have blocked the 12:01 MU add at $528 (up 5.4% intraday).

**Diff (config.yaml):**
```yaml
# Before
rebalance:
  winner_profit_threshold: 0.03    # don't trim if unrealized pnl > +3%

# After
rebalance:
  winner_profit_threshold: 0.03
  max_intraday_gain_for_add_pct: 0.04   # block adds when position already up >4% intraday
```

> Requires a companion code change in the rebalance logic to check current_price vs day_open_price before issuing an add. Config key surfaces the threshold so it is tuneable without code changes later.

**Expected impact:** MU add at 12:01 (up 5.4%) blocked. FIX add at 14:00 (up 4.8%) blocked. Estimated prevention of $6,091 in losing add notional; estimated loss reduction ~$315–640 at today's close prices.

---

### Change 4: Kill switch anchoring to prior-day EOD equity

**Why:** The kill switch computed daily_return = +1.24% at 15:56 ET because it measured from the intraday open snapshot, not from the prior-day close. Prior-day close was $99,343; today's EOD was $96,448 = -2.91% from prior close. Had the kill switch been anchored to the 04-24 EOD equity, it would have been closer to triggering in the final hour.

**Diff (config.yaml):**
No config key controls this — it is a code-level fix in the kill switch daily return calculation. Proposed change: anchor `daily_return = (current_equity - prior_eod_equity) / prior_eod_equity` where `prior_eod_equity` is read from the previous `*_eod.json` file.

> Config proposal (new key for documentation/override):
```yaml
# Before
kill_switch:
  daily_drawdown_pct: 0.025

# After
kill_switch:
  daily_drawdown_pct: 0.025
  anchor_to_prior_close: true      # measure daily drawdown from prior EOD, not intraday open
```

**Expected impact:** Today, anchored daily_return would have reached -2.91% sometime in the final session minutes, potentially triggering a partial halt. Conservative estimate: would have blocked the 15:33 MU/VRT verifier reconcile adds ($2,561), preserving cash above the 5% floor.

---

### Change 5: Verifier reconcile must respect cash floor

**Why:** The 15:33 ET verifier reconcile adds (MU $1,338 + VRT $1,223) pushed EOD cash to $4,697 (4.87%) — below the 5% floor. Reconcile trades should be gated by available cash minus `cash_reserve_pct * equity`.

**Diff (config.yaml):**
```yaml
# Before
cash_proxy:
  min_rebalance_usd: 500

# After
cash_proxy:
  min_rebalance_usd: 500
  reconcile_respect_cash_floor: true   # verifier reconcile skips buys if cash < cash_reserve_pct * equity
```

> Requires code change in the verifier reconcile path to check remaining cash before each buy order.

**Expected impact:** Today's reconcile buys would have been partially or fully skipped, keeping cash ≥ $4,820 (5% of $96,448). Prevents floor breach without changing strategy.

---

## 2d — Backtest Notes

- **Change 1 (max_position_pct 0.50→0.15)**: In-repo journal shows MU was added to 28% in a single session. Applying the 15% cap retroactively to today's trades would have blocked the 12:01 add ($3,991) and the 14:03 reconcile ($3,179) and 15:33 reconcile ($1,338) — total $8,508 not deployed into MU. At MU's actual daily drop, that's ~$321–428 saved. DELL blocked above 15%: the 11:00 add would have been capped to ~$5,200 instead of $8,245 (~$477 saved). Cannot backtest further without historical daily data beyond 4 dates in repo.

- **Change 2 (hold_threshold 0.0→0.15)**: Applying to 04-24 preclose data is not possible (no 04-24 preclose file in repo). Applying to today: AMD+AVGO would have been sold at preclose prices. Only 1 preclose file available in repo — single-day backtest only.

- **Changes 3–5**: Require code changes; cannot backtest against journal data without implementing the logic. Offline estimates provided in impact sections above.

---

## Summary & Priority

| # | Change | Config Key | Severity | Estimated Impact |
|---|--------|------------|----------|-----------------|
| 1 | Cap max_position_pct at 15% | `risk.max_position_pct` | **Critical** | Prevents ~$800–1,400 loss concentration on any single reversal day |
| 2 | Raise overnight hold_threshold | `overnight.hold_threshold` | **High** | Reduces weak-signal overnight exposure; frees ~$11.6K on days like today |
| 3 | Intraday gain guard for adds | `rebalance.max_intraday_gain_for_add_pct` | **High** | Blocks chasing breakouts near intraday highs; saves ~$300–640 on reversal days |
| 4 | Anchor kill switch to prior close | `kill_switch.anchor_to_prior_close` | **Medium** | Closes the 4-minute blind spot; prevents end-of-session add churn on down days |
| 5 | Verifier reconcile cash floor | `cash_proxy.reconcile_respect_cash_floor` | **Low** | Keeps cash ≥ 5% floor; prevents small structural breach |

**Root cause in one sentence:** The portfolio arbiter concentrated 28% into MU and 18% into DELL at intraday highs — both reversed -4% to -8% into the close — while AMD was serially churned 4× and FIX was trimmed then re-bought at higher prices twice, and the kill switch failed to trigger because it measured intraday equity rather than the prior-day close.

