"""Self-contained HTML weekly digest."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from .digest import _line, window_bounds


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def _ul(items: list[dict], empty: str = "None") -> str:
    if not items:
        return f"<p class='empty'>{_esc(empty)}</p>"
    lis = "".join(f"<li>{_esc(_line(a))}</li>" for a in items)
    return f"<ul>{lis}</ul>"


def format_digest_html(digest: dict[str, Any], days: int = 7) -> str:
    start, end = window_bounds(digest, days)
    overdue = digest.get("overdue") or []
    critical = digest.get("critical") or []
    due_today = digest.get("due_today") or []
    due_soon = digest.get("due_soon") or []
    unassigned = digest.get("unassigned") or []
    stale = digest.get("stale") or []
    completed = digest.get("completed") or []
    decisions = digest.get("recent_decisions") or []
    by_owner = digest.get("by_owner") or {}

    owner_rows = "".join(
        f"<tr><td>{_esc(n)}</td><td>{c}</td></tr>" for n, c in by_owner.items()
    ) or "<tr><td colspan='2'>None</td></tr>"

    dec_html = (
        "".join(f"<li>{_esc(d.get('text') or '')}</li>" for d in decisions)
        if decisions
        else "<li>None</li>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>DecisionLog · {_esc(start)} → {_esc(end)}</title>
<style>
  body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; line-height: 1.45; max-width: 820px; }}
  h1 {{ margin-bottom: 0.25rem; }}
  .meta {{ color: #64748b; margin-bottom: 1.5rem; }}
  h2 {{ margin-top: 1.4rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.25rem; }}
  .empty {{ color: #94a3b8; }}
  table {{ border-collapse: collapse; }}
  td, th {{ text-align: left; padding: 0.25rem 0.75rem 0.25rem 0; }}
</style>
</head>
<body>
  <h1>DecisionLog</h1>
  <p class="meta">{_esc(start)} → {_esc(end)} ·
     overdue {len(overdue)} · due today {len(due_today)} ·
     blocked {digest.get('actions_blocked', 0)} · open {digest.get('actions_open', 0)}</p>

  <h2>Critical (P0/P1 overdue)</h2>
  {_ul(critical)}

  <h2>Due today</h2>
  {_ul(due_today)}

  <h2>Due within {days} day(s)</h2>
  {_ul(due_soon)}

  <h2>Unassigned</h2>
  {_ul(unassigned)}

  <h2>Stale</h2>
  {_ul(stale[:20])}

  <h2>Completed this window</h2>
  {_ul(completed[:20])}

  <h2>Load by owner</h2>
  <table><thead><tr><th>Owner</th><th>Open</th></tr></thead>
  <tbody>{owner_rows}</tbody></table>

  <h2>Decisions this window</h2>
  <ul>{dec_html}</ul>
</body>
</html>
"""


def write_digest_html(digest: dict[str, Any], path: Path, days: int = 7) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_digest_html(digest, days), encoding="utf-8")
    return path
