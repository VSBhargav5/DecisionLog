from datetime import date
from pathlib import Path

from decisionlog.models import ActionItem, ExtractionResult
from decisionlog.progress import finish_action, start_action
from decisionlog.store import DecisionStore


def test_start_and_finish(tmp_path: Path):
    store = DecisionStore(tmp_path / "p.db")
    result = ExtractionResult(
        action_items=[ActionItem(meeting_id="m", text="Do the thing", owner="Sam")]
    )
    store.save_extraction("m", "M", result, meeting_date=date(2026, 8, 1))
    aid = store.list_actions()[0]["id"]
    assert start_action(store, aid)
    assert store.get_action(aid)["status"] == "in_progress"
    assert finish_action(store, aid)
    assert store.get_action(aid)["status"] == "done"
