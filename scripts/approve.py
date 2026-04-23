"""CLI to review + approve pending trades that exceeded the size threshold.

Usage:
  py approve.py              # list pending
  py approve.py --id ID yes  # approve + execute
  py approve.py --id ID no   # reject
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rich.console import Console
from rich.table import Table

from src.alpaca_client import AlpacaClient
from src.config import Config
from src.decision import TradeDecision
from src.executor import TradeExecutor
from src.journal import list_pending_approvals, mark_approval
from src.kill_switch import increment_trade_counter
from src.risk import SizingDecision

console = Console()


def show_pending():
    pending = list_pending_approvals()
    if not pending:
        console.print("[green]No pending approvals.[/green]")
        return
    t = Table(title=f"Pending Approvals ({len(pending)})")
    for col in ("ID", "Symbol", "Action", "Qty", "Notional", "Entry", "Stop", "Target", "Conf"):
        t.add_column(col)
    for p in pending:
        s = p.get("sizing", {})
        d = p.get("decision", {})
        t.add_row(
            p.get("id", "?"),
            s.get("symbol", "?"),
            d.get("action", "?"),
            str(s.get("qty", "")),
            f"${s.get('notional', 0):.0f}",
            f"${s.get('entry', 0):.2f}",
            f"${s.get('stop_loss', 0):.2f}",
            f"${s.get('take_profit', 0):.2f}",
            f"{d.get('confidence', 0):.2f}",
        )
    console.print(t)
    for p in pending:
        console.print(f"\n[bold cyan]{p['id']}[/bold cyan] — {p['sizing']['symbol']} {p['decision']['action']}")
        console.print(f"  reasoning: {', '.join(p['decision']['reasoning'])}")
        console.print(f"  sizing: {p['sizing']['reasoning']}")


def execute_approved(approval: dict):
    cfg = Config.load()
    client = AlpacaClient(cfg)
    d = approval["decision"]
    s = approval["sizing"]
    decision = TradeDecision(
        symbol=d["symbol"], action=d["action"], confidence=d["confidence"],
        combined_score=d["combined_score"], signal_scores=d["signal_scores"],
        signal_details=d.get("signal_details", {}), reasoning=d["reasoning"],
    )
    sizing = SizingDecision(
        symbol=s["symbol"], side=s["side"], qty=s["qty"],
        notional=s["notional"], entry=s["entry"],
        stop_loss=s["stop_loss"], take_profit=s["take_profit"],
        risk_usd=s["risk_usd"], confidence=s["confidence"],
        reasoning=s["reasoning"],
    )
    execer = TradeExecutor(client, cfg, is_crypto="/" in sizing.symbol)
    # Bypass the approval threshold by calling submit_bracket directly
    side = "buy" if sizing.side == "buy" else "sell"
    order = client.submit_bracket(
        symbol=sizing.symbol, qty=sizing.qty, side=side,
        stop_loss=sizing.stop_loss if "/" not in sizing.symbol else None,
        take_profit=sizing.take_profit if "/" not in sizing.symbol else None,
        tif="gtc" if "/" in sizing.symbol else "day",
    )
    increment_trade_counter()
    console.print(f"[green]Submitted order {order.id} for {sizing.symbol}[/green]")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=str, help="Approval ID to act on")
    parser.add_argument("decision", nargs="?", choices=["yes", "no"], help="yes = approve + execute, no = reject")
    args = parser.parse_args()

    if not args.id:
        show_pending()
        return 0

    pending = list_pending_approvals()
    match = next((p for p in pending if p["id"] == args.id), None)
    if not match:
        console.print(f"[red]No pending approval with id {args.id}[/red]")
        return 1
    if args.decision == "yes":
        execute_approved(match)
        mark_approval(args.id, "approved")
    elif args.decision == "no":
        mark_approval(args.id, "rejected")
        console.print(f"[yellow]Rejected {args.id}[/yellow]")
    else:
        show_pending()
    return 0


if __name__ == "__main__":
    sys.exit(main())
