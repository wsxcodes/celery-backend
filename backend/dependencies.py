import sqlite3

from backend.config import DB_PATH


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT NOT NULL UNIQUE,
            customer_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            analysis_status TEXT NOT NULL DEFAULT 'pending',
            analysis_started_at TEXT,
            analysis_completed_at TEXT,
            analysis_cost INTEGER NOT NULL DEFAULT 0,
            file_size INTEGER
        )
    """)
    conn.commit()
    conn.close()
