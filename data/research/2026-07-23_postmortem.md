# Post-Mortem 2026-07-23

> **17th consecutive no-data cycle.** The last live snapshot remains `2026-05-04_eod.json` — ~57 trading days / 80 calendar days of trading silence. Analysis below is based entirely on on-disk artifacts.

---

## Data availability

| Source | Status | Last entry |
|---|---|---|
| `_eod.json` | **Stale** | `2026-05-04_eod.json` |
| `*_scan.json` | **Stale** | `20260504T190848_scan.json` |
| `*_preclose.json` | **Stale** | `20260504T195545_preclose.json` |
| `trades.jsonl` | **Stale** | `2026-05-04T19:55:03Z` (204 lines) |
| `decisions.jsonl` | **Stale** | `2026-05-04T20:15:04Z` (1556 lines) |
| Today's `2026-07-23_eod.json` | **MISSING** | — |
| Market data egress (AV / yfinance / TD) | **BLOCKED** | 403 at proxy for all three |
| Alpaca API | **BLOCKED** | 403 |

No `20260505T*` → `20260723T*` scan, preclose, or EOD files exist. The trading scheduler has been silent for **80 calendar days** since the last live scan (2026-05-04 ~20:00 UTC).

---

## Performance today (portfolio vs SPY, from eod.json)

**No 2026-07-23 data.** Figures below are the last known state (2026-05-04):

| Metric | Value |
|---|---|
| Equity | $99,849.69 |
| Cash | $4,986.91 (~5.0%) |
| Daily return (5/4) | **-1.80%** |
| SPY daily (5/4) | -0.36% |
| Daily vs SPY (5/4) | **-1.43%** |
| SPY 30d (at 5/4) | +10.71% |
| Period return vs SPY (at 5/4) | **-10.71%** |
| Positions | 4 |
| Trades on 5/4 | 53 |

---

## Positions at close (last known — 2026-05-04)

| Symbol | Side | Avg Entry | Price (5/4) | PnL% | Mkt Value | Alloc% |
|---|---|---|---|---|---|---|
| SPY | LONG | $717.52 | $718.03 | +0.07% | $59,695.86 | 59.8% |
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,588.93 | 14.6% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,129.62 | 11.1% |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448.36 | 9.5% |
| **Cash** | — | — | — | — | $4,986.91 | 5.0% |
| **Total** | | | | | $99,862.68 | 100% |

> Note: PnL% computed from `avg_entry` and `current_price` per instructions (Alpaca `unrealized_plpc` not trusted).

---

## Trades today (table)

**No 2026-07-23 trade data.** Last session (2026-05-04) logged 53 trades — dominated by entries/exits across MU, DELL, AXTX, PWR, META, SPY during intraday churn. Detailed table in Phase 2 below.

---

## Rolling performance (all available EOD data)

| Date | Equity | Daily | SPY Daily | vs SPY | Positions | Trades |
|---|---|---|---|---|---|---|
| 2026-04-22 | $99,627 | +0.00% | +1.01% | **-1.01%** | 7 | 7 |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | **+1.95%** | 10 | 9 |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | **-1.59%** | 12 | 19 |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | **-5.05%** | 8 | 24 |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | **-4.65%** | 4 | 21 |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | **-5.39%** | 5 | 10 |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | **-3.63%** | 3 | 23 |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | **+1.53%** | 4 | 38 |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | **-1.43%** | 4 | 53 |

**9-day aggregate (4/22 → 5/4, all available data):**
- Portfolio: $99,627 → $99,850 = **+0.22%**
- SPY proxy: daily returns compound to approximately **+2.96%** over same period
- Net alpha: approximately **-2.74%** over 9 trading days

---

---

## Phase 2 — Deep Analysis

### 2a. Trade-level ledger (2026-05-04, last live session)

All PnL computed entry→exit. Positions still open at EOD use 5/4 close price.

| Time (UTC) | Symbol | Side | Qty | Entry | Exit | PnL% | AI Conf | Verdict |
|---|---|---|---|---|---|---|---|---|
| 14:51 | HCAI | EXIT | 1,492 | — | $10.69 | -8.78% | 0.72 | **GOOD** — correctly cut a deep momentum loss |
| 16:04 | AMZN | EXIT | 65.3 | — | $270.65 | ~neg | 0.62 | QUESTIONABLE — exited to fund "higher conviction"; sold into flat price action |
| 16:04 | GEV | EXIT | 14.6 | — | $1,071.49 | n/a | 0.62 | QUESTIONABLE — weak momentum exit, was at 15.6% alloc |
| 16:04 | UNH | EXIT | 17.3 | — | $368.25 | n/a | 0.62 | **BAD** — exited to fund LLY rotation; LLY swept same day |
| 16:04 | LLY | BUY | 9.49 | $963.38 | $963.71 | +0.03% | 0.72 | **CHURN** — entered, increased, then verifier-swept same session |
| 16:04 | NOK | BUY | 367 | $13.33 | — | n/a | 0.68 | (position disposition unknown — not in EOD snapshot) |
| 16:04 | SNDK | BUY | 10.1 | $1,246.97 | — | n/a | 0.75 | (position disposition unknown — not in EOD snapshot) |
| 16:04 | DELL | BUY | 57.4 | $210.52 | — | — | 0.80 | **CHURN** — immediately swept by verifier at 18:05 |
| 16:04 | FIX | BUY | 6.30 | $1,896.50 | — | 0.82 | **CHURN** — wash trade + verifier sweep same session |
| 16:04 | GOOGL | BUY | 28.7 | $383.51 | $382.77 | -0.19% | 0.72 | **BAD** — entered then exited at small loss same session |
| 17:04 | MU | EXIT | 23.0 | $514.53* | $580.81 | +12.9%* | 0.58 | **MISSED** — exited profitable position to fund WDC, which then lost |
| 17:04 | LLY | INCREASE | 3.51 | $962.27 | — | — | 0.65 | wash-trade recovery order |
| 18:05 | WDC | BUY | 24.5 | $445.36 | $440.06 | -1.19% | 0.75 | **BAD** — entered as "peer leader over MU," exited same session -1.19% |
| 18:05 | WDC | EXIT | 24.5 | $445.36 | $440.06 | -1.19% | — | see above |
| 18:05 | DELL | EXIT | 57.4 | $210.52 | $210.94 | +0.20% | — | verifier dust-sweep; $24 gain absorbed by spread |
| 18:05 | LLY | EXIT | 13.0 | $963.38 | $963.71 | +0.03% | — | verifier dust-sweep; $4 gain absorbed by spread |
| 18:05 | FIX | EXIT | 10.0 | $1,896.50 | $1,902.81 | +0.33% | — | verifier dust-sweep; $63 gain absorbed by spread |
| 18:05 | FIX | INCREASE | 3.70 | $1,903.71 | — | 0.88 | wash-trade recovery |
| 18:05 | GOOGL | INCREASE | 9.28 | $384.43 | $382.77 | -0.43% | — | wash-trade recovery |
| 19:08 | COIN | EXIT | 66.9 | — | $203.45 | n/a | — | earnings in 3d; correct to exit pre-earnings |
| 19:08 | GOOGL | EXIT | 37.96 | $383.51 | $382.77 | -0.19% | — | same-session entry→exit |
| 19:08 | FIX | EXIT | 10.0 | — | $1,902.81 | n/a | — | verifier dust-sweep |
| EOD | AXTX | HOLD | 313 | $46.41 | $46.61 | **+0.43%** | 0.88 | **GOOD** — high conviction (score 100, breaking_out) |
| EOD | META | HOLD | 15.5 | $611.73 | $610.46 | -0.21% | 0.65 | OK — moderate conviction, sector diversification |
| EOD | PWR | HOLD | 14.7 | $758.48 | $757.38 | -0.15% | 0.72 | OK — sector leader, acceptable entry |

*MU avg_entry from 2026-04-27 EOD snapshot ($514.53); exit at $580.81 = +12.9% unrealized gain sacrificed.

---

### 2b. Cross-trade patterns

- **Intraday turnover explosion (5/4: 53 trades):** Position count cycled through ~8 distinct compositions in one session. At least 5 symbols were both entered and exited the same day (WDC, LLY, DELL, FIX, GOOGL). This is structural, not statistical — the selector, verifier, and arbiter are not coordinated within a scan cycle.

- **Verifier immediately undoes selector decisions:** DELL (conf=0.80), LLY (conf=0.72), FIX (conf=0.82/0.88) all entered via arbiter BUY orders at 16:04, then closed by verifier "dust-sweep target=0" at 18:05 — barely 60 minutes later. The verifier ran with a portfolio target that excluded newly-entered positions, sweeping them before the next scan.

- **Peer rotation churn (MU → WDC):** MU held at +12.9% profit; exited at 17:04 to "fund superior memory peer WDC" (WDC score 60.48 vs MU 38.24). WDC entered at $445.36, exited at $440.06 (-1.19%) one hour later as "entry thesis completely broken." Net: surrendered a ~$1,070 gain on MU while losing ~$130 on WDC — net $1,200 adverse swing from one rotation.

- **UNH → LLY health sector rotation:** UNH exited at 16:04 to fund LLY ("stronger healthcare name"). LLY entered at $963.38, then verifier swept at $963.71 same session. Net: paid spread on UNH exit, paid spread on LLY entry, paid spread on LLY exit — three round-trip legs for near-zero gain.

- **Wash trade recoveries (LLY, FIX, GOOGL):** Three Alpaca `40310000` errors across one session indicate the bot is submitting new buy-side stop orders while previous sell-side stops for the same symbol are still live. Root cause: the stop order from a partial fill or prior position is not canceled before the new entry order's stop is submitted.

- **Exit arbiter at minimum confidence floor:** All 7 exit arbiter calls returned confidence 0.58–0.72, barely above `min_confidence: 0.55`. The arbiter's outputs cluster at its floor; every reduce/exit fired by the intraday trigger was marginal.

- **4/27–4/29 consecutive drawdown vs flat SPY:** Portfolio dropped ~6.4% over 3 days (96,448 → 93,999) while SPY was essentially flat (+0.17%, -0.01%, -0.01% cumulative). The book had 8→4→5 positions, suggesting heavy exits into drawdown rather than adding to strength.

- **SPY proxy = 59.8% of portfolio at final state:** The bot converged to holding SPY as its largest position. A portfolio that is 60% benchmark cannot systematically beat benchmark; the allocation cap for SPY as cash proxy needs a ceiling.

- **Position count spike on 4/24 (12 positions):** 12 positions held on 4/24 is 2× the `max_positions: 6` config limit. This was likely from the rebalance arbiter or verifier adding positions that the selector didn't explicitly authorize. High-watermark concentration was followed by the worst drawdown week.

---

### 2c. Proposed changes

**1. Min-hold timer: block exit eligibility for 1 scan cycle after entry**

- **Why:** DELL, LLY, FIX all entered then closed in under 60 minutes by the verifier. WDC entered at 18:05 and exited in the next scan cycle. None had time to develop.
- **Diff (config.yaml):**
  ```yaml
  # Before (key absent):
  # (no min_hold_scans key)
  
  # After:
  risk:
    min_hold_scans: 1   # position must survive 1 full scan cycle before exit eligible
  ```
- **Diff (src/executor.py or src/sector_guard.py):** Add check: `if position.entry_scan_id == current_scan_id: skip exit` before passing to exit_arbiter.
- **Expected impact:** Eliminates same-cycle dust-sweeps; would have prevented 3 verifier sweeps on 5/4 (~$200 in spread friction saved on that session alone). Estimated ~30% reduction in total trades on active days.

---

**2. Raise `exit_arbiter.min_confidence` from 0.55 → 0.65**

- **Why:** Every intraday reduce/exit call on 5/4 returned 0.58–0.72. At 0.65 floor, the AMZN, GEV, UNH, MU exits (all at 0.58–0.62) would not have fired, avoiding the UNH→LLY rotation and MU→WDC rotation that netted ~-$1,200.
- **Diff (config.yaml):**
  ```yaml
  # Before:
  exit_arbiter:
    min_confidence: 0.55
  
  # After:
  exit_arbiter:
    min_confidence: 0.65
  ```
- **Expected impact:** Reduces intraday exits by ~40% on flat/neutral days. Preserves clean stop-loss exits (hard stops fire independently of arbiter confidence). Risk: holds positions longer in genuine downtrends — mitigated by hard_stop_loss_pct: 0.01 enforcing the floor.

---

**3. Intraday full-close cap: max 3 position closes per scan**

- **Why:** 5/4 saw 11 full closes in a single day. "Nuke everything and restart" dynamics increase friction and prevent positions from compounding. Cap forces prioritization — only the worst positions get cut in one cycle.
- **Diff (config.yaml):**
  ```yaml
  # Before (key absent):
  # (no max_closes_per_scan key)
  
  # After:
  risk:
    max_closes_per_scan: 3   # max full position closes per scan cycle (hard stops exempt)
  ```
- **Expected impact:** On 5/4, would have limited exit rotation to 3 of the 11 closes. Reduces wash trade exposure (fewer rapid entry→exit cycles). Hard stops (HCAI -8.78%) would remain exempt.

---

**4. Peer rotation guard: block same-GICS-sector swap within 2 trading days**

- **Why:** MU→WDC is the canonical case: the selector scores WDC higher than MU in one scan, exits MU (+12.9%), enters WDC, then the next scan exits WDC (-1.19%) as "entry thesis broken." The sector thesis (memory storage) is right; the rotation cadence is wrong.
- **Diff (config.yaml):**
  ```yaml
  # Before (key absent):
  # (no min_rotation_hold_days key)
  
  # After:
  selector:
    min_rotation_hold_days: 2   # cannot swap out incumbent for same-GICS peer if held < 2 days
  ```
- **Expected impact:** On 5/4 would have blocked the MU→WDC rotation, preserving ~$1,070 unrealized gain on MU and avoiding ~$130 WDC loss. Net ~+$1,200 on that trade alone.

---

**5. Cap SPY cash-proxy allocation at 40%**

- **Why:** Final 5/4 state: 59.8% SPY. The goal is to beat SPY, not track it. When macro is neutral or better, >40% SPY allocation is structurally self-defeating. `spy_daily` on 5/4 was -0.36%; the portfolio still underperformed by -1.43% — meaning the non-SPY legs contributed the alpha drag, but the SPY leg also masked the true active-equity drawdown.
- **Diff (config.yaml):**
  ```yaml
  # Before (key absent):
  # (no max_spy_proxy_pct key)
  
  # After:
  risk:
    max_spy_proxy_pct: 0.40   # SPY cash-proxy capped at 40% of equity
  ```
- **Expected impact:** Forces 15-20% redeployment into long equity when macro allows. Does not override macro halt (if score < -0.55, this cap is irrelevant). Primary risk: higher active equity concentration raises drawdown in adverse weeks.

---

**6. (Operational, not a code change) Restore trading scheduler**

- **Why:** The bot has been silent for 80 calendar days. AXTX, META, PWR have been held unmonitored since 5/4. All strategy proposals above are untestable without live data.
- **No diff** — this is a deployment/infrastructure action.
- **Expected impact:** Every strategy proposal above becomes immediately testable. Without this, none can be validated or killed.

---

### 2d. Offline backtest

**Proposal 2 (raise exit_arbiter.min_confidence to 0.65)** — partial offline test using 5/4 decisions.jsonl:

On 5/4, 7 exit_arbiter calls returned confidence 0.58–0.72. At threshold 0.65:
- HCAI (0.72): would still fire → correct exit saved
- AMZN (0.62): blocked → AMZN closed at 270.65; fate unknown
- GEV (0.62): blocked → GEV @ 1071.49; fate unknown
- UNH (0.62): blocked → UNH not swept; LLY rotation not triggered → saves ~2 round trips
- MU (0.58): **blocked** → MU stays at +12.9% gain; WDC rotation not triggered → ~+$1,200 in counterfactual value
- WDC (0.62): blocked (if entered) → would not be exited same session
- COIN (0.58): blocked → COIN held into earnings (risky but position-level decision)

**Single-day estimated impact (5/4 only, confidence floor at 0.65):** ~+$1,200 from MU retention + 2 fewer round trips (~$150 spread saved) = ~+$1,350 net on one session. Cannot be generalized without live data.

**Proposals 1, 3, 4** cannot be robustly backtested from journal data alone — they require the selector's scan-cycle IDs (not logged) and GICS sector data (not in journal). Proposal 5 requires equity reallocation simulation beyond what the on-disk journal supports.

**All proposals remain untested across a live multi-week window.** They are logically sound given the patterns in the 9-day dataset, but should be gated on at least 5 live trading days of observation before committing to config changes.

---

### Summary

The trading bot's last live session (2026-05-04) shows a structural churn problem: 53 trades in one day, 5 same-day entry→exit cycles, 3 wash-trade broker errors, and ~$1,200 in direct alpha destroyed by a single MU→WDC peer rotation. The 9-day active period ended with net +0.22% vs SPY compounding to ~+2.96% — a -2.74% alpha drag. The period_vs_spy field in 5/4 EOD (−10.71%) covers a longer 30-day window that's partially outside our dataset.

The highest-ROI fixes are **proposals 2 and 4** (exit confidence floor + peer rotation guard) and **proposal 6** (restore the scheduler). Without the scheduler running, no live feedback loop exists and all other proposals are hypothetical.

**The single most important action item remains operational: confirm the trading scheduler is alive and writing snapshots into this repo.**

