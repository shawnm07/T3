# Daily Review — 2026-05-22

> **No new data to review — third consecutive no-data report.** Today is Fri 2026-05-22 (America/Phoenix). The most recent snapshots in `data/research/` still end on **Mon 2026-05-04**. There are no scan files, no `_eod.json`, and no `trades.jsonl` / `decisions.jsonl` events for any session from **2026-05-05 (Tue)** through **2026-05-22 (Fri)** — a **17-calendar-day, ~14-trading-day gap**. The 5/4 session has already been covered by `2026-05-05_daily_review.md` and is not re-graded here. Per the hard rules ("If snapshots are missing… write a short report saying so and exit cleanly. Do NOT invent data"), no scoreboard, no per-trade ledger, and no overnight grading is produced.

## Evidence

| Source | Newest entry on disk | Path |
|---|---|---|
| `_eod.json` | `2026-05-04_eod.json` | `data/research/2026-05-04_eod.json` |
| Last preclose snapshot | `20260504T195545_preclose.json` | `data/research/` |
| Last intraday scan | `20260504T190848_scan.json` | `data/research/` |
| Last crypto scan | `20260428T190557_crypto_scan.json` (4/28) | `data/research/` |
| Last `_daily_review.md` | `2026-05-13_daily_review.md` (no-data) | `data/research/` |
| `trades.jsonl` last event | `2026-05-04T19:55:03Z` exit_learning_metrics (COIN) | `data/journal/trades.jsonl` |
| `decisions.jsonl` last event | `2026-05-04T20:15:04Z` eod_report | `data/journal/decisions.jsonl` |

Verification:
- `grep '"ts": "2026-05-0[5-9]"|"ts": "2026-05-1[0-9]"|"ts": "2026-05-2[0-2]"'` against both journal files → **0 matches**.
- No `data/research/20260505T*` … `20260522T*` files of any kind (scan, preclose, crypto).
- No `2026-05-05_eod.json` through `2026-05-22_eod.json`.
- `_daily_review.md` series itself has a widening gap: 5/5 → 5/7 → 5/13 → 5/22. The intervening reviews (5/6, 5/8, 5/11, 5/12, 5/14–5/21) were never written, presumably because nothing ran to generate them either.

## The gap is now a primary operational issue, not a strategy issue

- **5/7 review (gap = 2 trading days)** read as a scheduler hiccup; ambiguous between "didn't run", "ran but didn't commit", or "running in a different working tree".
- **5/13 review (gap = ~6 trading days)** flagged the ambiguity could no longer be explained as a scheduler blip.
- **Today (gap = ~14 trading days, ~3 calendar weeks)** removes the remaining benign explanations. Whatever broke after the 2026-05-04 EOD has not been fixed, or the fix is not landing artifacts into the path this review reads from.

Possible root causes I still cannot distinguish from the directory alone (unchanged from the 5/13 report):

1. `scripts/scan_and_trade.py` (and `preclose_decision.py`, `eod_report.py`) are no longer being invoked — cron/scheduler disabled or silently failing since 5/4.
2. The bot is running but writing `data/research/` / `data/journal/` to a different filesystem/branch/remote, and the committed snapshot is stale.
3. The live Alpaca paper account is fine but this review's harness (no Alpaca credentials by design) only sees committed artifacts. I cannot rule out live activity exists; only that nothing has been committed for ~3 weeks.

The 5/13 report already flagged this. **The fact that we are now writing the same observation a third time means the prior reports' operational ask has not been resolved.** No strategy diagnosis is possible until this is fixed.

## Open strategy proposals from 5/5 — still pending, still untested

The 5/5 review tabled 8 proposals (selector inertia / Jaccard floor, earnings-flag stickiness, min-hold timer, preclose close-fill verifier, intraday turnover cap, SPY-proxy chaos-day rule, red-tape BUY gate, sticky-portfolio cadence). All eight were carried forward unchanged on 5/7 and again on 5/13.

They remain open and **completely untested by live data** because no new sessions have produced evidence either way. Re-stating them here adds no information; the 5/5 review is the authoritative source.

## Proposed strategy changes from today's data

**None.** There is no "today's data." The only action item is operational, not strategic — exactly as on 5/7 and 5/13:

> **Confirm the bot is actually running and writing snapshots into this repo.** Until that is resolved, every strategy proposal sits in limbo because nothing can falsify or validate it.

I want to be explicit about the second-order effect: the bot's own `exit_learning_metrics` and `trade_learning_resolved` machinery (visible at the tail of `trades.jsonl` / `decisions.jsonl`) is also frozen at 5/4. Whatever post-trade learning loop those records were meant to feed has been starved for three weeks too.

## Backtests Run

None — would have required either fresh session data or live API access. This report is bounded to a "no data" verdict.

## What would change this report

The instant `data/research/` contains any `20260505T*` … `20260522T*` snapshot or `2026-05-05_eod.json` … `2026-05-22_eod.json`, a real review can be written. Without that, three weeks of consecutive "no-data" reviews is the only honest output.
