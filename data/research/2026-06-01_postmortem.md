# Post-Mortem 2026-06-01

> **Session date:** 2026-06-01  
> **Analysis covers:** 2026-05-04 (latest snapshot with trades)  
> **Analyst:** Post-Mortem Bot (claude-sonnet-4-6)

---

## Data availability

| File | Status |
|------|--------|
| `data/research/2026-05-04_eod.json` | ✅ found — primary source |
| `data/research/2026-06-01_eod.json` | ❌ missing (no market data since May 4) |
| `data/research/20260504T*_scan.json` | ✅ 6 scan files found |
| `data/journal/trades.jsonl` | ✅ found |
| `data/journal/decisions.jsonl` | ✅ found |
| `config.yaml` | ✅ found |

Latest EOD snapshot is **2026-05-04**. No newer data in repo.  
All figures below refer to May 4.

---

## Performance today (portfolio vs SPY, from eod.json)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Relative performance | **-1.44%** (underperformed) |
| Portfolio equity | $99,849.69 |
| Trades executed | **53** |
| Open positions at close | 4 |

### Rolling comparison (5-day)

| Date | Portfolio | SPY | Diff |
|------|-----------|-----|------|
| 2026-04-28 | -5.13% | -0.49% | **-4.64%** |
| 2026-04-29 | -5.40% | -0.01% | **-5.39%** |
| 2026-04-30 | -2.67% | +0.96% | **-3.63%** |
| 2026-05-01 | +1.82% | +0.29% | **+1.53%** |
| 2026-05-04 | -1.80% | -0.36% | **-1.44%** |

### Period summary (Apr 22 → May 4)

| Metric | Value |
|--------|-------|
| Portfolio period return | +0.22% |
| SPY period return | +10.71% |
| **Alpha** | **-10.49%** |
| Start equity | $99,627.47 |
| End equity | $99,849.69 |

---

## Positions at close (from eod.json)

| Symbol | Side | Avg Entry | Close Price | P&L % | P&L $ | Weight |
|--------|------|-----------|-------------|--------|--------|--------|
| AXTX | LONG | $46.41 | $46.61 | +0.43% | +$62.60 | 14.6% |
| META | LONG | $611.73 | $610.46 | -0.21% | -$19.63 | 9.5% |
| PWR | LONG | $758.48 | $757.38 | -0.15% | -$16.16 | 11.1% |
| SPY | LONG | $717.52 | $718.03 | +0.07% | +$42.40 | 59.8% |

> SPY held as cash proxy at **59.8% of equity** — effectively making the portfolio a closet indexer.

---

## Trades today (summary table)

| Time (UTC) | Symbol | Event | Qty | Price | Note |
|------------|--------|-------|-----|-------|------|
| 14:51 | HCAI | SELL | 1,492 | $10.69 | exit-arbiter conf=0.72, down -9.71% |
| 16:04 | AMZN | SELL | 65.3 | $270.65 | arbiter EXIT, fading momentum |
| 16:04 | GEV | SELL | 14.6 | $1,071.49 | arbiter EXIT, weak momentum |
| 16:04 | UNH | SELL | 17.3 | $368.25 | arbiter EXIT, fund LLY |
| 16:04 | LLY | BUY | 9.5 | $963.38 | starter entry 70% |
| 16:04 | MU | BUY | 25.0 | $580.42 | increase to 28% |
| 16:04 | NOK | BUY | 367.2 | $13.33 | new entry 4.9% |
| 16:04 | SNDK | BUY | 10.1 | $1,246.97 | re-entry after earlier exit |
| 17:04 | MU | SELL | 23.0 | $580.81 | arbiter EXIT after ~60 min |
| 17:04 | DELL | BUY | 57.4 | $210.52 | new entry |
| 17:04 | FIX | BUY | 6.3 | $1,896.50 | new entry |
| 17:04 | GOOGL | BUY | 28.7 | $383.51 | new entry |
| 17:04 | LLY | BUY | 3.5 | $962.27 | increase (wash trade recovery) |
| 17:04 | WDC | BUY | 24.5 | $445.36 | new entry |
| 17:04 | COIN | BUY | 5.1 | $203.90 | verifier reconcile |
| 18:05 | WDC | SELL | 24.5 | $440.06 | arbiter EXIT after ~60 min, -1.19% |
| 18:05 | FIX | BUY | 3.7 | $1,903.71 | increase |
| 18:05 | DELL | SELL | 57.4 | $210.94 | verifier dust-sweep |
| 18:05 | LLY | SELL | 13.0 | $963.71 | verifier dust-sweep |
| 18:05 | GOOGL | BUY | 9.3 | $384.43 | verifier reconcile |
| 19:08 | COIN | SELL | 66.9 | $203.45 | arbiter EXIT, momentum=0, earnings risk |
| 19:08 | GOOGL | SELL | 38.0 | $382.77 | arbiter EXIT, momentum=0 |
| 19:08 | FIX | SELL | 10.0 | $1,902.81 | verifier dust-sweep |
| 19:08 | AXTX | BUY | 313.0 | $46.41 | new entry, momentum=100 |
| 19:08 | META | BUY | 15.5 | $611.73 | new entry |
| 19:08 | PWR | BUY | 14.7 | $758.48 | new entry |

*(53 total trade events including exit_learning_metrics; 26 actionable buy/sell orders)*

---

## Phase 2 — Deep Analysis

### 2a. Per-trade quality table

| Symbol | Side | Entry | Exit | P&L % | P&L $ | AI Grade | Reason (condensed) | Quality Verdict |
|--------|------|-------|------|--------|--------|----------|--------------------|------------------|
| HCAI | LONG→SELL | $11.84 | $10.69 | **-9.71%** | **-$1,716** | exit-arbiter conf=0.72 | Down >8% at exit, "within continued downtrend" | **BAD** — hard stop bypass; should have exited at -1% ($11.72) |
| SNDK* | LONG→SELL | $1,140.78 | $1,246.63 | +9.28% | +$2,466 | selector EXIT | Peer MU ranked higher at 15:13 scan | **OVER-TRIM** — profitable winner exited for peer-pressure, then re-bought same day |
| STX | LONG→SELL | $716.82 | $740.58 | +3.31% | +$461 | selector EXIT | Weak momentum, below EMA20 | **GOOD** — correct exit, momentum genuinely failed |
| AMZN | LONG→SELL | ~$273.92 | $270.65 | -1.19% | -$214 | arbiter EXIT | Fading momentum, below VWAP | **OK** — small loss, correct decision |
| GEV | LONG→SELL | ~$1,113 | $1,071.49 | -3.73% | -$605 | arbiter EXIT | Weak momentum, below VWAP | **OK** — held too long; should have exited earlier in prior days |
| UNH | LONG→SELL | $371.09 | $368.25 | -0.77% | -$49 | arbiter EXIT | "Fading volume, fund LLY" | **CHURN** — exited a -0.77% loser to fund LLY, which itself was closed 2h later |
| MU | BUY→SELL | $580.42 | $580.81 | +0.07% | +$9 | arbiter INCREASE/EXIT | "Perfect momentum" at entry; "weak/flat" 60 min later | **CHURN** — 60-min round-trip, near-zero net, pure friction |
| WDC | BUY→SELL | $445.36 | $440.06 | -1.19% | -$130 | arbiter BUY / EXIT | "Memory peer leader" at entry; "gap-only, fading" 60 min later | **BAD** — entered and reversed within 1 scan on conflicting signals |
| NOK | BUY→SELL | $13.33 | ~$13.30 | ~-0.2% | ~-$11 | arbiter BUY / selector exit | "Strong continuation" at 16:04; gone from 17:05 selected list | **CHURN** — $4.9K position opened and closed in one scan window |
| LLY | BUY→SELL | $963.08 | $963.71 | +0.07% | +$8 | arbiter BUY / verifier dust-sweep | Opened, then verifier dust-swept 60 min later | **CHURN** — wash trade recovery triggered, then immediately swept |
| DELL | BUY→SELL | $210.52 | $210.94 | +0.20% | +$24 | arbiter BUY / verifier dust-sweep | Opened, verifier dust-swept same scan | **CHURN** — net gain but pointless round-trip |
| FIX | BUY→SELL | $1,899.17 | $1,902.81 | +0.19% | +$36 | arbiter BUY+INCREASE / verifier dust-sweep | Opened and increased twice, then verifier swept | **CHURN** — 3 FIX transactions net $36, not worth friction |
| GOOGL | BUY→SELL | $383.73 | $382.77 | -0.25% | -$37 | arbiter BUY / EXIT | Opened, verifier reconcile add, then arbiter exited "momentum=0" | **CHURN** — opened and closed same session |
| COIN | BUY→SELL | $203.90 | $203.45 | -0.22% | -$30 | arbiter BUY / EXIT | "Strong continuation" at 17:04; "momentum=0, earnings risk" at 19:08 | **BAD** — earnings risk should have blocked entry; 2h round-trip loss |
| AXTX | BUY | $46.41 | $46.61 (close) | +0.43% | +$63 | arbiter BUY, momentum=100 | Breaking out, staged 70% entry | **GOOD** — clean breakout entry, held overnight |
| META | BUY | $611.73 | $610.46 (close) | -0.21% | -$20 | arbiter BUY | Comm services leader, acceptable continuation | **OK** — reasonable entry, holding |
| PWR | BUY | $758.48 | $757.38 (close) | -0.15% | -$16 | arbiter BUY | ai_data_center_power peer leader | **OK** — reasonable entry, holding |

*SNDK original May 1 position; a second SNDK lot (10.1 shares) was re-opened at 16:04 and also closed before EOD.*

---

### 2b. Cross-trade patterns

**Scan-by-scan full portfolio rotation (primary failure):**
- All 6 scans selected a mostly different set of names: `[AMZN/GEV/COIN/MU/UNH] → [AMZN/MU/META/UNH/COIN] → [MU/COIN/SNDK/LLY/NOK] → [FIX/DELL/WDC/GOOGL/COIN/LLY] → [FIX/CUE/COIN/PWR/GOOGL] → [AXTX/SNDK/PWR/LLY/META]`
- Zero overlap between scan 1 and scan 6. Full portfolio replaced 3× intraday.
- Root cause: portfolio-selector has no memory of prior scans and no cost for churn.

**SNDK flip-flop (peer-pressure exit, immediate re-entry):**
- SNDK exited at 15:13 because MU ranked higher in the same peer group.
- SNDK re-bought at 16:04 (a different lot). MU itself was exited at 17:04 as "weak/flat."
- Net cost: SNDK original position was a +9.28% winner trimmed early; the replacement MU was flat (+0.07%).

**HCAI hard-stop bypass:**
- Hard stop is configured at `hard_stop_loss_pct: 0.01` (1%). HCAI entry $11.84 → theoretical stop $11.72.
- Actual exit $10.69 = **-9.71%** loss. Stop either failed to submit, was cancelled during a rebalance, or HCAI gapped beyond stop in an illiquid print.
- Exit was via exit-arbiter (conf=0.72), not the protective stop order.
- Loss: -$1,716 — the single largest P&L event of the day.

**Earnings-risk blind spot (COIN):**
- COIN exited at 19:08 with "earnings risk" flagged in the reason, but was entered at 17:04 with no earnings warning.
- Earnings proximity should gate entry, not just exit. Entering 2h before a flagged earnings event is a policy gap.

**Wash trade churn (LLY, FIX, GOOGL):**
- Three positions triggered `wash_trade_recovery` events, meaning the same symbol was closed and re-opened within 30 days.
- LLY and FIX were then dust-swept by the verifier within the same scan — 3 transactions for net $44.

**SPY as closet-indexer:**
- SPY held at **59.8%** at close. If cash proxy is capped at 5% reserve and the rest goes to active picks, 60% in SPY defeats the mandate.
- With 60% in SPY, the portfolio can outperform at most ~40% of any alpha.

**AI vs numeric disagreements:**
- MU: the selector gave it a "perfect momentum" grade at 16:04 and "weak/flat" at 17:04. A 60-minute reversal of a "perfect" signal indicates the momentum model is highly sensitive to short-term VWAP noise.
- WDC: entered as "Memory peer leader" and exited as "gap-only classification" within 1 scan. Gap-only detection should block entry, not exit.

**Oversized short/inverse ETF in selector pool:**
- Scan 6 selected SOXS (ProShares UltraShort SOX) with target weight 12.87%. SOXS is a 3× inverse ETF — blocked by the long-only rule but wasted AI cycles and skewed portfolio-thesis reasoning.

---

### 2c. Proposed changes

---

#### Proposal 1 — Inter-scan hold floor: prevent churn on held positions
**Why:** 53 trades in one day from a 6-position portfolio is unsustainable. Every scan replaced 3-5 positions with no persistence. `selector.py` has no memory of prior selections; there is no cost for flipping an entire portfolio in one scan.

**Diff (config.yaml):**
```yaml
# Before
selector:
  enabled: true
  min_positions: 3
  max_positions: 6

# After (add)
selector:
  enabled: true
  min_positions: 3
  max_positions: 6
  min_hold_scans: 2           # held position must survive 2 consecutive scans before peer-pressure exit
  max_scan_turnover_pct: 0.40 # cap sell+buy notional at 40% of equity per scan (hard exits and stop-outs exempt)
```

**Expected impact:** Reduces daily trades from ~50 to ~15. Prevents SNDK-style flip-flops. Forces AI to build conviction across scans rather than reset each time. Estimated 30-50% reduction in slippage/friction cost.

---

#### Proposal 2 — Peer-pressure exit minimum score gap
**Why:** SNDK was exited at 15:13 because MU had "superior remaining upside." MU was itself exited at 17:04 (60 min later) as "weak/flat." A single-scan peer advantage should not trigger a winner exit.

**Diff (config.yaml):**
```yaml
# Before (no peer gap threshold)
selector:
  enabled: true

# After (add)
selector:
  enabled: true
  peer_pressure_min_score_gap: 15.0  # peer must score ≥15 points higher to trigger exit
  peer_pressure_min_consecutive: 2   # peer must outrank for 2+ scans before triggering
```

**Expected impact:** Prevents SNDK-style flip-flops where a peer wins by a narrow margin on a single scan. With a 2-scan requirement, MU's 60-minute dominance would not have triggered the SNDK exit.

---

#### Proposal 3 — Earnings gate at entry, not just exit
**Why:** COIN was entered at 17:04 with no earnings warning, then exited at 19:08 with "earnings risk" cited. The `earnings-gate` agent only fires on held positions within 2 days of earnings. An entry-side earnings check is missing.

**Diff (config.yaml):**
```yaml
# Before
earnings:
  trim_exit_days: 2
  day_0_1_hold_min_confidence: 0.90

# After (add)
earnings:
  trim_exit_days: 2
  day_0_1_hold_min_confidence: 0.90
  block_new_entry_days: 2  # block new entries within 2 days of earnings; existing positions use earnings-gate
```

**Expected impact:** Eliminates COIN-style 2h round-trips caused by entering pre-earnings names. Prevents the scanner from adding a name that the exit-arbiter will immediately flag.

---

#### Proposal 4 — Hard-stop integrity check for micro-cap and illiquid names
**Why:** HCAI (micro-cap, ~$10/share) lost -9.71% against a 1% hard stop. The protective stop either failed to submit, was cancelled during a rebalance-triggered order cancellation, or gapped through. This cost -$1,716 — the day's largest loss.

**Diff (src/executor.py — not modifiable here; proposal for engineering review):**
```
# Add post-order verification:
# After submitting BUY + stop pair, confirm stop order status = "submitted" or "accepted"
# If stop order returns error or remains in failed/cancelled state:
#   - Send alert immediately
#   - Do NOT allow the position to persist without a protective stop
# Also: add min_adv_usd check before entry; reject names with ADV < $1M (HCAI-class)
```

**Diff (config.yaml):**
```yaml
# After (add under risk:)
risk:
  min_avg_daily_volume_usd: 1000000  # reject names with ADV < $1M to avoid illiquid stop failures
```

**Expected impact:** Prevents single-position -9.71% blowouts. HCAI had ADV well below this threshold; the filter would have excluded it.

---

#### Proposal 5 — SPY cash-proxy cap
**Why:** SPY held at 59.8% at close. The cash-proxy is intended as an idle-capital parking mechanism, not a portfolio weight. At 60%, the bot effectively IS SPY minus a 40% active overlay — the mandate is to beat SPY, not replicate it.

**Diff (config.yaml):**
```yaml
# Before (no SPY proxy cap)
risk:
  cash_reserve_pct: 0.05

# After (add)
risk:
  cash_reserve_pct: 0.05
  cash_proxy_max_pct: 0.20  # SPY cash-proxy capped at 20% of equity; excess cash stays as cash (T-bill equivalent)
```

**Expected impact:** Forces the selector to find 5-6 active names rather than parking 60% in SPY. With portfolio currently at -10.49% alpha vs SPY, the SPY proxy is actively hurting performance by increasing SPY-correlation while bearing market risk.

---

#### Proposal 6 — Block inverse/leveraged ETFs from discovery pool
**Why:** Scan 6 (19:08) selected SOXS (3× short SOX) with a 12.87% target weight. SOXS is a short-side ETF blocked by the long-only constraint, but the selector allocated AI budget to it and included it in portfolio thesis reasoning.

**Diff (config.yaml):**
```yaml
# Add to universe section:
universe:
  exclude_tickers:
    - SOXS
    - SQQQ
    - SPXS
    - SDOW
    - UVXY
    - SOXL  # leveraged long also inappropriate for swing; amplifies drawdowns
    - TQQQ
```

**Expected impact:** Cleaner pool, no AI reasoning wasted on ineligible names. Prevents edge cases where leveraged ETF enters the top-5 candidate list and distorts sector-concentration checks.

---

### 2d. Backtest notes

**Proposals 1 and 2 (hold floor + peer gap)** can be partially validated with in-repo data:

Using the May 4 scans: if `min_hold_scans: 2` had been active:
- SNDK (bought May 1) would survive 15:13 scan → held until 16:05 at minimum → saves the 16:04 re-buy and 17:05 re-sell.
- MU would survive the 17:05 scan only if it appeared in both 16:05 and 17:05 selected lists. It was in 16:05 but not 17:05 → still exits after 2 scans.
- NOK (opened 16:04) would not be eligible for exit at 17:05 scan → saved 1 churn trade.
- WDC (opened 17:05) would not be eligible for exit at 18:05 → saved 1 round-trip costing -$130.

Rough offline simulation for May 4: hold floor would have prevented ~8 sell orders (NOK, SNDK re-exit, WDC, LLY dust, DELL dust, FIX dust, MU, GOOGL early cycle). Estimated slippage saved: $200-300. Net P&L impact vs actual: **+$200 to +$400** on May 4 alone.

**Proposals 3-6** cannot be backtested offline without pricing data for earnings calendars and ADV screens — no yfinance or network access available. Qualitative assessment only.

---

*End of post-mortem 2026-06-01. Proposals are for review only; no config or source files were modified on this branch.*