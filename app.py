import streamlit as st

from infrastructure.db import create_table
from ui.log_screen import render_log_screen
from ui.stats import render_stats_screen
from ui.reflection import render_reflection_page
from ui.sync_screen import render_sync_screen
from infrastructure.db import update_session_by_uuid



def main() -> None:
    st.set_page_config(
        page_title="Karate Training Journal",
        layout="centered",
    )

    # Ensure database schema exists before rendering UI
    create_table()

    page = st.sidebar.radio(
        "Navigation",
        [
            "Log session",
            "Statistics",
            "Reflection",
            "Sync",  # NEW
        ],
    )

    if page == "Log session":
        render_log_screen()
    elif page == "Statistics":
        render_stats_screen()
    elif page == "Reflection":
        render_reflection_page()
    elif page == "Sync":
        render_sync_screen()


if __name__ == "__main__":
    main()
