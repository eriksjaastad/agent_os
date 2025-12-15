# core/db.py
import os
import sqlite3
from contextlib import contextmanager

# CONFIGURABLE: Database path can be set via environment variable.
# This allows different environments (dev, prod, testing) to use different databases.
# Default: "agent_os.db" in current working directory
DB_PATH = os.getenv("AGENT_OS_DB_PATH", "agent_os.db")


def init_db():
    """
    Initialize the database schema.

    Creates the 'runs' and 'results' tables if they don't exist.
    This function is idempotent - safe to call multiple times.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # INTEGRITY: Enable foreign key enforcement.
    # SQLite has foreign keys disabled by default for backwards compatibility.
    # We enable them to ensure referential integrity between runs and results.
    cursor.execute("PRAGMA foreign_keys = ON")

    # Runs table: tracks every execution
    # Each run represents a single invocation of a collector plugin
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
    # INTEGRITY: Foreign key ensures every result is linked to a valid run.
    # IDEMPOTENCY: UNIQUE(provider, date) prevents duplicate entries for the same day.
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
            UNIQUE(provider, date),
            FOREIGN KEY (run_id) REFERENCES runs(id)
        )
    """)

    conn.commit()
    conn.close()


@contextmanager
def get_db():
    """
    Context manager for database connections.

    Ensures connections are properly closed after use, even if an exception occurs.
    Enables Row factory for dict-like access to query results.

    Usage:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM runs")

    Yields:
        sqlite3.Connection with Row factory enabled
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # INTEGRITY: Enable foreign key enforcement for this connection.
    # Must be set on each connection as it's not persisted.
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
    finally:
        conn.close()
