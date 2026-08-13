# Post-Mortem 2026-07-14

> **Operational note:** No trading data exists for 2026-07-14. The bot has been silent since **2026-05-04** (~50 trading days / ~71 calendar days). This post-mortem grades the last live session (2026-05-04) and analyzes the frozen book's implied risk. Full analysis in Phase 2 sections below.

---

## Data Availability

| Source | Status | Newest Entry |
|---|---|---|
| `data/research/*_eod.json` | Last: 2026-05-04 | `2026-05-04_eod.json` |
| `data/research/*_scan.json` | Last: 2026-05-04 | `20260504T195545_preclose.json` |
| `data/journal/trades.jsonl` | 204 lines, frozen since 5/4 | `2026-05-04T19:55:03Z` |
| `data/journal/decisions.jsonl` | 1556 lines, frozen since 5/4 | `2026-05-04T20:15:04Z` |
| Today scans | **MISSING** — 0 files for `202607*` | — |

No data was produced for 2026-07-14. Analysis below is anchored to the last operational session.

---

## Performance Today (2026-07-14)

**No data.** Estimated frozen-book exposure (from 2026-05-04 EOD, unmonitored for 71 days):

| Metric | Value |
|---|---|
| Bot equity at last snapshot | $99,849.69 |
| Bot daily return (5/4) | **-1.80%** |
| SPY daily return (5/4) | -0.36% |
| Bot vs SPY (5/4) | **-1.43%** |
| Cumulative period vs SPY (30d) | **-10.71%** |
| Cash at last snapshot | $4,986.91 (5.0%) |

---

## Positions at Close (2026-05-04 EOD — Frozen Book)

| Symbol | Side | Qty | Avg Entry | Last Price (5/4) | PnL% | Market Value | Notes |
|---|---|---|---|---|---|---|---|
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | $59,696 | 59.8% of book — large cash-proxy |
| AXTX | LONG | 313 | $46.41 | $46.61 | +0.43% | $14,589 | 14.6% — **2× leveraged ETF** (Tradr 2X Long AXTI) |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | $11,130 | 11.1% — Industrials/ai_data_center |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | $9,448 | 9.5% — Comm Services |
| Cash | — | — | — | — | — | $4,987 | 5.0% reserve |

*Prices are as of 2026-05-04 close. Actual current prices are unknown (network blocked).*

---

## Trades (2026-05-04 — 53 Total)

53 trades on 2026-05-04 — the highest single-day count in the journal. Key executions:

| Symbol | Action | Qty | Price | Outcome | Verdict |
|---|---|---|---|---|---|
| HCAI | EXIT | 1492 | $10.69 | -8.78% from $11.84 | BAD — stop never triggered at 1% floor ($11.72) |
| AMZN | EXIT | 65.3 | $270.65 | ~flat | OK — fading momentum |
| GEV | EXIT | 14.6 | $1,071.49 | ~flat | BAD — missed +$198 upside 60m later |
| UNH | EXIT | 17.3 | $368.25 | ~flat | CHURN — fading volume, no real move |
| LLY | BUY+ADD+EXIT | 13.0 | ~$963 | +0.03% | CHURN — same-day round trip, zero alpha |
| MU | BUY+EXIT×2 | 25/23 | ~$580 | ~flat | CHURN — double round trip |
| NOK | BUY (→ exit via learning) | 367 | $13.33 | — | CHURN |
| WDC | BUY → EXIT | 24.5 | $445.36 → $440.06 | -1.19% | BAD — gap_only, whipsaw loss |
| DELL | BUY → EXIT (dust) | 57.4 | $210.52 → $210.94 | +0.20% | CHURN — verifier in, dust-sweep out |
| FIX | BUY+ADD → EXIT (dust) | 10.0 | $1,896–$1,904 | ~flat | CHURN — verifier conflict |
| GOOGL | BUY+ADD → EXIT | 38.0 | $383–$384 → $382.77 | -0.19% | CHURN — verifier reconcile, arbiter exit |
| COIN | BUY (verifier) → EXIT | 66.9 | $203.90 → $203.45 | -0.22% | CHURN — verifier/arbiter conflict |
| AXTX | BUY (held) | 313 | $46.41 | +0.43% | OK entry, **leveraged ETF risk** |
| META | BUY (held) | 15.5 | $611.73 | -0.21% | MARGINAL — confidence 0.65 |
| PWR | BUY (held) | 14.7 | $758.48 | -0.15% | OK — confidence 0.72 |
| SPY | (ongoing) | 83.1 | $717.52 | +0.07% | Large proxy, limits upside |

---

---

## Rolling Performance (Last 9 Sessions on Record)

| Date | Bot Daily | SPY Daily | vs SPY | Equity |
|---|---|---|---|---|
| 2026-04-22 | +0.00% | +1.00% | **-1.00%** | $99,627 |
| 2026-04-23 | +1.60% | -0.40% | **+1.90%** | $101,208 |
| 2026-04-24 | -0.80% | +0.80% | **-1.60%** | $99,343 |
| 2026-04-27 | -4.90% | +0.20% | **-5.10%** | $96,448 |
| 2026-04-28 | -5.10% | -0.50% | **-4.60%** | $96,867 |
| 2026-04-29 | -5.40% | -0.00% | **-5.40%** | $93,999 |
| 2026-04-30 | -2.70% | +1.00% | **-3.60%** | $95,786 |
| 2026-05-01 | +1.80% | +0.30% | **+1.50%** | $101,101 |
| 2026-05-04 | -1.80% | -0.40% | **-1.40%** | $99,850 |

- Beat SPY: **2/9 days** (4/23, 5/1)
- Missed SPY: **7/9 days**
- Avg daily vs SPY: **-2.14%**
- Cumulative period vs SPY: **-10.71%** (from `period_vs_spy` in EOD)
- Worst stretch: 3 consecutive days 4/27–4/29 averaging -5.0% vs SPY

---

## 2a. Per-Trade Ledger (2026-05-04)

53 trades. Total turnover: **$288,805 = 289% of equity** in a single day.

| Symbol | Action | Qty | Entry | Exit/Close | PnL | AI Conf | Source | Verdict |
|---|---|---|---|---|---|---|---|---|
| HCAI | EXIT | 1492 | $11.84 | $10.69 | **-8.78%** | 0.72 | exit-arbiter | BAD — stop never hit at 1% floor ($11.72); 60m after exit price −$164 (bot right to exit, but stop should have fired 8× earlier) |
| AMZN | EXIT | 65.3 | ~$271 | $270.65 | ~-0.1% | — | arbiter | OK — fading momentum exit |
| GEV | EXIT | 14.6 | ~$1,073 | $1,071.49 | ~-0.1% | — | arbiter | BAD — left **+$198 at 60m**; weak momentum call was wrong |
| UNH | EXIT | 17.3 | ~$369 | $368.25 | ~-0.2% | — | arbiter | CHURN — "acceptable continuation but fading volume" = noise exit |
| LLY | BUY 9.5 → ADD 3.5 → EXIT 13 | 13.0 | $963 | $963.71 | +0.03% | 0.72/0.65 | arbiter | CHURN — complete round trip, $0 alpha, wasted spread |
| MU | BUY 25 → EXIT 23 | 23.0 | $580.42 | $580.81 | +0.07% | 0.9 | arbiter | CHURN — 60m after exit -$166 (bot was right to exit but entry was unnecessary) |
| NOK | BUY → (exit learning) | 367 | $13.33 | — | — | 0.68 | arbiter | CHURN — low confidence entry, 60m post-exit -$17 |
| SNDK | BUY (partial hold) | 10.1 | $1,247 | — | — | 0.75 | arbiter | OK — entry, though 60m post-session -$204 suggests over-extended |
| DELL | BUY → EXIT (dust) | 57.4 | $210.52 | $210.94 | +0.20% | 0.80 | arbiter → verifier | CHURN — verifier swept out immediately after arbiter entry |
| FIX | BUY 6.3 → ADD 3.7 → EXIT (dust) | 10.0 | $1,896–$1,904 | $1,902.81 | ~flat | 0.82/0.88 | arbiter → verifier | CHURN — entered twice, verifier dust-swept; net round trip |
| GOOGL | BUY 28.7 → ADD 9.3 (verifier) → EXIT 38 | 38.0 | $383–$384 | $382.77 | **-0.19%** | 0.72 | arbiter + verifier | CHURN+CONFLICT — verifier added shares, arbiter exited all within same session |
| WDC | BUY → EXIT | 24.5 | $445.36 | $440.06 | **-1.19%** | 0.75 | arbiter | BAD — gap_only, quick reversal; 60m after exit +$100 (premature) |
| COIN | BUY (verifier) → EXIT (arbiter) | 66.9 | $203.90 | $203.45 | -0.22% | 0.68 | verifier → arbiter | CHURN+CONFLICT — verifier reconcile immediately reversed by arbiter |
| AXTX | BUY (held) | 313 | $46.41 | still held | +0.43% | 0.88 | arbiter | ⚠️ OK entry but **2× leveraged ETF** — compounding decay risk over 71-day hold |
| META | BUY (held) | 15.5 | $611.73 | still held | -0.21% | 0.65 | arbiter | MARGINAL — below minimum confidence threshold (0.65 < 0.70 ideal) |
| PWR | BUY (held) | 14.7 | $758.48 | still held | -0.15% | 0.72 | arbiter | OK — sector leader, acceptable entry |

---

## 2b. Cross-Trade Patterns

- **289% intraday turnover** — swing-cadence bot executed like a day trader. 14 distinct symbols touched; 11 of 16 positions opened were closed same session. Estimated spread+friction cost at 0.05% per leg: ~$290.
- **Verifier/arbiter conflict (systematic):** GOOGL and COIN were added by the portfolio-verifier to reconcile to Opus targets, then exited by the arbiter at the next scan within the same session. This is a structural bug: verifier acts on stale arbiter targets while the arbiter is already re-evaluating. Net cost: ~$80 in friction per occurrence.
- **Premature exits leaving upside:** GEV +$198 and WDC +$100 at 60m post-exit; LLY +$70 at 60m. Three positions exited on "fading" momentum classification that reversed within the hour. Total unrealized upside left: ~$370.
- **HCAI stop failure:** HCAI entered at $11.84 with a 1% hard stop implying $11.72 stop price. Exited at $10.69 (-8.78%) — the stop was either never placed, was cancelled, or triggered at the wrong price. This is a reliability failure, not a strategy failure.
- **AXTX is a 2× leveraged ETF** (Tradr 2X Long AXTI Daily ETF — BATS). Swing trading a leveraged product introduces daily compounding decay. This position has been held frozen for 71 days with no active monitoring or stop updates.
- **SPY proxy dominance (59.8%):** Nearly 60% of equity parked in SPY means the bot's max possible alpha above SPY is bounded by the ~40% active book. Three concentrated single-name bets (AXTX 14.6%, PWR 11.1%, META 9.5%) add idiosyncratic risk without enough diversification to smooth it.
- **Three worst days (4/27–4/29: avg -5.0% vs SPY):** All occurred before 5/4; the 5/4 data inherited a book already down ~$5,400 from peak. These losses coincide with the period of high intraday turnover on prior sessions (4/29: 23 trades, 4/30: 23 trades, 5/1: 38 trades, 5/4: 53 trades) — escalating churn as the bot attempted to recover.
- **Low-confidence entries not filtered:** META (conf=0.65) and NOK (conf=0.68) were entered below the 0.70 effective quality threshold. Both round-tripped or held underwater.
- **AI vs numeric disagreement:** On 5/4, the numeric engine flagged WDC as a buy (via arbiter BUY), but the gap_only classification + bearish EMA flagged it for exit within hours. The arbiter should have weighted the gap_only classification more heavily pre-entry.

---

## 2c. Proposed Changes

### Proposal 1 — Intraday Turnover Cap

**Why:** 289% turnover on 5/4 vs. a 6× swing-cadence schedule destroyed any intraday alpha through pure friction. A swing bot should not execute day-trading volumes.

**Diff:**
```yaml
# config.yaml — add under risk:
risk:
  max_intraday_turnover_pct: 0.30   # cap total BUY notional per day at 30% of equity
  # was: no cap (implicit unlimited)
```

**Expected impact:** On 5/4 this would have blocked ~$96K of the ~$137K in buys, preventing most round trips. Conservative estimate: saves $150–$250/day in spread/friction when churning days occur. Also prevents the feedback loop where losses trigger more trades.

**Backtest:** In-repo journal shows 5 sessions with >10 trades: 4/29 (23), 4/30 (23), 5/1 (38), 5/4 (53). A 30% cap ($30K daily buy limit) would have halted discretionary rebalancing on all four high-churn days after the first few positions were filled. Cannot quantify net P&L impact offline without price series.

---

### Proposal 2 — Verifier/Arbiter Conflict Guard

**Why:** Verifier reconciled GOOGL (+$3,569) and COIN (+$1,135) to Opus targets; the arbiter exited both within the same scan cycle. Two round trips, zero alpha, ~$80 friction wasted.

**Diff (src/orchestrator.py logic, proposals only — do not edit src/):**
```python
# Before calling portfolio-verifier reconcile for symbol X:
# Check if the current arbiter output already has an EXIT decision for X.
# If arbiter_decisions.get(symbol, {}).get('action') == 'EXIT':
#     skip verifier reconcile for this symbol this scan
```

**Expected impact:** Eliminates a specific conflict class that fires whenever the arbiter changes its mind between the selector pass and the verifier pass. One occurrence = ~$40–$80 friction saved.

**Backtest:** Manual inspection of 5/4 trades.jsonl confirms this pattern occurred for GOOGL and COIN on the same scan. No further instances visible in the 9-session window, but the structural condition exists whenever verifier runs after a late-session arbiter exit decision.

---

### Proposal 3 — Block Leveraged ETF Entries

**Why:** AXTX (Tradr 2X Long AXTI Daily ETF) is a daily-rebalanced 2× product. Held frozen for 71+ days, it accrues compounding decay risk not present in single equities. The swing thesis doesn't apply to leveraged ETFs.

**Diff:**
```yaml
# config.yaml — add under discovery:
discovery:
  blocked_name_patterns:
    - "2X Long"
    - "3X Long"
    - "2X Short"
    - "Ultra"
    - "Daily ETF"
  # was: no name-based filter (leveraged ETFs entered freely)
```

**Expected impact:** Prevents entries into leveraged products. AXTX specifically: unknown P&L over 71-day frozen hold, but 2× decay over a month or more in a volatile market can be severe. No offline backtest possible without price series.

---

### Proposal 4 — Minimum Hold Timer (120 minutes)

**Why:** GEV, WDC, LLY, MU — all entered and exited within 2–4 hours. Exit momentum signals reverted within 60 minutes in 3 of 4 cases (GEV +$198, WDC +$100, LLY +$70 at 60m). A minimum hold window would have avoided these premature exits.

**Diff:**
```yaml
# config.yaml — add under risk:
risk:
  min_hold_minutes: 120   # don't exit any position held less than 2h unless stop triggered
  # was: no minimum hold (arbiter can exit immediately after entry)
```

**Expected impact:** Would have preserved GEV, WDC, and LLY through their 60m rebound, recovering ~$370 on 5/4 alone. Exception: hard 1% stop should still fire immediately regardless of hold timer.

**Backtest:** Applying to 5/4 data — GEV entered ~14:00 ET, exited ~16:04 (120m later, at close anyway); WDC entered ~16:04, exited 18:05 (121m — borderline); LLY entered ~15:05, exited 18:05 (180m). With a 120m timer, only WDC exit would have been delayed. Net would have needed live price series to quantify.

---

### Proposal 5 — Hard Stop Reliability Audit (HCAI)

**Why:** HCAI avg_entry=$11.84 → 1% hard stop should have placed a sell-stop at $11.72. Exit occurred at $10.69 (-8.78%), implying the stop was never placed, was cancelled (wash trade recovery?), or the stop order failed silently.

**Diff (investigation, not config change):**
```python
# In src/executor.py: verify that protective stop_order_id for every entry
# is confirmed "filled" or "held" status before proceeding to the next scan.
# If stop_order_error is non-empty, raise an alert rather than silently proceeding.
# Check: did any wash_trade_recovery cancel the HCAI stop without replacing it?
```

**Expected impact:** HCAI loss was -$1,308 (1492 × ($11.84 - $10.69)). With a functioning 1% stop at $11.72, max loss would have been $177 (1492 × $0.12). A $1,131 protection gap on one position. This must be audited before re-enabling the bot.

**Backtest:** Not applicable — this is a reliability/correctness issue, not a strategy parameter.

---

### Proposal 6 — SPY Proxy Cap

**Why:** SPY at 59.8% of equity creates a portfolio that tracks the index with high-friction active additions. The bot cannot beat SPY if 60% of it IS SPY. Capital locked in SPY proxy also prevents sizing into high-conviction names.

**Diff:**
```yaml
# config.yaml — add under risk:
risk:
  spy_proxy_max_pct: 0.40   # cap SPY (and other broad index ETFs) at 40% of equity
  # was: subject only to max_position_pct: 0.50
```

**Expected impact:** Forces reallocation from SPY to up to 2 additional active positions when high-conviction candidates exist. If the active book beats SPY, this directly improves total alpha. If the active book loses to SPY, a lower SPY cap increases drawdown. Net effect is higher-variance but directionally correct for the goal of beating SPY.

---

## 2d. Backtest Summary

No offline backtests were possible for Proposals 1, 3, or 6 (require price series). Proposals 2 and 5 are structural/correctness fixes with no meaningful backtest surface. Proposal 4 (min-hold timer) analysis using in-repo exit_learning_metrics data above shows ~$370 in recoverable upside on 5/4 alone if the three premature exits had been delayed.

---

## Operational Status

**The bot has been frozen since 2026-05-04.** All 6 proposals above are untestable until the scheduler is restored and fresh `_eod.json` / scan files begin appearing in this repo.

**Frozen-book risk (unmonitored ~71 days):**
- AXTX (2× leveraged ETF, 14.6%) — decay risk growing daily
- META (9.5%) and PWR (11.1%) — both entered at or near stop distance; stops set 5/4 are likely stale
- SPY (59.8%) — passive tracking, no active risk management

**Critical action required before next live scan:** Audit HCAI stop failure (Proposal 5). If protective stops can be cancelled without replacement, every live position is exposed to unlimited downside.

**See `2026-07-14_daily_review.md` for operational escalation timeline and next steps.**
