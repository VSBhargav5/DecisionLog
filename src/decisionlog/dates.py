"""Normalize relative deadline phrases into concrete dates."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Tuple

from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta, FR, MO, SA, SU, TH, TU, WE


WEEKDAY_MAP = {
    "monday": MO,
    "mon": MO,
    "tuesday": TU,
    "tue": TU,
    "wednesday": WE,
    "wed": WE,
    "thursday": TH,
    "thu": TH,
    "friday": FR,
    "fri": FR,
    "saturday": SA,
    "sat": SA,
    "sunday": SU,
    "sun": SU,
}


def normalize_deadline(
    due_text: Optional[str],
    reference: Optional[date] = None,
) -> Tuple[Optional[date], Optional[str]]:
    """
    Try to turn a free-text deadline into a concrete date.

    Returns (normalized_date, original_text).
    If parsing fails, returns (None, original_text).
    """
    if not due_text or not due_text.strip():
        return None, None

    text = due_text.strip().lower()
    ref = reference or date.today()

    # Common relative patterns we handle explicitly for reliability
    if text in {"today"}:
        return ref, due_text
    if text in {"tomorrow"}:
        return ref + timedelta(days=1), due_text
    if "next week" in text:
        return ref + timedelta(days=7), due_text
    if "end of month" in text or "eom" in text:
        next_month = ref.replace(day=1) + relativedelta(months=1)
        return next_month - timedelta(days=1), due_text
    if "end of week" in text or "eow" in text:
        # Friday of current week
        days_ahead = 4 - ref.weekday()  # Friday = 4
        if days_ahead < 0:
            days_ahead += 7
        return ref + timedelta(days=days_ahead), due_text

    # "next Friday", "this Monday", etc.
    for name, weekday in WEEKDAY_MAP.items():
        if f"next {name}" in text:
            return ref + relativedelta(weekday=weekday(+1)), due_text
        if f"this {name}" in text or text == name:
            # upcoming occurrence (including today if it matches)
            return ref + relativedelta(weekday=weekday(+1)), due_text

    # "in 3 days", "in 2 weeks"
    if text.startswith("in "):
        parts = text.split()
        if len(parts) >= 3 and parts[1].isdigit():
            n = int(parts[1])
            unit = parts[2]
            if unit.startswith("day"):
                return ref + timedelta(days=n), due_text
            if unit.startswith("week"):
                return ref + timedelta(weeks=n), due_text
            if unit.startswith("month"):
                return ref + relativedelta(months=n), due_text

    # Fallback: let dateutil try absolute / natural language parse
    try:
        parsed = date_parser.parse(due_text, default=datetime.combine(ref, datetime.min.time()))
        return parsed.date(), due_text
    except (ValueError, OverflowError, TypeError):
        return None, due_text
