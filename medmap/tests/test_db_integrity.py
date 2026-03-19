"""Test production database integrity checks."""

import os
import sys
import sqlite3
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import DB_DIR

DB_PATH = os.path.join(DB_DIR, "medmap.db")


@pytest.fixture
def db_conn():
    """Open connection to production DB."""
    if not os.path.exists(DB_PATH):
        pytest.skip("Production DB not found")
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()


class TestDatabaseTables:
    """Verify all expected tables exist."""

    def test_tbCaseData_exists(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tbCaseData'")
        assert cur.fetchone() is not None

    def test_tbImportLabsData_exists(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tbImportLabsData'")
        assert cur.fetchone() is not None

    def test_tbImportIcd10Data_exists(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tbImportIcd10Data'")
        assert cur.fetchone() is not None

    def test_tbImportAcData_exists(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tbImportAcData'")
        assert cur.fetchone() is not None

    def test_tbImportDeviceMotionData_exists(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tbImportDeviceMotionData'")
        assert cur.fetchone() is not None

    def test_tbImportDevice1HzMotionData_exists(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tbImportDevice1HzMotionData'")
        assert cur.fetchone() is not None

    def test_tbImportMedicationInpatientData_exists(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tbImportMedicationInpatientData'")
        assert cur.fetchone() is not None

    def test_tbImportNursingDailyReportsData_exists(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tbImportNursingDailyReportsData'")
        assert cur.fetchone() is not None

    def test_tbAuditLog_exists(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tbAuditLog'")
        assert cur.fetchone() is not None

    def test_tbDataPassport_exists(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tbDataPassport'")
        assert cur.fetchone() is not None


class TestDatabaseRowCounts:
    """Verify tables have reasonable row counts."""

    def test_case_data_not_empty(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbCaseData")
        assert cur.fetchone()[0] > 0

    def test_labs_data_not_empty(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportLabsData")
        assert cur.fetchone()[0] > 0

    def test_icd10_data_not_empty(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportIcd10Data")
        assert cur.fetchone()[0] > 0

    def test_medication_data_not_empty(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportMedicationInpatientData")
        assert cur.fetchone()[0] > 0

    def test_nursing_data_not_empty(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportNursingDailyReportsData")
        assert cur.fetchone()[0] > 0

    def test_device_motion_not_empty(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportDeviceMotionData")
        assert cur.fetchone()[0] > 0

    def test_audit_log_not_empty(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbAuditLog")
        assert cur.fetchone()[0] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
