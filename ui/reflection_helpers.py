from datetime import date, datetime, timedelta
from collections import Counter
from typing import List, Dict, Tuple, Optional

from domain.time_ranges import resolve_time_range


def resolve_current_and_previous_period(range_key: str, anchor: Optional[date] = None) -> Tuple[date, date, date, date]:
    if anchor is None:
        anchor = date.today()
    cur_start, cur_end = resolve_time_range(range_key, anchor)
    prev_anchor = cur_start - timedelta(days=1)
    prev_start, prev_end = resolve_time_range(range_key, prev_anchor)
    return cur_start, cur_end, prev_start, prev_end


def filter_sessions_by_date(sessions: List[Dict], start: date, end: date) -> List[Dict]:
    def to_date(s):
        return datetime.strptime(s["session_date"], "%Y-%m-%d").date()
    return [s for s in sessions if start <= to_date(s) <= end]


def compute_period_summary(sessions: List[Dict]) -> Optional[Dict]:
    if not sessions:
        return None

    durations = [int(s.get("duration_minutes", 0)) for s in sessions]
    total_minutes = sum(durations)

    days = sorted({datetime.strptime(s["session_date"], "%Y-%m-%d").date() for s in sessions})
    active_days = len(days)

    max_gap = 0
    for a, b in zip(days, days[1:]):
        gap = (b - a).days - 1
        if gap > max_gap:
            max_gap = gap

    activities = Counter(s.get("activity_type") for s in sessions)
    dominant_activity = activities.most_common(1)[0][0] if activities else None

    load_density = round(total_minutes / active_days, 1) if active_days else None

    return {
        "sessions": len(sessions),
        "total_minutes": total_minutes,
        "active_days": active_days,
        "max_gap": max_gap,
        "dominant_activity": dominant_activity,
        "load_density": load_density,
    }


def compute_phase_deltas(cur_summary: Optional[Dict], prev_summary: Optional[Dict]) -> Optional[Dict]:
    if not cur_summary or not prev_summary:
        return None

    delta_load = None
    if cur_summary.get("load_density") is not None and prev_summary.get("load_density") is not None:
        delta_load = round(cur_summary["load_density"] - prev_summary["load_density"], 1)

    return {
        "delta_minutes": cur_summary["total_minutes"] - prev_summary["total_minutes"],
        "delta_active_days": cur_summary["active_days"] - prev_summary["active_days"],
        "delta_max_gap": cur_summary["max_gap"] - prev_summary["max_gap"],
        "delta_load_density": delta_load,
        "dominant_activity_changed": cur_summary.get("dominant_activity") != prev_summary.get("dominant_activity"),
    }