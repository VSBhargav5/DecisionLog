from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
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
        None, "--date", "-d", help="Meeting date YYYY-MM-DD (for relative deadlines)"
    ),
    model: str = typer.Option("gpt-4o-mini", "--model", help="LLM model name"),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="OpenAI-compatible API base URL (e.g. https://api.groq.com/openai/v1)",
    ),
    replace: bool = typer.Option(
        False, "--replace", help="Replace existing meeting with same title (re-run)"
    ),
    db: Optional[Path] = typer.Option(None, "--db", help="Custom SQLite path"),
):
    """Extract decisions and action items from a meeting file."""
    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    text = file.read_text(encoding="utf-8").strip()
    if not text:
        console.print("[red]File is empty[/red]")
        raise typer.Exit(1)

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
    try:
        result = extract(
            text,
            meeting_id=meeting_id,
            reference_date=ref_date,
            model=model,
            base_url=base_url,
        )
    except Exception as e:
        msg = str(e).lower()
        if "api_key" in msg or "authentication" in msg or "401" in msg:
            console.print(
                "[red]API key missing or invalid.[/red]\n"
                "Set OPENAI_API_KEY (or the key for your provider) and retry.\n"
                "For other providers use --base-url (OpenAI-compatible)."
            )
        else:
            console.print(f"[red]Extraction failed:[/red] {e}")
        raise typer.Exit(1) from e

    if not result.decisions and not result.action_items:
        console.print(
            "[yellow]No decisions or action items extracted. "
            "Check that the notes contain clear decisions/assignments.[/yellow]"
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
    console.print(f"  ID        : {used_id[:8]}…")
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
    meeting: Optional[str] = typer.Option(
        None, "--meeting", "-m", help="Filter by meeting title (exact match)"
    ),
    db: Optional[Path] = typer.Option(None, "--db"),
):
    """List items from the decision log."""
    store = _store(db)
    meeting_id = None
    if meeting:
        m = store.find_meeting_by_title(meeting)
        if not m:
            console.print(f"[red]No meeting titled '{meeting}'[/red]")
            raise typer.Exit(1)
        meeting_id = m["id"]

    if kind == "decisions":
        rows = store.list_decisions(status=status, meeting_id=meeting_id)
        table = Table(title="Decisions")
        table.add_column("ID", style="dim", max_width=8)
        table.add_column("Text")
        table.add_column("Status")
        table.add_column("Meeting")
        for r in rows:
            table.add_row(r["id"][:8], r["text"], r["status"], r.get("meeting_title", ""))
        console.print(table)
        if not rows:
            console.print("[dim]No decisions found.[/dim]")

    elif kind == "actions":
        rows = store.list_actions(status=status, owner=owner, meeting_id=meeting_id)
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
        if not rows:
            console.print("[dim]No action items found.[/dim]")

    elif kind == "meetings":
        rows = store.list_meetings()
        table = Table(title="Meetings")
        table.add_column("ID", style="dim", max_width=8)
        table.add_column("Title")
        table.add_column("Date")
        table.add_column("Created")
        for r in rows:
            table.add_row(
                r["id"][:8],
                r["title"],
                r.get("meeting_date") or "—",
                r["created_at"][:19],
            )
        console.print(table)
        if not rows:
            console.print("[dim]No meetings yet. Run extract first.[/dim]")

    else:
        console.print("[red]kind must be one of: actions, decisions, meetings[/red]")
        raise typer.Exit(1)


@app.command("show")
def show_cmd(
    item_id: str = typer.Argument(..., help="Full or short ID"),
    kind: str = typer.Option("action", "--kind", "-k", help="action | decision"),
    db: Optional[Path] = typer.Option(None, "--db"),
):
    """Show full details for one decision or action item."""
    store = _store(db)
    item = store.resolve_id(item_id, kind)
    if not item:
        console.print(f"[red]{kind.capitalize()} not found: {item_id}[/red]")
        raise typer.Exit(1)

    title = item.get("meeting_title") or item.get("meeting_id", "")[:8]
    body_lines = [
        f"[bold]{item['text']}[/bold]",
        "",
        f"Status     : {item['status']}",
        f"Meeting    : {title}",
        f"Confidence : {item.get('confidence', '—')}",
        f"ID         : {item['id']}",
    ]
    if kind == "action":
        body_lines.insert(2, f"Owner      : {item.get('owner') or '(unassigned)'}")
        due = item.get("due_date") or item.get("due_text") or "—"
        body_lines.insert(3, f"Due        : {due}")
    if item.get("evidence"):
        body_lines.extend(["", f"Evidence   : {item['evidence']}"])

    console.print(Panel("\n".join(body_lines), title=kind.capitalize(), border_style="blue"))


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
    item = store.resolve_id(item_id, kind)
    if not item:
        console.print(f"[red]{kind.capitalize()} not found: {item_id}[/red]")
        raise typer.Exit(1)

    if kind == "decision":
        ok = store.update_decision_status(item["id"], new_status)
        if not ok:
            console.print(
                "[red]Invalid status. Use: proposed | decided | reversed | superseded[/red]"
            )
            raise typer.Exit(1)
        console.print(f"[green]Updated decision[/green] {item['id'][:8]} → {new_status}")
    else:
        ok = store.update_action_status(item["id"], status=new_status, owner=owner)
        if not ok:
            console.print(
                "[red]Invalid status. Use: open | in_progress | done | cancelled[/red]"
            )
            raise typer.Exit(1)
        extra = f" (owner → {owner})" if owner is not None else ""
        console.print(f"[green]Updated action[/green] {item['id'][:8]} → {new_status}{extra}")


@app.command("export")
def export_cmd(
    format: str = typer.Option("md", "--format", "-f", help="md | json"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write to file instead of stdout"
    ),
    db: Optional[Path] = typer.Option(None, "--db"),
):
    """Export the decision log as Markdown or JSON."""
    store = _store(db)

    if format == "md":
        content = store.export_markdown()
    elif format == "json":
        content = store.export_json()
    else:
        console.print("[red]--format must be md or json[/red]")
        raise typer.Exit(1)

    if output:
        output.write_text(content, encoding="utf-8")
        console.print(f"[green]Wrote[/green] {output}")
    else:
        console.print(content)


def main():
    app()


if __name__ == "__main__":
    main()
