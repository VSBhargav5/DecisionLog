from datetime import date
from pathlib import Path

from decisionlog.importer import import_actions_csv
from decisionlog.store import DecisionStore


def test_import_csv(tmp_path: Path):
    csv_path = tmp_path / "actions.csv"
    csv_path.write_text(
        "text,owner,due_date,priority,tags,status\n"
        "Ship docs,Sarah,2026-08-20,P1,docs;release,open\n"
        "Cleanup,, ,P3,,open\n",
        encoding="utf-8",
    )
    # tags use comma in real CSV - rewrite properly
    csv_path.write_text(
        "text,owner,due_date,priority,tags,status\n"
        'Ship docs,Sarah,2026-08-20,P1,"docs,release",open\n'
        "Cleanup,,,,P3,open\n",
        encoding="utf-8",
    )
    store = DecisionStore(tmp_path / "i.db")
    mid, n = import_actions_csv(store, csv_path, meeting_title="Import batch")
    assert n == 2
    assert store.get_meeting(mid)
    actions = store.list_actions(meeting_id=mid)
    assert any(a["text"] == "Ship docs" and a["owner"] == "Sarah" for a in actions)
