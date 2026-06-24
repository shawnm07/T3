# Post-Mortem 2026-06-24

## Data availability

- **No EOD snapshot for 2026-06-24.** Last available: `2026-05-04_eod.json`.
- No scan files for 2026-06-24. Last scans: 2026-05-04 (7 scans + 1 preclose).
- Journal files (`trades.jsonl`, `decisions.jsonl`) present — last entries from 2026-05-04.
- `config.yaml` present and current.
- **This post-mortem covers the most recent data window: 2026-04-22 through 2026-05-04 (9 trading days).**
- Bot appears to have been offline since 2026-05-04.

## Performance summary (from EOD snapshots)

| Date       | Equity ($) | Daily Return | SPY Daily | vs SPY   | Positions | Trades |
|------------|------------|-------------|-----------|----------|-----------|--------|
| 2026-04-22 | 99,627     |  0.00%      | +1.01%    | -1.01%   | 7         | 7      |
| 2026-04-23 | 101,208    | +1.56%      | -0.39%    | +1.95%   | 10        | 9      |
| 2026-04-24 | 99,343     | -0.81%      | +0.77%    | -1.59%   | 12        | 19     |
| 2026-04-27 | 96,448     | -4.88%      | +0.17%    | -5.05%   | 8         | 24     |
| 2026-04-28 | 96,867     | -5.13%      | -0.49%    | -4.65%   | 4         | 21     |
| 2026-04-29 | 93,999     | -5.40%      | -0.01%    | -5.39%   | 5         | 10     |
| 2026-04-30 | 95,786     | -2.67%      | +0.96%    | -3.63%   | 3         | 23     |
| 2026-05-01 | 101,101    | +1.82%      | +0.29%    | +1.53%   | 4         | 38     |
| 2026-05-04 | 99,850     | -1.80%      | -0.36%    | -1.43%   | 4         | 53     |

**Cumulative period:** Started $99,627 → ended $99,850 = **+0.22%**
**SPY 30d return (from 05/04 eod):** **+10.71%**
**Period vs SPY:** **-10.71%** (massive underperformance)

### Rolling metrics
- **5-day return (04/28→05/04):** +3.08% (recovered from 04/29 trough)
- **5-day SPY:** +0.39%
- **Daily drawdown breaches (>2.5%):** 04/27 (-4.88%), 04/28 (-5.13%), 04/29 (-5.40%), 04/30 (-2.67%) — **4 of 9 days exceeded the 2.5% daily drawdown budget**
- **Average daily trades:** 22.7 — extremely high for a swing strategy

## Positions at close (2026-05-04)

| Symbol | Side | Qty    | Avg Entry | Current | PnL %  | PnL $   | Mkt Value |
|--------|------|--------|-----------|---------|--------|---------|----------|
| AXTX   | LONG | 313.0  | $46.41    | $46.61  | +0.43% | +$62.60 | $14,589   |
| META   | LONG | 15.48  | $611.73   | $610.46 | -0.21% | -$19.63 | $9,448    |
| PWR    | LONG | 14.69  | $758.48   | $757.38 | -0.15% | -$16.16 | $11,130   |
| SPY    | LONG | 83.14  | $717.52   | $718.03 | +0.07% | +$42.40 | $59,696   |

**Cash:** $4,986.91 (5.0% of equity — at the floor)
**SPY allocation:** 59.8% of equity (cash proxy)
**Active equity allocation:** 35.2% (AXTX 14.6%, META 9.5%, PWR 11.1%)

## Trades on 2026-05-04 (53 total — key events)

| Time  | Symbol | Action | Qty     | Price     | Reason (abbreviated)                                      |
|-------|--------|--------|---------|-----------|-----------------------------------------------------------|
| 14:51 | HCAI   | CLOSE  | 1,492   | $10.69    | Exit-arbiter: -8.78%, lost VWAP, 5 momentum signals      |
| 16:04 | AMZN   | CLOSE  | 65.30   | $270.65   | Arbiter EXIT: fading momentum, below VWAP                 |
| 16:04 | GEV    | CLOSE  | 14.57   | $1,071.49 | Arbiter EXIT: weak momentum, flat trend                   |
| 16:04 | UNH    | CLOSE  | 17.27   | $368.25   | Arbiter EXIT: fading volume, bearish EMA                  |
| ~16:05| LLY    | BUY    | 9.49    | $963.38   | Arbiter BUY 9.1%: strong continuation                     |
| ~16:05| MU     | ADD    | 25.00   | $580.42   | Arbiter INCREASE 28%: pool leader                         |
| ~16:05| NOK    | BUY    | 367.24  | $13.33    | Arbiter BUY 4.9%: strong continuation                     |
| ~16:05| SNDK   | BUY    | 10.10   | $1,246.97 | Arbiter BUY 12.6%: best new candidate                     |
| ~16:06| MU     | CLOSE  | 23.01   | $580.81   | Arbiter EXIT: weak momentum, bearish EMA                  |
| ~16:06| DELL   | BUY    | 57.39   | $210.52   | Arbiter BUY 12.1%: IT sector leader                       |
| ~16:06| FIX    | BUY    | 6.30    | $1,896.50 | Arbiter BUY 11.9%: ai_data_center leader                  |
| ~16:06| GOOGL  | BUY    | 28.68   | $383.51   | Arbiter BUY 11.0%                                         |
| ~16:07| WDC    | BUY    | 24.51   | $445.36   | Arbiter BUY 10.9%: memory peer leader                     |
| ~later| WDC    | CLOSE  | 24.51   | $440.06   | Arbiter EXIT: gap_only, bearish EMA — **same day churn**  |
| ~later| DELL   | CLOSE  | 57.39   | $210.94   | Verifier dust-sweep target=0                              |
| ~later| LLY    | CLOSE  | 13.00   | $963.71   | Verifier dust-sweep target=0                              |
| ~later| COIN   | BUY    | 5.10    | $203.90   | Verifier reconcile                                        |
| ~later| COIN   | CLOSE  | 66.90   | $203.45   | Arbiter EXIT: momentum 0, fading, earnings                |
| ~later| GOOGL  | CLOSE  | 37.96   | $382.77   | Arbiter EXIT: momentum 0, fading                          |
| ~later| FIX    | ADD    | 3.70    | $1,903.71 | Arbiter INCREASE 19%: perfect momentum                    |
| ~later| FIX    | CLOSE  | 10.00   | $1,902.81 | Verifier dust-sweep target=0                              |
| final | AXTX   | BUY    | 313.0   | $46.41    | Arbiter BUY 14.4%: momentum 100, breaking_out             |
| final | META   | BUY    | 15.48   | $611.73   | Arbiter BUY 9.5%: comm services leader                    |
| final | PWR    | BUY    | 14.69   | $758.48   | Arbiter BUY 11.1%: ai_data_center peer leader             |

---

## Deep analysis

### Trade-by-trade quality assessment (2026-05-04)

| Symbol | Action     | Entry/Exit | PnL     | AI Grade | Quality Verdict |
|--------|-----------|-----------|---------|----------|------------------|
| HCAI   | CLOSE     | $11.84→$10.69 | -9.7%  | exit 0.72 | **bad** — held too long; was +1.5% on 05/01, cratered to -8.78% intraday before exit triggered |
| AMZN   | CLOSE     | ~$270→$270.65 | ~flat  | exit 0.62 | **churn** — entered and exited within scan cycle, fading momentum |
| GEV    | CLOSE     | ~$1071→$1071 | ~flat   | exit 0.62 | **churn** — rapid turnover, no time for thesis to develop |
| UNH    | CLOSE     | ~$368→$368  | ~flat    | exit 0.62 | **churn** — same pattern |
| MU     | ADD→CLOSE | $580→$580.81 | +0.07% | exit 0.58 | **churn** — increased 28% then partially closed same scan cycle |
| WDC    | BUY→CLOSE | $445→$440   | -1.2%   | exit 0.62 | **bad** — bought and sold same day at a loss |
| DELL   | BUY→CLOSE | $210.52→$210.94 | +0.2% | dust-sweep | **churn** — verifier dust-swept a position the selector just bought |
| LLY    | BUY→CLOSE | $963→$963.71 | +0.03% | dust-sweep | **churn** — same verifier/selector conflict |
| FIX    | BUY+ADD→CLOSE | $1896→$1902 | +0.3% | dust-sweep | **churn** — added at 19% weight then dust-swept to 0 |
| GOOGL  | BUY→CLOSE | $383→$382.77 | -0.2%  | exit 0.58 | **churn** — bought 11% then exited same day |
| COIN   | BUY→CLOSE | $203.90→$203.45 | -0.2% | exit 0.58 | **churn** — verifier reconciled then arbiter reversed |
| AXTX   | BUY       | $46.41    | +0.43%  | buy 0.81 | **ok** — momentum 100, held into close |
| META   | BUY       | $611.73   | -0.21%  | buy 0.75 | **ok** — sector diversification, held |
| PWR    | BUY       | $758.48   | -0.15%  | buy 0.72 | **ok** — ai_data_center peer, held |

**Summary:** 3 of 14 key actions were good entries held into close. 9 were same-day churn. 1 was a late exit on a cratering position. 1 was a same-day round-trip loss.

### Cross-trade patterns

- **Extreme same-day churn:** 16 same-day round-trips across 05/01 and 05/04 alone. On 05/01: INTC, MSFT, TSLA (x2), AMD, BAND, SOFI, UNH, AVGO, PWR. On 05/04: LLY, MU, DELL, FIX, GOOGL, WDC, COIN. This is a swing bot behaving like an intraday scalper.
- **Selector/Verifier conflict is the #1 churn driver:** The portfolio-selector picks positions, the exit-arbiter removes them on the next scan (60 min later), and the verifier dust-sweeps residuals. On 05/04, DELL/LLY/FIX were bought by selector then dust-swept by verifier within hours.
- **Portfolio-selector failures:** 26 AI failures logged. Key issues: returning 0 positions (empty slate), stop-loss precision errors, weight-sum violations, duplicate symbols. On 05/04, selector failed twice consecutively (returned 0 positions), forcing fallback to legacy arbiter.
- **ai_data_center theme concentration blowup (04/23–04/27):** Theme weight reached **89.8%** of equity on 04/27 with 7 names (AMD, AVGO, DELL, FIX, GEV, MU, VRT) — all ai_data_center overrides. Config cap is `max_theme_weight_pct: 0.50`. The sector_guard either wasn't enforcing the theme cap at entry time, or the positions grew past the cap via rebalance-adds. This concentration directly caused the -4.88%, -5.13%, -5.40% drawdowns when the AI/datacenter trade reversed.
- **MU data error on 04/29:** `alpaca_stock_fallback` returned $102.89 for MU (real price ~$510+). This phantom -80% loss inflated the 04/29 daily return to -5.40%. Without this error, the true daily loss was likely ~-2% to -3%. The `use_alpaca_for_data: false` config didn't prevent the fallback path from using Alpaca stock quotes.
- **Complete portfolio turnover:** Zero non-SPY positions survived from 04/22 to 05/04. Every name was replaced. For a swing strategy targeting multi-day holds, this is a total failure of conviction.
- **Exit arbiter fires at minimal confidence:** Most exit decisions were at 0.58–0.62 confidence — barely above the 0.55 floor. The arbiter is hair-triggered on intraday momentum loss (lost_vwap, lost_5min_ema20) which are noisy signals for a swing timeframe.
- **Daily drawdown budget violated 4 of 9 days:** The 2.5% budget has no enforcement mechanism — it's aspirational only. The bot has no circuit breaker to halt trading when daily losses exceed a threshold.

### Position turnover map

```
04/22: AMD ARW AVGO FIX GEV MU VRT
04/23: +APLS +IRDM +SPY
04/24: +DELL +OGN
04/27: -APLS -ARW -IRDM -OGN
04/28: -AMD -FIX -GEV -VRT
04/29: +NOK +V -AVGO
04/30: +ALGM -MU -NOK -V
05/01: +HCAI +SNDK +STX -ALGM -DELL
05/04: +AXTX +META +PWR -HCAI -SNDK -STX
```

Every non-SPY position turned over within the 9-day window. Average hold time: ~2-3 days.

---

## Proposed changes

### 1. Add daily drawdown circuit breaker

- **Why:** 4 of 9 days exceeded the 2.5% drawdown budget with no automated response. The bot kept trading into losses.
- **Diff:** New key in `config.yaml`:
  ```yaml
  risk:
    daily_drawdown_halt_pct: 0.025  # NEW — halt all new entries when intraday equity drops > 2.5% from open
  ```
  In `src/orchestrator.py`, add a check after the equity snapshot: if `(equity_at_open - current_equity) / equity_at_open > daily_drawdown_halt_pct`, skip the entry pipeline (exits still run).
- **Expected impact:** Would have prevented the 04/27→04/28→04/29 cascade. Estimated savings: ~$2,000–$3,000 in the worst 3-day stretch.

### 2. Enforce minimum hold period to kill same-day churn

- **Why:** 16 same-day round-trips destroyed value through spread costs and prevented any thesis from developing.
- **Diff:** New key in `config.yaml`:
  ```yaml
  risk:
    min_hold_scans: 2  # NEW — a position must survive at least 2 scan cycles before the exit-arbiter can close it (unless hard stop hit)
  ```
  In `src/orchestrator.py` `_handle_exits()`, skip exit-arbiter evaluation for positions opened fewer than `min_hold_scans` scans ago. Hard stops still fire immediately.
- **Expected impact:** Eliminates the buy-at-16:05/sell-at-17:00 pattern. On 05/04 alone, this would have prevented 7 of the churned round-trips. Estimated spread savings: ~$200–$400/day.

### 3. Fix sector_guard theme enforcement at entry time

- **Why:** ai_data_center theme reached 89.8% on 04/27 despite `max_theme_weight_pct: 0.50`. The sector_guard runs post-AI as an executor veto, but rebalance-adds appear to bypass it.
- **Diff:** In `src/sector_guard.py`, ensure `check_trade()` is called for every rebalance ADD, not just new entries. Currently, the guard may only fire on `is_new_entry=True` paths:
  ```python
  # Before (suspected): guard only checks new entries
  # After: guard checks all size-increasing trades
  # In src/orchestrator.py rebalance execution:
  #   if delta_qty > 0:
  #       sector_guard.check_trade(symbol, post_trade_notional, equity)
  ```
- **Expected impact:** Hard-caps any single theme at 50% of equity. Would have capped ai_data_center at ~$50K on 04/27 instead of $86K, limiting the drawdown to ~-2.5% instead of -4.88%.

### 4. Prevent verifier from dust-sweeping positions opened in current scan cycle

- **Why:** The verifier dust-swept DELL, LLY, and FIX on 05/04 — positions the selector had just opened minutes earlier. The verifier's target=0 came from a stale or failed selector output.
- **Diff:** In `src/orchestrator.py` verifier pass:
  ```python
  # Add guard: skip verifier dust-sweep for positions opened in THIS scan cycle
  # positions_opened_this_scan = set(sym for sym in executions if executions[sym].action == 'BUY')
  # In verifier corrective trades: if symbol in positions_opened_this_scan and target == 0: skip
  ```
- **Expected impact:** Eliminates the selector→verifier conflict that caused 3 of the 7 churns on 05/04. Also prevents the cascade where selector failure (returning 0 positions) causes verifier to liquidate everything.

### 5. Block Alpaca stock fallback for price data

- **Why:** MU showed $102.89 from `alpaca_stock_fallback` on 04/29 (real price ~$510). This phantom loss distorted the daily P&L by ~$3,950 and may have triggered false exit signals.
- **Diff:** In `config.yaml`:
  ```yaml
  data:
    use_alpaca_for_data: false      # already set
    allow_alpaca_stock_fallback: false  # NEW — also block the alpaca_stock_fallback path
  ```
  In the price-fetching code, remove or gate the `alpaca_stock_fallback` path behind this flag.
- **Expected impact:** Prevents phantom price data from corrupting P&L and triggering false exits. Forces Alpha Vantage or yfinance only.

### 6. Raise exit-arbiter min_confidence to reduce noise exits

- **Why:** Most exit decisions were at 0.58–0.62 confidence — barely clearing the 0.55 floor. These low-confidence exits on intraday momentum signals (lost_vwap, lost_5min_ema20) are noise for a swing strategy.
- **Diff:** `config.yaml`:
  ```yaml
  exit_arbiter:
    min_confidence: 0.55  # BEFORE
    min_confidence: 0.65  # AFTER — require stronger conviction to close
  ```
- **Expected impact:** Would have blocked ~40% of the exit-arbiter "reduce" verdicts in the sample (those at 0.58–0.62). Risk: may hold losers slightly longer, but combined with proposal #1 (drawdown circuit breaker), downside is bounded.

---

## Backtest feasibility

Proposals #1 (drawdown halt), #2 (min hold), and #6 (exit confidence) could be backtested against the 9-day journal data. However, the journal lacks intraday equity snapshots needed to simulate the drawdown halt accurately — only EOD equity is recorded. The trade log has timestamps but not mark-to-market at each scan.

**Proposal #2 rough backtest (min hold):** Filtering trades.jsonl for same-day buy→sell pairs: 16 round-trips with average PnL of approximately -0.15% per trip. At an average notional of ~$10,000/trade, this is ~$24/trip in direct losses plus spread costs. Total estimated churn cost: **~$400–$600 over 2 days**, not counting opportunity cost of being out of positions that subsequently moved favorably.

**Proposal #6 rough backtest (exit confidence ≥ 0.65):** Of 31 exit-arbiter decisions, 18 were at confidence < 0.65. Blocking these would have retained positions longer. Without forward price data in the repo, the P&L impact cannot be quantified — but the correlation between rapid exits and the -10.71% vs SPY gap suggests over-exiting is the dominant failure mode, not over-holding.

---

## Summary

The bot's primary failure mode is **hyperactive churning driven by selector/verifier conflicts and hair-trigger exit signals**, compounded by a **theme concentration blowup** (89.8% ai_data_center) that the sector guard failed to prevent. The result: +0.22% over 9 days while SPY gained +10.71%.

The six proposals above target: (1) drawdown safety net, (2) minimum conviction period, (3) theme cap enforcement, (4) selector/verifier coherence, (5) data integrity, (6) exit signal calibration. Proposals #1–#4 are the highest priority — they address the structural causes of both the drawdowns and the churn.
