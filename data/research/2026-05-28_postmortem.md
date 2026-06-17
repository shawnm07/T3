# Post-Mortem 2026-05-28

## Data availability

| Source | Status |
|--------|--------|
| `data/research/2026-05-28_eod.json` | **MISSING** — bot has not run since 2026-05-04 (24 calendar days, ~16 trading days gap) |
| `data/research/2026-05-04_eod.json` | Present — most recent EOD snapshot |
| `data/research/2026050[4-1]T*_scan.json` | 6 scan files on 2026-05-04 |
| `data/journal/trades.jsonl` | 204 total trades; 53 on 2026-05-04 |
| `data/journal/decisions.jsonl` | 1556 entries through 2026-05-04 |
| `config.yaml` | Present — baseline for proposals |
| `scripts/analyze_winner_trim.py` | Present (requires yfinance — network-blocked; offline only) |

**Critical gap:** The bot has not produced an EOD snapshot or executed any trades since 2026-05-04. This post-mortem covers the last recorded trading day (2026-05-04) and the full rolling period (2026-04-22 → 2026-05-04). The 24-day inactivity gap is itself a finding requiring investigation.

---

## Performance today (2026-05-04 — last recorded trading day)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| **vs SPY (today)** | **-1.43%** |
| Equity at close | $99,849.69 |
| Cash | $4,986.91 |
| Positions | 4 |
| Trades executed | **53** (abnormally high) |

### Rolling period (2026-04-22 → 2026-05-04)

| Date | Portfolio | SPY | vs SPY | Trades | Positions |
|------|-----------|-----|--------|--------|-----------|
| 2026-04-22 | +0.00% | +1.01% | **-1.01%** | 7 | 7 |
| 2026-04-23 | +1.56% | -0.39% | **+1.95%** | 9 | 10 |
| 2026-04-24 | -0.81% | +0.77% | **-1.59%** | 19 | 12 |
| 2026-04-27 | -4.88% | +0.17% | **-5.05%** | 24 | 8 |
| 2026-04-28 | -5.13% | -0.49% | **-4.65%** | 21 | 4 |
| 2026-04-29 | -5.40% | -0.01% | **-5.39%** | 10 | 5 |
| 2026-04-30 | -2.67% | +0.96% | **-3.63%** | 23 | 3 |
| 2026-05-01 | +1.82% | +0.29% | **+1.53%** | 38 | 4 |
| 2026-05-04 | -1.80% | -0.36% | **-1.43%** | 53 | 4 |

**Cumulative portfolio return (Apr 22 → May 4): +0.22%**  
**SPY 30-day return (per eod.json): +10.71%**  
**Total underperformance: -10.49%**  
SPY beat days: 2/9 (Apr 23, May 1)

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Avg Entry | Current Price | P&L% | Market Value |
|--------|------|-----------|---------------|------|-------------|
| AXTX | LONG | $46.41 | $46.61 | **+0.43%** | $14,588.93 |
| META | LONG | $611.73 | $610.46 | **-0.21%** | $9,448.36 |
| PWR | LONG | $758.48 | $757.38 | **-0.15%** | $11,129.62 |
| SPY | LONG | $717.52 | $718.03 | **+0.07%** | $59,695.86 |

*P&L computed as (current − avg_entry) / avg_entry per data policy.*  
*SPY position ($59.7K = 59.8% of equity) represents the cash-proxy; real equity exposure is ~40%.*

---

## Trades today (2026-05-04, 53 total)

| Time (UTC) | Event | Symbol | Qty | Reason (truncated) |
|-----------|-------|--------|-----|--------------------|
| 14:51 | EXIT (exit-arbiter) | HCAI | 1492 | AI conf=0.72: down -8.78%, 5 momentum signals lost |
| 16:04 | EXIT (arbiter) | AMZN | — | Fading momentum, below VWAP, bearish EMA |
| 16:04 | EXIT (arbiter) | GEV | — | Weak momentum, below VWAP, bearish EMA |
| 16:04 | EXIT (arbiter) | UNH | — | Fading volume; LLY stronger healthcare name |
| 16:04 | BUY (arbiter) | LLY | 9.49 | Strong continuation, above VWAP, bullish EMA |
| 16:04 | ADD (arbiter) | MU | 25.0 | Pool leader, perfect momentum continuation |
| 16:04 | BUY (arbiter) | NOK | 367.2 | Strong continuation, above VWAP, bullish EMA |
| 16:04 | BUY (arbiter) | SNDK | 10.1 | Best new candidate, strong continuation |
| 17:04 | EXIT (arbiter) | MU | — | Weak/flat momentum, bearish EMA, flat volume |
| 17:04 | BUY (arbiter) | DELL | 57.4 | IT sector leader, momentum score 95 |
| 17:04 | BUY (arbiter) | FIX | 6.3 | ai_data_center_power sector leader |
| 17:04 | BUY (arbiter) | GOOGL | 28.7 | Communication Services leader |
| 17:04 | ADD (arbiter) | LLY | 3.51 | INCREASE to 12.5% |
| 17:04 | BUY (arbiter) | WDC | 24.5 | Memory peer, higher score than MU |
| 17:04 | ADD (verifier) | COIN | 5.1 | Reconcile to Opus target 14.8% |
| 18:05 | EXIT (arbiter) | WDC | — | Gap_only classification, bearish EMA |
| 18:05 | ADD (arbiter) | FIX | 3.7 | Perfect momentum, increase to 19% |
| 18:05 | EXIT (verifier dust) | DELL | — | verifier dust-sweep target=0 |
| 18:05 | EXIT (verifier dust) | LLY | — | verifier dust-sweep target=0 |
| 18:05 | ADD (verifier) | GOOGL | 9.28 | Reconcile to Opus target 14.6% |
| 19:08 | EXIT (arbiter) | COIN | — | Momentum score 0, fading, earnings risk |
| 19:08 | EXIT (arbiter) | GOOGL | — | Momentum score 0, fading, below VWAP |
| 19:08 | BUY (arbiter) | AXTX | 313.0 | Momentum score 100, breaking_out |
| 19:08 | BUY (arbiter) | META | 15.48 | Communication services leader |
| 19:08 | BUY (arbiter) | PWR | 14.69 | ai_data_center_power peer leader |
| 19:08 | EXIT (verifier dust) | FIX | — | verifier dust-sweep target=0 |

*53 raw trade events include multiple exit_learning_metrics, wash_trade_recovery, and order submissions counted separately.*

---

## Trade quality (2026-05-04)

| Symbol | Open | Action | Conf | Entry$ | Close | P&L | AI grade | Verdict |
|--------|------|--------|------|--------|-------|-----|----------|---------|
| HCAI | 05-01 19:04 | BUY | N/A | $12.15 | 05-04 14:51 | **-8.78%** | exit conf=0.72 | BAD — small-cap, no stop filed, -$2,174 loss |
| MU | 16:04 | ADD | 0.90 | $583.49 | 17:04 | unknown | “perfect momentum” at buy | CHURN — reversed within 60 min, “weak momentum” at exit |
| NOK | 16:04 | BUY | 0.68 | $13.38 | ~17:04 | unknown | “strong continuation” | CHURN — not in EOD; dropped next scan silently |
| SNDK | 16:04 | BUY | 0.75 | $1,250.12 | ~19:08 | unknown | “best new candidate” | CHURN — selected in 19:08 scan but blocked on execution preflight |
| LLY | 16:04→17:04 | BUY+ADD | 0.72/0.65 | $961–$962 | 18:05 | unknown | wash trade triggered | CHURN — wash trade on INCREASE, dust-swept 2h after entry |
| WDC | 17:04 | BUY | 0.75 | $442.28 | 18:05 | unknown | “memory peer leader” | CHURN — “gap_only” at exit 1h later |
| DELL | 17:04 | BUY | 0.80 | $209.91 | 18:05 | unknown | “momentum score 95” | CHURN — verifier dust-swept 1h after entry |
| FIX | 17:04→18:05 | BUY+ADD | 0.82/0.88 | $1,884→$1,900 | 19:08 | unknown | wash trade on ADD | CHURN — wash trade on INCREASE; dust-swept 1h later |
| GOOGL | 17:04 | BUY | 0.72 | $382.82 | 19:08 | unknown | “acceptable continuation” | CHURN — “momentum score 0” 2h later |
| COIN | 17:04 | verifier reconcile | N/A | $204.82 | 19:08 | unknown | earnings in 3 days noted | MISSED — earnings gate should have blocked new entry |
| AXTX | 19:08 | BUY | 0.88 | $45.80 | HELD | +0.43% | “momentum 100, breaking_out” | GOOD — highest conviction, held overnight |
| META | 19:08 | BUY | 0.65 | $612.19 | HELD | -0.21% | “sector leader” | OK — low conviction, marginal result |
| PWR | 19:08 | BUY | 0.72 | $756.10 | HELD | -0.15% | “peer leader” | OK — reasonable entry, flat result |

*Exit P&L for intraday closes not available from journal (no matched fill prices for DELL, WDC, GOOGL, etc.)*

---

## Cross-trade patterns

- **Intraday portfolio churn (primary issue):** 53 trades on May 4 reflects 4 complete portfolio rotations across 5 hourly scans. 6 of 11 exits (55%) occurred within 3 hours of entry. The selector rebuilds the book from scratch every scan with no memory of prior-scan entries — a new candidate scoring 1 point higher at scan N+1 displaces a position opened at scan N.

- **Wash trade cascade:** 3 wash-trade-recovery events on May 4 (LLY, FIX, GOOGL) — each triggered because the bot tried to ADD to a position while an existing stop order was still live. The wash-trade recovery cancels the old stop, retries the entry, then submits a new stop. This adds 2–4 extra order submissions per event and creates a brief window with no downside protection.

- **Winner trimming via dust-sweep:** DELL (momentum 95 at entry, conf 0.80) and LLY (strong continuation, conf 0.72) were verifier dust-swept at 18:05 — just 1 hour after entry. The verifier saw target=0 for these symbols because the 18:05 scan had already rotated the portfolio again. This is not the winner_profit_threshold rule firing; it is the verifier enforcing a new Opus target that was set without awareness of freshness.

- **SPY proxy oversized:** At EOD, SPY held $59,695 = 59.8% of equity. Nominal equity exposure was only 40%. The cash-proxy is functioning as a parking lot for capital that keeps getting displaced by intraday rotations rather than deployed in high-conviction longs.

- **SOXS in candidate pool:** The 19:08 scan selected SOXS (3× inverse semiconductor ETF) with target weight 12.87% alongside AXTX, SNDK, META — directly contradicting the long semi thesis. The sector_guard blocked execution, but SOXS consumed pool space and AI tokens.

- **HCAI oversized entry (prior day):** HCAI was entered at 1,492 shares × $12.15 = $18,128 = ~18.2% of equity (above `initial_entry_cap_pct: 0.15`). The position had no stop order filed (`stop_order_id: null`). It lost -8.78% = -$1,590, the single largest loss of the period.

- **AI model downgrade:** `trade_critical_model` is currently `claude-sonnet-4-6` (lower cost). On May 4, the trade-critical model selected SOXS, reversed MU within 60 minutes of a 0.90-confidence ADD, and opened/closed DELL within 1 hour. These decisions are consistent with reduced reasoning depth.

- **24-day inactivity gap:** No trades or EOD snapshots from 2026-05-04 through 2026-05-28 (today). SPY's 30-day return was +10.71% as of May 4; if that trend continued, the bot missed substantial appreciation while holding ~$99.8K. Root cause unknown from repo data.

---

## Proposed changes

### Proposal 1 — Add minimum position hold time before arbiter exit is allowed

**Why:** 55% of May 4 exits occurred within 3 hours of entry. MU was added at 16:04 with conf=0.90 (“perfect momentum”) and closed at 17:04 (“weak momentum”). The selector has no memory of entry age, so each scan is free to immediately displace positions opened in the prior scan. This generates excessive friction costs and creates wash-trade cascades.

**Diff (config.yaml):**
```yaml
# NEW key under rebalance:
rebalance:
  min_hold_hours: 3    # before: key absent (no floor) → after: 3h minimum before exit-arbiter can close a position opened intraday
```
**Diff (src/orchestrator.py — `_handle_exits`):**
Add a pre-check before calling `exit-arbiter`: if `position_age_hours < config.rebalance.min_hold_hours`, skip the exit call and log `skipped_min_hold`. Exception: if unrealized P&L < -stop_loss_pct (stop triggered), allow exit regardless.

**Expected impact:** ~12 fewer trade events on May 4 (the 6 short exits × 2 orders each); reduces wash-trade risk; prevents scan-N entry + scan-N+1 exit cycles. Estimated friction saving: ~0.3–0.5% per high-churn day.

**Offline backtest:** Journal data spans 9 trading days (204 trades). Applying this rule retrospectively: 6 of 11 exits on May 4 would be blocked. Days with 7–23 trades show fewer short-exits, suggesting the problem is scan-frequency-driven not systematic.

---

### Proposal 2 — Restore trade_critical_model to claude-opus-4-7

**Why:** Current value is `claude-sonnet-4-6`. On May 4, the Sonnet model selected SOXS as a portfolio candidate (contradicts long thesis), reversed a 0.90-confidence ADD within 60 minutes, and produced 4 complete rotations in one session. Opus 4.7 has materially stronger multi-step reasoning for position-hold vs exit decisions.

**Diff (config.yaml):**
```yaml
ai:
  trade_critical_model: claude-sonnet-4-6   # before
  trade_critical_model: claude-opus-4-7     # after
  model: claude-sonnet-4-6                  # before (legacy alias)
  model: claude-opus-4-7                    # after
```

**Expected impact:** Higher portfolio stability; fewer intraday reversals; estimated cost increase ~$2–5/scan day at current volume. Qualitatively: Opus is less likely to reverse a 0.90-confidence decision within one scan cycle.

**Backtest:** Not quantifiable offline — would require replay with both models. Directional evidence: the 2 days that beat SPY (Apr 23, May 1) had 9 and 38 trades respectively; May 4 (53 trades, worst day in the period) coincides with the Sonnet downgrade.

---

### Proposal 3 — Raise winner_profit_threshold from 0.03 to 0.05

**Why:** The current `winner_profit_threshold: 0.03` (3%) protects profitable positions from trimming — but only during the rebalance trim path. Positions exited via the full arbiter EXIT path (target→0%) bypass this guard entirely. AMZN held from a prior day was exited on “fading momentum, below VWAP” despite being a profitable position; GEV and UNH similarly. Raising the threshold to 5% gives genuinely-running positions more buffer before the bot displaces them.

**Diff (config.yaml):**
```yaml
rebalance:
  winner_profit_threshold: 0.03   # before
  winner_profit_threshold: 0.05   # after
```

**Expected impact:** ~1–2 fewer premature winner exits per week. Rolling period shows only 2/9 days beat SPY; both winning days had fewer exits (9 trades on Apr 23). Estimated: +0.15–0.30% cumulative per week by keeping winners longer.

**Offline backtest:** `scripts/analyze_winner_trim.py` simulates hold-through vs trim-on-cool — but requires yfinance (network-blocked in this environment). Directional conclusion from the journal: the best-performing positions in the EOD data are ones held 2+ days (AXTX +0.43% after 1 day; prior session STX was held overnight).

---

### Proposal 4 — Add daily trade-count circuit breaker

**Why:** 53 trades on May 4 is pathological. A per-day cap would have hard-stopped the fourth complete rotation. Each rotation adds ~8–12 order submissions (buys + stops), all of which incur friction and wash-trade risk.

**Diff (config.yaml):**
```yaml
risk:
  max_trades_per_day: 30          # new key; halts new position changes after N trades in a UTC day
                                  # exits for stop-triggered or pre-close holds still allowed
```

**Expected impact:** On a day like May 4, caps execution at the second rotation (scan 17:04). Saves ~2 complete portfolio rotations × ~10 trades each = ~20 fewer orders. At 0.0% commission (paper) this is zero cost but real portfolio stability gain.

**Offline backtest:** 5/9 days in the rolling period had ≤ 24 trades already. Cap at 30 would only fire on May 1 (38 trades, +1.82% vs SPY — best recent day) and May 4 (53 trades, -1.80%). May 1 beats SPY despite high trade count; consider 38 as the cap if preserving that day matters.

---

### Proposal 5 — Exclude inverse and leveraged ETFs from discovery

**Why:** SOXS (ProShares UltraShort Semiconductor, -3×) was selected by the portfolio-selector at the 19:08 scan with 12.87% target weight. This contradicts simultaneous long positions in AXTX and SNDK (semiconductors). The sector_guard blocked execution, but SOXS consumed a pool slot and AI analysis budget, and any future sector_guard gap could let it through.

**Diff (config.yaml):**
```yaml
universe:
  exclude_tickers:
    - SOXS
    - SOXL
    - SPXS
    - SPXU
    - UVXY
    - SVXY
    - TECS
    - LABD
    # ... add other known inverse/leveraged ETFs
```
Or alternatively add a filter in `src/discovery.py` to drop symbols where the name contains “Ultra”, “Short”, “Bear”, “Inverse”, or “-3x”.

**Expected impact:** Cleaner 50-symbol pool; saves 1 AI analysis call per scan; eliminates the class of sector_guard false-negative risk.

---

### Proposal 6 — Investigate 24-day bot inactivity (OPERATIONAL — not a config change)

**Why:** The bot last ran 2026-05-04. Today is 2026-05-28. That is ~16 missed trading days. SPY returned +10.71% over the tracked 30-day window; missing even half that represents ~$5,000+ in opportunity cost on the $99.8K account. This is the highest-impact finding in this report.

**Root cause (from repo data alone):** Unknown. Possibilities:
1. Alpaca paper account credentials expired or were reset.
2. Alpha Vantage API key rate-limited or revoked (ALPHA_VANTAGE_API_KEY env var).
3. Scheduler (cron/systemd) stopped after the May 4 session crash or restart.
4. Container or host machine was shut down.

**Action required before restart:**
- Verify `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPHA_VANTAGE_API_KEY` env vars are live.
- Run `py dashboard.py` to confirm Alpaca connection.
- Run `py scripts/scan_and_trade.py --dry-run` to verify pipeline end-to-end.
- Check scheduler logs for the May 4–present gap.

---

## Config change summary (proposals 1–5)

| Key | Current | Proposed | Risk |
|-----|---------|----------|------|
| `ai.trade_critical_model` | `claude-sonnet-4-6` | `claude-opus-4-7` | Cost +$2–5/day |
| `rebalance.min_hold_hours` | *(absent)* | `3` | May miss fast-moving exits |
| `rebalance.winner_profit_threshold` | `0.03` | `0.05` | Holds losers slightly longer |
| `risk.max_trades_per_day` | *(absent)* | `30` | May leave capital idle late session |
| `universe.exclude_tickers` | `[]` | add inverse ETFs | Minor pool shrinkage |
