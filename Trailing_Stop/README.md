# Converging Trailing-Stop Bot

A deterministic, **API/AI-free** safety layer that runs every 5 minutes (24/7),
ratchets protective stops upward as price climbs, and never lets the stop drop
below 2% under your average fill. Lives **alongside** the main bot — it does
not call any decision logic and only manages stop orders.

## Mechanics

- **Floor:** stop is never below `avg_entry_price * 0.98`.
- **Trail:** stop trails the running peak. Distance from peak shrinks linearly
  from **2% (at 0% gain)** → **0.5% (at +10% gain)**. Past +10% the stop stays
  at 0.5% below peak (clamped).
- **Ratchet only:** stops only move up. Pullbacks don't lower the stop.
- **Tighter existing stops respected:** if the main bot already placed an
  ATR-aware stop tighter than the rule, we leave it alone.
- **No-existing-stop positions get one created** at 2% below avg fill on first
  contact.
- **Extended hours:** native Alpaca stop orders only fill 09:30–16:00 ET.
  When the regular session is closed AND price has crossed the desired stop,
  the bot cancels the native stop and submits a marketable limit-sell with
  `extended_hours=True` so the position can actually exit overnight. When
  the regular session reopens it cleans up the synthetic order and a native
  GTC stop is restored on the next cycle.

### Convergence formula

```
gain        = max(0, peak / avg_fill - 1)              # fractional, e.g. 0.05
trail_pct   = clamp(2.0 - gain * 15.0, 0.5, 2.0)       # %
trail_stop  = peak * (1 - trail_pct / 100)
floor_stop  = avg_fill * 0.98
desired     = max(trail_stop, floor_stop)
```

Examples (`avg_fill = $10.00`):

| peak  | gain | trail_pct | trail_stop | desired (incl. floor) |
|-------|------|-----------|------------|------------------------|
| 10.00 |  0%  | 2.00%     | 9.80       | **9.80** |
| 10.50 |  5%  | 1.25%     | 10.369     | **10.37** |
| 11.00 | 10%  | 0.50%     | 10.945     | **10.95** |
| 12.00 | 20%  | 0.50%     | 11.940     | **11.94** |

## Price source priority

The bot computes the running peak from a price fetched in this order. First
source that returns a price wins:

1. **Twelve Data** — round-robin across keys in `TWELVEDATA_API_KEYS` env var
   (comma-separated). On HTTP 429 / "API credits" error, the next key is tried.
2. **Alpha Vantage** — uses `ALPHA_VANTAGE_API_KEY` env var (`GLOBAL_QUOTE`).
3. **Alpaca** — last-resort: the position's `current_price` field. (No bars,
   no news — only account state, which is allowed by the project's data rules.)

### Adding a second Twelve Data key

Edit `.env` in the project root:

```
TWELVEDATA_API_KEYS=973c386014f74026a2a9fa0935ea67ef,YOUR_SECOND_KEY
```

Comma-separated; no quotes. The bot rotates round-robin across all keys and
disables a key only for the current cycle if it returns 429 / "credits" /
401 / 403.

## Files

```
Trailing_Stop/
  __init__.py
  trailing_stops.py     # cycle, convergence formula, stop placement, fill detection
  price_fetcher.py      # TD-rotation -> AV -> Alpaca fallback chain
  state.py              # StopState — atomic JSON peak/last-stop tracking
  run.py                # entry point invoked every 5 min
  tests/
    test_trailing_stops.py
  state/
    trailing_stops.json # runtime state (gitignored)
  logs/                 # log dir kept for parity (logs go to ../logs/trailing_stop_bot.log)
  README.md
```

## Configuration (`config.yaml`)

```yaml
trailing_stops:
  enabled: true
  floor_pct: 2.0
  converged_pct: 0.5
  converge_gain_pct: 10.0
  state_file: Trailing_Stop/state/trailing_stops.json
  price_sources:
    - twelve_data
    - alpha_vantage
    - alpaca
  notify_on_create: true
  notify_on_fill: true
  notify_on_adjust: false
  extended_hours:
    enabled: true
    limit_discount_pct: 0.3
    tif: gtc
```

## Running

### Dry run (no orders submitted)

```bash
.venv/Scripts/python.exe Trailing_Stop/run.py --dry-run
```

Logs every action it would take. Use this to sanity-check before the first live cycle.

### Live cycle

```bash
.venv/Scripts/python.exe Trailing_Stop/run.py
```

### Schedule (Windows Task Scheduler)

The task `TradingBot_TrailingStops` is registered alongside other bot tasks by
the existing setup script — re-run as Administrator after pulling these changes:

```powershell
.\scripts\setup_schedule.ps1
```

Trigger: **every 5 minutes, 24/7** (no day-of-week filter, no market-hours filter).

### Tests

```bash
.venv/Scripts/python.exe -m pytest Trailing_Stop/tests/ -v
```

## Notifications

Telegram messages (uses existing `src.telegram_notifier`):

- **On stop creation** — when the bot places the first protective stop on a
  freshly-filled position.
- **On stop fill** — when a tracked stop disappears from open orders AND the
  position is no longer held (= it got hit).
- **On synthetic ext-hours stop** — when after-hours price triggers a synthetic
  limit-sell.
- Routine "moved stop up" adjustments are silent by default
  (`notify_on_adjust: false`) to reduce alert fatigue.

## Interaction with the main bot

- The main bot still places its initial ATR-aware protective stop at entry. The
  trailing bot **inspects** that stop on its first pass:
  - If the existing stop is **tighter** than 2% below fill → leave it.
  - If it's **wider** (or absent) → cancel and replace at 2% below fill.
- As price rises and the convergence formula tightens to <2%, the trailing bot
  may eventually move the stop above the main bot's original ATR stop. That's
  by design — the trailing layer always wins over the entry layer once the
  price action justifies it.
- If `scan_and_trade` replaces a stop mid-cycle, our recorded `last_stop_id`
  becomes stale; the next cycle re-queries open orders by symbol and adopts
  whatever is on the book as the canonical stop.

## State file shape

```json
{
  "AAPL": {
    "avg_fill": 187.42,
    "peak": 195.10,
    "last_stop_id": "abc-123",
    "last_stop_price": 193.15,
    "synthetic_stop_id": null,
    "first_seen": "2026-05-04T10:02:00-04:00",
    "last_update": "2026-05-05T14:35:00-04:00"
  }
}
```

Symbols no longer held are pruned at the start of each cycle.
