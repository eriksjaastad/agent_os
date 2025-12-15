# core/db.py
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "agent_os.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Runs table: tracks every execution
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            plugin_name TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            error TEXT
        )
    """)
    
    # Results table: stores normalized billing data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            date TEXT NOT NULL,
            tokens INTEGER,
            cost REAL,
            raw_json TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(provider, date)
        )
    """)
    
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
