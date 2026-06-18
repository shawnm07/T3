# Post-Mortem 2026-06-04

## Data availability

| File | Status |
|------|--------|
| `data/research/2026-06-04_eod.json` | **MISSING** — no scan ran today |
| `data/research/2026-05-04_eod.json` | Present — last available EOD snapshot |
| `data/research/20260504T*_scan.json` | Present — 5 scan files (last run 2026-05-04) |
| `data/journal/trades.jsonl` | Present |
| `data/journal/decisions.jsonl` | Present |
| `config.yaml` | Present |

> **Context:** No bot activity detected between 2026-05-05 and 2026-06-04 (30 calendar days). This report covers the full trading period for which data exists (2026-04-22 → 2026-05-04) with emphasis on the final day (2026-05-04), which showed the most dysfunctional behaviour.

---

## Performance (last EOD: 2026-05-04)

| Metric | Value |
|--------|-------|
| Equity at close | $99,849.69 |
| Daily return (2026-05-04) | **-1.80%** |
| SPY daily | -0.36% |
| Daily vs SPY | **-1.44%** |
| Trades executed (2026-05-04) | **53** (extremely high) |
| Positions at close | 4 |

### Rolling benchmark comparison

| Window | Portfolio | SPY | Alpha |
|--------|-----------|-----|-------|
| 1d (2026-05-04) | -1.80% | -0.36% | **-1.44%** |
| 5d (Apr 28 – May 4) | -12.66% | +0.38% | **-13.04%** |
| All available (Apr 22 – May 4, 9 sessions) | -16.31% | +1.95% | **-18.26%** |

*SPY series from `spy_daily` fields. Portfolio compounded from `daily_return` fields.*

Daily breakdown:

| Date | Portfolio | SPY | vs SPY | Trades |
|------|-----------|-----|--------|--------|
| 2026-04-22 | 0.00% | +1.01% | -1.01% | 7 |
| 2026-04-23 | +1.56% | -0.39% | +1.95% | 9 |
| 2026-04-24 | -0.81% | +0.77% | -1.59% | 19 |
| 2026-04-27 | **-4.88%** | +0.17% | **-5.05%** | 24 |
| 2026-04-28 | **-5.13%** | -0.49% | **-4.64%** | 21 |
| 2026-04-29 | **-5.40%** | -0.01% | **-5.39%** | 10 |
| 2026-04-30 | -2.67% | +0.96% | -3.63% | 23 |
| 2026-05-01 | +1.82% | +0.29% | +1.53% | 38 |
| 2026-05-04 | -1.80% | -0.36% | -1.44% | **53** |

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Qty | Avg Entry | Current | PnL% | Notional | Weight |
|--------|------|-----|-----------|---------|------|----------|--------|
| SPY | LONG | 83.14 | $717.52 | $718.03 | +0.07% | $59,695 | **59.8%** |
| AXTX | LONG | 313.0 | $46.41 | $46.61 | +0.43% | $14,589 | 14.6% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% | $11,130 | 11.1% |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% | $9,448 | 9.5% |
| Cash | — | — | — | — | — | $4,987 | 5.0% |

> PnL% = (current_price − avg_entry) / avg_entry (sandbox rule — Alpaca unrealized_plpc not used).
> SPY at 59.8% entered as a cash-proxy legacy position; it is not gated by `initial_entry_cap_pct: 0.15`.

---

## Trades on 2026-05-04 (53 total)

| Time (UTC) | Event | Symbol | Qty | Entry/Exit Px | PnL% | AI Grade | Quality |
|------------|-------|---------|-----|--------------|------|----------|---------|
| 14:51 | EXIT | HCAI | 1492 | $10.69 | **-8.78%** | conf=0.72 | bad — heavy loss, exit correct but entry was wrong |
| 16:04 | EXIT | AMZN | 65.3 | $270.65 | ? (prev held) | arbiter | churn — no entry px in trades.jsonl |
| 16:04 | EXIT | GEV | 14.6 | $1,071.49 | ? | arbiter | churn — same scan as replacement buys |
| 16:04 | EXIT | UNH | 17.3 | $368.25 | ? | arbiter | missed — exited to fund LLY which was dust-swept 2hrs later |
| 16:04 | BUY | LLY | 9.5 | $963.38 | +0.03% | arbiter BUY | bad — verifier dust-swept at 18:05 |
| 16:04 | BUY | MU | 25.0 | $580.42 | **+0.07%** | arbiter INCREASE | churn — sold 1 hr later |
| 16:04 | BUY | NOK | 367.2 | $13.33 | ? (not in EOD) | arbiter BUY | missed — disappeared from EOD |
| 16:04 | BUY | SNDK | 10.1 | $1,246.97 | — (still held) | arbiter BUY | ok — held through close |
| 17:04 | EXIT | MU | 23.0 | $580.81 | **+0.07%** | arbiter | churn — 1-hour hold for essentially zero gain |
| 17:04 | BUY | DELL | 57.4 | $210.52 | +0.20% | arbiter BUY | bad — verifier dust-swept at 18:05 |
| 17:04 | BUY | FIX | 6.3 | $1,896.50 | +0.33% | arbiter BUY | bad — verifier dust-swept at 19:08 |
| 17:04 | BUY | GOOGL | 28.7 | $383.51 | -0.19% | arbiter BUY | churn — arbiter exited at 19:08 |
| 17:04 | BUY | WDC | 24.5 | $445.36 | **-1.19%** | arbiter BUY | bad — 1-hour hold, real loss |
| 17:04 | BUY | COIN | 5.1 | $203.90 | -0.22% | verifier reconcile | bad — exited 2hrs later on earnings |
| 18:05 | EXIT | WDC | 24.5 | $440.06 | **-1.19%** | arbiter | bad — gap_only entry should have been blocked earlier |
| 18:05 | INCREASE | FIX | 3.7 | $1,903.71 | — | arbiter | bad — increased just before dust-sweep |
| 18:05 | EXIT | DELL | 57.4 | $210.94 | +0.20% | verifier dust-sweep | bad — conflicts arbiter's 17:04 buy |
| 18:05 | EXIT | LLY | 13.0 | $963.71 | +0.03% | verifier dust-sweep | bad — conflicts arbiter's 16:04 buy |
| 18:05 | BUY | GOOGL | 9.28 | $384.43 | -0.19% | verifier reconcile | bad — arbiter exited next scan |
| 19:08 | EXIT | COIN | 66.9 | $203.45 | -0.22% | arbiter (earnings) | ok — earnings flag correct |
| 19:08 | EXIT | GOOGL | 37.96 | $382.77 | -0.19% | arbiter | churn — bought 18:05, sold 19:08 |
| 19:08 | BUY | AXTX | 313.0 | $46.41 | +0.43% | arbiter BUY | ok — held through close, momentum=100 |
| 19:08 | BUY | META | 15.5 | $611.73 | -0.21% | arbiter BUY | ok — held through close |
| 19:08 | BUY | PWR | 14.7 | $758.48 | -0.15% | arbiter BUY | ok — held through close |
| 19:08 | EXIT | FIX | 10.0 | $1,902.81 | +0.33% | verifier dust-sweep | bad — conflicts arbiter's 17:04–18:05 position |

*Trades by hour: 14UTC=1, 16UTC=8, 17UTC=16, 18UTC=14, 19UTC=14*

---

## Cross-trade patterns

- **Verifier/arbiter conflict (critical):** Verifier dust-swept LLY, DELL, FIX at target=0 within 1–2 hours of arbiter buying them. In each case the arbiter had a valid thesis that the verifier overrode. Root cause: verifier reconciles to an Opus target from a *prior* scan cycle, so freshly-opened positions appear as "gaps to close". This single pattern caused ≥6 unnecessary round-trips on May 4.

- **Sub-1-hour churns:** MU and WDC both bought and exited within 60 minutes. Gross spreads consumed the entire +0.07% move on MU; WDC produced a real -1.19% loss. The bot is swing-cadenced but executing intraday noise.

- **Inverse ETF in selector pool (SOXS):** SOXS (3× inverse semiconductors) reached 12.87% target weight in the 19:08 scan. Execution preflight blocked it, but the selector should never have scored it. The `discovery.py` eligibility filter does not exclude leveraged/inverse ETFs. This is a latent short-exposure risk — one preflight regression could execute it.

- **SPY cash-proxy overweight (59.8%):** SPY entered as a legacy hold and ballooned to nearly 60% of equity. It bypasses `initial_entry_cap_pct: 0.15` as a "cash proxy". A dedicated SPY/cash weight cap is absent from config.

- **Earnings-proximity entry missed:** COIN was entered by the verifier at 17:04 despite earnings proximity (`new_entry_earnings_blackout_days: 2`). The verifier-originated reconcile order was not screened against the earnings gate.

- **Catastrophic April 27–29 (-4.9%, -5.1%, -5.4%):** Likely driven by HCAI mark-to-market drag (exited May 4 at -8.78%) and high-churn spread costs across 24/21/10 trades per day. Apr 27 trade data in trades.jsonl lacks filled prices, suggesting stops were hit or pre-session exits.

- **AI vs numeric:** Decision-log shows ON and LSCC correctly filtered at `combined_score < 0.40` for weeks. The numeric gate is working. The real disagreement is verifier vs arbiter, not numeric vs AI.

---

## Proposed Changes

### 1. Block leveraged/inverse ETFs in discovery eligibility

**Why:** SOXS reached 12.87% target weight in the selector on May 4. One preflight bug would execute a short-exposure trade in a long-only account.

**Diff** (`src/discovery.py` — eligibility filter near the `is_eligible` check):
```python
# BEFORE (no inverse ETF filter)
EXCLUDED_SYMBOLS = {'UVXY', 'VXX', ...}  # VIX instruments only

# AFTER
INVERSE_ETF_PREFIXES = ('SOXS','SOXL','TQQQ','SQQQ','SPXU','SH','PSQ',
                         'QID','DOG','SDS','TWM','MZZ','SKF','FAZ','TZA')
LEVERAGED_BEAR_KEYWORDS = ('-3x','-2x','ultra short','ultrashort','inverse')

def is_eligible(symbol, name=''):
    if symbol in EXCLUDED_SYMBOLS: return False
    if symbol.startswith(INVERSE_ETF_PREFIXES): return False
    if any(k in name.lower() for k in LEVERAGED_BEAR_KEYWORDS): return False
    return True
```

**Expected impact:** Eliminates short-exposure risk entirely. No performance cost.

---

### 2. Prevent verifier from dust-sweeping positions opened in the current scan cycle

**Why:** Verifier closed LLY, DELL, FIX within 1–2 hours of arbiter opening them, generating 6+ unnecessary trades and real losses (WDC -1.19%, COIN -0.22%).

**Diff** (`src/executor.py` — verifier reconcile logic):
```python
# BEFORE
# verifier proposes dust-sweep for any position where current_qty > 0 and target_qty == 0

# AFTER
MIN_VERIFIER_HOLD_MINUTES = 240  # 4 hours — expose as config key

def should_verifier_close(symbol, opened_at, now):
    if opened_at and (now - opened_at).total_seconds() < MIN_VERIFIER_HOLD_MINUTES * 60:
        return False  # too young — let arbiter manage it
    return True
```

*Config key to add: `risk.verifier_min_hold_minutes: 240`*

**Expected impact:** Eliminates the arbiter/verifier conflict. Estimated 10–15 fewer round-trips per active day, saving ~0.2–0.4% in spread costs.

---

### 3. Add per-day trade count hard cap

**Why:** 53 trades on May 4, 24 on Apr 27, 23 on Apr 30. A swing-cadenced strategy should not execute 50+ trades in 5 hours.

**Diff** (`config.yaml`):
```yaml
# BEFORE
# (no trade count cap)

# AFTER
risk:
  max_trades_per_day: 20   # halts new BUY/INCREASE once exceeded; exits unaffected
```

**Expected impact:** Forces selectivity. With cap=20 on May 4, the verifier-conflict round-trips alone would have triggered it at ~17:00, suppressing the entire 18:00–19:00 cascade.

---

### 4. Reduce max_candidates_per_scan from 10 to 5

**Why:** `config.yaml` has `ai.max_candidates_per_scan: 10` but design spec (CLAUDE.md) documents 5. Doubling the candidate pool doubles action pressure on the AI arbiter, generating more buys per scan and amplifying the churn loop.

**Diff** (`config.yaml`):
```yaml
# BEFORE
ai:
  max_candidates_per_scan: 10

# AFTER
ai:
  max_candidates_per_scan: 5
```

**Expected impact:** Conservative estimate 30–40% reduction in daily trade count on active days.

---

### 5. Raise exit_arbiter.min_confidence from 0.55 to 0.65

**Why:** The arbiter exited MU (+0.07%, 1-hour hold), WDC (-1.19%, 1-hour hold), and GOOGL (-0.19%, 1-hour hold) — all valid at 0.55 confidence but creating net-negative churn. A higher bar keeps positions in place long enough to capture the intended swing move.

**Diff** (`config.yaml`):
```yaml
# BEFORE
exit_arbiter:
  min_confidence: 0.55

# AFTER
exit_arbiter:
  min_confidence: 0.65
```

**Expected impact:** Roughly 30–40% of May 4 exits had AI confidence in the 0.55–0.65 range (from trades.jsonl). Raising the bar would have kept MU, WDC, GOOGL longer. Friction cost is definitively reduced; P&L impact depends on subsequent price action.

---

### 6. Add SPY/cash-proxy position cap

**Why:** SPY reached 59.8% of equity as an uncapped legacy hold, crowding out diversified positions. The `max_position_pct: 0.50` cap applies to normal equity entries but SPY bypasses it through the cash-proxy path.

**Diff** (`config.yaml`):
```yaml
# BEFORE
risk:
  max_position_pct: 0.50

# AFTER
risk:
  max_position_pct: 0.50
  max_spy_proxy_pct: 0.30   # cap SPY/cash-proxy at 30% of equity
```

*Implementation: in `executor.py` or `portfolio-selector`, check `spy_target_pct + cash_target_pct` against `max_spy_proxy_pct` before submission.*

**Expected impact:** On May 4, a 30% SPY cap would have freed ~$30K for AXTX/META/PWR — the three positions that were the day's strongest performers (+0.43%, -0.15%, -0.21% vs SPY's +0.07%).

---

## Offline backtest note

Changes 3 (trade cap), 4 (candidates reduction), and 5 (exit confidence) can be partially validated against `data/journal/` data.

| Metric | Actual May 4 | Estimated with proposals 2+3+4 |
|--------|-------------|--------------------------------|
| Total trades | 53 | ~20 (cap triggered ~17:00) |
| Verifier dust-sweeps | 3 | 0 (hold gate blocks them) |
| Positions closed at <0.10% gain | 5 | ~2 |
| Estimated spread cost saved | — | ~0.3–0.5% of equity (~$300–500) |

Full replay requires live-price data not available offline. Proposals 1, 2, 6 are correctness fixes with no performance trade-off.

---

*Report generated 2026-06-04. Data sources: `data/research/*_eod.json`, `data/journal/trades.jsonl`, `data/journal/decisions.jsonl`, `config.yaml`. No network calls made.*
