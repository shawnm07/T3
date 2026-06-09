# Post-Mortem 2026-06-09

## Data Availability

| Source | Status | Notes |
|--------|--------|-------|
| `2026-06-09_eod.json` | **MISSING** | Bot has been dormant since 2026-05-04 |
| `20260609*_scan.json` | **MISSING** | No scans ran today |
| `data/journal/trades.jsonl` | Present | Last entry: 2026-05-04 |
| `data/journal/decisions.jsonl` | Present | Last entry: 2026-05-04 |
| `config.yaml` | Present | Baseline for proposals |
| Historical EOD (9 days) | Present | 2026-04-22 → 2026-05-04 |

**Critical finding:** The bot has been completely dormant for ~26 calendar days (~18 trading days) between 2026-05-04 and 2026-06-09. No trades, no scans, no EOD snapshots exist for this period. All analysis below is based on the last active trading session (2026-05-04) and the available historical window (2026-04-22 → 2026-05-04).

---

## Performance Today (Portfolio vs SPY)

*No data for 2026-06-09. Reporting last-known state from 2026-05-04.*

| Metric | Value |
|--------|-------|
| Last known equity | $99,849.69 |
| Daily return (2026-05-04) | **-1.80%** |
| SPY daily (2026-05-04) | -0.36% |
| Daily vs SPY | **-1.43%** |
| 30-day portfolio return | ~0.22% ($99,627 → $99,850) |
| 30-day SPY return | **+10.71%** (from `spy_30d` field) |
| 30-day alpha | **-10.49%** |
| Cash position | $4,987 (5.0% of equity) |

### Rolling Returns (from EOD history)

| Window | Portfolio | SPY | Alpha |
|--------|-----------|-----|-------|
| 5-day (04-28→05-04) | -12.67% | +0.38% | **-13.05%** |
| 9-day (04-22→05-04) | +0.22% | +10.71% | **-10.49%** |

### Daily Return Series

| Date | Portfolio | SPY | vs SPY |
|------|-----------|-----|--------|
| 2026-04-22 | 0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | **+1.95%** |
| 2026-04-24 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | -4.88% | +0.17% | **-5.05%** |
| 2026-04-28 | -5.13% | -0.49% | -4.65% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.43% |

---

## Positions at Last Close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | Close Price | P&L % | P&L $ | Weight |
|--------|------|-----|-----------|-------------|-------|-------|--------|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** | +$62.60 | 14.6% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | -$19.63 | 9.5% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | -$16.16 | 11.1% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | +$42.40 | **59.8%** |

*P&L computed as (current_price - avg_entry) / avg_entry per instructions. Alpaca's unrealized_plpc disregarded.*

SPY is 59.8% of portfolio — effectively the bot is running ~60% as a market-tracking cash proxy.

---

## Trades Last Active Day (2026-05-04)

**53 trades executed on 2026-05-04** (highest churn day in the dataset).

Key events from `trades.jsonl` (last active session):

| Event | Symbol | Side | Price | Reason Summary |
|-------|--------|------|-------|----------------|
| EXIT | GEV | SELL | $1,071.49 | Weak momentum, below VWAP, bearish EMA |
| EXIT | UNH | SELL | $368.25 | Fading volume; LLY preferred as healthcare name |
| BUY | LLY | BUY | $963.38 | Strong continuation; healthcare sector leader |
| ROTATION | FIX,CUE,COIN,PWR,GOOGL,RBLX | — | — | Selector rotated 3 in, 3 out (WDC/LLY/DELL exited) |
| EXIT | WDC | SELL | — | Gap-only classification, thesis broken |
| EXIT | LLY | SELL | — | Fading momentum score 53 (entered and exited same session) |

*LLY was entered and then exited within the same scan cycle — a wash trade.*

Trade count per day: 7, 9, 19, 24, 21, 10, 23, 38, 53. Accelerating churn.

---

## Trade / Decision Quality Table (Last Active Session: 2026-05-04)

| Symbol | Action | Entry | Exit/Current | P&L % | AI Grade | One-line Reason | Verdict |
|--------|--------|-------|--------------|-------|----------|-----------------|----------|
| GEV | EXIT | $1,140.45 (avg) | $1,071.49 | -6.1% | conf 0.97 | Weak momentum, below VWAP, bearish EMA | OK — correctly exited loser |
| UNH | EXIT | — | $368.25 | — | conf 0.97 | Fading volume; LLY preferred | Premature — UNH had acceptable continuation |
| LLY | BUY→EXIT | $963.38 | $963.71 | +0.03% | — | Entered; exited same scan (score 53, "fading") | **CHURN** — wash trade, net loss after spread |
| WDC | EXIT | — | $440.06 | — | — | Gap-only, thesis broken | OK — correctly exited |
| HCAI | EXIT | $11.84 (05-01) | $10.69 | -9.7% | conf 0.72 | Down -8.78% with low volume | OK — loss cut, reasonable |
| AMZN | EXIT | — | $270.65 | — | — | Fading momentum, below VWAP | Cannot evaluate without avg_entry |
| MU | EXIT | $512.74 | $580.81 | +13.0% | — | "Weak_or_flat momentum" | **MISSED** — sold a winner, possibly confusion from split price |
| DELL | EXIT | $208.54 | $210.94 | +1.1% | — | Verifier dust-sweep | Neutral — near-flat position cleared |
| COIN | EXIT | — | $203.45 | — | — | Momentum 0, earnings risk | OK — risk-based exit |
| GOOGL | EXIT | — | $382.77 | — | — | Momentum 0, fading | OK |
| FIX | EXIT | $1,768.58 (avg) | $1,902.81 | +7.6% | — | Verifier dust-sweep | **MISSED** — exited a 7.6% winner via dust-sweep |
| AXTX | BUY+HOLD | $46.41 | $46.61 | +0.43% | conf high | Momentum 100, breaking_out | Good — small starter, holding |
| META | BUY+HOLD | $611.73 | $610.46 | -0.21% | — | Comm Services leader | OK — flat, thesis intact |
| PWR | BUY+HOLD | $758.48 | $757.38 | -0.15% | — | AI data center power leader | OK — flat, thesis intact |

**2026-05-01 same-session entry+exit pairs (churn day):**

| Symbol | Entered | Exited | Hold Duration | P&L est |
|--------|---------|--------|---------------|---------|
| TSLA | Scan 1 | Scan 1 | <1 scan | minimal |
| TSLA | Scan 2 | Scan 2 | <1 scan | minimal |
| AMD | Scan 1 | Scan 1 | <1 scan | minimal |
| INTC | Scan 1 | Scan 1 | <1 scan | +5.9% intraday then exited |
| MSFT | Scan 1 | Scan 1 | <1 scan | — |
| SOFI | Scan 1 | Scan 1 | <1 scan | minimal |
| UNH | Scan 1 | Scan 1 | <1 scan | minimal |
| AVGO | Scan 1 | Scan 1 | <1 scan | minimal |
| PWR | Scan 1 | Scan 1 | <1 scan | minimal |
| BAND | Scan 1 | Scan 1 | <1 scan | +23.5% intraday then exited |

38 events on 2026-05-01 = 10 of 11 new entries exited same session.

---

## Cross-Trade Patterns

- **Escalating churn spiral:** Trade counts grew 7→9→19→24→21→10→23→38→53 over 9 active days. Each scan found reasons to rotate, even though every rotation produced additional wash trades and spread drag.

- **Same-session entry+exit (wash trades):** 10 symbols entered and exited on 2026-05-01 within the same session. LLY bought and exited within a single scan cycle on 2026-05-04. The 120-minute fresh-entry protection exists in the selector system prompt but is NOT enforced in code — the exit-arbiter can override it the same scan.

- **INTC and BAND were winners — exited prematurely:** INTC was up +5.9% intraday; BAND was up +23.5% intraday. Both were exited "due to fading volume" with no opportunity to compound. These are the type of moves the bot should be holding, not rotating out of.

- **SOXS selected 24 times across multiple scans (2026-04-28 onward):** SOXS is a 3× inverse semiconductor ETF — a **short position**. The CLAUDE.md policy is "Long US equities only (no shorts, no crypto)." `exclude_tickers` is currently `[]`. No filtering prevents this in discovery or the selector pool.

- **AI data center over-concentration (8 sector guard violations):** The `ai_data_center` theme repeatedly hit or exceeded the 50% weight cap. The sector guard detected violations but the selector kept proposing the same concentrated portfolio. MU/AVGO/FIX/PWR/VRT/GEV all in the same theme simultaneously on multiple scans.

- **Exhaustion penalty cycling — same names repeat:** AMD penalized 8×, STX 8×, NOK 7×, BAND 7×, INTC 6×. These symbols are being bought, exhaustion-penalized, exited, and re-entered across scans. The exhaustion penalty is scan-scoped, not session-scoped — a symbol penalized at 14:00 can re-enter at 16:00.

- **MU price/avg_entry mismatch (data quality bug):** On 2026-04-29, MU showed avg_entry=$517.23, current=$102.89, pnl_pct=-80.1%. This coincides with a ~5:1 split in MU pricing. The avg_entry was not split-adjusted, triggering an apparent -80% loss that was likely a data artifact. MU was then exited on 2026-04-30 with "weak momentum" — but the real position may have been near flat. **Risk: the bot may have panic-exited a position based on a false price signal.**

- **SPY proxy grew to 60% of portfolio:** Starting from ~2% SPY exposure (04-22), the cash proxy grew to 59.8% by 05-04. This means 60% of capital is earning ~SPY return with the remaining 40% subject to high churn drag. Net expected alpha approaches zero or negative from friction alone.

- **FIX exited at +7.6% via verifier dust-sweep:** The verifier's dust-sweep closed FIX (only ~6 shares remaining) at $1,902.81. This is fine mechanically, but highlights that the selector rotated FIX out in an earlier cycle, leaving a dust position that needed cleanup. FIX was a winner.

---

## Proposed Changes

### P1 — Block inverse/leveraged ETFs from the candidate pool

**Why:** SOXS appeared in the selector pool 24 times and was recommended by portfolio-selector on 2026-04-28 and 2026-05-04 scans. SOXS is a 3× inverse ETF — holding it is equivalent to a short. Policy strictly forbids shorts.

**Diff (config.yaml):**
```yaml
# BEFORE
universe:
  exclude_tickers: []

# AFTER
universe:
  exclude_tickers:
    - SOXS    # 3x inverse semis
    - SQQQ    # 3x inverse QQQ
    - SDOW    # 3x inverse Dow
    - SPXS    # 3x inverse S&P
    - UVXY    # leveraged VIX long (not equity)
    - SVXY    # inverse VIX
    - TECS    # 3x inverse tech
```

**Expected impact:** Eliminates all inverse/leveraged-short ETF selection. Zero risk to upside trades. One-line change.

---

### P2 — Cap SPY cash-proxy allocation at 35%

**Why:** SPY reached 59.8% of portfolio on 2026-05-04. At 60% passive exposure, the bot cannot beat SPY — churn friction alone guarantees underperformance. The 9-day alpha is -10.49%.

**Diff (config.yaml):**
```yaml
# BEFORE
cash_proxy:
  # (no max_pct field currently)

# AFTER
cash_proxy:
  # ... existing fields ...
  max_pct: 0.35   # hard ceiling on SPY proxy allocation
```

The portfolio-selector prompt already receives `cash_proxy` configuration. Adding `max_pct: 0.35` gives it a guardrail to enforce. If the Python code doesn't read this key yet, it becomes an explicit selector prompt constraint.

**Expected impact:** Forces 65%+ of capital into active positions. If the bot's active positions underperform, this increases drawdown risk — but the current -10.49% alpha shows parking in SPY while churning active positions is worse.

---

### P3 — Extend exhaustion penalty to session-scope (not scan-scope)

**Why:** AMD penalized 8×, STX 8×, NOK 7×, BAND 7×. These symbols are bought, exhaustion-penalized at end of scan, then re-enter the pool the next scan because the penalty resets. The result is a continuous loop of buying, penalizing, exiting, re-entering.

**Diff (config.yaml):**
```yaml
# BEFORE
selector:
  # (no exhaustion_cooldown_hours field)

# AFTER
selector:
  exhaustion_cooldown_hours: 8   # symbol penalized in scan N is excluded until N+8h
```

This requires the selector in `ai_pipeline.py` to track exhaustion timestamps per symbol across scans (in `data/state/` or passed via context). The current scan-level penalty already uses a list; extending it to a time-bounded set is a small change.

**Expected impact:** Breaks the buy→penalize→exit→re-buy loop. AMD, STX, BAND would cycle at most once per session instead of 7-8 times. Estimated trade reduction: 15-20 fewer trades/day.

---

### P4 — Hard-code a minimum 2-scan hold requirement for new entries

**Why:** 10 of 11 new entries on 2026-05-01 were exited in the same session. The 120-minute fresh-entry protection is in the selector system prompt but the exit-arbiter overrides it freely. LLY was entered and exited within a single scan cycle. This generates wash trades and spread drag with zero opportunity to capture the move.

**Diff (config.yaml):**
```yaml
# BEFORE
selector:
  enabled: true

# AFTER
selector:
  enabled: true
  min_hold_scans: 2   # new entries cannot be exit-arbited until they've survived 2 scans
```

Implementation: `orchestrator.py` tracks `first_scan_ts` per position in `data/state/`. The exit-arbiter call is skipped for positions whose `first_scan_ts` is within the last `min_hold_scans × scan_interval` minutes, unless a stop-loss triggers.

**Expected impact:** Prevents same-session wash trades. With 6 scans/day and min_hold_scans=2, minimum hold ≈ 40-80 minutes. Stop-loss still fires normally — this only blocks AI-initiated discretionary exits.

---

### P5 — Add stock-split detection to avg_entry recalculation

**Why:** MU showed avg_entry=$517, current=$103, pnl=-80.1% on 2026-04-29. This is consistent with a 5:1 split where avg_entry was not adjusted. The bot likely exited MU based on this false signal, missing any recovery. The correct pnl would have been close to 0%.

**Diff (src/orchestrator.py — detection logic, not a config change):**
```python
# In _build_position_snapshot() or equivalent, after computing pnl_pct:
# BEFORE: no split detection
pnl_pct = (current_price - avg_entry) / avg_entry

# AFTER: detect likely split artifact
SPLIT_RATIOS = [2, 3, 4, 5, 10]
for ratio in SPLIT_RATIOS:
    if abs((current_price * ratio - avg_entry) / avg_entry) < 0.05:
        log.warning("[%s] Possible %d:1 split detected (avg_entry=%.2f, current=%.2f). "
                    "Adjusting avg_entry.", symbol, ratio, avg_entry, current_price)
        avg_entry = avg_entry / ratio
        pnl_pct = (current_price - avg_entry) / avg_entry
        break
```

This is a safeguard: if current_price × integer ratio ≈ avg_entry (within 5%), the avg_entry is halved/thirded/etc. and pnl recalculated. The correct value is still logged as a warning for human review. The bot also updates its internal state so the exit-arbiter doesn't see a phantom -80% loss.

**Expected impact:** Prevents panic-exits on split artifacts. Low risk: only fires when the ratio check is satisfied, which is rare outside actual splits.

---

## Offline Backtest (P3 — exhaustion cooldown)

Using `data/journal/trades.jsonl` only (no network):

- Total exhaustion-penalized symbols across 26 scans: AMD×8, STX×8, NOK×7, BAND×7, INTC×6, GBTG×6, AKAN×5, PWR×5, DELL×4, CRMX×4 = ~60 exhaustion-penalty events
- Each exhaustion penalty typically results in: 1 exit event (same scan or next) + 1 re-entry (next scan) = ~2 trades/cycle
- Estimated wash-trade pairs attributable to cycling: ~30 round-trips
- At ~$10K average position size, spread/slippage est. 0.02%: 30 × $10K × 0.02% × 2 = **~$120 friction cost**
- Over 9 active days: $120 / $99K = 0.12% direct drag from exhaustion cycling alone
- With P3 (8h cooldown): 60 exhaustion events → ~15 (one per symbol per session), saving ~45 round-trips → **~$90 friction saved over 9 days**

This is conservative (doesn't account for buying back at worse prices). Not backtestable for alpha impact without price data.

P1 (SOXS block), P2 (SPY cap), P4 (min_hold_scans), P5 (split detection) cannot be quantified from journal data alone — they require price time-series.
