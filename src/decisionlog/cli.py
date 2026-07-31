from __future__ import annotations

import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .extractor import extract
from .store import DecisionStore

app = typer.Typer(
    help="DecisionLog – extract and track decisions from meetings",
    no_args_is_help=True,
)
console = Console()


def _store(db: Optional[Path] = None) -> DecisionStore:
    return DecisionStore(db) if db else DecisionStore()


@app.command("extract")
def extract_cmd(
    file: Path = typer.Argument(..., help="Path to meeting notes / transcript"),
    meeting: str = typer.Option(..., "--meeting", "-m", help="Meeting title"),
    meeting_date: Optional[str] = typer.Option(
        None, "--date", "-d", help="Meeting date YYYY-MM-DD (used for relative deadlines)"
    ),
    model: str = typer.Option("gpt-4o-mini", "--model", help="LLM model name"),
    replace: bool = typer.Option(
        False, "--replace", help="If a meeting with this title exists, replace its items (re-run)"
    ),
    db: Optional[Path] = typer.Option(None, "--db", help="Custom SQLite path"),
):
    """Extract decisions and action items from a meeting file."""
    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    text = file.read_text(encoding="utf-8")
    ref_date = date.today()
    if meeting_date:
        try:
            ref_date = date.fromisoformat(meeting_date)
        except ValueError:
            console.print("[red]--date must be YYYY-MM-DD[/red]")
            raise typer.Exit(1)

    meeting_id = str(uuid.uuid4())
    store = _store(db)

    existing = store.find_meeting_by_title(meeting)
    if existing and not replace:
        console.print(
            f"[yellow]Meeting '{meeting}' already exists.[/yellow]\n"
            "Use --replace to overwrite its decisions and actions, or choose a different title."
        )
        raise typer.Exit(1)

    console.print(f"[bold]Extracting from[/bold] {file.name} ...")
    result = extract(
        text,
        meeting_id=meeting_id,
        reference_date=ref_date,
        model=model,
    )

    used_id = store.save_extraction(
        meeting_id,
        meeting,
        result,
        meeting_date=ref_date,
        replace_existing=replace,
    )

    action = "Updated" if (existing and replace) else "Saved"
    console.print(f"\n[green]{action} meeting:[/green] {meeting}")
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
            due = a.due_date.isoformat() if a.due_date else (a.due_text or "—")
            console.print(f"  • [{owner}] {a.text}  (due: {due})")


@app.command("list")
def list_cmd(
    kind: str = typer.Argument("actions", help="actions | decisions | meetings"),
    status: Optional[str] = typer.Option(None, "--status", "-s"),
    owner: Optional[str] = typer.Option(None, "--owner", "-o"),
    db: Optional[Path] = typer.Option(None, "--db"),
):
    """List items from the decision log."""
    store = _store(db)

    if kind == "decisions":
        rows = store.list_decisions(status=status)
        table = Table(title="Decisions")
        table.add_column("ID", style="dim", max_width=8)
        table.add_column("Text")
        table.add_column("Status")
        table.add_column("Meeting")
        for r in rows:
            table.add_row(r["id"][:8], r["text"], r["status"], r.get("meeting_title", ""))
        console.print(table)

    elif kind == "actions":
        rows = store.list_actions(status=status, owner=owner)
        table = Table(title="Action Items")
        table.add_column("ID", style="dim", max_width=8)
        table.add_column("Owner")
        table.add_column("Text")
        table.add_column("Due")
        table.add_column("Status")
        for r in rows:
            due = r.get("due_date") or r.get("due_text") or "—"
            table.add_row(
                r["id"][:8],
                r["owner"] or "—",
                r["text"],
                str(due),
                r["status"],
            )
        console.print(table)

    elif kind == "meetings":
        rows = store.list_meetings()
        table = Table(title="Meetings")
        table.add_column("Title")
        table.add_column("Date")
        table.add_column("Created")
        for r in rows:
            table.add_row(
                r["title"],
                r.get("meeting_date") or "—",
                r["created_at"][:19],
            )
        console.print(table)

    else:
        console.print("[red]kind must be one of: actions, decisions, meetings[/red]")
        raise typer.Exit(1)


@app.command("status")
def status_cmd(
    item_id: str = typer.Argument(..., help="Full or short ID of decision / action"),
    new_status: str = typer.Argument(..., help="New status value"),
    kind: str = typer.Option("action", "--kind", "-k", help="action | decision"),
    owner: Optional[str] = typer.Option(None, "--owner", help="Also set owner (actions only)"),
    db: Optional[Path] = typer.Option(None, "--db"),
):
    """Update status of an action item or decision."""
    store = _store(db)

    # Allow short IDs (first 8 chars)
    def resolve(get_fn, list_fn):
        item = get_fn(item_id)
        if item:
            return item
        # try prefix match
        for row in list_fn():
            if row["id"].startswith(item_id):
                return row
        return None

    if kind == "decision":
        item = resolve(store.get_decision, store.list_decisions)
        if not item:
            console.print(f"[red]Decision not found: {item_id}[/red]")
            raise typer.Exit(1)
        ok = store.update_decision_status(item["id"], new_status)
        if not ok:
            console.print("[red]Invalid status. Use: proposed | decided | reversed | superseded[/red]")
            raise typer.Exit(1)
        console.print(f"[green]Updated decision[/green] {item['id'][:8]} → {new_status}")

    else:
        item = resolve(store.get_action, store.list_actions)
        if not item:
            console.print(f"[red]Action not found: {item_id}[/red]")
            raise typer.Exit(1)
        ok = store.update_action_status(item["id"], status=new_status, owner=owner)
        if not ok:
            console.print("[red]Invalid status. Use: open | in_progress | done | cancelled[/red]")
            raise typer.Exit(1)
        extra = f" (owner → {owner})" if owner is not None else ""
        console.print(f"[green]Updated action[/green] {item['id'][:8]} → {new_status}{extra}")


@app.command("export")
def export_cmd(
    format: str = typer.Option("md", "--format", "-f", help="md (Markdown)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write to file instead of stdout"),
    db: Optional[Path] = typer.Option(None, "--db"),
):
    """Export the decision log (currently Markdown)."""
    store = _store(db)

    if format != "md":
        console.print("[red]Only --format md is supported right now[/red]")
        raise typer.Exit(1)

    content = store.export_markdown()

    if output:
        output.write_text(content, encoding="utf-8")
        console.print(f"[green]Wrote[/green] {output}")
    else:
        console.print(content)


def main():
    app()


if __name__ == "__main__":
    main()
