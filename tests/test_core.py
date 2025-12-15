# tests/test_core.py
"""
Tests for Agent OS core functionality.

These tests verify the kernel infrastructure works correctly:
- Database initialization and connections
- Export functionality with SQL injection protection
- Logger configuration

Run with: pytest tests/test_core.py -v
"""
import os
import tempfile
import pytest

# Create a temp file for the test database BEFORE importing modules
# Note: :memory: doesn't work because each connection gets a separate database
_test_db_fd, _test_db_path = tempfile.mkstemp(suffix=".db")
os.close(_test_db_fd)

# Set test environment variables BEFORE importing modules
# This ensures tests use isolated database and log files
os.environ["AGENT_OS_DB_PATH"] = _test_db_path
os.environ["AGENT_OS_LOG_FILE"] = "/dev/null"  # Discard logs during tests

from core.db import init_db, get_db
from core.export import export_results_to_csv, ALLOWED_TABLES


def teardown_module():
    """Clean up temp database after all tests"""
    if os.path.exists(_test_db_path):
        os.unlink(_test_db_path)


class TestDatabase:
    """Tests for core/db.py"""

    def test_init_db_creates_tables(self):
        """Verify init_db creates the expected tables"""
        init_db()

        with get_db() as conn:
            cursor = conn.cursor()

            # Check runs table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='runs'"
            )
            assert cursor.fetchone() is not None, "runs table should exist"

            # Check results table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='results'"
            )
            assert cursor.fetchone() is not None, "results table should exist"

    def test_get_db_returns_connection_with_row_factory(self):
        """Verify get_db returns a connection with Row factory enabled"""
        init_db()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 as test_column")
            row = cursor.fetchone()

            # Row factory should allow dict-like access
            assert row["test_column"] == 1

    def test_init_db_is_idempotent(self):
        """Verify init_db can be called multiple times safely"""
        # Should not raise any errors when called multiple times
        init_db()
        init_db()
        init_db()

        with get_db() as conn:
            cursor = conn.cursor()
            # Check for our specific tables (not sqlite internal tables like sqlite_sequence)
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('runs', 'results')"
            )
            count = cursor.fetchone()[0]
            assert count == 2, "Should have exactly runs and results tables"


class TestExport:
    """Tests for core/export.py"""

    def test_export_rejects_invalid_table_names(self):
        """Verify SQL injection protection works"""
        init_db()

        with get_db() as conn:
            # These should all raise ValueError
            invalid_tables = [
                "users; DROP TABLE runs;--",
                "results UNION SELECT * FROM runs",
                "../../../etc/passwd",
                "nonexistent_table",
            ]

            for invalid_table in invalid_tables:
                with pytest.raises(ValueError) as exc_info:
                    export_results_to_csv(conn, table=invalid_table)

                assert "Invalid table name" in str(exc_info.value)

    def test_export_accepts_valid_table_names(self):
        """Verify allowed tables can be exported"""
        init_db()

        with get_db() as conn:
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
                temp_path = f.name

            try:
                for table in ALLOWED_TABLES:
                    result_path = export_results_to_csv(
                        conn, output_path=temp_path, table=table
                    )
                    assert os.path.exists(result_path)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def test_allowed_tables_contains_expected_values(self):
        """Verify ALLOWED_TABLES whitelist is correct"""
        assert "results" in ALLOWED_TABLES
        assert "runs" in ALLOWED_TABLES
        assert len(ALLOWED_TABLES) == 2  # Only these two tables


class TestLogger:
    """Tests for core/logger.py"""

    def test_setup_logger_is_idempotent(self):
        """Verify setup_logger doesn't add duplicate handlers"""
        from core.logger import setup_logger

        logger1 = setup_logger("test_logger")
        initial_handler_count = len(logger1.handlers)

        # Call setup_logger again with same name
        logger2 = setup_logger("test_logger")

        # Should return same logger instance
        assert logger1 is logger2

        # Should not have added more handlers
        assert len(logger2.handlers) == initial_handler_count


# Marker for tests that require network access (skip in CI)
# Usage: @pytest.mark.network
# Run with: pytest -m "not network" to skip these

