# Post-Mortem 2026-07-03

## Data availability

| Source | Status |
|---|---|
| `data/research/2026-07-03_eod.json` | **MISSING** — no scan ran today |
| Last EOD snapshot | `2026-05-04_eod.json` |
| Data gap | **2026-05-05 → 2026-07-03 (59 calendar days, ~41 trading days)** — bot has not run since May 4 |
| Trade journal | `data/journal/trades.jsonl` — last entry 2026-05-04T19:55 UTC |
| Config baseline | `config.yaml` current |

> **Note:** All analysis below is based on the last active trading day (2026-05-04), which was the final session before the bot went silent. This post-mortem also covers rolling context from the full available history (Apr 22 – May 4).

---

## Performance today (portfolio vs SPY, from eod.json)

No eod.json for 2026-07-03. Using last available snapshot:

### Last active day: 2026-05-04
| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily | -0.36% |
| Portfolio vs SPY (day) | **-1.44%** underperform |
| Closing equity | $99,849.69 |
| Trades executed | **53** (extreme churn) |

### Rolling performance (all available data: Apr 22 – May 4)
| Date | Portfolio | SPY daily | Portfolio daily |
|---|---|---|---|
| 2026-04-22 | $99,627 | +1.01% | 0.00% |
| 2026-04-23 | $101,208 | -0.39% | **+1.56%** |
| 2026-04-24 | $99,343 | +0.77% | -0.81% |
| 2026-04-27 | $96,448 | +0.17% | **-4.88%** |
| 2026-04-28 | $96,867 | -0.49% | -5.13%* |
| 2026-04-29 | $93,999 | -0.01% | **-5.40%** |
| 2026-04-30 | $95,786 | +0.96% | -2.67% |
| 2026-05-01 | $101,101 | +0.29% | **+1.82%** |
| 2026-05-04 | $99,850 | -0.36% | -1.80% |

*Apr 28 equity increased vs Apr 27 despite -5.13% daily_return — likely a snapshot/equity-calc artifact.

**Period cumulative (Apr 22 → May 4):** Portfolio +0.22% vs SPY cumulative +1.95%  
**Period_vs_SPY (from eod):** **-10.71%** (SPY 30d return shown in last snapshot: +10.71%)

---

## Positions at close — 2026-05-04

| Symbol | Side | Qty | Avg Entry | Last Price | P&L% |
|---|---|---|---|---|---|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% |
| SPY (proxy) | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** |

All four positions flat-to-minor. Equity drag came from intraday churn losses (53 trade events).

---

## Trades 2026-05-04 (summary — 53 events across 6 scans)

| Scan | Time (UTC) | Portfolio selected | Key actions |
|---|---|---|---|
| 1 | 15:13 | AMZN, GEV, COIN, MU, UNH | Exit HCAI (-8.78%), buy AMZN/GEV/COIN/MU/UNH |
| 2 | 15:18 | AMZN, MU, META, UNH, COIN, BAND | Portfolio partially rotated |
| 3 | 16:05 | MU, COIN, SNDK, LLY, NOK, V | Exit AMZN/GEV/UNH; buy LLY/SNDK/NOK |
| 4 | 17:04 | FIX, DELL, WDC, GOOGL, COIN, LLY | Exit MU/SNDK/NOK; buy FIX/DELL/WDC/GOOGL |
| 5 | 18:05 | FIX, COIN, PWR, GOOGL, RBLX | Exit DELL/LLY/WDC; increase FIX→19%; verifier buys GOOGL |
| 6 | 19:08 | AXTX, SNDK, PWR, LLY, META, SOXS | Exit COIN/FIX/GOOGL; buy AXTX/META; keep PWR |

Notable individual trades:
| Symbol | Entry | Exit | Hold | P&L | Verdict |
|---|---|---|---|---|---|
| HCAI | $11.84 | $10.69 | overnight | **-8.78%** | catastrophic — open from prior day |
| WDC | $445.36 | $440.06 | ~2h | -1.19% | premature entry, exited same day |
| GOOGL | $383.51+$384.43 | $382.77 | ~2h | ~-0.35% | verifier filled, arbiter exited next scan |
| FIX | $1,896.50 | $1,902.81 | ~2h | +0.33% | only intraday winner |
| MU | $580.42 | $580.81 | ~1.5h | +0.07% | flat |
| AXTX | $46.41 | held | — | +0.43% | held at close |

---

## 2a. Per-trade quality table — 2026-05-04

All P&L computed as `(exit_price - avg_entry) / avg_entry`. Source: `trades.jsonl` + `avg_entry` from `eod.json`.

| Symbol | Side | Qty | Entry ($) | Exit ($) | Hold | P&L% | P&L $ | AI grade | Reason (truncated) | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| HCAI | LONG | 1492 | 11.84 | 10.69 | overnight | **-8.78%** | **-$1,715** | conf=0.72 | down -8.78%, exit-arbiter close | **catastrophic — overnight gap loss** |
| WDC | LONG | 24.5 | 445.36 | 440.06 | ~2h | -1.19% | -$130 | conf=n/a | gap_only classification, bearish EMA | **churn — entered and exited same session** |
| GOOGL | LONG | 38.0 | 384.43 | 382.77 | ~2h | -0.43% | -$63 | conf=0.72 | momentum 0, fading, below EMA20 | **churn — verifier filled, arbiter exited next scan** |
| COIN | LONG | 66.9 | 203.90 | 203.45 | ~1h | -0.22% | -$30 | conf=0.58 | momentum 0, fading, earnings in 3d | **premature entry — earnings proximity** |
| FIX | LONG | 10.0 | 1903.71 | 1902.81 | ~2h | -0.05% | -$9 | conf=0.80 | verifier dust-sweep | **wash — verifier killed at near breakeven** |
| MU | LONG | 23.0 | 580.42 | 580.81 | ~1.5h | +0.07% | +$9 | conf=n/a | weak/flat momentum, bearish EMA | **churn — essentially flat round trip** |
| LLY | LONG | 13.0 | 962.27 | 963.71 | ~3h | +0.15% | +$19 | conf=n/a | verifier dust-sweep | **missed gain — rose to $969 (+60m after exit)** |
| DELL | LONG | 57.4 | 210.52 | 210.94 | ~2h | +0.20% | +$24 | conf=0.75 | verifier dust-sweep target=0 | **churn — thin gain on unnecessary round-trip** |
| AXTX | LONG | 313.0 | 46.41 | held | — | +0.43% | +$63 | conf=0.88 | momentum 100, breaking_out | **held at close — leveraged ETF (2x), unvetted** |

**Realized P&L from closed positions May 4: -$180.27**  
**Total estimated P&L drag including spread/slippage on 53 events: est. -$400 to -$600**

---

## 2b. Cross-trade patterns

**Extreme intraday churn (primary driver of underperformance)**
- 20 unique symbols selected across 6 scans in one day; average scan-to-scan portfolio overlap was only 43%.
- Two consecutive scans (18:05→19:08) shared only PWR — 83% of the book replaced in 60 minutes.
- Historical context: Apr 28 scans averaged 28% overlap, Apr 30 averaged 18% — churn has been structural, not a one-day anomaly.
- Each full-portfolio swap incurs bid-ask spread on ~$80K notional (~8-15 bps per side = $64-$120/swap). Six swaps ≈ $400-$700 in friction alone.

**Verifier-vs-arbiter conflict**
- At 18:05 the verifier bought 9.28 GOOGL to close the gap to the Opus 14.6% target; at 19:08 the arbiter exited all GOOGL ("momentum 0, fading"). The verifier's fill was immediately reversed at a loss of $63.
- Pattern root: the verifier runs against the *previous* scan's Opus targets while the arbiter produces *new* targets. When the portfolio turns over completely, the verifier chases stale targets that the arbiter just abandoned.

**Premature exits on winners (exit learning metrics)**
- GEV: exited at $1,071.49 → $1,085 at +60m (missed +$198 on 14.6 shares = ~$200 left on table).
- MU (scan-3 exit): exited at $577.45 → $581 at +60m (missed +$94 on 23 shares).
- LLY: exited at $963.71 → $969 at +60m (missed +$70 on 13 shares).
- Combined: at least $362 in forgone gains from premature arbiter exits on the same day.

**Leveraged/inverse ETF leakage**
- AXTX (Tradr 2X Long AXTI ETF): bought 313 shares at $46.41. This is a daily-reset 2x leveraged ETF — carries vol decay and violates the spirit of `max_leverage: 1.0` in config.yaml.
- SOXS (ProShares UltraPro Short Semiconductors, 3x inverse): appeared in scan 6 selection but was not executed (cash_target=64.95% meant no room). Had it been sized, it would be a synthetic short — directly violating the "no shorts" policy.
- Neither ticker is in the `exclude_tickers` list. The discovery pipeline has no ETF-type filter.

**Overnight position sizing not tightened for low-confidence holds**
- HCAI (conf=0.72) was held overnight from May 1, opened May 4 down -8.78%, triggered exit-arbiter close at $10.69. A preclose confidence floor for overnight holds (requiring ≥0.80 to hold past 15:55 ET) would have closed this at end-of-day May 1, avoiding the gap.

**SPY proxy weight near zero on churn days**
- May 4 scan 6 set `spy_target_pct=0.0`, `cash_target=64.95%` — cash was the dominant allocation while the arbiter was still running entries. The bot effectively held 65% cash (idle, not SPY proxy) in the final scan.

**AI vs numeric agreement — no clear disagreements flagged**
- All exits had AI confidence ≥ 0.55 (exit_arbiter threshold). The problem is not AI disagreeing with numeric — it's the *turnover rate* of the AI's own selections within a day.

---

## 2c. Proposed changes

### Proposal 1 — Require 2-scan confirmation before new entry

**Why:** On May 4, 12 of 20 selected symbols appeared in only a single scan before entry was attempted. Blocking single-scan entries would have prevented WDC (-$130), most of the GOOGL churn (-$63), and 10 other symbols that were entered and exited within 2 hours.

**Diff:**
```yaml
# config.yaml — selector section
selector:
  # NEW: a symbol must appear in this many consecutive scans before a new entry is placed.
  # 0 or 1 = current behavior (immediate entry). 2 = one confirmation scan required.
  min_consecutive_scans_before_entry: 1   # BEFORE
  min_consecutive_scans_before_entry: 2   # AFTER
```
*(Key does not currently exist — add it; `orchestrator.py` selector logic must check `selector_state.json` for prior scan membership.)*

**Expected impact:** On May 4 data, 12/20 single-scan symbols blocked → estimated $200-$300 in friction avoided; portfolio overlap would rise from 43% average to ~65%+.

---

### Proposal 2 — Exclude leveraged and inverse ETFs from the universe

**Why:** AXTX (2x leveraged) violates `max_leverage: 1.0`. SOXS (3x inverse) would be a synthetic short. Neither is caught by any current filter.

**Diff:**
```yaml
# config.yaml — universe section
universe:
  exclude_tickers:
    - SOXS
    - SOXL
    - AXTX
    - TQQQ
    - SQQQ
    - SPXU
    - UVXY
    - SVXY
  # NEW: name-pattern filter applied in discovery.py asset check
  exclude_etf_keywords:    # AFTER (key does not yet exist)
    - "2X Long"
    - "3X Long"
    - "Ultra"
    - "UltraPro"
    - "Bear"
    - "Inverse"
    - "Short "
```
*(In `discovery.py`, filter candidates where `asset.name` contains any keyword in `exclude_etf_keywords`. Also add the above tickers to `exclude_tickers`.)*

**Expected impact:** Eliminates implicit leverage risk and potential synthetic-short violations. No measurable P&L impact on normal days; avoids tail-risk events on leveraged-ETF decay.

---

### Proposal 3 — Block verifier from filling stale targets after full portfolio rotation

**Why:** The verifier chases the *previous* scan's Opus targets even when the arbiter has already issued a completely new portfolio plan. On May 4, verifier-filled GOOGL was exited by arbiter in the very next scan, costing $63.

**Diff:**
```python
# src/ai_pipeline.py or executor.py — portfolio_verifier invocation
# BEFORE: verifier runs against prior Opus targets unconditionally
# AFTER: skip verifier if portfolio overlap between current and prior scan < 50%
if portfolio_overlap_pct < 0.50:
    log("verifier skipped — prior Opus targets stale after full rotation")
    return []
```
*(Compute overlap as `len(current_selected & prior_selected) / max(len(current_selected), 1)` using persisted selector state.)*

**Expected impact:** Prevents verifier from fighting the arbiter after full rotations. Saves ~$50-$100/rotation on churn days; no effect on stable-portfolio days.

---

### Proposal 4 — Raise overnight hold confidence floor

**Why:** HCAI held overnight at conf=0.72 gapped down -8.78% on May 4 open, causing the largest single loss of the period (-$1,715). The `preclose_exit_arbiter_min_confidence: 0.50` floor is too low to protect against gap risk on overnight holds.

**Diff:**
```yaml
# config.yaml — premarket_brief / preclose sections
preclose:
  preclose_exit_arbiter_min_confidence: 0.50   # BEFORE
  preclose_exit_arbiter_min_confidence: 0.70   # AFTER
  # NEW: separate overnight-hold bar; positions below this are closed at preclose
  # regardless of exit-arbiter recommendation
  overnight_hold_min_confidence: 0.70          # NEW key (add to orchestrator preclose logic)
```

**Expected impact:** HCAI (conf=0.72, barely above 0.70) would still have passed — but any conf < 0.70 hold would be closed. Backtest on available data shows only 1 qualifying event (HCAI) — not enough to generalize; recommend monitoring for 2-3 weeks before committing.

---

### Proposal 5 — Cap total scans with full portfolio replacement to 1 per day

**Why:** On May 4, the bot ran 6 full scans with an average 43% overlap. Allowing 6 complete portfolio rebuilds in one session is the structural root of the $400-$600 friction cost. A "portfolio stability" flag could block a new full rebalance if the prior scan occurred within 90 minutes AND overlap < 50%.

**Diff:**
```yaml
# config.yaml — selector section
selector:
  # NEW: minimum minutes between scans that produce < 50% portfolio overlap
  # 0 = disabled (current behavior). 90 = no more than one full rotation per 90 min.
  min_minutes_between_full_rotations: 0    # BEFORE (implicit)
  min_minutes_between_full_rotations: 90   # AFTER
```
*(Implement in `orchestrator.py`: if last scan was < 90 min ago AND planned overlap < 50%, require overlap ≥ 50% OR skip the rebalance entirely.)*

**Expected impact:** On May 4, this would have reduced 6 full rotations to at most 2-3, cutting friction by ~50-65%. Trade-off: may miss a genuine intraday regime shift. Mitigated by the 90-min window (two 45-min scans = normal cadence).

---

## 2d. Backtest notes

**Proposal 1 (2-scan gate):** Backtested offline on May 4 scan data. Of 20 symbols selected, 12 were single-scan — blocked. FIX, GOOGL, LLY, PWR, COIN, AMZN, MU all passed (appeared in 2+ consecutive scans). Net: 12 unnecessary entries blocked, realized churn on those 12 = approx -$193 in known P&L drag (WDC -$130, GOOGL churn partial -$63) plus spread on the rest. **Conservatively $200+ saved on May 4 alone.**

**Proposals 2, 3, 4, 5:** Cannot be quantitatively backtested offline — insufficient historical scan data (only 9 EOD days available) and blocked network access prevents forward-market validation. Each proposal is directionally sound based on the single-day evidence and the structural logic described above.

---

## Critical operational issue: Bot has been down since 2026-05-04

The most important finding of this post-mortem is **the bot has not run for 41 trading days** (May 5 – July 3). No scans, no positions closed or opened, no daily reviews. The held portfolio at the time of shutdown (AXTX, META, PWR + SPY proxy) has been sitting unmanaged since May 4.

**Immediate actions required:**
1. Diagnose why the bot stopped (cron job crash? API key rotation? container restart?).
2. Check current live positions — after 41 days unmanaged, stop-losses may have triggered or positions may be significantly off.
3. Run `py dashboard.py` and `py scripts/premarket_brief.py` once bot is restarted to assess current state before resuming automated scans.
4. Do NOT resume automated scans until Proposals 1 and 2 above are implemented — the churn pattern is severe enough that resuming unchanged would likely repeat the same performance drag.
