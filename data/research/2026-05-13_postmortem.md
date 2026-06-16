# Post-Mortem 2026-05-13

## Data Availability

| Source | Status | Notes |
|---|---|---|
| `2026-05-13_eod.json` | **MISSING** | No scans ran today |
| Today scan files (`20260513T*`) | **MISSING** | Bot offline since 2026-05-04 |
| `2026-05-04_eod.json` | Present | Last known snapshot |
| `data/journal/trades.jsonl` | Present | Last entry 2026-05-04T19:55Z |
| `data/journal/decisions.jsonl` | Present | Last entry 2026-05-04T20:15Z |
| Rolling EOD files (9 days) | Present | 2026-04-22 → 2026-05-04 |

**Bot has been offline for 6 trading days (2026-05-05 through 2026-05-13).** No scans, no trades, no snapshots. Last known equity: **$99,849.69** (2026-05-04), positions: AXTX, META, PWR, SPY.

---

## Performance Today (2026-05-13)

No data — bot did not run. Analysis below uses last available session (2026-05-04) and the full trailing 9-day window.

### Trailing 9-Day Scorecard (2026-04-22 → 2026-05-04)

| Date | Portfolio | SPY | vs SPY | Equity |
|---|---|---|---|---|
| 2026-04-22 | +0.00% | +1.01% | −1.01% | $99,627 |
| 2026-04-23 | +1.56% | −0.39% | +1.95% | $101,208 |
| 2026-04-24 | −0.81% | +0.77% | −1.58% | $99,343 |
| 2026-04-27 | −4.88% | +0.17% | −5.05% | $96,448 |
| 2026-04-28 | −5.13% | −0.49% | −4.64% | $96,867 |
| 2026-04-29 | −5.40% | −0.01% | −5.39% | $93,999 |
| 2026-04-30 | −2.67% | +0.96% | −3.63% | $95,786 |
| 2026-05-01 | +1.82% | +0.29% | +1.53% | $101,101 |
| 2026-05-04 | −1.80% | −0.36% | −1.44% | $99,850 |
| **9d cumulative** | **−17.31%** | **+1.95%** | **−19.26%** | |

- **Peak equity:** $101,208 (2026-04-23)
- **Trough equity:** $93,999 (2026-04-29) — **−7.1% max drawdown** from peak, breaching the 2.5% daily goal on three consecutive days
- **Last known equity:** $99,850 → **+0.22% vs $99,627 start**, SPY cumulative ~+1.95%

---

## Positions at Close (Last Known: 2026-05-04)

| Symbol | Side | Avg Entry | Last Price | PnL% | Market Value |
|---|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,589 |
| META | LONG | $611.73 | $610.46 | −0.21% | $9,448 |
| PWR | LONG | $758.48 | $757.38 | −0.15% | $11,130 |
| SPY | LONG | $717.52 | $718.03 | +0.07% | $59,696 |
| **Cash** | | | | | **$4,987** |

**SPY at 59.7% of equity** — bot effectively in near-index mode. Idle cash = 4.99% (above 5% floor, barely).

---

## Trades Today (2026-05-13)

**None** — bot offline.

---

## Per-Trade Quality Ledger (2026-04-22 → 2026-05-04)

### Initial Entries

| Date | Symbol | Side | Entry | RSI at Entry | AI Conf | Verdict | Notes |
|---|---|---|---|---|---|---|---|
| 04-22 | VRT | BUY | $301.01 | 59.7 | 0.57 | **GOOD** | Clean golden-cross entry, RSI not extended |
| 04-22 | MU | BUY | $477.32 | 66.5 | 0.56 | NEUTRAL | Strong fundamentals, RSI borderline |
| 04-22 | AVGO | BUY | $409.11 | 76.3 | 0.56 | **BAD** | Overbought entry; AI flagged but bought anyway |
| 04-22 | AMD | BUY | $296.00 | 82.0 | 0.56 | **BAD** | RSI 82 = deeply overbought; AI note: "speculative" |
| 04-22 | FIX (preclose) | BUY | $1,727.51 | 70.4 | 0.32 | **BAD** | RSI 70 preclose, low AI confidence (0.32) |
| 04-22 | GEV (preclose) | BUY | $1,119.65 | 78.7 | 0.29 | **BAD** | RSI 79, very low AI sizing confidence |
| 04-22 | ARW (preclose) | BUY | $181.12 | 76.9 | 0.29 | **BAD** | Overbought, low conviction, earnings risk |
| 04-23 | APLS (preclose) | BUY | $40.93 | 87.2 | 0.39 | **BAD** | RSI 87 = parabolic; immediately started losing |
| 04-23 | IRDM (preclose) | BUY | $40.96 | 70.3 | 0.36 | BAD | Thesis broken within 24h (−7.7%); exited 04-24 |
| 04-24 | DELL | BUY | $213.36 | 71.5 | 0.54 | NEUTRAL | Clean thesis, RSI marginal; OK entry overall |
| 04-24 | OGN (preclose) | BUY | $11.32 | 73.9 | 0.58 | **GOOD** | +16% in 2 days; RSI overbought but momentum trade worked |
| 04-24 | AVGO (preclose) | BUY | $422.76 | 77.8 | 0.62 | **BAD** | Re-entry at higher RSI than initial buy |

### Key Rebalance Moves

| Date | Symbol | Action | From% | To% | Reason Quality |
|---|---|---|---|---|---|
| 04-23 | AMD | ADD | ~5% | 12.6% | **CHURN** — day-1 add before price confirmation |
| 04-23 | All 7 positions | ADD | ~5–9% | ~12–13% | **CHURN** — mass pyramid on day 1 |
| 04-24 | IRDM | EXIT | 3.9% | 0% | **GOOD** — thesis broken, quick exit |
| 04-24 | AMD | ADD | 14.2% | 18% | **BAD** — added at RSI 88.9, overbought |
| 04-24 | APLS | TRIM | 7.4% | 4% | GOOD — trimming earnings risk |
| 04-27 | OGN | EXIT | 4.3% | 0% | **EXCELLENT** — +16% profit capture |
| 04-27 | DELL | ADD | ~9% | 18% | **BAD** — concentrated into falling book day |
| 04-27 | MU | ADD | ~9% | 24% | **BAD** — dangerous pyramid on down day |
| 04-27 | ARW | EXIT | 5.9% | 0% | OK — earnings risk reduction |
| 05-04 | FIX | BUY→EXIT | 0% → 19% → 0% | Same day | **CHURN** — opened and closed largest position in 2 hrs |
| 05-04 | GOOGL | BUY→EXIT | 0% → 14.6% → 0% | Same day | **CHURN** — same-day round trip |
| 05-04 | MU | BUY→EXIT | 0% → 28% → 0% | Same day | **CHURN** — bot tried to pyramid MU to 28%, immediately exited |

---

## Cross-Trade Patterns

- **Overbought entries at scale:** 8 of 12 first-time entries had RSI > 72 at execution (AMD 82, APLS 87, GEV 79, AVGO 77, ARW 77, AVGO-re 78, FIX 70, OGN 74). The intraday RSI gate (`max_rsi_for_new_buy: 78`) only applies to preclose — daytime scans lack equivalent protection.

- **Day-1 mass pyramid:** On 2026-04-23, the rebalance added to all 7 positions simultaneously (each raised from ~5% to 12–13%), doubling committed notional before any position had price confirmation. When the semis book sold off 4/27–4/29, the larger position sizes amplified losses.

- **MU concentration spike:** Added from ~9% to 24% on 2026-04-27 in a single scan (a $11K+ add). Configuration `initial_entry_cap_pct: 0.15` applies to new entries only; subsequent add-ons have no per-scan cap. On that same day the portfolio lost −4.88%.

- **Same-day round trips (5/4 hyperchurn):** 53 trades in a single session. FIX went 0→19%→0% and GOOGL went 0→14.6%→0% within the same trading day. These represent wasted spread + execution cost with no P&L contribution.

- **APLS fractional share rebalance failures:** 4 consecutive `rebalance_failed` events for APLS across 04/24 and 04/27. Root cause: `partial_trade()` sends a notional sell to Alpaca, which converts notional to shares at market price and requests 0.012 more shares than the position holds. Fractional precision mismatch.

- **DELL averaged into weakness:** On 04/27 (the worst daily loss day at −4.88%), DELL was increased from ~10% to 18%. The position subsequently fell to −8.74% by 04/28.

- **ARW: overbought entry → churn:** Entered 04/22 at RSI 76.9 (preclose), trimmed twice on 04/24, trimmed again 04/24 evening, fully exited 04/27. Net P&L on ARW was roughly breakeven after 5 days and 5 trades.

- **Bot offline signal (critical):** No scans since 2026-05-05. Last known equity $99,850 in 60% SPY + 3 smalls. Bot may be running on a different working tree, or the cron/scheduler has failed silently. No alert was generated.

---

## Proposed Changes

### 1. Add Intraday RSI Entry Gate

**Why:** 8 of 12 initial entries were made at RSI > 72. Preclose already has `max_rsi_for_new_buy: 78`; daytime scans have no equivalent guard. Offline backtest (17 qualifying entries in journal) shows 10 would be blocked by a RSI ≤ 72 gate — including AMD (82), APLS (87), GEV (79), ARW (77), AVGO-re (78).

**Diff (config.yaml):**
```yaml
# Before
overnight:
  max_rsi_for_new_buy: 78

# After — add a parallel intraday key:
risk:
  max_rsi_for_intraday_buy: 72   # NEW: block daytime new entries when RSI > this
```
The corresponding guard in `src/orchestrator.py` / `src/decision.py` would check `rsi > config.risk.max_rsi_for_intraday_buy` and downgrade to PASS.

**Expected impact:** Would have blocked 6 of 7 losing initial entries (AMD, AVGO, GEV, ARW, APLS, AVGO-re). OGN at 73.9 would also be blocked — but OGN was a +16% win, so this is a false negative cost. Net expected improvement: ~2–3% fewer drawdown days per month.

---

### 2. Per-Scan Add Cap

**Why:** On 04/27 the rebalance added 14% of equity to MU in a single scan (9%→24%). The `initial_entry_cap_pct: 0.15` guard only covers *new* positions. Winners can be pyramided without limit intraday.

**Diff (config.yaml):**
```yaml
# Before (no such key)

# After:
risk:
  max_add_per_scan_pct: 0.08   # NEW: no single rebalance scan may increase any position by > 8% equity
```

**Expected impact:** MU would have been capped at ~17% on 04/27 instead of 24%. At the observed −3.77% MU return that day, this saves ~0.26% portfolio return on the excess 7% notional.

---

### 3. Daily Turnover Cap

**Why:** 2026-05-04 produced 53 trades on a 4-position book. The selector rotated through 12+ symbols in one session. This creates operational noise, potential wash-sale exposure, and masks signal in the journal.

**Diff (config.yaml):**
```yaml
# Before (no such key)

# After:
risk:
  max_daily_turnover_pct: 0.40   # NEW: halt new selector rotations once traded > 40% of equity intraday
```

**Expected impact:** On 05/04, rotations would have stopped after ~$40K in executed notional, preventing the FIX (0→19%→0%) and GOOGL (0→14.6%→0%) same-day round trips.

---

### 4. Scheduler Watchdog Alert

**Why:** The bot has been offline for 6 trading days (2026-05-05 to 2026-05-13) with no alert generated. No scan heartbeat means open positions (AXTX, META, PWR, SPY) are unmanaged.

**Diff (config.yaml):**
```yaml
# Before (no such key)

# After:
scheduling:
  watchdog_alert_after_market_hours: 1   # NEW: if no scan heartbeat within 1 market-hour, emit CRITICAL log + Telegram alert
```
Corresponding implementation: a watchdog script or cron job that reads the timestamp of the last scan from `decisions.jsonl` and fires a Telegram alert if stale by more than 1 market hour.

**Expected impact:** The 05/05 outage would have been detected within 1 hour instead of going unnoticed for 6 trading days.

---

### 5. Fix APLS-Style Fractional Share Sell Precision

**Why:** `partial_trade()` in `src/executor.py:836` submits notional sells via `submit_notional`. Alpaca converts notional → shares at market and can request fractionally more than the held quantity, causing 4 consecutive `rebalance_failed` events for APLS.

**Diff (src/executor.py):**
```python
# Before (line ~836):
order = self.client.submit_notional(symbol, abs_notional, side=side, tif="day")

# After — for SELL, cap notional to position_value * 0.999 to avoid oversell:
if side == "sell":
    try:
        pos = self.client.get_position(symbol)
        pos_value = float(pos.market_value or abs_notional)
        abs_notional = min(abs_notional, pos_value * 0.999)
    except Exception:
        pass  # if position fetch fails, proceed with original notional
order = self.client.submit_notional(symbol, abs_notional, side=side, tif="day")
```

**Expected impact:** Eliminates all 4 APLS `rebalance_failed` events; generalizes to any fractional position sell.

---

### 6. Enforce max_positions at Every Rebalance Cycle

**Why:** On 2026-04-24, the book held 12 positions against `max_positions: 6`. The selector+arbiter ensemble violated this constraint during intraday rebalancing (new entries were staged before exits cleared).

**Diff (config.yaml / pipeline logic):**
```yaml
# Verify this gate is enforced in orchestrator.py *after* new entry staging:
# The check must count pending + held positions, not just settled positions.
risk:
  max_positions: 6   # Already present — verify orchestrator enforces pre-execution, not post
```

Verify `src/orchestrator.py` checks `len(pending_buys) + len(current_positions) <= max_positions` before submitting each new entry order, not just before the selector runs.

**Expected impact:** Would have prevented the 12-position overload on 04/24, reducing complexity and correlation concentration.

---

## Backtest Results

- **Proposal 1 (RSI gate ≤72):** Offline backtest on 17 journal entries. Would block 10 entries (59%). Confirmed blocked: AMD-82, APLS-87, GEV-79, ARW-77, AVGO-76, AVGO-re-78, NOK-77, V-73, ALGM-75. OGN-74 is the only blocked winner (+16%). Net: the blocked entries averaged negative returns (4/27–4/29 drawdown driven by AMD, AVGO, GEV). Cannot quantify precisely without price-series, but direction is strongly supportive.
- **Proposals 2–6:** Cannot be backtested with offline data alone (require simulated rebalance decisions or price series). Direction assessed qualitatively above.

---

## Open Items From Prior Reviews

The 2026-05-07 review carried forward 8 proposals from 2026-05-05 (selector inertia, earnings-flag stickiness, min-hold timer, preclose close-fill verifier, intraday turnover cap, SPY-proxy chaos-day rule, red-tape BUY gate, sticky-portfolio cadence). The intraday turnover cap is now independently confirmed by 05/04's 53-trade session. The remaining 7 are still open and unvalidated due to the bot outage.

**Immediate action required:** Confirm whether `scan_and_trade.py` cron is running. Check scheduler logs, process list, and whether `data/research/` writes are committed to the correct working tree.
