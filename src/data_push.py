"""Auto-push data/ changes to GitHub so the remote post-mortem agent sees
fresh data. Called at the end of each bot task (scan, preclose, EOD, etc.).

Fails silently: a git error must never break the trading bot. All output
goes to the logger only.
"""
from __future__ import annotations
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

REPO_DIR = Path(__file__).resolve().parents[1]


def _git(*args: str, timeout: int = 30) -> tuple[int, str]:
    """Run a git command in the repo dir. Returns (returncode, combined_output)."""
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=str(REPO_DIR),
            capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return 1, f"{type(e).__name__}: {e}"


def push_data(tag: str = "data") -> None:
    """Stage data/ + .postmortem_offset, commit, push. No-op if repo isn't
    initialized or nothing changed. Never raises — errors just log a warning.
    """
    try:
        rc, _ = _git("rev-parse", "--is-inside-work-tree")
        if rc != 0:
            log.debug("data_push: not a git repo, skipping")
            return
        _git("add", "data", ".postmortem_offset", "-A", timeout=20)
        rc, _ = _git("diff", "--cached", "--quiet")
        if rc == 0:
            log.debug("data_push: no changes to commit")
            return
        from datetime import datetime
        msg = f"[auto] {tag} {datetime.utcnow().strftime('%Y-%m-%d %H:%MZ')}"
        rc, out = _git("commit", "-m", msg, timeout=20)
        if rc != 0:
            log.warning("data_push: commit failed: %s", out)
            return
        rc, out = _git("push", "origin", "HEAD", timeout=60)
        if rc != 0:
            log.warning("data_push: push failed: %s", out)
            return
        log.info("data_push: pushed %s", msg)
    except Exception as e:
        log.warning("data_push: unexpected error (%s) — continuing", e)
