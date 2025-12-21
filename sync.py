import requests
from typing import Dict, Any

from db import (
    get_state,
    set_state,
    local_changes_since,
    upsert_many,
)

def sync_now(base_url: str, sync_token: str) -> Dict[str, Any]:
    session = requests.Session()
    session.headers.update({
        "X-Sync-Token": sync_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "KarateJournalSync/1.0",
    })

    # ---------------- PULL FIRST ----------------
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

    upserted_locally = upsert_many(items)

    if items:
        set_state("last_pull", max(x["updated_at"] for x in items))

    # ---------------- PUSH SECOND ----------------
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

    return {
        "pulled": len(items),
        "upserted_locally": upserted_locally,
        "pushed": pushed,
    }

