import requests
from typing import Dict, Any

import streamlit as st

from db import (
    get_state,
    set_state,
    local_changes_since,
    upsert_many,
)

# ---------------------------------------------------------------------
# Core sync engine
# ---------------------------------------------------------------------

def sync_now(base_url: str, sync_token: str) -> Dict[str, Any]:
    # 🔎 DEBUG — TEMPORARY (REMOVE AFTER DEBUGGING)
  

    session = requests.Session()
    session.headers.update({
        "X-Sync-Token": sync_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "KarateJournalSync/1.0",
    })

    # ---------------- PUSH ----------------
    last_push = get_state("last_push")
    to_push = local_changes_since(last_push)

    pushed = 0
    if to_push:
        r = session.post(
            f"{base_url}/api/sync.php",
            json={"items": to_push},
            timeout=30,
        )

        if not r.headers.get("content-type", "").startswith("application/json"):
            raise RuntimeError(f"Push failed (non-JSON): {r.text[:500]}")

        r.raise_for_status()
        data = r.json()

        pushed = int(data.get("upserted", 0))
        set_state("last_push", max(x["updated_at"] for x in to_push))

    # ---------------- PULL ----------------
    last_pull = get_state("last_pull")
    r = session.get(
        f"{base_url}/api/sync.php",
        params={"since": last_pull},
        timeout=30,
    )

    if not r.headers.get("content-type", "").startswith("application/json"):
        raise RuntimeError(f"Pull failed (non-JSON): {r.text[:500]}")

    r.raise_for_status()
    items = r.json()

    # 🔎 DEBUG — TEMPORARY
    #print("SYNC PULL ITEMS:", items)

    upserted_locally = upsert_many(items)

    if items:
        set_state("last_pull", max(x["updated_at"] for x in items))

    return {
        "pushed": pushed,
        "pulled": len(items),
        "upserted_locally": upserted_locally,
    }


# ---------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------

def render_sync_screen() -> None:
    st.title("Sync")
    st.caption("Offline ↔ Online synchronization")

    base_url = st.secrets["BASE_URL"]
    sync_token = st.secrets["SYNC_TOKEN"]

    # ---- Current sync state ----
    col1, col2 = st.columns(2)
    col1.metric("Last push", get_state("last_push"))
    col2.metric("Last pull", get_state("last_pull"))

    st.divider()

    if st.button("Sync now"):
        try:
            res = sync_now(base_url, sync_token)
            st.success("Sync complete ✅")
            st.json(res)

            # Force UI refresh so metrics update
            st.rerun()

        except Exception as e:
            st.error(f"Sync failed: {e}")
