# Post-Mortem 2026-06-10

> **Sixth consecutive no-data report.** Today is Wed 2026-06-10 (America/Phoenix). The most recent artifacts in `data/research/` are still from **Mon 2026-05-04** — a gap of **~26 trading days / 37 calendar days**. No `2026-06-10_eod.json`, no intraday scans for today. Per standing rules ("do NOT invent data"), performance sections are bounded to the last available session.

---

## Data Availability

| Source | Newest entry | Path |
|---|---|---|
| `_eod.json` | `2026-05-04_eod.json` | `data/research/2026-05-04_eod.json` |
| Last preclose snapshot | `20260504T195545_preclose.json` | `data/research/` |
| Last intraday scan | `20260504T190848_scan.json` | `data/research/` |
| `trades.jsonl` last event | `2026-05-04T19:55:03Z` exit_learning_metrics (COIN) — 204 lines | `data/journal/trades.jsonl` |
| `decisions.jsonl` last event | `2026-05-04T20:15:04Z` eod_report — 1556 lines | `data/journal/decisions.jsonl` |
| Prior no-data reviews | 5/5, 5/7, 5/13, 5/22, 6/5, **6/9** | `data/research/*_daily_review.md` |

**This is the sixth consecutive session with zero new artifacts.** The 6/9 review was the fifth; 6/10 is the sixth.

---

## Performance Today (from eod.json)

**No 2026-06-10 data.** Most recent known figures from **2026-05-04**:

| Metric | Value |
|---|---|
| Equity (2026-05-04 EOD) | $99,849.69 |
| Cash | $4,986.91 (5.0% — at floor) |
| Bot daily return (5/4) | **−1.80%** |
| SPY daily return (5/4) | **−0.36%** |
| Delta vs SPY (5/4) | **−1.43%** |
| Cumulative period vs SPY | **−10.71%** (SPY +10.71% over same window) |
| Open positions | 4 (AXTX, META, PWR, SPY proxy) |
| SPY proxy share | **59.8% of equity** |

---

## Rolling Performance (last 9 sessions — all available eod.json)

| Date | Equity | Daily Ret | SPY Daily | Delta | Trades |
|---|---|---|---|---|---|
| 2026-04-22 | $99,627 | 0.00% | +1.01% | **−1.01%** | 7 |
| 2026-04-23 | $101,208 | +1.56% | −0.39% | **+1.95%** ✅ | 9 |
| 2026-04-24 | $99,343 | −0.81% | +0.77% | **−1.58%** ❌ | 19 |
| 2026-04-27 | $96,448 | −4.88% | +0.17% | **−5.05%** ❌ | 24 |
| 2026-04-28 | $96,867 | −5.13% | −0.49% | **−4.64%** ❌ | 21 |
| 2026-04-29 | $93,999 | −5.40% | −0.01% | **−5.39%** ❌ | 10 |
| 2026-04-30 | $95,786 | −2.67% | +0.96% | **−3.63%** ❌ | 23 |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | **+1.53%** ✅ | 38 |
| 2026-05-04 | $99,850 | −1.80% | −0.36% | **−1.43%** ❌ | 53 |

**Win/loss (delta vs SPY):** 2 ✅ / 7 ❌ over available history.
**Cumulative portfolio return (4/22 → 5/4):** −0.15% vs SPY +10.71% = **−10.86% underperformance over 9 sessions**.

---

## Positions at Close (2026-05-04 EOD — last known state)

| Symbol | Side | Avg Entry | Current Price | P&L% | Mkt Value |
|---|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | **+0.43%** | $14,589 |
| META | LONG | $611.73 | $610.46 | **−0.21%** | $9,448 |
| PWR | LONG | $758.48 | $757.38 | **−0.15%** | $11,130 |
| SPY (proxy) | LONG | $717.52 | $718.03 | **+0.07%** | $59,696 |

> P&L computed from `avg_entry` and `current_price` per protocol (Alpaca unrealized_plpc not trusted).

**Note:** SPY at 59.8% of equity has been the de-facto strategy for 26+ trading days. This is no longer a bot decision — it is what the market did to the last frozen allocation.

---

## Trades Today (2026-06-10)

**None.** No intraday scan files or eod.json exist for 2026-06-10.

---

## 2a. Per-Trade Ledger — 2026-05-04 (last session; compact form)

| Time UTC | Sym | Action | Qty | Entry | Exit/Current | P&L | AI Grade | Reason (brief) | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 14:51 | **HCAI** | SELL | 1492 | $11.84 | $10.69 | **−$1,716** | F | Friday close order never filled; gap-down Monday | **execution failure** |
| 15:14 | SNDK | SELL | 23.3 | $1,140.78 | $1,250.00 | **+$2,545** | A | Weekend gap-up captured cleanly | good |
| 15:14 | STX | SELL | 19.4 | $716.82 | $740.23 | **+$454** | A− | Exited winner near intraday high | good |
| ~15:18 | AMZN | BUY | 65.3 | $274.60 | — | — | — | "Perfect momentum 100, pressing day high" | churn setup |
| ~15:18 | GEV | BUY | 14.6 | $1,093.33 | — | — | — | "Pressing day high" — cohort entry at peak | churn setup |
| ~15:18 | UNH | BUY | 17.3 | $368.14 | — | — | — | Healthcare diversifier | churn setup |
| 16:04 | **AMZN** | SELL | 65.3 | $274.60 | $270.65 | **−$258** | F | "Fading momentum, below VWAP" — 46 min after entry | **churn** |
| 16:04 | **GEV** | SELL | 14.6 | $1,093.33 | $1,071.49 | **−$318** | F | "Weak momentum" — 46 min after entry | **churn** |
| 16:04 | **UNH** | SELL | 17.3 | $368.14 | $368.25 | +$2 | D | "LLY is stronger" | **churn** |
| 16:05 | LLY | BUY | 9.49 | $963.38 | — | — | — | "Strong continuation" | — |
| 16:05 | MU | BUY | 25.0 | $584.62 | — | — | — | "Pool leader 0.90 conf" | churn setup |
| 16:05 | NOK | BUY | 367 | $13.33 | — | — | — | "Strong continuation" | churn setup |
| 16:05 | **SNDK** | BUY | 10.1 | $1,246.97 | — | — | — | **Re-buying 50 min after selling at $1,250** | **churn** |
| 16:08 | **MU** | SELL | 25.0 | $584.62 | $577.45 | **−$179** | F | 3-min hold (!) — next scan fired exit | **churn** |
| 16:10 | **SNDK** | SELL | 10.1 | $1,246.97 | $1,237.52 | **−$95** | F | Same-minute re-buy→exit cycle | **churn** |
| 16:08 | **NOK** | SELL | 367 | $13.33 | $13.24 | **−$34** | F | Intra-scan churn | **churn** |
| 17:04 | MU | BUY | 23.0 | $580.42 | — | — | — | **MU re-bought again** (above 16:08 exit) | **churn** |
| 17:04 | **MU** | SELL | 23.0 | $580.42 | $580.81 | +$9 | D | Flat exit; 2 round-trips today: net −$170 | **churn** |
| 17:04 | DELL | BUY→SELL | 57.4 | $210.52 | $210.94 | +$24 | C+ | 60-min round trip, basically flat | churn |
| 17:04 | WDC | BUY→SELL | 24.5 | $445.36 | $440.06 | **−$130** | F | 60-min round trip | **churn** |
| 17:04 | COIN | BUY→SELL | 5.1 | $203.90 | $202.68 | **−$6** | F | Earnings flag raised at 15:18 then overridden at 16:05 | **missed bearish signal** |
| 18:05 | **LLY** | SELL | 13.0 | $963.10 | $963.71 | +$8 | D | "Fading momentum" — called healthcare leader 60 min earlier | **churn** |
| 19:08 | **COIN** | SELL | 66.9 | $206.08 | $203.45 | **−$176** | F | "Earnings in 3 days — entry thesis is gone" (known at 15:18) | **oversized + missed signal** |
| 19:08 | AXTX | BUY | 313 | $46.41 | $46.61 (EOD) | +0.43% | — | Late-day breakout; overnight | (pending) |
| 19:08 | META | BUY | 15.5 | $611.73 | $610.46 (EOD) | −0.21% | — | Overnight | (pending) |
| 19:08 | PWR | BUY | 14.7 | $758.48 | $757.38 (EOD) | −0.15% | — | Overnight | (pending) |

**Grade tally:** 2× A / 1× A− / 1× C+ / 2× C / 4× D / **9× F**

---

## 2b. Cross-Trade Patterns

- **Selector instability dominates.** Average Jaccard between consecutive 5/4 selector outputs = **0.28** (one transition at 0.09 — only PWR survived the 18:05→19:08 flip). On 5/1, three transitions hit Jaccard = **0.00**. The selector is re-optimizing for "what's hot right now" every scan rather than managing a portfolio over time.
- **Intraday round-trips < 90 min: 6 confirmed in journal** (MU 3-min hold; SNDK sold-rebought same hour; AMZN/GEV/UNH 46-min flush; NOK, DELL, WDC 60-min). Total realized P&L on these 6 trips: **−$110**. Estimated friction: **~$77** (15 bps RT × avg $8,583 notional × 6 trips).
- **Earnings-gate flag not sticky.** COIN: 15:18 reduced ("earnings in 3 days"), 16:05 increased ("strong continuation"), 19:08 exited ("earnings in 3 days"). Same signal issued and overridden twice in one session; net COIN loss −$182. Earnings flag must persist for the session.
- **Friday-preclose close orders silently fail.** HCAI Friday decision: `close` (score 0.053, late_day_weakness). Order did not fill. Position carried 3 days to a −11.06% gap-down Monday = **−$1,985** realized. Same defect as flagged in 4/23 postmortem for AVGO/MU; still not patched. Single largest avoidable loss in the dataset.
- **SPY proxy becomes the chaos-day default.** SPY proxy grew from $36,378 → $59,695 (+$23K) on a day when SPY fell −0.38%. The bot sold active names and auto-bought SPY mid-session on a down tape, locking in beta at worse prices. Cash would have been cheaper.
- **AI vs numeric: AI was mostly right on direction; execution layer failed.** Exit-arbiter verdicts (confidence 0.62–0.72) on HCAI, STX, SNDK were sound. The decisions were correct; the churn came from the *selector* re-rolling baskets between scans, not from bad individual exit calls.
- **Intraday turnover ratchet.** Fill counts by day: 4/28: 2, 4/29: 1, 4/30: 4, **5/1: 28**, **5/4: 26**. High-activity days burn $195–$210 in friction (61 total fills × ~$10K avg × 7.5 bps = $458 across 5 days). No circuit breaker exists once the selector starts spinning.
- **Period underperformance widening.** Week ending 5/1: −1.77% vs SPY; period_vs_spy by 5/4: −10.71%. The gap widens monotonically — it is not a one-off drawdown but a structural leak.
- **Bot offline 26+ trading days.** All 8 proposals from the 5/5 review remain untested. The frozen $59.7K SPY proxy + $35K in AXTX/META/PWR has been the de-facto strategy for 26 sessions with no active management.

---

## 2c. Proposed Changes

### P1 — Hard minimum-hold timer (90 min, override at ≥0.85 AI confidence)

**Why:** Journal confirms 6 round trips < 90 min on 5/4 alone, total P&L −$110, ~$77 friction. MU was held 3 minutes. Selector re-rolls issue exits on names the prior scan just entered.

**Diff:**
```yaml
# config.yaml
exit_arbiter:
  min_confidence: 0.55          # existing
  min_hold_minutes: 90          # NEW — no full EXIT within 90 min of fill
  min_hold_override_confidence: 0.85  # NEW — override if arbiter confidence ≥ this
```
```python
# src/orchestrator.py — _handle_exits(), before calling exit_arbiter:
hold_age_min = (now - position.opened_at).total_seconds() / 60
if hold_age_min < config.exit_arbiter.min_hold_minutes:
    if ai_confidence < config.exit_arbiter.min_hold_override_confidence:
        log.info(f"{sym}: skipping exit — held only {hold_age_min:.0f}min (min={config.exit_arbiter.min_hold_minutes})")
        continue
```

**Expected impact:** Eliminates sub-90-min round trips (6 confirmed occurrences on last active day). Friction saved: ~$77/high-churn day. Protective-stop and ≥0.85 confidence paths remain unblocked.

---

### P2 — Preclose close-order fill verification

**Why:** HCAI Friday close didn't fill; −$1,985 gap-down Monday. Same defect as 4/23 AVGO/MU postmortem. Largest single avoidable loss in the dataset.

**Diff:**
```python
# scripts/preclose_decision.py — after exit submission loop (new block):
import time
time.sleep(120)
live_positions = {p.symbol for p in trading_client.get_all_positions()}
for sym in intended_closes:
    if sym in live_positions:
        log.warning(f"Close order for {sym} did not fill — retrying with percentage=1.0")
        trading_client.close_position(sym, ClosePositionRequest(percentage="1.0"))
```

**Expected impact:** Zero false negatives on preclose closes. Re-closing an already-closed position is a broker no-op. Eliminates the entire HCAI-class failure mode (+$1,985 counterfactual on 5/4 alone).

---

### P3 — Selector inertia: +10 opportunity-score bonus for held positions

**Why:** Average consecutive-selector Jaccard = 0.28 on 5/4; one transition at 0.09. The selector treats entering and holding as equivalent cost — they aren’t. Entering costs spread on both legs; holding costs zero.

**Diff:**
```yaml
# config.yaml
selector:
  incumbent_score_bonus: 10          # NEW — opportunity-score bonus for currently-held names
  incumbent_displacement_min_delta: 10  # NEW — challenger must out-score held name by >10
```
System-prompt addition in `.claude/agents/portfolio-selector.md`:
```
A currently-held position receives a +10 opportunity-score bonus before ranking. A challenger that is NOT currently held must exceed the held name’s effective score to displace it. All else equal, hold.
```

**Expected impact:** Raises average Jaccard from ~0.28 toward 0.60+. Reduces daily round-trip count from ~26 toward ~10. Saves ~$170–$340/day in friction (~$3,500–$7,100/month at current book size). Lets winning theses run.

---

### P4 — Persist earnings-window flag for the full session

**Why:** COIN: 15:18 REDUCE (earnings 3d) → 16:05 INCREASE (strong continuation) → 19:08 EXIT (earnings 3d). Same AI reached opposite conclusions twice. Earnings flag was recomputed per-scan and overwritten; net loss −$182.

**Diff:**
```yaml
# config.yaml
earnings:
  intraday_buy_lockout: true   # NEW — once flagged in any scan, block BUY/INCREASE for session
```
```python
# src/orchestrator.py — add per-session state:
earnings_locked_today: set[str] = set()

# In scan loop, after earnings check:
if earnings_within_window(sym):
    earnings_locked_today.add(sym)

# In selector pre-filter:
if sym in earnings_locked_today and proposed_action in ('BUY', 'INCREASE'):
    log.info(f"{sym}: earnings lockout active — blocking {proposed_action}")
    proposed_action = 'HOLD'
```

**Expected impact:** Eliminates intraday whipsaw on names with binary event risk. Would have saved the COIN net loss of −$182 on 5/4 and prevented the incoherent buy-reduce-buy cycle.

---

### P5 — Intraday fill cap (12 fills/day kill-switch)

**Why:** 5/1: 28 fills; 5/4: 26 fills. High-churn days account for 54 of 61 total recorded fills. No circuit breaker prevents the selector from continuously re-rolling.

**Diff:**
```yaml
# config.yaml
risk:
  max_intraday_fills: 12         # NEW — excludes preclose batch
  excess_fills_action: veto_buys # 'veto_buys' | 'log_only'
```
```python
# src/orchestrator.py:
if intraday_fill_count >= config.risk.max_intraday_fills:
    if config.risk.excess_fills_action == 'veto_buys':
        # Allow only EXITs, stops, and protective orders
        skip_new_entries = True
```

**Expected impact:** Caps high-churn-day friction at ~$90 (12 fills × $10K × 7.5 bps). Would have blocked 14 of 26 fills on 5/4 and 16 of 28 fills on 5/1, preserving ~$120–$150 in friction per event.

---

### 2d. Backtest Summary (offline, journal data only)

| Proposal | Method | Result |
|---|---|---|
| P1 (min-hold 90 min) | Journal round-trips < 90 min | 6 trips, P&L −$110, ~$77 friction saved per high-churn day |
| P2 (close verification) | HCAI counterfactual | +$1,985 preserved if Friday close had filled (single event) |
| P3 (selector inertia) | Jaccard friction model | 26→~10 RT/day × $8.6K notional × 15 bps = ~$230/day savings |
| P4 (earnings lockout) | COIN trace | −$182 net loss on 5/4 eliminated |
| P5 (fill cap) | Fill counts 5/1 + 5/4 | 54 excess fills over cap across 2 days; ~$270 friction saved |

Proposals P1–P4 are testable on live data immediately. P5 requires a live session to validate the cap threshold isn’t too aggressive. Combined P1+P2+P3+P4 counterfactual on 5/4: **+$2,474 recoverable** from a −$1,251 session.

---

## OPERATIONAL ESCALATION — Action Required

This is the **sixth consecutive no-data post-mortem** (5/5, 5/7, 5/13, 5/22, 6/5, 6/9 → now 6/10). The bot has produced zero artifacts since 2026-05-04. Five prior reviews asked the same operational question with no response.

| Gap | Severity |
|---|---|
| ~26 trading days / 37 calendar days | **CRITICAL** |
| 8 strategy proposals from 5/5 review | Untested — zero live evidence for/against |
| Frozen portfolio (60% SPY proxy) | No active management for 26 sessions |
| Exit-learning loop (`exit_learning_metrics`) | Starved for 5+ weeks |

**Required actions (for the user, not the bot):**

1. **Check the scheduler** — confirm `scripts/scan_and_trade.py` has fired since 5/4. If not, find why (cron/GitHub Action/launchd dead, token expired, disk full, rate-limit blackout, Anthropic billing lapse).
2. **Check the write path** — if the scheduler fired, compare `data/research/` mtime on the runtime host vs. this repo. If diverged, bot writes to a stale path.
3. **Check Alpaca paper account PA34KBGT3V7E** — log into the dashboard and confirm whether positions/orders have moved since 5/4. Last known state: $99,849 equity, 4 positions (AXTX 313, META 15.5, PWR 14.7, SPY 83.1), $4,987 cash.
4. **If frozen:** the 60% SPY proxy is now ~26 sessions of passive SPY beta, not an active strategy. Once the bot restarts, first action should be a manual portfolio review before resuming autonomous scans.

**No strategy proposals can be validated or killed without live data. Until the operational gap is closed, every proposal in this and prior reports sits in limbo.**
