from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def _due(a: dict) -> str:
    return str(a.get("due_date") or a.get("due_text") or "—")


def _pri(a: dict) -> str:
    return (a.get("priority") or "P2").upper()


def _owner(a: dict) -> str:
    return (a.get("owner") or "unassigned").strip() or "unassigned"


def _line(a: dict) -> str:
    return f"[{_pri(a)}] {_owner(a)} — {a.get('text', '').strip()} (due {_due(a)})"


def window_bounds(digest: dict[str, Any], days: int) -> tuple[str, str]:
    as_of = digest.get("as_of") or date.today().isoformat()
    end = date.fromisoformat(str(as_of)[:10])
    start = end - timedelta(days=max(days, 0))
    return start.isoformat(), end.isoformat()


def format_digest_markdown(digest: dict[str, Any], days: int = 7) -> str:
    """Standup / weekly update you can paste into Notion, Slack, or email."""
    start, end = window_bounds(digest, days)
    overdue = digest.get("overdue") or []
    critical = digest.get("critical") or []
    due_soon = digest.get("due_soon") or []
    unassigned = digest.get("unassigned") or []
    decisions = digest.get("recent_decisions") or []
    by_owner = digest.get("by_owner") or {}

    lines = [
        f"# DecisionLog · {start} → {end}",
        "",
        (
            f"Overdue **{len(overdue)}** · "
            f"Due in {days}d **{len(due_soon)}** · "
            f"Unassigned **{len(unassigned)}** · "
            f"Open **{digest.get('actions_open', 0)}** · "
            f"In progress **{digest.get('actions_in_progress', 0)}**"
        ),
        "",
    ]

    lines.append("## Critical (P0/P1 overdue)")
    if critical:
        for a in critical:
            lines.append(f"- {_line(a)}")
    else:
        lines.append("- None")
    lines.append("")

    rest_overdue = [a for a in overdue if a not in critical]
    if rest_overdue:
        lines.append("## Other overdue")
        for a in rest_overdue:
            lines.append(f"- {_line(a)}")
        lines.append("")

    lines.append(f"## Due within {days} day(s)")
    if due_soon:
        for a in due_soon:
            lines.append(f"- {_line(a)}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Unassigned")
    if unassigned:
        for a in unassigned:
            lines.append(f"- {_line(a)}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Load by owner")
    if by_owner:
        for name, count in by_owner.items():
            lines.append(f"- {name}: {count}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Decisions this window")
    if decisions:
        for d in decisions:
            title = d.get("meeting_title") or ""
            extra = f" — _{title}_" if title else ""
            lines.append(f"- {d.get('text', '').strip()}{extra}")
    else:
        lines.append("- None captured in this window")
    lines.append("")
    return "\n".join(lines)


def format_digest_slack(digest: dict[str, Any], days: int = 7) -> str:
    """Plain Slack-friendly text (mrkdwn)."""
    start, end = window_bounds(digest, days)
    overdue = digest.get("overdue") or []
    critical = digest.get("critical") or []
    due_soon = digest.get("due_soon") or []
    unassigned = digest.get("unassigned") or []
    decisions = digest.get("recent_decisions") or []
    by_owner = digest.get("by_owner") or {}

    blocks = [
        f"*DecisionLog · {start} → {end}*",
        (
            f"Overdue {len(overdue)} · Due in {days}d {len(due_soon)} · "
            f"Unassigned {len(unassigned)} · Open {digest.get('actions_open', 0)}"
        ),
        "",
        "*Critical (P0/P1 overdue)*",
    ]
    if critical:
        blocks.extend(f"• {_line(a)}" for a in critical)
    else:
        blocks.append("• None")

    blocks += ["", f"*Due within {days} day(s)*"]
    if due_soon:
        blocks.extend(f"• {_line(a)}" for a in due_soon)
    else:
        blocks.append("• None")

    blocks += ["", "*Unassigned*"]
    if unassigned:
        blocks.extend(f"• {_line(a)}" for a in unassigned)
    else:
        blocks.append("• None")

    if by_owner:
        load = ", ".join(f"{n} {c}" for n, c in by_owner.items())
        blocks += ["", f"*Load:* {load}"]

    if decisions:
        blocks += ["", "*Decisions this window*"]
        blocks.extend(f"• {d.get('text', '').strip()}" for d in decisions)

    return "\n".join(blocks).rstrip() + "\n"
