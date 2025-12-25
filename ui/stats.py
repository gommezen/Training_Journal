from datetime import date
from typing import List

import pandas as pd
import streamlit as st
import plotly.express as px

from infrastructure.db import get_sessions_between
from domain.time_ranges import resolve_time_range
from domain.weeks import WeekSummary, build_week_summaries


# --------------------------------------------------
# Public entry point (called from app.py)
# --------------------------------------------------

def render_stats_screen() -> None:
    st.title("Training Statistics")

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
    _render_week_load_chart(weeks)
    _render_week_notes_stub()


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


def _render_week_load_chart(weeks: List[WeekSummary]) -> None:
    st.subheader("Weekly training load")

    df = pd.DataFrame({
        "Week": [w.week_id for w in weeks],
        "Minutes": [w.total_duration for w in weeks],
    })

    st.plotly_chart(
        px.bar(
            df,
            x="Week",
            y="Minutes",
            labels={"Minutes": "Total minutes"},
        ),
        width="stretch",
    )


def _render_week_notes_stub() -> None:
    st.subheader("Reflection (coming later)")
    st.caption(
        "This section will later connect weekly structure with RPE and notes. "
        "Use the table above to identify weeks worth reflecting on."
    )


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _format_delta(value: int | None) -> str:
    if value is None:
        return ""
    if value > 0:
        return f"+{value}"
    return str(value)

