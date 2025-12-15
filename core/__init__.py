# Agent OS Core - The Kernel
"""
Core infrastructure for Agent OS.

This package provides the foundational components that all plugins and
applications build upon:

- db: SQLite database management (init_db, get_db)
- logger: Structured logging (setup_logger)
- export: Data export utilities (export_results_to_csv)

Usage:
    from core import init_db, get_db, setup_logger, export_results_to_csv
"""

from .db import init_db, get_db, DB_PATH
from .logger import setup_logger, LOG_FILE
from .export import export_results_to_csv, ALLOWED_TABLES

# Public API - what gets exported with "from core import *"
__all__ = [
    # Database
    "init_db",
    "get_db",
    "DB_PATH",
    # Logging
    "setup_logger",
    "LOG_FILE",
    # Export
    "export_results_to_csv",
    "ALLOWED_TABLES",
]
