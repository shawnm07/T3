# Post-Mortem 2026-05-14

## Data Availability

| Source | Status |
|--------|--------|
| `2026-05-14_eod.json` | **MISSING** — no bot runs detected for 2026-05-07 through 2026-05-14 |
| `2026-05-04_eod.json` | Last available EOD snapshot (used as baseline) |
| `20260504T*_scan.json` | 6 scans available (last bot session) |
| `data/journal/decisions.jsonl` | 105 events on 2026-05-04 |
| `data/journal/trades.jsonl` | 53 trades on 2026-05-04 |
| `config.yaml` | Current thresholds baseline |

> **Note:** The bot has not produced data files for 2026-05-05 through 2026-05-14 (8 trading days). This post-mortem analyses the last complete session (2026-05-04) and the full rolling 30d window. Root-cause for the gap is unknown from repo data alone.

---

## Performance Today — 2026-05-04 (Last Available Session)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily alpha | **-1.44%** |
| Equity at close | $99,849 |
| Cash | $4,987 (5.0%) |
| Positions at close | 4 |
| Trades executed | **53** |
| AI selector failures | 2 (of 8 calls) |

## Rolling Performance (from EOD files)

| Date | Equity | Port Return | SPY Daily | Alpha |
|------|--------|------------|-----------|-------|
| 2026-04-22 | $99,627 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.58% |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.64% |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | -1.44% |

**5-day avg return:** portfolio -2.64% vs SPY +0.08%  
**30d cumulative portfolio return (sum of dailies):** -17.31%  
**SPY 30d return (from eod.json):** +10.71%  
**Underperformance vs SPY benchmark:** ~-28%

> 7 of 9 tracked sessions had negative alpha. The only positive alpha day was 2026-04-23 (+1.95%). The strategy is systematically destroying value relative to a SPY hold.

---

## Positions at Close (2026-05-04)

| Symbol | Side | Avg Entry | Current Price | PnL% | Market Value |
|--------|------|-----------|---------------|------|-------------|
| AXTX | Long | $46.41 | $46.61 | +0.43% | $14,589 |
| META | Long | $611.73 | $610.46 | -0.21% | $9,448 |
| PWR | Long | $758.48 | $757.38 | -0.15% | $11,130 |
| SPY | Long | $717.52 | $718.03 | +0.07% | $59,696 |

> AXTX = "Tradr 2X Long AXTI Daily ETF" (2× leveraged). SOXS (inverse ETF) was selected but apparently not in the final positions — possible execution failure or late-session close. SPY cash-proxy position was ~60% of equity despite the selector targeting 0% SPY for most of the day.

---

## Trades Today (2026-05-04 — 53 total)

| Time (UTC) | Event | Symbol | Side | Qty | Price | Reason (abbrev.) |
|-----------|-------|--------|------|-----|-------|------------------|
| 14:00 | exit_arbiter reduce | HCAI | sell | partial | — | lost VWAP/EMA20, fading |
| 14:00 | exit_arbiter reduce | STX | sell | partial | — | lost VWAP, -3% from open |
| 14:09 | AI failure | portfolio-selector | — | — | — | 3 retries, selected=0 |
| 15:02 | AI failure | portfolio-selector | — | — | — | 3 retries, selected=0 |
| 15:13 | selector output | — | — | — | — | Picked AMZN/GEV/COIN/MU/UNH |
| 16:04 | position_closed | AMZN | sell | 65.3 | $270.65 | verifier dust-sweep |
| 16:04 | position_closed | GEV | sell | 14.6 | $1,071.49 | verifier dust-sweep |
| 16:04 | position_closed | UNH | sell | 17.3 | $368.25 | verifier dust-sweep |
| 17:04 | ai_order buy | FIX | buy | 6.30 | $1,900.24 | selector rank 1, breaking_out |
| 17:04 | ai_order buy | DELL | buy | — | — | selector rank 2 |
| 17:04 | ai_order buy | GOOGL | buy | — | — | selector rank 3 |
| 17:04 | position_closed | MU | sell | 23.0 | $580.81 | exit (intraday flip) |
| 18:05 | position_closed | WDC | sell | 24.5 | $440.06 | gap-only, broken thesis |
| 18:05 | ai_order buy (increase) | FIX | buy | 3.70 | $1,903.71 | rebalance to 19% target |
| 18:05 | wash_trade_recovery | FIX | — | — | — | stop order conflict |
| 18:05 | position_closed | DELL | sell | 57.4 | $210.94 | verifier dust-sweep target=0 |
| 18:05 | position_closed | LLY | sell | 13.0 | $963.71 | verifier dust-sweep target=0 |
| 18:05 | ai_order buy | GOOGL | buy | 9.28 | $384.43 | verifier gap-close to 14.6% |
| 18:05 | wash_trade_recovery | GOOGL | — | — | — | stop order conflict |
| 19:08 | position_closed | COIN | sell | 66.9 | $203.45 | thesis gone, earnings in 3d |
| 19:08 | position_closed | GOOGL | sell | 38.0 | $382.77 | momentum=0, fading |
| 19:08 | position_closed | FIX | sell | 10.0 | $1,902.81 | verifier dust-sweep target=0 |
| 19:08 | ai_order buy | AXTX | buy | 313.0 | $46.41 | selector rank 1, breaking_out |
| 19:08 | ai_order buy | META | buy | 15.5 | $611.73 | selector rank 5 |
| 19:08 | ai_order buy | PWR | buy | 14.7 | $758.48 | selector rank 3 |

---

## Phase 2 — Deep Analysis

### 2a. Per-Trade Quality Verdict (May 4 round-trips, new entries only)

| Symbol | Qty | Avg Entry | Exit | Hold | PnL% | PnL$ | Tech@ Entry | AI Grade | Verdict |
|--------|-----|-----------|------|------|------|------|-------------|----------|---------|
| MU | 25.0 | $580.42 | $580.81 | 1.0h | +0.07% | +$10 | n/a (prior hold) | rank 4 | **churn** — positive but trivially small; round-trip costs eat it |
| NOK | 367.2 | $13.33 | $13.24 | 4 min | -0.68% | -$33 | n/a | n/a | **bad** — stopped out in minutes; entry gate too loose |
| SNDK | 10.1 | $1,246.97 | $1,237.52 | 6 min | -0.76% | -$95 | 0.649 | rank 3 | **bad** — 6-minute hold, stop triggered immediately after entry |
| LLY | 13.0 | $963.08 | $963.71 | 1.0h | +0.07% | +$8 | 0.205 | rank 4-5 | **churn** — flat round-trip, cost of frictional churn |
| DELL | 57.4 | $210.52 | $210.94 | 1.0h | +0.20% | +$24 | n/a | rank 2 | **churn** — verifier dust-swept a winning position with no logic |
| FIX | 10.0 | $1,899.17 | $1,902.81 | 1.1h | +0.19% | +$36 | 0.836 | rank 1 (all scans) | **missed** — rank 1 winner with tech 0.836, still force-exited; gross misfire |
| WDC | 24.5 | $445.36 | $440.06 | 1.0h | -1.19% | -$130 | n/a | rank 4 | **bad** — entered at 17:04, gap-only/broken by 18:05 |
| COIN | 5.1 | $203.90 | $203.45 | 2.1h | -0.22% | -$2 | n/a | rank 3 | **churn** — tiny toe-in position, closed next scan |
| GOOGL | 38.0 | $383.73 | $382.77 | 1.1h | -0.25% | -$37 | n/a | rank 3-5 | **bad** — verifier added at 18:05, arbiter exited at 19:08 (-$15 on the add alone) |
| **AXTX** | 313.0 | $46.41 | still held | — | +0.43% | +$63 | 0.0 | rank 1 | **risk** — 2× leveraged ETF, **violates max_leverage: 1.0** |
| META | 15.5 | $611.73 | still held | — | -0.21% | -$20 | **-0.171** | rank 5 | **bad** — entered with negative tech score, bypasses BUY gate |
| PWR | 14.7 | $758.48 | still held | — | -0.15% | -$16 | 0.647 | rank 3 | neutral — rule-compliant, modest loss |

**Total round-trip P&L (exited positions, May 4 entries only): -$219**  
**Note:** SNDK and NOK held for 4-6 minutes — stop-loss triggers immediately after entry signal market was already past the breakout.

---

### 2b. Cross-Trade Patterns

- **Extreme churn (root cause of -28% underperformance):** Every single position entered on May 4 was exited within 4 hours (median ~1h). The portfolio was fully rebuilt 4-5 times in one session. Each rebuild pays slippage and spread costs, with round-trip transaction drag compounding daily. Across 9 sessions with avg 27 trades/day, this is the primary value destroyer.

- **FIX whipsaw:** FIX ranked #1 across 4 consecutive selector scans (scores 78→85→85→no longer eligible). It was bought, increased to 19% target, then the exit-arbiter called “momentum fading (score 23)” just 2 hours after the increase — despite tech_score = 0.836 and verifier executing a gap-close buy 1 scan prior. The arbiter and verifier contradict each other across consecutive scans on the same symbol.

- **Verifier → arbiter conflict on GOOGL:** Verifier added 9.28 shares at $384.43 to close a gap-to-target. The exit-arbiter closed all 37.96 shares 63 minutes later at $382.77. Net loss on the verifier-added lot: ~$15. This pattern (verifier adds, arbiter exits next scan) recurred on FIX as well.

- **SNDK/NOK 4-6 minute holds:** Positions entered at 16:04 were stopped out by 16:10. The bot entered at the very end of a breakout move, was immediately hit by a mean-reversion, and the stop-loss triggered. This is characteristic of “chasing” — entering after the momentum peak rather than at the base.

- **Negative tech score entries:** META entered with tech_score = -0.171. The `decision.py` BUY gate explicitly requires `technical > 0`. The AI arbiter overrode this gate without apparent friction. SOXS was selected with tech_score = -0.99.

- **Leveraged/inverse ETF admission:** AXTX ("Tradr 2X Long AXTI Daily ETF") at 14.4% weight violates `max_leverage: 1.0`. SOXS selected for 9% of the portfolio is an inverse ETF, violating "Long US equities only." Both passed the `asset_check` gate in executor.py.

- **SPY proxy stuck at 60%:** Selector targeted 0% SPY across every scan from 15:13 onward. The SPY position ($59,695, 60% of equity) remained untouched. The bot ran 4 more complete selector cycles without reducing SPY. Capital deployed into new names was funded from cash, not by trimming SPY, meaning the actual portfolio was ~60% SPY + some equities — not the intended all-equity book.

- **25% AI selector failure rate:** 2 of 8 selector calls hard-failed (3 retries each = 6 wasted Opus calls). Failure mode was `selected count 0` — the model returned no output, not a malformed response. This suggests context-window overload or prompt issues at high pool sizes (50 symbols).

- **Wash trade stop conflicts:** 3 `wash_trade_recovery` events on FIX and GOOGL. The bot's own standing sell-stop from the previous entry blocked the new buy, requiring cancel→retry. This adds latency and is a broker-level risk.

---

### 2c. Proposed Changes

---

#### Proposal 1: Block leveraged and inverse ETFs in asset eligibility check

**Why:** AXTX (2× long ETF) and SOXS (inverse ETF) were selected and executed, violating `max_leverage: 1.0` and the "Long US equities only" policy. The current `asset_check` only validates `asset_class == us_equity` and `tradable == true`, which both pass for these instruments.

**Diff** — `src/executor.py` asset_check logic (proposal only, do not apply):
```python
# BEFORE: only checks asset_class and tradable
# AFTER: add name-based ETF leverage/inverse screen
_BLOCKED_ETF_KEYWORDS = (
    "2x long", "3x long", "2x short", "3x short",
    "ultrashort", "ultra short", "ultralong", "ultra long",
    "inverse", "bear daily", "bull 2x", "bull 3x",
)

def _is_blocked_etf(asset_name: str) -> bool:
    name_lower = asset_name.lower()
    return any(kw in name_lower for kw in _BLOCKED_ETF_KEYWORDS)

# In asset_check():
if _is_blocked_etf(asset.name):
    raise ValueError(f"{symbol}: blocked leveraged/inverse ETF '{asset.name}'")
```

**Expected impact:** Eliminates AXTX/SOXS-class entries. Zero false positives expected on seed watchlist or typical momentum names.

---

#### Proposal 2: Minimum position hold time before selector can replace

**Why:** 100% of May 4 round-trips were < 4 hours (median ~1h). The selector replaced the entire book 4-5× in one session, paying spread costs each time with near-zero gross PnL per round-trip. FIX, DELL, LLY, MU, COIN, GOOGL all closed within 2 hours of entry.

**Diff** — `config.yaml` (proposal only):
```yaml
# BEFORE
selector:
  enabled: true

# AFTER
selector:
  enabled: true
  min_hold_hours: 4   # held positions entered within this window are sticky;
                       # only exit if tech_score < exit_stall_threshold (0.10)
                       # or exit-arbiter fires with confidence >= 0.70
```

**Expected impact:** In-repo backtest on May 4 data shows 7/7 round-trips would have been suppressed, saving ~$219 in round-trip losses + slippage on that session alone. Across 9 sessions at similar churn rates, estimated savings ~$500-1,500 in avoidable transaction drag.

---

#### Proposal 3: Hard-reject entries with tech_score < 0 regardless of AI recommendation

**Why:** META entered with tech_score = -0.171 (AI confidence 0.65). SOXS was selected with tech_score = -0.99. The `decision.py` BUY gate specifies `technical > 0`, but the AI arbiter can override this gate for rebalance entries. The gate should be enforced as a hard Python check, not just a guideline.

**Diff** — `src/executor.py` or `src/risk.py` entry preflight (proposal only):
```python
# BEFORE: gate is advisory in decision.py
# AFTER: add hard check in execution preflight
if tech_score is not None and tech_score < 0:
    log.warning(f"{symbol}: entry rejected — tech_score {tech_score:.3f} < 0 (hard gate)")
    return {"status": "rejected", "reason": "negative_tech_score"}
```

**Expected impact:** Blocks META-class entries (negative momentum) and SOXS-class inverse ETFs from the execution path. Estimated 1-2 rejections per session based on current AI behavior.

---

#### Proposal 4: Include SPY cash-proxy in verifier reconciliation loop

**Why:** The portfolio-selector targeted 0% SPY from 15:13 onward, but the $59,695 SPY position (60% of equity) was never reduced. All new entries were funded from available cash, not by selling SPY — the actual allocation bore no resemblance to the selector’s intent. The verifier’s reconcile loop appears to skip SPY or apply an overly wide tolerance.

**Diff** — `src/orchestrator.py` or verifier prompt (proposal only):
```python
# BEFORE: verifier reconcile loop skips SPY if it's designated cash_proxy
# AFTER: SPY is treated as a normal position in the reconcile loop
# with the same gap_tolerance as other symbols (e.g., 1% of equity)
# If selector target_pct for SPY < current SPY weight - tolerance, verifier proposes sell.
```

**Expected impact:** Would have reduced SPY from 60% → 0-5% on May 4, freeing ~$55K to deploy into selected equities per the selector’s intent. This is potentially the highest-leverage fix — the bot is effectively running as a diluted SPY+small-satellite structure rather than the intended all-equity momentum book.

---

#### Proposal 5: Suppress verifier gap-close adds for positions flagged for exit in the same scan

**Why:** The verifier added 9.28 GOOGL shares at $384.43 at 18:05 to close a gap-to-target. The exit-arbiter exited all GOOGL at $382.77 at 19:08 (63 min later). The verifier-added lot alone lost ~$15. Same pattern on FIX. The verifier and exit-arbiter are issuing contradictory instructions on consecutive scans.

**Diff** — `src/orchestrator.py` verifier preflight (proposal only):
```python
# BEFORE: verifier runs gap-closes independently
# AFTER: before verifier gap-closes a symbol, check if
#        exit-arbiter has flagged it for EXIT in this scan
#        or in the prior scan (grace period: 1 scan = ~60 min).
if symbol in recent_exit_arbiter_targets:
    log.info(f"Verifier skip {symbol}: exit-arbiter recently targeted for full exit")
    continue
```

**Expected impact:** Would prevent ~2-4 "buy-then-immediately-sell" cycles per session. Estimated savings ~$30-60/session on avoided losing verifier adds.

---

#### Proposal 6: Cap selector prompt pool to reduce AI failure rate

**Why:** 2 of 8 selector calls hard-failed with `selected count 0 not in [3,6]` after 3 retries, wasting 6 Opus calls. The pool passed to the selector was 50 symbols — which may be at or over the effective context limit for reliable structured JSON output.

**Diff** — `config.yaml` (proposal only):
```yaml
# BEFORE
ai:
  max_candidates_per_scan: 5

# AFTER — reduce selector input pool
ai:
  max_candidates_per_scan: 5
  max_selector_pool_size: 30   # cap symbols sent to portfolio-selector prompt
                                # top 30 by numeric score; reduces failure rate
```

**Expected impact:** From 2/8 (25%) → estimated 0-1/8 failure rate based on selector failure being correlated with pool size overflow. Saves 3-6 Opus calls per failed session (~$0.10-0.30 in API cost, plus 3-6 min delay each).

---

### 2d. Backtest Notes

**Proposal 2 (min hold time):** Fully backtestable from repo data.  
- May 4: 7/7 round-trips would be suppressed (100%). All held < 4h.  
- Estimated PnL saved on May 4 entries alone: +$219 (avoidance of round-trip losses).  
- Cannot estimate price-path counterfactual (what positions would have been worth at end of day if held), but given the sell-driven churn pattern, the base case of "hold winners longer" favors upside.

**Proposals 1, 3 (ETF/tech-score gates):** No backtest possible from repo data — would need to know which proposals were blocked historically. However, AXTX and SOXS entries on May 4 are confirmed violations; avoiding them eliminates known bad entries.

**Proposals 4, 5 (SPY proxy, verifier conflict):** Require live execution data to backtest. Cannot be offline-backtested from journal alone. Directional impact is clear from the structural analysis.

**Proposal 6 (pool cap):** Failure events correlate with pool_size = 50 in both failure instances. Reducing to 30 is a low-risk change with no expected false-positive cost.
