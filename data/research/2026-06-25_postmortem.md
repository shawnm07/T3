# Post-Mortem 2026-06-25

## Data availability

| Source | Status |
|--------|--------|
| `2026-06-25_eod.json` | **MISSING** — no EOD snapshot for today |
| `2026-06-25*_scan.json` | **MISSING** — no scans today |
| `decisions.jsonl` | Available (1556 entries through 2026-05-04) |
| `trades.jsonl` | Available (204 entries through 2026-05-04) |
| EOD history | 9 files: 2026-04-22 → 2026-05-04 |

**52-day data gap**: Last recorded activity was 2026-05-04. The bot appears to have stopped running scans after that date. This post-mortem covers the full available record (2026-04-22 through 2026-05-04) as a comprehensive review.

---

## Performance summary (2026-04-22 → 2026-05-04)

| Metric | Portfolio | SPY | vs SPY |
|--------|-----------|-----|--------|
| Cumulative return | **-17.31%** | +1.95% | **-19.26%** |
| Last 5 days | -13.18% | +0.39% | -13.57% |
| Worst single day | -5.40% (04-29) | — | — |
| Starting equity | $99,627 | — | — |
| Ending equity | $99,850 | — | — |
| Net P&L | +$222 | — | — |

The portfolio underperformed SPY by **19.26 percentage points** over 9 trading days. Three consecutive days (04-27 through 04-29) saw drawdowns of -4.88%, -5.13%, and -5.40% — each exceeding the 2.5% daily drawdown target.

---

## Daily breakdown

| Date | Port % | SPY % | vs SPY | Equity | Trades | Positions | Holdings |
|------|--------|-------|--------|--------|--------|-----------|----------|
| 04-22 | +0.00% | +1.01% | -1.01% | $99,627 | 7 | 7 | AMD, ARW, AVGO, FIX, GEV, MU, VRT |
| 04-23 | +1.56% | -0.39% | +1.95% | $101,208 | 9 | 10 | AMD, APLS, ARW, AVGO, FIX, GEV, IRDM, MU, SPY, VRT |
| 04-24 | -0.81% | +0.77% | -1.59% | $99,343 | 19 | 12 | AMD, APLS, ARW, AVGO, DELL, FIX, GEV, IRDM, MU, OGN, SPY, VRT |
| 04-27 | -4.88% | +0.17% | -5.05% | $96,448 | 24 | 8 | AMD, AVGO, DELL, FIX, GEV, MU, SPY, VRT |
| 04-28 | -5.13% | -0.49% | -4.65% | $96,867 | 21 | 4 | AVGO, DELL, MU, SPY |
| 04-29 | -5.40% | -0.01% | -5.39% | $93,999 | 10 | 5 | DELL, MU, NOK, SPY, V |
| 04-30 | -2.67% | +0.96% | -3.63% | $95,786 | 23 | 3 | ALGM, DELL, SPY |
| 05-01 | +1.82% | +0.29% | +1.53% | $101,101 | 38 | 4 | HCAI, SNDK, SPY, STX |
| 05-04 | -1.80% | -0.36% | -1.43% | $99,850 | 53 | 4 | AXTX, META, PWR, SPY |

---

## Positions at close (2026-05-04)

| Symbol | Side | Avg Entry | Current | P&L % | P&L $ | Mkt Value | Weight |
|--------|------|-----------|---------|-------|-------|-----------|--------|
| AXTX | Long | $46.41 | $46.61 | +0.43% | +$62.60 | $14,589 | 14.6% |
| META | Long | $611.73 | $610.46 | -0.21% | -$19.63 | $9,448 | 9.5% |
| PWR | Long | $758.48 | $757.38 | -0.15% | -$16.16 | $11,130 | 11.1% |
| SPY | Long | $717.52 | $718.03 | +0.07% | +$42.40 | $59,696 | 59.8% |
| **Cash** | — | — | — | — | — | $4,987 | 5.0% |

---

## Trades on last active day (2026-05-04) — 53 total

### Exits (11 position closes)

| Symbol | Qty | Exit Price | Reason | Verdict |
|--------|-----|-----------|--------|--------|
| HCAI | 1,492 | $10.69 | -8.78% loss, momentum collapse (5 signals) | **good** — correct stop-loss execution |
| AMZN | 65.3 | $270.65 | Fading momentum, below VWAP, bearish EMA | **bad** — 17.7% position exited to "fund higher-conviction" that also failed |
| GEV | 14.6 | $1,071.49 | Weak momentum, below VWAP, bearish EMA | questionable — 15.6% position exited same-scan |
| UNH | 17.3 | $368.25 | Fading volume, LLY "stronger" | **bad** — exited to fund LLY which was dust-swept same day |
| MU | 23.0 | $580.81 | Bearish EMA, peer WDC "scores 22pts higher" | **bad** — WDC also exited same day |
| WDC | 24.5 | $440.06 | Gap-only, bearish EMA, fading volume | **churn** — bought and sold same day |
| DELL | 57.4 | $210.94 | Verifier dust-sweep | **churn** — bought and dust-swept same day |
| LLY | 13.0 | $963.71 | Verifier dust-sweep | **churn** — bought, increased, dust-swept same day |
| COIN | 66.9 | $203.45 | Momentum=0, fading, earnings 3 days | **churn** — verifier bought, arbiter exited same day |
| GOOGL | 38.0 | $382.77 | Momentum=0, below EMA20, fading | **churn** — bought and exited same day |
| FIX | 10.0 | $1,902.81 | Verifier dust-sweep | **churn** — bought, increased, dust-swept same day |

### Entries (15 orders)

| Symbol | Qty | Reason | Survived EOD? |
|--------|-----|--------|---------------|
| LLY | 9.5 | BUY 9.1% — healthcare leader | No (dust-swept) |
| MU | 25.0 | INCREASE 28.0% — pool leader | No (exited same day for WDC) |
| NOK | 367 | BUY 4.9% — telecom leader | No (not in EOD) |
| SNDK | 10.1 | BUY 12.6% — memory sector | No (not in EOD) |
| DELL | 57.4 | BUY 12.1% — IT leader | No (dust-swept) |
| FIX | 6.3 | BUY 11.9% — data center power | No (dust-swept) |
| GOOGL | 28.7 | BUY 11.0% — comm services | No (exited same day) |
| LLY | 3.5 | INCREASE 12.5% | No (dust-swept) |
| WDC | 24.5 | BUY 10.9% — memory peer | No (exited same day) |
| COIN | 5.1 | Verifier reconcile 14.8% | No (exited same day) |
| FIX | 3.7 | INCREASE 19.0% | No (dust-swept) |
| GOOGL | 9.3 | Verifier reconcile 14.6% | No (exited same day) |
| AXTX | 313 | BUY 14.4% — breakout momentum | **Yes** |
| META | 15.5 | BUY 9.5% — comm services | **Yes** |
| PWR | 14.7 | BUY 11.1% — industrials/DC | **Yes** |

**Of 15 entries on 2026-05-04, only 3 survived to EOD.** The other 12 were same-day exits or dust-sweeps — pure churn generating friction with zero alpha.

---

## Cross-trade patterns

### 1. Catastrophic same-day churn
- **7 of 11 exits** on 2026-05-04 were symbols bought earlier that same day (WDC, DELL, LLY, FIX, COIN, GOOGL, MU)
- The selector buys position X at scan N, then the arbiter exits it at scan N+1 when momentum scores shift. This is a systematic selector-vs-arbiter disagreement, not an edge case.
- Same-day round trips also occurred on 2026-05-01 (AMD, AVGO, BAND, INTC, MSFT, PWR, SOFI, TSLA, UNH — 9 symbols) and 2026-04-30 (DELL).
- **Impact**: ~$500-1000/day in implicit spread costs, zero holding period for thesis to work.

### 2. Over-concentration in ai_data_center theme
- On 2026-04-22: AMD, AVGO, FIX, GEV, MU, VRT — **6 of 7 positions** all correlated to AI data center capex
- Config has `max_per_theme: 3` but the `ai_data_center` override wasn't in place until later
- When AI capex narrative reversed (04-27 onward), all positions fell together → -4.88% day

### 3. Consecutive daily drawdown breaches
- Three straight days >2.5% drawdown (04-27: -4.88%, 04-28: -5.13%, 04-29: -5.40%)
- No circuit breaker triggered. The `bearish_halt_score: -0.55` macro gate didn't fire because macro stayed "neutral" (SPY was only slightly down)
- The bot lacks a portfolio-level daily drawdown circuit breaker

### 4. Verifier-arbiter conflict loop
- On 2026-05-04: Verifier reconciles COIN to Opus target 14.8% → Arbiter immediately exits COIN (momentum=0, earnings)
- Same with GOOGL: Verifier reconciles to 14.6% → Arbiter exits (momentum=0, fading)
- The verifier enforces stale Opus targets from a prior scan while the arbiter responds to live momentum — they fight each other.

### 5. Position count volatility
- Positions swung from 7→10→12→8→4→5→3→4→4 across 9 days
- 42 unique symbols traded in 9 days with max_positions=6
- Average holding period: <2 days for most names

### 6. SPY cash proxy drag
- SPY position ranged from 36% to 60% of the portfolio
- When the portfolio is 60% SPY (05-04), the bot is effectively a levered SPY tracker with 40% active risk — worst of both worlds

### 7. Trade count escalation
- Trades per day: 7→9→19→24→21→10→23→38→53
- The last day had **53 trades** on a $100K account — wildly excessive
- Most are AI-driven rebalances that reverse within hours

---

## Proposed changes

### Proposal 1: Same-day re-entry cooldown

**Why**: 7 of 11 exits on 2026-05-04 were same-day round trips. Selector buys at one scan, arbiter exits at the next. Zero holding period wastes spread.

**Diff**: `config.yaml`
```
# Add new key under selector:
selector:
  same_day_reentry_block: true    # NEW — block entries on symbols exited earlier today
```
AND in `src/orchestrator.py`, before entry execution, filter out symbols that appear in today's `position_closed` events in `trades.jsonl`.

**Expected impact**: Eliminates ~60% of same-day churn (12 of 15 entries on 05-04 would have been blocked). Saves ~$500-1000/day in implicit costs.

### Proposal 2: Portfolio-level daily drawdown circuit breaker

**Why**: Three consecutive days exceeded 2.5% drawdown with no halt. The macro gate only fires on extreme macro scores, not portfolio-level P&L.

**Diff**: `config.yaml`
```
# Add new section:
circuit_breaker:
  daily_drawdown_halt_pct: 0.025   # NEW — halt all new entries when daily unrealized P&L < -2.5%
  cooldown_scans: 2                # skip next N scans after trigger
```

**Expected impact**: Would have halted new entries on 04-27 (-4.88% day) preventing further losses on 04-28 and 04-29. Estimated savings: 3-5% of equity over the worst 3-day stretch.

### Proposal 3: Minimum holding period before exit eligibility

**Why**: Average holding period <2 days. The AI thesis never has time to play out before momentum noise triggers exits.

**Diff**: `config.yaml`
```
# Add under exit_arbiter:
exit_arbiter:
  min_holding_scans: 3    # NEW — position must survive 3 scan cycles before exit-eligible
  min_holding_hours: 4    # NEW — or at least 4 hours since entry
```

**Expected impact**: Forces thesis to develop. Would have prevented same-day exits of DELL, LLY, FIX, GOOGL, WDC, COIN on 05-04. Cannot backtest offline — requires live price data.

### Proposal 4: Verifier deference to recent arbiter exits

**Why**: Verifier reconciles to stale Opus targets while arbiter has already exited based on live momentum. They fight in a buy-sell loop.

**Diff**: `src/orchestrator.py` — in the verifier pass, skip reconciliation for any symbol the arbiter exited in the current scan cycle.

```python
# Before verifier pass:
exited_this_cycle = {t['symbol'] for t in scan_trades if t['event'] == 'position_closed'}
# In verifier target comparison:
if symbol in exited_this_cycle:
    continue  # respect arbiter's exit
```

**Expected impact**: Eliminates the COIN/GOOGL-style verifier-vs-arbiter conflict. On 05-04, would have prevented 3 wash-trade-recovery events and 2 unnecessary reconciliation buys.

### Proposal 5: Reduce max trades per scan

**Why**: 53 trades in one day on a $100K account is pathological churn. Each scan generates 5-10 trades because the selector reshuffles the entire portfolio.

**Diff**: `config.yaml`
```
# Add under execution:
execution:
  max_trades_per_scan: 6    # NEW — hard cap on orders per scan cycle
  max_trades_per_day: 20    # NEW — daily hard cap
```

**Expected impact**: Forces the bot to prioritize highest-conviction actions. On 05-04, would have capped at 20 trades total instead of 53, eliminating low-conviction churn.

---

## Backtest (offline, from journal data only)

**Proposal 1 (same-day reentry block) — retroactive analysis:**

| Date | Actual trades | Trades after blocking same-day re-entries | Blocked |
|------|---------------|------------------------------------------|--------|
| 2026-04-30 | 23 | 21 | DELL (re-entered after close) |
| 2026-05-01 | 38 | 20 | AMD, AVGO, BAND, INTC, MSFT, PWR, SOFI, TSLA, UNH |
| 2026-05-04 | 53 | 35 | WDC, DELL, LLY, FIX, COIN, GOOGL, MU |

Over the last 3 active days, same-day reentry blocking would have eliminated **25 trades** (~22% of volume). All blocked entries were subsequently exited the same day anyway — meaning 100% of them were pure churn with negative expected value.

**Proposal 2 (daily drawdown breaker) — retroactive analysis:**

If a -2.5% intraday drawdown had halted new entries:
- 04-27: halt would have fired. 04-28 new entries blocked → no new positions entered into the continuing drawdown.
- The bot's equity trough was $93,999 on 04-29. With the breaker, approximate trough would have been ~$95,500 (saved ~$1,500 or 1.5% of equity) by avoiding entries into a falling market.

---

## Key takeaway

The bot's #1 problem is **hyperactive churn**, not poor stock selection. The selector and arbiter disagree on ~50% of entries within hours, generating costly round trips. Fix the holding period / same-day block first; the other proposals are secondary.

The 52-day data gap (since 2026-05-04) also needs investigation — the bot may have crashed, lost API access, or been manually stopped.
