from datetime import date
from pathlib import Path

from decisionlog.digest import format_digest_markdown, format_today_markdown
from decisionlog.html_digest import format_digest_html
from decisionlog.models import ActionItem, ExtractionResult
from decisionlog.store import DecisionStore


def test_digest_markdown_sections(tmp_path: Path):
    store = DecisionStore(tmp_path / "d.db")
    result = ExtractionResult(
        action_items=[
            ActionItem(
                meeting_id="m",
                text="Fix login",
                owner="Sam",
                due_date=date(2026, 8, 1),
                priority="P0",  # type: ignore[arg-type]
            )
        ]
    )
    # priority must be enum - fix
    from decisionlog.models import ActionPriority

    result.action_items[0].priority = ActionPriority.P0
    store.save_extraction("m", "M1", result, meeting_date=date(2026, 8, 1))
    d = store.digest(due_within_days=7, as_of=date(2026, 8, 10))
    md = format_digest_markdown(d, days=7)
    assert "Critical" in md
    assert "Fix login" in md
    assert "Due today" in md
    html = format_digest_html(d, days=7)
    assert "<!DOCTYPE html>" in html
    assert "Fix login" in html


def test_today_markdown():
    board = {
        "owner": "Sam",
        "as_of": "2026-08-10",
        "overdue": [{"text": "A", "priority": "P1", "owner": "Sam", "due_date": "2026-08-01"}],
        "due_today": [],
        "blocked": [],
        "in_progress": [],
        "open": [],
    }
    text = format_today_markdown(board)
    assert "Today" in text and "Sam" in text and "Overdue" in text
