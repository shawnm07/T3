"""Local bridge for the remote post-mortem agent.

The remote CCR sandbox cannot reach Telegram or Alpaca. This script runs on
the local Windows machine (hourly via Task Scheduler) and:

  1. Fetches new postmortem-YYYY-MM-DD branches from GitHub origin.
  2. Sends a Telegram summary for any branch it hasn't notified yet.
  3. Polls Telegram getUpdates for 'accept postmortem-YYYY-MM-DD' or
     'reject postmortem-YYYY-MM-DD' messages and acts on them (merge/delete).

State lives in data/state/bridge_state.json (gitignored).
Secrets come from .env (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID).

Exits silently on normal no-op runs. Logs errors; never raises on git/net.
"""
from __future__ import annotations
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
STATE = REPO / "data" / "state" / "bridge_state.json"
BRANCH_RE = re.compile(r"^postmortem-(\d{4}-\d{2}-\d{2})$")
ACCEPT_RE = re.compile(r"^accept\s+postmortem-(\d{4}-\d{2}-\d{2})\s*(.*)$", re.I)
REJECT_RE = re.compile(r"^reject\s+postmortem-(\d{4}-\d{2}-\d{2})\s*$", re.I)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("bridge")


def _git(*args: str, timeout: int = 60) -> tuple[int, str]:
    r = subprocess.run(
        ["git", *args], cwd=str(REPO),
        capture_output=True, text=True, timeout=timeout,
    )
    return r.returncode, (r.stdout + r.stderr).strip()


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except json.JSONDecodeError:
            pass
    return {"notified_branches": [], "last_update_id": 0}


def save_state(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2))


def tg_send(token: str, chat_id: str, text: str) -> None:
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
    except Exception as e:
        log.warning("telegram send failed: %s", e)


def tg_poll(token: str, offset: int) -> list[dict]:
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": offset + 1, "timeout": 0},
            timeout=15,
        )
        return r.json().get("result", [])
    except Exception as e:
        log.warning("telegram poll failed: %s", e)
        return []


def discover_branches() -> list[str]:
    _git("fetch", "origin", "--prune")
    rc, out = _git("branch", "-r", "--list", "origin/postmortem-*")
    if rc != 0:
        return []
    branches = []
    for line in out.splitlines():
        name = line.strip().replace("origin/", "")
        if BRANCH_RE.match(name):
            branches.append(name)
    return branches


def read_report_summary(branch: str) -> str:
    rc, out = _git("show", f"origin/{branch}:data/research/{branch.split('-', 1)[1]}_postmortem.md", timeout=30)
    if rc != 0 or not out:
        return ""
    lines = out.splitlines()
    proposals = []
    in_proposals = False
    for ln in lines:
        lower = ln.lower()
        if lower.startswith("## proposed changes") or "proposed changes" in lower and ln.startswith("#"):
            in_proposals = True
            continue
        if in_proposals and ln.startswith("## "):
            break
        if in_proposals and ln.strip().startswith(("- ", "* ", "**")):
            proposals.append(ln.strip().lstrip("*- ").split("\n")[0])
        if len(proposals) >= 6:
            break
    return "\n".join(f"\u2022 {p[:160]}" for p in proposals[:6])


def notify_new_branch(branch: str, token: str, chat_id: str) -> None:
    date = branch.split("-", 1)[1] if "-" in branch else branch
    proposals = read_report_summary(branch) or "(see PR for full report)"
    pr_url = f"https://github.com/shawnm07/TheTradingTim/pulls"
    msg = (
        f"<b>Post-Mortem {date}</b>\n"
        f"<b>Proposed changes:</b>\n{proposals}\n\n"
        f"PR: {pr_url}\n"
        f"Reply <code>accept postmortem-{date}</code> to merge\n"
        f"or <code>reject postmortem-{date}</code> to close."
    )
    tg_send(token, chat_id, msg)
    log.info("notified branch %s", branch)


def merge_branch(branch: str) -> tuple[bool, str]:
    rc, out = _git("checkout", "main")
    if rc != 0:
        return False, f"checkout main failed: {out}"
    rc, out = _git("pull", "--ff-only", "origin", "main")
    if rc != 0:
        return False, f"pull failed: {out}"
    rc, out = _git("merge", "--no-ff", f"origin/{branch}", "-m", f"accept {branch}")
    if rc != 0:
        _git("merge", "--abort")
        return False, f"merge conflict: {out[:500]}"
    rc, out = _git("push", "origin", "main")
    if rc != 0:
        return False, f"push failed: {out}"
    return True, ""


def delete_branch(branch: str) -> tuple[bool, str]:
    rc, out = _git("push", "origin", "--delete", branch, timeout=30)
    if rc != 0:
        return False, out
    return True, ""


def handle_accept(branch: str, token: str, chat_id: str) -> None:
    ok, err = merge_branch(branch)
    if ok:
        tg_send(token, chat_id, f"\u2713 Applied {branch}. Live on next scan.")
        try:
            subprocess.run(["gh", "pr", "close", branch, "--comment", "merged via Telegram accept"],
                           cwd=str(REPO), capture_output=True, timeout=30)
        except Exception:
            pass
        log.info("merged %s", branch)
    else:
        tg_send(token, chat_id, f"\u26a0 Could not merge {branch}: {err[:300]}")
        log.warning("merge failed for %s: %s", branch, err)


def handle_reject(branch: str, token: str, chat_id: str) -> None:
    ok, err = delete_branch(branch)
    if ok:
        tg_send(token, chat_id, f"\u2717 Rejected {branch}. Branch deleted.")
        try:
            subprocess.run(["gh", "pr", "close", branch, "--comment", "rejected via Telegram"],
                           cwd=str(REPO), capture_output=True, timeout=30)
        except Exception:
            pass
        log.info("rejected %s", branch)
    else:
        tg_send(token, chat_id, f"\u26a0 Could not delete {branch}: {err[:300]}")


def process_replies(state: dict, token: str, chat_id: str) -> None:
    offset = state.get("last_update_id", 0)
    updates = tg_poll(token, offset)
    cutoff = datetime.now(timezone.utc).timestamp() - 48 * 3600
    max_seen = offset
    for u in updates:
        uid = u.get("update_id", 0)
        max_seen = max(max_seen, uid)
        msg = u.get("message", {})
        if msg.get("chat", {}).get("id") != int(chat_id):
            continue
        if msg.get("date", 0) < cutoff:
            continue
        text = (msg.get("text") or "").strip()
        m = ACCEPT_RE.match(text)
        if m:
            handle_accept(f"postmortem-{m.group(1)}", token, chat_id)
            continue
        m = REJECT_RE.match(text)
        if m:
            handle_reject(f"postmortem-{m.group(1)}", token, chat_id)
            continue
    state["last_update_id"] = max_seen


def main() -> int:
    load_dotenv(REPO / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log.warning("no TELEGRAM_BOT_TOKEN/CHAT_ID in .env; exiting")
        return 0

    state = load_state()
    notified = set(state.get("notified_branches", []))

    for branch in discover_branches():
        if branch not in notified:
            notify_new_branch(branch, token, chat_id)
            notified.add(branch)

    state["notified_branches"] = sorted(notified)[-30:]

    process_replies(state, token, chat_id)
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
