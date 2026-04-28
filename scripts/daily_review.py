"""Daily post-mortem: pulls latest data from GitHub, runs deep analysis via Claude,
writes data/research/YYYY-MM-DD_daily_review.md.

Run automatically each weekday at 5 pm Phoenix via Task Scheduler, or manually:
    .venv\Scripts\python.exe scripts\daily_review.py
"""
from __future__ import annotations
import json
import logging
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# ── project root ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import anthropic

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("daily_review")

PHOENIX = ZoneInfo("America/Phoenix")
OPUS_MODEL   = "claude-opus-4-7"
SONNET_MODEL = "claude-sonnet-4-6"
MODEL = SONNET_MODEL  # toggle: switch to OPUS_MODEL to restore full accuracy
RESEARCH = ROOT / "data" / "research"


# ── helpers ───────────────────────────────────────────────────────────────────

def git_pull() -> None:
    log.info("git pull …")
    result = subprocess.run(
        ["git", "pull", "--ff-only"],
        cwd=ROOT, capture_output=True, text=True,
    )
    log.info(result.stdout.strip() or result.stderr.strip())


def today_phoenix() -> date:
    return datetime.now(tz=PHOENIX).date()


def load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def collect_day_files(day: date) -> dict:
    prefix = day.strftime("%Y%m%d")
    iso = day.isoformat()
    scans = sorted(RESEARCH.glob(f"{prefix}T*_scan.json"))
    crypto = sorted(RESEARCH.glob(f"{prefix}T*_crypto_scan.json"))
    preclose = sorted(RESEARCH.glob(f"{prefix}T*_preclose.json"))
    eod = RESEARCH / f"{iso}_eod.json"
    return {
        "scans": [load_json(p) for p in scans],
        "crypto_scans": [load_json(p) for p in crypto],
        "preclosing": [load_json(p) for p in preclose],
        "eod": load_json(eod),
        "eod_path": str(eod),
        "scan_count": len(scans) + len(crypto) + len(preclose),
    }


def load_journal_tail(n: int = 200) -> list[dict]:
    path = ROOT / "data" / "journal" / "trades.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-n:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def load_prior_reviews(n: int = 3) -> list[str]:
    reviews = sorted(RESEARCH.glob("*_daily_review.md"), reverse=True)[:n]
    return [p.read_text(encoding="utf-8") for p in reviews if p.exists()]


def load_config_excerpt() -> str:
    cfg = ROOT / "config.yaml"
    if cfg.exists():
        return cfg.read_text(encoding="utf-8")[:4000]
    return ""


# ── main prompt assembly ──────────────────────────────────────────────────────

SYSTEM = """\
You are the daily post-mortem analyst for an Alpaca paper-trading bot.
Your job: deliver a deep, honest review of the last trading day and propose
concrete strategy changes for the human to accept or reject.

North star: beat SPY on percentage return, NOT by being overly aggressive.
Balanced-risk swing cadence. Longs + shorts + crypto. -5% weekly drawdown halt.

Rules:
- DO NOT propose edits you will make yourself. PROPOSE ONLY — user reviews and accepts.
- Be honest about uncertainty. Label ambiguous calls as such.
- 3-6 high-signal proposals beats 15 weak ones.
- Architectural proposals welcome: new signals, arbiter prompt changes,
  model routing, rebalance cadence, new exit rules, hedging, regime switching.
- If today's data is sparse (holiday, weekend, first run), say so and exit cleanly.
"""

REPORT_SCHEMA = """\
# Daily Review — {date}

## Scoreboard
- Bot day return: X.XX%
- SPY day return: X.XX%
- Delta vs benchmark: +/-X.XX%
- Open positions: N (long X / short Y / crypto Z)
- Cash / cash-proxy: $X / $Y

## Today's Decisions — Graded
(per symbol: Symbol | Action | Entry/Exit price | Outcome by EOD | Grade A-F | Notes)

## Yesterday's Overnight Holds — Graded
For each position the bot held through YESTERDAY's close:
did the hold pay off to TODAY's close? Was the thesis validated?
(Same table format. DO NOT grade today's overnight decision — it hasn't played out.)

## Patterns & Systematic Issues
(2-5 bullets with evidence — cite specific scan timestamps or file names)

## Proposed Strategy Changes

### Proposal N: <short title>
- **What:** concrete change (config knob / code path / agent prompt)
- **Why:** evidence from recent sessions
- **Expected impact:** upside and cost
- **Risk of being wrong:** what could go sideways
- **Backtest result** (if applicable): numbers
- **Diff sketch:** exact file + line or config key, before → after

## Summary
One paragraph overall verdict on the day.
"""


def build_user_message(today: date, yesterday: date,
                       today_data: dict, yesterday_data: dict,
                       journal: list[dict], prior_reviews: list[str],
                       config_excerpt: str) -> str:
    def _dump(obj, label: str) -> str:
        if obj is None:
            return f"[{label}: not available]"
        try:
            return json.dumps(obj, indent=2, default=str)[:6000]
        except Exception:
            return f"[{label}: serialization error]"

    sections = [
        f"Today's date (America/Phoenix): {today.isoformat()}",
        f"Yesterday's date: {yesterday.isoformat()}",
        "",
        "=== CONFIG (current) ===",
        config_excerpt,
        "",
        "=== TODAY EOD SNAPSHOT ===",
        _dump(today_data["eod"], "today_eod"),
        "",
        f"=== TODAY SCAN SNAPSHOTS ({today_data['scan_count']} files — showing merged executions/exits/rebalance) ===",
    ]

    # Flatten today's executions, exits, and rebalance actions across all scans
    all_execs, all_exits, all_rebal = [], [], []
    for scan in (today_data["scans"] or []) + (today_data["crypto_scans"] or []):
        if isinstance(scan, dict):
            all_execs.extend(scan.get("executions") or [])
            all_exits.extend(scan.get("exits") or [])
            all_rebal.extend(scan.get("rebalance") or [])
    for preclose in (today_data["preclosing"] or []):
        if isinstance(preclose, dict):
            all_exits.extend(preclose.get("exits") or [])

    sections += [
        "Today executions: " + _dump(all_execs, "execs"),
        "Today exits: " + _dump(all_exits, "exits"),
        "Today rebalance actions: " + _dump(all_rebal, "rebal"),
        "",
        "=== YESTERDAY EOD SNAPSHOT ===",
        _dump(yesterday_data["eod"], "yesterday_eod"),
        "",
        "=== YESTERDAY PRECLOSE (overnight hold decisions) ===",
    ]
    for preclose in (yesterday_data["preclosing"] or []):
        if isinstance(preclose, dict):
            sections.append(_dump(preclose.get("hold_reports"), "hold_reports"))

    sections += [
        "",
        "=== RECENT TRADES JOURNAL (last 200 entries) ===",
        _dump(journal[-100:], "journal"),
    ]

    if prior_reviews:
        sections += [
            "",
            "=== PRIOR REVIEWS (last 3 — do not repeat the same proposals) ===",
        ]
        for i, rev in enumerate(prior_reviews, 1):
            sections.append(f"--- Review {i} ---\n{rev[:2000]}")

    sections += [
        "",
        "=== YOUR TASK ===",
        "1. Use the EOD snapshots and scan data above to grade every decision made today.",
        "2. For yesterday's overnight holds (in the preclose hold_reports above): check whether",
        "   the hold paid off by comparing yesterday's EOD prices to today's EOD prices.",
        "   The today_eod 'positions' field shows current prices for still-held names.",
        "   For positions closed today, check today's exits data.",
        "3. Look for systematic patterns across the data.",
        "4. Propose 3-6 concrete strategy improvements with diff sketches.",
        "",
        f"Write the full report using this structure:\n{REPORT_SCHEMA.format(date=today.isoformat())}",
        "",
        "Important: you do NOT have live market data — use the prices in the JSON snapshots.",
        "SPY daily return is in the EOD snapshot under 'spy_daily'.",
        "Be creative. Be honest. Be specific.",
    ]

    return "\n".join(sections)


# ── run ───────────────────────────────────────────────────────────────────────

def run(force_date: date | None = None) -> None:
    git_pull()

    today = force_date or today_phoenix()
    yesterday = date.fromordinal(today.toordinal() - 1)

    log.info("Analyzing %s (yesterday holds: %s)", today, yesterday)

    today_data = collect_day_files(today)
    yesterday_data = collect_day_files(yesterday)
    journal = load_journal_tail(200)
    prior_reviews = load_prior_reviews(3)
    config_excerpt = load_config_excerpt()

    if today_data["eod"] is None and today_data["scan_count"] == 0:
        log.warning("No data found for %s — likely a weekend or holiday. Skipping.", today)
        out = RESEARCH / f"{today.isoformat()}_daily_review.md"
        out.write_text(
            f"# Daily Review — {today.isoformat()}\n\nNo trading data found for this date "
            "(weekend, holiday, or bot was not running).\n",
            encoding="utf-8",
        )
        log.info("Wrote sparse report: %s", out)
        return

    user_msg = build_user_message(
        today, yesterday, today_data, yesterday_data, journal, prior_reviews, config_excerpt
    )

    log.info("Calling Claude %s for analysis …", MODEL)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )

    report = message.content[0].text
    out = RESEARCH / f"{today.isoformat()}_daily_review.md"
    out.write_text(report, encoding="utf-8")
    log.info("Report written: %s", out)

    # Commit and push so it's in GitHub for tomorrow's review to reference
    subprocess.run(["git", "add", str(out)], cwd=ROOT, check=True)
    result = subprocess.run(
        ["git", "commit", "-m", f"[auto] daily review {today.isoformat()}"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode == 0:
        subprocess.run(["git", "push"], cwd=ROOT, check=False)
        log.info("Committed and pushed.")
    else:
        log.info("Nothing new to commit (report unchanged).")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Daily trade post-mortem")
    parser.add_argument("--date", help="Override analysis date (YYYY-MM-DD)", default=None)
    args = parser.parse_args()

    forced = date.fromisoformat(args.date) if args.date else None
    run(force_date=forced)
