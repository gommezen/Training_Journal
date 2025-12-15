import sqlite3
from typing import Dict, Any

import pandas as pd


DB_PATH = "training.db"


def get_connection() -> sqlite3.Connection:
    """
    Create a SQLite connection.

    `check_same_thread=False` is required because Streamlit may access
    the connection from different execution contexts.
    """
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def create_table() -> None:
    """
    Ensure the training_sessions table exists.
    Safe to call multiple times.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS training_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_date DATE NOT NULL,
                activity_type TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                energy_level INTEGER NOT NULL,
                session_emphasis TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def insert_session(session: Dict[str, Any]) -> None:
    """
    Insert a single training session.
    Expects a validated session dict from the UI layer.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO training_sessions (
                session_date,
                activity_type,
                duration_minutes,
                energy_level,
                session_emphasis,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session["session_date"],
                session["activity_type"],
                session["duration_minutes"],
                session["energy_level"],
                session["session_emphasis"],
                session["notes"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def load_sessions() -> pd.DataFrame:
    """
    Load all training sessions into a pandas DataFrame.
    """
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM training_sessions", conn)
    finally:
        conn.close()
