from datetime import date

from decisionlog.dates import normalize_deadline, snooze_date


def test_relative_phrases():
    ref = date(2026, 8, 10)  # Monday
    d, _ = normalize_deadline("tomorrow", reference=ref)
    assert d == date(2026, 8, 11)
    d, _ = normalize_deadline("EOD", reference=ref)
    assert d == ref
    d, _ = normalize_deadline("in 3 days", reference=ref)
    assert d == date(2026, 8, 13)


def test_snooze_from_today_when_overdue():
    ref = date(2026, 8, 10)
    # overdue due date
    assert snooze_date(date(2026, 8, 1), days=2, reference=ref) == date(2026, 8, 12)
    # future due keeps base
    assert snooze_date(date(2026, 8, 15), days=2, reference=ref) == date(2026, 8, 17)
