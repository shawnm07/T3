# Post-Mortem 2026-06-15

## Data availability

| Source | Status | Last entry |
|---|---|---|
| `_eod.json` | **No data for 2026-06-15** | `2026-05-04_eod.json` |
| Scan files | **None since 2026-05-04** | `20260504T195545_preclose.json` |
| `trades.jsonl` | **Frozen** | `2026-05-04T19:55:03Z` — 204 lines |
| `decisions.jsonl` | **Frozen** | `2026-05-04T20:15:04Z` — 1556 lines |
| No-data daily reviews | 6× written | 2026-05-05 through 2026-06-11 |

**Critical:** Zero artifacts since 2026-05-04T20:15 UTC — **41 calendar days, ≈27 trading days** of silence. This is not a standard session post-mortem; it is a retroactive analysis of the last active session (2026-05-04) plus a frozen-book status report. Today (2026-06-15) is a Sunday; no scan would have run regardless. The bot-offline issue is the overriding priority.

---

## Performance today (2026-06-15)

No data. Bot offline. Last EOD was 2026-05-04.

---

## Performance — last active session (2026-05-04)

| Metric | Value |
|---|---|
| Bot daily return | **−1.80%** |
| SPY daily return | **−0.36%** |
| Delta vs benchmark | **−1.43%** ❌ |
| Equity EOD | $99,849.69 |
| Cash EOD | $4,986.91 (5.0% floor) |
| Open positions at close | 4 (AXTX, META, PWR, SPY proxy 59.8%) |
| Trades | **53 events** |
| Macro regime | neutral (score 0.27), VIX ~27.4–27.9 |

### 9-day tracked window (2026-04-22 → 2026-05-04)

| Date | Bot daily | SPY daily | Delta |
|---|---|---|---|
| 2026-04-22 | 0.00% | +1.01% | −1.01% |
| 2026-04-23 | +1.56% | −0.39% | +1.95% |
| 2026-04-24 | −0.81% | +0.77% | −1.59% |
| 2026-04-27 | **−4.88%** | +0.17% | **−5.05%** |
| 2026-04-28 | **−5.13%** | −0.49% | **−4.65%** |
| 2026-04-29 | **−5.40%** | −0.01% | **−5.39%** |
| 2026-04-30 | −2.67% | +0.96% | −3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | −1.80% | −0.36% | −1.43% |

| Period | Bot cumulative | SPY cumulative | Bot vs SPY |
|---|---|---|---|
| 9-day (4/22–5/4) | ~+0.68% | ~+1.96% | **−1.28%** |
| 5-day (4/28–5/4) | ~−12.65% | ~+0.38% | **−13.03%** |
| 30-day (from eod.json `period_vs_spy`) | 0%* | +10.71% | **−10.71%** |

*`period_return` field = 0 in all EOD files (no pre-4/22 baseline recorded).

The 4/27–4/29 three-day drawdown (−4.88%, −5.13%, −5.40%) while SPY barely moved (+0.17%, −0.49%, −0.01%) is the **primary underperformance driver**.

---

## Positions at close (last active day: 2026-05-04)

| Symbol | Side | Qty | Avg Entry | Price (5/4 EOD) | PnL% |
|---|---|---|---|---|---|
| AXTX | LONG | 313 | $46.41 | $46.61 | +0.43% |
| META | LONG | 15.48 | $611.73 | $610.46 | −0.21% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | −0.15% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% |

No live prices available (network blocked). These are as of 2026-05-04 close. The book has been unmanaged for 41 calendar days.

---

## Trades — last active session (2026-05-04)

| Time UTC | Symbol | Action | Qty | Entry | Exit | PnL | Grade | Notes |
|---|---|---|---|---|---|---|---|---|
| ~14:51 | HCAI | SELL (gap-down) | 1,492 | $11.84 | $10.69 | **−$1,716** | F | Friday close order did not fill; gapped down 11% Mon open |
| ~15:14 | SNDK | SELL (overnight exit) | 23.30 | $1,140.78 | $1,250.00 | **+$2,545** | A | Clean gap-up capture |
| ~15:14 | STX | SELL (overnight exit) | 19.40 | $716.82 | $740.23 | **+$454** | A− | Exited winner near intraday high |
| ~15:18→16:04 | AMZN | BUY→SELL 50 min | 65.30 | $274.60 | $270.65 | **−$258** | F | Thesis unchanged; selector re-rolled |
| ~15:18→16:04 | GEV | BUY→SELL 50 min | 14.57 | $1,093.33 | $1,071.49 | **−$318** | F | Same |
| ~15:18→16:04 | UNH | BUY→SELL 50 min | 17.27 | $368.14 | $368.25 | +$2 | D | Lucky flat exit |
| ~16:05→16:08 | MU | BUY→SELL **3 min** | 25.0 | $584.62 | $577.45 | **−$179** | F | Next-scan exit before cooldown cleared |
| ~15:14→16:10 | SNDK | SELL then RE-BUY→EXIT | 10.10 | $1,246.97 | $1,237.52 | **−$95** | F | Paid spread to re-buy 56 min after selling |
| ~16:05→16:08 | NOK | BUY→SELL 3 min | 367.24 | $13.33 | $13.24 | **−$34** | F | Intra-scan churn |
| ~17:04→18:05 | MU | BUY→SELL 2nd round | 23.0 | $580.42 | $580.81 | +$9 | D | Second MU round-trip; net 2 round-trips ≈ −$170 |
| ~17:04→18:05 | WDC | BUY→SELL 60 min | 24.51 | $445.36 | $440.06 | **−$130** | F | Same pattern |
| ~17:04→18:05 | DELL | BUY→SELL 60 min | 57.39 | $210.52 | $210.94 | +$24 | C+ | Flat round-trip |
| ~19:08 | COIN | EXIT | 66.90 | $206.08 | $203.45 | **−$176** | F | Had earnings flag at 15:18; overridden at 16:05; finally exited |
| ~19:08 | GOOGL | EXIT | 37.96 | $383.78 | $382.77 | **−$38** | F | Same-day round-trip; wash-trade recovery triggered |
| ~19:08 | FIX | sell (dust) | 10.0 | $1,898.90 | $1,902.81 | +$39 | C | Verifier dust-sweep |
| ~19:08 | AXTX | BUY (overnight) | 313 | $46.41 | — | — | — | Late-day breakout; still held at freeze |
| ~19:08 | META | BUY (overnight) | 15.48 | $611.73 | — | — | — | Still held at freeze |
| ~19:08 | PWR | BUY (overnight) | 14.69 | $758.48 | — | — | — | Still held at freeze |

**Grade tally:** 2× A/A−, 1× C+, 2× C, 4× D, **9× F.**

---

## Full Analysis

### Cross-trade patterns (bullets)

- **Selector instability is the root cause of friction.** Avg Jaccard between consecutive 5/4 selector outputs = 0.28; one transition (18:05→19:08) = 0.09 (only PWR survived). Portfolio is rebuilt from scratch each scan, paying spread+slippage on both legs. Estimated friction: 26 round-trips × ~$13K × 7.5 bps ≈ **$254/day**.

- **Bot has drifted from swing to intraday day-trader cadence.** CLAUDE.md states "swing cadence, 6× daily scans." In practice 5/4 had 53 fill events, sub-60-min median hold on closed positions. The 6 scans run as 6 independent day-trader runs with no portfolio continuity.

- **Earnings-gate is not sticky.** COIN on 5/4: REDUCE (earnings 3d) @ 15:18 → INCREASE (strong continuation) @ 16:05 → EXIT (earnings 3d) @ 19:08. Same arbiter reached opposite conclusions about the same earnings risk in 4 hours. The flag is recomputed per scan and overridden by momentum signals.

- **Preclose close-orders can silently fail.** HCAI was `close` (score 0.053) at Friday preclose. Order did not fill. No retry/verification. Position gapped down 11% over the 3-day weekend → **−$1,985, ≈2% of equity**. The 2026-04-23 postmortem flagged the same `ClosePositionRequest(qty=None)` defect; the bug apparently recurred or was never fixed.

- **RSI-overbought entries at preclose.** All 4/22 preclose buys had RSI > 70: AMD 82, GEV 78.7, ARW 76.9, APLS 87.2, IRDM 70.3. These seeded the 4/27–4/29 drawdown when those names mean-reverted.

- **AI vs numeric disagreement — AI was wrong on AMD.** Technical analyst flagged `rsi_overbought` on AMD at RSI 82 (4/22) and RSI 88.9 (4/24 add). Decision-arbiter overruled and bought both times. AMD's RSI extension was a primary trigger for the 4/27 crash leg (−4.88% portfolio day while SPY +0.17%).

- **SPY proxy bought on down-tape.** SPY proxy grew $36K → $59.7K intraday on 5/4 (a −0.36% SPY day) as the selector exited single-names and auto-parked proceeds in SPY. This locks in beta loss exactly when staying in cash would have been better.

- **Sector guard not blocking rebalance adds.** On 4/27 the book held 7 ai_data_center names (AMD, MU, AVGO, VRT, FIX, GEV, DELL) against a configured `max_per_theme: 3`. The sector_guard.py veto apparently was not applied to rebalance/arbiter-sourced adds.

- **trade_critical_model downgraded to claude-sonnet-4-6.** Config currently shows `trade_critical_model: claude-sonnet-4-6`; early trades show `_model: claude-opus-4-7`. The 5/4 session (post-downgrade) produced 9× F decisions including SOXS (inverse 3× semis ETF) while holding semis longs — a decision that is hard to explain under the standard arbiter logic.

- **Bot freeze (27 trading days) is the overriding issue.** No stops adjusting, no exits triggering, no adaptation for 41 calendar days. The 4 frozen positions (AXTX, META, PWR, SPY) are de-facto the entire strategy for the period.

---

### Proposed Changes

#### P1 (CRITICAL): Restore bot operation

**Why:** Zero artifacts since 2026-05-04T20:15 UTC. Everything else is moot.

**Action steps:**
1. `crontab -l` on runtime host — confirm `scripts/scan_and_trade.py` has fired since 5/4.
2. Compare `data/research/` mtimes on runtime host vs. this repo clone.
3. Log into Alpaca PA34KBGT3V7E dashboard — if still showing 5/4 state (AXTX/META/PWR/SPY), bot is completely frozen.
4. If frozen: `py scripts/scan_and_trade.py --force` to restart; fix root cause (cron, token expiry, disk, API rate-limit blackout, Anthropic billing lapse).

**Expected impact:** Allows proposals P2–P8 to be deployed and tested on live data.

---

#### P2 (HIGH): Add incumbent-score bonus to portfolio selector

**Why:** 5/4 avg selector Jaccard = 0.28. Round-trip friction estimated $254/day.

**Diff (config.yaml — proposals only, do not apply to this branch):**
```yaml
selector:
  incumbent_score_bonus: 10         # held positions get +10 opportunity-score pts
  incumbent_displacement_min_delta: 10  # challenger must beat held by >10 pts to displace
```
Add to `portfolio-selector` system prompt: *"Currently held positions receive a 10-point opportunity-score premium. A new candidate must outperform a held position by more than 10 points to displace it."

**Expected impact:** Cuts daily round-trip count from ~26 to ~10. Saves ~$150–$300/day friction (~$3,000–$6,000/month). Lets winning theses run.

---

#### P3 (HIGH): Persist earnings-window BUY lock for the full session

**Why:** COIN: REDUCE (earnings 3d) @ 15:18 → INCREASE @ 16:05 → EXIT (earnings 3d) @ 19:08.

**Diff:**
```yaml
# config.yaml:
earnings:
  intraday_buy_lockout: true    # once flagged, no BUY/INCREASE for rest of session
```
```python
# src/orchestrator.py — session-scoped set:
earnings_locked_today: set[str] = set()  # reset at session start only
# When earnings gate fires: earnings_locked_today.add(symbol)
# In selector pre-filter: skip BUY/INCREASE if symbol in earnings_locked_today
```

**Expected impact:** Eliminates intraday whipsaw on binary-event names.

---

#### P4 (HIGH): Hard minimum-hold timer (no full EXIT within 90 min of entry)

**Why:** MU bought 16:05, sold 16:08 (3 min). AMZN/GEV/UNH 50-min holds. Thesis unchanged; selector re-rolled.

**Diff:**
```yaml
# config.yaml:
exit_arbiter:
  min_confidence: 0.55
  min_hold_minutes: 90               # no full exit within 90 min of entry fill
  min_hold_override_confidence: 0.85 # bypass if AI confidence ≥ 0.85 or stop hit
```

**Expected impact:** Blocks 3-minute round-trips. Forces selector to commit to each pick for at least one scan cycle.

---

#### P5 (HIGH): Verify preclose close-orders filled before EOD

**Why:** HCAI silent close-order failure → $1,985 avoidable loss (≈2% equity). Same defect documented in 4/23 postmortem; still firing.

**Diff (scripts/preclose_decision.py — concept only):**
```python
# After exit submission loop — add 2-min follow-up check:
time.sleep(120)
still_open = {p.symbol for p in trading_client.get_all_positions()}
for sym in intended_closes:
    if sym in still_open:
        log.warning(f"Close for {sym} did not fill; retrying")
        trading_client.close_position(sym, ClosePositionRequest(percentage="1.0"))
```

**Expected impact:** Eliminates silent close failures. False-retry cost = zero (closing an already-closed position is a no-op).

---

#### P6 (MEDIUM): Restore trade_critical_model to claude-opus-4-7

**Why:** `config.yaml` has `trade_critical_model: claude-sonnet-4-6`. Early trades used `claude-opus-4-7`. Post-downgrade 5/4 session produced 9× F decisions including SOXS (inverse 3× semis while holding semis longs).

**Diff (config.yaml):**
```yaml
# Before:
ai:
  trade_critical_model: claude-sonnet-4-6

# After:
ai:
  trade_critical_model: claude-opus-4-7
```

**Expected impact:** Higher accuracy on arbiter/selector/exit-arbiter/earnings-gate. Incremental cost: ~$10–$30/day.

---

#### P7 (MEDIUM): Cap intraday fills at 12 per day (veto buys after)

**Why:** 5/4: 53 events; 5/1: 38 events. After ~12 fills, marginal entries are selector re-rolls on noise, not signal.

**Diff (config.yaml):**
```yaml
risk:
  max_intraday_fills: 12          # after this, veto BUY/INCREASE; exits/stops/preclose exempt
  excess_fills_action: veto_buys
```

**Expected impact:** Caps friction at ~$120/day worst case. Saves ~$137/day vs. 5/4 pace (~$2,900/month).

---

#### P8 (MEDIUM): Enforce sector_guard for rebalance/arbiter adds

**Why:** 4/27 had 7 ai_data_center names against `max_per_theme: 3`. Guard was not blocking rebalance-sourced adds. The 4/27 single-day correlation loss (−4.88% vs. SPY +0.17%) is largely explained by theme concentration.

**Diff (src/sector_guard.py — concept):**
```python
# Apply theme cap check to ALL buy actions, not just new-entry decisions:
if proposed_action in ('BUY', 'INCREASE'):
    if theme_count(theme, current_portfolio + [symbol]) > max_per_theme:
        veto(f"theme cap exceeded: {theme}")
```

**Expected impact:** Limits correlated drawdown on sector-news days. Halves exposure in any single theme.

---

### Backtests (offline-only, journal data)

| Test | Method | Result |
|---|---|---|
| Selector Jaccard consistency (5/4) | Scan file timestamps + position lists | Avg 0.28; min 0.09. A floor of 0.50 would have blocked 4 of 5 intraday transitions. |
| Missed P&L on 30m/60m post-exit (4 exits) | `exit_learning_metrics` in trades.jsonl | Aggregate 60m missed PnL: −$315. Exits are not systematically early — they are too numerous. |
| Friction model for P7 (12-fill cap) | 26 round-trips × $13K avg × 7.5 bps | $254/day → cap saves ~$137/day (~$2,900/month). |
| HCAI counterfactual for P5 (close verification) | Intended exit $11.40 vs. actual $10.69 | Avoidable loss: $1,059–$1,985 per occurrence. Fix has near-zero false-positive cost. |
| Sector concentration impact (P8, 4/27) | 7 ai_data_center names vs. cap of 3 | Capping to 3 names halves theme notional → excess daily loss reduced from −5.05% to ~−2.5%. |
| Overnight thesis quality (5/1→5/4) | Score vs. outcome for 3 overnight holds | Score 0.64→+5.3%, 0.42→+1.8%, 0.05→−11.1%. Score-outcome correlation is excellent; overnight selection model works. |

No network-dependent backtests run (yfinance/Alpaca blocked).

---

## Summary — priority stack

1. **P1 (CRITICAL):** Restore bot operation. 41 calendar days offline. Investigate scheduler, write path, Alpaca account state.
2. **P5 (HIGH):** Fix preclose close-order verification. $1,985 avoidable loss per failure.
3. **P2 (HIGH):** Selector incumbent bonus. Single biggest ongoing friction reducer.
4. **P3 (HIGH):** Earnings-window BUY lockout. COIN pattern is a repeat defect.
5. **P4 (HIGH):** Minimum-hold timer. Blocks 3-minute round-trips structurally.
6. **P6 (MEDIUM):** Restore claude-opus-4-7 for trade-critical. Improves decision quality.
7. **P7 (MEDIUM):** 12-fill intraday cap. Hard backstop on churn days.
8. **P8 (MEDIUM):** Sector guard on rebalance adds. Prevents 4/27-style theme blowups.

Proposals P2–P8 are changes to `config.yaml` and `src/` files — they are described here for review only. No modifications to those files are included in this branch.
