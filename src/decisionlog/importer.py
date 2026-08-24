"""Import action rows from a simple CSV (text, owner, due_date, priority, tags, status)."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from .models import ActionItem, ActionPriority, ActionStatus, ExtractionResult
from .owners import normalize_owner
from .store import DecisionStore


def _parse_date(raw: str | None) -> date | None:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _parse_priority(raw: str | None) -> ActionPriority:
    if not raw:
        return ActionPriority.P2
    try:
        return ActionPriority(str(raw).strip().upper())
    except ValueError:
        return ActionPriority.P2


def _parse_status(raw: str | None) -> ActionStatus:
    if not raw:
        return ActionStatus.OPEN
    try:
        return ActionStatus(str(raw).strip().lower())
    except ValueError:
        return ActionStatus.OPEN


def import_actions_csv(
    store: DecisionStore,
    path: Path,
    *,
    meeting_title: str = "CSV import",
    meeting_date: date | None = None,
) -> tuple[str, int]:
    """Create a synthetic meeting and load actions. Returns (meeting_id, count)."""
    path = Path(path)
    rows: list[ActionItem] = []
    meeting_id = str(uuid4())
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (row.get("text") or row.get("action") or "").strip()
            if not text:
                continue
            tags_raw = row.get("tags") or ""
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            rows.append(
                ActionItem(
                    meeting_id=meeting_id,
                    text=text,
                    owner=normalize_owner(row.get("owner")),
                    due_date=_parse_date(row.get("due_date") or row.get("due")),
                    due_text=(row.get("due_text") or None),
                    status=_parse_status(row.get("status")),
                    priority=_parse_priority(row.get("priority")),
                    tags=tags,
                    notes=(row.get("notes") or None),
                    confidence=0.9,
                )
            )

    result = ExtractionResult(
        decisions=[],
        action_items=rows,
        meeting_summary=f"Imported {len(rows)} actions from {path.name}",
    )
    mid = store.save_extraction(
        meeting_id,
        meeting_title,
        result,
        meeting_date=meeting_date or date.today(),
        source_path=str(path),
    )
    store.log_activity("meeting", mid, "import_csv", f"{len(rows)} from {path.name}")
    return mid, len(rows)
