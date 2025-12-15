import streamlit as st

from db import create_table
from log_screen import render_log_screen
from stats import render_stats_screen
from day_view import render_day_view



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
        ],

    )

    if page == "Log session":
        render_log_screen()
    elif page == "Reflection":
        render_day_view()
    else:
        render_stats_screen()



if __name__ == "__main__":
    main()


