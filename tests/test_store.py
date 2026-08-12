from datetime import date
from pathlib import Path

from decisionlog.models import ActionItem, Decision, ExtractionResult
from decisionlog.store import DecisionStore


def _store(tmp_path: Path) -> DecisionStore:
    return DecisionStore(tmp_path / "test.db")


def _seed(store: DecisionStore) -> None:
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
                due_date=date(2026, 8, 12),
                due_text="soon",
            ),
            ActionItem(
                meeting_id="m1",
                text="TBD cleanup",
                owner=None,
                due_date=None,
            ),
        ],
        meeting_summary="Planning",
    )
    store.save_extraction("m1", "Sprint Planning", result, meeting_date=date(2026, 8, 1))


def test_overdue_and_search(tmp_path: Path):
    store = _store(tmp_path)
    _seed(store)

    overdue = store.list_actions(overdue=True, as_of=date(2026, 8, 10))
    assert len(overdue) == 1
    assert overdue[0]["text"] == "Write release notes"

    hits = store.search("release")
    assert any("release" in a["text"].lower() for a in hits["actions"])
    hits2 = store.search("ship")
    assert any("Ship" in d["text"] for d in hits2["decisions"])


def test_due_soon_unassigned_digest_delete(tmp_path: Path):
    store = _store(tmp_path)
    _seed(store)
    as_of = date(2026, 8, 10)

    soon = store.list_actions(due_within_days=5, as_of=as_of)
    assert any(a["text"] == "Update docs" for a in soon)

    unassigned = store.list_actions(unassigned=True)
    assert len(unassigned) == 1
    assert unassigned[0]["text"] == "TBD cleanup"

    d = store.digest(due_within_days=5, as_of=as_of)
    assert d["actions_open"] >= 2
    assert len(d["overdue"]) == 1
    assert "Sarah" in d["by_owner"] or "Alex" in d["by_owner"]

    m = store.resolve_meeting("Sprint Planning")
    assert m
    assert store.delete_meeting(m["id"])
    assert store.list_meetings() == []
    assert store.list_actions() == []
