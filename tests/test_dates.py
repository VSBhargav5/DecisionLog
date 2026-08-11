from datetime import date

from decisionlog.dates import normalize_deadline

REF = date(2026, 8, 5)  # Wednesday


def test_today_eod():
    d, orig = normalize_deadline("EOD", REF)
    assert d == REF
    assert orig == "EOD"


def test_tomorrow():
    d, _ = normalize_deadline("tomorrow", REF)
    assert d == date(2026, 8, 6)


def test_next_friday():
    d, _ = normalize_deadline("by next Friday", REF)
    assert d == date(2026, 8, 7)


def test_in_two_weeks():
    d, _ = normalize_deadline("in 2 weeks", REF)
    assert d == date(2026, 8, 19)


def test_end_of_month():
    d, _ = normalize_deadline("end of month", REF)
    assert d == date(2026, 8, 31)


def test_empty():
    assert normalize_deadline(None) == (None, None)
    assert normalize_deadline("   ") == (None, None)


def test_iso_date():
    d, orig = normalize_deadline("2026-09-01", REF)
    assert d == date(2026, 9, 1)
    assert orig == "2026-09-01"
