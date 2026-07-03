# Post-Mortem 2026-07-03

## Data availability

| Source | Status |
|---|---|
| `data/research/2026-07-03_eod.json` | **MISSING** — no scan ran today |
| Last EOD snapshot | `2026-05-04_eod.json` |
| Data gap | **2026-05-05 → 2026-07-03 (59 calendar days, ~41 trading days)** — bot has not run since May 4 |
| Trade journal | `data/journal/trades.jsonl` — last entry 2026-05-04T19:55 UTC |
| Config baseline | `config.yaml` current |

> **Note:** All analysis below is based on the last active trading day (2026-05-04), which was the final session before the bot went silent. This post-mortem also covers rolling context from the full available history (Apr 22 – May 4).

---

## Performance today (portfolio vs SPY, from eod.json)

No eod.json for 2026-07-03. Using last available snapshot:

### Last active day: 2026-05-04
| Metric | Value |
|---|---|
| Portfolio daily return | **-1.80%** |
| SPY daily | -0.36% |
| Portfolio vs SPY (day) | **-1.44%** underperform |
| Closing equity | $99,849.69 |
| Trades executed | **53** (extreme churn) |

### Rolling performance (all available data: Apr 22 – May 4)
| Date | Portfolio | SPY daily | Portfolio daily |
|---|---|---|---|
| 2026-04-22 | $99,627 | +1.01% | 0.00% |
| 2026-04-23 | $101,208 | -0.39% | **+1.56%** |
| 2026-04-24 | $99,343 | +0.77% | -0.81% |
| 2026-04-27 | $96,448 | +0.17% | **-4.88%** |
| 2026-04-28 | $96,867 | -0.49% | -5.13%* |
| 2026-04-29 | $93,999 | -0.01% | **-5.40%** |
| 2026-04-30 | $95,786 | +0.96% | -2.67% |
| 2026-05-01 | $101,101 | +0.29% | **+1.82%** |
| 2026-05-04 | $99,850 | -0.36% | -1.80% |

*Apr 28 equity increased vs Apr 27 despite -5.13% daily_return — likely a snapshot/equity-calc artifact.

**Period cumulative (Apr 22 → May 4):** Portfolio +0.22% vs SPY cumulative +1.95%  
**Period_vs_SPY (from eod):** **-10.71%** (SPY 30d return shown in last snapshot: +10.71%)

---

## Positions at close — 2026-05-04

| Symbol | Side | Qty | Avg Entry | Last Price | P&L% |
|---|---|---|---|---|---|
| AXTX | LONG | 313.0 | $46.41 | $46.61 | **+0.43%** |
| META | LONG | 15.48 | $611.73 | $610.46 | -0.21% |
| PWR | LONG | 14.69 | $758.48 | $757.38 | -0.15% |
| SPY (proxy) | LONG | 83.14 | $717.52 | $718.03 | **+0.07%** |

All four positions flat-to-minor. Equity drag came from intraday churn losses (53 trade events).

---

## Trades 2026-05-04 (summary — 53 events across 6 scans)

| Scan | Time (UTC) | Portfolio selected | Key actions |
|---|---|---|---|
| 1 | 15:13 | AMZN, GEV, COIN, MU, UNH | Exit HCAI (-8.78%), buy AMZN/GEV/COIN/MU/UNH |
| 2 | 15:18 | AMZN, MU, META, UNH, COIN, BAND | Portfolio partially rotated |
| 3 | 16:05 | MU, COIN, SNDK, LLY, NOK, V | Exit AMZN/GEV/UNH; buy LLY/SNDK/NOK |
| 4 | 17:04 | FIX, DELL, WDC, GOOGL, COIN, LLY | Exit MU/SNDK/NOK; buy FIX/DELL/WDC/GOOGL |
| 5 | 18:05 | FIX, COIN, PWR, GOOGL, RBLX | Exit DELL/LLY/WDC; increase FIX→19%; verifier buys GOOGL |
| 6 | 19:08 | AXTX, SNDK, PWR, LLY, META, SOXS | Exit COIN/FIX/GOOGL; buy AXTX/META; keep PWR |

Notable individual trades:
| Symbol | Entry | Exit | Hold | P&L | Verdict |
|---|---|---|---|---|---|
| HCAI | $11.84 | $10.69 | overnight | **-8.78%** | catastrophic — open from prior day |
| WDC | $445.36 | $440.06 | ~2h | -1.19% | premature entry, exited same day |
| GOOGL | $383.51+$384.43 | $382.77 | ~2h | ~-0.35% | verifier filled, arbiter exited next scan |
| FIX | $1,896.50 | $1,902.81 | ~2h | +0.33% | only intraday winner |
| MU | $580.42 | $580.81 | ~1.5h | +0.07% | flat |
| AXTX | $46.41 | held | — | +0.43% | held at close |

---

## (Full analysis appending in next commit)
