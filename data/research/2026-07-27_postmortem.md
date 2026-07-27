# Post-Mortem 2026-07-27

## Data Availability

**Critical: No trading data for 2026-07-27.**

The bot has been silent since **2026-05-04T19:55Z** (~83 calendar days / ~58 trading days). All analysis in this report covers the **last live session: 2026-05-04**, which is also the focus of this post-mortem given it was the final active trading day before the outage.

| Source | Status | Last Entry |
|---|---|---|
| `_eod.json` | ✓ Available | `2026-05-04_eod.json` |
| Intraday scans | ✓ Available | `20260504T190848_scan.json` |
| `trades.jsonl` | ✓ Available | `2026-05-04T19:55:03Z` (204 lines) |
| `decisions.jsonl` | ✓ Available | `2026-05-04T20:15:04Z` (1556 lines) |
| Today's EOD (`2026-07-27_eod.json`) | ✗ MISSING | — |
| Any scan post 2026-05-04 | ✗ MISSING | — |
| Alpaca API | BLOCKED (403) | — |
| yfinance / Alpha Vantage / Twelve Data | BLOCKED (403) | — |

**Root cause candidates (from prior daily reviews):**
1. Trading scheduler (`scripts/scan_and_trade.py`) disabled or silently failing since 2026-05-04.
2. Bot running but writing to a different filesystem / branch not committed to this repo.
3. Alpaca paper account PA34KBGT3V7E may be frozen at the 2026-05-04 state.

---

## Performance — 2026-05-04 (Last Active Session)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| vs SPY (daily) | **-1.43%** |
| Closing equity | $99,849.69 |
| Trades executed | **53** (extremely high for swing cadence) |
| Positions at close | 4 |

### Rolling Context

| Date | Portfolio | SPY | vs SPY | Equity |
|---|---|---|---|---|
| 2026-04-22 | +0.00% | +1.01% | -1.01% | $99,627 |
| 2026-04-23 | +1.56% | -0.39% | +1.95% | $101,208 |
| 2026-04-24 | -0.81% | +0.77% | -1.59% | $99,343 |
| 2026-04-27 | -4.88% | +0.17% | -5.05% | $96,448 |
| 2026-04-28 | -5.13% | -0.49% | -4.65% | $96,867 |
| 2026-04-29 | -5.40% | -0.01% | -5.39% | $93,999 |
| 2026-04-30 | -2.67% | +0.96% | -3.63% | $95,786 |
| 2026-05-01 | +1.82% | +0.29% | +1.53% | $101,101 |
| **2026-05-04** | **-1.80%** | **-0.36%** | **-1.43%** | **$99,850** |

**5-day summary (Apr 28 → May 4):** Portfolio +3.1% vs SPY estimated +0.4% → +2.7% outperformance.
**Period vs SPY (from eod.json):** -10.71% (portfolio significantly underperformed SPY over the measured period).

---

## Positions at Close — 2026-05-04

| Symbol | Side | Qty | Avg Entry | Close Price | P&L % | Market Value | Notes |
|---|---|---|---|---|---|---|---|
| AXTX | LONG | 313 | $46.41 | $46.61 | **+0.43%** | $14,589 | Tradr 2X Long AXTI ETF; entered same session |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** | $9,448 | New entry, starter (70% of target) |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** | $11,130 | New entry, starter (70% of target) |
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** | $59,696 | Cash proxy ~59.8% of portfolio |

**Positions frozen since 2026-05-04.** If Alpaca account shows the same state today (2026-07-27), these four positions have been held unmonitored for 83 days.

---

## Trades — 2026-05-04

53 events logged (11 closes, 15 AI buys/increases, 3 wash-trade recoveries, 24 exit-learning metrics).

### Closes

| Symbol | Qty | Fill Price | Reason |
|---|---|---|---|
| HCAI | 1,492 | $10.69 | Exit-arbiter: down -8.78% |
| AMZN | 65.30 | $270.65 | Arbiter: fading momentum, below VWAP |
| GEV | 14.57 | $1,071.49 | Arbiter: weak momentum, below VWAP |
| UNH | 17.27 | $368.25 | Arbiter: fading volume |
| MU | 23.01 | $580.81 | Arbiter: weak/flat momentum, bearish EMA |
| WDC | 24.51 | $440.06 | Arbiter: gap-only classification, bearish EMA |
| COIN | 66.90 | $203.45 | Arbiter: momentum=0, earnings in 3 days |
| GOOGL | 37.96 | $382.77 | Arbiter: momentum=0, fading, below EMA20 |
| DELL | 57.39 | $210.94 | Verifier dust-sweep (target=0) |
| LLY | 13.00 | $963.71 | Verifier dust-sweep (target=0) |
| FIX | 10.00 | $1,902.81 | Verifier dust-sweep (target=0) |

### Buys / Increases

| Symbol | Action | Qty | Fill Price | Target % | Reason |
|---|---|---|---|---|---|
| LLY | BUY | 9.49 | $963.38 | 9.1% | Strong continuation, bullish EMA |
| MU | INCREASE | 25.00 | $580.42 | 28.0% | Pool leader, perfect momentum |
| NOK | BUY | 367.24 | $13.33 | 4.9% | Strong continuation (later exited same scan) |
| SNDK | BUY | 10.10 | $1,246.97 | 12.6% | Best new candidate |
| DELL | BUY | 57.39 | $210.52 | 12.1% | IT sector leader, score 95 |
| FIX | BUY | 6.30 | $1,896.50 | 11.9% | ai_data_center_power peer leader |
| GOOGL | BUY | 28.68 | $383.51 | 11.0% | Comm Services leader |
| LLY | INCREASE | 3.51 | $962.27 | 12.5% | 120-min cooldown with acceptable cont. |
| WDC | BUY | 24.51 | $445.36 | 10.9% | Memory peer leader vs MU |
| COIN | BUY (verifier) | 5.10 | $203.90 | 14.8% target reconcile | Verifier gap fill |
| FIX | INCREASE | 3.70 | $1,903.71 | 19.0% | Perfect momentum, breaking out |
| GOOGL | BUY (verifier) | 9.28 | $384.43 | 14.6% target reconcile | Verifier gap fill |
| AXTX | BUY | 313.00 | $46.41 | 14.4% | Momentum score 100, breaking_out |
| META | BUY | 15.48 | $611.73 | 9.5% | Comm services, acceptable continuation |
| PWR | BUY | 14.69 | $758.48 | 11.1% | ai_data_center_power, bullish EMA |

---

## Per-Trade Quality Ledger — 2026-05-04

> Source: `trades.jsonl` + `decisions.jsonl`. P&L computed from `avg_entry` / `filled_avg_price` fields — not Alpaca's unrealized_plpc. Grade reflects outcome quality (A–F). "Round-trip" = entered and exited in the same session.

| UTC | Symbol | Action | Qty | Entry | Exit/Price | Realized P&L | AI Conf | Grade | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 14:51 | HCAI | CLOSE | 1,492 | $11.84 | $10.69 | **-$1,716** | 0.72 | F | Gap-down Monday on unexecuted Friday preclose close order. Biggest avoidable loss. |
| 15:13 | SNDK | SELL | 23.30 | $1,140.78 | $1,250.00 | **+$2,545** | — | A | Clean weekend gap-up capture. |
| 15:13 | STX | SELL | 19.40 | $716.82 | $740.23 | **+$454** | — | A- | Good exit near intraday high. |
| 15:18 | AMZN | BUY→SELL | 65.30 | $274.60 | $270.65 | **-$258** | — | F | 50-min round-trip. Bought pressing day high, sold on first fade. |
| 15:18 | GEV | BUY→SELL | 14.57 | $1,093.33 | $1,071.49 | **-$318** | 0.62 | F | 50-min round-trip. Arbiter said HOLD; verifier dust-swept. +$198 missed (60m). |
| 15:18 | UNH | BUY→SELL | 17.27 | $368.14 | $368.25 | **+$2** | — | D | Flat exit. Replaced by LLY which itself was closed 2h later. |
| 16:05 | MU | BUY→SELL | 25.00 | $584.62 | $577.45 | **-$179** | — | F | **3-minute hold.** Next scan EXIT fired before previous scan's fill settled. |
| 16:05 | SNDK | BUY→SELL | 10.10 | $1,246.97 | $1,237.52 | **-$95** | — | F | Re-bought 50 min after selling at $1,250. Round-trip gave back alpha. |
| 16:05 | NOK | BUY→SELL | 367.24 | $13.33 | $13.24 | **-$34** | — | F | Same-session churn. |
| 16:05 | LLY | BUY→SELL | 13.00 | $963.38 | $963.71 | **+$8** | 0.62 | D | Arbiter HOLD. Verifier dust-swept. +$70 missed (60m). |
| 16:05 | DELL | BUY→SELL | 57.39 | $210.52 | $210.94 | **+$24** | — | C | 60-min hold, essentially flat. |
| 17:04 | WDC | BUY→SELL | 24.51 | $445.36 | $440.06 | **-$130** | — | F | Entered "memory peer leader vs MU"; exited "gap-only, bearish EMA" 60 min later. |
| 17:04 | MU | BUY→SELL | 23.01 | $580.42 | $580.81 | **+$9** | — | D | Third MU cycle today. Flat result. |
| 17:04 | FIX | BUY→SELL | 10.00 | $1,898.90 | $1,902.81 | **+$39** | 0.62 | C | Verifier dust-sweep but small profit. Wash-trade recovery triggered. |
| 17:04 | GOOGL | BUY→SELL | 37.96 | $383.51 | $382.77 | **-$28** | — | F | Same-session round-trip. Wash-trade recovery triggered. |
| 17:04 | COIN | BUY→SELL | 66.90 | $203.90 | $203.45 | **-$30** | 0.58 | F | Earnings flagged at 15:18 (REDUCE); overridden at 16:05 (INCREASE); final EXIT at 19:08 citing same earnings flag. |
| 19:08 | AXTX | BUY | 313.00 | $46.41 | ~$46.61 | — | 0.88 | ? | Overnight hold — not graded. **2× leveraged ETF; swing hold inappropriate.** |
| 19:08 | META | BUY | 15.48 | $611.73 | ~$610.46 | — | 0.65 | ? | Overnight starter (70% of target). |
| 19:08 | PWR | BUY | 14.69 | $758.48 | ~$757.38 | — | 0.72 | ? | Overnight starter (70% of target). |

**Grade summary: 2× A/A-, 2× C, 4× D, 9× F.** Session P&L split: overnights from SNDK/STX gap-up saved the day (+$2,999); intraday churn destroyed ~-$1,600 of that.

---

## Cross-Trade Patterns

**1. Selector instability — average Jaccard 0.28 between consecutive scans**
- 6 scans in one session produced 5 portfolio resets. The 18:05→19:08 transition had Jaccard = 0.09 (only PWR survived).
- Every flip costs spread + slippage on both legs. ~$96K notional churned in round-trips, estimated $96–$200 in spread cost alone.
- The 8 proposals from `2026-05-05_daily_review.md` remain open (carried forward 17 cycles). Most relevant: Proposal 1 (selector inertia bonus) and Proposal 8 (reduce to 3× scans/day).

**2. Exit-arbiter monoculture — all 13 calls fired on `intraday_momentum_lost` at 0.58–0.62 confidence**
- The `exit_arbiter.min_confidence: 0.55` floor means any arbiter response ≥0.55 fires an exit.
- 0.58–0.62 is barely above the floor — these are low-conviction exits driving full position closes.
- GEV and LLY received `action=hold` from the exit-arbiter (conf 0.62) but were closed anyway by the verifier dust-sweep logic. The arbiter's HOLD vote was effectively ignored.
- GEV went up $198 in the 60 min after its "hold" was overridden. LLY went up $70 in the same window.

**3. Verifier dust-sweep overriding arbiter HOLDs**
- DELL, LLY, FIX were bought by arbiter BUY signals in one scan, then dust-swept by the verifier in the next scan (target=0) — meaning the selector had already moved on before the verifier ran.
- This creates a guaranteed round-trip: arbiter BUY → selector PASS in next scan → verifier sweep. No hold time whatsoever.
- Total dust-sweep round-trip cost: ~-$35 realized + $268 in missed 60m gains (GEV + LLY).

**4. Earnings-flag bypass (COIN)**
- 15:18 scan: selector REDUCE COIN (earnings flag, 3 days out).
- 16:05 scan: selector INCREASE COIN ("strong continuation") — earnings flag re-evaluated as non-blocking.
- 19:08 scan: EXIT COIN ("momentum 0, earnings in 3 days — entry thesis gone").
- Net result: added $176 in realized losses chasing a name that was already flagged for earnings risk.

**5. Leveraged and inverse ETF exposure**
- AXTX (Tradr 2× Long AXTI Daily ETF) selected as the highest-conviction overnight hold at 14.4% of portfolio.
- SOXS (3× inverse semis ETF) briefly appeared in the 19:08 selector output (`selected_positions: [..., "SOXS"]`) before execution excluded it.
- Leveraged ETFs decay over multi-day holds (daily rebalancing drag). Both contradict the "long US equities only, swing cadence" mandate.
- AXTX has been held unmonitored since 2026-05-04 (83 calendar days). A 2× leveraged ETF on a narrow underlying can diverge substantially over that period.

**6. SPY proxy dominance — 59.8% of portfolio**
- The bot scanned 50 candidates across 6 scans and ended with 59.8% in SPY, 5% cash.
- The effective active portion (AXTX + META + PWR = 35.2%) drove all the intraday friction.
- Against the goal of "beat SPY", holding 60% SPY means the active book must outperform by 2× the tracking error just to match. The active book returned roughly flat on 5/4; SPY position returned +0.07%.

**7. Wash-trade friction (3 occurrences)**
- LLY, FIX, GOOGL all triggered broker wash-trade blocks (code 40310000) when new BUY orders were submitted while outstanding SELL stops were live.
- Each required cancel-and-retry, introducing slippage and partial fill risk.
- Root cause: the executor places standalone stop-market orders after fills, but the next scan's entry for the same symbol sees the stop as an open sell order.

---

## Proposed Changes

> These are proposals only. No config.yaml or src/ files are modified on any branch. The 8 proposals from `2026-05-05_daily_review.md` remain open and are superseded/extended by items 1–5 below.

### Proposal A: Hard minimum-hold timer with high-confidence override *(extends prior Proposal 3)*

**Why:** MU held 3 minutes; AMZN/GEV/UNH held 50 minutes; all entered and exited in the same session. These are selector-flip exits, not thesis breaks. The exit-arbiter said HOLD for GEV and LLY but the selector overrode it.

**Diff:**
```yaml
# config.yaml
exit_arbiter:
  min_confidence: 0.55          # current
  min_hold_minutes: 90          # NEW — block non-stop exits < 90 min after entry fill
  min_hold_override_confidence: 0.87  # NEW — allow early exit only at high conviction
```
```python
# src/orchestrator.py _handle_exits():
# Before calling exit-arbiter, check position age:
hold_minutes = (now - position.opened_at).total_seconds() / 60
if hold_minutes < config.exit_arbiter.min_hold_minutes:
    if ai_confidence < config.exit_arbiter.min_hold_override_confidence:
        log.info(f"Skipping exit for {sym}: held only {hold_minutes:.0f}m (< {config.exit_arbiter.min_hold_minutes}m min)")
        continue
```

**Expected impact:** Eliminates 3-minute (MU) and sub-60-minute (AMZN, GEV, UNH, WDC) round-trips that cost ~-$985 on 5/4. Stops protecting: still enforced. Estimated $400–$900/day friction savings on active scan days.

**Backtest:** Not run (requires per-position timestamps across sessions; journal has `exit_time` but not `entry_time` consistently). Directional analysis: 7 same-day round-trips on 5/4, all would have been blocked. Net round-trip P&L was -$88; combined with opportunity cost (GEV +$198 60m, LLY +$70 60m) = ~$356 avoidable on a single session.

---

### Proposal B: Session-level earnings BUY lockout *(extends prior Proposal 2)*

**Why:** COIN was flagged for earnings risk at 15:18 (REDUCE) then re-entered at 16:05 (INCREASE "strong continuation"). The earnings flag was recomputed per-scan and overwritten by momentum signal. Final exit at 19:08 cited the same earnings flag. Net: -$176 realized loss + broker friction.

**Diff:**
```yaml
# config.yaml
earnings:
  intraday_buy_lockout: true   # NEW
  intraday_lockout_scope: [BUY, INCREASE]
```
```python
# src/orchestrator.py: at session start, initialize set
_earnings_locked_today: set[str] = set()

# When selector proposes REDUCE/EXIT due to earnings:
_earnings_locked_today.add(symbol)

# In execution gate:
if symbol in _earnings_locked_today and action in ('BUY', 'INCREASE'):
    log.info(f"Skipping {action} {symbol}: earnings lockout active this session")
    continue
```

**Expected impact:** Eliminates same-session earnings flip-flop. On 5/4, would have prevented the COIN re-entry (-$176 realized). Carries zero downside risk for names not in the earnings window.

**Backtest:** Trivially verifiable: 1 affected symbol (COIN) on 5/4. Savings = $176 realized loss avoided.

---

### Proposal C: Block leveraged and inverse ETFs from selection

**Why:** AXTX (2× leveraged) was the top overnight selection at 14.4%. SOXS (3× inverse) appeared in the 19:08 selector output before execution excluded it. Leveraged ETFs decay over multi-day holds due to daily rebalancing. AXTX has been held unmonitored 83 days since 5/4 — the maximum potential decay scenario.

**Diff:**
```python
# src/discovery.py — in eligibility filter:
BLOCKED_LEVERAGED_PATTERNS = [
    r'\b[23][Xx]\b',      # "2X", "3X"
    r'\bUltra\b',
    r'\bInverse\b',
    r'\bBear\b',
    r'\bShort\b',
    r'\bDaily ETF\b',     # catches "Tradr 2X Long AXTI Daily ETF"
]
import re
def is_leveraged_etf(name: str) -> bool:
    return any(re.search(p, name, re.IGNORECASE) for p in BLOCKED_LEVERAGED_PATTERNS)

# In candidate eligibility check:
if asset.asset_class == 'us_equity' and is_leveraged_etf(asset.name):
    log.info(f"Skipping {symbol}: leveraged/inverse ETF ({asset.name})")
    continue
```
```yaml
# config.yaml
discovery:
  block_leveraged_etf: true   # NEW — enforced in discovery.py eligibility filter
```

**Expected impact:** Removes AXTX, SOXS, and similar names from the candidate pool. Swing strategy holds leveraged ETFs for days; daily-rebalanced leverage compounds decay. Prevents the frozen-book scenario (83 days unmonitored) from including a 2× instrument.

**Backtest:** Not run for future impact. Historical: AXTX entered at $46.41 on 5/4. Current price unknown (blocked). A 2× leveraged ETF on a narrow underlying (AXTI = AXT Inc, a semiconductor materials stock) is high-decay; even if AXTI is flat, AXTX decays.

---

### Proposal D: Raise exit-arbiter confidence floor *(refines prior config baseline)*

**Why:** All 13 exit-arbiter calls on 5/4 fired at 0.58–0.62 — barely above the 0.55 floor. These low-conviction calls drove the bulk of same-session closes. GEV arbiter said hold (0.62) but still triggered a verifier dust-sweep close.

**Diff:**
```yaml
# config.yaml
exit_arbiter:
  min_confidence: 0.55   # current
  # →
  min_confidence: 0.65   # NEW — requires higher conviction to trigger exit
```

**Expected impact:** Raises the bar for same-scan exits driven by `intraday_momentum_lost`. On 5/4, would have blocked all 13 exit-arbiter calls (all were 0.58–0.62) except those triggered by stop-loss or explicit technical flip. Combined with Proposal A (min-hold-timer), the bot holds longer and lets theses play out. Estimated: 6–9 fewer close events per active scan session.

**Backtest:** 5/4 exit arbiter calls: 13 total; 0 were above 0.65. All 13 would have been blocked (filtered to exits only via stop-market or explicit signal). Net: would have kept AMZN, GEV, UNH, MU, SNDK, NOK, WDC, COIN, GOOGL through the session. Some were correct exits; this is the risk. Protective stop at 1% limits downside.

---

### Proposal E: Cap selector SPY-proxy auto-growth on high-churn days

**Why:** SPY position grew from ~$36K to $59.7K during 5/4 as the selector recycled exits into cash-proxy. SPY fell -0.36% that day — the bot was buying index exposure into a red tape. Cash is cheaper and does not track intraday declines.

**Diff:**
```yaml
# config.yaml
cash_proxy:
  intraday_growth_cap: true       # NEW
  intraday_growth_disabled_when:
    spy_daily_change_pct_below: -0.003  # -0.3%
    intraday_fills_above: 8
  intraday_growth_max_pct_above_morning: 0.10  # max 10% new SPY buys above morning value
```

**Expected impact:** On 5/4, would have capped SPY growth at ~$39.6K (morning $36K + 10%). Saves spread on ~$23K of mid-session SPY buys (+$12–$23 in friction) and avoids index exposure when the tape is clearly negative. On positive days, growth cap doesn't bind.

**Backtest:** Not directly testable — would need per-scan SPY notional history. Directional: 5/4 SPY grew $23K mid-session on a red-tape day; cap would have held cash instead, saving ~$83 in SPY decline on that notional ($23K × 0.36%).

---

## Operational Status

| Item | Status |
|---|---|
| Bot running since 2026-05-04 | **NO** — 83 calendar days (~58 trading days) of silence |
| Frozen positions (AXTX, META, PWR, SPY) | Unmonitored; Alpaca API blocked in this container |
| AXTX (2× leveraged ETF) decay risk | Unknown; 83 days is significant for a daily-rebalanced 2× instrument |
| 8 proposals from 2026-05-05 review | Still open; zero live data to validate since then |
| Proposals A–E above | New; can be merged to main after user review; require live cycle to validate |

**Priority action (unchanged from 17 prior daily reviews):** Confirm the trading scheduler (`scripts/scan_and_trade.py`) is running and writing snapshots. Until resolved, all proposals are untested.

---

## Backtests Run (this session)

| Test | Result |
|---|---|
| Same-day round-trips count | 7 identified on 2026-05-04; total notional $96K; net P&L -$88 |
| Premature exit opportunity cost (60m) | GEV +$198, LLY +$70, WDC +$100, MU(1st) +$95 = **$463 missed** |
| Exit-arbiter confidence distribution | 100% of calls (13/13) at 0.58–0.62; zero above 0.65 |
| Earnings-lockout counterfactual | COIN re-entry blocked → -$176 realized loss avoided |
| Rolling 9-session portfolio vs SPY | Portfolio equity: $99,627→$99,850 (+0.2%); SPY 30d: +10.71%; period_vs_spy: **-10.71%** |

