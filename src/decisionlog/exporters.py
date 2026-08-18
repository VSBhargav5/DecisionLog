from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta


def _ics_escape(text: str) -> str:
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def actions_to_ics(
    actions: list[dict],
    *,
    calendar_name: str = "DecisionLog Actions",
) -> str:
    """Build a minimal ICS calendar from actions that have due_date."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DecisionLog//EN",
        f"X-WR-CALNAME:{_ics_escape(calendar_name)}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    for a in actions:
        due = a.get("due_date")
        if not due:
            continue
        if isinstance(due, date):
            start = due
        else:
            try:
                start = date.fromisoformat(str(due)[:10])
            except ValueError:
                continue
        end = start + timedelta(days=1)
        uid = f"{a.get('id', 'action')}@decisionlog"
        summary = a.get("text") or "Action item"
        owner = a.get("owner") or "unassigned"
        meeting = a.get("meeting_title") or ""
        status = a.get("status") or ""
        priority = a.get("priority") or "P2"
        desc = f"Owner: {owner}\nStatus: {status}\nPriority: {priority}\nMeeting: {meeting}"
        if a.get("evidence"):
            desc += f"\nEvidence: {a['evidence']}"
        if a.get("notes"):
            desc += f"\nNotes: {a['notes']}"

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now}",
                f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
                f"SUMMARY:{_ics_escape(summary)}",
                f"DESCRIPTION:{_ics_escape(desc)}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def actions_to_csv(actions: list[dict]) -> str:
    buf = io.StringIO()
    fields = [
        "id",
        "text",
        "owner",
        "due_date",
        "due_text",
        "status",
        "priority",
        "tags",
        "notes",
        "meeting_title",
        "confidence",
        "evidence",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for a in actions:
        row = {k: a.get(k, "") for k in fields}
        tags = a.get("tags") or []
        if isinstance(tags, list):
            row["tags"] = ",".join(tags)
        writer.writerow(row)
    return buf.getvalue()


def decisions_to_csv(decisions: list[dict]) -> str:
    buf = io.StringIO()
    fields = ["id", "text", "status", "meeting_title", "confidence", "evidence"]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for d in decisions:
        writer.writerow({k: d.get(k, "") for k in fields})
    return buf.getvalue()
