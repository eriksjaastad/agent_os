# core/export.py
"""Generic data export utilities for agent_os"""
import csv
from datetime import datetime
from pathlib import Path

def export_results_to_csv(db_conn, output_path: str = None, table: str = "results"):
    """
    Generic CSV export from any table in the database.
    
    Args:
        db_conn: Database connection
        output_path: Where to save CSV (defaults to timestamped filename)
        table: Which table to export (default: "results")
    
    Returns:
        Path to created CSV file
    """
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"export_{table}_{timestamp}.csv"
    
    cursor = db_conn.cursor()
    
    # Get all columns from table
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Get all data
    cursor.execute(f"SELECT * FROM {table} ORDER BY created_at DESC" if "created_at" in columns else f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    
    # Write to CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    
    return output_path
