# Post-Mortem 2026-07-24

## Data availability

| File | Status |
|------|--------|
| `data/research/2026-07-24_eod.json` | ❌ **MISSING** — no bot run on 2026-07-24 |
| `data/research/2026-07-24_*_scan.json` | ❌ **MISSING** — no scans on 2026-07-24 |
| `data/journal/trades.jsonl` | ✅ Present (last entry: 2026-05-04) |
| `data/journal/decisions.jsonl` | ✅ Present (last entry: 2026-05-04) |
| Most recent EOD | ✅ `2026-05-04_eod.json` |
| Most recent scan | ✅ `20260504T190848_scan.json` |
| 30-day EOD history | ⚠️ Only 9 days (2026-04-22 → 2026-05-04) |

> ⚠️ **CRITICAL: Bot has been inactive for ~81 calendar days (2026-05-04 → 2026-07-24).**
> No trades, no scans, no EOD snapshots since May 4. This post-mortem covers the last
> active session (2026-05-04) and the cumulative 9-day record that exists in repo data.

---

## Performance — last active session (2026-05-04 vs SPY)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | **-0.36%** |
| Daily alpha vs SPY | **-1.44%** ❌ |
| Equity (EOD 2026-05-04) | $99,849.69 |
| Cash (EOD) | $4,986.91 (5.0% — at floor) |
| Positions | 4 |
| Trades that session | **53** (extreme churn for swing cadence) |
| Macro regime | neutral (score 0.27, VIX 27.83) |

### Rolling benchmark (all available data: 9 trading days)

| Period | Portfolio | SPY | Alpha |
|--------|-----------|-----|-------|
| 9-day (Apr 22 – May 4) | **-16.31%** | **+1.95%** | **-18.26%** |
| 5-day (Apr 29 – May 4) | **-12.66%** | **+0.38%** | **-13.04%** |
| Days beating SPY | 2 / 9 | — | — |
| Avg daily alpha | -2.14% / day | — | — |
| Worst single day | **-5.40%** (Apr 29) | — | — |
| Best single day | **+1.82%** (May 1) | — | — |

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Qty | Avg Entry | Close | P&L% | Market Value | % Portfolio |
|--------|------|-----|-----------|-------|------|-------------|-------------|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** | $14,589 | 14.6% |
| META | LONG | 15.48 | $611.73 | $610.46 | **-0.21%** | $9,448 | 9.5% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | **-0.15%** | $11,130 | 11.1% |
| SPY | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** | $59,696 | 59.8% ⚠️ |

> P&L computed as `(current_price - avg_entry) / avg_entry`. SPY at 59.8% of equity = de facto cash-proxy position crowding out all active alpha.

---

## Trades on 2026-05-04 (53 total — notable events)

| Time (UTC) | Symbol | Side | Action | Reason |
|------------|--------|------|--------|--------|
| 14:51 | HCAI | CLOSE | Exit arbiter conf=0.72 | Down -8.78%; intraday momentum loss (5 signals) |
| 16:04 | AMZN | CLOSE | Exit arbiter | Fading momentum, below VWAP, bearish EMA |
| 16:04 | GEV | CLOSE | Exit arbiter | Weak momentum, below VWAP, flat trend |
| 16:04 | UNH | CLOSE | Exit arbiter | Acceptable but exited to fund LLY |
| 16:04 | LLY | BUY | Arbiter 9.1% | Strong healthcare leader, above VWAP, rising volume (staged 70%) |
| 16:04 | MU | ADD | Arbiter +28.0% | Pool leader; perfect momentum; increase to full target |
| 16:04 | NOK | BUY | Arbiter 4.9% | Telecom diversification (staged 70%) |
| 16:04 | SNDK | BUY | Arbiter 12.6% | Memory #2 behind MU (staged 70%) |
| 18:05 | DELL | EXIT | Exit learning | Qty 57.4, exit $210.94 |
| 18:05 | LLY | EXIT | Exit learning | Qty 13.0, exit $963.71 |
| 18:05 | WDC | EXIT | Exit learning | Qty 24.5, exit $440.06 |
| 18:25 | COIN | EXIT | Exit learning | Qty 5.1, exit $202.68 |
| 18:05 | MU | EXIT | Exit learning | Qty 57.4, exit ≈ $580.8 |

> Many positions entered and exited within the same session — classic churn pattern.

---

## (Full analysis appending in next commit)
