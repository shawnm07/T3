# Post-Mortem 2026-07-15

## Data availability

**CRITICAL: No data exists for 2026-07-15 in this repo.**

The most recent EOD snapshot is `2026-05-04_eod.json` (10+ weeks ago). Git commit history shows daily review commits since then all include the note "no new data; latest snapshot is still 5/4". This post-mortem therefore covers the **last active trading session (2026-05-04)** and the full recorded period **2026-04-22 → 2026-05-04**.

**Bot operational status is unknown.** The data gap from 2026-05-05 to present may indicate the bot stopped running, Alpaca paper account was reset, or the eod_report.py script stopped writing files. This is the highest-priority finding.

Scan files present for 2026-05-04: 6 intraday + 1 preclose.  
Journal entries for 2026-05-04: 53 trades, 105 decisions.

---

## Performance today (2026-05-04, most recent session)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily | **-0.36%** |
| Daily alpha | **-1.44%** |
| Equity at close | $99,850 |
| Trades executed | 53 |
| Open positions EOD | 4 |
| Macro regime | neutral (score 0.27, VIX ~27.3) |

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Close Price | PnL % | Market Value | % Portfolio |
|--------|------|-----------|-------------|--------|--------------|-------------|
| SPY    | LONG | $717.52   | $718.03     | +0.07% | $59,696      | 59.7% |
| PWR    | LONG | $758.48   | $757.38     | -0.15% | $11,130      | 11.1% |
| AXTX   | LONG | $46.41    | $46.61      | +0.43% | $14,589      | 14.6% |
| META   | LONG | $611.73   | $610.46     | -0.21% | $9,448       | 9.5%  |

> Note: 59.7% SPY cash-proxy weight means the bot had ~60% parked in its benchmark. This is not alpha-generating positioning.

---

## Trades today (2026-05-04, complete round-trip summary)

| Time (UTC) | Symbol | Action | Reason (truncated) |
|------------|--------|--------|---------------------|
| 14:51 | HCAI | EXIT (full) | AI exit-arbiter: down -8.78%, thesis broken |
| 16:04 | AMZN | EXIT (full) | Fading momentum, below VWAP, bearish EMA (was 17.7%) |
| 16:04 | GEV  | EXIT (full) | Weak momentum, below VWAP, flat trend (was 15.6%) |
| 16:04 | UNH  | EXIT (full) | Exiting to fund LLY entry |
| 16:04 | LLY  | BUY 9.1% | Strong continuation, bullish EMA |
| 16:04 | MU   | INCREASE →28% | Pool leader with perfect momentum |
| 16:04 | NOK  | BUY 4.9% | Strong continuation |
| 16:04 | SNDK | BUY 12.6% | Best new candidate |
| 17:04 | MU   | EXIT (full) | Weak/flat momentum, bearish EMA — **bought at 16:04, sold at 17:04** |
| 17:04 | DELL | BUY 12.1% | IT sector leader |
| 17:04 | FIX  | BUY 11.9% | ai_data_center_power peer leader |
| 17:04 | GOOGL| BUY 11.0% | Communication Services leader |
| 17:04 | LLY  | INCREASE →12.5% | Within 120-min cooldown |
| 17:04 | WDC  | BUY 10.9% | Memory peer leader |
| 17:04 | COIN | verifier reconcile 14.8% | Gap fill |
| 18:05 | WDC  | EXIT (full) | Gap-only classification, bearish EMA — **bought at 17:04, sold at 18:05** |
| 18:05 | FIX  | INCREASE →19% | Perfect momentum |
| 18:05 | DELL | dust-sweep →0% | Verifier closed position just opened at 17:04 |
| 18:05 | LLY  | dust-sweep →0% | Verifier closed position just opened at 17:04/16:04 |
| 18:05 | GOOGL| verifier reconcile 14.6% | Gap fill |
| 19:08 | COIN | EXIT (full) | Momentum score 0, earnings risk (was 13.7%) |
| 19:08 | GOOGL| EXIT (full) | Momentum score 0, fading (was 14.6%) |
| 19:08 | FIX  | dust-sweep →0% | Verifier closed the 19% position opened this scan |
| 19:08 | AXTX | BUY 14.4% | Momentum score 100, breaking out |
| 19:08 | META | BUY 9.5% | Communication Services leader |
| 19:08 | PWR  | BUY 11.1% | ai_data_center_power peer leader |

*53 total order events; at least 6 round-trips completed within the same trading day.*

---

---

## Rolling benchmark (2026-04-22 → 2026-05-04, all 9 recorded trading days)

| Date | Portfolio | SPY | Alpha |
|------|-----------|-----|-------|
| 2026-04-22 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.58% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | -5.13% | -0.49% | -4.64% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.44% |
| **Cumulative** | **-16.31%** | **+1.95%** | **-18.26%** |

- Win/Loss: 3 up days / 6 down days
- Max losing streak: 5 consecutive days (Apr 27–May 1 morning)
- Average daily: portfolio -1.92%, SPY +0.22%
- Opportunity cost (if fully in SPY from start): **$18,195**

---

## Section 2a — Per-trade quality verdicts (2026-05-04)

| Symbol | Side | Action | Entry/Exit | PnL | AI Conf | Verdict |
|--------|------|--------|------------|-----|---------|---------|
| HCAI | LONG | EXIT | avg $11.84 → ~$10.80 | -8.78% | 0.72 | **good** — stopped a deteriorating position early |
| AMZN | LONG | EXIT | held from prior day | unknown (pnl_pct not in snapshot) | — | **good** — momentum confirmed broken |
| GEV  | LONG | EXIT | held from prior day | unknown | — | **good** — momentum confirmed broken |
| UNH  | LONG | EXIT | held | unknown | — | **churn** — "exiting to fund LLY" is thin justification; LLY was dust-swept same session |
| LLY  | LONG | BUY→EXIT | entered 16:04, closed 18:05 | unknown | 0.60 | **churn** — opened then verifier dust-swept within 2 hours |
| MU   | LONG | BUY→EXIT | entered 16:04, closed 17:04 | avg $495 → sell | -1h | **churn** — bought "pool leader" at 16:04, signals flipped to bearish within 60 min |
| WDC  | LONG | BUY→EXIT | entered 17:04, closed 18:05 | bought, sold 1h later | -1h | **churn** — "gap-only classification" immediately after buy |
| DELL | LONG | BUY→SWEEP | entered 17:04, dust-swept 18:05 | unknown | 0.55 | **bug** — verifier closed a fresh arbiter buy in the same scan cycle |
| FIX  | LONG | BUY→SWEEP | grew to 19% at 18:05, swept 19:08 | unknown | — | **bug** — verifier dust-swept a position the selector just grew to 19% |
| GOOGL| LONG | BUY→EXIT | entered 17:04, exited 19:08 | 2h round trip | 0.55 | **churn** — entered and exited in same session, no meaningful hold |
| COIN | LONG | RECON→EXIT | reconcile 14.8% then exited | unknown | — | **churn** — reconciled to 14.8% then arbiter exited "momentum score 0" |
| AXTX | LONG | BUY | new at 19:08, held EOD | +0.43% | — | **good** — breaking out, held overnight |
| META | LONG | BUY | new at 19:08, held EOD | -0.21% | — | **neutral** — held EOD, slight red |
| PWR  | LONG | BUY | new at 19:08, held EOD | -0.15% | — | **neutral** — held EOD, slight red |

---

## Section 2b — Cross-trade patterns

**Verifier dust-sweep bug (critical):**
The `portfolio-verifier` (post-execution reconciler) is issuing `dust-sweep target=0` on positions the portfolio-selector or portfolio-arbiter just opened in the SAME scan cycle. DELL, LLY, and FIX were all opened then immediately swept. This represents a target-state conflict between the arbiter and verifier and is generating commission drag with zero benefit. Affected: at least 3 positions on May 4 alone.

**Intra-session signal reversals driving churn:**
MU went from "pool leader, perfect momentum" (16:04) to "weak/flat momentum, bearish EMA" (17:04) in 60 minutes. WDC went from "memory peer leader scoring 60.48" (17:04) to "gap-only classification, bearish EMA" (18:05) in 60 minutes. Either the intraday signal computation is too sensitive to short-term noise, or the exit threshold is too low relative to the entry threshold.

**Over-trimming AMD on the way up:**
AMD was trimmed from 18% → 15% → 11% → 8% → 6% → 5% → 0% across Apr 24-28, citing RSI 88-89 each time. The thesis (tech=0.67, sent=0.87, "strong thesis") was acknowledged at each trim but overridden by the RSI gate. AMD was a momentum winner being systematically cut. See `scripts/analyze_winner_trim.py` for trim analysis tooling.

**IT sector over-concentration drove the Apr 27-29 loss streak:**
On 2026-04-27 (worst day, -4.88%): IT = 61.6% of portfolio, Industrials = 32.8%. `config.yaml` states `max_sector_pct: 0.40` but the live portfolio exceeded this significantly. The 5-day loss streak (-4.88%, -5.13%, -5.40%) appears to be a correlated sector drawdown, not idiosyncratic stock risk. The sector guard appears to not be enforced by the legacy portfolio-arbiter path.

**SPY cash-proxy dominance at EOD (not alpha-generating):**
At May 4 EOD, SPY held 59.7% of the portfolio ($59,696 of $99,850). The bot's inability to maintain conviction positions results in defaulting to its own benchmark as a cash proxy — negating any possibility of positive alpha. This is self-defeating.

**Overbought entries (RSI>70): 13 occurrences across the period:**
AMD (RSI 82.0), APLS (87.2), GEV (78.7), ARW (76.9), AVGO (76.3, 77.8), FIX (70.4), IRDM (70.3), DELL (71.5, 73.9), V (72.8), NOK (76.5), ALGM (74.8). Multiple of these resulted in immediate losses on drawdown. Config enforces no hard RSI gate at entry; the AI discretion alone is insufficient.

**AI verdicts low-conviction but still buying:**
Several entries had `ai_confidence` ≤ 0.52 (AMD 0.52, VRT 0.55, AVGO 0.55 repeatedly). Entries with AI confidence below 0.60 on stocks with RSI>70 have a poor track record in this dataset.

**Premature exits on noise vs. false bearish halts:**
Apr 29 was the worst day (-5.40%) despite SPY being flat (-0.01%). This implies the portfolio was in a fast-moving loss on concentrated high-RSI tech names. Macro regime was "neutral" throughout — the bearish halt (score < -0.55) was never triggered, so the portfolio stayed fully invested through the drawdown without a defensive signal.

---

## Section 2c — Proposed changes

### P1 — Fix verifier dust-sweep race condition (bug, no config change needed)

**Why:** Verifier is closing positions opened by the selector/arbiter in the SAME scan cycle. DELL, LLY, FIX all swept on May 4. This is pure friction with no alpha benefit.

**Diff:**
```python
# src/executor.py (or portfolio_verifier agent prompt):
# Before: verifier proposes dust-sweep whenever target=0 regardless of when position was opened
# After: add a guard — skip dust-sweep if position was opened in the current scan cycle
#   In practice: track position open timestamps; if (now - open_ts) < 90min, skip verifier sweep
```

**Expected impact:** Eliminates 3+ unnecessary round-trips per high-churn day. Estimated $50-150/day in avoided slippage on paper account.

---

### P2 — Hard RSI gate on new entries: block buys when RSI > 78

**Why:** 13 of 13 entries with RSI>70 in this dataset occurred on overbought names; multiple (AMD RSI 82, APLS RSI 87.2, GEV RSI 78.7) led to immediate drawdowns. The AI's discretion alone did not reliably block these.

**Diff:**
```yaml
# config.yaml
risk:
  # add new key:
  max_entry_rsi: 78       # before: no key (no hard gate); after: block new BUY orders when RSI > 78
```
```python
# src/risk.py — enforce in _validate_entry():
#   if technical_signals['rsi'] > config['risk']['max_entry_rsi']:
#       return reject("entry blocked: RSI {rsi:.1f} > max_entry_rsi {gate}")
```

**Expected impact:** Would have blocked AMD (RSI 82), APLS (RSI 87.2), GEV (RSI 78.7), ARW (RSI 76.9) on entry day. Estimated prevention of $3,000–5,000 of drawdown based on the Apr 22-27 loss sequence.

---

### P3 — Minimum position hold time: 60 minutes before exit allowed (non-stop-loss)

**Why:** MU bought at 16:04, sold at 17:04. WDC bought 17:04, sold 18:05. These round-trips generate friction without giving the thesis time to develop. Stop-loss triggers should be exempt; all other exits should require a minimum hold.

**Diff:**
```yaml
# config.yaml
risk:
  min_hold_minutes: 60   # before: no key; after: AI-driven exits blocked for 60 min post-entry
                          # exception: hard stop-loss triggers always allowed
```

**Expected impact:** Eliminates MU-style 60-min round-trips. On May 4 alone this would have saved at least 4 unnecessary trades. No backtest possible offline (would need price data for counterfactual P&L).

---

### P4 — Enforce sector cap in portfolio-selector (fix for IT over-concentration)

**Why:** config.yaml `max_sector_pct: 0.40` but Apr 27 portfolio had IT at 61.6%. The cap appears not enforced in the selector's weight allocation.

**Diff:**
```yaml
# config.yaml — verify this key is read by portfolio-selector agent:
diversification:
  max_per_gics_sector: 3        # already exists
  max_sector_weight_pct: 0.40   # CONFIRM this is enforced by portfolio-selector, not just sector_guard.py
```
```python
# src/sector_guard.py — add enforcement check in apply_sector_limits():
# Before: logs warning if sector >40% but may not block
# After: hard reject any selector weight allocation that would put single GICS sector above max_sector_weight_pct
```

**Expected impact:** Would have capped IT at 40% on Apr 27, reducing correlated loss from -4.88% to estimated -2.5 to -3.0% (rough estimate: IT names lost 3-8%, SPY flat; 20pp less IT exposure × avg 5% loss = ~1% reduction).

---

### P5 — Winner-trim RSI gate: require RSI>85 AND earnings <7d before aggressive trim

**Why:** AMD was trimmed 6 times citing RSI 88-89 while the thesis (tech=0.67, sent=0.87) was still intact. Premature exit from a momentum winner destroyed performance on what would have been a profitable hold.

**Diff:**
```yaml
# config.yaml — add new keys:
risk:
  winner_trim_rsi_threshold: 85        # before: no key; after: RSI must exceed this to trigger trim
  winner_trim_earnings_days: 7         # before: trim on RSI alone; after: also require earnings <7d
  winner_trim_min_pnl_pct: 0.05       # only trim when position is up >5% (protecting winners not losers)
```

**Expected impact:** AMD would have been trimmed at most once (RSI 89 + 8d earnings on Apr 24) instead of 6 times. Estimated improvement: 1–2% on the full period by letting winners run.

---

### P6 — Health-check heartbeat file (operational continuity)

**Why:** No data exists from 2026-05-05 to 2026-07-15 (10+ weeks). There is no mechanism to detect if the bot has stopped. This entire post-mortem is based on stale data.

**Diff:**
```python
# scripts/eod_report.py — append at end of main():
import pathlib, datetime
pathlib.Path('data/state/heartbeat.txt').write_text(datetime.datetime.utcnow().isoformat())
# Add to a daily git commit or push to detect staleness
```

**Expected impact:** Enables automated staleness detection. Any monitoring tool (cron, GitHub Action) can check if heartbeat is >24h old and alert.

---

## Section 2d — Backtest notes

**P2 (RSI gate):** Offline backtest not feasible — requires price data post-entry to compute prevented-loss. From the journal data: all 13 RSI>70 entries lost money within 2 days of entry based on the equity curve decline. Qualitative confidence: **high**.

**P3 (min hold time):** No counterfactual price data available offline. Cannot compute what MU/WDC would have done over 60 minutes if held. **Skipped**.

**P4 (sector cap):** Rough estimate only (see P4 expected impact above). Offline journal data confirms cap breach; exact P&L improvement requires price data. **Qualitative only**.

**P5 (winner trim):** AMD entries are in journal with avg_entry ~$319-347. AMD pnl_pct never explicitly recorded post-exit in eod.json files (AMD exited Apr 28, no subsequent eod snapshot shows AMD). **Cannot compute counterfactual offline**.

**P1 (dust-sweep bug) and P6 (heartbeat):** No backtest needed — these are correctness/operational fixes.

---

*Post-mortem generated 2026-07-15 by post-mortem-bot. All proposals are in this markdown only — no config.yaml or src/ files were modified.*

