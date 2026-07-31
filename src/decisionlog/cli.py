from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .extractor import extract
from .store import DecisionStore

app = typer.Typer(help="DecisionLog – extract and track decisions from meetings")
console = Console()


@app.command()
def extract_cmd(
    file: Path = typer.Argument(..., help="Path to meeting notes / transcript"),
    meeting: str = typer.Option(..., "--meeting", "-m", help="Meeting title"),
    model: str = typer.Option("gpt-4o-mini", "--model", help="LLM model name"),
    db: Optional[Path] = typer.Option(None, "--db", help="Custom SQLite path"),
):
    """Extract decisions and action items from a meeting file."""
    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    text = file.read_text(encoding="utf-8")
    meeting_id = str(uuid.uuid4())

    console.print(f"[bold]Extracting from[/bold] {file.name} ...")
    result = extract(text, meeting_id=meeting_id, model=model)

    store = DecisionStore(db or DecisionStore.DEFAULT_DB if hasattr(DecisionStore, "DEFAULT_DB") else None)
    # Fix: use default properly
    store = DecisionStore()
    if db:
        store = DecisionStore(db)

    store.save_extraction(meeting_id, meeting, result)

    console.print(f"\n[green]Saved meeting:[/green] {meeting}")
    console.print(f"  Decisions : {len(result.decisions)}")
    console.print(f"  Actions   : {len(result.action_items)}")

    if result.decisions:
        console.print("\n[bold]Decisions[/bold]")
        for d in result.decisions:
            console.print(f"  • {d.text}")

    if result.action_items:
        console.print("\n[bold]Action Items[/bold]")
        for a in result.action_items:
            owner = a.owner or "(unassigned)"
            due = a.due_text or (str(a.due_date) if a.due_date else "—")
            console.print(f"  • [{owner}] {a.text}  (due: {due})")


@app.command("list")
def list_cmd(
    kind: str = typer.Argument("actions", help="actions | decisions | meetings"),
    status: Optional[str] = typer.Option(None, "--status", "-s"),
    owner: Optional[str] = typer.Option(None, "--owner", "-o"),
):
    """List items from the decision log."""
    store = DecisionStore()

    if kind == "decisions":
        rows = store.list_decisions(status=status)
        table = Table(title="Decisions")
        table.add_column("Text")
        table.add_column("Status")
        table.add_column("Confidence")
        for r in rows:
            table.add_row(r["text"], r["status"], f"{r['confidence']:.2f}")
        console.print(table)

    elif kind == "actions":
        rows = store.list_actions(status=status, owner=owner)
        table = Table(title="Action Items")
        table.add_column("Owner")
        table.add_column("Text")
        table.add_column("Due")
        table.add_column("Status")
        for r in rows:
            table.add_row(
                r["owner"] or "—",
                r["text"],
                r["due_text"] or r["due_date"] or "—",
                r["status"],
            )
        console.print(table)

    elif kind == "meetings":
        rows = store.list_meetings()
        table = Table(title="Meetings")
        table.add_column("Title")
        table.add_column("Created")
        for r in rows:
            table.add_row(r["title"], r["created_at"][:19])
        console.print(table)

    else:
        console.print("[red]kind must be one of: actions, decisions, meetings[/red]")
        raise typer.Exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
