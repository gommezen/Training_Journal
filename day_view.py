from datetime import date

import pandas as pd
import streamlit as st

from db import load_sessions, soft_delete_by_uuid


def render_day_view() -> None:
    st.title("Reflection")
    st.markdown("Review your training, rest, and readiness for a specific day.")

    # --- Date selector ---
    selected_date = st.date_input(
        "Select date",
        value=date.today(),
    )

    df = load_sessions()
    if df.empty:
        st.info("No sessions logged yet.")
        return

    df["session_date"] = pd.to_datetime(df["session_date"]).dt.date

    day_sessions = df[df["session_date"] == selected_date]

    if day_sessions.empty:
        st.info("No training or rest logged for this day.")
        st.caption("You may still want to reflect on how you felt.")
        return

    # --- Sessions for the day ---
    for _, row in day_sessions.sort_values("created_at").iterrows():
        st.subheader(row["activity_type"].capitalize())

        cols = st.columns(3)
        cols[0].metric("Duration", f"{row['duration_minutes']} min")
        cols[1].metric("Energy", row["energy_level"])
        cols[2].metric("Emphasis", row["session_emphasis"])

        if row["notes"]:
            st.markdown(f"**Notes:** {row['notes']}")

        # --- Delete action ---
        with st.expander("⚠️ Session actions"):
            if st.button(
                "🗑 Delete this session",
                key=f"delete_{row['uuid']}",
            ):
                soft_delete_by_uuid(row["uuid"])
                st.success("Session deleted")
                st.rerun()

        st.divider()
