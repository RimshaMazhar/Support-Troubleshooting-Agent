import json
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "conversations.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            route TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def add_message(conversation_id: str, role: str, message: str, route: str = None):
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (conversation_id, role, message, route) VALUES (?, ?, ?, ?)",
        (conversation_id, role, message, route),
    )
    conn.commit()
    conn.close()


MAX_HISTORY_MESSAGES = 20  # last 20 messages = last 10 turns (user+bot)


def get_history(conversation_id: str, limit: int = MAX_HISTORY_MESSAGES):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT role, message, route, created_at FROM (
            SELECT role, message, route, created_at, id
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
        ) ORDER BY id
        """,
        (conversation_id, limit),
    ).fetchall()
    conn.close()
    return [{"role": r[0], "message": r[1], "route": r[2], "created_at": r[3]} for r in rows]


def conversation_exists(conversation_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM messages WHERE conversation_id = ? LIMIT 1", (conversation_id,)
    ).fetchone()
    conn.close()
    return row is not None


def count_turns(conversation_id: str) -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conversation_id,)
    ).fetchone()
    conn.close()
    return row[0] // 2