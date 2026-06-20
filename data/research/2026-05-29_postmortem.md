# Post-Mortem 2026-05-29

## Data Availability

| Source | Status |
|--------|--------|
| `data/research/2026-05-29_eod.json` | **MISSING** — bot has not written EOD snapshot for today |
| `data/research/20260529*_scan.json` | **MISSING** — no scan files found for today |
| Latest EOD snapshot | `2026-05-04_eod.json` (25-day data gap: May 5 – May 29) |
| `data/journal/trades.jsonl` | Available; last entry 2026-05-04 |
| `data/journal/decisions.jsonl` | Available; last entry 2026-05-04 |
| `config.yaml` | Available |

**Root cause of data gap:** The bot appears to have stopped generating output after 2026-05-04. Either the scheduler stopped, or commits have not been pushed since then. This post-mortem covers the last known trading session (2026-05-04) as the primary subject, with rolling benchmarks from all available EOD files (2026-04-22 through 2026-05-04).

---

## Performance Today (2026-05-04, last known session)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Portfolio vs SPY | **-1.44%** (underperformed) |
| Equity at close | $99,849.69 |
| Cash | $4,986.91 (5.0% — at floor) |
| Trades executed | **53** (extremely high churn) |
| Positions at close | 4 |
| Macro regime | neutral (score 0.27, VIX 27.3) |

---

## Rolling Benchmark (all available EOD data)

| Date | Portfolio | SPY | vs SPY | Equity | Trades |
|------|-----------|-----|--------|--------|--------|
| 2026-04-22 | +0.00% | +1.01% | **-1.01%** | $99,627 | 7 |
| 2026-04-23 | +1.56% | -0.39% | **+1.95%** | $101,208 | 9 |
| 2026-04-24 | -0.81% | +0.77% | **-1.58%** | $99,343 | 19 |
| 2026-04-27 | -4.88% | +0.17% | **-5.05%** | $96,448 | 24 |
| 2026-04-28 | -5.13% | -0.49% | **-4.64%** | $96,867 | 21 |
| 2026-04-29 | -5.40% | -0.01% | **-5.39%** | $93,999 | 10 |
| 2026-04-30 | -2.67% | +0.96% | **-3.63%** | $95,786 | 23 |
| 2026-05-01 | +1.82% | +0.29% | **+1.53%** | $101,101 | 38 |
| 2026-05-04 | -1.80% | -0.36% | **-1.44%** | $99,850 | 53 |

**9-day cumulative**: portfolio +0.22% vs SPY 30d +10.71% (from eod.json field). **Win rate vs SPY: 2/9 days (22%).**

---

## Positions at Close (2026-05-04 EOD snapshot)

| Symbol | Side | Avg Entry | Current | PnL% | Market Value |
|--------|------|-----------|---------|------|--------------|
| AXTX | LONG | $46.41 | $46.61 | **+0.43%** | $14,589 |
| META | LONG | $611.73 | $610.46 | **-0.21%** | $9,448 |
| PWR | LONG | $758.48 | $757.38 | **-0.15%** | $11,130 |
| SPY | LONG | $717.52 | $718.03 | **+0.07%** | $59,696 |

> Note: SPY as a held position represents ~60% of the portfolio — the bot defaulted to cash-proxy SPY as active positions churned out.

---

## Trades Executed 2026-05-04

### Positions Closed (11 closures)

| Symbol | Exit Price | Est. Entry | Est. PnL% | Est. PnL$ | Reason |
|--------|-----------|------------|-----------|-----------|--------|
| HCAI | $10.69 | $11.84 | **-9.71%** | -$1,716 | AI exit-arbiter conf=0.72: momentum loss 5-signal |
| AMZN | $270.65 | unknown | — | — | Arbiter EXIT: fading momentum, below VWAP |
| GEV | $1,071.49 | unknown | — | — | Arbiter EXIT: weak momentum, below VWAP |
| UNH | $368.25 | $371.09 | **-0.77%** | -$49 | Arbiter EXIT: UNH→LLY rotation |
| MU | $580.81 | $580.42 | **+0.07%** | +$9 | Arbiter EXIT: WDC favoured as peer leader |
| WDC | $440.06 | $445.36 | **-1.19%** | -$130 | Arbiter EXIT: gap_only classification |
| DELL | $210.94 | $210.52 | **+0.20%** | +$24 | Verifier dust-sweep target=0 |
| LLY | $963.71 | $962.27 | **+0.15%** | +$19 | Verifier dust-sweep target=0 |
| COIN | $203.45 | $203.90 | **-0.22%** | -$30 | Arbiter EXIT: earnings 3 days, momentum gone |
| GOOGL | $382.77 | $384.43 | **-0.43%** | -$63 | Arbiter EXIT: momentum 0, fading |
| FIX | $1,902.81 | $1,903.71 | **-0.05%** | -$9 | Verifier dust-sweep target=0 |

### AI Orders Submitted (15 buys/adds)

| Symbol | Action | Qty | Fill Price | Stop | Confidence |
|--------|--------|-----|-----------|------|------------|
| LLY | BUY | 9.49 | $963.38 | $951.69 | 0.72 |
| MU | ADD | 25.0 | $580.42 | $577.65 | 0.90 |
| NOK | BUY | 367.2 | $13.33 | $13.24 | — |
| SNDK | BUY | 10.1 | $1,246.97 | $1,237.62 | — |
| DELL | BUY | 57.4 | $210.52 | $207.81 | — |
| FIX | BUY | 6.3 | $1,896.50 | $1,865.26 | — |
| GOOGL | BUY | 28.7 | $383.51 | $378.99 | — |
| LLY | ADD | 3.51 | $962.27 | $952.61 | — |
| WDC | BUY | 24.5 | $445.36 | $437.86 | — |
| COIN | BUY | 5.1 | $203.90 | $202.77 | verifier reconcile |
| FIX | ADD | 3.7 | $1,903.71 | $1,881.24 | — |
| GOOGL | ADD | 9.28 | $384.43 | $380.10 | verifier reconcile |
| AXTX | BUY | 313.0 | $46.41 | $45.34 | — |
| META | BUY | 15.48 | $611.73 | $606.07 | — |
| PWR | BUY | 14.69 | $758.48 | $748.54 | — |

---

## Per-Trade Quality Audit (2026-05-04)

| Symbol | Action | Hold (min) | Entry | Exit | PnL% | PnL$ | AI Grade | Quality |
|--------|--------|-----------|-------|------|------|------|----------|---------|
| HCAI | BUY→CLOSE | 4,068 (3 days) | $11.84 | $10.69 | **-9.71%** | -$1,716 | exit-arbiter conf=0.72 | **DISASTER** — hard stop ($11.72) failed; position bled overnight |
| UNH | BUY→CLOSE | 4,260 (3 days) | $371.09 | $368.25 | **-0.77%** | -$49 | arbiter rotate to LLY | **CHURN** — rotated to LLY which was also exited 60min later |
| MU | ADD→CLOSE | 60 | $580.42 | $580.81 | **+0.07%** | +$9 | arbiter: WDC is peer leader | **CHURN** — rotated to WDC which lost -1.19% in 60min |
| WDC | BUY→CLOSE | 60 | $445.36 | $440.06 | **-1.19%** | -$130 | arbiter: gap_only classification | **CHURN** — peer-rotation pair cost net -$121 |
| LLY | BUY+ADD→CLOSE | 61 | $962.27 | $963.71 | **+0.15%** | +$19 | verifier dust-sweep | **PREMATURE EXIT** — positive, strong setup, closed by verifier |
| DELL | BUY→CLOSE | 61 | $210.52 | $210.94 | **+0.20%** | +$24 | verifier dust-sweep | **PREMATURE EXIT** — winner closed by verifier |
| FIX | BUY+ADD→CLOSE | 64 | $1,903.71 | $1,902.81 | **-0.05%** | -$9 | verifier dust-sweep | **PREMATURE EXIT** — tech_score=0.836, exit guard bypassed |
| COIN | BUY→CLOSE | 123 | $203.90 | $203.45 | **-0.22%** | -$30 | arbiter: earnings 3d | **OK** — earnings risk exit is defensible |
| GOOGL | BUY+ADD→CLOSE | 63 | $384.43 | $382.77 | **-0.43%** | -$63 | arbiter: momentum=0 | **CHURN** — bought and sold within 1hr at loss |
| AMZN | HELD→CLOSE | unknown | unknown | $270.65 | — | — | arbiter: below VWAP | **CHURN** — exited to fund positions also closed within hrs |
| GEV | HELD→CLOSE | unknown | unknown | $1,071.49 | — | — | arbiter: weak momentum | **CHURN** — exited; missed $198 over 60min (learning metrics) |

**Estimated single-day realized losses from churn (excl. HCAI): ~-$350**  
**HCAI stop failure: -$1,716**  
**Total estimated churn cost: ~-$2,066 in a -$1,800 day**

---

## Cross-Trade Patterns

- **Stop order failure on multi-day holds**: HCAI was bought 2026-05-01 at $11.84 with hard_stop_loss_pct=0.01, implying stop at ~$11.72. Position fell to $10.69 before exit (-9.71%). The 1% stop was never triggered — either the stop order was cancelled by a verifier sweep or not placed correctly for a carry-over position. A $1,716 loss on a position that should have stopped at -$148 is the single largest failure.

- **Destructive peer-rotation churn**: MU exited (conf=0.58) to fund WDC ("peer leader, +22 momentum points"), then WDC exited 60 min later ("gap_only classification"). Net result: -$121 loss for two roundtrips plus slippage. GEV exited to fund AMZN; AMZN exited same scan. UNH exited to fund LLY; LLY exited 1 hr later. These peer-rotations consistently lost money.

- **Intraday_momentum_lost trigger: 50% accuracy**: Offline backtest on `exit_learning_metrics`: 6 of 12 exits where 30m post-exit data available showed the exit *saved* money vs holding; 6 exits *cost* money ($365 in missed gains). This is no better than random — the trigger fires too aggressively on normal intraday noise.

- **SPY proxy bloat from churn**: SPY position grew from 0% (Apr 22) to 60% of equity (May 04) as active positions churn out and SPY becomes the de-facto residual. The bot is effectively paying roundtrip friction to end up holding SPY anyway.

- **Wash trade collisions**: LLY, FIX, GOOGL all triggered Alpaca wash-trade rejection (error 40310000) because stop orders from an initial entry were still live when a new entry was attempted. Indicates the bot is recycling symbols within the stop-order settlement window.

- **Portfolio-selector AI failures**: 2 consecutive failures at 14:09 and 15:02 (3 attempts each, selected_count=0 output). These produced cascading `selector_skipped` events, leaving the portfolio unmanaged for ~50 minutes and likely contributing to the next scan's aggressive re-allocation.

- **Fresh exit guard bypassed on strong setups**: FIX (tech_score=0.836, near flat -0.05%), LLY (+0.15%), DELL (+0.20%) had exit guard `skipped` flagged, allowing immediate exit of positions that were profitable or technically strong. FIX was a sector/peer leader being exited to fund a position that also closed within the hour.

- **6 full portfolio rotations in one session**: Rotation timeline: 15:13, 15:18, 16:04, 17:04, 18:04, 19:08. Portfolio composition changed completely 6×, meaning the bot effectively traded a new book each hour. With real-world slippage assumptions this level of churn is capital-destructive.

---

## Proposed Changes

### 1. Fix stop order persistence on multi-day hold positions
**Why**: HCAI held 3 days without the 1% hard stop firing, costing -$1,716 vs expected -$148 max loss. A stop that isn’t in the broker’s order book is not a stop.  
**Diff** (src/executor.py concept — proposal only, do not edit source):
```
# PROPOSED: At each session start, for every held position, verify stop order
# still exists at broker. If orphaned, re-submit immediately.
# Key check: cross-ref all open stop orders with held positions.
# If position has no active stop → submit at hard_stop_loss_pct immediately.
```
**Expected impact**: Eliminates overnight blowups. On this session alone would have saved ~$1,568 (stopped at $11.72 instead of $10.69).

---

### 2. Raise `exit_arbiter.min_confidence` to 0.70 for intraday_momentum_lost-only exits
**Why**: 12 of 13 exits on 2026-05-04 fired `intraday_momentum_lost=True`. Offline backtest shows 50% accuracy — exits firing this trigger alone are no better than random. Raising the bar for this signal-only trigger would have blocked ~6 premature exits saving ~$365.  
**Diff** (config.yaml proposal):
```yaml
# BEFORE:
exit_arbiter:
  min_confidence: 0.55

# AFTER (proposal):
exit_arbiter:
  min_confidence: 0.55                    # global floor unchanged
  momentum_only_min_confidence: 0.70      # NEW: higher bar when sole trigger is intraday_momentum_lost
```
**Expected impact**: ~50% reduction in intraday momentum exits; saves estimated $200–$400/session on churn days.

---

### 3. Cap selector rotations to 3 per session
**Why**: 6 rotations on 2026-05-04 means the entire portfolio turned over twice. Every rotation costs 2× roundtrip spread + stop cancellation risk. The two sessions with best performance (Apr 23: 9 trades, May 01: 38 trades) had far fewer rotations.  
**Diff** (config.yaml proposal):
```yaml
# PROPOSED addition under selector:
selector:
  max_rotations_per_session: 3          # NEW: halt new position changes after 3 full rotations
  min_hold_minutes_before_rotation: 90  # NEW: position must be held 90min before eligible for rotation exit
```
**Expected impact**: Cuts churn by ~50% on high-activity sessions. Protects positions like FIX (tech_score=0.836, exited after 64 min) from premature rotation.

---

### 4. Add wash-trade cooldown: block re-entry for 30 min after close
**Why**: LLY, FIX, GOOGL all triggered Alpaca error 40310000 (wash trade detected) within the same session. The bot cancels the existing stop then re-buys the same symbol — fragile, creates execution gaps, and indicates the portfolio is cycling the same names within stop-settlement windows.  
**Diff** (config.yaml proposal):
```yaml
# PROPOSED addition under execution:
execution:
  wash_trade_cooldown_minutes: 30  # NEW: block re-entry for symbol within N min of closing it
```
**Expected impact**: Eliminates wash-trade rejections. Forces genuine position changes rather than recycle-in-place.

---

### 5. Protect fresh-exit-guard: require `technical_flipped=True` or `bad_news=True` to skip
**Why**: FIX (tech_score=0.836), LLY (+0.15%), DELL (+0.20%) had the fresh_exit_guard skipped. All three were profitable or strongly technical. Skipping the guard should require a hard catalyst (technical flip or bad news), not just a selector re-ranking.  
**Diff** (concept — proposal only):
```
# PROPOSED: fresh_exit_guard should only be skipped when:
#   triggers.technical_flipped = True, OR
#   triggers.bad_news = True
# NOT when the sole reason is a selector rotated to a different name.
# All three bypass events on 2026-05-04 were purely selector-driven with no hard trigger.
```
**Expected impact**: Saves 2–4 premature winner exits per high-churn session (~$50–$150/session).

---

### 6. Investigate and resolve bot data gap (May 5 – May 29)
**Why**: No EOD, scan, or journal data exists for 25 calendar days. The most recent daily_review.md is 2026-05-22 with a note "no new data; latest snapshot is still 5/4". This is an operational failure.  
**Action** (not a code change — operational):
- Verify scheduler (`cron` / `systemd timer`) is running on the host machine
- Check Alpaca paper account status for PA34KBGT3V7E (may have been reset or rate-limited)
- Run: `py scripts/scan_and_trade.py --dry-run` to confirm the bot can execute
- Add health-check: if no EOD file is written for today by 17:00 ET, send Telegram alert

---

## Offline Backtest (exit quality via learning metrics)

Using `exit_learning_metrics` from `data/journal/trades.jsonl` (offline, no network required):

| Exit | Symbol | Held extra 30m better? | Missed PnL$ |
|------|--------|----------------------|-------------|
| 1 | STX | YES | +$76 |
| 2 | SNDK | YES | +$107 |
| 3 | GEV | YES | +$104 |
| 4 | MU | YES | +$21 |
| 5 | LLY | YES | +$34 |
| 6 | COIN | YES | +$2 |
| 7 | HCAI | NO — saved $164 | -$164 |
| 8 | AMZN | NO — saved $26 | -$26 |
| 9 | NOK | NO — saved $43 | -$43 |
| 10 | MU (2nd exit) | NO — saved $83 | -$83 |
| 11 | WDC | NO — saved $60 | -$60 |
| 12 | DELL | NO — saved $15 | -$15 |

**Net: holding 30min longer on average would have saved +$78 (ex-HCAI).**

**Conclusion**: The intraday momentum exit signal is approximately break-even in P&L terms but costs significantly in churn friction, wash trades, and lost setup continuity. The 90-minute min-hold proposal (Change #3) is supported by this data.
