# Post-Mortem 2026-06-03

## Data availability

| Source | Status |
|--------|--------|
| `data/research/2026-06-03_eod.json` | **MISSING** — no market activity logged for today |
| Most recent EOD snapshot | `2026-05-04_eod.json` (last traded session) |
| Scan files (today) | None — post-mortem covers last logged session (2026-05-04) |
| `data/journal/trades.jsonl` | Present — 204 records through 2026-05-04 |
| `data/journal/decisions.jsonl` | Present |
| `config.yaml` | Present |

**Note:** Today (2026-06-03) has no market data. This post-mortem covers the last recorded trading session (2026-05-04) and the 30-day rolling window through that date. The system produced no EOD logs between 2026-05-05 and 2026-06-03, indicating the bot has not run or traded since May 4.

---

## Performance today (last session: 2026-05-04)

| Metric | Value |
|--------|-------|
| Portfolio daily return | **-1.80%** |
| SPY daily return | -0.36% |
| Daily alpha | **-1.43%** |
| Equity (EOD) | $99,849 |
| Positions held | 4 (incl. 1 SPY cash-proxy) |
| Trade events | 53 |
| Positions closed | 11 |
| AI orders submitted | 15 |
| Wash-trade recoveries | 3 |

### Rolling window (9 sessions: 2026-04-22 → 2026-05-04)

| Date | Portfolio | SPY | Alpha |
|------|-----------|-----|-------|
| 2026-04-22 | +0.00% | +1.01% | -1.01% |
| 2026-04-23 | +1.56% | -0.39% | +1.95% |
| 2026-04-24 | -0.81% | +0.77% | -1.59% |
| 2026-04-27 | -4.88% | +0.17% | -5.05% |
| 2026-04-28 | -5.13% | -0.49% | -4.65% |
| 2026-04-29 | -5.40% | -0.01% | -5.39% |
| 2026-04-30 | -2.67% | +0.96% | -3.63% |
| 2026-05-01 | +1.82% | +0.29% | +1.53% |
| 2026-05-04 | -1.80% | -0.36% | -1.43% |
| **Cumulative** | **-16.31%** | **+1.95%** | **-18.26%** |

Beat SPY: **2 / 9 sessions (22%)** — well below target.

---

## Positions at close (2026-05-04 EOD)

| Symbol | Side | Qty | Avg Entry | Current | P&L% | Mkt Value | % Equity |
|--------|------|-----|-----------|---------|------|-----------|----------|
| AXTX | Long | 313.0 | $46.41 | $46.61 | +0.43% | $14,589 | 14.6% |
| META | Long | 15.48 | $611.73 | $610.46 | -0.21% | $9,448 | 9.5% |
| PWR | Long | 14.69 | $758.48 | $757.38 | -0.15% | $11,130 | 11.1% |
| **SPY** | Long | 83.14 | $717.52 | $718.03 | +0.07% | $59,696 | **59.8%** |

Cash: $4,987 (5.0% — at floor). Total invested: $94,863.
**Critical: 59.8% of equity is parked in SPY overnight via the cash-proxy. The bot is effectively indexing 60% of the portfolio.**

P&L computed from `avg_entry` and `current_price` per snapshot (Alpaca `unrealized_plpc` disregarded).

---

## Trades today (2026-05-04) — key events

| Time (UTC) | Event | Symbol | Side | Qty | Price | Note |
|------------|-------|--------|------|-----|-------|------|
| 14:51 | CLOSE | HCAI | sell | 1,492 | $10.69 | AI exit conf=0.72, -8.78% loss |
| 16:04 | CLOSE | AMZN | sell | 65.3 | $270.65 | Arbiter: fading momentum |
| 16:04 | CLOSE | GEV | sell | 14.6 | $1,071.49 | Arbiter: weak momentum |
| 16:04 | CLOSE | UNH | sell | 17.3 | $368.25 | Arbiter: exiting to fund LLY |
| 16:04 | AI BUY | LLY | buy | 9.5 | ~$963 | 9.1% target |
| 16:04 | AI BUY | MU | add | 25.0 | ~$580 | 28.0% target (doubled) |
| 16:04 | AI BUY | NOK | buy | 367 | — | 4.9% target |
| 16:04 | AI BUY | SNDK | buy | 10.1 | $1,247 | Stop hit at $1,237.52 in 6 min |
| 17:04 | CLOSE | MU | sell | 23.0 | $580.81 | Arbiter: flat momentum (1 hr after doubling) |
| 17:04 | AI BUY | DELL | buy | 57.4 | ~$210 | 12.1% target |
| 17:04 | WASH | LLY | — | — | — | Wash-trade recovery triggered |
| 18:05 | CLOSE | DELL | sell | 57.4 | $210.94 | Verifier dust-sweep |
| 18:05 | CLOSE | LLY | sell | 13.0 | $963.71 | Verifier dust-sweep |
| 18:05 | AI BUY | FIX | add | 3.7 | — | INCREASE → 19% |
| 19:08 | CLOSE | COIN | sell | 66.9 | $203.45 | Arbiter: fading |
| 19:08 | CLOSE | GOOGL | sell | 37.96 | $382.77 | Arbiter: fading |
| 19:08 | CLOSE | FIX | sell | 10.0 | $1,902.81 | Verifier dust-sweep |
| 19:08 | AI BUY | AXTX | buy | 313 | $46.41 | Final portfolio entry |
| 19:08 | AI BUY | META | buy | 15.5 | $611.73 | Final portfolio entry |
| 19:08 | AI BUY | PWR | buy | 14.7 | $758.48 | Final portfolio entry |
| ~19:55 | PRECLOSE | SPY | buy_proxy | — | — | $59,654 parked in SPY |

---

## (Full analysis appending in next commit)
