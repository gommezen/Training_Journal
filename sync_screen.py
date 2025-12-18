import streamlit as st
from sync import sync_now
from db import get_state


def render_sync_screen() -> None:
    st.title("Sync")
    st.caption("Offline ↔ Online sync status")

    base_url = st.secrets["BASE_URL"]
    sync_token = st.secrets["SYNC_TOKEN"]

    # ---- Status ----
    col1, col2 = st.columns(2)
    col1.metric("Last push", get_state("last_push"))
    col2.metric("Last pull", get_state("last_pull"))

    st.divider()
            
    if st.button("Sync now"):
        try:
            res = sync_now(base_url, sync_token)
            st.success("Sync complete ✅")
            st.json(res)

            # 🔄 Force re-render so metrics update
            st.rerun()
        except Exception as e:
            st.error(f"Sync failed: {e}")

