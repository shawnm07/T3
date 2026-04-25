"""Rich CLI dashboard: account, positions, recent trades, pending approvals, kill switch."""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.alpaca_client import AlpacaClient
from src.config import Config
from src.journal import list_pending_approvals, read_recent_decisions, read_recent_trades
from src.kill_switch import check_kill_switch, is_manually_halted, trades_today

console = Console()


def main() -> int:
    cfg = Config.load()
    client = AlpacaClient(cfg)
    # Independent valuation: equity / market_value / P&L recomputed from
    # Alpha-Vantage-sourced prices, not Alpaca's reported fields.
    account, positions = client.get_snapshot()
    clock = client.get_clock()

    header = (
        f"Mode=[bold]{cfg.alpaca.mode}[/bold] | "
        f"Market={'[green]OPEN[/green]' if clock.is_open else '[red]CLOSED[/red]'} | "
        f"Equity=${float(account.equity):,.2f} | "
        f"Cash=${float(account.cash):,.2f} | "
        f"BP=${float(account.buying_power):,.2f}"
    )
    console.print(Panel(header, title="Trading Bot Status"))

    if positions:
        t = Table(title=f"Positions ({len(positions)})")
        for col in ("Symbol", "Side", "Qty", "Avg Entry", "Current", "Market Value", "P&L %", "P&L $"):
            t.add_column(col)
        for p in positions:
            upl = float(p.unrealized_plpc) * 100
            style = "green" if upl >= 0 else "red"
            t.add_row(
                p.symbol, str(p.side), str(p.qty),
                f"${float(p.avg_entry_price):.2f}",
                f"${float(p.current_price):.2f}" if p.current_price else "-",
                f"${float(p.market_value):.2f}",
                f"[{style}]{upl:+.2f}%[/{style}]",
                f"[{style}]${float(p.unrealized_pl):+.2f}[/{style}]",
            )
        console.print(t)
    else:
        console.print("[dim]No open positions.[/dim]")

    halted, reason = is_manually_halted()
    kill_status = "[red]HALTED[/red] " + reason if halted else "[green]Active[/green]"
    console.print(Panel(
        f"Kill switch: {kill_status} | Trades today: {trades_today()}",
        title="Risk",
    ))

    pending = list_pending_approvals()
    if pending:
        t = Table(title=f"[yellow]Pending Approvals ({len(pending)})[/yellow]")
        for col in ("ID", "Symbol", "Action", "Notional", "Conf", "Reasoning"):
            t.add_column(col)
        for p in pending:
            s = p.get("sizing", {})
            d = p.get("decision", {})
            t.add_row(
                p["id"], s.get("symbol", "?"), d.get("action", "?"),
                f"${s.get('notional', 0):.0f}",
                f"{d.get('confidence', 0):.2f}",
                "; ".join(d.get("reasoning", []))[:60],
            )
        console.print(t)
        console.print("[dim]Approve with: py scripts/approve.py --id <ID> yes[/dim]")

    trades = read_recent_trades(limit=10)
    if trades:
        t = Table(title="Recent Trades")
        for col in ("Time", "Event", "Symbol", "Detail"):
            t.add_column(col)
        for tr in trades[-10:]:
            detail = tr.get("sizing", {}).get("reasoning") or tr.get("reason") or tr.get("error", "")
            t.add_row(tr["ts"][:19], tr.get("event", "?"), tr.get("symbol", "?"), str(detail)[:60])
        console.print(t)

    return 0


if __name__ == "__main__":
    sys.exit(main())
