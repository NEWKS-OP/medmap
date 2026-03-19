"""Test production database row counts are within expected ranges."""

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


class TestCaseDataCount:
    """Test tbCaseData row count."""

    def test_min_cases(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbCaseData")
        assert cur.fetchone()[0] >= 100

    def test_max_cases(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbCaseData")
        assert cur.fetchone()[0] <= 7000


class TestLabsDataCount:
    """Test tbImportLabsData row count."""

    def test_min_labs(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportLabsData")
        assert cur.fetchone()[0] >= 500

    def test_max_labs(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportLabsData")
        assert cur.fetchone()[0] <= 50000


class TestICD10DataCount:
    """Test tbImportIcd10Data row count."""

    def test_min_icd10(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportIcd10Data")
        assert cur.fetchone()[0] >= 100

    def test_max_icd10(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportIcd10Data")
        assert cur.fetchone()[0] <= 20000


class TestMedicationDataCount:
    """Test medication row count."""

    def test_min_medication(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportMedicationInpatientData")
        assert cur.fetchone()[0] >= 100

    def test_max_medication(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportMedicationInpatientData")
        assert cur.fetchone()[0] <= 200000


class TestNursingDataCount:
    """Test nursing row count."""

    def test_min_nursing(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportNursingDailyReportsData")
        assert cur.fetchone()[0] >= 100

    def test_max_nursing(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportNursingDailyReportsData")
        assert cur.fetchone()[0] <= 50000


class TestDeviceMotionCount:
    """Test device motion row count."""

    def test_min_motion(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportDeviceMotionData")
        assert cur.fetchone()[0] >= 1000

    def test_max_motion(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportDeviceMotionData")
        assert cur.fetchone()[0] <= 500000


class TestDevice1HzCount:
    """Test device 1Hz row count."""

    def test_min_1hz(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportDevice1HzMotionData")
        assert cur.fetchone()[0] >= 10000

    def test_max_1hz(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportDevice1HzMotionData")
        assert cur.fetchone()[0] <= 1000000


class TestAcDataCount:
    """Test AC data row count."""

    def test_min_ac(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportAcData")
        assert cur.fetchone()[0] >= 10

    def test_max_ac(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tbImportAcData")
        assert cur.fetchone()[0] <= 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
