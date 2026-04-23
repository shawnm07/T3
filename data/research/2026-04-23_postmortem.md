# Post-Mortem 2026-04-23

## Data availability
| File | Status |
|------|--------|
| `data/research/2026-04-23_eod.json` | ✅ Present |
| `data/research/2026-04-22_eod.json` | ✅ Present (30d series: 2 days only) |
| `data/journal/trades.jsonl` | ✅ Present |
| `data/journal/decisions.jsonl` | ✅ Present |
| `data/research/20260423T150718_scan.json` | ✅ Present |
| `data/research/20260423T195604_preclose.json` | ✅ Present |
| 30-day EOD history | ⚠️ Only 2 days available — rolling stats limited |

---

## Performance today (portfolio vs SPY)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **+1.56%** |
| SPY daily return | **-0.39%** |
| Outperformance vs SPY | **+1.95%** ✅ |
| Equity (EOD) | $101,208.19 |
| Cash (EOD) | **-$935.19** ⚠️ (negative — cash_reserve_pct breached) |
| Positions | 10 |
| Trades today | 9 |
| daily_drawdown | 0% (positive day) |
| Kill switch | Not triggered |

**Risk budget status:**
- `cash_reserve_pct` (5%): **BREACHED** — cash is -$935 (-0.92% of equity)
- `max_position_pct` (15%): ✅ max position is ~13% (AMD)
- `daily_drawdown` (2.5%): ✅ no drawdown

---

## Positions at close

| Symbol | Side | Qty | Avg Entry | Close | P&L% | MV ($) | % Portfolio |
|--------|------|-----|-----------|-------|------|--------|-------------|
| AMD | LONG | 41.42 | $302.72 | $305.33 | +0.86% | $13,166 | 13.0% |
| APLS | LONG | 184 | $40.93 | $40.94 | +0.02% | $7,533 | 7.4% |
| ARW | LONG | 67.25 | $183.21 | $187.50 | +2.34% | $12,609 | 12.5% |
| AVGO | LONG | 29.16 | $420.07 | $419.94 | **-0.03%** | $12,289 | 12.1% |
| FIX | LONG | 7.08 | $1758.55 | $1773.91 | +0.87% | $13,100 | 12.9% |
| GEV | LONG | 10.98 | $1140.45 | $1149.53 | +0.80% | $12,627 | 12.5% |
| IRDM | LONG | 105 | $40.86 | $40.93 | +0.17% | $4,298 | 4.2% |
| MU | LONG | 25.68 | $480.57 | $481.72 | +0.24% | $12,434 | 12.3% |
| SPY | LONG | 2.37 | $711.70 | $708.45 | **-0.46%** | $1,677 | 1.7% |
| VRT | LONG | 38.53 | $315.20 | $321.75 | +2.08% | $12,410 | 12.3% |

> P&L computed as `(current_price - avg_entry) / avg_entry`; shorts flip sign. `pnl_pct` from eod.json used directly.

---

## Trades today

| Time (UTC) | Symbol | Side | Type | Notional | Reason |
|------------|--------|------|------|----------|--------|
| 15:06:17 | AMD | BUY | Rebalance add | $7,506 | conf=0.74, tech=+0.85, pnl=+3.7% |
| 15:06:18 | ARW | BUY | Rebalance add | $3,803 | conf=0.73, tech=+0.82, pnl=+3.5% |
| 15:06:18 | AVGO | BUY | Rebalance add | $7,344 | conf=0.71, tech=+0.78, pnl=+4.5% |
| 15:06:18 | FIX | BUY | Rebalance add | $7,274 | conf=0.73, tech=+0.81, pnl=+3.1% — **risk agent: REJECT** |
| 15:06:18 | GEV | BUY | Rebalance add | $6,918 | conf=0.73, tech=+0.83, pnl=+2.8% — risk agent: caution |
| 15:06:18 | MU | BUY | Rebalance add | $8,052 | conf=0.70, tech=+0.75, pnl=+1.1% |
| 15:06:19 | VRT | BUY | Rebalance add | $7,001 | conf=0.72, tech=+0.79, pnl=+7.3% |
| 19:56:03 | APLS | BUY | Preclose overnight | $7,531 | ov=+0.39, RSI 87.2 ⚠️ |
| 19:56:03 | IRDM | BUY | Preclose overnight | $4,301 | ov=+0.36, RSI 70.3 |

**Failed exits (preclose — Pydantic bug):**
| Symbol | Decision | Error |
|--------|----------|-------|
| AVGO | close (dir=-0.034) | `ClosePositionRequest`: qty and percentage both None |
| MU | close (dir=-0.102) | `ClosePositionRequest`: qty and percentage both None |

---

---

## 2a. Per-trade quality verdict

| Time (UTC) | Symbol | Side | Size | Avg Entry | Close | P&L% | AI Grade | Reason | Verdict |
|------------|--------|------|------|-----------|-------|------|----------|--------|---------|
| 15:06:17 | AMD | BUY add | $7,506 | $302.72 | $305.33 | +0.86% | B/C/B+/C+ | Rebalance: conf=0.74, tech=+0.85, pnl entering=+3.7% | **good** — momentum confirmed, still below 13% cap |
| 15:06:18 | ARW | BUY add | $3,803 | $183.21 | $187.50 | +2.34% | B/C/D/C+ | Rebalance: conf=0.73, tech=+0.82; sentiment grade D | **good** — smallest add; sentiment weak but tech held |
| 15:06:18 | AVGO | BUY add | $7,344 | $420.07 | $419.94 | **-0.03%** | B/B-/A/C+ | Added at original RSI 76.3 overbought; late-day reversal triggered close signal | **bad** — added $7k then directional reversed same session; close failed (bug) |
| 15:06:18 | FIX | BUY add | $7,274 | $1758.55 | $1773.91 | +0.87% | B/D/B-/**REJECT** | Rebalance executed despite risk agent explicit REJECT | **bad process** — outcome ok today but risk gate bypassed |
| 15:06:18 | GEV | BUY add | $6,918 | $1140.45 | $1149.53 | +0.80% | B/D/B-/caution | Rebalance with risk caution; RSI 78.7 at original entry | **churn risk** — GEV fundamental D, sentiment crowding flag |
| 15:06:18 | MU | BUY add | $8,052 | $480.57 | $481.72 | +0.24% | B/A/C+/approve | Largest add ($8k); close_strength -0.67 at preclose; tried to exit same day | **bad** — biggest add, weakest end-of-day; close failed (bug) |
| 15:06:19 | VRT | BUY add | $7,001 | $315.20 | $321.75 | +2.08% | B/C/A/approve | Best performer; added at pnl=+7.3% entering; VRT held overnight ✅ | **good** — winner scaling with strong overnight hold score |
| 19:56:03 | APLS | BUY new | $7,531 | $40.93 | $40.94 | +0.02% | none (overnight) | ov=+0.39 (low); RSI 87.2; market_bias=-0.024 | **oversized** — extreme RSI, negative market bias, near-zero gain |
| 19:56:03 | IRDM | BUY new | $4,301 | $40.86 | $40.93 | +0.17% | none (overnight) | ov=+0.36 (below buy threshold of 0.35); close_strength=0.36 | **missed filter** — overnight score barely above buy threshold on down-bias day |

> AI grades listed as macro/fundamental/sentiment/risk (technical was B for all rebalances).

---

## 2b. Cross-trade patterns

- **Add-then-same-session-close (AVGO, MU):** Both positions were rebalanced up by $7k–$8k at 10:06 ET, then the preclose run at 15:56 ET issued close signals for both (AVGO dir=-0.034, MU dir=-0.102). Close calls failed due to Pydantic bug — both carried overnight against the system's own judgment. This is the most acute operational risk today.

- **ClosePositionRequest Pydantic bug:** `src/` preclose close logic passes `qty=None, percentage=None` to `ClosePositionRequest`. This silently rejected two exit orders. Both AVGO and MU are held overnight in contradiction to the overnight hold logic.

- **Risk agent gate bypassed on rebalance:** FIX risk grade "REJECT" was logged but rebalance executed $7,274 add. GEV risk grade "caution" also ignored. The rebalance path does not gate on risk agent outcome — it only gates on `blended_confidence >= add_confidence_floor`. A risk=reject should veto the add regardless of blended confidence.

- **Overbought entries on overnight scanner (APLS RSI 87.2, IRDM RSI 70.3):** The overnight scanner scores direction and sentiment but does not filter on absolute RSI. APLS at RSI 87.2 with market_bias=-0.024 and ov_score=0.39 is a poor risk/reward overnight position. Result: +0.02% on $7,531 notional.

- **IRDM scored below buy threshold:** config `overnight.buy_threshold: 0.35`. IRDM ov_score=0.357 — barely above threshold and on a negative-bias day. The effective threshold should be higher on negative market-bias days.

- **Cash reserve floor breached:** 7 rebalance buys ($47,897) + 2 preclose buys ($11,832) = $59,729 deployed from $60,501 starting cash. EOD cash: -$935. The `cash_reserve_pct: 0.05` floor ($5,060 at today's equity) was not maintained. Likely cause: preclose sizing used "reserve_capped@5%" label but two simultaneous orders each computed independently against the same cash balance.

- **SPY cash proxy near-zero:** SPY position is $1,677 (1.7% of equity). After cash went negative, the proxy provides almost no liquidity buffer. Any new buy tomorrow requires a proxy liquidation.

- **Portfolio 100% long, all US equities, sector concentration:** 5 of 10 positions are semiconductor/tech or AI infrastructure (AMD, AVGO, MU, APLS, IRDM, VRT, ARW). No shorts, no defensive exposure. Period_vs_spy = -3.82% reflects cumulative underperformance since tracking began.

---

## 2c. Proposed Changes

### Change 1 — Fix ClosePositionRequest to always pass `percentage=1.0` for full closes

**Why:** AVGO and MU preclose exits failed today because `ClosePositionRequest` received `qty=None, percentage=None`. Both positions were incorrectly held overnight.

**Diff (`src/` preclose/exit logic):**
```python
# BEFORE (somewhere in exit execution path):
ClosePositionRequest(qty=qty, percentage=pct)   # both None when full close

# AFTER:
percentage = pct if pct is not None else (None if qty is not None else 1.0)
ClosePositionRequest(qty=qty, percentage=percentage)
```

**Expected impact:** Eliminates silent exit failures. AVGO and MU would have been closed tonight. Prevents unintended overnight carry of positions the system itself wanted to exit.

---

### Change 2 — Gate rebalance adds on risk agent "reject" (hard block)

**Why:** FIX was added $7,274 today with risk agent grade REJECT and fundamental grade D. Today it was +0.87%, but the process is broken — a risk veto should stop the trade.

**Diff (`config.yaml`):**
```yaml
# BEFORE:
rebalance:
  add_confidence_floor: 0.55

# AFTER — add one line:
rebalance:
  add_confidence_floor: 0.55
  block_on_risk_reject: true   # if AI risk agent graded 'reject', skip add regardless of blended confidence
```

**Expected impact:** Today: FIX add blocked (saves ~$7k exposure on a "D fundamental / reject risk" name). Estimated 1–2 blocked adds/week on names with near-term event risk or deteriorating fundamentals.

---

### Change 3 — Add RSI ceiling for overnight new entries

**Why:** APLS was bought overnight at RSI 87.2 on a negative market-bias day (bias=-0.024). RSI 87 represents mean-reversion risk that the overnight score doesn't penalize. Result: +0.02% on a $7,531 position.

**Diff (`config.yaml`):**
```yaml
# BEFORE:
overnight:
  buy_threshold: 0.35

# AFTER — add one line:
overnight:
  buy_threshold: 0.35
  max_rsi_for_new_buy: 78     # block new overnight long entries when RSI > 78 at preclose scan
```

**Expected impact:** Today: APLS (RSI 87.2) blocked. IRDM (RSI 70.3) passes. Avoids extending overbought momentum into overnight gap risk. Estimated impact: prevents ~1 overbought overnight entry per week.

---

### Change 4 — Raise overnight buy threshold when market_bias < 0

**Why:** IRDM ov_score=0.357 barely exceeded `buy_threshold: 0.35` on a day with `market_bias=-0.024`. The system should require higher conviction when the market is tilted negative.

**Diff (`config.yaml`):**
```yaml
# BEFORE:
overnight:
  buy_threshold: 0.35

# AFTER — add one line:
overnight:
  buy_threshold: 0.35
  bearish_bias_buy_threshold: 0.45   # when market_bias < 0, require overnight score >= 0.45 for new buy
```

**Expected impact:** Today: IRDM (ov=0.357) blocked on negative bias day. Reduces noise entries on weak-close days. Estimated 1–2 fewer borderline overnight entries per week, concentrated on down-bias sessions.

---

### Change 5 — Sequential cash accounting for concurrent preclose buys

**Why:** APLS ($7,531) and IRDM ($4,301) were sized simultaneously, each checking the 5% floor independently against the same cash balance. Combined they consumed the entire cash buffer, leaving EOD cash at -$935.

**Diff (`config.yaml`):**
```yaml
# BEFORE:
overnight:
  max_new_positions: 3

# AFTER — add one line:
overnight:
  max_new_positions: 3
  sequential_cash_check: true   # deduct each confirmed buy notional from available cash before sizing the next candidate
```

**Expected impact:** Today: IRDM would have been sized down or blocked after APLS consumed available cash above the 5% floor. Prevents cash_reserve_pct breaches caused by concurrent preclose order sizing.

---

## 2d. Backtest notes

**Change 1 (close bug fix):** Not backtestable — operational bug with no historical signal. Fix is deterministic; impact today = AVGO + MU would have been flat/closed rather than carried overnight.

**Change 2 (risk reject gate):** Only 2 EOD days available. Today's data: FIX added $7,274 despite reject; ended +0.87% (+$63 on the add). Blocking it would have cost $63 today. Long-run risk-adjusted benefit (avoiding one bad earnings-day add or a confidence-override on a deteriorating name) is qualitatively positive but can't be quantified without 30+ days of journal data.

**Changes 3 & 4 (RSI/bias overnight gates):** Both candidates (APLS +0.02%, IRDM +0.17%) are nearly flat. Blocking both saves $11,832 in overnight exposure with no material P&L cost today. Insufficient historical overnight data to compute win rate improvement.

**Change 5 (sequential cash):** Directly verifiable from today: if APLS consumed $7,531 first, available cash before IRDM = (pre-buy cash ~$13k) − $7,531 − $5,060 floor = ~$409. IRDM min_trade_usd = $500 → IRDM buy blocked. Net: $4,301 of cash preserved, EOD cash ≈ +$3,366 vs actual -$935. Cash_reserve_pct maintained at ~3.3% — still below 5% floor but no longer negative.

---

## Summary scorecard

| Category | Grade | Notes |
|----------|-------|-------|
| Daily return vs SPY | **A** | +1.56% vs -0.39% SPY; +1.95% outperformance ✅ |
| Risk budget — position sizing | **A** | Max position 13.0% (AMD); all within 15% cap |
| Risk budget — cash reserve | **F** | Cash = -$935 (-0.92%); breaches cash_reserve_pct 5% floor |
| Exit execution | **F** | AVGO + MU preclose exits silently failed; both carried overnight against system judgment |
| Rebalance discipline | **C** | FIX added despite risk=REJECT; GEV added with risk=caution |
| Overnight quality | **C-** | APLS RSI 87.2 on negative bias day; IRDM below-threshold score |
| Sector concentration | **C** | 70%+ in tech/AI infra + industrials; no defensive hedge |
| Period vs SPY | **D** | -3.82% since tracking began (cash drag from pre-deployment idle period) |
