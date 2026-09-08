import sqlite3
from contextlib import closing

from config import DB_PATH

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                status TEXT DEFAULT 'pending',
                requested_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def add_or_update_request(user_id: int, username: str, full_name: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, full_name, status)
            VALUES (?, ?, ?, 'pending')
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                status='pending'
        """, (user_id, username, full_name))
        conn.commit()

def set_status(user_id: int, status: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("UPDATE users SET status=? WHERE user_id=?", (status, user_id))
        conn.commit()

def get_user(user_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            "SELECT user_id, username, full_name, status, requested_at FROM users WHERE user_id=?",
            (user_id,)
        )
        return cur.fetchone()

def list_users(status: str = None):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        if status:
            cur = conn.execute(
                "SELECT user_id, username, full_name, status, requested_at "
                "FROM users WHERE status=? ORDER BY requested_at DESC",
                (status,)
            )
        else:
            cur = conn.execute(
                "SELECT user_id, username, full_name, status, requested_at "
                "FROM users ORDER BY requested_at DESC"
            )
        return cur.fetchall()
