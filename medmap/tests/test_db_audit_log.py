"""Test audit log entries in production database."""

import os
import sys
import sqlite3
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import DB_DIR

DB_PATH = os.path.join(DB_DIR, "medmap.db")


@pytest.fixture
def db_conn():
    if not os.path.exists(DB_PATH):
        pytest.skip("Production DB not found")
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()


class TestAuditLogCategories:
    """Verify audit log has expected error categories."""

    def test_has_missing_value_entries(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbAuditLog WHERE error_type='MISSING_VALUE'")
        assert cur.fetchone()[0] > 0

    def test_has_severity_values(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT DISTINCT severity FROM tbAuditLog")
        values = {r[0] for r in cur.fetchall()}
        assert len(values) > 0

    def test_severity_values_valid(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT DISTINCT severity FROM tbAuditLog")
        values = {r[0] for r in cur.fetchall()}
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        assert values <= valid, f"Unexpected severity values: {values - valid}"

    def test_action_taken_values_valid(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT DISTINCT action_taken FROM tbAuditLog")
        values = {r[0] for r in cur.fetchall()}
        valid = {"QUARANTINE", "AUTO_CORRECT", "FLAGGED", "ACCEPTED", "MANUAL_CORRECT", "ROLLBACK"}
        assert values <= valid, f"Unexpected action values: {values - valid}"

    def test_has_case_ids(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT case_id) FROM tbAuditLog WHERE case_id IS NOT NULL")
        assert cur.fetchone()[0] > 0

    def test_has_table_names(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT table_name) FROM tbAuditLog WHERE table_name IS NOT NULL")
        assert cur.fetchone()[0] > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
