# core/export.py
"""Generic data export utilities for agent_os"""
import csv
from datetime import datetime
from pathlib import Path

# SECURITY: Whitelist of allowed table names to prevent SQL injection.
# The table parameter is used in SQL queries, so we must validate it against
# a known-safe list rather than interpolating user input directly.
ALLOWED_TABLES = {"results", "runs"}


def export_results_to_csv(db_conn, output_path: str = None, table: str = "results"):
    """
    Generic CSV export from any table in the database.

    Args:
        db_conn: Database connection
        output_path: Where to save CSV (defaults to timestamped filename)
        table: Which table to export (default: "results")
              Must be one of: "results", "runs"

    Returns:
        Path to created CSV file

    Raises:
        ValueError: If table name is not in the allowed whitelist
    """
    # SECURITY: Validate table name against whitelist to prevent SQL injection.
    # Even though this function is currently only called with hardcoded values,
    # we enforce this check to prevent vulnerabilities if the function is reused
    # or exposed to user input in the future.
    if table not in ALLOWED_TABLES:
        raise ValueError(
            f"Invalid table name: '{table}'. "
            f"Must be one of: {', '.join(sorted(ALLOWED_TABLES))}"
        )

    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"export_{table}_{timestamp}.csv"

    cursor = db_conn.cursor()

    # Get all columns from table
    # NOTE: Table name is safe here because we validated it above against ALLOWED_TABLES
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]

    # Get all data, ordered by created_at if that column exists
    # NOTE: Table name is safe here because we validated it above against ALLOWED_TABLES
    if "created_at" in columns:
        cursor.execute(f"SELECT * FROM {table} ORDER BY created_at DESC")
    else:
        cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()

    # Write to CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    return output_path
