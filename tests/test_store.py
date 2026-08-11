from datetime import date, datetime
from pathlib import Path

from decisionlog.models import ActionItem, Decision, ExtractionResult
from decisionlog.store import DecisionStore


def _store(tmp_path: Path) -> DecisionStore:
    return DecisionStore(tmp_path / "test.db")


def test_overdue_and_search(tmp_path: Path):
    store = _store(tmp_path)
    result = ExtractionResult(
        decisions=[
            Decision(meeting_id="m1", text="Ship v1 on Friday", evidence="we decided to ship")
        ],
        action_items=[
            ActionItem(
                meeting_id="m1",
                text="Write release notes",
                owner="Sarah",
                due_date=date(2026, 8, 1),
                due_text="last week",
            ),
            ActionItem(
                meeting_id="m1",
                text="Update docs",
                owner="Alex",
                due_date=date(2026, 12, 1),
                due_text="Dec",
            ),
        ],
        meeting_summary="Planning",
    )
    store.save_extraction("m1", "Sprint Planning", result, meeting_date=date(2026, 8, 1))

    overdue = store.list_actions(overdue=True, as_of=date(2026, 8, 10))
    assert len(overdue) == 1
    assert overdue[0]["text"] == "Write release notes"

    hits = store.search("release")
    assert any("release" in a["text"].lower() for a in hits["actions"])
    hits2 = store.search("ship")
    assert any("Ship" in d["text"] for d in hits2["decisions"])
