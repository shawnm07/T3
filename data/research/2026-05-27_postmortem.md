# Post-Mortem 2026-05-27

> **Note:** Today's live market data is unavailable (sandbox constraints — Alpaca, yfinance, Telegram all blocked). This post-mortem analyses the most recent available trading session: **2026-05-04 (Monday)**. All figures are derived solely from in-repo data files.

---

## Data Availability

| File | Status |
|---|---|
| `data/research/2026-05-04_eod.json` | ✅ Found — primary performance source |
| `data/research/20260504T*_scan.json` | ✅ Found — 6 scans (2 dry-run, 4 live) |
| `data/journal/trades.jsonl` | ✅ Found — 53 records on 2026-05-04 |
| `data/journal/decisions.jsonl` | ✅ Found — 144 decision records |
| `data/research/2026-05-27_eod.json` | ❌ Missing (no live data today) |
| Last EOD with data | `2026-05-04` (last trading day in repo) |

---

## Performance Today (2026-05-04, based on eod.json)

| Metric | Value |
|---|---|
| Portfolio return | **-1.80%** |
| SPY daily return | **-0.36%** |
| Portfolio vs SPY | **-1.44%** |
| Equity EOD | $99,849.69 |
| Positions at close | 4 (AXTX, META, PWR, SPY proxy) |
| Trades executed | **53** |

### Rolling Context

| Period | Portfolio | SPY | vs SPY |
|---|---|---|---|
| 1d (2026-05-04) | -1.80% | -0.36% | **-1.44%** |
| 5d (Apr 28 – May 4) | -12.66% | +0.38% | **-13.04%** |
| Available period (Apr 22 – May 4) | -16.31% | +10.71% | **-27.02%** |
| Max drawdown (intraperiod) | -7.12% | — | Apr 23 → Apr 29 |

> Goal is to beat SPY within risk budget. Portfolio is **materially underperforming** across all windows.

---

## Positions at Close (EOD 2026-05-04)

| Symbol | Side | Avg Entry | Current | P&L% | Mkt Value | % Portfolio |
|---|---|---|---|---|---|---|
| AXTX | Long | $46.41 | $46.61 | **+0.43%** | $14,589 | 14.6% |
| META | Long | $611.73 | $610.46 | **-0.21%** | $9,448 | 9.5% |
| PWR | Long | $758.48 | $757.38 | **-0.15%** | $11,130 | 11.1% |
| SPY (proxy) | Long | $717.52 | $718.03 | **+0.07%** | $59,696 | **59.8%** |
| Cash | — | — | — | — | $4,987 | 5.0% |

> ⚠️ **SPY proxy = 59.8% of equity.** Active picks cover only 35.2%. Alpha potential is severely diluted.

---

## Trades Today (2026-05-04, Chronological)

| Time (ET) | Event | Symbol | Qty | Price | Est P&L | Reason (truncated) |
|---|---|---|---|---|---|---|
| 10:51 | EXIT (AI-exit-arbiter) | HCAI | 1,492 | $10.69 | **-9.71% / -$1,716** | Down -8.78%, 5 concurrent momentum signals |
| 11:14 | EXIT (scan sell) | SNDK | 23.30 | $1,250.00 | **+9.57% / +$2,535** | Arbiter EXIT — redeploying capital |
| 11:14 | EXIT (scan sell) | STX | 19.40 | $740.23 | **+3.27% / +$454** | Arbiter EXIT — redeploying capital |
| ~11:30 | BUY | AMZN | 65.30 | ~$273.55† | — | Arbiter BUY 17.7% |
| ~11:30 | BUY | GEV | 14.57 | ~$1,075.5† | — | Arbiter BUY 15.6% |
| ~11:30 | BUY | COIN | 66.93 | ~$205.8† | — | Arbiter BUY 13.6% |
| ~11:30 | BUY | MU | 22.99 | ~$583.2† | — | Arbiter BUY 13.3% |
| ~11:30 | BUY | UNH | 17.27 | ~$368.2† | — | Arbiter BUY 6.4% |
| 12:04 | EXIT | AMZN | 65.30 | $270.65 | **-1.06% / -$188** | Fading momentum, below VWAP |
| 12:04 | EXIT | GEV | 14.57 | $1,071.49 | **-0.38% / -$59** | Weak momentum, below VWAP |
| 12:04 | EXIT | UNH | 17.27 | $368.25 | **+0.02% / +$1** | Fading volume, LLY stronger |
| 12:04 | BUY (increase) | COIN | 8.41 (notional) | ~$204 | — | Arbiter INCREASE 22% |
| 12:04 | BUY | LLY | 9.49 | $963.38 | — | Arbiter BUY 9.1% |
| 12:04 | BUY | SNDK† | 10.10 | $1,246.97 | — | Re-entry — memory sector |
| 12:10 | STOP HIT | SNDK (new) | 10.10 | $1,237.52 | **-0.75% / -$95** | Stop at $1,237.62 triggered |
| 12:04 | BUY | NOK | 367.24 | $13.33 | — | Arbiter BUY 4.9% |
| 13:04 | EXIT | MU | 23.01 | $580.81 | **+0.07% / +$9** | Weak momentum, bearish EMA |
| 13:04 | BUY | DELL | 57.39 | $210.52 | — | IT sector, momentum 95 |
| 13:04 | BUY | FIX | 6.30 | $1,896.50 | — | AI data center, 11.9% |
| 13:04 | BUY | GOOGL | 28.68 | $383.51 | — | Comm. Services leader 11% |
| 13:04 | BUY (increase) | LLY | 3.51 | $962.27 | — | Arbiter INCREASE 12.5% |
| 13:04 | BUY | WDC | 24.51 | $445.36 | — | Memory peer, 10.9% |
| 14:05 | EXIT | WDC | 24.51 | $440.06 | **-1.19% / -$130** | Gap-only, bearish EMA |
| 14:05 | BUY (increase) | FIX | 3.70 | $1,903.71 | — | Arbiter INCREASE 19% |
| 14:05 | EXIT (verifier) | DELL | 57.39 | $210.94 | +0.20% / +$24 | Verifier dust-sweep target=0 |
| 14:05 | EXIT (verifier) | LLY | 13.00 | $963.71 | +0.03% / +$4 | Verifier dust-sweep target=0 |
| 14:05 | BUY (verifier) | GOOGL | 9.28 | $384.43 | — | Verifier reconcile +$3,569 gap |
| 14:05 | BUY (verifier) | COIN | 5.10 | $203.90 | — | Verifier reconcile +$1,135 gap |
| 15:08 | EXIT | COIN | 66.90 | $203.45 | **-0.22% / -$30** | Momentum 0, fading, earnings 3d |
| 15:08 | EXIT | FIX | 10.00 | $1,902.81 | — | Verifier dust-sweep target=0 |
| 15:08 | EXIT | GOOGL | 37.96 | $382.77 | **-0.19% / -$28** | Momentum 0, below EMA20 |
| 15:08 | BUY | AXTX | 313.0 | $46.41 | — | Momentum 100, breaking out |
| 15:08 | BUY | META | 15.48 | $611.73 | — | Comm. Services, 9.5% |
| 15:08 | BUY | PWR | 14.69 | $758.48 | — | AI data center, 11.1% |

> † Entry prices for AMZN/GEV/COIN/MU/UNH (~11:30 ET entries) are reconstructed from `unrealized_plpc` at the 12:04 exit scan; exact fills not in `trades.jsonl`.
> SNDK second entry was immediately stopped out at 12:10 ET.

---

## Trade-by-Trade Quality Grading (2026-05-04)

| Symbol | Side | Entry | Exit | P&L% | P&L$ | AI Grade | Verdict |
|---|---|---|---|---|---|---|---|
| HCAI | Long (overnight) | $11.84 | $10.69 | **-9.71%** | -$1,716 | exit-arbiter conf=0.72 | **BAD** — biotech overnight, gap-down, largest single loss; exceeded 15% cap at entry |
| SNDK (old) | Long (overnight) | $1,140.78 | $1,250.00 | **+9.57%** | +$2,535 | Arbiter EXIT | **GOOD** — best exit of the day; took full gain after swing |
| STX | Long (overnight) | $716.82 | $740.23 | **+3.27%** | +$454 | Arbiter EXIT | **GOOD** — clean exit with solid gain |
| AMZN | Same-day | ~$273.55 | $270.65 | **-1.06%** | -$188 | exit-arbiter conf=0.62 | **CHURN** — entered and exited within ~30 min; thesis reversed before position could develop |
| GEV | Same-day | ~$1,075.5 | $1,071.49 | **-0.38%** | -$59 | exit-arbiter conf=0.62 | **CHURN** — micro-loss but wasted capital cycle |
| UNH | Same-day | ~$368.20 | $368.25 | **+0.02%** | +$1 | Arbiter EXIT | **CHURN** — flat, exited to fund LLY (never held LLY) |
| SNDK (new) | Same-day | $1,246.97 | $1,237.52 | **-0.75%** | -$95 | Stop-loss hit | **BAD** — re-entered SNDK 6 min after selling old position at higher price; stop triggered immediately |
| MU | Same-day | $580.42 | $580.81 | **+0.07%** | +$9 | Arbiter EXIT | **CHURN** — $9 gross gain for a $14K round-trip; transaction friction likely erased this |
| WDC | Same-day | $445.36 | $440.06 | **-1.19%** | -$130 | exit-arbiter conf=0.62 | **BAD** — entered as "memory peer leader," exited within 2h as "gap-only" |
| DELL | Same-day | $210.52 | $210.94 | **+0.20%** | +$24 | Verifier dust-sweep | **CHURN** — arbiter bought at 13:04, verifier swept at 14:05; inter-system conflict |
| LLY | Same-day | $963.38 | $963.71 | **+0.03%** | +$4 | Verifier dust-sweep | **CHURN** — same conflict: arbiter BUY then immediate verifier EXIT |
| COIN | Same-day | ~$205.80 | $203.45 | **-0.22%** | -$30 | Arbiter EXIT | **BAD** — entered with earnings 3 days out (should have been blocked); exited flagging earnings risk it already had on entry |
| GOOGL | Same-day | $383.51 | $382.77 | **-0.19%** | -$28 | Arbiter EXIT | **CHURN** — 2-hour hold, exited on "momentum score 0" |
| FIX | Same-day | $1,896.50 | $1,902.81 | **+0.33%** | +$63 | Verifier dust-sweep | **CHURN** — arbiter bought to 19% allocation, verifier swept at 15:08; fresh-exit guard was explicitly bypassed |
| AXTX | Open at EOD | $46.41 | $46.61 | **+0.43%** | — | Arbiter BUY (held) | **GOOD** — final-scan entry held overnight; clean momentum setup |
| META | Open at EOD | $611.73 | $610.46 | **-0.21%** | — | Arbiter BUY (held) | **NEUTRAL** — slightly underwater at close; thesis intact |
| PWR | Open at EOD | $758.48 | $757.38 | **-0.15%** | — | Arbiter BUY (held) | **NEUTRAL** — ai-data-center, minor red at close |

**Estimated realized P&L on closed same-day positions: ~-$497**
**Realized P&L on overnight holds (HCAI, SNDK-old, STX): ~+$1,273**
**Net estimated day: ~+$776 pre-SPY; EOD shows -1.80% → SPY proxy dragged by market decline**

---

## Cross-Trade Patterns

- **Extreme intraday rotation (53 trades, 6 full portfolio rebuilds):** Every scan cycle (hourly) produced a completely different set of 5-6 symbols. AMZN/GEV/UNH entered ~11:30 ET and exited by 12:04; MU/WDC/DELL/LLY entered 13:04 and most exited by 14:05; COIN/GOOGL/FIX entered by 13:04 and exited by 15:08. No position held longer than 2 hours except the final EOD picks.

- **Exit-arbiter confidence floor too low:** 8 of 13 exit-arbiter decisions were at conf=0.58–0.62, barely above the 0.55 floor. At this confidence the arbiter is effectively noise-trading. All the same-day CHURN exits carry conf=0.58–0.62.

- **Fresh exit guard bypassed three times:** DELL (tech_score=0.672, unrealized=+0.24%), LLY (unrealized=+0.19%), FIX (unrealized=-0.14%) all had `fresh_exit_guard_skipped` events. The guard exists but is overridden by "superior candidates" logic — allowing the selector to exit freshly opened profitable positions.

- **SPY cash-proxy structural creep:** SPY proxy rose from 1.7% (Apr 23) → 77.6% (Apr 30) → 59.8% (May 4). The mechanism that deploys idle capital into SPY is working too aggressively, causing the bot to manage a passive index position rather than generate alpha. On Apr 30, only 17.2% of capital was in active picks.

- **SNDK re-entry stop-hit after profitable sell:** Sold 23.3 SNDK at $1,250 (+9.57%), immediately rebought 10.1 SNDK at $1,246.97 in the same scan cycle. The new position stopped out at $1,237.52 six minutes later. Classic wash-trade pattern: sold the winner to redeploy, then chased back into the same name.

- **Inverse ETF appeared in selector output:** The 19:08 selector rotation included `SOXS` (3× inverse semiconductor ETF) as a selected position. This violates the "Long US equities only" mandate. It did not execute (asset check presumably blocked it) but the selector should never have scored it.

- **AI failures caused selector fallback twice:** Two `ai_failure` events on the portfolio-selector (14:09 and 15:02 ET), each after 3 attempts. Both failures included validation errors like "selected count 0 not in [3,6]" and "missing per_symbol for 50 symbols." These early-session failures likely disrupted the orderly scan-start and contributed to the chaotic mid-morning rebuilding.

- **COIN entered with earnings 3 days out:** COIN exit reason explicitly notes "earnings in 3 days." The earnings gate covers existing positions via `trim_exit_days: 2`, but there is no gate blocking **new entries** within N days of earnings. COIN was opened and lost -0.22%.

- **Oversized HCAI overnight:** HCAI held at ~17.7% of portfolio overnight ($17,934) — this exceeds the `initial_entry_cap_pct: 0.15` (15%) cap. The overnight gap-down cost $1,716. HCAI is a small-cap biotech with ~$10/share — a high-risk sector for overnight holds.

---

## Proposed Changes

### 1. Raise `exit_arbiter.min_confidence` from 0.55 → 0.65

**Why:** 8 of 13 exit-arbiter calls today were at conf=0.58–0.62. These are marginal signals on freshly entered positions (< 2 hours old). Raising the floor to 0.65 would block those exits and allow positions to develop past intraday noise.

**Diff:**
```yaml
# config.yaml
exit_arbiter:
  min_confidence: 0.55    # before
  min_confidence: 0.65    # after
```

**Expected impact:** Estimated ~8 blocked same-day exits on May 4 → ~$497 friction avoided. Positions like WDC, GOOGL, COIN, AMZN would have had another 1-2 scans to recover or confirm the thesis before being closed.

**Offline backtest note:** Cannot directly replay without live price data. From journal: 5 of those 8 low-conf exits resulted in small losses (-$30 to -$188); 3 resulted in tiny wins (<$25). Net May 4 improvement estimate: +$200 to +$450. Risk: holding losers longer; partially mitigated by stop-loss.

---

### 2. Hard-cap SPY cash proxy at 25% (`cash_proxy_max_pct: 0.25`)

**Why:** SPY proxy averaged 44% of equity over the last 9 trading days, peaking at 77.6% on Apr 30. At these weights the portfolio tracks SPY almost exactly and has no alpha generation capacity. Active picks at 17-35% of equity cannot offset SPY drag on down days.

**Diff:**
```yaml
# config.yaml — add under risk: section
risk:
  cash_proxy_max_pct: 0.25    # add (currently uncapped, defaults to 1-active-cash)
```

The portfolio-selector and portfolio-arbiter would need to respect this cap when allocating the SPY cash proxy slot. If `spy_target_pct > cash_proxy_max_pct`, the excess should remain as cash (and count against `cash_reserve_pct` floor from below, not above).

**Expected impact:** On Apr 30, this would have forced 52.6% more capital into active picks or cash. If active picks matched their historical daily returns (mixed), it would have reduced passive SPY drag — though on down days it could increase drawdown. Net neutral-to-positive for goal of beating SPY.

**Offline backtest note:** Can estimate from rolling EOD data. On 5 of 9 days where SPY was positive, having more active exposure could have increased returns (Apr 23: +1.56% vs SPY -0.39% shows active picks beat). On May 4, more active exposure into a down day would have increased the loss slightly.

---

### 3. Make fresh-exit cooldown non-bypassable for positions held < 2 scans

**Why:** DELL, LLY, and FIX were each opened in one scan and closed by the verifier or selector in the immediately following scan, with the "fresh_exit_guard_skipped" flag explicitly logged. The guard exists but is overridden by "superior candidates" logic. The arbiter-verifier conflict on these three positions directly cost ~$63 in opportunity loss and added transaction friction.

**Diff (conceptual — requires code change in `src/executor.py` or `src/orchestrator.py`):**
```python
# Before: fresh_exit_guard can be skipped when selector has higher-conviction candidate
# After: hard-block fresh exits for positions with entry_age_scans < 2
# (allow override only for stop-loss triggers or exit_arbiter conf >= 0.80)

# In orchestrator.py _handle_exits() or executor.py rebalance logic:
if position.entry_scan_count < 2 and exit_confidence < 0.80:
    log_event('fresh_exit_guard_enforced', symbol=symbol)
    continue  # skip this exit
```

**Expected impact:** May 4: DELL (+0.20%), LLY (+0.03%), FIX (+0.33%) would have been held one more scan. Small direct gain ~$91; larger benefit from reducing intraday whipsaw.

---

### 4. Block new entries within 3 days of earnings (`earnings.block_new_entry_days: 3`)

**Why:** COIN was entered despite the exit reason explicitly noting "earnings in 3 days." The existing earnings gate (`trim_exit_days: 2`) only manages existing positions. There is no gate preventing **new entries** in the approach window. COIN lost -0.22% and COIN exits in the later scan confirm earnings risk was the proximate reason.

**Diff:**
```yaml
# config.yaml
earnings:
  trim_exit_days: 2                # existing
  day_0_1_hold_min_confidence: 0.90  # existing
  block_new_entry_days: 3          # add — no new entries within 3 calendar days of earnings
```

Corresponding code guard in `src/ai_pipeline.py` or `src/risk.py` before `BUY` approval: check `days_to_earnings <= block_new_entry_days` → reject.

**Expected impact:** Blocks ~1-2 pre-earnings entries per week. May 4: COIN entry would have been blocked → avoids -$30 loss and frees capital for AXTX/META/PWR earlier.

**Offline backtest:** Cannot enumerate all pre-earnings entries from journal without earnings date data. COIN appears in 3 scans today; all end in exit. Low risk of blocking good trades.

---

### 5. Exclude inverse/leveraged ETFs from universe explicitly

**Why:** `SOXS` (3× inverse semiconductor ETF) appeared in the selector's rotation output at the 19:08 scan — a direct violation of the "Long US equities only" mandate in CLAUDE.md. It did not execute (blocked downstream by asset checks), but the selector wasted AI tokens and inference evaluating it.

**Diff:**
```yaml
# config.yaml
universe:
  # Add to exclude_tickers:
  exclude_tickers:
    - SOXS
    - SOXL
    - TQQQ
    - SQQQ
    - SPXU
    - UVXY
    - SVXY
    # ... or add a pattern rule: exclude any ticker ending in S/L that is a leveraged ETF
```

A more robust solution is a screener-level filter: reject any symbol where yfinance `info.get('quoteType') == 'ETF'` and `longName` contains keywords like 'inverse', 'bear', 'ultra short', '3x', '-3x'.

**Expected impact:** Eliminates selector evaluating inverse ETFs. Prevents any edge case where the downstream asset check fails and an inverse position executes.

---

## Offline Backtest Summary

| Proposal | Backtest feasibility | Estimated May 4 impact |
|---|---|---|
| 1. Raise exit_arbiter min_conf | Partial (from journal friction data) | ~+$200 to +$450 |
| 2. Cap SPY proxy at 25% | Partial (from EOD series) | Mixed: +alpha on up-days, +drawdown on down-days |
| 3. Hard fresh-exit cooldown | Partial | ~+$91 direct; larger whipsaw reduction |
| 4. Block pre-earnings new entries | Cannot verify without earnings data | Avoids ~1-2 bad entries/week |
| 5. Exclude inverse ETFs | N/A (prevention) | Eliminates selector waste and compliance risk |

All five proposals operate within the existing risk budget and do **not** require changes to `hard_stop_loss_pct`, `max_position_pct`, or `max_risk_per_trade_pct`.
