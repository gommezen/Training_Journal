# weeks.py

from datetime import datetime, date, timedelta
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Dict, List

@dataclass
class WeekSummary:
    week_id: str
    start_date: date
    end_date: date

    session_count: int
    total_duration: int

    modality_counts: Dict[str, int]

    hard_sessions: int
    energy1_sessions: int
    
    training_load: int            # ← ADD
    avg_rpe: float | None         # ← OPTIONAL

    active_days: int
    max_gap_days: int

    delta_session_count: int | None
    delta_total_duration: int | None
    delta_hard_sessions: int | None

# def is_hard_session(session: dict) -> bool:
#     """
#     A session is 'hard' if it is energetically or cognitively demanding.
#     """
#     return session["energy_level"] >= 3


def _iso_week_start(d: date) -> date:
    """Return Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


def _iso_week_id(d: date) -> str:
    """Return ISO week id like '2025-W02'."""
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def build_week_buckets(
    sessions: List[Dict]
) -> Dict[str, Dict]:
    """
    Group sessions into ISO week buckets.

    Returns:
        {
          "2025-W02": {
              "week_id": "2025-W02",
              "start_date": date,
              "end_date": date,
              "sessions": [ ... ]
          },
          ...
        }
    """
    buckets = defaultdict(list)

    # --- group sessions by ISO week
    for s in sessions:
        d = datetime.strptime(s["session_date"], "%Y-%m-%d").date()
        week_id = _iso_week_id(d)
        buckets[week_id].append(s)

    week_data = {}

    for week_id, items in buckets.items():
        # all sessions in same week → pick any date
        sample_date = datetime.strptime(
            items[0]["session_date"], "%Y-%m-%d"
        ).date()

        start = _iso_week_start(sample_date)
        end = start + timedelta(days=6)

        # sort sessions inside week
        items_sorted = sorted(
            items,
            key=lambda x: x["session_date"]
        )

        week_data[week_id] = {
            "week_id": week_id,
            "start_date": start,
            "end_date": end,
            "sessions": items_sorted,
        }

    # return weeks ordered chronologically
    return dict(
        sorted(
            week_data.items(),
            key=lambda kv: kv[1]["start_date"]
        )
    )

from collections import Counter
from datetime import datetime, timedelta

def build_week_summaries(sessions: list[dict]) -> list[WeekSummary]:
    """
    Build ordered WeekSummary objects from raw session dicts.
    """
    buckets = build_week_buckets(sessions)
    summaries: list[WeekSummary] = []

    previous: WeekSummary | None = None

    for week_id, w in buckets.items():
        week_sessions = w["sessions"]

        durations = [s["duration_minutes"] for s in week_sessions]
        total_duration = sum(durations)

        modality_counts = Counter(
            s["activity_type"] for s in week_sessions
        )

        # hard_sessions = sum(
        #     1 for s in week_sessions if is_hard_session(s)
        # )

        energy1_sessions = sum(
            1 for s in week_sessions if s["energy_level"] == 1
        )
        
        HARD_RPE_THRESHOLD = 7

        # --- RPE-aware metrics (explicit intensity) ---
        rpe_sessions = [
            s for s in week_sessions
            if s.get("rpe") is not None
        ]

        hard_sessions = sum(
            1 for s in rpe_sessions
            if s["rpe"] >= HARD_RPE_THRESHOLD
        )

        training_load = sum(
            s["duration_minutes"] * s["rpe"]
            for s in rpe_sessions
        )

        avg_rpe = (
            sum(s["rpe"] for s in rpe_sessions) / len(rpe_sessions)
            if rpe_sessions else None
        )


        # --- active days & gaps ---
        days = sorted(
            {
                datetime.strptime(
                    s["session_date"], "%Y-%m-%d"
                ).date()
                for s in week_sessions
            }
        )

        active_days = len(days)

        max_gap = 0
        for d1, d2 in zip(days, days[1:]):
            gap = (d2 - d1).days - 1
            if gap > max_gap:
                max_gap = gap

        summary = WeekSummary(
            week_id=week_id,
            start_date=w["start_date"],
            end_date=w["end_date"],

            session_count=len(week_sessions),
            total_duration=total_duration,

            modality_counts=dict(modality_counts),

            hard_sessions=hard_sessions,
            energy1_sessions=energy1_sessions,
            
            training_load=training_load,
            avg_rpe=avg_rpe,

            active_days=active_days,
            max_gap_days=max_gap,

            delta_session_count=(
                len(week_sessions) - previous.session_count
                if previous else None
            ),
            delta_total_duration=(
                total_duration - previous.total_duration
                if previous else None
            ),
            delta_hard_sessions=(
                hard_sessions - previous.hard_sessions
                if previous else None
            ),
        )

        summaries.append(summary)
        previous = summary

    return summaries
