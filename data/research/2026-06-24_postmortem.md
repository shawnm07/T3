# Post-Mortem 2026-06-24

## Data availability

- **No EOD snapshot for 2026-06-24.** Last available: `2026-05-04_eod.json`.
- No scan files for 2026-06-24. Last scans: 2026-05-04 (7 scans + 1 preclose).
- Journal files (`trades.jsonl`, `decisions.jsonl`) present — last entries from 2026-05-04.
- `config.yaml` present and current.
- **This post-mortem covers the most recent data window: 2026-04-22 through 2026-05-04 (9 trading days).**
- Bot appears to have been offline since 2026-05-04.

## Performance summary (from EOD snapshots)

| Date       | Equity ($) | Daily Return | SPY Daily | vs SPY   | Positions | Trades |
|------------|------------|-------------|-----------|----------|-----------|--------|
| 2026-04-22 | 99,627     |  0.00%      | +1.01%    | -1.01%   | 7         | 7      |
| 2026-04-23 | 101,208    | +1.56%      | -0.39%    | +1.95%   | 10        | 9      |
| 2026-04-24 | 99,343     | -0.81%      | +0.77%    | -1.59%   | 12        | 19     |
| 2026-04-27 | 96,448     | -4.88%      | +0.17%    | -5.05%   | 8         | 24     |
| 2026-04-28 | 96,867     | -5.13%      | -0.49%    | -4.65%   | 4         | 21     |
| 2026-04-29 | 93,999     | -5.40%      | -0.01%    | -5.39%   | 5         | 10     |
| 2026-04-30 | 95,786     | -2.67%      | +0.96%    | -3.63%   | 3         | 23     |
| 2026-05-01 | 101,101    | +1.82%      | +0.29%    | +1.53%   | 4         | 38     |
| 2026-05-04 | 99,850     | -1.80%      | -0.36%    | -1.43%   | 4         | 53     |

**Cumulative period:** Started $99,627 → ended $99,850 = **+0.22%**
**SPY 30d return (from 05/04 eod):** **+10.71%**
**Period vs SPY:** **-10.71%** (massive underperformance)

### Rolling metrics
- **5-day return (04/28→05/04):** +3.08% (recovered from 04/29 trough)
- **5-day SPY:** +0.39%
- **Daily drawdown breaches (>2.5%):** 04/27 (-4.88%), 04/28 (-5.13%), 04/29 (-5.40%), 04/30 (-2.67%) — **4 of 9 days exceeded the 2.5% daily drawdown budget**
- **Average daily trades:** 22.7 — extremely high for a swing strategy

## Positions at close (2026-05-04)

| Symbol | Side | Qty    | Avg Entry | Current | PnL %  | PnL $   | Mkt Value |
|--------|------|--------|-----------|---------|--------|---------|----------|
| AXTX   | LONG | 313.0  | $46.41    | $46.61  | +0.43% | +$62.60 | $14,589   |
| META   | LONG | 15.48  | $611.73   | $610.46 | -0.21% | -$19.63 | $9,448    |
| PWR    | LONG | 14.69  | $758.48   | $757.38 | -0.15% | -$16.16 | $11,130   |
| SPY    | LONG | 83.14  | $717.52   | $718.03 | +0.07% | +$42.40 | $59,696   |

**Cash:** $4,986.91 (5.0% of equity — at the floor)
**SPY allocation:** 59.8% of equity (cash proxy)
**Active equity allocation:** 35.2% (AXTX 14.6%, META 9.5%, PWR 11.1%)

## Trades on 2026-05-04 (53 total — key events)

| Time  | Symbol | Action | Qty     | Price     | Reason (abbreviated)                                      |
|-------|--------|--------|---------|-----------|-----------------------------------------------------------|
| 14:51 | HCAI   | CLOSE  | 1,492   | $10.69    | Exit-arbiter: -8.78%, lost VWAP, 5 momentum signals      |
| 16:04 | AMZN   | CLOSE  | 65.30   | $270.65   | Arbiter EXIT: fading momentum, below VWAP                 |
| 16:04 | GEV    | CLOSE  | 14.57   | $1,071.49 | Arbiter EXIT: weak momentum, flat trend                   |
| 16:04 | UNH    | CLOSE  | 17.27   | $368.25   | Arbiter EXIT: fading volume, bearish EMA                  |
| ~16:05| LLY    | BUY    | 9.49    | $963.38   | Arbiter BUY 9.1%: strong continuation                     |
| ~16:05| MU     | ADD    | 25.00   | $580.42   | Arbiter INCREASE 28%: pool leader                         |
| ~16:05| NOK    | BUY    | 367.24  | $13.33    | Arbiter BUY 4.9%: strong continuation                     |
| ~16:05| SNDK   | BUY    | 10.10   | $1,246.97 | Arbiter BUY 12.6%: best new candidate                     |
| ~16:06| MU     | CLOSE  | 23.01   | $580.81   | Arbiter EXIT: weak momentum, bearish EMA                  |
| ~16:06| DELL   | BUY    | 57.39   | $210.52   | Arbiter BUY 12.1%: IT sector leader                       |
| ~16:06| FIX    | BUY    | 6.30    | $1,896.50 | Arbiter BUY 11.9%: ai_data_center leader                  |
| ~16:06| GOOGL  | BUY    | 28.68   | $383.51   | Arbiter BUY 11.0%                                         |
| ~16:07| WDC    | BUY    | 24.51   | $445.36   | Arbiter BUY 10.9%: memory peer leader                     |
| ~later| WDC    | CLOSE  | 24.51   | $440.06   | Arbiter EXIT: gap_only, bearish EMA — **same day churn**  |
| ~later| DELL   | CLOSE  | 57.39   | $210.94   | Verifier dust-sweep target=0                              |
| ~later| LLY    | CLOSE  | 13.00   | $963.71   | Verifier dust-sweep target=0                              |
| ~later| COIN   | BUY    | 5.10    | $203.90   | Verifier reconcile                                        |
| ~later| COIN   | CLOSE  | 66.90   | $203.45   | Arbiter EXIT: momentum 0, fading, earnings                |
| ~later| GOOGL  | CLOSE  | 37.96   | $382.77   | Arbiter EXIT: momentum 0, fading                          |
| ~later| FIX    | ADD    | 3.70    | $1,903.71 | Arbiter INCREASE 19%: perfect momentum                    |
| ~later| FIX    | CLOSE  | 10.00   | $1,902.81 | Verifier dust-sweep target=0                              |
| final | AXTX   | BUY    | 313.0   | $46.41    | Arbiter BUY 14.4%: momentum 100, breaking_out             |
| final | META   | BUY    | 15.48   | $611.73   | Arbiter BUY 9.5%: comm services leader                    |
| final | PWR    | BUY    | 14.69   | $758.48   | Arbiter BUY 11.1%: ai_data_center peer leader             |

**(Full analysis appending in next commit)**
