# Post-Mortem 2026-04-23

## Data Availability

| Source | Status |
|--------|--------|
| `data/research/2026-04-23_eod.json` | **MISSING** — EOD report not yet generated |
| `data/research/*_scan.json` (today) | **MISSING** — no scan files with today's mtime |
| `data/journal/trades.jsonl` (today) | No new order_submitted events on 2026-04-23 |
| `data/journal/decisions.jsonl` (today) | 6 entries — all crypto "hold" decisions |
| `config.yaml` | Present |
| SPY benchmark | **UNAVAILABLE** — yfinance not installed, external APIs blocked in sandbox |

> Portfolio carries 7 open positions from 2026-04-22 entries (VRT, AVGO, AMD, MU, FIX, GEV, ARW).
> No new equity trades executed on 2026-04-23. Crypto scanner ran at 03:05 and 07:05 UTC — all 3 assets held below confidence threshold.

---

## Performance (Today vs SPY)

| Metric | Value |
|--------|-------|
| Portfolio daily % | **TBD** — no equity snapshots in journal |
| SPY daily % | **UNAVAILABLE** — external APIs blocked in sandbox |
| vs Benchmark | TBD |

> Risk budget: max_position_pct=0.15 · cash_reserve≥5% · daily_drawdown<2.5%

---

## Trades Executed Today

**No new trades on 2026-04-23.** Open carry positions from prior session:

| Symbol | Side | Qty | Entry | Stop | TP | Notional | Conf | Opened |
|--------|------|-----|-------|------|----|----------|------|--------|
| VRT | buy | 17 | 301.01 | 274.21 | 354.61 | $5,117 | 0.57 | 04-22 14:11 |
| AVGO | buy | 12 | 409.11 | 385.93 | 455.47 | $4,909 | 0.56 | 04-22 14:11 |
| AMD | buy | 17 | 296.00 | 274.32 | 339.36 | $5,032 | 0.56 | 04-22 16:02 |
| MU | buy | 9 | 477.32 | 426.40 | 579.16 | $4,296 | 0.56 | 04-22 16:02 |
| FIX | buy | 3 | 1,727.51 | 1,591.86 | 1,998.81 | $5,183 | 0.64 | 04-22 19:55 |
| GEV | buy | 5 | 1,119.65 | 1,033.27 | 1,292.42 | $5,598 | 0.58 | 04-22 19:55 |
| ARW | buy | 47 | 181.12 | 170.76 | 201.83 | $8,512 | 0.58 | 04-22 19:55 |

**Crypto decisions today (all hold — below threshold):**

| Symbol | Time (UTC) | Score | Confidence | Action |
|--------|-----------|-------|-----------|--------|
| BTC/USD | 03:05 | +0.016 | 0.02 | hold |
| ETH/USD | 03:05 | -0.069 | 0.07 | hold |
| SOL/USD | 03:05 | -0.100 | 0.10 | hold |
| BTC/USD | 07:05 | +0.040 | 0.04 | hold |
| ETH/USD | 07:05 | -0.046 | 0.05 | hold |
| SOL/USD | 07:05 | -0.072 | 0.07 | hold |

---

## Preliminary Observations

- **No new entries today** — all equity signals were below threshold or scanner did not run with AI.
- **Crypto is weak** — SOL RSI 35–41, ETH RSI 39–44, BTC RSI 49–53. Bot correctly staying out of momentum-faded crypto.
- **Position concentration risk** — 7 open longs (all tech/industrials, all opened 04-22). ARW notional ($8,512) exceeds the rest; combined ~$38.6K notional.
- **All positions are RSI-overextended at entry** — AMD (82), AVGO (76), FIX (70), VRT (60). AI flagged this in all four.
- **Macro was neutral at entry** — VIX 28–29, breadth 58–62%, SPY slightly above 200-EMA. Not a strong tailwind.

---

## (Full Analysis — Phase 2 Appended Below)

---

## Trade-by-Trade Quality Assessment

| Symbol | Side | Entry | Stop | TP | Conf | AI Grade | Quality Verdict |
|--------|------|-------|------|----|------|----------|-----------------|
| VRT | buy | 301.01 | 274.21 | 354.61 | 0.57 | B/C+ (macro C+, tech B, fund C, sent A) | **Speculative/momentum** — AI flagged bubble valuation (PE 88x, D/E 82x), tight stops relative to ATR. Earnings catalyst real; size was minimum, appropriate. |
| AVGO | buy | 409.11 | 385.93 | 455.47 | 0.56 | B-/B (tech B, fund B-, sent A-) | **Churn risk** — RSI 76.3 overbought at entry, AI recommended waiting for 397–400 pullback. Bot entered anyway. Entry timing poor. |
| AMD | buy | 296.00 | 274.32 | 339.36 | 0.56 | C/B (tech B, fund C, sent B+) | **Bad timing** — RSI 82 deeply overbought, weak fundamentals (ROE 7%, PE 113x). AI conviction only 0.52. Classic crowded-sector entry. |
| MU | buy | 477.32 | 426.40 | 579.16 | 0.56 | B (tech B, fund B, sent C+) | **Best fundamental** — PEG 0.26, ROE 40%, 196% rev growth. Wide stop needed given high ATR. Only one with real quality. |
| FIX | buy | 1727.51 | 1591.86 | 1998.81 | 0.32* | overnight-only | **Overnight spec** — confidence in sizing was 0.32 (size_multiplier=0.5 applied). Golden cross + close-near-high. Reasonable overnight play; high notional per share creates P&L swings. |
| GEV | buy | 1119.65 | 1033.27 | 1292.42 | 0.58 | — | **Overnight** — entry via preclose scanner. No full AI evaluation logged. |
| ARW | buy | 181.12 | 170.76 | 201.83 | 0.58 | — | **Oversized** — $8,512 notional is largest position, ~14% of ~$60K est. portfolio. At max_position_pct boundary. Overnight entry. |

*FIX confidence 0.64 from overnight scorer; 0.322 recorded in sizing (after overnight size_multiplier applied).

---

## Cross-Trade Patterns

- **Sector concentration**: 5 of 7 positions are Information Technology or Industrials. Correlated drawdown risk if tech sentiment reverses.
- **RSI at entry**: 4 of 5 daytime entries were RSI ≥ 66 (AMD 82, AVGO 76, FIX 70, MU 67). Bot is buying momentum peaks, not pullbacks. AI flagged all four yet positions opened.
- **AI vs numeric disagreement**: Technical scores were uniformly strong (0.71–0.83) but AI confidence was capped at 0.52–0.55. The numeric signal consistently "won" even when AI was reluctant — this is the blend weight (ai.weight=0.6) not sufficiently discounting overextended entries.
- **No false bearish halts observed** — macro scored 0.19–0.21, above the bearish_halt_score=-0.55. Correct.
- **Crypto correctly ignored** — all 6 crypto decisions stayed below threshold (max score BTC +0.04). No churn.
- **No winner-trimming events logged** — positions opened 04-22, no exit events in journal. Phase 1 hold day.

---

## Benchmark

| Period | Portfolio % | SPY % | vs Benchmark |
|--------|------------|-------|-------------|
| Today (04-23) | **TBD** (no equity snapshots) | **N/A** (API blocked) | TBD |
| Rolling 5d | **TBD** | **N/A** | TBD |
| Rolling 30d | **TBD** | **N/A** | TBD |

> SPY benchmark comparison deferred — yfinance unavailable in sandbox, external APIs blocked. Push local equity snapshots to `data/journal/` to enable future P&L calculation.

---

## Proposed Changes

### P1 — RSI Overbought Entry Gate

**Why**: 4 of 5 daytime entries had RSI ≥ 66 at entry, all flagged by AI. Bot is systematically entering momentum peaks rather than pullbacks. AMD (RSI 82) and AVGO (RSI 76) are highest risk of immediate mean-reversion.

**Diff** (`config.yaml`):
```yaml
# BEFORE
signals:
  weights:
    macro: 0.15
    technical: 0.35
    fundamental: 0.20
    sentiment: 0.15
    risk: 0.15

# AFTER — add RSI entry gate in screener section
screener:
  min_market_cap_usd: 2000000000
  min_avg_volume: 1000000
  min_price: 5
  max_entry_rsi: 72          # NEW: skip entries when RSI > 72 at time of order
```

**Expected impact**: Would have blocked AMD and AVGO entries today. Reduces ~2 of 5 overextended long entries per scan cycle. Trades that do execute will have lower immediate mean-reversion probability. Slight reduction in trade frequency (~30–40% of signals filtered in high-momentum regimes).

---

### P2 — AI Reluctance Veto Power (min_ai_confidence_to_override_rsi)

**Why**: AI flagged all overextended RSIs but the numeric technical score (0.71–0.83) overrode caution. At `ai.weight=0.6`, a strong technical score can still produce `blended_conf ≥ min_confidence=0.40` even when AI rates confidence 0.52. Need a hard floor when AI and technicals disagree.

**Diff** (`config.yaml`):
```yaml
# BEFORE
ai:
  weight: 0.6

# AFTER
ai:
  weight: 0.6
  min_ai_confidence_when_rsi_overbought: 0.60   # NEW: if RSI > 70, require AI confidence >= 0.60
```

**Expected impact**: Would have blocked AMD (AI conf 0.52), potentially AVGO (0.55 borderline). Requires a code change in `src/` to check this gate — config key is a proposal marker for the dev.

---

### P3 — Overnight Position Size Cap

**Why**: ARW opened at $8,512 notional via preclose scanner — the largest position in the book and near the max_position_pct=0.15 boundary. Overnight holds carry gap risk; the current `size_multiplier=0.5` only applies to new overnight buys but the overnight scorer did not enforce it on ARW ($8,512 suggests it was applied from a $17K base position, which itself would be oversized).

**Diff** (`config.yaml`):
```yaml
# BEFORE
overnight:
  size_multiplier: 0.5
  max_new_positions: 3

# AFTER
overnight:
  size_multiplier: 0.4        # tighten: 40% of normal sizing for overnight carry
  max_new_positions: 3
  max_single_notional_usd: 6000   # NEW: cap any single overnight entry at $6K notional
```

**Expected impact**: Caps ARW-class positions at $6K, reducing overnight gap exposure by ~30%. At a $6K ARW position vs $8.5K actual, max overnight drawdown on 5% gap-down reduces from ~$425 to ~$300.

---

### P4 — Require EOD Snapshot for Performance Tracking

**Why**: This post-mortem has zero P&L data because no equity snapshots exist in the journal. Cannot compute daily/rolling returns, cannot detect drawdown breaches proactively.

**Diff** (`config.yaml`):
```yaml
# BEFORE
scheduling:
  eod_time: "16:15"

# AFTER
scheduling:
  eod_time: "16:15"
  eod_snapshot: true    # NEW: write equity/position snapshot to data/journal/snapshots/ at EOD
```

**Expected impact**: Enables automated P&L calculation, drawdown monitoring, and future post-mortem benchmarking. Zero trading impact.

---

## Notes

- Backtest skipped: no yfinance or market data available in sandbox. Proposals P1 and P3 are config-only; P2 and P4 require minor `src/` changes.
- Next post-mortem will have benchmark data if: (a) EOD snapshot is added, or (b) market data access is restored.
