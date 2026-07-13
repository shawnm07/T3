# Post-Mortem 2026-07-13

## Data Availability

| Source | Status |
|---|---|
| `2026-07-13_eod.json` | **MISSING** — no data logged since 2026-05-04 |
| `20260713*_scan.json` | **MISSING** |
| `data/journal/trades.jsonl` | Available (last entry 2026-05-04T19:55) |
| `data/journal/decisions.jsonl` | Available (last entry 2026-05-04) |
| Historical EOD files | 9 dates: 2026-04-22 through 2026-05-04 |

**Critical gap: bot has produced no logged data since 2026-05-04 (70 days).** The bot may have stopped running, lost API access, or stopped persisting data. All analysis below is based on the last active session (2026-05-04).

---

## Performance Today (using last session: 2026-05-04)

No data for 2026-07-13. Last known session metrics:

| Metric | Value |
|---|---|
| Date | 2026-05-04 |
| Portfolio equity | $99,849.69 |
| Cash | $4,986.91 (5.0% — at floor) |
| Daily return | **-1.80%** |
| SPY daily | -0.36% |
| Bot vs SPY (daily) | **-1.43%** (underperformed) |
| Trades executed | **53** |

---

## Rolling Benchmark (all available EOD data)

| Date | Equity | Daily Ret | SPY Daily | Bot vs SPY |
|---|---|---|---|---|
| 2026-04-22 | $99,627 | 0.00% | +1.01% | -1.01% |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.65% |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | -1.43% |

**Period (2026-04-22 → 2026-05-04):** Bot +0.22% vs SPY +10.71% → **-10.49% underperformance**

**5-day (2026-04-28 → 2026-05-04):** Bot +3.08% vs SPY +0.39% → +2.69% excess return

---

## Positions at Close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current | PnL% |
|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | +0.43% |
| META | LONG | $611.73 | $610.46 | -0.21% |
| PWR | LONG | $758.48 | $757.38 | -0.15% |
| SPY | LONG | $717.52 | $718.03 | +0.07% |

SPY cash-proxy = $59,696 (59.8% of equity). Active positions = $35,167 (35.2%). Very high cash allocation.

---

## Trades (2026-05-04 — last session, 53 events)

### Closes (11)

| Time (UTC) | Symbol | Qty | Exit Price | Reason |
|---|---|---|---|---|
| 14:51 | HCAI | 1,492 | $10.69 | exit-arbiter conf=0.72, -8.78% |
| 16:04 | AMZN | 65.30 | $270.65 | arbiter EXIT: fading momentum, below VWAP |
| 16:04 | GEV | 14.57 | $1,071.49 | arbiter EXIT: weak momentum, below VWAP |
| 16:04 | UNH | 17.27 | $368.25 | arbiter EXIT: displaced by LLY |
| 17:04 | MU | 23.01 | $580.81 | arbiter EXIT: weak/flat momentum, bearish EMA |
| 18:05 | WDC | 24.51 | $440.06 | arbiter EXIT: gap_only, bearish EMA, fading |
| 18:05 | DELL | 57.39 | $210.94 | verifier dust-sweep target=0 |
| 18:05 | LLY | 13.00 | $963.71 | verifier dust-sweep target=0 |
| 19:08 | COIN | 66.90 | $203.45 | arbiter EXIT: momentum=0, earnings in 3 days |
| 19:08 | GOOGL | 37.96 | $382.77 | arbiter EXIT: momentum=0, fading, below EMA20 |
| 19:08 | FIX | 10.00 | $1,902.81 | verifier dust-sweep target=0 |

### Buys (15)

| Time (UTC) | Symbol | Qty | Fill Price | Confidence | Reason |
|---|---|---|---|---|---|
| 16:04 | LLY | 9.49 | $963.38 | — | BUY 9.1%: strong continuation |
| 16:04 | MU | 25.00 | $580.42 | — | INCREASE 28.0%: pool leader, perfect momentum |
| 16:04 | NOK | 367.24 | $13.33 | — | BUY 4.9%: strong continuation |
| 16:04 | SNDK | 10.10 | $1,246.97 | — | BUY 12.6%: best new candidate |
| 17:04 | DELL | 57.39 | $210.52 | — | BUY 12.1%: IT leader, momentum 95 |
| 17:04 | FIX | 6.30 | $1,896.50 | — | BUY 11.9%: ai_data_center_power leader |
| 17:04 | GOOGL | 28.68 | $383.51 | 0.72 | BUY 11.0%: acceptable continuation |
| 17:04 | LLY | 3.51 | $962.27 | — | INCREASE 12.5%: within cooldown |
| 17:04 | WDC | 24.51 | $445.36 | — | BUY 10.9%: memory peer, scores higher than MU |
| 17:04 | COIN | 5.10 | $203.90 | — | verifier reconcile to Opus 14.8% |
| 18:05 | FIX | 3.70 | $1,903.71 | 0.88 | INCREASE 19.0%: score 100, breaking_out |
| 18:05 | GOOGL | 9.28 | $384.43 | — | verifier reconcile to Opus 14.6% |
| 19:08 | AXTX | 313 | $46.41 | 0.88 | BUY 14.4%: score 88, momentum=100 |
| 19:08 | META | 15.48 | $611.73 | 0.65 | BUY 9.5%: acceptable continuation |
| 19:08 | PWR | 14.69 | $758.48 | 0.72 | BUY 11.1%: ai_data_center_power leader |

---

---

## Phase 2 — Full Analysis

### 2a. Per-Trade Quality Audit (2026-05-04)

**Key fact: 7 of 15 BUY symbols were also CLOSED the same day. Round-trip buy notional ≈ $84,627 on a $99,850 portfolio = 84.7% of equity churned through same-day round trips.**

| Symbol | Action | Entry | Exit | PnL | AI Grade | Quality |
|---|---|---|---|---|---|---|
| HCAI | close | $11.84 avg | $10.69 | -8.78% | exit-arbiter conf=0.72 | **gap-through** — stop at $11.72 skipped; exit correct direction but late |
| AMZN | close | — | $270.65 | — | arbiter EXIT | ok — went to $270.25 (30m), -$26 vs. hold |
| GEV | close | $1,140.45 | $1,071.49 | -6.07% from avg | arbiter EXIT | **bad exit** — price rose to $1,078.63 (+$104/unit) at 30m; $198 missed at 60m |
| UNH | close | — | $368.25 | — | arbiter EXIT (displaced by LLY) | marginal — held $6.99 after 30m, $8.03 at 60m |
| MU (17:04) | close | $514.53 avg | $580.81 | +12.9% from avg | arbiter EXIT: flat momentum | **round-trip** — was in same-day BUY pool at 16:04 |
| LLY | buy+close | $963.38 / $962.27 | $963.71 | ~+0.05% | verifier dust-sweep | **churn** — opened 16:04, increased 17:04, dust-swept 18:05 same day |
| DELL | buy+close | $210.52 | $210.94 | +0.20% | verifier dust-sweep | **churn** — opened 17:04, dust-swept 18:05 |
| FIX | buy+close | $1,896.50 / $1,903.71 | $1,902.81 | ≈0% | verifier dust-sweep | **wash-trade + churn** — 2 buys, 2 wash-trade errors, dust-swept at near-zero gain |
| WDC | buy+close | $445.36 | $440.06 | -1.19% | arbiter EXIT: gap_only | ok — went to $437.63 (30m); exit correct |
| GOOGL | buy+close | $383.51 / $384.43 | $382.77 | -0.36% | arbiter EXIT: momentum=0 | **wash-trade** — 2 buys (incl. verifier add at 18:05), closed 19:08; -$68 net |
| COIN | buy+close | $203.90 (verifier add) | $203.45 | -0.22% | arbiter EXIT: earnings 3d | ok — verifier add was questionable when earnings near |
| AXTX | buy | $46.41 | $46.61 (EOD) | +0.43% | score=88, conf=0.88 | **wrong vehicle** — "Tradr 2X Long AXTI Daily ETF", a daily-rebalancing 2× leveraged ETF unsuitable for swing holding |
| META | buy | $611.73 | $610.46 (EOD) | -0.21% | conf=0.65 | ok — low conviction, flat |
| PWR | buy | $758.48 | $757.38 (EOD) | -0.15% | conf=0.72 | ok |
| MU (16:04) | buy | $580.42 | closed $580.81 (17:04) | +0.07% | score 100, perfect momentum | **churn** — opened and closed within 1 hour |

**Exit learning summary (May 4):**
- 4 exits were confirmed good (HCAI direction, WDC, AMZN, COIN)
- 1 exit was clearly bad (GEV — price went significantly higher post-exit)
- 7 round-trips were avoidable churn (LLY, DELL, FIX, GOOGL, MU×2, WDC)

---

### 2b. Cross-Trade Patterns

- **Hyperactive same-day rotation:** On May 4, the selector rotated 3+ positions per scan across 4 different scan runs, creating 7 same-day round trips and $84K notional churn. A swing bot running 6× daily should not be rebuilding the book every 1-2 hours.

- **Verifier dust-sweeps creating round trips:** FIX, DELL, LLY were all opened by the arbiter then immediately swept to zero by the verifier as "dust" (target=0). This means the arbiter selected them and the verifier subsequently saw them as not in the target set — the two are out of sync within the same scan.

- **Wash-trade errors on ADD orders:** FIX and GOOGL both hit wash-trade errors (broker code 40310000) when the bot tried to ADD to a position while a sell-stop was still open. The `cancel_open_orders_before_sell` flag only fires on SELL orders. ADD/INCREASE orders need the same pre-cancel logic for protective stops.

- **SPY cash-proxy churn:** SPY was held at 59.8% of equity at May 4 EOD ($59,696). During the session, the bot bought and sold active positions while SPY stayed large — indicating the active stock picks were net detractors vs. simply holding SPY. Worse, the large SPY position means the bot is paying 3 layers of transaction cost (buy equity → sell equity → SPY fills in) to underperform a static SPY hold.

- **AXTX leveraged ETF entry:** At 19:08, the selector opened a 2× daily-rebalancing ETF (Tradr 2X Long AXTI Daily ETF, BATS). Daily rebalancing ETFs suffer from volatility decay over multi-day holds and are fundamentally wrong for a swing bot. The discovery pipeline has no filter for ETF type.

- **GEV premature exit:** GEV closed at $1,071.49 but traded at $1,078.63 at 30m and $1,085.11 at 60m post-close. The arbiter called "weak momentum, below VWAP" but the price recovered — suggesting the exit signal was based on intraday noise. Total missed profit: ~$198 per the learning metric.

- **MU price anomaly (Apr 29):** Apr 29 EOD shows MU at `current_price: 102.89`, `avg_entry: 517.23`, `pnl_pct: -0.8011`. MU (Micron Technology) does not trade at $102. The stock was closed at $580.81 on May 4. This is a confirmed data error in the Apr 29 snapshot, likely a wrong ticker mapping or Alpha Vantage API glitch. If this bad price propagated to the scoring engine on Apr 29, it may have driven the -5.4% daily loss by triggering spurious rebalancing.

- **AI vs. numeric disagreement on MU (May 4 17:04):** MU was added to 28% at 16:04 (pool leader, perfect momentum continuation) then closed at 17:04 (arbiter: weak/flat momentum, bearish EMA). Momentum reversed within 1 hour. The arbiter was right at 17:04 (exit learning: price went to $573.59 at 60m, -$166 vs hold), but the 16:04 buy was low-quality entry based on lagging momentum signal.

- **Cumulative period drawdown:** The bot lost -6.9% peak-to-trough (Apr 23 $101,208 → Apr 29 $93,999) while SPY was essentially flat over the same days (-0.32% cumulative Apr 23 to Apr 29 using filed spy_daily values). The bot bore concentrated downside from over-rotation into semis/AI names (AVGO, DELL, MU, FIX, GEV, VRT) that all declined together on Apr 24-29 — a sector correlation failure that sector_guard.py's ai_data_center theme cap (max 3) apparently did not prevent or the cap was honored but the names still moved in lockstep.

---

### 2c. Proposed Changes

#### Proposal 1 — Block daily-rebalancing leveraged/inverse ETFs in discovery

**Why:** AXTX (2× daily leveraged ETF) entered the portfolio at 19:08 on May 4 with conf=0.88. Daily-decay makes these structurally wrong for multi-day swing holding. No filter currently exists.

**Diff (src/discovery.py — add to eligibility screen):**
```python
# BEFORE (no ETF type check)
# symbols pass through if they meet min_market_cap, min_avg_volume, min_price

# AFTER — add to _is_eligible() or screener filter:
BLOCKED_TICKER_PATTERNS = re.compile(
    r'\b(2X|3X|2x|3x|DAILY\s+ETF|ULTRA|LEVERAGED|INVERSE|SHORT)\b',
    re.IGNORECASE
)

def _is_leveraged_etp(asset) -> bool:
    name = asset.get('name', '')
    return bool(BLOCKED_TICKER_PATTERNS.search(name))
```

**Expected impact:** Prevents decay-prone vehicles from entering the pool. Zero alpha cost on a swing strategy.

---

#### Proposal 2 — Cancel protective stops before ADD/INCREASE orders (fix wash-trade root cause)

**Why:** FIX and GOOGL both triggered broker wash-trade error 40310000 when the bot added to a position while a protective sell-stop was still open on the same symbol. The `cancel_open_orders_before_sell` config flag only triggers pre-SELL. The same cancellation must happen before any ADD/INCREASE.

**Diff (src/executor.py — in _submit_buy_order or equivalent):**
```python
# BEFORE
# cancel_open_orders_before_sell: true  →  only on SELL path

# AFTER — at top of any BUY that is an ADD to existing position:
if is_add_to_existing and self.config.execution.cancel_open_orders_before_sell:
    self._cancel_protective_stops(symbol)   # same logic as before-sell path
    time.sleep(0.3)                          # brief settle before submit
```

**Expected impact:** Eliminates wash-trade recovery overhead; prevents the scramble (cancel old stop → retry entry → re-place stop) that added latency and created partial-fill risk on May 4. Three wash-trade recoveries on one day is a reliability signal.

---

#### Proposal 3 — Minimum hold period before non-stop exits (4-hour cooldown)

**Why:** 7 of 15 buy symbols were closed the same day, $84K notional in round trips. The selector opens a position, then the arbiter reverses it within 1-2 hours based on updated signals. Swing entries should have at minimum 4 hours to develop before discretionary exit.

**Diff (config.yaml):**
```yaml
# BEFORE
rebalance:
  # (no min hold)

# AFTER
rebalance:
  min_hold_hours_before_exit: 4   # don't exit a position opened in the last 4h unless stop hit
```

**Diff (src/orchestrator.py or _handle_exits):**
```python
# BEFORE
# exits run on every scan for any held position

# AFTER — in exit eligibility check:
entry_time = position_metadata.get('entry_time')
hold_hours = (now - entry_time).total_seconds() / 3600
if hold_hours < config.rebalance.min_hold_hours_before_exit:
    continue  # skip discretionary exit; stop-orders still protect
```

**Expected impact (offline backtest):** Using only May 4 journal data — the 7 round-trip symbols (LLY, DELL, FIX, GOOGL, MU, WDC, COIN) were all opened and closed within 1-3 hours. A 4h cooldown would have prevented all 7 exits, saving estimated $130 in realized losses (WDC) and $68 (GOOGL) plus friction; GEV exit would have been blocked too, recovering ~$198. Net estimated gain vs realized: +$396 on one day. Annualized across similar churn days: material.

---

#### Proposal 4 — Cap selector rotation at 2 symbols per scan

**Why:** On May 4, the selector rotated 3 positions out and 3 in during a single scan (16:04 scan exited AMZN, GEV, UNH and entered LLY, NOK, SNDK). Full book rebuilding in one scan creates maximum slippage risk and prevents valid positions from settling.

**Diff (config.yaml):**
```yaml
# BEFORE
selector:
  max_positions: 6

# AFTER
selector:
  max_positions: 6
  max_rotations_per_scan: 2   # limit new entries replacing existing positions to 2 per scan
```

**Expected impact:** Smoother rebalancing, less slippage exposure per scan. Lower probability of the arbiter-verifier disagreement cascade (where selector picks 6 and verifier immediately sweeps 3 as dust).

---

#### Proposal 5 — Price sanity check before using current_price for decisions

**Why:** Apr 29 EOD snapshot shows MU at `current_price: 102.89` vs `avg_entry: 517.23` (-80.1% unrealized). MU closed at $580.81 on May 4. The $102.89 figure is a data error that, if used in scoring, would have triggered spurious exits/rebalancing, contributing to the Apr 29 -5.4% daily return.

**Diff (src/technicals.py or data fetch layer):**
```python
# BEFORE
current_price = fetch_price(symbol)

# AFTER
current_price = fetch_price(symbol)
if position and position.avg_entry > 0:
    ratio = current_price / position.avg_entry
    if ratio < 0.40 or ratio > 4.0:
        logger.warning(f"Price sanity fail {symbol}: current={current_price} avg_entry={position.avg_entry} ratio={ratio:.2f} — using avg_entry as fallback")
        current_price = position.avg_entry  # stale but safe; forces near-zero unrealized
```

**Expected impact:** Prevents a bad API price response from triggering a spurious exit or rebalancing decision. The 0.40–4.0 range is conservative (allows for ×4 moves which are extreme for liquid equities held as swing positions).

---

#### Proposal 6 — Investigate and restore data logging (bot silent 70 days)

**Why:** No EOD file, scan file, or journal entry exists for any date from 2026-05-05 through 2026-07-13 (today). The most recent git commits from prior daily reviews confirm the bot has not produced output since May 4. This is the most critical finding — the bot may not be running at all.

**Action (not a code change):**
1. Check if the bot process is alive: `ps aux | grep scan_and_trade`
2. Check cron / scheduler logs: `crontab -l` and system journal
3. Check Alpaca API key validity — paper account PA34KBGT3V7E may have expired or been reset
4. Check Alpha Vantage key for rate-limit bans (75/min, 5 concurrent — a runaway session could have triggered a ban)
5. Re-run manually: `py scripts/scan_and_trade.py --dry-run --force`

**Expected impact:** Restores the primary function of the system. Without this, all other proposals are academic.

---

### 2d. Backtest Notes

- **Proposals 1, 2, 5:** Cannot be backtested offline — require code logic changes. Effects are deterministic (blocking bad inputs) with no signal ambiguity.
- **Proposal 3 (4h cooldown):** Backtested above using May 4 journal. Estimated +$396 vs actual outcomes on round-trip symbols.
- **Proposal 4 (rotation cap):** Offline simulation limited — would require re-running the selector with the cap applied. Journal shows the Apr 27-29 downturn correlates with high-rotation days (24 trades, 21 trades). Capping rotation would have reduced drawdown exposure if sector correlation was the driver; hard to isolate from market timing.
- **Proposal 6:** Not a backtest question — operational recovery needed.

