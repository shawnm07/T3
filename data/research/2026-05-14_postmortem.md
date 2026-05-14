# Post-Mortem 2026-05-14

## Data Availability

| Source | Status |
|--------|--------|
| `2026-05-14_eod.json` | **MISSING** — no bot runs detected for 2026-05-07 through 2026-05-14 |
| `2026-05-04_eod.json` | Last available EOD snapshot (used as baseline) |
| `20260504T*_scan.json` | 6 scans available (last bot session) |
| `data/journal/decisions.jsonl` | 105 events on 2026-05-04 |
| `data/journal/trades.jsonl` | 53 trades on 2026-05-04 |
| `config.yaml` | Current thresholds baseline |

> **Note:** The bot has not produced data files for 2026-05-05 through 2026-05-14 (8 trading days). This post-mortem analyses the last complete session (2026-05-04) and the full rolling 30d window. Root-cause for the gap is unknown from repo data alone.

---

## Performance Today — 2026-05-04 (Last Available Session)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily alpha | **-1.44%** |
| Equity at close | $99,849 |
| Cash | $4,987 (5.0%) |
| Positions at close | 4 |
| Trades executed | **53** |
| AI selector failures | 2 (of 8 calls) |

## Rolling Performance (from EOD files)

| Date | Equity | Port Return | SPY Daily | Alpha |
|------|--------|------------|-----------|-------|
| 2026-04-22 | $99,627 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | $101,208 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | $99,343 | -0.81% | +0.77% | -1.58% |
| 2026-04-27 | $96,448 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | $96,867 | -5.13% | -0.49% | -4.64% |
| 2026-04-29 | $93,999 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | $95,786 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | $101,101 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | $99,850 | -1.80% | -0.36% | -1.44% |

**5-day avg return:** portfolio -2.64% vs SPY +0.08%  
**30d cumulative portfolio return (sum of dailies):** -17.31%  
**SPY 30d return (from eod.json):** +10.71%  
**Underperformance vs SPY benchmark:** ~-28%

> 7 of 9 tracked sessions had negative alpha. The only positive alpha day was 2026-04-23 (+1.95%). The strategy is systematically destroying value relative to a SPY hold.

---

## Positions at Close (2026-05-04)

| Symbol | Side | Avg Entry | Current Price | PnL% | Market Value |
|--------|------|-----------|---------------|------|-------------|
| AXTX | Long | $46.41 | $46.61 | +0.43% | $14,589 |
| META | Long | $611.73 | $610.46 | -0.21% | $9,448 |
| PWR | Long | $758.48 | $757.38 | -0.15% | $11,130 |
| SPY | Long | $717.52 | $718.03 | +0.07% | $59,696 |

> AXTX = "Tradr 2X Long AXTI Daily ETF" (2× leveraged). SOXS (inverse ETF) was selected but apparently not in the final positions — possible execution failure or late-session close. SPY cash-proxy position was ~60% of equity despite the selector targeting 0% SPY for most of the day.

---

## Trades Today (2026-05-04 — 53 total)

| Time (UTC) | Event | Symbol | Side | Qty | Price | Reason (abbrev.) |
|-----------|-------|--------|------|-----|-------|------------------|
| 14:00 | exit_arbiter reduce | HCAI | sell | partial | — | lost VWAP/EMA20, fading |
| 14:00 | exit_arbiter reduce | STX | sell | partial | — | lost VWAP, -3% from open |
| 14:09 | AI failure | portfolio-selector | — | — | — | 3 retries, selected=0 |
| 15:02 | AI failure | portfolio-selector | — | — | — | 3 retries, selected=0 |
| 15:13 | selector output | — | — | — | — | Picked AMZN/GEV/COIN/MU/UNH |
| 16:04 | position_closed | AMZN | sell | 65.3 | $270.65 | verifier dust-sweep |
| 16:04 | position_closed | GEV | sell | 14.6 | $1,071.49 | verifier dust-sweep |
| 16:04 | position_closed | UNH | sell | 17.3 | $368.25 | verifier dust-sweep |
| 17:04 | ai_order buy | FIX | buy | 6.30 | $1,900.24 | selector rank 1, breaking_out |
| 17:04 | ai_order buy | DELL | buy | — | — | selector rank 2 |
| 17:04 | ai_order buy | GOOGL | buy | — | — | selector rank 3 |
| 17:04 | position_closed | MU | sell | 23.0 | $580.81 | exit (intraday flip) |
| 18:05 | position_closed | WDC | sell | 24.5 | $440.06 | gap-only, broken thesis |
| 18:05 | ai_order buy (increase) | FIX | buy | 3.70 | $1,903.71 | rebalance to 19% target |
| 18:05 | wash_trade_recovery | FIX | — | — | — | stop order conflict |
| 18:05 | position_closed | DELL | sell | 57.4 | $210.94 | verifier dust-sweep target=0 |
| 18:05 | position_closed | LLY | sell | 13.0 | $963.71 | verifier dust-sweep target=0 |
| 18:05 | ai_order buy | GOOGL | buy | 9.28 | $384.43 | verifier gap-close to 14.6% |
| 18:05 | wash_trade_recovery | GOOGL | — | — | — | stop order conflict |
| 19:08 | position_closed | COIN | sell | 66.9 | $203.45 | thesis gone, earnings in 3d |
| 19:08 | position_closed | GOOGL | sell | 38.0 | $382.77 | momentum=0, fading |
| 19:08 | position_closed | FIX | sell | 10.0 | $1,902.81 | verifier dust-sweep target=0 |
| 19:08 | ai_order buy | AXTX | buy | 313.0 | $46.41 | selector rank 1, breaking_out |
| 19:08 | ai_order buy | META | buy | 15.5 | $611.73 | selector rank 5 |
| 19:08 | ai_order buy | PWR | buy | 14.7 | $758.48 | selector rank 3 |

*(Full analysis appending in next commit)*
