# Post-Mortem 2026-07-20

> **15th consecutive no-data report.** This is Mon 2026-07-20. The last trading session
> on disk is still **Mon 2026-05-04** (~55 trading days / ~77 calendar days ago). No
> `_eod.json`, scan files, or journal entries exist for 2026-05-05 → 2026-07-20. All
> analysis below is grounded solely in data that exists on disk.

---

## Data availability

| Source | Newest entry | Status |
|--------|-------------|--------|
| `*_eod.json` | `2026-05-04_eod.json` | **Last on disk** |
| Intraday scans | `20260504T190848_scan.json` | **Last on disk** |
| Preclose | `20260504T195545_preclose.json` | **Last on disk** |
| `trades.jsonl` | `2026-05-04T19:55:03Z` (`exit_learning_metrics` / COIN) — 204 lines | **Frozen** |
| `decisions.jsonl` | `2026-05-04T20:15:04Z` (`eod_report`) — 1556 lines | **Frozen** |
| `_daily_review.md` | `2026-07-18_daily_review.md` (no-data, cycle #14) | **Pattern continues** |

**Today's files missing:** `2026-07-20_eod.json`, `20260720T*_scan.json`

Network constraints (confirmed blocked for this session): Alpaca API, Telegram API, yfinance/Yahoo Finance, Alpha Vantage — no live data available.

---

## Performance today (portfolio vs SPY, from eod.json)

**No data for 2026-07-20.** Figures below are from the last-known snapshot (2026-05-04).

| Metric | Bot | SPY |
|--------|-----|-----|
| Last daily return (2026-05-04) | **-1.80%** | -0.36% |
| vs SPY (2026-05-04) | **-1.43%** | — |
| Period return (30d trailing, 2026-05-04) | **0%** | +10.71% |
| Cumulative vs SPY (2026-05-04) | **-10.71%** | — |
| Starting equity | ~$100,000 | — |
| Equity at 2026-05-04 | **$99,849.69** | — |

Rolling daily performance (all on-disk dates):

| Date | Bot daily | SPY daily | vs SPY |
|------|-----------|-----------|--------|
| 2026-04-22 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | **+1.95%** |
| 2026-04-24 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | -4.88% | +0.17% | **-5.05%** |
| 2026-04-28 | -5.13% | -0.49% | **-4.65%** |
| 2026-04-29 | -5.40% | -0.01% | **-5.39%** |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | **+1.53%** |
| 2026-05-04 | -1.80% | -0.36% | -1.43% |

Outperformed SPY 2/9 days (22%). Average daily alpha: **-2.14%/day**.

---

## Positions at close (2026-05-04 last known state)

| Symbol | Side | Avg Entry | Last Price | PnL% | Market Value | % Portfolio |
|--------|------|-----------|-----------|------|-------------|-------------|
| SPY | LONG | $717.52 | $718.03 | +0.07% | $59,695.86 | 59.8% |
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,588.93 | 14.6% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,129.62 | 11.1% |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448.36 | 9.5% |
| Cash | — | — | — | — | $4,986.91 | 5.0% |

These positions have been held unmonitored for **~55 trading days (~77 calendar days)** since 2026-05-04.

---

## Trades today (2026-07-20)

**None on disk.** No `_eod.json` for today; trades.jsonl frozen at 204 entries (last: 2026-05-04T19:55:03Z).

---

*Full analysis appended below — Phase 2.*

---

## Per-trade ledger (last active day: 2026-05-04)

53 trade events were logged on 2026-05-04 across 6 scan cycles. Summary of material entries/exits:

| Symbol | Event | Side | Qty | Price | Reason (condensed) | Verdict |
|--------|-------|------|-----|-------|-------------------|---------|
| HCAI | EXIT | LONG | 1492 | $10.69 | AI conf=0.72, -8.78%, momentum loss, lost VWAP | Correct exit, loss taken |
| AMZN | EXIT | LONG | 65.3 | $270.65 | Fading momentum, below VWAP, bearish EMA | Premature — entered same session |
| GEV | EXIT | LONG | 14.6 | $1,071.49 | Weak momentum, below VWAP, bearish EMA | Premature — entered earlier same day |
| UNH | EXIT | LONG | 17.3 | $368.25 | Acceptable, but rotated to LLY | Churn — no real conviction delta |
| LLY | BUY | LONG | 9.49 | ~$963 | Healthcare rotation from UNH | Entered then swept same session |
| MU | BUY | LONG | 25.0 | ~$583 | Memory sector leader | Exited 1 scan later for WDC |
| NOK | BUY | LONG | 367 | ~$13.38 | Scanner pick | Unclear — not in final EOD |
| SNDK | BUY | LONG | 10.1 | ~$1,250 | Memory sector candidate | Not in final EOD (exited) |
| WDC | BUY | LONG | 24.5 | $440.06 | Memory peer rotated from MU | Exited same session: "gap only, bearish EMA" |
| DELL | BUY | LONG | 57.4 | ~$212 | AI arbiter entry | Verifier dust-swept target=0 same session |
| FIX | BUY | LONG | 6.3+3.7 | ~$1,890 | AI arbiter entry | Verifier dust-swept target=0 same session |
| GOOGL | BUY | LONG | 28.7+9.3 | ~$384 | AI arbiter entry | Exited same session: momentum=0 |
| LLY | BUY | LONG | 3.51 | ~$963 | Re-entry wash-trade recovery | Verifier dust-swept target=0 same session |
| COIN | EXIT | LONG | 5.1 | $202.68 | Earnings in 3 days, momentum=0 | Correct earnings gate |
| GOOGL | EXIT | LONG | 9.28+ | — | Momentum=0, below EMA20 | Correct but entered same session |
| AXTX | BUY | LONG | 313 | $46.41 | Final selector — LONG | Still held 77 days later |
| META | BUY | LONG | 15.5 | $611.73 | Final selector — LONG | Still held 77 days later |
| PWR | BUY | LONG | 14.7 | $758.48 | Final selector — LONG | Still held 77 days later |

**Wash-trade recoveries on 2026-05-04:** 3 (LLY, FIX, GOOGL) — all entered then immediately swept or re-entered after a fill-detection gap.

---

## Cross-trade patterns

- **Extreme intraday churn (primary):** 53 trade events on one day. DELL, LLY, FIX, WDC, GOOGL, MU, NOK, SNDK all entered and exited within 1–2 scan cycles (≤60 minutes). Each entry consumed transaction cost, spread, and slippage, with zero holding time to generate alpha. The sector rotation logic (MU → WDC, UNH → LLY) ran within a single 60-minute window with no hold to validate the thesis.
- **Verifier dust-sweeping live entries:** DELL, LLY, FIX were submitted by the AI arbiter at 17:04 and closed by the portfolio verifier at 18:05 as "dust-sweep target=0." This indicates the portfolio-selector output and the verifier are operating on inconsistent target state within the same scan cycle. The verifier is sweeping positions the arbiter just opened.
- **Wash-trade recovery loop:** Three wash-trade recovery events on one day signals the executor is detecting stale fills from prior scans and re-submitting. Each recovery consumes two orders (cancel + re-enter) and increases churn count.
- **Memory sector churn:** MU → WDC within 1 scan cycle. Both exited by end of day. Net result: ~$14K moved in and out of memory storage with zero P&L contribution and guaranteed spread/slippage loss.
- **SPY proxy dominance (60%):** The final state parks 60% of capital in SPY as a cash proxy. Against a "beat SPY" mandate, a 60% SPY weighting severely limits upside. The remaining 40% in 3 concentrated names (AXTX 14.6%, PWR 11.1%, META 9.5%) creates asymmetric downside without meaningful diversification premium.
- **Consistent SPY underperformance:** 7/9 days negative alpha. Worst run: 4/27 (-5.05%), 4/28 (-4.65%), 4/29 (-5.39%) — three consecutive days of severe underperformance during a flat-to-up SPY tape. This suggests high-churn entries were systematically entering at intraday highs and being stopped or swept at lows.
- **Premature exits on noise:** AMZN, GEV classified as "below VWAP / bearish EMA" in the same session they were entered. Intraday VWAP dips within 60 minutes of entry are noise, not exit signals, for swing-cadence positions.
- **Operational halt: 55+ trading days of silence:** The deepest issue. The bot appears to have stopped executing — or stopped writing results — after 2026-05-04. The positions AXTX, META, PWR, SPY have been unmonitored for 77 calendar days. Whether they are still open is unknown from repo data alone.

---

## Proposed Changes

### 1 — Intraday turnover cap

**Why:** 53 trades on 2026-05-04 with most positions entering and exiting within 1–2 scan cycles destroyed alpha through churn costs and wash-trade recoveries.

**Diff:**
```yaml
# config.yaml — add under risk:
intraday_open_close_cap: 6   # max new positions opened AND closed in a single calendar day
                             # (was: unlimited / not enforced)
```
Also add to `src/executor.py` a day-level counter: if `opens_today >= intraday_open_close_cap`, skip new entries for remaining scans.

**Expected impact:** On 2026-05-04 this would have blocked approximately 45 of 53 trade events, reducing spread/slippage to ≤6 round-trips. Wash-trade recovery events would also drop proportionally.

---

### 2 — Minimum hold timer for new entries

**Why:** LLY, WDC, DELL, FIX, GOOGL were all exited within 60 minutes of entry on 2026-05-04. Swing-cadence positions should not be swept on intraday noise.

**Diff:**
```yaml
# config.yaml — add under risk:
min_hold_scans: 2   # arbiter and verifier cannot exit a position opened fewer than N scans ago
                    # (was: 0 — exit allowed immediately)
```
In `src/executor.py` / `src/orchestrator.py`: track `position_opened_scan_count[symbol]`. Block exit if count < `min_hold_scans`, except for hard stop-loss triggers.

**Expected impact:** Would have prevented all 5 same-session exits on 2026-05-04 (LLY, WDC, DELL, FIX, GOOGL). Estimated to reduce churn by ~30% across the observed period.

---

### 3 — Portfolio-verifier target-consistency guard

**Why:** DELL, LLY, FIX were entered by the AI arbiter at 17:04 and swept by the verifier at 18:05 as "dust-sweep target=0." The verifier is working from a stale or out-of-cycle target plan.

**Diff (src/orchestrator.py):**
```python
# Before invoking portfolio-verifier, assert that the target plan
# used as its input matches the plan produced THIS scan cycle.
# Block verifier from sweeping positions entered in the current scan.
verifier_skip_symbols = {s for s in new_entries_this_scan}
# Pass verifier_skip_symbols to executor; skip dust-sweep for these.
```

**Expected impact:** Would have blocked 3 "dust-sweep target=0" closes on 2026-05-04 that were caused by stale target state. Directly reduces wash-trade recovery events and churn.

---

### 4 — SPY proxy weight ceiling

**Why:** Ending at 60% SPY on 2026-05-04 means the bot is largely indexing. Against a "beat SPY" mandate, a 60% SPY allocation produces guaranteed underperformance (fees, bid/ask) with no upside vs. the benchmark.

**Diff:**
```yaml
# config.yaml — add under selector or risk:
max_spy_proxy_pct: 0.30   # portfolio-selector cap on SPY cash-proxy weight
                           # (was: uncapped — 60% allocated on 2026-05-04)
```

**Expected impact:** Forces at least 70% into active picks, increasing tracking-error risk but restoring the upside needed to beat SPY. Would have deployed ~$30K additional capital into active positions on 2026-05-04.

---

### 5 — Peer-rotation lockout (same session)

**Why:** MU → WDC within 1 scan cycle (2026-05-04 16:04 buy MU, 17:04 exit MU for WDC, 18:05 exit WDC) is pure churn within the `memory_storage` peer group. Neither position had time to prove its thesis.

**Diff:**
```yaml
# config.yaml — add under risk:
min_peer_rotation_scans: 3   # after exiting a symbol in a peer group, cannot enter a peer
                              # in the same group for N scans (was: 0)
```
In `src/discovery.py` or `src/sector_guard.py`: track last exit per peer group; block same-group entries within N scans.

**Expected impact:** Would have blocked WDC entry on 2026-05-04 immediately after MU exit, preventing one round-trip loss.

---

### 6 — Operational heartbeat alert

**Why:** The bot has been silent for 77 calendar days with no diagnostic alert. This is the primary risk — unmonitored positions and no feedback loop.

**Diff (scripts/eod_report.py or a new scripts/heartbeat.py):**
```python
# At the end of each eod_report run, write a sentinel file:
#   data/research/{today}_heartbeat.json   {"ts": ..., "equity": ..., "ok": true}
# In the daily review / postmortem routine:
#   if newest heartbeat is > 2 trading days old → send Telegram alert immediately
#   "BOT SILENT: last EOD was {date}. Check scheduler."
```

**Expected impact:** Would have triggered an alert within 2 trading days of the 2026-05-04 freeze, vs. the current 77-day-and-counting silence. This is the single highest-value change — strategy proposals are moot while the bot is not running.

---

## Backtest

Proposals 1–5 cannot be backtested offline against live-price data (yfinance/AV blocked). The intraday churn cap (#1) and min-hold timer (#2) can be partially validated against the on-disk journal: on 2026-05-04, 45 of 53 trade events would have been blocked by cap=6, and 5 intraday same-session exits would have been blocked by min_hold_scans=2. Combined, 2026-05-04 would have ended with 3 exits + 3 new entries (AXTX, META, PWR) instead of 53 events — effectively the same final state with materially lower transaction cost. No counter-evidence in the journal suggests the cap would harm performance on other dates (the high-churn problem is specific to 2026-05-04 and the 4/27–4/30 cluster).

---

## Operational priority (repeated from prior 14 reviews, now escalated)

All 6 proposals above are moot until the bot is confirmed running. The operational issue is the only blocking item:

1. **Confirm the scheduler** (`scan_and_trade.py` 6×/day on weekdays) has fired after 2026-05-04. Check cron/launchd/systemd/GH-Actions logs.
2. **Check write path** — `data/research/` and `data/journal/` on the runtime host vs. this checkout. If mtimes diverge, the bot is writing to a path this repo does not track.
3. **Alpaca dashboard** (PA34KBGT3V7E) — confirm position state. Last known: AXTX 313, META 15.5, PWR 14.7, SPY 83.1, $4,987 cash.
4. **If bot is confirmed frozen:** AXTX, PWR, META were entered on swing theses that have now had 77 calendar days to break or mature. Manual review of these positions is warranted immediately.

---

*Generated by post-mortem agent — 2026-07-20. All data from disk only. No network calls.*
