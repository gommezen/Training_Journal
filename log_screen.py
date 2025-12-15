from datetime import date

import streamlit as st

from db import insert_session
from models import (
    ACTIVITIES,
    ENERGY_LABELS,
    ENERGY_MAP,
    SESSION_EMPHASIS,
)


def render_log_screen() -> None:
    st.title("Training Log")
    st.markdown("Log your session. Keep it light. Keep it honest.")

    with st.form("log_form", clear_on_submit=True):

        # --- Context ---
        session_date = st.date_input(
            "Date",
            value=date.today(),
        )

        activity_type = st.radio(
            "Activity",
            ACTIVITIES,
            horizontal=True,
        )

        # --- Load (always allow 0; validate later) ---
        duration_minutes = st.number_input(
            "Duration (minutes)",
            min_value=0,
            max_value=300,
            step=5,
            help="Use 0 for rest days",
        )

        # --- Session state ---
        energy_label = st.radio(
            "How did you feel?",
            ENERGY_LABELS,
            horizontal=True,
        )

        session_emphasis = st.radio(
            "Session emphasis",
            SESSION_EMPHASIS,
            horizontal=True,
        )

        # --- Reflection ---
        notes = st.text_input(
            "Key focus / takeaway",
            placeholder="Timing off, good snap, knee stiff…",
        )

        submitted = st.form_submit_button("Save session")

        if not submitted:
            return

        # --- Validation ---
        if activity_type != "rest" and duration_minutes < 5:
            st.error("Training sessions must be at least 5 minutes.")
            return

        # --- Persist ---
        insert_session(
            {
                "session_date": session_date.isoformat(),
                "activity_type": activity_type,
                "duration_minutes": duration_minutes,
                "energy_level": ENERGY_MAP[energy_label],
                "session_emphasis": session_emphasis,
                "notes": notes,
            }
        )

        st.success("Session saved.")
