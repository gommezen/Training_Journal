import sqlite3
from typing import Dict, Any, List
import uuid as uuidlib
from datetime import datetime, timezone

import pandas as pd

DB_PATH = "training.db"


# ---------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------

def utc_now_sql() -> str:
    """UTC timestamp in MySQL-compatible format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# ---------------------------------------------------------------------
# Schema & migration
# ---------------------------------------------------------------------

def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r[1] for r in rows]


def _ensure_base_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS training_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            energy_level INTEGER NOT NULL,
            session_emphasis TEXT NOT NULL,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )


def _migrate_training_sessions(conn: sqlite3.Connection) -> None:
    _ensure_base_table(conn)
    cols = set(_table_columns(conn, "training_sessions"))

    if "uuid" not in cols:
        conn.execute("ALTER TABLE training_sessions ADD COLUMN uuid TEXT")
    if "deleted" not in cols:
        conn.execute("ALTER TABLE training_sessions ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0")
    if "updated_at" not in cols:
        conn.execute("ALTER TABLE training_sessions ADD COLUMN updated_at TEXT")

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_training_sessions_uuid "
        "ON training_sessions(uuid)"
    )

    rows = conn.execute(
        "SELECT id, created_at, uuid, updated_at FROM training_sessions"
    ).fetchall()

    for row_id, created_at, u, updated in rows:
        if not u:
            u = str(uuidlib.uuid4())
        if not updated:
            updated = created_at or utc_now_sql()

        conn.execute(
            "UPDATE training_sessions SET uuid=?, updated_at=? WHERE id=?",
            (u, updated, row_id),
        )


def _ensure_sync_state(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO sync_state(key, value) "
        "VALUES ('last_pull', '1970-01-01 00:00:00')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO sync_state(key, value) "
        "VALUES ('last_push', '1970-01-01 00:00:00')"
    )


def create_table() -> None:
    conn = get_connection()
    try:
        _migrate_training_sessions(conn)
        _ensure_sync_state(conn)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Sync state helpers
# ---------------------------------------------------------------------

def get_state(key: str, default: str = "1970-01-01 00:00:00") -> str:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM sync_state WHERE key=?",
            (key,),
        ).fetchone()
        return row[0] if row else default
    finally:
        conn.close()


def set_state(key: str, value: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO sync_state(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------

def insert_session(session: Dict[str, Any]) -> None:
    conn = get_connection()
    try:
        u = session.get("uuid") or str(uuidlib.uuid4())
        updated_at = session.get("updated_at") or utc_now_sql()

        conn.execute(
            """
            INSERT INTO training_sessions (
                session_date,
                activity_type,
                duration_minutes,
                energy_level,
                session_emphasis,
                notes,
                uuid,
                deleted,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                session["session_date"],
                session["activity_type"],
                session["duration_minutes"],
                session["energy_level"],
                session["session_emphasis"],
                session.get("notes"),
                u,
                updated_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def load_sessions() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql(
            "SELECT * FROM training_sessions WHERE deleted = 0",
            conn,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Sync primitives
# ---------------------------------------------------------------------

def local_changes_since(ts: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT session_date, activity_type, duration_minutes, energy_level,
                   session_emphasis, notes, uuid, deleted, updated_at
            FROM training_sessions
            WHERE updated_at > ?
            """,
            (ts,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()

def upsert_many(items: List[Dict[str, Any]]) -> int:
    if not items:
        return 0

    conn = get_connection()
    try:
        count = 0
        for it in items:
            # If remote row is deleted → remove locally
            if int(it.get("deleted", 0)) == 1:
                conn.execute(
                    "DELETE FROM training_sessions WHERE uuid = ?",
                    (it["uuid"],),
                )
                continue

            # Otherwise upsert normally
            conn.execute(
                """
                INSERT INTO training_sessions (
                    session_date, activity_type, duration_minutes, energy_level,
                    session_emphasis, notes, uuid, deleted, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(uuid) DO UPDATE SET
                    session_date=excluded.session_date,
                    activity_type=excluded.activity_type,
                    duration_minutes=excluded.duration_minutes,
                    energy_level=excluded.energy_level,
                    session_emphasis=excluded.session_emphasis,
                    notes=excluded.notes,
                    deleted=0,
                    updated_at=excluded.updated_at
                WHERE excluded.updated_at > training_sessions.updated_at
                """,
                (
                    it["session_date"],
                    it["activity_type"],
                    int(it["duration_minutes"]),
                    int(it["energy_level"]),
                    it["session_emphasis"],
                    it.get("notes"),
                    it["uuid"],
                    it["updated_at"],
                ),
            )
            count += 1

        conn.commit()
        return count
    finally:
        conn.close()


# def upsert_many(items: List[Dict[str, Any]]) -> int:
#     if not items:
#         return 0

#     conn = get_connection()
#     try:
#         count = 0
#         for it in items:
#             conn.execute(
#                 """
#                 INSERT INTO training_sessions (
#                     session_date, activity_type, duration_minutes, energy_level,
#                     session_emphasis, notes, uuid, deleted, updated_at
#                 )
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#                 ON CONFLICT(uuid) DO UPDATE SET
#                     session_date=excluded.session_date,
#                     activity_type=excluded.activity_type,
#                     duration_minutes=excluded.duration_minutes,
#                     energy_level=excluded.energy_level,
#                     session_emphasis=excluded.session_emphasis,
#                     notes=excluded.notes,
#                     deleted=excluded.deleted,
#                     updated_at=excluded.updated_at
#                 WHERE excluded.updated_at > training_sessions.updated_at
#                 """,
#                 (
#                     it["session_date"],
#                     it["activity_type"],
#                     int(it["duration_minutes"]),
#                     int(it["energy_level"]),
#                     it["session_emphasis"],
#                     it.get("notes"),
#                     it["uuid"],
#                     int(it.get("deleted", 0)),
#                     it["updated_at"],
#                 ),
#             )
#             count += 1

#         conn.commit()
#         return count
#     finally:
#         conn.close()

def soft_delete_by_uuid(uuid: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE training_sessions
            SET deleted = 1,
                updated_at = ?
            WHERE uuid = ?
            """,
            (utc_now_sql(), uuid),
        )
        conn.commit()
    finally:
        conn.close()
