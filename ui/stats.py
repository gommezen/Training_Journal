from datetime import date
from typing import List

import pandas as pd
import streamlit as st
import plotly.express as px
import altair as alt #
from collections import defaultdict #

from infrastructure.db import get_sessions_between
from domain.time_ranges import resolve_time_range
from domain.weeks import WeekSummary, build_week_summaries


# --------------------------------------------------
# Public entry point (called from app.py)
# --------------------------------------------------

def render_stats_screen() -> None:
    st.title("Training Statistics")
    
    # ------------------------------------------------
    # Statistics explanation
    # ------------------------------------------------
    with st.expander("Understanding these statistics", expanded=False):
        st.markdown(
            """
            **This page shows weekly training load and rhythm.**

            **Week**
            - ISO calendar week (Monday-Sunday).

            **Sessions**
            - Number of recorded training sessions that week (including rest days).

            **Hard sessions**
            - Sessions marked as high intensity 
            (Number of sessions with RPE ≥ threshold (e.g. 7)).

            **Minutes**
            - Total recorded training duration for the week.

            **Active days**
            - Number of distinct days with at least one session.

            **Max gap (days)**
            - Longest consecutive break between active days within the week.

            **Δ sessions / Δ minutes**
            - Change compared to the previous week.

            These metrics describe **load, intensity, and continuity** —
            not performance or outcomes.
            """
        )

    # 1. Canonical time range selection
    range_key = _select_time_range()

    today = date.today()
    start, end = resolve_time_range(range_key, today)

    st.caption(f"Period: {start} → {end}")

    # 2. Deterministic data load
    sessions = get_sessions_between(
        start.isoformat(),
        end.isoformat(),
    )

    if not sessions:
        st.info("No sessions in this period.")
        return

    # 3. Build week summaries (domain layer)
    weeks = build_week_summaries(sessions)

    if not weeks:
        st.info("No complete weeks in this range.")
        return

    # Defensive ordering (UI should not rely on internals)
    weeks = sorted(weeks, key=lambda w: w.start_date)

    # 4. Render views
    _render_week_overview_table(weeks)

    if _should_show_period_composition(range_key):
        _render_period_activity_composition(sessions)

    _render_week_load_chart(weeks, sessions)


# --------------------------------------------------
# UI components
# --------------------------------------------------

def _select_time_range() -> str:
    labels = {
        "1w": "1 week",
        "1m": "1 month",
        "3m": "3 months",
        "6m": "6 months",
    }

    return st.selectbox(
        "Time range",
        list(labels.keys()),
        index=1,
        format_func=lambda k: labels[k],
    )



def _render_week_overview_table(weeks: List[WeekSummary]) -> None:
    st.subheader("Week overview")

    rows = []
    for w in weeks:
        rows.append({
            "Week": w.week_id,
            "Sessions": w.session_count,
            "Hard sessions": w.hard_sessions,
            "Minutes": w.total_duration,
            "Active days": w.active_days,
            "Max gap (days)": w.max_gap_days,
            "Δ sessions": _format_delta(w.delta_session_count),
            "Δ minutes": _format_delta(w.delta_total_duration),
        })

    df = pd.DataFrame(rows)

    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
    )


def _render_week_load_chart(
    weeks: List[WeekSummary],
    sessions,
) -> None:
    st.subheader("Weekly training load (by activity)")

    weekly_activity = _weekly_minutes_by_activity(sessions)

    rows = []
    for w in weeks:
        week_id = w.week_id
        activities = weekly_activity.get(week_id, {})

        for activity, minutes in activities.items():
            rows.append({
                "Week": week_id,
                "Activity": activity,
                "Minutes": minutes,
            })

    if not rows:
        st.info("No activity data to display.")
        return

    df = pd.DataFrame(rows)

    chart = (
    alt.Chart(df)
    .mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
    .encode(
        x=alt.X(
            "Week:N",
            title="Week",
            axis=alt.Axis(labelAngle=0),
            sort=None,
        ),
        y=alt.Y(
            "Minutes:Q",
            title="Total minutes",
        ),
        color=alt.Color(
            "Activity:N",
            scale=alt.Scale(
                domain=["cardio", "karate", "weights", "run", "rowing"],
                range=["#4e79a7", "#f28e2b", "#59a14f", "#76b7b2", "#e15759"],
            ),
            legend=alt.Legend(orient="bottom"),
        ),
        tooltip=[
            alt.Tooltip("Activity:N", title="Activity"),
            alt.Tooltip("Minutes:Q", title="Minutes"),
        ],
    )
    .properties(height=320)
    .configure_scale(
        bandPaddingInner=0.3,
        bandPaddingOuter=0.15,
    )
)


    st.altair_chart(chart, width="stretch")



# Period activity composition (for certain ranges)
def _render_period_activity_composition(sessions) -> None:
    st.subheader("Activity composition (period total)")

    totals = _aggregate_minutes_by_activity(sessions)

    if not totals:
        st.info("No activity data to summarise.")
        return

    df = pd.DataFrame(
        [{"Activity": k, "Minutes": v} for k, v in totals.items()]
    )

    
    total_minutes = int(df["Minutes"].sum())
    
    
    donut = (
        alt.Chart(df)
        .mark_arc(innerRadius=60, outerRadius=100)
        .encode(
            theta=alt.Theta("Minutes:Q"),
            color=alt.Color(
                "Activity:N",
                scale=alt.Scale(
                    domain=["cardio", "karate", "weights", "run", "rowing"],
                    range=["#4e79a7", "#f28e2b", "#59a14f", "#76b7b2", "#e15759"],
                ),
                #legend=None,  # ← IMPORTANT
                legend=alt.Legend(
                    title="Activity",
                    labelFontSize=11,
                    titleFontSize=12,
                    orient="right",
                    direction="vertical",
                    offset=20,
                ),
               
            ),
            tooltip=[
                alt.Tooltip("Activity:N", title="Activity"),
                alt.Tooltip("Minutes:Q", title="Minutes"),
            ],
        )
        .properties(width=220, height=220)
        
    )
    

    center_text = alt.Chart(
        pd.DataFrame(
            [{"label": f"{total_minutes} min"}]
        )
    ).mark_text(
        fontSize=20,
        fontWeight="bold",
        color="white",   # ← THIS LINE
    ).encode(
        text="label:N"
    )
    
    col_left, col_spacer = st.columns([4, 5])

    with col_left:
        st.altair_chart(donut + center_text, width="stretch")






# --------------------------------------------------
# Data transformations
# --------------------------------------------------

from collections import defaultdict
from datetime import date

def _weekly_minutes_by_activity(sessions):
    """
    sessions: list[dict] as returned by get_sessions_between
    """
    data = defaultdict(lambda: defaultdict(int))

    for s in sessions:
         # Skip rest days: they are rhythm, not load
        if s.get("activity_type") == "rest":
            continue
        
        session_date = date.fromisoformat(s["session_date"])
        year, week, _ = session_date.isocalendar()
        week_key = f"{year}-W{week:02d}"

        activity = s["activity_type"]
        minutes = s["duration_minutes"] or 0

        data[week_key][activity] += minutes

    return data

# --------------------------------------------------
# Activities - Period composition visibility
# --------------------------------------------------
def _should_show_period_composition(range_key: str) -> bool:
    return range_key in {"1m", "3m", "6m"}

# --------------------------------------------------
# Helpers
# --------------------------------------------------

# Format delta values with sign
def _format_delta(value: int | None) -> str:
    if value is None:
        return ""
    if value > 0:
        return f"+{value}"
    return str(value)

from collections import defaultdict


# Aggregate total minutes by activity type, excluding rest sessions
def _aggregate_minutes_by_activity(sessions):
    totals = defaultdict(int)

    for s in sessions:
        if s["activity_type"] == "rest":
            continue

        minutes = s.get("duration_minutes") or 0
        totals[s["activity_type"]] += minutes

    return totals


