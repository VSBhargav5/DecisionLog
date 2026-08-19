from decisionlog.digest import format_digest_markdown, format_digest_slack


def _sample() -> dict:
    return {
        "as_of": "2026-08-19",
        "window_start": "2026-08-12",
        "actions_open": 3,
        "actions_in_progress": 1,
        "overdue": [
            {
                "text": "Write release notes",
                "owner": "Sarah",
                "due_date": "2026-08-01",
                "priority": "P0",
            }
        ],
        "critical": [
            {
                "text": "Write release notes",
                "owner": "Sarah",
                "due_date": "2026-08-01",
                "priority": "P0",
            }
        ],
        "due_soon": [
            {
                "text": "Update docs",
                "owner": "Alex",
                "due_date": "2026-08-22",
                "priority": "P2",
            }
        ],
        "unassigned": [
            {"text": "TBD cleanup", "owner": None, "due_date": None, "priority": "P3"}
        ],
        "recent_decisions": [{"text": "Ship v1 on Friday", "meeting_title": "Sprint"}],
        "by_owner": {"Sarah": 2, "Alex": 1},
    }


def test_markdown_digest_has_critical_and_load():
    md = format_digest_markdown(_sample(), days=7)
    assert "# DecisionLog" in md
    assert "2026-08-12" in md
    assert "Critical" in md
    assert "Write release notes" in md
    assert "Sarah: 2" in md
    assert "Ship v1 on Friday" in md


def test_slack_digest_is_pasteable():
    text = format_digest_slack(_sample(), days=7)
    assert text.startswith("*DecisionLog")
    assert "Write release notes" in text
    assert "Load:" in text
    assert text.endswith("\n")
