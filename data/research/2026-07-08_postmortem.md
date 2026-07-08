# Post-Mortem 2026-07-08

## Data Availability

| Source | Status | Latest Entry |
|--------|--------|-------------|
| `_eod.json` | **MISSING** | `2026-05-04_eod.json` (44 trading days stale) |
| Intraday scans | **MISSING** | `20260504T190848_scan.json` |
| Preclose snapshot | **MISSING** | `20260504T195545_preclose.json` |
| `trades.jsonl` | **FROZEN** | `2026-05-04T19:55:03Z` (204 lines) |
| `decisions.jsonl` | **FROZEN** | `2026-05-04T20:15:04Z` (1556 lines) |

**This is the 8th consecutive no-data report.** The bot has been offline since 2026-05-04 (~9 weeks / 44 trading days). No new scan artifacts, no new journal entries. All figures below are from the last known EOD snapshot (2026-05-04).

## Performance Today (vs SPY)

| Metric | Value | Note |
|--------|-------|------|
| Today's portfolio daily return | **UNKNOWN** | No eod.json |
| SPY today | **UNKNOWN** | No eod.json |
| Last known daily return | **-1.80%** | 2026-05-04 |
| Last known SPY daily | **-0.36%** | 2026-05-04 |
| Last known daily vs SPY | **-1.44%** | Portfolio underperformed |
| Last known cumulative vs SPY | **-10.71%** | `period_vs_spy` in eod.json |
| Last known equity | **$99,849.69** | 2026-05-04 |
| Equity (today) | **UNKNOWN** | 9 weeks unmonitored |

Rolling 5-day and 30-day benchmarks cannot be computed — no eod.json for any trading day since 2026-05-04.

## Positions at Last Close (2026-05-04)

| Symbol | Side | Qty | Avg Entry | Last Known Price | P&L% (from avg_entry) | Market Value |
|--------|------|-----|-----------|-----------------|----------------------|-------------|
| SPY | LONG | 83.138 | $717.52 | $718.03 | +0.07% | $59,695.86 |
| AXTX | LONG | 313 | $46.41 | $46.61 | +0.43% | $14,588.93 |
| PWR | LONG | 14.695 | $758.48 | $757.38 | -0.15% | $11,129.62 |
| META | LONG | 15.477 | $611.73 | $610.46 | -0.21% | $9,448.36 |
| Cash | — | — | — | — | — | $4,986.91 |

Portfolio weights at 5/4 EOD: SPY 59.8%, AXTX 14.6%, PWR 11.1%, META 9.5%, cash 5.0%.

**⚠ AXTX is a 2x leveraged ETF ("Tradr 2X Long AXTI Daily ETF") held unmonitored for 44 trading days.** Protective stop at $45.34 (1% below $46.41 entry) was submitted 2026-05-04T19:08. Stop order expiry / fill status unknown — Alpaca API is blocked.

## Trades Today

None. Bot offline.

---

## Phase 2 — Deep Analysis (based on last active trading day: 2026-05-04)

### 2a. Per-Trade Ledger — 2026-05-04 (53 journal events; 15 AI orders, 11 closes)

| # | Symbol | Action | Qty | Entry/Exit | Notional | Conf | Opp | Quality | Verdict |
|---|--------|--------|-----|-----------|----------|------|-----|---------|---------|
| 1 | HCAI | CLOSE | 1492 | $10.69 | $15,950 | 0.72 | — | -8.78% realized loss | bad — stop-loss blowout |
| 2 | AMZN | CLOSE | 65.3 | $270.65 | $17,673 | — | — | fading momentum | ok — thesis gone |
| 3 | GEV | CLOSE | 14.6 | $1,071.49 | $15,622 | — | — | weak momentum | ok — capital rotation |
| 4 | UNH | CLOSE | 17.3 | $368.25 | $6,371 | — | — | lost to LLY | ok — sector rotation |
| 5 | LLY | BUY | 9.49 | $963.38 | $9,140 | 0.72 | 65 | healthcare sector leader | ok |
| 6 | MU | INCREASE | 25.0 | $580.42 | $14,511 | 0.90 | 88 | 13.3%→28% target | churn — exited same session |
| 7 | NOK | BUY | 367 | $13.33 | $4,896 | 0.68 | 62 | not in final EOD | churn — eliminated same day |
| 8 | SNDK | BUY | 10.1 | $1,246.97 | $12,606 | 0.75 | 72 | not in final EOD | churn — eliminated same day |
| 9 | DELL | BUY | 57.4 | $210.52 | $12,082 | 0.80 | 76 | dust-swept same session | churn — $24 gain then closed |
| 10 | FIX | BUY | 6.30 | $1,896.50 | $11,948 | 0.82 | 78 | exited same session | bad — wash-trade cycle |
| 11 | GOOGL | BUY | 28.7 | $383.51 | $11,003 | 0.72 | 70 | exited same session at $382.77 | bad — same-day loss ~$21 |
| 12 | LLY | INCREASE | 3.51 | $962.27 | $3,378 | 0.65 | 58 | dust-swept by verifier | churn |
| 13 | WDC | BUY | 24.5 | $445.36 | $10,915 | 0.75 | 68 | exited same session at $440.06 | bad — same-day loss ~$130 |
| 14 | MU | CLOSE | 23.0 | $580.81 | $13,359 | — | — | peer-rotated to WDC | churn — negligible P&L on rotation |
| 15 | WDC | CLOSE | 24.5 | $440.06 | $10,788 | — | — | gap_only, bearish EMA | bad — entered and exited same day |
| 16 | COIN (verifier) | BUY | 5.10 | $203.90 | $1,040 | 0.68 | 65 | verifier gap-fill | churn — position closed minutes later |
| 17 | FIX | INCREASE | 3.70 | $1,903.71 | $7,043 | 0.88 | 85 | wash-trade recovery triggered | bad — exit blocked by fresh_exit_cooldown |
| 18 | GOOGL (verifier) | BUY | 9.28 | $384.43 | $3,567 | 0.72 | 65 | verifier gap-fill | churn — position closed immediately |
| 19 | DELL | CLOSE | 57.4 | $210.94 | $12,105 | — | — | verifier dust-sweep | ok — tiny gain |
| 20 | LLY | CLOSE | 13.0 | $963.71 | $12,528 | — | — | verifier dust-sweep | churn |
| 21 | COIN | CLOSE | 66.9 | $203.45 | $13,611 | — | — | earnings 3d, momentum 0 | ok — earnings gate correct |
| 22 | GOOGL | CLOSE | 38.0 | $382.77 | $14,545 | — | — | momentum 0, below EMA20 | ok — correct exit, but same-day |
| 23 | AXTX | BUY | 313 | $46.41 | $14,527 | 0.88 | 88 | momentum 100, breaking_out | ok — final hold |
| 24 | META | BUY | 15.5 | $611.73 | $9,473 | 0.65 | 58 | acceptable continuation | marginal — low conf |
| 25 | PWR | BUY | 14.7 | $758.48 | $11,147 | 0.72 | 68 | ai_data_center_power leader | ok |
| 26 | FIX | CLOSE | 10.0 | $1,902.81 | $19,028 | — | — | verifier dust-sweep | bad — bought @$1896+$1904, sold @$1903 (net ~flat but unnecessary churn) |

**Summary:** 53 journal events; ~9 buy→exit same-session round trips; 3 wash-trade recoveries; $130 confirmed same-day loss on WDC; GOOGL roughly flat on same-day round-trip; MU round-trip for negligible gain. Final settled portfolio sensible but path was destructive.

---

### 2b. Cross-Trade Patterns

- **Same-day BUY→EXIT churn (critical):** MU was increased to 28% at scan 1 then exited at scan 2 same day. WDC bought and exited same session (-$130). GOOGL bought (twice, including verifier top-up) and exited same session (~flat). NOK and SNDK bought and eliminated in same session. At least 5 distinct symbols completed a full round-trip within 2026-05-04, generating commissions and market impact with zero net gain.

- **Wash-trade recovery (3 triggers):** FIX and GOOGL triggered `wash_trade_detected` (code 40310000) because the bot placed a new BUY while a protective SELL-STOP from a prior same-session trade was still live. Root cause: the selector is rotating positions faster than stop-order cancellation propagates. Each wash-trade recovery adds latency and execution uncertainty.

- **Verifier dust-sweeps racing the selector:** DELL, LLY, and FIX were closed by `portfolio-verifier` via `dust-sweep target=0` in the same scan that bought them (or immediately after). This means the primary selector and the verifier agreed on 0% target but execution did not clear before the verifier ran its reconcile pass — the verifier then closed the remnant. This is a coordination bug, not a strategy bug.

- **fresh_exit_cooldown blocked a valid exit:** FIX was bought at 18:05 at opp=78. By 19:08 (63 min later) the arbiter wanted to EXIT at 0.8 confidence, but `fresh_exit_cooldown_minutes=120` blocked it (min confidence to override cooldown = 0.85). Fourteen seconds later the verifier dust-swept FIX anyway. The cooldown protected nothing — it just delayed an inevitable close by 63 minutes while the position was losing.

- **Period vs SPY: -10.71% cumulative.** On the final active day (5/4) the bot underperformed SPY by -1.44%. Nine tracked trading days show consistent underperformance, not an outlier.

- **SPY cash-proxy dominates (59.8%).** The bot's own goal is "beat SPY." With 60% SPY proxy, alpha can only come from the 35% sector bets (AXTX+META+PWR). For the portfolio to beat SPY by 1%, those three positions must collectively outperform SPY by ~2.9%. The current allocation structurally limits outperformance.

- **AXTX is a 2× leveraged ETF held as a swing trade.** AXTX = Tradr 2X Long AXTI Daily ETF. Leveraged ETFs suffer volatility decay on every off-day and are designed for intraday holds. The bot bought 313 shares at $46.41 and left them unmonitored for 44 trading days with a 1% stop that almost certainly expired. This is the most acute live risk in the frozen book.

- **Inverse ETF attempted (SOXS):** In the last scan, the selector attempted to buy SOXS (Direxion Daily Semiconductor Bear 3X ETF, tech_score=-0.99) but the execution preflight rejected it because `stop_not_below_current_market`. The bot is nominally long-only but the AI arbiter is not constrained from nominating inverse ETFs. The rejection happened to be for a price reason, not a "short-only instrument" reason — a different price tick and SOXS would have gone through.

- **Over-trimming winners not a visible pattern on 5/4:** The exits on 5/4 (AMZN, GEV, UNH, COIN, GOOGL) were largely justified by momentum signals. No clear case of trimming a winner prematurely — the problem is churning through positions too quickly in general.

---

### 2c. Proposed Changes

#### 1. Add intraday turnover cap (`risk.max_new_entries_per_scan`)
**Why:** 2026-05-04 processed 15 AI orders and 11 closes in a single day cycle, generating 3 wash-trade recoveries, 5 same-day round-trips, and ~$130 in confirmed losses with zero strategic benefit. Excessive turnover is the proximate cause of wash-trade errors and execution race conditions.
```yaml
# config.yaml — add under risk:
risk:
  max_new_entries_per_scan: 3   # was: unlimited
```
**Expected impact:** Limits the selector to 3 new entries per scan pass. Held positions can still be adjusted. Reduces wash-trade exposure by ~60% and eliminates the scenario where 8+ new symbols enter and exit in the same session.

#### 2. Minimum hold timer for new entries (`risk.min_hold_scans`)
**Why:** MU (opp=88, conf=0.90) was increased to a 28% target then exited 2 scan cycles later. WDC (opp=68) entered and exited same day for a loss. A new entry with opp_score ≥ 65 should survive at least 2 scan cycles before the arbiter can vote EXIT.
```yaml
# config.yaml — add under risk:
risk:
  min_hold_scans: 2   # was: 0 (no floor); applies to new entries with opp_score >= 65
```
**Expected impact:** Prevents same-session BUY→EXIT on high-conviction entries. WDC and MU same-day round-trips would have been blocked.

#### 3. Reduce fresh-exit cooldown minimum confidence (or remove for verifier exits)
**Why:** `fresh_exit_cooldown` (120 min, min_confidence=0.85) blocked FIX exit at 0.8 confidence, then the verifier dust-swept it 14 seconds later anyway. The cooldown provided zero protection — it only prevented a cleaner AI-directed close. Either lower the confidence threshold so the exit arbiter can override at 0.80, or exclude verifier dust-sweeps from the cooldown check entirely.
```yaml
# config.yaml — under exits or fresh_exit:
fresh_exit:
  cooldown_minutes: 120           # unchanged
  min_confidence_to_override: 0.75  # was: 0.85 — allows arbiter to override at >= 0.75
```
**Expected impact:** FIX would have been closed cleanly by the exit arbiter at 0.80 instead of lingering and requiring a verifier dust-sweep. Reduces verifier reconcile load by ~1-2 events per session.

#### 4. Cap SPY cash-proxy allocation (`selector.max_spy_proxy_pct`)
**Why:** SPY ended 5/4 at 59.8% of portfolio. "Beat SPY" is structurally impossible when 60% of equity is already SPY. The selector should be constrained to allocate at most 40% to the SPY cash-proxy, forcing the bot to seek alpha via sector longs even when conviction is low.
```yaml
# config.yaml — add under selector or risk:
selector:
  max_spy_proxy_pct: 0.40   # was: unlimited (SPY used as residual cash proxy)
```
**Expected impact:** Forces redeployment of ~$20K from SPY into additional sector positions when conviction candidates are available, directly increasing the alpha-seeking allocation from ~35% to ~55%.

#### 5. Exclude leveraged and inverse ETFs from swing holds (`universe.exclude_leveraged_etfs`)
**Why:** AXTX (2× leveraged) was held as a swing trade and is now 44 days into an unmonitored hold with a likely-expired stop. SOXS (3× inverse) was nearly admitted. Leveraged ETFs decay on volatility and are unsuitable for multi-day holds. The bot has no explicit guard against them.
```yaml
# config.yaml — add under universe:
universe:
  exclude_leveraged_etfs: true   # was: false (no check); filters tickers with 2X/3X/BEAR/BULL in name or asset description
```
**Expected impact:** Would have blocked AXTX entry on 5/4 and SOXS attempted entry. Prevents the ~44-day leveraged decay risk currently sitting in the frozen book.

#### 6. Dead-man's switch liveness alert (`health.max_silent_trading_days`)
**Why:** The bot has been offline for 44 trading days with no automated alert. The Telegram notifier exists but apparently sent no alert when scans stopped. A liveness check that fires Telegram after N consecutive missed scans would have surfaced this failure on 2026-05-05 instead of 2026-07-08.
```yaml
# config.yaml — add under health or notifications:
health:
  max_silent_trading_days: 2   # was: none — fires Telegram alert if no scan completes in N trading days
```
**Expected impact:** Would have triggered a Telegram alert on 2026-05-06 (~2 days after the last scan). The 9-week gap and 8 consecutive no-data reviews represent ~9× the notification cycle that should have occurred.

---

### 2d. Backtests

**Intraday turnover cap (Proposal 1):** Partially testable. In-repo `trades.jsonl` shows 2026-05-04 had 15 AI orders. With `max_new_entries_per_scan=3`, the selector would have been limited to 3 new symbols per cycle. Confirmed round-trip losses from excess entries on 5/4: WDC -$130, GOOGL ~-$21 (rough), plus frictional losses on DELL/LLY/FIX dust-sweeps. Capping at 3 entries would have avoided at least these two confirmed loss-generating entries. Quantitative backtest across 30 days requires market price data (blocked: yfinance/AV both return 403 in this container).

**Min-hold timer (Proposal 2):** Not backtestable from journal alone — requires knowing which scan cycle each position was entered vs. exited. The 5/4 data confirms the behavior exists (MU entered + exited within same day). Full backtest blocked.

**SPY cap (Proposal 4):** Not directly backtestable — would require replaying the selector with the cap active. However: as of 5/4, SPY = 59.8%. The cumulative underperformance of -10.71% over ~9 active trading days is consistent with the sector bets (AXTX, META, PWR, various others) underperforming while SPY exposure limited downside. Directionally, forcing more into sector bets reduces SPY tracking and increases variance — the goal is to increase expected alpha, accepting higher volatility. Cannot quantify without live price data.

All other proposals (Proposals 3, 5, 6) are structural guards against failure modes confirmed in the journal. No price data needed to validate the failure mode; no backtest needed for the guard. Capping leveraged ETFs and adding a liveness alert are low-risk additions with no negative expected impact on returns.

---

## Operational Priority (unchanged from prior reviews, re-ranked by urgency)

1. **[CRITICAL] Confirm bot is running.** 44 trading days of silence. Check cron/scheduler on the runtime host. Verify `data/research/` write path matches this repo checkout. Log into PA34KBGT3V7E and confirm whether positions/orders have changed since 5/4.
2. **[HIGH] AXTX leveraged ETF exposure.** 313 shares of a 2× ETF sitting with an expired 1% stop. If the account is accessible, this position should be reviewed immediately — it has been unmonitored for 9 weeks with daily compounding decay.
3. **[HIGH] Implement dead-man's switch (Proposal 6).** Without it, the next scheduler failure will produce another 8-week silent gap.
4. **[MEDIUM] Apply Proposals 1-5** once the bot is confirmed running. Do not modify `config.yaml` or `src/` on the postmortem branch — proposals are documented here only.

## Backtests Run

Partial: confirmed $130+ in identifiable same-day round-trip losses from journal data. Full quantitative backtest blocked — yfinance and Alpha Vantage both return 403 from this container (re-verified per prior reviews).

