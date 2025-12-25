import streamlit as st

from infrastructure.db import create_table
from ui.log_screen import render_log_screen
from ui.stats import render_stats_screen
from ui.day_view import render_day_view
from ui.sync_screen import render_sync_screen  # NEW


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
        render_day_view()
    elif page == "Sync":
        render_sync_screen()


if __name__ == "__main__":
    main()
