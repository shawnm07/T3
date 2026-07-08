# Post-Mortem 2026-07-08

## Data Availability

| Source | Status | Latest Entry |
|--------|--------|-------------|
| `_eod.json` | **MISSING** | `2026-05-04_eod.json` (44 trading days stale) |
| Intraday scans | **MISSING** | `20260504T190848_scan.json` |
| Preclose snapshot | **MISSING** | `20260504T195545_preclose.json` |
| `trades.jsonl` | **FROZEN** | `2026-05-04T19:55:03Z` (204 lines) |
| `decisions.jsonl` | **FROZEN** | `2026-05-04T20:15:04Z` (1556 lines) |

**This is the 8th consecutive no-data report.** The bot has been offline since 2026-05-04 (~9 weeks / 44 trading days). No new scan artifacts, no new journal entries. All figures below are from the last known EOD snapshot (2026-05-04).

## Performance Today (vs SPY)

| Metric | Value | Note |
|--------|-------|------|
| Today's portfolio daily return | **UNKNOWN** | No eod.json |
| SPY today | **UNKNOWN** | No eod.json |
| Last known daily return | **-1.80%** | 2026-05-04 |
| Last known SPY daily | **-0.36%** | 2026-05-04 |
| Last known daily vs SPY | **-1.44%** | Portfolio underperformed |
| Last known cumulative vs SPY | **-10.71%** | `period_vs_spy` in eod.json |
| Last known equity | **$99,849.69** | 2026-05-04 |
| Equity (today) | **UNKNOWN** | 9 weeks unmonitored |

Rolling 5-day and 30-day benchmarks cannot be computed — no eod.json for any trading day since 2026-05-04.

## Positions at Last Close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | Last Known Price | P&L% (from avg_entry) | Market Value |
|--------|------|-----|-----------|-----------------|----------------------|-------------|
| SPY | LONG | 83.138 | $717.52 | $718.03 | +0.07% | $59,695.86 |
| AXTX | LONG | 313 | $46.41 | $46.61 | +0.43% | $14,588.93 |
| PWR | LONG | 14.695 | $758.48 | $757.38 | -0.15% | $11,129.62 |
| META | LONG | 15.477 | $611.73 | $610.46 | -0.21% | $9,448.36 |
| Cash | — | — | — | — | — | $4,986.91 |

Portfolio weights at 5/4 EOD: SPY 59.8%, AXTX 14.6%, PWR 11.1%, META 9.5%, cash 5.0%.

**⚠ AXTX is a 2x leveraged ETF ("Tradr 2X Long AXTI Daily ETF") held unmonitored for 44 trading days.** Protective stop at $45.34 (1% below $46.41 entry) was submitted 2026-05-04T19:08. Stop order expiry / fill status unknown — Alpaca API is blocked.

## Trades Today

None. Bot offline.

## (Full analysis — Phase 2 — in next commit)
