# Post-Mortem 2026-04-23

## Data availability
| File | Status |
|------|--------|
| `data/research/2026-04-23_eod.json` | ✅ Present |
| `data/research/2026-04-22_eod.json` | ✅ Present (30d series: 2 days only) |
| `data/journal/trades.jsonl` | ✅ Present |
| `data/journal/decisions.jsonl` | ✅ Present |
| `data/research/20260423T150718_scan.json` | ✅ Present |
| `data/research/20260423T195604_preclose.json` | ✅ Present |
| 30-day EOD history | ⚠️ Only 2 days available — rolling stats limited |

---

## Performance today (portfolio vs SPY)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **+1.56%** |
| SPY daily return | **-0.39%** |
| Outperformance vs SPY | **+1.95%** ✅ |
| Equity (EOD) | $101,208.19 |
| Cash (EOD) | **-$935.19** ⚠️ (negative — cash_reserve_pct breached) |
| Positions | 10 |
| Trades today | 9 |
| daily_drawdown | 0% (positive day) |
| Kill switch | Not triggered |

**Risk budget status:**
- `cash_reserve_pct` (5%): **BREACHED** — cash is -$935 (-0.92% of equity)
- `max_position_pct` (15%): ✅ max position is ~13% (AMD)
- `daily_drawdown` (2.5%): ✅ no drawdown

---

## Positions at close

| Symbol | Side | Qty | Avg Entry | Close | P&L% | MV ($) | % Portfolio |
|--------|------|-----|-----------|-------|------|--------|-------------|
| AMD | LONG | 41.42 | $302.72 | $305.33 | +0.86% | $13,166 | 13.0% |
| APLS | LONG | 184 | $40.93 | $40.94 | +0.02% | $7,533 | 7.4% |
| ARW | LONG | 67.25 | $183.21 | $187.50 | +2.34% | $12,609 | 12.5% |
| AVGO | LONG | 29.16 | $420.07 | $419.94 | **-0.03%** | $12,289 | 12.1% |
| FIX | LONG | 7.08 | $1758.55 | $1773.91 | +0.87% | $13,100 | 12.9% |
| GEV | LONG | 10.98 | $1140.45 | $1149.53 | +0.80% | $12,627 | 12.5% |
| IRDM | LONG | 105 | $40.86 | $40.93 | +0.17% | $4,298 | 4.2% |
| MU | LONG | 25.68 | $480.57 | $481.72 | +0.24% | $12,434 | 12.3% |
| SPY | LONG | 2.37 | $711.70 | $708.45 | **-0.46%** | $1,677 | 1.7% |
| VRT | LONG | 38.53 | $315.20 | $321.75 | +2.08% | $12,410 | 12.3% |

> P&L computed as `(current_price - avg_entry) / avg_entry`; shorts flip sign. `pnl_pct` from eod.json used directly.

---

## Trades today

| Time (UTC) | Symbol | Side | Type | Notional | Reason |
|------------|--------|------|------|----------|--------|
| 15:06:17 | AMD | BUY | Rebalance add | $7,506 | conf=0.74, tech=+0.85, pnl=+3.7% |
| 15:06:18 | ARW | BUY | Rebalance add | $3,803 | conf=0.73, tech=+0.82, pnl=+3.5% |
| 15:06:18 | AVGO | BUY | Rebalance add | $7,344 | conf=0.71, tech=+0.78, pnl=+4.5% |
| 15:06:18 | FIX | BUY | Rebalance add | $7,274 | conf=0.73, tech=+0.81, pnl=+3.1% — **risk agent: REJECT** |
| 15:06:18 | GEV | BUY | Rebalance add | $6,918 | conf=0.73, tech=+0.83, pnl=+2.8% — risk agent: caution |
| 15:06:18 | MU | BUY | Rebalance add | $8,052 | conf=0.70, tech=+0.75, pnl=+1.1% |
| 15:06:19 | VRT | BUY | Rebalance add | $7,001 | conf=0.72, tech=+0.79, pnl=+7.3% |
| 19:56:03 | APLS | BUY | Preclose overnight | $7,531 | ov=+0.39, RSI 87.2 ⚠️ |
| 19:56:03 | IRDM | BUY | Preclose overnight | $4,301 | ov=+0.36, RSI 70.3 |

**Failed exits (preclose — Pydantic bug):**
| Symbol | Decision | Error |
|--------|----------|-------|
| AVGO | close (dir=-0.034) | `ClosePositionRequest`: qty and percentage both None |
| MU | close (dir=-0.102) | `ClosePositionRequest`: qty and percentage both None |

---

*(Full analysis appending in next commit)*
