from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .exporters import actions_to_csv, actions_to_ics, decisions_to_csv
from .extractor import extract
from .store import DecisionStore

app = typer.Typer(
    help="DecisionLog – extract and track decisions from meetings",
    no_args_is_help=True,
)
console = Console()


def _store(db: Optional[Path] = None) -> DecisionStore:
    return DecisionStore(db) if db else DecisionStore()


def _print_actions(rows: list[dict], title: str) -> None:
    table = Table(title=title)
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
        console.print("[dim]None.[/dim]")


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
    overdue: bool = typer.Option(
        False, "--overdue", help="Only open/in-progress actions past due_date"
    ),
    due_soon: Optional[int] = typer.Option(
        None,
        "--due-soon",
        help="Actions due within N days (inclusive of today)",
    ),
    unassigned: bool = typer.Option(
        False, "--unassigned", help="Only open actions with no owner"
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
        rows = store.list_actions(
            status=status,
            owner=owner,
            meeting_id=meeting_id,
            overdue=overdue,
            due_within_days=due_soon,
            unassigned=unassigned,
        )
        if overdue:
            title = "Overdue action items"
        elif due_soon is not None:
            title = f"Due within {due_soon} day(s)"
        elif unassigned:
            title = "Unassigned action items"
        else:
            title = "Action Items"
        _print_actions(rows, title)

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


@app.command("digest")
def digest_cmd(
    days: int = typer.Option(7, "--days", "-n", help="Due-soon window in days"),
    db: Optional[Path] = typer.Option(None, "--db"),
):
    """Daily-style summary: overdue, due soon, unassigned, load by owner."""
    store = _store(db)
    d = store.digest(due_within_days=days)

    console.print(Panel.fit(
        f"[bold]DecisionLog digest[/bold]  ·  {d['as_of']}\n"
        f"Meetings {d['meetings']}  ·  Decided {d['decisions_decided']}  ·  "
        f"Open {d['actions_open']}  ·  In progress {d['actions_in_progress']}",
        border_style="cyan",
    ))

    if d["by_owner"]:
        console.print("\n[bold]Open load by owner[/bold]")
        for name, count in d["by_owner"].items():
            console.print(f"  {name}: {count}")

    console.print()
    _print_actions(d["overdue"], "Overdue")
    console.print()
    _print_actions(d["due_soon"], f"Due within {days} day(s)")
    console.print()
    _print_actions(d["unassigned"], "Unassigned")


@app.command("assign")
def assign_cmd(
    item_id: str = typer.Argument(..., help="Action id (prefix ok)"),
    owner: str = typer.Argument(..., help="New owner name (use '' to clear)"),
    db: Optional[Path] = typer.Option(None, "--db"),
):
    """Set or clear the owner of an action item."""
    store = _store(db)
    item = store.resolve_id(item_id, "action")
    if not item:
        console.print(f"[red]Action not found: {item_id}[/red]")
        raise typer.Exit(1)

    new_owner = owner.strip() or None
    ok = store.update_action_status(item["id"], owner=new_owner if new_owner is not None else "")
    # update_action_status treats empty string as clear when owner is not None
    # Fix: pass empty string to clear - looking at store, owner if owner else None clears
    if not ok:
        # owner-only update should work even without status
        ok = store.update_action_status(item["id"], owner=new_owner or "")
    if not ok:
        console.print("[red]Failed to update owner[/red]")
        raise typer.Exit(1)
    label = new_owner or "(unassigned)"
    console.print(f"[green]Assigned[/green] {item['id'][:8]} → {label}")


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Substring to search for"),
    db: Optional[Path] = typer.Option(None, "--db"),
):
    """Search decisions, actions, and meetings by text."""
    store = _store(db)
    hits = store.search(query)
    total = sum(len(v) for v in hits.values())
    if total == 0:
        console.print(f"[dim]No matches for '{query}'[/dim]")
        raise typer.Exit(0)

    if hits["meetings"]:
        console.print("[bold]Meetings[/bold]")
        for m in hits["meetings"]:
            console.print(f"  • {m['title']}  [dim]{m['id'][:8]}[/dim]")
        console.print()

    if hits["decisions"]:
        console.print("[bold]Decisions[/bold]")
        for d in hits["decisions"]:
            console.print(
                f"  • [{d['status']}] {d['text']}  "
                f"[dim]{d.get('meeting_title', '')} · {d['id'][:8]}[/dim]"
            )
        console.print()

    if hits["actions"]:
        console.print("[bold]Actions[/bold]")
        for a in hits["actions"]:
            owner = a.get("owner") or "—"
            console.print(
                f"  • [{a['status']}] [{owner}] {a['text']}  "
                f"[dim]{a.get('meeting_title', '')} · {a['id'][:8]}[/dim]"
            )


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


@app.command("delete-meeting")
def delete_meeting_cmd(
    meeting: str = typer.Argument(..., help="Meeting title or id (prefix ok)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    db: Optional[Path] = typer.Option(None, "--db"),
):
    """Delete a meeting and all of its decisions/actions."""
    store = _store(db)
    m = store.resolve_meeting(meeting)
    if not m:
        console.print(f"[red]Meeting not found: {meeting}[/red]")
        raise typer.Exit(1)

    if not yes:
        console.print(
            f"Delete meeting [bold]{m['title']}[/bold] ({m['id'][:8]}…) "
            "and all linked decisions/actions?"
        )
        confirm = typer.confirm("Continue?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    ok = store.delete_meeting(m["id"])
    if ok:
        console.print(f"[green]Deleted[/green] {m['title']}")
    else:
        console.print("[red]Delete failed[/red]")
        raise typer.Exit(1)


@app.command("export")
def export_cmd(
    format: str = typer.Option(
        "md", "--format", "-f", help="md | json | csv | ics"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write to file instead of stdout"
    ),
    open_only: bool = typer.Option(
        False,
        "--open-only",
        help="For csv/ics: only open + in_progress actions",
    ),
    db: Optional[Path] = typer.Option(None, "--db"),
):
    """Export the decision log as Markdown, JSON, CSV, or ICS calendar."""
    store = _store(db)

    if format == "md":
        content = store.export_markdown()
    elif format == "json":
        content = store.export_json()
    elif format == "csv":
        actions = store.list_actions()
        if open_only:
            actions = [a for a in actions if a["status"] in ("open", "in_progress")]
        content = actions_to_csv(actions)
    elif format == "ics":
        actions = store.list_actions()
        if open_only:
            actions = [a for a in actions if a["status"] in ("open", "in_progress")]
        content = actions_to_ics(actions)
    else:
        console.print("[red]--format must be md, json, csv, or ics[/red]")
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
