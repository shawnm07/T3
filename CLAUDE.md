# Trading Bot — Context

Autonomous Alpaca paper-trading bot. Goal: beat SPY. **Long US equities only** (no shorts, no crypto — code enforces this). Swing cadence, 4× daily scans on weekdays.

**Account:** PA34KBGT3V7E (~$99K paper equity).

## Pipeline (scan_and_trade.py → orchestrator.py)

Exits run first, then entries:

1. **Market check** — Alpaca clock; skip if closed (unless `--force`)
2. **Macro regime** — `macro.py`: SPY EMA50/200, VIXY proxy, breadth → score [-1,1], regime: `risk_on / neutral / risk_off`. Halt NEW entries if score < -0.55 or VIX spike.
3. **Discovery** — `discovery.py`: held positions + Alpha Vantage movers (gainers/losers/actives) + news-sentiment outliers + TradingView breakouts/squeezes + seed/dynamic watchlists (eligibility only, no score bonus) → pool of ~40-50 candidates
4. **Technicals** — `technicals.py`: RSI, MACD, EMA50/200, ATR, trend/momentum/volatility score per symbol
5. **Fundamentals** — `fundamentals.py`: yfinance → PE, PEG, rev growth, ROE, debt/equity
6. **Sentiment** — `sentiment.py`: Alpaca news API, lexical scoring
7. **Numeric decision** — `decision.py`: weighted blend (macro 15%, technical 35%, fundamental 20%, sentiment 15%, risk 15%). **BUY gate: |combined| ≥ 0.40 AND ≥2 agents agree AND technical > 0**
8. **AI pipeline** — top 5 candidates (numeric ≥ 0.30) sent to:
   - Analysts in parallel (Haiku 4.5): `technical-analyst`, `fundamental-analyst`, `sentiment-analyst`
   - `decision-arbiter` (Opus 4.7): final BUY/PASS per candidate
9. **Portfolio selector** — `portfolio-selector` (Opus 4.7): selects 3-6 positions from held + new pool with target weights + SPY/cash split; no incumbent bias; enforces diversification caps
10. **Risk sizing** — `risk.py`: AI-direct qty/entry with a Python-enforced stop no wider than 1%; AI tighter stops are honored, 0.5% max risk/trade
11. **Rebalance arbitration** — `portfolio-arbiter` (Opus 4.7): grow winners, trim weak (legacy; portfolio-selector is primary)
12. **Earnings gate** — `earnings-gate` (Opus 4.7): within 2-day earnings window → close/trim_50/hold based on confidence floors (day 0-1: ≥0.90 hold; day 2: ≥0.75)
13. **Sector guard** — `sector_guard.py`: max 3/GICS sector, max 3/theme, max 50% theme weight
14. **Execution** — `executor.py`: protected Alpaca orders; AI owns the decision/sizing, while Python's 1% maximum stop-loss distance is a non-contradictory execution guardrail
15. **Portfolio verifier** — `portfolio-verifier` (Sonnet 4.6, non-critical): post-execution reconcile vs Opus targets, proposes corrective trades
16. **Exits** — `_handle_exits()`: technical flip or stall (score < 0.10) → `exit-arbiter` (Opus 4.7, min confidence 0.55 to close)
17. **Notifications** — `telegram_notifier.py`

## Data sources
- **Alpha Vantage** (primary): daily/intraday bars, movers, news sentiment. Key: `ALPHA_VANTAGE_API_KEY`. 75/min, 5 concurrent.
- **yfinance**: fundamentals only (PE, PEG, growth, ROE, debt/equity)
- **Alpaca news API**: sentiment lexical scoring only
- **Twelve Data** (fallback): SPY daily for P&L reporting. Key: `TWELVEDATA_API_KEYS` (800/day)
- **TradingView screener**: volume breakout / Bollinger squeeze (fallback when AV unavailable)
- **Alpaca SDK**: account, positions, orders, clock ONLY — **never bars, charts, or news**

## AI model routing
- `ai.trade_critical_model` (currently `claude-sonnet-4-6`, switchable to `claude-opus-4-7`) — trade-critical: decision-arbiter, portfolio-selector, portfolio-arbiter, exit-arbiter, earnings-gate
- `claude-haiku-4-5-20251001` — analysts: technical-analyst, fundamental-analyst, sentiment-analyst
- `claude-sonnet-4-6` — non-critical: portfolio-verifier

## Key files
```
src/orchestrator.py        # end-to-end pipeline
src/discovery.py           # unified candidate pool builder
src/ai_pipeline.py         # AI arbiter orchestration
src/decision.py            # numeric consensus engine
src/risk.py                # sizing + stops + caps
src/technicals.py          # RSI/MACD/ATR/EMA signals
src/sector_guard.py        # diversification hard caps
scripts/scan_and_trade.py  # intraday entry point (4×/day)
scripts/preclose_decision.py  # ~15:55 ET overnight hold/buy
scripts/premarket_brief.py    # ~8:30 ET macro brief
scripts/eod_report.py         # ~16:15 ET daily P&L vs SPY
scripts/weekly_review.py      # Friday wrap-up
config.yaml                # all tunable parameters
data/journal/              # decisions.jsonl, trades.jsonl
```

## Subagents (.claude/agents/) — for deep research on demand, NOT in autonomous loop
- `decision-arbiter` — final BUY/PASS per candidate, inside the fixed 1% maximum stop-loss guardrail
- `portfolio-selector` — portfolio composition authority, inside the fixed 1% maximum stop-loss guardrail
- `exit-arbiter` — close/reduce authority
- `earnings-gate` — pre-earnings position management
- `portfolio-arbiter` — rebalance (legacy)
- `portfolio-verifier` — post-execution reconcile (non-critical)
- `technical-analyst`, `fundamental-analyst`, `sentiment-analyst`, `macro-analyst` — narrative analysts

## Key config knobs (config.yaml)
- `risk.min_confidence: 0.40` — numeric BUY gate
- `risk.max_positions: 6`
- `risk.initial_entry_cap_pct: 0.15` — new entry size cap
- `risk.max_position_pct: 0.50` — rebalance can grow to this
- `risk.hard_stop_loss_pct: 0.01` — Python-enforced maximum stop distance for every strategy BUY/ADD; AI tighter stops are accepted
- `risk.stop_loss_atr_mult: 2.0`, `take_profit_atr_mult: 4.0` — ATR reference/target knobs
- `risk.max_risk_per_trade_pct: 0.005` — 0.5% equity max risk/trade
- `risk.cash_reserve_pct: 0.05` — 5% idle cash floor
- `macro.bearish_halt_score: -0.55` — halts new entries (not exits)
- `ai.weight: 0.6` — 60% AI / 40% numeric blend
- `ai.max_candidates_per_scan: 5`
- `selector.enabled: true` — unified portfolio selector active
- `earnings.trim_exit_days: 2`, `day_0_1_hold_min_confidence: 0.90`
- `exit_arbiter.min_confidence: 0.55`
- `diversification.max_per_gics_sector: 3`, `max_theme_weight_pct: 0.50`

## Quick commands
```
py dashboard.py                              # status + P&L
py scripts/scan_and_trade.py --dry-run       # simulate next scan
py scripts/scan_and_trade.py --force         # run now (skip hours check)
py scripts/dry_run_selector.py               # test portfolio-selector only
py scripts/premarket_brief.py                # macro brief
py scripts/eod_report.py                     # today vs SPY
```
