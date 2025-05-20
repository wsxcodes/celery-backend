import sqlite3

from openai import AzureOpenAI

from backend import config
from backend.config import DB_PATH

ai_client = AzureOpenAI(
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    api_version=config.OPENAI_API_VERSION
)


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
            file_preview TEXT,
            uploaded_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            analysis_status TEXT NOT NULL DEFAULT 'pending',
            analysis_started_at TEXT,
            analysis_completed_at TEXT,
            analysis_cost INTEGER NOT NULL DEFAULT 0,
            ai_alert TEXT,
            ai_expires TEXT,
            ai_is_expired INTEGER,
            ai_category TEXT,
            ai_sub_category TEXT,
            ai_summary_short TEXT,
            ai_summary_long TEXT,
            ai_analysis_criteria TEXT,
            ai_features_and_insights TEXT,
            ai_alerts_and_actions TEXT,
            ai_enterny_legacy_schema TEXT,
            file_size INTEGER,
            document_raw_text TEXT,
            health_score INTEGER DEFAULT 0
        )
    """)
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_uuid TEXT NOT NULL,
            message_type TEXT NOT NULL CHECK(message_type IN ('question', 'answer')),
            content TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')),
            FOREIGN KEY (document_uuid) REFERENCES files(uuid) ON DELETE CASCADE
        )
    """)
    conn.close()
