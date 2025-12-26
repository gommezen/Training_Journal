import streamlit as st
from datetime import date

from infrastructure.db import (
    load_sessions,
    soft_delete_by_uuid,
    update_session_by_uuid,  # 👈 DEN MANGLEDE
)
from ui.reflection_helpers import (
    resolve_current_and_previous_period,
    filter_sessions_by_date,
    compute_period_summary,
    compute_phase_deltas,
)

def render_reflection_page() -> None:
    st.title("Reflection")
    st.caption("Review training experience with structural context.")

    sessions_df = load_sessions()
    if sessions_df.empty:
        st.info("No sessions logged yet.")
        return
    
    # TEMP DEBUG — inspect SQLite RPE values #delete
    # st.write(
    #     sessions_df[["session_date", "activity_type","duration_minutes", "rpe"]].head(15)
    # )

    sessions = sessions_df.to_dict("records")

    # --------------------------------------------------
    # Reflection context (NEW)
    # --------------------------------------------------
    st.subheader("Reflection context")

    range_key = st.selectbox(
        "Context period",
        ["1m", "3m", "6m"],
        format_func=lambda k: {
            "1m": "1 month",
            "3m": "3 months",
            "6m": "6 months",
        }[k],
    )

    today = date.today()
    cur_start, cur_end, prev_start, prev_end = (
        resolve_current_and_previous_period(range_key, today)
    )

    # Filter sessions into current and previous periods
    cur_sessions = filter_sessions_by_date(sessions, cur_start, cur_end)
    prev_sessions = filter_sessions_by_date(sessions, prev_start, prev_end)

    
    # Compute summaries (may be partial if RPE is missing)
    cur_summary = compute_period_summary(cur_sessions)
    prev_summary = compute_period_summary(prev_sessions)
    
    # Compute deltas (may return None or incomplete dict)
    deltas = compute_phase_deltas(cur_summary, prev_summary)

    # --- Render ---
    if cur_summary:
        _render_period_summary(
            cur_start,
            cur_end,
            cur_summary,
        )

    # Always render comparison section.
    # Missing values are displayed as "—" inside the renderer.
    _render_phase_deltas(deltas or {})
    
    # DEBUG
    # st.write("DEBUG cur_summary:", cur_summary)
    # st.write("DEBUG prev_summary:", prev_summary)
    # st.write("DEBUG deltas:", deltas)

    st.divider()

    # --------------------------------------------------
    # Daily / session review (old day_view, refined)
    # --------------------------------------------------
    _render_daily_sessions(sessions)


def _render_period_summary(start, end, summary):
    st.markdown(f"**Period:** {start} → {end}")

    cols = st.columns(3)
    cols[0].metric("Sessions", summary["sessions"])
    cols[1].metric("Total minutes", summary["total_minutes"])
    cols[2].metric("Active days", summary["active_days"])

    cols = st.columns(3)
    cols[0].metric("Max gap (days)", summary["max_gap"])
    cols[1].metric("Dominant activity", summary["dominant_activity"] or "—")
    cols[2].metric("Load density", summary["load_density"] or "—")

def _render_phase_deltas(deltas):
    st.subheader("Period comparison")

    st.markdown("**Load & volume**")
    cols = st.columns(2)
    cols[0].metric(
        "Δ minutes",
        deltas.get("delta_minutes", "—")
    )
    cols[1].metric(
        "Δ load density",
        deltas.get("delta_load_density") or "—"
    )

    st.markdown("**Rhythm & continuity**")
    cols = st.columns(2)
    cols[0].metric(
        "Δ active days",
        deltas.get("delta_active_days", "—")
    )
    cols[1].metric(
        "Δ max gap",
        deltas.get("delta_max_gap", "—")
    )

    if deltas.get("dominant_activity_changed"):
        st.caption(
            "Activity emphasis changed compared to previous period."
        )
    
    # delete this block if not needed
    if not deltas:
        st.caption(
            "No previous period available for comparison."
        )
        return



#--------------------------------------------------
# Daily / session review
#--------------------------------------------------

def _render_daily_sessions(sessions) -> None:
    
    
    st.subheader("Daily review")

    selected_date = st.date_input(
        "Select date",
        value=date.today(),
        key="reflection_day_selector",
    )

    day_sessions = [
        s for s in sessions
        if date.fromisoformat(s["session_date"]) == selected_date
        and not s.get("deleted", False)
    ]

    if not day_sessions:
        st.info("No training or rest logged for this day.")
        st.caption("You may still want to reflect on how you felt.")
        return

    for s in sorted(day_sessions, key=lambda x: x["created_at"]):
        #st.write("Raw RPE value:", s.get("rpe")) #delete
        st.subheader(s["activity_type"].capitalize())
        

        cols = st.columns(4)

        cols[0].metric("Duration", f"{s['duration_minutes']} min")
        cols[1].metric("Energy", s["energy_level"])
        cols[2].metric("Emphasis", s["session_emphasis"])

        with cols[3]:
            new_rpe = st.number_input(
                "RPE",
                min_value=1,
                max_value=10,
                value=s.get("rpe") or 5,
                step=1,
                key=f"rpe_{s['uuid']}",
            )

            if new_rpe != s.get("rpe"):
                if st.button("Save", key=f"save_rpe_{s['uuid']}"):
                    update_session_by_uuid(
                        s["uuid"],
                        {"rpe": new_rpe}
                    )
                    st.success("RPE updated")
                    st.rerun()



        if s.get("notes"):
            st.markdown(f"**Notes:** {s['notes']}")

        
        # if st.button(
        #     "Delete session",
        #     key=f"delete_{s['uuid']}",
        # ):
        #     soft_delete_by_uuid(s["uuid"])
        #     st.success("Session deleted")
        #     st.rerun()
       
         
        delete_key = f"confirm_delete_{s['uuid']}"

        if st.button(
            "Delete session",
            key=f"delete_{s['uuid']}",
        ):
            st.session_state[delete_key] = True

        if st.session_state.get(delete_key):
            st.warning("This will permanently remove this session.")
            cols = st.columns(2)

            with cols[0]:
                if st.button("Confirm delete", key=f"confirm_{s['uuid']}"):
                    soft_delete_by_uuid(s["uuid"])
                    st.success("Session deleted")
                    del st.session_state[delete_key]
                    st.rerun()

            with cols[1]:
                if st.button("Cancel", key=f"cancel_{s['uuid']}"):
                    del st.session_state[delete_key]
        
                    st.info("Deletion cancelled.")
        st.divider()
