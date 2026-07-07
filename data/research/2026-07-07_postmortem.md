# Post-Mortem 2026-07-07

> **Analysis date:** 2026-07-07 (scheduled run)
> **Last trading day with data:** 2026-05-04
> **Data gap:** No EOD, scan, or journal entries exist between 2026-05-04 and 2026-07-07. All analysis below covers the period ending 2026-05-04.

---

## Data Availability

| Source | Status |
|---|---|
| `data/research/2026-07-07_eod.json` | **MISSING** |
| `data/research/20260707*_scan.json` | **MISSING** |
| `data/research/2026-05-04_eod.json` | Present (most recent) |
| `data/research/*_scan.json` | Present through 2026-05-04T19:55 UTC |
| `data/journal/trades.jsonl` | Present (last entry: 2026-05-04T19:55 UTC) |
| `data/journal/decisions.jsonl` | Present (1556 entries) |
| EOD history | 9 trading days: 2026-04-22 → 2026-05-04 |

All benchmarks and analysis below derive exclusively from on-disk files. No network calls were made.

---

## Performance — Last Trading Day (2026-05-04)

| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| **vs SPY (day)** | **-1.43%** |
| Equity at close | $99,849.69 |
| Cash | $4,986.91 (4.99%) |
| Positions (excl. SPY proxy) | 4 |
| Trades executed | 53 |

**Period benchmarks (from on-disk EOD files):**

| Window | Portfolio | SPY | vs SPY |
|---|---|---|---|
| 5-day (Apr 28 – May 4) | -13.18% | +0.39% | **-13.57%** |
| 9-day (Apr 22 – May 4) | -17.31% | +1.95% | **-19.27%** |
| Win days vs SPY | 2 / 9 | — | — |
| Peak-to-trough drawdown (9d) | **-7.12%** | — | — |
| Avg trades/day | 22.7 | — | — |

Goal (beat SPY within risk budget): **NOT MET**. Bot underperformed SPY by >13% over the 5-day window and exceeded effective daily drawdown twice (Apr 27: -4.88%, Apr 28: -5.13% cumulative).

---

## Positions at Close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current Price | P&L% | Market Value |
|---|---|---|---|---|---|
| AXTX | LONG | 46.41 | 46.61 | +0.43% | $14,588.93 |
| META | LONG | 611.73 | 610.46 | -0.21% | $9,448.36 |
| PWR | LONG | 758.48 | 757.38 | -0.15% | $11,129.62 |
| SPY (proxy) | LONG | 717.52 | 718.03 | +0.07% | $59,695.86 |

SPY proxy represents **59.7% of portfolio** — the strategy effectively became a beta-1 passive fund by end of session.

---

## Trades on 2026-05-04

### Buys (15)

| Symbol | Qty | Entry | Stop | Reason (truncated) |
|---|---|---|---|---|
| LLY | 9.49 | 963.38 | 951.69 | BUY 9.1% — Strong continuation, above VWAP |
| MU | 25.0 | 580.42 | 577.65 | INCREASE 28.0% — Perfect momentum continuation |
| NOK | 367.2 | 13.33 | 13.24 | BUY 4.9% — Strong continuation, above VWAP |
| SNDK | 10.1 | 1246.97 | 1237.62 | BUY 12.6% — Best new candidate |
| DELL | 57.4 | 210.52 | 207.81 | BUY 12.1% — IT sector leader, momentum 95 |
| FIX | 6.30 | 1896.50 | 1865.26 | BUY 11.9% — ai_data_center_power leader |
| GOOGL | 28.68 | 383.51 | 378.99 | BUY 11.0% — Comm Services leader |
| LLY | 3.51 | 962.27 | 952.61 | INCREASE 12.5% — Within 120-min cooldown |
| WDC | 24.51 | 445.36 | 437.86 | BUY 10.9% — Memory peer leader |
| COIN | 5.10 | 203.90 | 202.77 | Verifier reconcile to 14.8% |
| FIX | 3.70 | 1903.71 | 1881.24 | INCREASE 19.0% — Perfect momentum, breaking_out |
| GOOGL | 9.28 | 384.43 | 380.10 | Verifier reconcile to 14.6% |
| AXTX | 313.0 | 46.41 | 45.34 | BUY 14.4% — Momentum 100, breaking_out |
| META | 15.48 | 611.73 | 606.07 | BUY 9.5% — Comm Services diversification |
| PWR | 14.69 | 758.48 | 748.54 | BUY 11.1% — ai_data_center_power |

### Sells / Closes (11)

| Symbol | Qty | Exit Price | Reason |
|---|---|---|---|
| HCAI | 1492.0 | 10.69 | AI exit-arbiter (conf=0.72) — down -8.78% |
| AMZN | 65.30 | 270.65 | arbiter EXIT — Fading momentum, below VWAP |
| GEV | 14.57 | 1071.49 | arbiter EXIT — Weak momentum, below VWAP |
| UNH | 17.27 | 368.25 | arbiter EXIT — Fading volume |
| MU | 23.01 | 580.81 | arbiter EXIT — Weak/flat momentum, bearish EMA |
| WDC | 24.51 | 440.06 | arbiter EXIT — Gap_only, bearish EMA |
| DELL | 57.39 | 210.94 | verifier dust-sweep (target=0) |
| LLY | 13.0 | 963.71 | verifier dust-sweep (target=0) |
| COIN | 66.90 | 203.45 | arbiter EXIT — Momentum 0, earnings in 3d |
| GOOGL | 37.96 | 382.77 | arbiter EXIT — Momentum 0, below EMA20 |
| FIX | 10.0 | 1902.81 | verifier dust-sweep (target=0) |

---

## Trade-by-Trade Quality Table (2026-05-04)

All P&L computed from `avg_entry` / `filled_avg_price` against exit price. "Verdict" based on exit_learning_metrics 30m/60m follow-through.

| Symbol | Side | Event | Qty | Entry | Exit | P&L | AI Grade | One-line Reason | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| HCAI | LONG→exit | buy→close | 1492 | 11.84 | 10.69 | **-8.78%** | conf=0.72 | Stop order never submitted (stop_order_id=null); held unprotected 3 days | **CRITICAL BUG — stop miss** |
| AMZN | LONG→exit | close | 65.3 | ~271 | 270.65 | ~-0.1% | conf=0.85 | Fading momentum, below VWAP | GOOD — price fell after |
| GEV | LONG→exit | close | 14.6 | ~1072 | 1071.49 | ~-0.05% | conf=0.85 | Weak momentum, below VWAP | PREMATURE — +$104 missed at 30m |
| UNH | LONG→exit | close | 17.3 | ~369 | 368.25 | ~-0.2% | conf=0.80 | Fading volume | PREMATURE — +$7 missed (minimal) |
| MU | LONG→exit | close | 23.0 | ~577 | 580.81 | +0.66% | conf=0.85 | Weak/flat momentum, bearish EMA | GOOD — price fell 30m/60m after |
| WDC | LONG→exit | close | 24.5 | ~446 | 440.06 | -1.18% | conf=0.92 | Gap_only, bearish EMA | GOOD (30m) / BAD (60m +$100 missed) |
| DELL | LONG→exit | dust-sweep | 57.4 | 210.52 | 210.94 | +0.20% | verifier | Bought and immediately swept same scan | **CHURN — sequencing defect** |
| LLY | LONG→exit | dust-sweep | 13.0 | ~963 | 963.71 | +0.07% | verifier | Bought and immediately swept same scan | **CHURN — sequencing defect** |
| FIX | LONG→exit | dust-sweep | 10.0 | ~1900 | 1902.81 | +0.15% | verifier | Bought (twice) and immediately swept same scan | **CHURN — sequencing defect** |
| COIN | LONG→exit | close | 66.9 | ~205 | 203.45 | -0.75% | conf=0.80 | Momentum 0, earnings in 3d | GOOD — earnings gate rationale valid |
| GOOGL | LONG→exit | close | 38.0 | 383.51 | 382.77 | -0.19% | conf=0.80 | Momentum 0, below EMA20 | MIXED — entered and exited same session |
| SNDK | LONG→exit | close (prev) | 10.1 | 1246.97 | 1237.52 | -0.76% | conf=0.85 | Early exit — price up 30m later | PREMATURE — +$24 missed at 30m |
| STX | LONG→exit | close (prev) | — | — | 740.23 | — | conf=0.90 | High-confidence exit | PREMATURE — +$76 missed at 30m |

**Exit quality:** 12/24 exit_learning_metrics records were premature (left money on table) vs 12/24 correctly timed. Exit arbiter running at ~50% accuracy on direction.

---

## Cross-Trade Patterns

- **Verifier/arbiter sequencing creates instant round-trips:** DELL, LLY, and FIX were all purchased in the 19:08 UTC scan then immediately "dust-swept" (closed) by the verifier in the same scan pass (within ~10 seconds of buying). The arbiter had already decided to exit these symbols; the verifier reconciled against the prior scan's targets and bought them, then the arbiter's exit fired. These are pure transaction-cost losses with no exposure taken.

- **HCAI stop order never submitted (critical):** `stop_order_id: null` in the trade log. HCAI was bought on 2026-05-01 with a stop at 11.73 that was never placed with the broker. The position drifted unprotected for 3 days and exited at -8.78% ($1,699 loss vs. ~$165 at the intended 1% stop).

- **Same-day round-trips on 7 symbols (May 4 alone):** MU, WDC, DELL, LLY, FIX, COIN, GOOGL — all bought and closed on 2026-05-04. Combined friction from spread costs, stop resets, and wash-trade recovery cycles compounded the realized loss.

- **Two scans 5 minutes apart (15:13 and 15:18 UTC):** The first scan bought 7 positions; the second scan fired before fills could settle, executing 5 more (including a COIN reduce that partially offset a position just opened). This is the core driver of intraday churn — the bot is re-planning before the previous plan is even executed.

- **AXTX is a 2x leveraged ETF:** "Tradr 2X Long AXTI Daily ETF" with `max_leverage: 1.0` in config. The bot treats it as a regular equity. This is policy-violating and introduces implicit leverage to the book.

- **SPY proxy overweight (59.7%):** Portfolio finished the day 60% SPY proxy. When the bot exits conviction positions and can't find replacement candidates, the entire book defaults to passive beta-1 exposure, negating the alpha mandate. The selector is not penalizing SPY proxy overconcentration.

- **No winner trimming problem observed:** Unlike prior periods, May 4 showed the opposite — exiting winners too soon (GEV, SNDK, STX all had positive 30m follow-through). The selector replaced them with lower-quality names that were also exited intraday.

- **AI vs numeric disagreements (minor):** FIX tech_score=0.836 but was still exited at conf=0.80. GOOGL tech_score=0.772 with exit conf=0.80. High technical scores are being overridden by short-term momentum signals ("score 23, below EMA20") that may be noise at the 2h scan cadence.

---

## Proposed Changes

### 1. Fix null stop_order_id (CRITICAL — `src/executor.py`)

**Why:** HCAI lost $1,699 in 3 days because the protective stop was never submitted to the broker (stop_order_id=null in trade log). The 1% hard stop is the primary risk guardrail; a silent submission failure voids it.

**Diff:**
```python
# src/executor.py — after submitting stop order, add:
# BEFORE (current — silent failure):
#   stop_order = await self._submit_stop(...)
#   trade_log["stop_order_id"] = stop_order.id if stop_order else None

# AFTER (proposed — fail-loud):
stop_order = await self._submit_stop(...)
if stop_order is None:
    logger.error(f"CRITICAL: stop order submission failed for {symbol} — position unprotected")
    # Attempt one retry, then alert and cancel the entry order if retry also fails
    stop_order = await self._submit_stop(...)
    if stop_order is None:
        await self._cancel_entry(symbol, order_id)
        raise RuntimeError(f"Stop submission failed twice for {symbol}; entry cancelled")
trade_log["stop_order_id"] = stop_order.id
```

**Expected impact:** Eliminates the class of unprotected multi-day gap-down losses. HCAI alone cost $1,534 above the 1% target (the delta between -8.78% actual and -1% intended).

**Backtest:** Not needed — this is a correctness fix, not a strategy change.

---

### 2. Enforce minimum scan separation (config + `scripts/scan_and_trade.py`)

**Why:** Two scans ran 5 minutes apart (15:13 and 15:18 UTC on May 4). The second scan saw unfilled or just-filled orders and re-planned against stale state, creating conflicting positions and wash-trade recovery chains.

**Diff:**
```yaml
# config.yaml — add under risk:
  min_scan_interval_minutes: 45   # was: no floor (relied on cron only)
```

```python
# scripts/scan_and_trade.py — near top, after market open check:
# BEFORE: (no guard)
# AFTER:
last_scan_ts = _read_last_scan_timestamp()
if last_scan_ts and (now - last_scan_ts).seconds < cfg.risk.min_scan_interval_minutes * 60:
    logger.info(f"Skipping scan — last ran {(now-last_scan_ts).seconds//60}m ago (min={cfg.risk.min_scan_interval_minutes}m)")
    sys.exit(0)
```

**Expected impact:** Eliminates the 15:13/15:18 double-fire pattern. Reduces daily trade count from ~23 toward ~14 (4 scans × ~3.5 executions). Allows fills to settle before re-planning.

**Backtest:** From 9-day journal: pairs of scans within 10 minutes fired 3 times (Apr 28, Apr 30, May 4). All 3 days had > 20 trades. Eliminating them would have cut ~15 trades/week.

---

### 3. Block verifier from sweeping positions younger than 30 minutes (`src/orchestrator.py` or verifier prompt)

**Why:** DELL, LLY, and FIX were bought by the arbiter and immediately dust-swept by the verifier within 10 seconds in the same scan pass. These are pure transaction-cost losses (no actual exposure change, just bid-ask spread paid twice).

**Diff:**
```yaml
# config.yaml — add under verifier or risk:
  verifier_min_position_age_minutes: 30   # new key
```

```python
# src/orchestrator.py — in _run_verifier() or verifier input assembly:
# BEFORE: pass all positions to verifier regardless of age
# AFTER:
from datetime import timezone, timedelta
min_age = timedelta(minutes=cfg.get("risk.verifier_min_position_age_minutes", 30))
positions_for_verifier = [
    p for p in current_positions
    if (now - p.entry_time) >= min_age
]
```

**Expected impact:** Eliminates the 3 dust-sweep round-trips on May 4. At ~$16K average position size, each unnecessary open+close costs ~$16–32 in spread. Across the 3 symbols: ~$50–100 direct cost saved, plus stop-order churn avoided.

**Backtest:** Verifier dust-sweeps on positions < 5 minutes old occurred on 2 of 9 trading days (May 4, May 1). Both days had > 20 trades.

---

### 4. Exclude 2x/3x leveraged ETFs from universe (`src/discovery.py`)

**Why:** AXTX ("Tradr 2X Long AXTI Daily ETF") was bought at 14.4% position size. `config.yaml` sets `max_leverage: 1.0`, but the bot doesn't screen ETF names or prospectus leverage. A 2x leveraged ETF at 14.4% of a $100K book creates $28.8K of effective notional exposure in a single name — violating both the spirit of the leverage cap and the per-position size cap on a risk-adjusted basis.

**Diff:**
```yaml
# config.yaml — add under universe:
  exclude_leveraged_etfs: true      # blocks ETF tickers with "2X", "3X", "Ultra", "Bear" in name
  leveraged_etf_keywords: ["2X", "3X", "Ultra", "Bear", "Micro", "Short"]
```

```python
# src/discovery.py — in _filter_candidates() or asset eligibility check:
# BEFORE: no leverage screen on ETF names
# AFTER:
if cfg.universe.exclude_leveraged_etfs:
    keywords = cfg.universe.leveraged_etf_keywords
    if any(kw.lower() in asset.name.lower() for kw in keywords):
        logger.debug(f"Skipping {symbol} — leveraged ETF name match: {asset.name}")
        continue
```

**Expected impact:** AXTX would be removed from the candidate pool. The $14.5K slot would either remain as cash or be reallocated to a qualifying equity. No realized P&L impact on May 4 (AXTX was +0.43% at close), but eliminates hidden leverage risk. AXTX's 2x nature means a -1% move in underlying AXTI becomes -2% in AXTX, and the 1% stop on the ETF only guards ~0.5% of underlying risk.

**Backtest:** AXTX held at end of session with +$62 unrealized. No downside realized, but the leverage risk exposure was unquantified.

---

### 5. Add same-session reentry cooldown (`config.yaml` + `src/decision.py`)

**Why:** GOOGL was bought at 15:13 UTC and exited at 19:08 UTC (same session). FIX was bought at 15:13, increased at 18:05, and exited at 19:08. The selector treated these as fresh opportunities in subsequent scans without penalizing the recent exit. Same-day round-trips account for 7 of 11 closed positions on May 4.

**Diff:**
```yaml
# config.yaml — add under risk:
  same_session_reentry_cooldown_hours: 4.0   # don't re-enter a symbol within 4h of exiting it
```

```python
# src/decision.py — in _apply_cooldowns() or buy-gate check:
# BEFORE: cooldown only applied to entries (120-minute entry cooldown exists)
# AFTER (extend to cover reentry after exit):
exit_ts = self._get_last_exit_ts(symbol)
if exit_ts and (now - exit_ts).total_seconds() < cfg.risk.same_session_reentry_cooldown_hours * 3600:
    return DecisionResult(action=PASS, reason=f"same-session reentry cooldown ({symbol} exited {ago}m ago)")
```

**Expected impact:** On May 4: would have blocked GOOGL re-entry at 18:05 (verifier reconcile, bought 9.28 shares that were then exited at 19:08 at -$16 realized), FIX INCREASE at 18:05 (3.7 shares → immediate dust-sweep at 19:08), and potentially WDC (bought at 15:13, exited at 18:05 at -$135). Estimated savings: ~$150–200 in direct P&L plus friction avoided.

**Backtest:** From full journal, 14 unique symbols had same-day buy+sell at some point. Applying a 4h cooldown would have blocked an estimated 8–10 round-trips across the 9-day window.

---

## Offline Backtest Note

Full backtest of proposed changes was not performed. Reason: `decisions.jsonl` has 1556 entries but all `final_score`, `ai_action`, and `ai_confidence` fields are null (scores not populated in this schema version). Without numeric scores, we cannot simulate which entries the cooldown/score-filter proposals would have blocked. The exit quality analysis above (exit_learning_metrics) is the extent of what can be quantified from on-disk data.

---

*Post-mortem generated 2026-07-07 by scheduled bot. All figures from local repo files only. No network calls made.*
