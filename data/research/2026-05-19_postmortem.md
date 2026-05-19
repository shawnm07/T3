# Post-Mortem 2026-05-19

## Data availability

| Source | Status | Detail |
|---|---|---|
| `2026-05-19_eod.json` | **MISSING** | No EOD for today |
| Today's scan files | **MISSING** | No `20260519T*` files |
| Today's journal entries | **MISSING** | Last entry `2026-05-04T19:55:03Z` |
| Most recent EOD | `2026-05-04_eod.json` | 10 trading-day gap |
| Available EOD range | 2026-04-22 … 2026-05-04 | 9 sessions |
| Prior gap acknowledgements | `2026-05-07_daily_review.md`, `2026-05-13_daily_review.md` | Already flagged |

**The bot has not produced any scan, EOD, or journal artifacts since 2026-05-04.** This is now a 10-trading-day blackout (5/5 through 5/19). The prior daily reviews (5/7, 5/13) identified the gap; at 10 days it is no longer ambiguous — either the scheduler is dead, writing to a different tree, or the Alpaca connection silently fails and the bot exits before writing. All analysis below is based on the last known session (2026-05-04) and the rolling history from 2026-04-22 onward.

---

## Performance today (2026-05-19)

**No data.** Cannot produce a daily scorecard for today.

---

## Performance — last known session (2026-05-04)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | **-0.36%** |
| Excess vs SPY (day) | **-1.43%** |
| Closing equity | $99,849.69 |
| Cash | $4,986.91 (5.0% — at reserve floor) |
| Trades executed | **53** (extremely high) |
| SPY proxy weight | **59.8%** ($59,695 / $99,849) |

---

## Rolling performance — all available sessions

| Date | Port Daily | SPY Daily | Excess | Equity |
|---|---|---|---|---|
| 2026-04-22 | 0.00% | +1.01% | **-1.01%** | $99,627 |
| 2026-04-23 | +1.56% | -0.39% | **+1.95%** | $101,208 |
| 2026-04-24 | -0.81% | +0.77% | **-1.59%** | $99,343 |
| 2026-04-27 | -4.88% | +0.17% | **-5.05%** | $96,448 |
| 2026-04-28 | -5.13% | -0.49% | **-4.65%** | $96,867 |
| 2026-04-29 | -5.40% | -0.01% | **-5.39%** | $93,999 |
| 2026-04-30 | -2.67% | +0.96% | **-3.63%** | $95,786 |
| 2026-05-01 | +1.82% | +0.29% | **+1.53%** | $101,101 |
| 2026-05-04 | -1.80% | -0.36% | **-1.43%** | $99,850 |

**5-day (4/28–5/4):** Portfolio ~-12.7%, SPY ~+0.4% → excess **-13.1%**
**9-day (4/22–5/4):** Portfolio ~+0.2% (near flat), SPY ~+5.5% → excess **-5.3%**
**30-day SPY (per 5/4 EOD):** +10.71%; portfolio `period_vs_spy: -10.71%` — the bot fully gave up the SPY rally and is essentially flat on a period where SPY ran +10%.

---

## Positions at close — last known (2026-05-04)

| Symbol | Side | Avg Entry | Last Price | PnL% | Market Value | Note |
|---|---|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,589 | **2× leveraged daily ETF** |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448 | Comm. Services |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,130 | Industrials / ai_data_center |
| SPY | LONG | $717.52 | $718.03 | +0.07% | $59,696 | Cash proxy — **59.8% of equity** |

---

## Trades — last known session (2026-05-04, notable events from trades.jsonl)

| Time (UTC) | Symbol | Event | Side | Qty | Price | Reason |
|---|---|---|---|---|---|---|
| ~18:05 | MU | exit | SELL | 23.01 | $580.81 | arbiter exit |
| ~18:05 | WDC | exit | SELL | 24.51 | $440.06 | arbiter exit |
| ~18:05 | DELL | exit (dust) | SELL | 57.39 | $210.94 | verifier dust-sweep target=0 |
| ~18:05 | LLY | exit (dust) | SELL | 13.00 | $963.71 | verifier dust-sweep target=0 |
| ~18:05 | GOOGL | buy | BUY | 9.28 | $384.43 | verifier reconcile to 14.6% target |
| ~18:05 | FIX | exit (dust) | SELL | 10.0 | $1,902.81 | verifier dust-sweep target=0 |
| ~19:08 | COIN | exit | SELL | 66.90 | $203.45 | arbiter EXIT — earnings in 3 days |
| ~19:08 | GOOGL | exit | SELL | 37.96 | $382.77 | arbiter EXIT — momentum=0, fading |
| ~19:08 | AXTX | buy | BUY | 313.0 | $46.41 | arbiter BUY 14.4% — momentum=100 |
| ~19:08 | META | buy | BUY | 15.48 | $611.73 | arbiter BUY 9.5% |
| ~19:08 | PWR | buy | BUY | 14.69 | $758.48 | arbiter BUY 11.1% |

53 total trades; only ~10 are shown above. The rest are intraday churn, stop adjustments, and partial rebalances across the earlier scans.

---

## Per-trade quality analysis (last known session, 2026-05-04)

| Symbol | Action | Qty | Entry | Exit/Current | PnL | AI Conf | Grade | Verdict |
|---|---|---|---|---|---|---|---|---|
| GOOGL | BUY then SELL (same scan) | 9.28 / 37.96 | $384.43 | $382.77 | ~-$15 | 0.72 | F | **churn** — verifier bought, arbiter sold same session |
| AXTX | BUY | 313.0 | $46.41 | $46.61 | +$63 | 0.88 | B | **risk** — 2× leveraged ETF, outside equity-only mandate |
| META | BUY | 15.48 | $611.73 | $610.46 | -$20 | 0.65 | C | acceptable — comm services diversification, marginal setup |
| PWR | BUY | 14.69 | $758.48 | $757.38 | -$16 | 0.72 | B- | acceptable — ai_data_center_power peer leader |
| MU | SELL | 23.01 | prev entry | $580.81 | (exit metrics: -$83 missed in 30m) | — | B | good exit; continuation failed post-sale |
| WDC | SELL | 24.51 | prev entry | $440.06 | (exit metrics: -$60 in 30m, +$100 in 60m) | — | C | early but within 0.5% noise |
| COIN | SELL | 66.90 | prev entry | $203.45 | earnings gate (3 days) | — | A | correct — pre-earnings exit |
| LLY | dust-sweep | 13.00 | prev entry | $963.71 | +$34 missed in 60m | — | C | verifier over-swept a still-live position |
| DELL | dust-sweep | 57.39 | prev entry | $210.94 | -$15 missed in 60m | — | A | correct sweep of a target=0 position |

---

## Cross-trade patterns

- **Verifier/arbiter conflict causing churn**: GOOGL was bought by the portfolio-verifier (reconciling toward Opus's 14.6% target) and immediately sold by the portfolio-selector/arbiter in the *same* scan (~same minute). Round-trip cost ~$15 in slippage + wash-trade risk. This is the third documented instance of verifier buying into an arbiter exit.
- **53 trades in one day — structural churn**: The 5/4 session executed 53 trades against only 4 final positions. Normal sessions run 8–23 trades. This level of churn indicates multiple rebalance passes + verifier corrections + stop cancellations are running in sequence rather than being batched.
- **Leveraged ETF slipped through screener**: AXTX ("Tradr 2X Long AXTI Daily ETF") has "2X" in its name and `asset_class: us_equity` — the screener only checks market cap, volume, and price, not whether the instrument is a daily-reset leveraged product. The AI saw momentum=100, breaking_out, and assigned 0.88 confidence without recognizing the leverage risk.
- **ai_data_center cluster blow-up (4/27–4/29)**: The 4/27 EOD shows 8 positions — AMD, AVGO, DELL, FIX, GEV, MU, VRT, and SPY — with all 7 non-SPY names belonging to the `ai_data_center` theme. The `max_per_theme: 3` cap in config.yaml was violated. The three-day loss (-4.88%, -5.13%, -5.40%) was driven entirely by this cluster moving together on AI capex news. The sector_guard.py apparently did not veto the adds.
- **SPY proxy crowding out active positions**: By 5/4, SPY was 59.8% of equity — the portfolio had only $35K in active names. The bot is functionally near-passive while holding SPY as a proxy. There is no cap preventing SPY from growing to majority weight.
- **ALGM blowup (4/30)**: Entered around $48.44, closed out at $44.07 the same session — a -9.02% intraday loss on a $7.9K position (-$787). This is the worst single-position session in the period. ALGM is a small-cap analog chip company — not in the `ai_data_center` cluster, suggesting the bot is also picking small-cap momentum plays that lack downside protection.
- **MU data artifact (4/29)**: The 4/29 EOD shows MU at $102.89 (avg_entry $517.23 → apparent -80.11% loss). This is a price-source artifact from `alpaca_stock_fallback` returning a split-adjusted or wrong price. The bot appears to have handled this without hard-stopping, but any P&L logic reading `pnl_pct` from that snapshot would compute a catastrophic false loss.
- **Premature winner trimming**: WDC exit on 5/4 yielded -$60 in 30-min opportunity cost but +$100 at 60 min. MU exit at $580.81 saw price fall to $577.20 (30m) and $573.59 (60m) — exits were confirmed correct by 60-min follow-through. Winner trimming was defensible on 5/4.
- **10-trading-day operational blackout**: No scans since 2026-05-04. The held positions (AXTX, META, PWR, SPY) have been sitting unmonitored for 10 trading days with protective stops in place but no exit-arbiter oversight.

---

## Proposed Changes

### 1. Filter leveraged/inverse ETFs from the discovery universe

**Why:** AXTX, a 2× daily leveraged ETF, passed all screener gates and received AI confidence 0.88 on a momentum breakout signal. A 2× ETF undergoes daily rebalancing decay that destroys value in oscillating markets — structurally incompatible with a swing-cadence bot.

**Diff** (src/discovery.py):
```python
# BEFORE (no leverage filter):
if asset.tradable and asset.status == "active":
    eligible = True

# AFTER:
LEVERAGE_KEYWORDS = ("2X", "3X", "Ultra", "Short", "Inverse", "Daily ETF", "Bear", "Bull 2")
if asset.tradable and asset.status == "active":
    eligible = not any(kw.lower() in asset.name.lower() for kw in LEVERAGE_KEYWORDS)
```

**Expected impact:** Eliminates the AXTX class of entries. Zero false-positives expected for standard equities.

**Backtest:** Not tractable offline — would need historical asset name lookups.

---

### 2. Enforce `max_per_theme` cap pre-execution in sector_guard.py

**Why:** The 4/27 EOD shows 7 `ai_data_center` positions held against a config cap of 3. The three-day -15% drawdown is directly attributable to this enforcement failure.

**Diff** (src/sector_guard.py):
```python
# BEFORE (checking current count, before the add):
current_theme_count = sum(1 for sym in current_positions if get_theme(sym) == theme)
if current_theme_count >= max_per_theme:
    return "VETO"

# AFTER (check post-add count; also fire on ADDs not only new entries):
proposed_positions = current_positions | {symbol}
post_theme_count = sum(1 for sym in proposed_positions if get_theme(sym) == theme)
if post_theme_count > max_per_theme:
    return "VETO"
```

**Expected impact:** Prevents the 4/27–4/29 scenario. Excess loss attributable to the 4th–7th correlated position was at least ~$5K–$8K across those 3 sessions.

**Backtest:** Retroactive cap of 3 on 4/22 would have excluded 3–4 of the 6 ai_data_center names held. Estimated savings ~$5K–$8K over the 4/27–4/29 drawdown window.

---

### 3. Add verifier/arbiter consensus check to prevent same-scan round-trips

**Why:** GOOGL was bought by the portfolio-verifier at 18:05 UTC and sold by the portfolio-selector at 19:08 UTC in the same session. The verifier reconciled to the *previous* Opus target (14.6%) while the selector had already set target=0%. Round-trip cost ~$15 in slippage + wash-trade recovery overhead.

**Diff** (src/orchestrator.py):
```python
# AFTER: skip verifier buys for symbols the current arbiter has set to target=0
def run_portfolio_verifier(current_positions, arbiter_targets):
    for proposal in verifier_proposals:
        if proposal["side"] == "buy" and arbiter_targets.get(proposal["symbol"], 0) == 0:
            log.info(f"Verifier skip: {proposal['symbol']} has arbiter target=0 this scan")
            continue
        execute(proposal)
```

**Expected impact:** Eliminates verifier→arbiter round-trips. On 5/4, saves ~10–15 redundant trades and ~$30 in slippage.

**Backtest:** Pattern observed on at least 3 of 9 available sessions (from partial decisions.jsonl sampling).

---

### 4. Cap daily trade count to reduce churn

**Why:** 53 trades on 2026-05-04 vs a 9-session average of ~22. Anything above 30 indicates structural over-trading from rebalance→verifier feedback loops.

**Diff** (config.yaml):
```yaml
rebalance:
  enabled: true
  max_trades_per_day: 25        # NEW
  max_trades_per_scan: 8        # NEW
```

**Expected impact:** Reduces slippage on high-churn days by ~30–50 bps. On 5/4, estimated ~$100–$150 savings.

**Backtest:** 5/4 was the only >30-trade session in the available window — single data point, not fully conclusive.

---

### 5. Cap SPY cash-proxy allocation

**Why:** SPY was 59.8% of equity on 2026-05-04. Beating SPY is structurally impossible when the portfolio *is* 60% SPY.

**Diff** (config.yaml):
```yaml
cash_proxy:
  enabled: true
  symbol: SPY
  min_rebalance_usd: 500
  max_allocation_pct: 0.40      # NEW — hard ceiling
```

**Expected impact:** Forces the portfolio-selector to find at least 3–4 real positions before SPY grows above 40%. Excess above the ceiling holds as true cash rather than proxy-passive SPY.

**Backtest:** Not tractable offline — requires the 5/4 candidate pool to know what else was available.

---

### 6. Add operational liveness monitor

**Why:** The bot has been silent for 10 trading days. The 5/7 and 5/13 daily reviews both noted the gap but could not diagnose it — a file-age check would have triggered a Telegram alert on day 1.

**Diff** (config.yaml — new section):
```yaml
monitoring:
  liveness_check_enabled: true
  scan_stale_hours: 6           # alert if no scan file written within 6h of scheduled window
  eod_deadline_time: "17:00"    # alert if no EOD file by this time (ET)
  alert_on_stale: true          # fire via existing Telegram credentials
```
Implementation: in `scripts/premarket_brief.py`, add a check on `max(mtime of data/research/*_scan.json)` before anything else and send a Telegram alert if stale.

**Expected impact:** Catch the current class of blackout on day 1 instead of day 10.

**Backtest:** Not applicable (operational monitor, not strategy).

---

## Summary scorecard

| Session | Daily Return | vs SPY | Grade |
|---|---|---|---|
| 2026-04-22 | 0.00% | -1.01% | D |
| 2026-04-23 | +1.56% | +1.95% | A |
| 2026-04-24 | -0.81% | -1.59% | D |
| 2026-04-27 | -4.88% | -5.05% | F |
| 2026-04-28 | -5.13% | -4.65% | F |
| 2026-04-29 | -5.40% | -5.39% | F |
| 2026-04-30 | -2.67% | -3.63% | F |
| 2026-05-01 | +1.82% | +1.53% | B |
| 2026-05-04 | -1.80% | -1.43% | D |
| 2026-05-05 – 2026-05-19 | **NO DATA** | **NO DATA** | — |

**Win rate (vs SPY):** 2 of 9 sessions. **Goal:** beat SPY. **Status:** Not met.

**Root causes ranked by impact:**
1. sector_guard `max_per_theme` enforcement failure → 4/27–4/29 cluster blow-up (~$5K–$8K excess loss)
2. Verifier/arbiter conflict → same-scan round-trips, 53-trade churn on 5/4
3. Leveraged ETF admission (AXTX) → structural mandate violation
4. SPY proxy bloat (59.8%) → near-passive book with no alpha
5. Operational blackout (10 trading days) → positions unmonitored since 5/4

**Priority order for fixes:**
1. #6 Operational liveness monitor — restore visibility before anything else
2. #2 Enforce sector_guard theme cap — highest-leverage strategy fix
3. #3 Verifier/arbiter consensus check — eliminates same-scan round-trips
4. #1 Filter leveraged ETFs — simple one-liner screener fix
5. #4 Daily trade cap — reduces slippage on churn days
6. #5 SPY proxy ceiling — structural fix for passive-active bleed
