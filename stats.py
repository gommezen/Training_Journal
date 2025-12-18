import pandas as pd
import streamlit as st
import plotly.express as px

from db import load_sessions
from models import ACTIVITIES


def render_stats_screen() -> None:
    st.title("Training Statistics")

    df = load_sessions()
    if df.empty:
        st.info("No sessions logged yet.")
        return

    # --- Time normalization ---
    df["session_date"] = pd.to_datetime(df["session_date"])

    # Stable weekly bucketing (aggregation-safe)
    # Pandas supports `.dt.to_period()` at runtime, but some type checkers
    # do not expose it on the `.dt` accessor in their stubs.
    # Weeks starting Monday (Mon–Sun)
    df["week"] = df["session_date"].dt.to_period("W-SUN").dt.start_time  # type: ignore[attr-defined]
    df["week"] = pd.to_datetime(df["week"]).dt.normalize()


    # --- Filters ---
    activity = st.selectbox("Activity", ["All"] + ACTIVITIES)
    time_range = st.selectbox("Time range", ["4 weeks", "3 months", "6 months"])

    weeks_back = {
        "4 weeks": 4,
        "3 months": 12,
        "6 months": 24,
    }[time_range]

    cutoff = pd.Timestamp.today() - pd.Timedelta(weeks=weeks_back)
    df = df[df["session_date"] >= cutoff]

    if activity != "All":
        df = df[df["activity_type"] == activity]

    if df.empty:
        st.info("No data for this selection.")
        return

    # --- Summary metrics ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total minutes", int(df["duration_minutes"].sum()))
    col2.metric("Sessions", len(df))
    col3.metric("Avg energy", round(df["energy_level"].mean(), 2))

    st.caption(
        f"Showing {len(df)} sessions from "
        f"{df['session_date'].min().date()} to {df['session_date'].max().date()}"
    )

    # --- Weekly volume ---
    weekly_duration = (
        df.groupby("week", as_index=False)
        .agg(duration_minutes=("duration_minutes", "sum"))
        .sort_values("week")
    )

    # Create categorical week labels
    weekly_duration["week_label"] = weekly_duration["week"].dt.strftime("%Y-%m-%d") # type: ignore[attr-defined]

    st.plotly_chart(
        px.bar(
            weekly_duration,
            x="week_label",
            y="duration_minutes",
            title="Weekly training volume",
            labels={
                "week_label": "Week starting",
                "duration_minutes": "Minutes",
            },
        ),
        width="stretch" #use_container_width=True,
    )

    # --- Weekly energy ---
    weekly_energy = (
        df.groupby("week", as_index=False)
        .agg(energy_level=("energy_level", "mean"))
        .sort_values("week")
    )

    weekly_energy["week_label"] = weekly_energy["week"].dt.strftime("%Y-%m-%d") # type: ignore[attr-defined]

    st.plotly_chart(
        px.line(
            weekly_energy,
            x="week_label",
            y="energy_level",
            title="Average energy per week",
            labels={
                "week_label": "Week starting",
                "energy_level": "Energy (1–5)",
            },
            markers=True,
        ),
        width="stretch" #use_container_width=True,
    )

    # --- Recent notes ---
    st.subheader("Recent notes")

    recent = df.sort_values("session_date", ascending=False).head(5)

    for _, row in recent.iterrows():
        st.markdown(
            f"**{row['session_date'].date()} – {row['activity_type']}**  \n"
            f"{row['notes'] if row['notes'] else '_No notes_'}"
        )
