"""Append-only JSON-lines log of every decision, trade, and approval."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

JOURNAL_DIR = Path(__file__).resolve().parents[1] / "data" / "journal"
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)

DECISIONS_LOG = JOURNAL_DIR / "decisions.jsonl"
TRADES_LOG = JOURNAL_DIR / "trades.jsonl"
APPROVAL_QUEUE = JOURNAL_DIR / "pending_approvals.jsonl"
APPROVED_FILE = JOURNAL_DIR / "approved.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(path: Path, obj: dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, default=str) + "\n")


def log_decision(payload: dict[str, Any]) -> None:
    _append(DECISIONS_LOG, {"ts": _ts(), **payload})


def log_trade(payload: dict[str, Any]) -> None:
    _append(TRADES_LOG, {"ts": _ts(), **payload})


def enqueue_approval(payload: dict[str, Any]) -> str:
    approval_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    _append(APPROVAL_QUEUE, {"id": approval_id, "ts": _ts(), "status": "pending", **payload})
    return approval_id


def list_pending_approvals() -> list[dict[str, Any]]:
    approved_ids = set()
    if APPROVED_FILE.exists():
        for line in APPROVED_FILE.read_text().splitlines():
            if line.strip():
                try:
                    approved_ids.add(json.loads(line)["id"])
                except Exception:
                    pass
    out: list[dict[str, Any]] = []
    if APPROVAL_QUEUE.exists():
        for line in APPROVAL_QUEUE.read_text().splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                if obj.get("id") not in approved_ids:
                    out.append(obj)
            except Exception:
                pass
    return out


def mark_approval(approval_id: str, status: str, notes: str = "") -> None:
    _append(APPROVED_FILE, {"id": approval_id, "ts": _ts(), "status": status, "notes": notes})


def read_recent_decisions(limit: int = 50) -> list[dict[str, Any]]:
    if not DECISIONS_LOG.exists():
        return []
    lines = DECISIONS_LOG.read_text().splitlines()[-limit:]
    return [json.loads(l) for l in lines if l.strip()]


def read_recent_trades(limit: int = 50) -> list[dict[str, Any]]:
    if not TRADES_LOG.exists():
        return []
    lines = TRADES_LOG.read_text().splitlines()[-limit:]
    return [json.loads(l) for l in lines if l.strip()]
