# Trading Bot — Context

Autonomous Alpaca paper-trading bot. Goal: beat SPY. **Long US equities only** (no shorts, no crypto — code enforces this). Swing cadence, 6× daily scans on weekdays.

**Account:** PA34KBGT3V7E (~$99K paper equity).

## Pipeline (scan_and_trade.py → orchestrator.py)

Exits run first, then entries:

1. **Market check** — Alpaca clock; skip if closed (unless `--force`)
1a. **Stop-coverage safety net** — `executor.ensure_stop_coverage()`: enumerates open positions, ensures every one has an active sell-stop in the order book at `avg_entry * (1 - hard_stop_loss_pct)`; missing stops are submitted with TIF=GTC (whole-share) or DAY (fractional). Runs BEFORE exits/selector and also at pre-market (before opening-stop guard cancels them for the open auction). This catches HCAI-style failures where the original stop was rejected at entry and the position was naked.
2. **Macro regime** — `macro.py`: SPY EMA50/200, VIXY proxy, breadth → score [-1,1], regime: `risk_on / neutral / risk_off`. Halt NEW entries if score < -0.55 or VIX spike.
3. **Discovery** — `discovery.py`: held positions + Alpha Vantage movers (gainers/losers/actives) + news-sentiment outliers + TradingView breakouts/squeezes + seed/dynamic watchlists (eligibility only, no score bonus) → pool of ~40-50 candidates
4. **Technicals** — `technicals.py`: RSI, MACD, EMA50/200, ATR, trend/momentum/volatility score per symbol
5. **Fundamentals** — `fundamentals.py`: yfinance → PE, PEG, rev growth, ROE, debt/equity
6. **Sentiment** — `sentiment.py`: Alpaca news API, lexical scoring
7. **Numeric decision** — `decision.py`: weighted blend (macro 15%, technical 35%, fundamental 20%, sentiment 15%, risk 15%). **BUY gate: |combined| ≥ 0.40 AND ≥2 agents agree AND technical > 0**
8. **AI pipeline** — top 5 candidates (numeric ≥ 0.30) sent to:
   - Analysts in parallel (Haiku 4.5): `technical-analyst`, `fundamental-analyst`, `sentiment-analyst`
   - `decision-arbiter` (Opus 4.7): final BUY/PASS per candidate
9. **Portfolio selector** — `portfolio-selector` (Opus 4.7): selects 3-6 positions from held + new pool with target weights + SPY/cash split. Slim schema (Phase 0, 2026-05-05): no `candidate_rankings` (per_symbol covers it), no `remaining_upside_score`/`exhaustion_penalty` per symbol, `one_sentence_reason` required only for action ∈ {BUY, INCREASE, EXIT, REDUCE}. Hits a `max_tokens` cap → no retry, Telegram MAX_TOKENS alert, scan skipped. Configured cap 12K (was 32K). Small `selector.incumbent_score_bonus` (default +3) surfaces in `system_state` so the agent applies an incumbent tie-break consistently.
10. **Risk sizing** — `risk.py` + `executor.py`: AI-direct qty/entry. Phase 3 (2026-05-05) ATR-aware protective hard stop: `max(hard_stop_loss_pct=0.01, hard_stop_loss_atr_mult=0.5 * ATR/price)` capped at `hard_stop_loss_pct_ceiling=0.025`. Falls back to the 1% floor when ATR is unavailable. AI tighter stops are honored. 0.5% max risk per trade.
11. **Rebalance arbitration** — Unified rebalance loop (Phase 1a, 2026-05-05) splits into three passes: **Sells → Pre-buy dust-sweep → Buys.** Pre-buy dust-sweep closes off-target held positions BEFORE buys execute, so freed cash funds same-scan entries. Honors the same fresh-entry guard (Phase 1b): never dust-sweep a position opened today that isn't already losing > 0.5%. (`portfolio-arbiter` legacy path remains for the old non-selector code path.)
12. **Earnings gate** — `earnings-gate` (Opus 4.7): within 2-day earnings window → close/trim_50/hold based on confidence floors (day 0-1: ≥0.90 hold; day 2: ≥0.75)
13. **Sector guard** — `sector_guard.py`: max 3/GICS sector, max 3/theme, max 50% theme weight
14. **Execution** — `executor.py`: protected Alpaca orders. The protective stop attached at entry uses ATR-aware sizing (Phase 3). If the stop is rejected by Alpaca (entry slipped below stop price — HCAI 2026-05-01 failure mode) and `risk.close_on_stop_failure` is true (default), the executor immediately market-sells the entry rather than carrying it naked. Cash-capped buys < 40% of target are DROPPED rather than stubbed (Phase 2b, 2026-05-05) — knob `cash.cap_drop_threshold_pct: 0.40`.
15. **Portfolio verifier** — `portfolio-verifier` (Sonnet 4.6, non-critical): post-execution reconcile vs Opus targets, proposes corrective trades. Same fresh-entry guard as the pre-buy dust-sweep (Phase 1b).
16. **Exits** — `_handle_exits()`: technical flip or stall (score < 0.10) → `exit-arbiter` (Opus 4.7, min confidence 0.55 to close). Phase 4a (2026-05-05): opinion-based EXIT signals require a 30-min consecutive-confirmation buffer (`exit_arbiter.confirmation_minutes`); deterministic stop-breach / earnings-window / macro-halt / material-loss bypass it. Phase 4b: `action=reduce` triggers a 50% partial sell (`exit_arbiter.reduce_trim_fraction`) instead of deferring to the rebalance arbiter.
16a. **Idle-cash SPY auto-park** — Phase 2a (2026-05-05): after the verifier completes, any cash above `cash_reserve_pct` is swept into SPY automatically (`_sweep_cash_to_proxy`), so capital isn't sitting flat while the index rallies. Knob `cash.idle_park_min_usd: 1000`.
17. **Notifications** — `telegram_notifier.py`. Telegram alert fires on selector `max_tokens` failures (Phase 0) so the user knows immediately when a scan was skipped.

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
scripts/scan_and_trade.py  # intraday entry point (6×/day)
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
- `risk.hard_stop_loss_pct: 0.01` — floor of the protective stop distance
- `risk.hard_stop_loss_atr_mult: 0.5` — ATR multiplier for the protective stop floor (Phase 3, 2026-05-05)
- `risk.hard_stop_loss_pct_ceiling: 0.025` — ceiling of the ATR-aware stop (2.5% max)
- `risk.close_on_stop_failure: true` — when the protective stop order is rejected at entry (e.g. price already below stop), immediately flatten rather than carry naked exposure
- `risk.stop_loss_atr_mult: 2.0`, `take_profit_atr_mult: 4.0` — ATR reference/target knobs (position sizing, separate from protective stop)
- `risk.max_risk_per_trade_pct: 0.005` — 0.5% equity max risk/trade
- `risk.cash_reserve_pct: 0.05` — 5% idle cash floor
- `cash.cap_drop_threshold_pct: 0.40` — drop a buy if cash-cap shrinks it below this fraction of target (Phase 2b)
- `cash.idle_park_min_usd: 1000` — minimum idle dollars before auto-parking into SPY at end of scan (Phase 2a)
- `macro.bearish_halt_score: -0.55` — halts new entries (not exits)
- `ai.weight: 0.6` — 60% AI / 40% numeric blend
- `ai.max_candidates_per_scan: 5`
- `ai.max_tokens_per_agent.portfolio-selector: 12000` — selector output cap (Phase 0); hitting it skips the scan with a Telegram alert, no retry
- `selector.enabled: true` — unified portfolio selector active
- `selector.incumbent_score_bonus: 3` — tie-break nudge for held positions (Phase 1c)
- `portfolio_verifier.fresh_entry_loss_floor_pct: -0.005` — block dust-sweep on same-day positions above this loss threshold (Phase 1b)
- `exit_arbiter.min_confidence: 0.55`
- `exit_arbiter.confirmation_buffer_enabled: true`, `confirmation_minutes: 30`, `confirmation_buffer_loss_floor_pct: -0.015` — 30-min hold confirmation buffer (Phase 4a)
- `exit_arbiter.reduce_trim_fraction: 0.5` — partial-sell fraction on AI `reduce` action (Phase 4b)
- `earnings.trim_exit_days: 2`, `day_0_1_hold_min_confidence: 0.90`
- `preclose.rsi_overbought_cap: 78`, `rsi_extreme_cap: 85`, `rsi_leader_override: true`, `rsi_macro_floor: 0.20` — tiered preclose RSI gate (Phase 5)
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
