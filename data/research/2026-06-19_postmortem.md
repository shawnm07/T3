# Post-Mortem 2026-06-19

## Data Availability

| Source | Status | Latest Entry |
|---|---|---|
| `_eod.json` | **STALE** — 46 calendar days old | `2026-05-04_eod.json` |
| Intraday scans | **STALE** | `20260504T190848_scan.json` |
| Preclose | **STALE** | `20260504T195545_preclose.json` |
| `trades.jsonl` | 204 lines, last entry 2026-05-04 | `position_closed COIN 19:55 UTC` |
| `decisions.jsonl` | 1,556 lines, last entry 2026-05-04 | `eod_report 20:15 UTC` |
| **Today (2026-06-19)** | **NO DATA** | — |

**Critical:** The bot has produced zero artifacts for ~33 trading days. This post-mortem uses the last known state (2026-05-04) as the reference point.

## Performance (last known period: 2026-04-22 → 2026-05-04, 9 trading days)

| Metric | Portfolio | SPY | vs SPY |
|---|---|---|---|
| **Full period return** (equity-based) | +0.22% | +1.95% | **-1.73%** |
| **Last 5 trading days** (4/28→5/4, equity-based) | +3.08% | +0.38% | +2.70% |
| **Last day** (5/4) | -1.24% | -0.36% | **-0.88%** |
| Equity (start → end) | $99,627 → $99,850 | — | — |
| SPY 30d benchmark (per 5/4 snapshot) | — | +10.71% | **-10.49% vs SPY 30d** |

### Equity Curve (daily)

| Date | Equity | Day Δ | SPY Day | vs SPY | Positions | Trades |
|---|---|---|---|---|---|---|
| 2026-04-22 | $99,627 | — | +1.01% | -1.01% | 7 | 7 |
| 2026-04-23 | $101,208 | +1.59% | -0.39% | +1.98% | 10 | 9 |
| 2026-04-24 | $99,343 | -1.84% | +0.77% | -2.61% | 12 | 19 |
| 2026-04-27 | $96,448 | -2.91% | +0.17% | -3.08% | 8 | 24 |
| 2026-04-28 | $96,867 | +0.43% | -0.49% | +0.92% | 4 | 21 |
| 2026-04-29 | $93,999 | -2.96% | -0.01% | -2.95% | 5 | 10 |
| 2026-04-30 | $95,786 | +1.90% | +0.96% | +0.94% | 3 | 23 |
| 2026-05-01 | $101,101 | +5.55% | +0.29% | +5.26% | 4 | 38 |
| 2026-05-04 | $99,850 | -1.24% | -0.36% | -0.88% | 4 | 53 |

**Daily drawdown breaches:** 4/27 (-2.91%), 4/29 (-2.96%) exceed the 2.5% daily_drawdown target.

## Positions at Close (2026-05-04, last known)

| Symbol | Side | Qty | Avg Entry | Current | P&L % | P&L $ | Mkt Value | Weight |
|---|---|---|---|---|---|---|---|---|
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42 | $59,696 | 59.8% |
| AXTX | LONG | 313 | $46.41 | $46.61 | +0.43% | +$63 | $14,589 | 14.6% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | -$16 | $11,130 | 11.1% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$20 | $9,448 | 9.5% |
| **Cash** | — | — | — | — | — | — | $4,987 | 5.0% |

**Concentration:** 59.8% in SPY proxy (idle capital). Three active longs total 35.2% of equity. Cash at 5.0% (at floor).

## Trades on 2026-05-04 (last active day)

53 trade events. Summary of meaningful actions:

| Time (UTC) | Symbol | Action | Qty | Entry/Stop | Outcome |
|---|---|---|---|---|---|
| 14:51 | HCAI | EXIT | 1,492 | — | Closed (was -8.78%) |
| 16:04 | AMZN | EXIT | — | — | Closed (bought earlier by selector) |
| 16:04 | GEV | EXIT | — | — | Closed (bought earlier by selector) |
| 16:04 | UNH | EXIT | — | — | Closed (bought earlier by selector) |
| 16:04 | LLY | BUY | 9.49 | $961.30 / $951.69 | Closed same day |
| 16:04 | MU | ADD | 25.0 | $583.49 / $577.65 | Closed 17:04 |
| 16:04 | NOK | BUY | 367.24 | $13.38 / $13.24 | Closed 17:04 |
| 16:04 | SNDK | BUY | 10.10 | $1250.12 / $1237.62 | Held → EOD position |
| 17:04 | DELL | BUY | 57.39 | $209.91 / $207.81 | Closed 18:05 |
| 17:04 | FIX | BUY | 6.30 | $1884.10 / $1865.26 | Closed 19:08 |
| 17:04 | GOOGL | BUY | 28.68 | $382.82 / $378.99 | Closed 19:08 |
| 17:04 | LLY | ADD | 3.51 | $962.24 / $952.61 | Closed 18:05 (wash trade) |
| 17:04 | WDC | BUY | 24.51 | $442.28 / $437.86 | Closed 18:05 |
| 17:04 | COIN | BUY | 5.10 | — | Closed 19:08 |
| 19:08 | AXTX | BUY | 313.0 | $45.80 / $45.34 | **Held** → EOD |
| 19:08 | META | BUY | 15.48 | $612.19 / $606.07 | **Held** → EOD |
| 19:08 | PWR | BUY | 14.69 | $756.10 / $748.54 | **Held** → EOD |

**11 symbols bought and exited same day.** Only AXTX, META, PWR survived to EOD.

---

## Deep Analysis

### 2a. Trade-by-Trade Quality Ledger (2026-05-04, last active day)

| Symbol | Side | Size ($) | Entry | Exit/Current | P&L | AI Grade | Reason | Verdict |
|---|---|---|---|---|---|---|---|---|
| HCAI | EXIT | $17,934 | $11.84 | ~$10.80 | -8.78% | exit@0.72 | Intraday momentum lost (5 signals) | **GOOD** — correct exit on breakdown |
| AMZN | BUY→EXIT | ~$13,600 | market | market | ~0% | opp_score=92 | Selector top-ranked; exited by next scan | **CHURN** — held <1h |
| GEV | BUY→EXIT | ~$12,000 | market | market | ~0% | opp_score=88 | Selector #2; exited by next scan | **CHURN** — held <1h |
| UNH | BUY→EXIT | ~$10,000 | market | market | ~0% | opp_score=72 | Selector #5; exited by next scan | **CHURN** — held <1h |
| MU | BUY→EXIT | $14,587 | $583.49 | market | ~0% | opp_score=80 | Selector #4 scan 1; closed scan 2 | **CHURN** — held 1h |
| NOK | BUY→EXIT | $4,912 | $13.38 | market | ~0% | selected scan 3 | Low-conviction small-cap | **CHURN** — held 1h |
| LLY | BUY→EXIT | $12,487 | $961.30 | market | ~0% | target 9.1%→12.5% | Bought, added (wash trade), closed | **BAD** — wash trade, net loss |
| SNDK | BUY→EXIT | $12,626 | $1250.12 | market | ~0% | opp_score=? | Bought scan 3; not in final portfolio | **CHURN** — selected then deselected |
| DELL | BUY→EXIT | $12,045 | $209.91 | market | ~0% | target 12.1% | Bought scan 4; closed scan 5 | **CHURN** — held 1h |
| FIX | BUY→EXIT | $11,850→$18,000 | $1884.10 | market | ~0% | target 11.9%→19% | Bought, added (wash trade), closed | **BAD** — wash trade + increased then dumped |
| GOOGL | BUY→EXIT | $10,980 | $382.82 | market | ~0% | target 11% | Bought scan 4, added (wash), closed | **BAD** — wash trade |
| WDC | BUY→EXIT | $10,842 | $442.28 | market | ~0% | target 10.9% | Bought scan 4; closed scan 5 | **CHURN** — held 1h |
| COIN | BUY→EXIT | ~$1,034 | market | market | ~0% | selected 5/6 scans | Most-selected symbol; still churned | **CHURN** — appeared in 5/6 scans, still sold |
| AXTX | BUY | $14,335 | $45.80 | $46.61 | +0.43% | target 14.4% | New entry scan 6 | **OK** — survived to EOD |
| META | BUY | $9,477 | $612.19 | $610.46 | -0.21% | target 9.5% | New entry scan 6 | **OK** — survived to EOD |
| PWR | BUY | $11,110 | $756.10 | $757.38 | -0.15% | target 11.1% | New entry scan 6 | **OK** — survived to EOD |

**Summary:** 3 wash trades. 8 same-day roundtrips. 3 positions survived to close. Of ~$130K notional traded, only ~$35K was productive. Estimated slippage + spread cost: $200-400 on wasted roundtrips.

### 2b. Cross-Trade Patterns

**1. Catastrophic Selector Instability (ROOT CAUSE)**
- 6 selector outputs on 5/4 recommended 6 nearly disjoint portfolios
- Average Jaccard similarity between consecutive scans: **0.26** (essentially random)
- Same pattern across all days: 4/28 avg_jaccard=0.42, 4/30=0.13, 5/1=0.30, 5/4=0.24
- Each scan triggers a full portfolio turnover: sell everything from last scan, buy the new picks
- This is the single largest source of P&L destruction

**2. Extreme Churn**
- 204 total trade events in 9 trading days (22.7/day average)
- 30 unique symbols traded; only SPY held continuously
- 16 same-day roundtrips across 5/1 and 5/4 (9 + 7)
- Position turnover: complete portfolio rotation every 2-3 days (see equity curve table)
- 53 trades on 5/4 alone for a 4-position portfolio = 13.25 trades per surviving position

**3. Wash Trade Pattern**
- 3 wash_trade_recovery events on 5/4: LLY, FIX, GOOGL
- Sequence: buy → next scan drops symbol → sell → next scan re-adds → buy again → sell again
- Violates IRS 30-day wash sale rule and generates unnecessary friction

**4. ai_data_center Theme Concentration Breach**
- 4/22: 6 ai_dc names, weight unknown (market_value=0 artifact)
- 4/23: 6 ai_dc names at **75.1%** weight (cap = 50%)
- 4/24: 7 ai_dc names at **75.4%** weight (cap = 3 per theme, had 7)
- 4/27: 7 ai_dc names at **89.8%** weight — catastrophic, preceded -2.91% drawdown
- sector_guard.py max_per_theme=3, max_theme_weight_pct=0.50 — both grossly violated

**5. Exit Arbiter Bias: Reduce Over Exit**
- 31 exit arbiter calls: 21 reduce (68%), 9 hold (29%), 1 exit (3%)
- The arbiter almost never cleanly exits — it "reduces," which the selector then overrides by buying more in the next scan
- Creates a feedback loop: reduce → selector re-adds → reduce again

**6. Problematic Universe Leakage**
- SOXS (inverse/leveraged semi ETF) appeared in selector output scan 6 on 5/4
- BITO (Bitcoin ETF) appeared in 3/6 scans on 5/4
- MARA (Bitcoin miner) appeared in 1 scan
- These violate "long US equities only, no crypto" mandate
- Discovery pool filter is not catching leveraged/inverse ETFs or crypto-proxy names

**7. SPY Cash-Proxy Churn**
- SPY weight swung wildly: 60.7% (4/22) → liquidated on 4/23 (cash=-$935) → rebuilt to 59.8% (5/4)
- Selector targets SPY at 0-5% but execution parks leftover capital there
- Execution_cash_target diverges massively from selector_cash_target (e.g., 5% target → 64.95% actual on 5/4)

**8. Selector AI Failures**
- 14 AI failures across 9 days (1.6/day)
- On 5/4: 2 consecutive failures before 3rd attempt succeeded (returned 0 positions both times)
- Common issues: "selected count 0 not in [3,6]", fractional qty mismatches, stop_loss precision errors

**9. Daily Drawdown Budget Breached**
- 4/27: -2.91% (limit 2.5%) — correlated to 89.8% ai_data_center concentration
- 4/29: -2.96% (limit 2.5%) — position churn + sector bet
- No circuit breaker exists for daily drawdown; the bot continues trading through breaches

**10. Bot Offline for 46 Days**
- Zero artifacts since 2026-05-04. ~33 trading days with no management
- Frozen portfolio: 59.8% SPY + 3 stale longs unmanaged for 7 weeks
- If any of AXTX, PWR, or META had an adverse event (earnings miss, guidance cut), there was no stop management

### 2c. Proposed Changes

#### Proposal 1: Intraday Selector Stability Floor (Jaccard Gate)

**Why:** Average Jaccard similarity of 0.26 between consecutive scans means the selector is essentially randomizing the portfolio every hour, causing 204 trades in 9 days and 16 same-day roundtrips.

**Diff:**
```yaml
# config.yaml — add under selector:
selector:
  min_jaccard_vs_previous: 0.50    # NEW: reject selector output if overlap with previous scan < 50%
  max_turnover_per_scan: 2         # NEW: max symbols to swap per scan (not counting SPY)
```

```python
# src/orchestrator.py — after selector output validation, before execution:
# Compute Jaccard similarity vs previous scan's selected set
# If jaccard < min_jaccard_vs_previous, skip this selector output and hold current positions
```

**Expected impact:** Reduces same-day roundtrips from ~8/day to ~1/day. Cuts trade count by 60-70%. Prevents wash trades entirely.

#### Proposal 2: Daily Trade Count Circuit Breaker

**Why:** 53 trades on 5/4 for a 4-position portfolio is destructive churn. No mechanism limits total daily trades.

**Diff:**
```yaml
# config.yaml — add under risk:
risk:
  max_trades_per_day: 20           # NEW: hard cap on total orders/day
  max_roundtrips_per_symbol: 1     # NEW: prevent buy→sell→buy same symbol same day
```

**Expected impact:** Caps daily slippage cost at ~$100 instead of $200-400. Prevents wash trades.

#### Proposal 3: Enforce Diversification in Selector Input Validation

**Why:** 4/23-4/27 had 6-7 ai_data_center names at 75-90% weight despite max_per_theme=3 and max_theme_weight_pct=50%. sector_guard.py runs post-execution but the selector itself ignores these caps, creating a conflict loop.

**Diff:**
```python
# src/ai_pipeline.py — in selector input construction:
# Before sending pool to selector, pre-filter:
# - Count existing held positions per theme
# - If theme already at max_per_theme, exclude new candidates from same theme
# - Pass theme caps as hard constraints in the selector prompt
```

```yaml
# config.yaml — add under selector:
selector:
  enforce_theme_caps_in_prompt: true  # NEW: include diversification caps in selector system prompt
```

**Expected impact:** Prevents the 4/27 scenario (89.8% ai_data_center). Estimated drawdown reduction: 1-2% on concentrated-sector down days.

#### Proposal 4: Universe Filter for Leveraged/Inverse/Crypto-Proxy Names

**Why:** SOXS (3x inverse semi ETF), BITO (Bitcoin ETF), MARA (Bitcoin miner) all appeared in selector candidates. These violate the "long US equities only, no crypto" mandate and add leveraged/inverse risk.

**Diff:**
```yaml
# config.yaml — add under universe:
universe:
  exclude_tickers:
    - SOXS
    - SOXL
    - TQQQ
    - SQQQ
    - BITO
    - MARA
    - RIOT
    - GBTG
  exclude_patterns:
    - leveraged_etf      # NEW: filter by ETF type flag
    - inverse_etf
    - crypto_proxy
```

**Expected impact:** Removes 4+ problematic symbols from candidate pool. Prevents regulatory and mandate violations.

#### Proposal 5: Daily Drawdown Circuit Breaker

**Why:** 4/27 (-2.91%) and 4/29 (-2.96%) both breached the 2.5% daily drawdown target. The bot continued trading through both breaches.

**Diff:**
```yaml
# config.yaml — add under risk:
risk:
  daily_drawdown_halt_pct: 0.025   # NEW: halt all new entries when intraday drawdown exceeds this
  daily_drawdown_reduce_pct: 0.02  # NEW: start trimming at 2% drawdown
```

**Expected impact:** Would have prevented additional entries on 4/27 and 4/29 after the drawdown threshold was hit. Estimated P&L savings: $500-1,500 per breach event.

#### Proposal 6: Operational Health Monitor / Watchdog

**Why:** The bot has been offline for 46 calendar days with zero alerting. No mechanism detects "the bot stopped running" as distinct from "the bot ran and found nothing to do."

**Diff:**
```yaml
# config.yaml — add under scheduling:
scheduling:
  watchdog:
    enabled: true                    # NEW
    max_silent_hours: 4              # alert if no scan artifact written in 4h during market hours
    alert_channel: telegram          # or email
    check_interval_minutes: 30
```

**Expected impact:** Would have caught the outage on 5/4 or 5/5 instead of discovering it 46 days later. Prevents unmanaged frozen portfolios.

### 2d. Offline Backtests

**Selector Stability (Proposal 1):**
Using the 26 selector outputs in `decisions.jsonl`, applying a Jaccard floor of 0.50 would have rejected 15 of 26 outputs (58%). On 5/4, only 1 of 6 scans would have executed (the first), preventing all 16 same-day roundtrips on 5/1 and 5/4.

Simulated trade count with Jaccard gate: ~80 (vs 204 actual) — 61% reduction.

**Theme Concentration (Proposal 3):**
On 4/23-4/27, enforcing max_per_theme=3 on ai_data_center would have capped exposure at ~$45K (45%) instead of $75K-$87K (75-90%). On the 4/27 drawdown day, the ai_dc cluster moved ~-3.5% intraday; at 45% weight instead of 90%, portfolio impact would have been -1.58% instead of -3.15% — staying within the 2.5% daily drawdown budget.

**Proposals 2, 4, 5, 6:** Cannot be backtested offline — require either intraday price data (unavailable), live universe screening, or infrastructure changes.

---

## Summary

**North-star gap: portfolio +0.22% vs SPY +1.95% over 9 trading days, then 46 days offline.**

The three critical failures:

1. **Selector instability** (Jaccard avg 0.26) causes hourly portfolio turnover, wash trades, and ~$200-400/day in friction. This is the dominant alpha destroyer.
2. **Theme concentration breach** (89.8% ai_data_center on 4/27) caused the worst drawdown days and violated hard config caps that sector_guard.py failed to prevent pre-execution.
3. **Bot offline for 46 days** with no watchdog, leaving a frozen portfolio of 60% SPY + 3 unmanaged longs.

Fixing selector stability alone (Proposal 1) would likely have preserved $1,500-3,000 in slippage and converted the -1.73% vs SPY into roughly flat performance. Combined with theme enforcement (Proposal 3) and the drawdown breaker (Proposal 5), the risk budget would have been respected.
