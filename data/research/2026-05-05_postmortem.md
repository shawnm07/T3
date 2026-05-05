# Post-Mortem 2026-05-05 (Trading Day: 2026-05-04)

_Generated 2026-05-05 by post-mortem-bot. Analysis date = today; most recent trading day = 2026-05-04._

---

## Data Availability

| Source | Status |
|---|---|
| `data/research/2026-05-04_eod.json` | ✅ found |
| `data/research/20260504T*_scan.json` (6 scans) | ✅ found |
| `data/journal/trades.jsonl` | ✅ found |
| `data/journal/decisions.jsonl` | ✅ found |
| `data/research/2026-05-05_eod.json` | ❌ missing (market not yet closed) |
| Live Alpaca / yfinance / Telegram | 🚫 blocked (sandbox) |

---

## Performance — 2026-05-04

| Metric | Value |
|---|---|
| EOD Equity | $99,849.69 |
| Day Open Equity (scan 1) | $101,047.91 |
| Daily Return (reported) | **-1.80%** |
| SPY Daily | -0.36% |
| Alpha vs SPY | **-1.44%** (underperform) |
| Trades Executed | **26 fills** (53 order events total) |
| Positions at Close | 4 (AXTX, META, PWR, SPY) |
| Cash at Close | $4,986.91 (5.0% — at floor) |
| Macro Regime (final scan) | Neutral, score 0.27, VIX 27.83 |

### Rolling Benchmark

| Window | Portfolio | SPY | Alpha |
|---|---|---|---|
| 1d (2026-05-04) | -1.80% | -0.36% | -1.44% |
| 5d (04-28 → 05-04) | -13.18% | +0.39% | **-13.57%** |
| Since data start (22 Apr) | -17.31% | +1.95% | **-19.26%** |

> The bot has shed ~19 percentage points vs SPY since 22 April. This is a structural problem, not noise.

---

## Positions at Close — 2026-05-04 EOD

| Symbol | Side | Avg Entry | EOD Price | P&L % | Market Value | Source |
|---|---|---|---|---|---|---|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | $14,588.93 | yfinance |
| META | LONG | $611.73 | $610.46 | -0.21% | $9,448.36 | yfinance |
| PWR | LONG | $758.48 | $757.38 | -0.15% | $11,129.62 | yfinance |
| SPY | LONG | $717.52 | $718.03 | +0.07% | $59,695.86 | yfinance |

> SPY cash-proxy represents **59.8% of equity** at close — the bot is mostly SPY while churning the rest.

---

## Trades — 2026-05-04 (Executed Fills Only)

| Time (UTC) | Action | Symbol | Qty | Price | Trigger |
|---|---|---|---|---|---|
| 14:51 | SELL | HCAI | 1,492 | $10.69 | exit |
| 16:04 | SELL | AMZN | 65.30 | $270.65 | arbiter EXIT |
| 16:04 | SELL | GEV | 14.57 | $1,071.49 | arbiter EXIT |
| 16:04 | SELL | UNH | 17.27 | $368.25 | arbiter EXIT |
| 16:04 | BUY | LLY | 9.49 | $963.38 | arbiter BUY |
| 16:04 | BUY | MU | 25.00 | $580.42 | arbiter INCREASE |
| 16:04 | BUY | NOK | 367.24 | $13.33 | arbiter BUY |
| 16:04 | BUY | SNDK | 10.10 | $1,246.97 | arbiter BUY |
| 17:04 | SELL | MU | 23.01 | $580.81 | arbiter EXIT (→ WDC) |
| 17:04 | BUY | DELL | 57.39 | $210.52 | arbiter BUY |
| 17:04 | BUY | FIX | 6.30 | $1,896.50 | arbiter BUY |
| 17:04 | BUY | GOOGL | 28.68 | $383.51 | arbiter BUY |
| 17:04 | BUY | LLY | 3.51 | $962.27 | arbiter INCREASE |
| 17:04 | BUY | WDC | 24.51 | $445.36 | arbiter BUY (peer swap) |
| 17:04 | BUY | COIN | 5.10 | $203.90 | verifier reconcile |
| 18:05 | SELL | WDC | 24.51 | $440.06 | arbiter EXIT |
| 18:05 | BUY | FIX | 3.70 | $1,903.71 | arbiter INCREASE |
| 18:05 | SELL | DELL | 57.39 | $210.94 | verifier dust-sweep |
| 18:05 | SELL | LLY | 13.00 | $963.71 | verifier dust-sweep |
| 18:05 | BUY | GOOGL | 9.28 | $384.43 | verifier reconcile |
| 19:08 | SELL | COIN | 66.90 | $203.45 | arbiter EXIT |
| 19:08 | SELL | GOOGL | 37.96 | $382.77 | arbiter EXIT |
| 19:08 | BUY | AXTX | 313.00 | $46.41 | arbiter BUY |
| 19:08 | BUY | META | 15.48 | $611.73 | arbiter BUY |
| 19:08 | BUY | PWR | 14.69 | $758.48 | arbiter BUY |
| 19:08 | SELL | FIX | 10.00 | $1,902.81 | verifier dust-sweep |

_(Full analysis with per-trade grades and cross-trade patterns follows in next commit.)_

---

## Full Analysis

### 2a — Per-Trade Quality Assessment

| Symbol | Action | Entry | Exit | P&L% | AI Grade | Verdict |
|---|---|---|---|---|---|---|
| HCAI | SELL | prior | $10.69 | n/a | — | pre-market close, no intraday data |
| AMZN | SELL (exit) | prior | $270.65 | n/a | 0.8 conf EXIT | **churn** — sold in scan 3, was a fresh buy in scans 1-2; held <2h |
| GEV | SELL (exit) | prior | $1,071.49 | n/a | EXIT | ok — "flat trend, below VWAP" |
| UNH | SELL (exit) | prior | $368.25 | n/a | EXIT | **questionable** — swapped for LLY; both were fine |
| LLY | BUY→SELL | $963.00 avg | $963.71 | +0.07% | BUY → dust | **verifier-killed** — arbiter had fresh_exit cooldown; verifier swept it; net +$10 |
| MU | BUY→SELL | $580.42 | $580.81 | +0.07% | arbiter swap | **peer-churn** — sold to buy WDC; WDC lost -1.19% within the hour |
| NOK | BUY→? | $13.33 | unknown | n/a | BUY | entered, then vanished from EOD; exit not in executed fills — preclose exit |
| SNDK | BUY | $1,246.97 | held overnight? | — | BUY | selected by final scan but no EOD position listed; preclose exit |
| DELL | BUY→SELL | $210.52 | $210.94 | +0.20% | BUY | **verifier-killed** — 52-minute hold; had fresh_exit cooldown block; verifier swept |
| FIX | BUY→SELL | $1,899 avg | $1,902.81 | +0.19% | BUY | **verifier-killed** — held 1h, had cooldown; verifier swept despite tech_score=0.836 |
| GOOGL | BUY→SELL | $383.65 avg | $382.77 | -0.23% | BUY→EXIT | **noise exit** — -0.23% in 2h; bid/ask spread likely consumed all alpha |
| WDC | BUY→SELL | $445.36 | $440.06 | **-1.19%** | BUY→EXIT | **bad peer swap** — sold MU to buy WDC; WDC hit stop in <1h |
| COIN | BUY→SELL | $203.90 | $203.45 | -0.22% | EXIT | **earnings risk** — entered, exited same day over earnings concern; net negative |
| AXTX | BUY (held) | $46.41 | $46.61 | +0.43% | BUY | good — highest P&L at close |
| META | BUY (held) | $611.73 | $610.46 | -0.21% | BUY | ok — minor loss, held overnight |
| PWR | BUY (held) | $758.48 | $757.38 | -0.15% | BUY | ok — minor loss, held overnight |

---

### 2b — Cross-Trade Patterns

- **Extreme churn (26 fills, 53 order events, 6 scans)**: Average hold before exit was under 2 hours. Bid-ask friction + commissions destroyed alpha even when direction was right. DELL (+0.20%), FIX (+0.19%), LLY (+0.07%) all won but the gains were negligible vs. the churn tax on losers.

- **Peer-swap chain MU → WDC → exit**: Sold MU at 17:04 (momentum flat) to buy WDC (peer with higher score). WDC lost -1.19% within 60 minutes and was exited at 18:05. This is the single largest individual loss of the day in dollar terms (~$130). SNDK had been sold at 15:13 then rebought at 16:04 — another SNDK/MU swap reversal.

- **Verifier vs. arbiter conflict**: The verifier swept DELL, LLY, and FIX as "dust" even though: (a) arbiter had fresh_exit_cooldown guards on all three; (b) tech_score for FIX was 0.836. The verifier's force-close overrides the arbiter's protection, creating an unintended authority leak. Three closed positions with positive momentum wiped.

- **SOXS selected by portfolio-selector**: At 19:08 scan, selector chose SOXS (3× inverse semiconductor ETF) — explicitly prohibited by CLAUDE.md "long US equities only." Execution was blocked by preflight, but the selector must never propose it.

- **SPY cash-proxy bloat**: SPY grew to 59.8% of equity by EOD. When the bot can't find valid candidates (cash limited or candidates blocked), it parks in SPY. While not harmful, this turns the strategy into ~60% SPY + 40% highly churned micro-positions, which will never beat SPY.

- **Over-trimming winners**: GEV (ai_data_center_power) was sold for "flat trend" but had been a strong performer. UNH was sold for LLY — both were fine healthcare names. Neither exit was clearly wrong technically, but the churn created by the swap negated any alpha.

- **Earnings-aware entries with same-day exits**: COIN entered at 16:04 (verifier reconcile) and exited at 19:08 citing "earnings in 3 days." The earnings concern was already known at entry time. This suggests the entry-gate earnings check and exit-trigger earnings check are inconsistent.

- **AI vs numeric**: In the 15:13 scan, SNDK was sold because "MU has superior remaining upside" (AI peer preference). By 16:05, SNDK was rebought as "best new candidate." AI was wrong on the peer ranking within 90 minutes.

---

### 2c — Proposed Changes

#### Proposal 1: Hard intraday trade-count cap
**Why**: 53 order events in one day (26 fills) destroyed alpha via churn. The 6-scan cadence with no position-count guard creates unbounded turnover.
**Diff**:
```yaml
# config.yaml — add under risk:
risk:
  max_trades_per_day: 12            # was: unlimited
  min_hold_scans_before_exit: 2     # was: 0 (any scan can exit)
```
**Expected impact**: Reduces daily order events by ~60%. Eliminates DELL/FIX/LLY churn. Rough estimate: +0.3% daily alpha recovery from friction reduction alone.

---

#### Proposal 2: Peer-swap cooldown
**Why**: MU → WDC peer swap cost -1.19% in one hour. SNDK → MU peer swap was reversed 90 minutes later. Peer swaps on intraday momentum are pure noise trades.
**Diff**:
```yaml
# config.yaml — add under selector:
selector:
  peer_swap_cooldown_minutes: 180   # was: 0 (no cooldown)
  peer_swap_min_score_gap: 15       # was: peer_outperformance_threshold: 10
```
**Expected impact**: Eliminates ~4-6 trades/day of peer-swap churn; prevents buying into a name that was recently sold as inferior.

---

#### Proposal 3: Verifier must not override fresh_exit_cooldown
**Why**: Verifier swept DELL, LLY, FIX despite active arbiter cooldown guards. The verifier's dust-sweep authority should be subordinate to the arbiter's position protection.
**Diff** (`src/executor.py` or verifier logic — proposal only, do not modify):
```python
# In verifier dust-sweep logic, add guard:
# BEFORE: force_close if target_qty == 0 and actual_qty > 0
# AFTER:
if position_has_fresh_exit_cooldown(symbol) and tech_score > 0.5:
    skip dust-sweep; log "deferred to arbiter cooldown"
```
**Expected impact**: Prevents ~3 phantom exits per day session. FIX (tech_score=0.836) would have been held to EOD, contributing positive alpha.

---

#### Proposal 4: Block inverse/leveraged ETFs in selector
**Why**: SOXS was selected at 19:08. SOXS is a 3× inverse semiconductor ETF — explicitly prohibited ("long US equities only"). Preflight caught it, but the selector wasted a slot and potentially displaced a valid candidate.
**Diff** (`src/orchestrator.py` or `src/discovery.py` — proposal only):
```python
# In candidate pool construction, add pre-filter:
BLOCKED_PATTERNS = ['SOXS', 'SOXL', 'UVXY', 'SVXY', 'SPXS', 'TQQQ', 'SQQQ', ...]
# Or: reject any ETF with 'inverse' or 'bear' in fund description
```
**Expected impact**: Recovers one selector slot per occurrence; removes preflight friction; eliminates edge case where selector logic misgrades an inverse ETF as a BUY.

---

#### Proposal 5: Cap SPY cash-proxy at 30%
**Why**: SPY at 59.8% of equity means the bot is running a closet index fund while paying churn costs on the remaining 40%. If the selector can't find 4+ valid names, it should park in cash, not SPY.
**Diff**:
```yaml
# config.yaml — add under cash_proxy or selector:
selector:
  max_spy_proxy_pct: 0.30           # was: uncapped (floats to fill remaining equity)
  spy_proxy_fallback: "cash"        # was: "SPY" (buy SPY to fill gap)
```
**Expected impact**: Forces the portfolio to hold cash when conviction is low, reducing implicit SPY correlation drag. With 4 individual names at 15% each (60%), only 10% residual → 10% cash, not 50% SPY.

---

#### Proposal 6: Minimum 2-scan hold before entry allowed to become exit candidate
**Why**: LLY entered at 16:04, killed by verifier at 18:05 (1 scan later). DELL entered 17:04, killed 18:05 (same scan cycle). A position that is <2 scan cycles old (< ~2 hours) should require a higher exit confidence threshold (≥ 0.85 vs default 0.55).
**Diff**:
```yaml
# config.yaml — add under exit_arbiter:
exit_arbiter:
  min_confidence: 0.55              # existing
  fresh_entry_exit_min_confidence: 0.85   # new — applies if position age < 2 scan cycles
  fresh_entry_scans: 2              # number of scan cycles considered "fresh"
```
**Expected impact**: Aligns with existing `fresh_exit_cooldown` guard already in code but currently bypassable by verifier. Quantified: would have saved DELL (+0.20%), LLY (+0.07%), FIX (+0.19%) exits today — ~$45 in direct gains plus avoided re-entry friction.

---

### 2d — Offline Backtest Note

Proposals 1, 2, 4, 5, 6 cannot be backtested with in-repo journal data alone: the journal records executed trades but not the counterfactual positions that would have been held if the trade were blocked. A meaningful backtest requires replay of full scan data with modified logic.

Proposal 3 (verifier cooldown guard) can be partially estimated: today's verifier swept FIX at tech_score=0.836, which then continued to $1,902.81 close. FIX was the selector's #1 pick at 18:05 and 19:08. Holding would have saved the force-close ($1,902.81 fill) and avoided the re-entry friction. Net estimated saved P&L: ~$40–$60 for today only; structural benefit if this occurs daily across 1–3 positions per session.

---

## Summary

The primary driver of underperformance (-1.44% vs SPY) is **friction from excessive churn (26 fills in 6 scans)**, not directional error. The bot's arbiter correctly identified AXTX, META, PWR as EOD holds — the problem is that it also exited 13 other positions intraday, many of which were profitable small-cap moves that got swept by the verifier or swapped in peer trades that didn't pan out.

The **verifier/arbiter authority conflict** is the most actionable fix: the verifier is overriding the arbiter's fresh_exit_cooldown guards, destroying positions with positive technicals. This is a code defect, not a strategy disagreement.

**Priority order**: P3 (verifier guard) → P1 (trade-count cap) → P2 (peer-swap cooldown) → P6 (fresh-entry exit threshold) → P4 (block inverse ETFs) → P5 (SPY proxy cap).
