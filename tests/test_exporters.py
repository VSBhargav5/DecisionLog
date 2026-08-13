from decisionlog.exporters import actions_to_csv, actions_to_ics


def test_ics_contains_event():
    actions = [
        {
            "id": "abc-123",
            "text": "Ship release",
            "owner": "Sarah",
            "due_date": "2026-08-20",
            "status": "open",
            "meeting_title": "Sprint",
        }
    ]
    ics = actions_to_ics(actions)
    assert "BEGIN:VCALENDAR" in ics
    assert "BEGIN:VEVENT" in ics
    assert "Ship release" in ics
    assert "DTSTART;VALUE=DATE:20260820" in ics
    assert "abc-123@decisionlog" in ics


def test_ics_skips_no_due():
    actions = [{"id": "x", "text": "No due", "status": "open"}]
    ics = actions_to_ics(actions)
    assert "BEGIN:VEVENT" not in ics


def test_csv_header_and_row():
    actions = [
        {
            "id": "1",
            "text": "Write notes",
            "owner": "Alex",
            "due_date": "2026-08-15",
            "due_text": "Fri",
            "status": "open",
            "meeting_title": "Standup",
            "confidence": 0.9,
            "evidence": "said so",
        }
    ]
    csv_text = actions_to_csv(actions)
    assert "id,text,owner" in csv_text
    assert "Write notes" in csv_text
    assert "Alex" in csv_text
