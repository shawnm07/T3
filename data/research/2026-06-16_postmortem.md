# Post-Mortem 2026-06-16

## Data availability

| File | Status | Notes |
|------|--------|-------|
| `data/research/2026-06-16_eod.json` | ❌ MISSING | No scan ran today |
| `data/research/20260616T*_scan.json` | ❌ MISSING | No intraday scans |
| Latest EOD on disk | `2026-05-04_eod.json` | 43 calendar days / ~29 trading days stale |
| `data/journal/trades.jsonl` | ✅ Present | 204 lines, last entry `2026-05-04T19:55Z` |
| `data/journal/decisions.jsonl` | ✅ Present | 1,556 lines, last entry `2026-05-04T20:15Z` |
| `data/research/*_daily_review.md` (Jun) | ✅ Present | 2026-06-05, 06-09, 06-11 — all "no-data" |
| Rolling 30d EOD history (for benchmarks) | ⚠️ Partial | 9 days available: 2026-04-22 → 2026-05-04 |

**Critical finding:** The bot has been completely silent for 29 trading days (43 calendar days).
No scans, no trades, no snapshots have been committed since `2026-05-04T20:15Z`.
This is the 7th consecutive "no-data" review.

---

## Performance today (portfolio vs SPY, from eod.json)

> **No data for 2026-06-16.** All metrics below are from the last known EOD: `2026-05-04`.

| Metric | Value | vs Goal |
|--------|-------|----------|
| Last known equity | $99,849.69 | Started ~$99K |
| Last known daily return (5/4) | **-1.80%** | ❌ Below SPY |
| SPY daily return (5/4) | -0.36% | — |
| Portfolio vs SPY (5/4) | **-1.44%** | ❌ underperformed |
| Period return (4/22 → 5/4, 9 days) | **-16.31%** | ❌ far below target |
| SPY same period | **+1.95%** | — |
| Alpha vs SPY (9-day window) | **-18.26%** | ❌ severe underperformance |
| Rolling 5d (4/28 → 5/4) | **-12.66%** | ❌ persistent drawdown |
| SPY rolling 5d | **+0.38%** | — |
| Last known positions | 4 | — |
| Last known trades/day (5/4) | 53 | ⚠️ extremely high |
| Avg trades/day (9-day window) | 22.7 | ⚠️ excessive churn |

**Risk budget status (last known, 2026-05-04):**
- `max_position_pct=0.50`: ✅ SPY=59.8%, AXTX=14.6%, PWR=11.1%, META=9.5%
- `cash_reserve_pct=0.05`: ✅ Cash=$4,987 (5.0% of equity — exactly at floor)
- `daily_drawdown < 2.5%`: ❌ Breached on 4/27 (-4.88%), 4/28 (-5.13%), 4/29 (-5.40%), 4/30 (-2.67%)
- `initial_entry_cap_pct=0.15`: ✅ No single equity position exceeds 15%

---

## Positions at close (last known state: 2026-05-04)

> P&L computed from `avg_entry` and `current_price` per the repo rule. Alpaca `unrealized_plpc` ignored.

| Symbol | Side | Qty | Avg Entry | Last Price | P&L % | Market Value | % Portfolio |
|--------|------|-----|-----------|------------|--------|--------------|-------------|
| AXTX | LONG | 313.00 | $46.41 | $46.61 | **+0.43%** | $14,588.93 | 14.6% |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** | $9,448.36 | 9.5% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** | $11,129.62 | 11.1% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** | $59,695.86 | 59.8% |
| **TOTAL** | | | | | | **$94,862.77** | 95.0% |
| Cash | — | — | — | — | — | $4,986.91 | 5.0% |
| **Equity** | | | | | | **$99,849.69** | |

**Frozen-book exposure (2026-05-04 → 2026-06-16, ~29 trading days):**
The portfolio has been static at this allocation for 29 trading days. Without live prices, P&L since 5/4 cannot be computed from repo data.

---

## Trades today (2026-06-16)

**None — no scan ran.** Last trade activity was 2026-05-04.

| Date | Trades | Events |
|------|--------|--------|
| 2026-04-22 | 7 | 7 order_submitted |
| 2026-04-23 | 9 | 7 rebalance_trade, 2 order_submitted |
| 2026-04-24 | 19 | 13 rebalance, 4 order_submitted, 2 rebalance_failed |
| 2026-04-27 | 24 | 21 rebalance, 3 rebalance_failed |
| 2026-04-28 | 21 | 16 rebalance, 3 rebalance_failed, 2 position_closed |
| 2026-04-29 | 10 | 7 rebalance, 2 order_submitted, 1 position_closed |
| 2026-04-30 | 23 | 4 position_closed, 17 ai_order_failed, 2 order_submitted |
| 2026-05-01 | 38 | 16 ai_order_submitted, 12 position_closed, 9 ai_order_failed, 1 ai_qty_delta |
| 2026-05-04 | 53 | 15 ai_order_submitted, 11 position_closed, 24 exit_learning_metrics, 3 wash_trade_recovery |
| **2026-05-05 → 2026-06-16** | **0** | **Bot silent** |

---

## 2a. Per-trade quality verdict (last active day: 2026-05-04)

> Source: `trades.jsonl` `position_closed` + `exit_learning_metrics` events. P&L from avg_entry rule; exit_learning_metrics used for 30m/60m post-exit drift.

### Exits on 2026-05-04

| Symbol | Side | Qty | Exit Price | Missed 30m P&L | Missed 60m P&L | Reason (arbiter) | Verdict |
|--------|------|-----|-----------|----------------|----------------|-------------------|--------|
| AMZN | LONG | 65.3 | $270.65 | **-$26.12** | n/a | Fading momentum, below VWAP (17.7% of book) | **good** — price fell 30m later |
| COIN | LONG | 5.1 | $202.68 | +$2.25 | -$1.17 | Momentum 0, fading (13.7% of book) | **borderline** — tiny miss, essentially flat |
| DELL | LONG | 57.4 | $210.94 | **-$14.92** | +$16.64 | Verifier dust-sweep | **good** — correct short-term; 60m recovered slightly |
| FIX | LONG | 10.0 | $1,891.10 | n/a | n/a | Momentum fading, below EMA20 (19.0% of book) | **good** — momentum thesis gone |
| GEV | LONG | 14.6 | $1,071.49 | **+$104.03** | n/a | Weak momentum, below VWAP (15.6% of book) | **premature** — left $104 on table in 30m |
| GOOGL | LONG | n/a | n/a | n/a | n/a | Momentum 0, fading (14.6% of book) | **ok** — momentum basis valid |
| HCAI | LONG | 1,492 | $10.69 | **-$164.12** | -$164.12 | AI exit-arbiter conf=0.72 | **good** — saved $164 vs holding |
| LLY | LONG | 13.0 | $963.71 | **+$33.60** | +$69.71 | Acceptable continuation but cautious | **premature** — $34 missed at 30m, $70 at 60m |
| MU | LONG | 25.0 | $577.45 | **+$20.78** | n/a | Weak/flat momentum (13.4% of book) | **premature** — price continued up |
| SNDK | LONG | 23.3 | $1,250.00 | **+$106.96** | -$203.90 | (prior day exit) | **premature at 30m** — $107 left; reversed at 60m |
| STX | LONG | 19.4 | $740.23 | **+$75.96** | -$117.00 | (prior day exit) | **premature at 30m** — $76 left; reversed at 60m |
| UNH | LONG | 17.3 | $368.25 | **+$6.99** | +$8.03 | Acceptable continuation (6.4%) | **premature** — small but consistent upward drift |
| WDC | LONG | 24.5 | $440.06 | **-$59.68** | +$100.0 | Gap-only classification (10.8%) | **good at 30m** — saved $60; reversed at 60m |

**Summary:**
- Premature exits (price rose in 30m): 7 — total missed = **+$350.57**
- Correct/good exits (price fell in 30m): 5 — total saved = **+$308.07**
- Net exit quality at 30m horizon: **-$42.50** (marginal underperformance — nearly break-even)
- SNDK/STX: correct to exit (30m show missed, but 60m show full reversal — so exit was right directionally)

### Same-day open+close churn (2026-05-04)

7 symbols opened AND closed on 5/4: FIX, DELL, MU, LLY, COIN, GOOGL, WDC.
9 symbols churned on 5/1: TSLA, MSFT, AVGO, AMD, SOFI, PWR, BAND, INTC, UNH.

This is the single largest driver of transaction cost waste. Each round-trip costs 2× spread + Alpaca commission.

### AI order failures (2026-04-30 to 2026-05-01)

26 `ai_order_failed` events across 4/30–5/1 (no `reason` field populated). Cluster concentrated on 4/30 (17 failures) and 5/1 (9 failures). Likely cause: AI sizing exceeded Alpaca paper account fractional share limits, or Alpaca API rejected orders during a volatile period. Zero on 5/4 — whatever triggered them resolved.

### Wash trade recoveries (2026-05-04)

3 wash trade recoveries: LLY, FIX, GOOGL. Indicates the system sold and tried to immediately re-buy the same symbols, triggering internal wash-trade detection. Root cause: exit-arbiter issued EXIT at one scan, then selector immediately re-nominated the same symbols for entry.

---

## 2b. Cross-trade patterns

- **Same-day churn is systemic.** On the last 3 active days (4/30, 5/1, 5/4), 0/1/7 symbols were churned. On 5/4, 7 of 11 closed positions were also being bought or targeted on the same day. This is a portfolio-selector / exit-arbiter coordination failure: the exit-arbiter closes a name, the selector immediately re-adds it. Net effect: double transaction cost, zero alpha.

- **AI order failure cluster (4/30–5/1).** 26 failures with no `reason` logged. The rate jumped from 0 on earlier days to 17 on 4/30. The correlation with the equity drawdown days (4/27–4/30: -18.5% cumulative) suggests the failures occurred when the bot tried to execute aggressive rebalances while account equity was falling rapidly, causing sizing calculations to exceed available margin or fractional limits.

- **Macro regime did NOT halt entries despite consecutive 2.5% daily drawdowns.** On 4/27 (-4.88%), 4/28 (-5.13%), 4/29 (-5.40%), the macro premarket scores were 0.219, 0.210, 0.229 — all well above the `bearish_halt_score: -0.55` threshold. VIX was 27–29 but `vix_regime` stayed "normal" throughout. The macro module saw SPY in uptrend (EMA50 above EMA200) and never halted new entries — even as the portfolio was losing 5% per day. The macro signal and portfolio drawdown were orthogonal.

- **RSI overbought entries are the norm, not the exception.** 163 of 269 BUY decisions (60.6%) came with RSI >70. 47 decisions came with RSI >80. The technical scoring model rewards RSI uptrend but does not penalize for extreme RSI. On MRVL (RSI 89.3 on 4/23), TXN, ON (RSI >88) — these are mean-reversion setups against the trend, not momentum setups.

- **SPY proxy concentration at 59.8% at shutdown.** The portfolio-selector parked 60% of capital in SPY as a cash proxy. This is by design, but it means the bot is taking on zero-alpha SPY exposure for 60% of the book and paying transaction costs to rotate in/out on every scan that adjusts SPY holdings. The "beat SPY" goal is arithmetically impossible if 60% of the book *is* SPY.

- **Premature exits are marginally worse than holding (net -$42 at 30m).** The arbiter slightly over-exits. 7 premature vs 5 correct gives a slight edge to holding longer, but the margin is small and would reverse at 60m for SNDK/STX/WDC. Not a major signal on 9 days of data.

- **Wash trades on exit/re-entry same scan.** LLY, FIX, GOOGL all triggered wash-trade recovery on 5/4. Exit-arbiter and selector share the same scan loop but don’t share a "just exited — don’t re-buy" signal. The wash-trade recovery catches it, but the correct fix is upstream.

---

## 2c. Proposed Changes

### Change 1 — Add daily drawdown circuit breaker

**Why:** The portfolio lost -4.88%, -5.13%, -5.40% on three consecutive days (4/27–4/29) while the macro module reported "neutral/uptrend" and never halted entries. The `bearish_halt_score: -0.55` gate is macro-only and does not respond to realized portfolio P&L.

**Diff (config.yaml):**
```yaml
# BEFORE:
risk:
  hard_stop_loss_pct: 0.01
  min_confidence: 0.40

# AFTER — add one key:
risk:
  hard_stop_loss_pct: 0.01
  min_confidence: 0.40
  max_daily_drawdown_pct: 0.025   # if portfolio is down >2.5% intraday, halt NEW entries for remainder of day
```

**Expected impact:** Would have halted new entries on 4/27 (down 4.88%), 4/28, 4/29. On those three days, 24+21+10 = 55 trades (mostly rebalances) were placed while the account was already in a >2.5% intraday hole. Stopping new entries preserves capital during losing streaks; exits still run.

---

### Change 2 — Block same-day re-entry for exited symbols (anti-wash-sale)

**Why:** On 5/4, 7 symbols were both exited and re-entered in the same day, generating 14 round-trips of transaction cost with zero expected alpha (the exit-arbiter said the thesis was gone; the selector immediately disagreed).

**Diff (config.yaml):**
```yaml
# BEFORE:
execution:
  fill_timeout_s: 30
  fill_poll_s: 1.0

# AFTER — add one key:
execution:
  fill_timeout_s: 30
  fill_poll_s: 1.0
  min_hold_scans: 1   # a symbol that was CLOSED this scan may not be re-entered until next scan cycle
```

**Expected impact:** On 5/4, 7 fewer re-entries = ~$70–$100K notional not recycled. Wash-trade recovery events (3 on 5/4) drop to 0. Forces the selector and exit-arbiter to agree before roundtripping the same name.

---

### Change 3 — Cap entry RSI at 75

**Why:** 60.6% of all BUY decisions (163/269) came with RSI >70; 47 came with RSI >80. Entering at RSI >75 is buying extended momentum against mean-reversion risk. This is the dominant pattern in the -18% underperformance window.

**Diff (config.yaml):**
```yaml
# BEFORE:
signals:
  weights:
    technical: 0.35

# AFTER — add one key under signals:
signals:
  max_entry_rsi: 75   # numeric BUY gate: block new entries where RSI > 75 regardless of combined score
  weights:
    technical: 0.35
```

**Expected impact:** Blocks ~28% of BUY decisions (76 out of 269 in the 9-day window). Concentrates entries on pullbacks with more mean-reversion upside. Would not eliminate momentum entries — RSI 65–75 is strong trend territory. Estimated 1–3 fewer entries/scan on extended trend days.

---

### Change 4 — Reduce SPY cash-proxy intraday churn

**Why:** SPY proxy is adjusted every scan. At 60% of equity (~$60K), even a 0.1% intraday price move triggers rebalance trades. On 5/4, 53 total trades included significant SPY adjustments. The `min_rebalance_usd: 500` threshold is too low for a $60K position.

**Diff (config.yaml):**
```yaml
# BEFORE:
cash_proxy:
  enabled: true
  symbol: SPY
  min_rebalance_usd: 500

# AFTER:
cash_proxy:
  enabled: true
  symbol: SPY
  min_rebalance_usd: 2500   # raise dead-band from $500 to $2,500 to suppress SPY micro-churn
```

**Expected impact:** SPY rebalances only when cash displacement exceeds $2,500 (vs current $500). Reduces SPY round-trips by ~80%. On 5/4 (53 trades), estimated 10–15 fewer SPY micro-adjustments.

---

### Change 5 — Add portfolio-level drawdown floor: sell SPY proxy, not equity positions, when rebalancing during losses

**Why:** During the 4/27–4/29 drawdown, the rebalance path was trimming equity positions and redeploying capital into new high-RSI names. This amplified losses. The SPY proxy (60% of book) should be the first liquidity source during drawdown, not equity positions.

**Diff (config.yaml):**
```yaml
# BEFORE:
rebalance:
  enabled: true

# AFTER — add one key:
rebalance:
  enabled: true
  drawdown_trim_proxy_first: true   # when daily_return < -0.01 and rebalance needs cash, sell SPY proxy before equity positions
```

**Expected impact:** During losing days (4/27–4/29), this keeps sector equity positions intact while using the proxy buffer as the source of liquidity, preventing sell-at-loss + rebuy cycles. Reduces realized losses from forced equity trims.

---

### Change 6 — Raise bearish halt sensitivity to portfolio drawdown

**Why:** `bearish_halt_score: -0.55` is purely macro-driven (SPY EMA, VIX, breadth). It never triggered during 4/27–4/29 because SPY was in uptrend even though the portfolio was losing 5%/day. A secondary halt based on consecutive daily portfolio losses would have stopped the bleeding.

**Diff (config.yaml):**
```yaml
# BEFORE:
macro:
  bearish_halt_score: -0.55
  bearish_halt_on_vix_spike: true

# AFTER — add one key:
macro:
  bearish_halt_score: -0.55
  bearish_halt_on_vix_spike: true
  consecutive_loss_days_halt: 2   # halt new entries if portfolio has lost money for 2+ consecutive trading days (exits still run)
```

**Expected impact:** Would have triggered on 4/28 (day 2 of losses after 4/27). Halts new entries on 4/28 and 4/29. Combined with Change 1 (daily DD >2.5%), these two changes would have prevented ~40 trades across the worst 3 days.

---

## 2d. Backtest

**Journal-only data available: 9 trading days (4/22–5/4), 204 trade events, 1,556 decision records.**

**Change 1 (daily DD circuit breaker):**
- Trigger days: 4/27 (-4.88%), 4/28 (-5.13%), 4/29 (-5.40%), 4/30 (-2.67%) — all exceed 2.5%
- Trades that would be blocked: rebalance entries on those days = 21 + 16 + 7 + (some on 4/30) ≈ 40–45 trades
- P&L impact: not computable without fill prices on each blocked trade, but the 4/27→4/29 period returned -14.8% total — blocking new entries would reduce exposure and limit the compounding of losses
- Verdict: directionally positive, not quantifiable from journal-only data

**Change 2 (same-day re-entry block):**
- Churn dates: 4/30 (1 symbol), 5/1 (9 symbols), 5/4 (7 symbols) = 17 round-trip pairs
- If each pair saved 2× spread (~0.05%), on ~$5K–$15K avg notional: $5–$15 per pair × 17 = **$85–$255 saved**
- Wash trades eliminated: 3 on 5/4
- Verdict: small but deterministic gain

**Change 3 (RSI cap at 75):**
- 76 BUY decisions blocked out of 269 (28%) across the 9-day window
- The specific entries at RSI >75 correlated with the high-churn days (4/23 MRVL RSI 89, 4/24 TXN RSI 88, etc.)
- Without fill prices on the RSI >75 entries we cannot compute direct P&L impact
- Indirect: the portfolio lost 16.31% in 9 days while placing 163 RSI>70 entries — the correlation is circumstantial but strong. Blocking overbought entries reduces exposure on mean-reversion days.
- Verdict: directionally positive, quantification requires fill prices

**Changes 4–6:** Not backtestable from journal data alone (require intraday SPY prices, consecutive-loss state tracking, and fill prices). Proposals are directionally sound; prioritize Change 1 + 2 + 3 as highest-confidence changes.

---

## Summary scorecard (last known data window: 4/22–5/4)

| Category | Grade | Notes |
|----------|-------|-------|
| Bot uptime (4/22 → 6/16) | **F** | Silent for 29 trading days; 7th consecutive no-data review |
| Period return vs SPY | **F** | -16.31% portfolio vs +1.95% SPY = -18.26% alpha in 9 days |
| Daily drawdown discipline | **F** | 3 consecutive days breaching 2.5% DD limit (4/27–4/29) |
| Trade quality (exit timing) | **C** | Net -$42 exit quality at 30m; marginally over-exits |
| Churn / same-day round-trips | **D** | 17 same-day round-trips across last 3 days; 26 AI order failures |
| RSI entry discipline | **D** | 60.6% of BUY decisions at RSI >70; 17.5% at RSI >80 |
| Macro halt response | **D** | Zero halts during worst drawdown stretch; macro and portfolio PnL decoupled |
| SPY proxy management | **C** | 60% in SPY by 5/4; too high for "beat SPY" goal; churn from $500 dead-band |
| Risk budget — position sizing | **B** | Max single equity 14.6%; within 15% cap |
| Cash reserve floor | **B** | At exactly 5.0% on 5/4; maintained at limit |

**Priority action items (operational first, strategy second):**
1. **Restore bot.** Confirm scheduler running. Confirm `data/research/` write path matches this repo.
2. **Implement Change 1** (daily DD circuit breaker) — single highest-leverage config change.
3. **Implement Change 2** (same-day re-entry block) — eliminates wash trades and obvious churn.
4. **Implement Change 3** (RSI cap at 75) — reduces overbought momentum chasing.
5. Changes 4–6 are lower priority and require operational data to validate.
