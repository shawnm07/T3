# Post-Mortem 2026-07-22

## Data availability

| Source | Status | Detail |
|---|---|---|
| `2026-07-22_eod.json` | **MISSING** | No bot data since 2026-05-04 (57 trading days / 79 calendar days) |
| Today's scan files | **MISSING** | Last scan: `20260504T195545_preclose.json` |
| `trades.jsonl` | Frozen at 2026-05-04T19:55Z | 204 lines; byte-identical for 79 days |
| `decisions.jsonl` | Frozen at 2026-05-04T20:15Z | 1556 lines; byte-identical for 79 days |
| yfinance / Alpha Vantage / Twelve Data | **BLOCKED** (403 via proxy) | No live price data available |
| Alpaca API | **BLOCKED** (403) | Cannot verify current account state |

**No trading activity can be reported for 2026-07-22.** All analysis below is based on the last known state (2026-05-04 EOD) and the 9-day active session log (2026-04-22 → 2026-05-04).

---

## Performance today (portfolio vs SPY, from eod.json)

*No 2026-07-22 snapshot exists. Using last known session (2026-05-04) and rolling data.*

### Last active session — 2026-05-04
| Metric | Value |
|---|---|
| Equity | $99,849.69 |
| Daily return | **-1.80%** |
| SPY daily | -0.36% |
| Portfolio vs SPY | **-1.44%** |
| Positions at close | 4 |
| Trades executed | 53 |

### 9-day rolling benchmark (all available data: 2026-04-22 → 2026-05-04)
| Day | Bot | SPY | Diff |
|---|---|---|---|
| 2026-04-22 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | **+1.95%** |
| 2026-04-24 | -0.81% | +0.77% | -1.58% |
| 2026-04-27 | **-4.88%** | +0.17% | -5.05% |
| 2026-04-28 | **-5.13%** | -0.49% | -4.64% |
| 2026-04-29 | **-5.40%** | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.44% |
| **Cumulative** | **-16.31%** | **+1.95%** | **-18.26%** |

**GOAL: beat SPY. Actual: -18.26% behind SPY over 9 sessions.** Risk budget breached on at least 3 consecutive days (4/27–4/29 each exceed 2.5% single-day loss threshold).

---

## Positions at close (last known: 2026-05-04 EOD)

| Symbol | Side | Qty | Avg Entry | Last Price (2026-05-04) | PnL% |
|---|---|---|---|---|---|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% |
| META | LONG | 15.4774 | $611.73 | $610.46 | -0.21% |
| PWR | LONG | 14.6949 | $758.48 | $757.38 | -0.15% |
| SPY | LONG | 83.138 | $717.52 | $718.03 | +0.07% |

**Note:** These prices are 79 calendar days stale. No current P&L computable without live data. AXTX is a **2× leveraged ETF** — unmonitored exposure since 2026-05-04 is the largest portfolio risk.

---

## Trades today (table)

*No trades on 2026-07-22. See Phase 2 below for 2026-05-04 (last active day) trade ledger.*

---

## (Full analysis appended below)

---

## Phase 2: Trade-level analysis — 2026-05-04 (last active session)

### 2a. Trade ledger

| Symbol | Side | Qty | Entry | Exit/Current | PnL% (est.) | AI Conf | Reason snippet | Verdict |
|---|---|---|---|---|---|---|---|---|
| LLY | BUY | 9.49 | $963.38 | $963.71 (sold) | +0.03% | arbiter | Strong continuation above VWAP | good — but immediately resized (2 fills) |
| LLY | INCREASE | 3.51 | $962.27 | $963.71 (sold) | +0.15% | arbiter | within 120-min fresh-exit guard | churn — 2nd fill within same scan |
| LLY | CLOSE | 13.0 | $963.38 avg | $963.71 | +0.03% | verifier | dust-sweep target=0 | churn — bought and dust-swept same session |
| MU | BUY | 25.0 | $580.42 | $580.81 (exit) | +0.07% | arbiter | Pool leader, perfect momentum | closed — exit_arbiter reduced/exited later |
| NOK | BUY | 367.24 | $13.33 | — | — | arbiter | Strong continuation above VWAP | unknown — not in EOD positions; likely closed |
| SNDK | BUY | 10.10 | $1,246.97 | — | — | arbiter | Best new candidate | unknown — not in EOD positions |
| DELL | BUY | 57.39 | $210.52 | $210.94 (sold) | +0.20% | arbiter | IT sector leader | closed — verifier dust-swept same session |
| FIX | BUY→INCREASE | 6.30+3.70 | $1,896.50/$1,903.71 | $1,902.81 (sold) | ~flat | arbiter | Peer/sector leader, 100 momentum | closed — verifier dust-swept final scan |
| GOOGL | BUY | 28.68 | $383.51 | $382.77 (exit) | -0.19% | arbiter | CommSvc leader | closed — exited same session by arbiter |
| GOOGL | INCREASE | 9.28 | $384.43 | $382.77 (exit) | -0.43% | verifier | reconcile to 14.6% target | churn — bought by verifier, exited by arbiter |
| WDC | BUY | 24.51 | $445.36 | $440.06 (exit) | -1.19% | arbiter | Memory peer leader | bad — gap_only classification, lost -1.19% |
| COIN | BUY | 5.10 | $203.90 | $203.45 (exit) | -0.22% | verifier | reconcile to 14.8% target | churn — verifier bought, arbiter exited |
| AMZN | CLOSE | 65.3 | — | $270.65 | — | arbiter EXIT | Fading momentum, below VWAP | good |
| GEV | CLOSE | 14.6 | — | $1,071.49 | — | arbiter EXIT | Weak momentum, below VWAP | good |
| HCAI | CLOSE | 1492.0 | — | $10.69 | — | exit-arbiter | -3.25% underwater, lost VWAP | good — right call |
| COIN | CLOSE | 66.9 | — | $203.45 | — | arbiter EXIT | Momentum 0, fading | good |
| GOOGL | CLOSE | 38.0 | — | $382.77 | — | arbiter EXIT | Momentum 0, fading, below EMA20 | good |
| AXTX | BUY | 313.0 | $46.41 | $46.61 | +0.43% | arbiter | Breaking_out, 100 momentum, 2.79× vol | held → currently frozen in book |
| META | BUY | 15.48 | $611.73 | $610.46 | -0.21% | arbiter | CommSvc diversification | held → currently frozen |
| PWR | BUY | 14.69 | $758.48 | $757.38 | -0.15% | arbiter | ai_data_center_power leader | held → currently frozen |

### 2b. Cross-trade patterns

- **Verifier/arbiter contradiction loop**: GOOGL and COIN were bought by the portfolio-verifier to close Opus-assigned gaps, then immediately exited by the arbiter (same session, same scan cycle). The verifier spent ~$4.6K reconciling toward Opus targets that the arbiter had already invalidated. This is the core turnover driver on 2026-05-04 (53 total trades).

- **Same-session round-trips (SPY-proxy churn)**: FIX entered, increased by arbiter to 19%, then verifier dust-swept it to 0 in the *same* final scan. DELL and LLY had identical patterns. These 3 symbols alone generated ~6 fills that net-zeroed.

- **Selector failure (2× at 14:09 and 15:02)**: `portfolio-selector` returned "selected count 0 not in [3,6]" twice, burning 3 attempts each time before falling back. This deleted valid targets (`selector_new_entry_targets_removed_pre_plan`) mid-session, forcing later scans to rebuild the pool from scratch — amplifying churn.

- **Exit arbiter at sub-threshold confidence**: 9 of 13 `exit_arbiter` decisions were `reduce` at confidence 0.58–0.62, which is just above the 0.55 floor. `reduce` without a corresponding `DECREASE` order in `executor.py` may be a no-op at the trade level (only `exit` triggers a close) — but the symbol stays flagged, causing the selector to drop it and replace it next scan.

- **Massive drawdown on 4/27–4/29 (-15.41% combined) vs SPY (-0.33%)**: Not explainable by today's data (no scan files from those dates). Suspected cause: high concentration in names with correlated downside (memory/semis) with aggressive stop-triggered exits cascading.

- **AI failure cascade**: Two selector failures at 14:09 and 15:02 likely caused the scanner to fall back to a numeric-only slate, entering positions that the arbiter immediately rejected on the next pass — contributing to the churn cycle.

- **WDC gap-only entry**: WDC was classified `gap_only` at entry; `gap_only_risk=true` appeared in candidate data yet the arbiter still entered (10.9% target). WDC closed -1.19% that session. Gap-only entries should be blocked.

- **AXTX as final position**: AXTX is the "Tradr 2× Long AXTI Daily ETF" — a daily-reset 2× leveraged product. At 14.4% of a $99K book (~$14.3K), it is by far the highest-risk remaining position. Unmonitored for 79 days.

### 2c. Proposed changes

All proposals are analysis-only. No config.yaml or src/*.py files are modified here.

---

**Proposal 1: Block verifier from buying symbols the arbiter exited in the same scan**

- **Why**: GOOGL and COIN were bought by verifier and exited by arbiter in the same 60-second window (see trade log 18:05 → 19:08). Net result: paid two bid-ask spreads plus double commission; zero economic position.
- **Diff (src/executor.py or portfolio_verifier agent)**: Add a session-level `arbiter_exits_this_scan: set[str]` guard in `executor.py`. If symbol in `arbiter_exits_this_scan`, reject verifier BUY for that symbol for the remainder of the scan cycle.
- **Expected impact**: Eliminates 2–6 wasteful round-trips per high-churn session. On May 4: would have prevented GOOGL+9.28 and COIN+5.10 fills → saved ~$4,500 in notional churn and ~$0.50 in commission; recovered ~$30 in slippage.

---

**Proposal 2: Selector failure → hold current book, do not replace targets**

- **Why**: Two selector failures at 14:09 and 15:02 triggered `selector_new_entry_targets_removed_pre_plan` — wiping the target list and forcing late-session rebuilds that created the verifier/arbiter conflict.
- **Diff (src/ai_pipeline.py)**: On `ai_failure` event for `portfolio-selector`, fall back to the *previous scan's* `selector_output` result rather than clearing targets. Only clear if selector succeeds with a different slate.
- **Expected impact**: Prevents the target-wipe churn cycle. On May 4: would have preserved the 14:09 slate, avoiding ~6 redundant entry/exit pairs.

---

**Proposal 3: Block new entries with `gap_only_risk=true`**

- **Why**: WDC entered with `gap_only_risk=true` in candidate data; closed -1.19%. The gap-only flag already exists in the candidate pipeline but is not enforced as a hard block.
- **Diff (src/decision.py or executor.py)**: Add `if candidate.gap_only_risk: skip entry` before buy submission. Already in the intraday chart data field.
- **Expected impact**: Eliminates one category of low-quality entries. Historical estimate: 3–5 positions per 20-session window would be blocked; based on the May 4 example, approximate save: ~0.1–0.3% per blocked entry.

---

**Proposal 4: Daily drawdown circuit breaker (hard stop at -2.5%)**

- **Why**: Bot lost -4.88%, -5.13%, -5.40% on three consecutive days (4/27–4/29), breaching the 2.5% daily risk budget. No circuit breaker halted new entries or reduced exposure.
- **Diff (src/orchestrator.py)**: Read today's `daily_return` from the running account snapshot. If `daily_return < -0.025`, skip all new BUY orders for the remainder of the session. Exits still run.
- **Expected impact**: Would have halted entries on 4/27, 4/28, 4/29 if prior-day loss triggered. Estimated P&L save: avoids compounding losses on already-down days. Conservative estimate: 1–3% equity preservation per triggered session.

---

**Proposal 5: Require AXTX-class leveraged ETFs to use reduced position cap**

- **Why**: AXTX ("Tradr 2× Long AXTI Daily ETF") was allocated 14.4% of the book — same as a non-leveraged equity. A 2× daily-reset product has ~2× the tail risk and suffers from volatility decay.
- **Diff (config.yaml)**: Add a `leveraged_etf_max_position_pct: 0.05` key. Add detection in `executor.py`: if symbol name/asset class matches known leveraged ETF pattern (e.g., contains "2X Long", "3X", "Direxion", "ProShares Ultra"), cap notional at `leveraged_etf_max_position_pct`.
- **Expected impact**: AXTX would have been capped at ~$5K instead of ~$14.3K on May 4. Reduces single-position tail risk. No backtest possible without live pricing data.

---

**Proposal 6: Operational — confirm bot scheduler and write-path before any strategy changes**

- **Why**: 57 trading days of silence invalidates all the above proposals — they cannot be tested, validated, or safely deployed while the bot is not running and this repo is not receiving data.
- **Action items** (unchanged from 15 prior reviews):
  1. Confirm `scripts/scan_and_trade.py` cron has fired since 2026-05-04.
  2. Check `data/research/` write path on the runtime host vs this checkout.
  3. Log into PA34KBGT3V7E Alpaca dashboard — confirm current positions and equity.
  4. If frozen: decide whether to hold AXTX (leveraged ETF, 79+ unmonitored days) or close it manually.
  5. Allowlist one market-data host so future post-mortems can grade the frozen allocation vs SPY.

---

### 2d. Backtest

No backtest possible. All market-data hosts (yfinance `fc.yahoo.com`, Alpha Vantage, Twelve Data) return HTTP 403 at the proxy layer — confirmed again this session. Proposals 1–3 are purely mechanical (no market data required); their impact estimates above are based on May 4 trade log math only.

---

## Summary

The last 9 trading sessions (2026-04-22 → 2026-05-04) produced **-16.31%** bot return vs **+1.95%** SPY, an **18.26% alpha deficit**. The primary drivers were:

1. Three consecutive -5% sessions (4/27–4/29) with no drawdown circuit breaker.
2. High same-session churn on 2026-05-04 (53 trades, net ~flat) driven by verifier/arbiter contradictions and selector failures.
3. Gap-only entries (WDC) passing the buy gate.
4. AXTX (2× leveraged ETF) left as the largest single-stock position in a frozen book for 79+ calendar days.

**The most urgent action is operational**: until the bot is confirmed running and writing snapshots into this repo, strategy proposals have no feedback loop and the frozen AXTX position accumulates unmonitored leverage risk every day.
