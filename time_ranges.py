# time_ranges.py

from datetime import date, datetime, timedelta
import calendar
from typing import Tuple


def _iso_week_bounds(d: date) -> Tuple[date, date]:
    """
    Return (monday, sunday) for the ISO week containing date d.
    """
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _month_bounds(d: date) -> Tuple[date, date]:
    """
    Return first and last day of the calendar month containing date d.
    """
    first_day = d.replace(day=1)
    last_day = d.replace(
        day=calendar.monthrange(d.year, d.month)[1]
    )
    return first_day, last_day


def resolve_time_range(
    range_type: str,
    anchor: date | None = None,
) -> Tuple[date, date]:
    """
    Resolve a canonical time range into (start_date, end_date).

    range_type: one of {"1w", "1m", "3m", "6m"}
    anchor: date used to anchor the range (default: today)

    Returns:
        (start_date, end_date) as date objects
    """
    if anchor is None:
        anchor = date.today()

    range_type = range_type.lower()

    # -----------------------------
    # 1 WEEK (ISO week)
    # -----------------------------
    if range_type == "1w":
        return _iso_week_bounds(anchor)

    # -----------------------------
    # 1 MONTH (calendar month)
    # -----------------------------
    if range_type == "1m":
        month_start, month_end = _month_bounds(anchor)
        start, _ = _iso_week_bounds(month_start)
        _, end = _iso_week_bounds(month_end)
        return start, end

    # -----------------------------
    # 3 MONTHS (calendar-aligned)
    # -----------------------------
    if range_type == "3m":
        year = anchor.year
        month = anchor.month - 2
        if month <= 0:
            month += 12
            year -= 1

        start_anchor = date(year, month, 1)
        end_anchor = _month_bounds(anchor)[1]

        start, _ = _iso_week_bounds(start_anchor)
        _, end = _iso_week_bounds(end_anchor)
        return start, end

    # -----------------------------
    # 6 MONTHS (calendar-aligned)
    # -----------------------------
    if range_type == "6m":
        year = anchor.year
        month = anchor.month - 5
        if month <= 0:
            month += 12
            year -= 1

        start_anchor = date(year, month, 1)
        end_anchor = _month_bounds(anchor)[1]

        start, _ = _iso_week_bounds(start_anchor)
        _, end = _iso_week_bounds(end_anchor)
        return start, end

    raise ValueError(f"Unknown range_type: {range_type}")
