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
    assert "by_priority" in d
    assert "due_today" in d
    assert "stale" in d
    assert "completed" in d

    m = store.resolve_meeting("Sprint Planning")
    assert m
    assert store.delete_meeting(m["id"])
    assert store.list_meetings() == []
    assert store.list_actions() == []


def test_priority_tags_notes_done_due_stats(tmp_path: Path):
    store = _store(tmp_path)
    _seed(store)
    actions = store.list_actions()
    aid = next(a["id"] for a in actions if a["text"] == "Update docs")

    assert store.update_action(aid, priority="P0")
    assert store.update_action(aid, tags=["docs", "release"])
    assert store.update_action(aid, append_note="Draft started")
    assert store.update_action(aid, due_date=date(2026, 8, 15))

    item = store.get_action(aid)
    assert item["priority"] == "P0"
    assert "docs" in item["tags"] and "release" in item["tags"]
    assert "Draft started" in (item.get("notes") or "")
    assert item["due_date"] == "2026-08-15"

    filtered = store.list_actions(priority="P0")
    assert any(a["id"] == aid for a in filtered)
    tagged = store.list_actions(tag="docs")
    assert any(a["id"] == aid for a in tagged)

    assert store.update_action(aid, status="done")
    assert store.get_action(aid)["status"] == "done"

    s = store.stats(as_of=date(2026, 8, 10))
    assert s["actions"] >= 3
    assert s["by_status"].get("done", 0) >= 1
    assert "completed_7d" in s


def test_activity_log_on_update(tmp_path: Path):
    store = _store(tmp_path)
    _seed(store)
    aid = store.list_actions()[0]["id"]
    store.update_action(aid, status="in_progress")
    log = store.list_activity(entity_id=aid)
    assert log
    assert any(e["action"] == "update" for e in log)


def test_blocked_and_today_board(tmp_path: Path):
    store = _store(tmp_path)
    _seed(store)
    aid = next(a["id"] for a in store.list_actions() if a["owner"] == "Sarah")
    assert store.update_action(aid, status="blocked", blocked_reason="waiting on legal")
    item = store.get_action(aid)
    assert item["status"] == "blocked"
    assert "legal" in (item.get("blocked_reason") or "")
    board = store.today_board("Sarah", as_of=date(2026, 8, 10))
    assert board["blocked"]


def test_archive_done(tmp_path: Path):
    store = _store(tmp_path)
    _seed(store)
    aid = store.list_actions()[0]["id"]
    store.update_action(aid, status="done")
    # Force updated_at old via direct SQL is hard; archive with 0 days archives all done
    n = store.archive_done(older_than_days=0, as_of=date(2026, 8, 20))
    assert n >= 1
    assert store.get_action(aid)["status"] == "archived"
