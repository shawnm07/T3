# Post-Mortem 2026-04-27

## Data Availability

| Source | Status |
|--------|--------|
| `data/research/2026-04-27_eod.json` | ✅ present |
| `data/research/20260427T*.json` (7 scans) | ✅ present |
| `data/journal/trades.jsonl` (24 today) | ✅ present |
| `data/journal/decisions.jsonl` (240 today) | ✅ present |
| `config.yaml` | ✅ present |
| Rolling EOD (4 dates: 04-22…04-27) | ✅ present |
| `data/research/20260427T195644_preclose.json` | ✅ present |

---

## Performance Today (Portfolio vs SPY, from eod.json)

| Metric | Value |
|--------|-------|
| EOD Equity | $96,447.88 |
| Daily Return | **-4.88%** |
| SPY Daily | +0.17% |
| vs SPY (daily) | **-5.05%** ❌ |
| Cash at EOD | $4,697.68 (4.87%) ⚠️ below 5% floor |
| Positions | 8 |
| Trades Today | 24 |
| Kill Switch | NOT triggered (preclose snapshot showed +1.24%) |

### Risk-Budget Breaches
- `daily_drawdown` = 4.88% > **2.5% limit** — kill switch threshold exceeded
- `cash_reserve_pct` = 4.87% < **5.0% floor**
- `max_position_pct` (goal: 0.15) = MU at **28.4%** of EOD equity

---

## Positions at Close

| Symbol | Side | Avg Entry | Close | PnL% | $ PnL | Wt% |
|--------|------|-----------|-------|------|-------|-----|
| AMD | LONG | $319.29 | $315.50 | -1.19% | -$57.83 | 4.99% |
| AVGO | LONG | $422.52 | $398.65 | -5.65% | -$406.57 | 7.04% |
| DELL | LONG | $214.48 | $205.67 | -4.11% | -$751.65 | 18.19% |
| FIX | LONG | $1,768.58 | $1,615.00 | -8.68% | -$1,218.55 | 13.28% |
| GEV | LONG | $1,140.45 | $1,050.70 | -7.87% | -$321.64 | 3.90% |
| MU | LONG | $514.53 | $495.13 | -3.77% | -$1,071.68 | **28.36%** |
| SPY | LONG | $711.05 | $714.90 | +0.54% | +$27.57 | 5.31% |
| VRT | LONG | $316.00 | $303.16 | -4.06% | -$573.94 | 14.04% |

**All 8 positions red except SPY cash proxy.** Total mark-to-market loss: **-$4,374.29**

---

## Trades Today (24 total)

| Time (UTC) | Symbol | Side | Notional | Fill Px | Reason |
|------------|--------|------|----------|---------|--------|
| 15:00 | AMD | SELL | $2,145 | $335.14 | arbiter REDUCE 12.1% → 10% |
| 15:00 | ARW | SELL | $6,032 | $185.83 | arbiter EXIT 5.9% → 0% |
| 15:00 | FIX | SELL | $2,522 | $1,750.21 | arbiter REDUCE 12.5% → 10% |
| 15:00 | GEV | SELL | $2,205 | $1,107.26 | arbiter REDUCE 12.2% → 10% |
| 15:00 | OGN | SELL | $4,344 | $13.17 | arbiter EXIT, take +16% gain |
| 15:00 | DELL | BUY | $8,245 | $214.06 | arbiter INCREASE 9.9% → 18% |
| 15:00 | MU | BUY | $11,160 | $519.97 | arbiter INCREASE 9% → 20% |
| 16:01 | AMD | SELL | $1,914 | $332.45 | arbiter REDUCE 9.9% → 8% |
| 16:01 | GEV | SELL | $2,758 | $1,110.08 | arbiter REDUCE 9.7% → 7% |
| 16:01 | FIX | BUY | $2,014 | $1,782.44 | arbiter INCREASE 10% → 12% |
| 16:01 | MU | BUY | $3,991 | $528.65 | arbiter INCREASE 20.1% → 24% |
| 16:03 | VRT | BUY | $754 | $319.24 | verifier reconcile → 13% |
| 18:00 | AMD | SELL | $2,074 | $335.03 | arbiter REDUCE 8% → 6% |
| 18:00 | GEV | SELL | $2,290 | $1,121.20 | arbiter REDUCE 7.3% → 5% |
| 18:00 | FIX | BUY | $2,100 | $1,803.74 | arbiter INCREASE 11.9% → 14% |
| 18:03 | AVGO | SELL | $818 | $416.30 | verifier reconcile → 7% |
| 18:03 | MU | BUY | $3,179 | $518.29 | verifier reconcile → 27% |
| 19:30 | AMD | SELL | $1,000 | $336.73 | arbiter REDUCE 6% → 5% |
| 19:30 | GEV | SELL | $983 | $1,115.10 | arbiter REDUCE 5% → 4% |
| 19:33 | MU | BUY | $1,338 | $520.59 | verifier reconcile → 28% |
| 19:33 | VRT | BUY | $1,223 | $322.10 | verifier reconcile → 14% |

*(3 zero-fill events: APLS ×2, IRDM ×1 — apparent order rejections, not included above)*

---

## (Full analysis appending in next commit)
