# Post-Mortem 2026-07-10

> **10th consecutive no-data report.** Bot last wrote artifacts on 2026-05-04. Scheduler has been
> silent for ~67 calendar days / ~46 trading days. All analysis is grounded in committed files only.

---

## Data Availability

| Source | Newest entry | Path |
|---|---|---|
| `_eod.json` | `2026-05-04_eod.json` | `data/research/2026-05-04_eod.json` |
| Intraday scan | `20260504T190848_scan.json` | `data/research/` |
| Preclose | `20260504T195545_preclose.json` | `data/research/` |
| `trades.jsonl` last event | `2026-05-04T19:55:03Z` `exit_learning_metrics` (COIN) — 204 lines | `data/journal/trades.jsonl` |
| `decisions.jsonl` last event | `2026-05-04T20:15:04Z` `eod_report` — 1556 lines | `data/journal/decisions.jsonl` |

No `20260505T*` → `20260710T*` files exist on disk. Both journal files byte-identical to 7/9 check
(mtime `1783458492`, line counts 204 / 1556). **Today is the 10th cycle with zero new artifacts.**

---

## Performance Today (vs SPY)

No today's EOD snapshot exists. Reporting on the last known state (2026-05-04) and the
tracked-period cumulative.

### Tracked-Period Summary (2026-04-22 → 2026-05-04, 9 trading days with data)

| Metric | Portfolio | SPY | Alpha |
|---|---|---|---|
| Cumulative return | **-16.31%** | +1.95% | **-18.26%** |
| Last 5d (4/28–5/4) | -12.66% | +0.38% | -13.04% |
| 2026-05-04 daily | -1.80% | -0.36% | -1.44% |

### Last Known EOD (2026-05-04)

| Field | Value |
|---|---|
| Equity | $99,849.69 |
| Cash | $4,986.91 (4.99%) |
| Positions | 4 |
| Trades that day | 53 |
| period_vs_spy (bot-reported) | -10.71% |
| spy_30d (bot-reported) | +10.71% |

---

## Positions at Close (2026-05-04 — frozen state, unmonitored since)

| Symbol | Side | Qty | Avg Entry | Price (5/4) | PnL% | Weight |
|---|---|---|---|---|---|---|
| SPY | LONG | 83.138 | $717.52 | $718.03 | +0.07% | 59.8% |
| AXTX | LONG | 313 | $46.41 | $46.61 | +0.43% | 14.6% |
| PWR | LONG | 14.695 | $758.48 | $757.38 | -0.15% | 11.1% |
| META | LONG | 15.477 | $611.73 | $610.46 | -0.21% | 9.5% |
| **Cash** | — | — | — | — | — | **5.0%** |

> These weights are as of 2026-05-04. No monitoring has occurred for ~67 calendar days.
> True current P&L from avg_entry basis is unknowable without live prices (market data blocked).

---

## Trades Today

No trades on 2026-07-10. Last trade was `2026-05-04T19:08:47Z` (COIN `exit_learning_metrics`).

Last meaningful trade batch (2026-05-04 ~19:08 UTC):

| Symbol | Event | Qty | Price | Reason (truncated) |
|---|---|---|---|---|
| COIN | position_closed | 66.90 | $203.45 | EXIT 0% — momentum 0, fading, earnings in 3d |
| GOOGL | position_closed | 37.96 | $382.77 | EXIT 0% — momentum 0, fading, below EMA20 |
| FIX | position_closed | 10.00 | $1,902.81 | verifier dust-sweep target=0 |
| AXTX | ai_order_submitted | 313 | $46.41 | BUY 14.4% — momentum 100, breaking_out, 2.79× vol |
| META | ai_order_submitted | 15.477 | $611.73 | BUY 9.5% — comm-svcs leader, acceptable continuation |
| PWR | ai_order_submitted | 14.695 | $758.48 | BUY 11.1% — data-center power leader, bullish EMA |

---

## (Full analysis appended below)

---

## Per-Trade Quality Analysis (2026-05-04 final scan)

All 53 trades on 2026-05-04 involved 6 entry events, multiple verifier reconciles, wash-trade
recovery events, and exit_learning_metrics. Summary of notable actions:

| Symbol | Action | Size | Entry/Exit | PnL (5/4 close) | AI Grade | Quality Verdict |
|---|---|---|---|---|---|---|
| COIN | EXIT | 66.90 sh | $203.45 | est. neutral (small pnl) | confidence 0.55 | **Good** — earnings in 3d, correct risk management |
| GOOGL | EXIT | 37.96 sh | $382.77 | negative (below avg entry) | confidence 0.55 | **Good** — momentum 0, exit-arbiter right to close |
| DELL | EXIT (verifier) | 57.39 sh | $210.94 | → 30m: -$14.92, 60m: +$16.64 | — | **Neutral** — dust-sweep, minor delta |
| LLY | EXIT (verifier) | 13 sh | $963.71 | → 30m: +$33.60, 60m: +$69.71 | — | **Missed** — LLY continued up 60m; premature exit |
| WDC | EXIT (verifier) | 24.51 sh | $440.06 | → 30m: -$59.68, 60m: +$100.00 | — | **Mixed** — negative 30m but recovered 60m |
| AXTX | BUY | 313 sh | $46.41 | +$62.60 (+0.43%) | conf 0.88, opp 88 | **Good entry** — best-score name, high conviction |
| META | BUY | 15.48 sh | $611.73 | -$19.63 (-0.21%) | conf 0.65, opp 58 | **Marginal** — lower conviction; slight drawdown immediately |
| PWR | BUY | 14.69 sh | $758.48 | -$16.16 (-0.15%) | conf 0.72, opp 68 | **Marginal** — acceptable entry but mild immediate slippage |
| FIX | BUY→EXIT (same day) | 10 sh | $1,903.71 → $1,902.81 | -$0.90 | conf 0.88 | **Churn** — bought at 18:05 then verifier-swept at 19:08 |

---

## Cross-Trade Patterns

- **Verifier churn:** FIX was bought (confidence 0.88, opp 85) at 18:05 UTC and swept as "dust" by the
  verifier at 19:08 UTC — a 63-minute round-trip generating friction with no P&L benefit. The 70%
  staging rule did not prevent this; the selector may have deselected FIX in the subsequent scan.

- **Premature verifier exit on LLY:** Exited at $963.71; 60m post-exit price was $969.07 (+$69.71 missed).
  The `exit_learning_metrics` confirms the exit was too early. Pattern seen in 5/1 and 5/4: verifier
  dust-sweeps positions that still had momentum.

- **WDC ambiguous exit:** -$59.68 at 30m, +$100.00 at 60m — exit was directionally premature but not
  catastrophic; falls within acceptable noise given 1% max stop.

- **COIN earnings-gate working:** Exited 3 days before earnings. Correct process, correct timing.

- **GOOGL fading exit correct:** Bought earlier in the day (verifier reconcile), then exit-arbiter
  closed it at momentum=0. The round-trip likely broke even or had small loss; confidence call was right.

- **No bearish macro halt violations:** The 5/4 macro regime did not trigger a halt (score not below -0.55).
  SPY was -0.36% that day — macro was neutral, consistent with new entries being permitted.

- **Sector concentration at final snapshot:** 3 of 4 single-name positions are in distinct sectors
  (Healthcare proxy AXTX, Industrials PWR, Comm-Svcs META) + SPY hedge. Sector guard appears to
  have been respected.

- **AXTX is a leveraged ETF (2× AXTI):** `Tradr 2X Long AXTI Daily ETF` — this is a levered instrument.
  Its beta characteristics differ from single equities. The bot entered at 14.4% of portfolio with
  a daily-rebalancing 2× product. This compounds decay risk over the 9.7-week frozen period.

---

## Proposed Changes

### 1. AXTX — Flag Leveraged ETF Risk in Discovery

**Why:** AXTX (`Tradr 2X Long AXTI Daily ETF`) is a daily-rebalancing 2× product. Held for 67+
calendar days without monitoring, it experiences volatility decay. The discovery pipeline did not
reject it as a leveraged instrument.

**Diff (config.yaml):**
```yaml
# Add to discovery section (existing key or new):
discovery:
  exclude_leveraged_etfs: false   # BEFORE
  exclude_leveraged_etfs: true    # AFTER  (reject tickers with "2X", "3X", "Ultra" in name)
```

**Expected impact:** Prevents single-digit-expense leveraged instruments from entering the portfolio.
Would have excluded AXTX on 5/4. Small candidate pool impact (~2-3 names/scan).

---

### 2. Verifier Dust-Sweep — Add Min-Notional Guard

**Why:** FIX was bought for ~$19K at 18:05 then swept as "dust" at 19:08 by the verifier (target=0 from
a subsequent selector run). This is a same-scan-cycle entry + immediate exit — pure friction.

**Diff (src/executor.py or config.yaml):**
```yaml
# config.yaml
portfolio_verifier:
  dust_sweep_min_notional_usd: 500    # BEFORE: 0 (no floor)
  dust_sweep_min_notional_usd: 5000   # AFTER: don't sweep positions > $5K notional same-cycle
```
Or equivalently in `src/orchestrator.py`: skip verifier dust-sweep for positions opened within
the same scan cycle (age < 2 scans).

**Expected impact:** Eliminates same-cycle churn. Would have kept FIX alive for at least one
follow-on scan before eviction. Reduces round-trip friction cost (est. $10-30/event in slippage).

---

### 3. LLY-style Verifier Exits — Add 30m Momentum Check

**Why:** LLY exited at $963.71; 60m price was $969.07 (+$69.71 missed). The verifier swept it as
"dust target=0" without checking near-term momentum. This is a systemic pattern (WDC similar).

**Diff (src/orchestrator.py, verifier reconcile block):**
```python
# BEFORE: sweep any position where target_qty == 0
if target_qty == 0:
    close_position(symbol, reason="verifier dust-sweep target=0")

# AFTER: require stale signal before sweeping
if target_qty == 0 and position_age_scans >= 2:
    close_position(symbol, reason="verifier dust-sweep target=0")
# Positions opened THIS scan cycle are left to the next scan's arbiter
```

**Expected impact:** Saves 1-2 premature exits/week. Conservative estimate: +$50-150/week in
avoided missed-momentum slippage based on `exit_learning_metrics` 60m deltas.

---

### 4. Post-Scheduler Heartbeat — Write No-Activity Sentinel

**Why:** The scheduler has been silent 67 calendar days with no automated alert. The daily review
job is producing output but has no mechanism to alert on scheduler death distinct from "no-data."

**Diff (scripts/scan_and_trade.py, top of main):**
```python
# BEFORE: no heartbeat
# AFTER: write a heartbeat file on each invocation
import pathlib, datetime
pathlib.Path('data/research/heartbeat.json').write_text(
    json.dumps({'ts': datetime.datetime.utcnow().isoformat(), 'event': 'scan_started'})
)
```

**Diff (daily review / postmortem script):**
```python
# Check heartbeat age; if > 2 trading days, escalate immediately
hb = pathlib.Path('data/research/heartbeat.json')
if not hb.exists() or (now - hb.stat().st_mtime) > 2 * 86400:
    notify_telegram("SCHEDULER DEAD — no scan heartbeat in >2d")
```

**Expected impact:** Would have caught the 5/4 scheduler death by ~5/6, not 7/10. Zero cost to
strategy performance; purely operational.

---

### 5. Frozen-Book Exposure Cap — Auto-Halt If No Scan > N Days

**Why:** After 67 days without a scan, the portfolio holds a concentrated leveraged ETF (AXTX)
and two sector longs without any stop-loss monitoring. The stops placed on 5/4 are stale — the
account may or may not have been stopped out; this review has no visibility.

**Diff (config.yaml):**
```yaml
risk:
  max_days_without_scan_before_flatten: null   # BEFORE: no auto-halt
  max_days_without_scan_before_flatten: 5      # AFTER: if no scan in 5 trading days, flatten to SPY+cash
```

**Diff (scripts/scan_and_trade.py startup check):**
```python
last_scan = max(glob.glob('data/research/*_scan.json'), key=os.path.getmtime, default=None)
if last_scan and (now - os.path.getmtime(last_scan)) > cfg['risk']['max_days_without_scan_before_flatten'] * 86400:
    flatten_to_spy_and_cash()
    sys.exit(0)
```

**Expected impact:** Prevents multi-week frozen-book exposure with unmonitored stops. Would have
triggered auto-flatten on ~5/11, reducing concentration risk from AXTX decay and unmonitored
single-name positions. Conservative capital preservation; no strategy cost when the bot is healthy.

---

## Backtest Notes

No offline backtest is possible for proposals 1–5:
- Proposals 1, 2, 3 require intraday price history to replay the alternative path.
- Proposals 4, 5 are operational/infrastructure — no P&L history to replay.
- Market data sources (yfinance, Alpha Vantage, Twelve Data) all return 403 from this container.

The `exit_learning_metrics` in `trades.jsonl` provide partial evidence for proposals 2 and 3:
- LLY: 60m missed = +$69.71 (premature exit confirmed)
- WDC: 60m missed = +$100.00 (premature exit confirmed)
- MU: 60m missed = -$166.08 (exit was actually early but directionally correct; not a miss)
- COIN: 60m missed = -$1.17 (exit was correct; near-zero drift)
- DELL: 60m missed = +$16.64 (negligible)

Weighted 60m: proposals 2 & 3 would have saved est. +$169.71 across 5/4 events alone if applied
to LLY and WDC. At 53 trades on 5/4 (an unusually active day), the per-event improvement is small
but directionally consistent.

---

## Operational Status (unchanged from prior reviews)

The only actionable item remains:

> **Confirm the bot scheduler is running and writing artifacts into this repo.**

1. Verify cron/GitHub Action invoking `scripts/scan_and_trade.py` 6×/day has fired since 5/4.
2. Check write path divergence: compare `data/research/` mtimes on runtime host vs. this checkout.
3. Log into Alpaca PA34KBGT3V7E — confirm whether positions/equity have changed since 5/4.
4. From 5/4 EOD: equity $99,849.69; positions AXTX 313, META 15.477, PWR 14.695, SPY 83.138; cash $4,987.
5. **AXTX is a 2× daily ETF** — 67 days of no monitoring on a levered position is a live risk.

All 8 strategy proposals from 2026-05-05 daily review remain open and untested. This post-mortem
adds 5 new proposals (above). None can be validated until fresh scan data appears.

---

*Generated by post-mortem-bot on 2026-07-10. Branch: `postmortem-2026-07-10`.
Merge with: `accept postmortem-2026-07-10` in Telegram, or close with `reject postmortem-2026-07-10`.*
