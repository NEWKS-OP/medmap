"""Test distinct value counts in production database."""

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


class TestDistinctCaseIds:
    """Test distinct case IDs across tables."""

    def test_case_data_distinct_ids(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT coPatientId) FROM tbCaseData")
        assert cur.fetchone()[0] >= 50

    def test_labs_distinct_case_ids(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT coCaseId) FROM tbImportLabsData WHERE coCaseId IS NOT NULL")
        assert cur.fetchone()[0] >= 10

    def test_icd10_distinct_case_ids(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT coCaseId) FROM tbImportIcd10Data WHERE coCaseId IS NOT NULL")
        assert cur.fetchone()[0] >= 10

    def test_medication_distinct_case_ids(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT coCaseId) FROM tbImportMedicationInpatientData WHERE coCaseId IS NOT NULL")
        assert cur.fetchone()[0] >= 10

    def test_nursing_distinct_case_ids(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT coCaseId) FROM tbImportNursingDailyReportsData WHERE coCaseId IS NOT NULL")
        assert cur.fetchone()[0] >= 10


class TestDistinctWards:
    """Test distinct wards in ICD10 data."""

    def test_has_multiple_wards(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT coWard) FROM tbImportIcd10Data WHERE coWard IS NOT NULL")
        assert cur.fetchone()[0] >= 2


class TestDistinctMedications:
    """Test distinct medications."""

    def test_has_multiple_medications(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT coMedication_name) FROM tbImportMedicationInpatientData WHERE coMedication_name IS NOT NULL")
        assert cur.fetchone()[0] >= 10

    def test_has_multiple_atc_codes(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT coMedication_code_atc) FROM tbImportMedicationInpatientData WHERE coMedication_code_atc IS NOT NULL")
        assert cur.fetchone()[0] >= 5


class TestDistinctAuditEntries:
    """Test distinct audit log entries."""

    def test_multiple_error_types(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT error_type) FROM tbAuditLog")
        assert cur.fetchone()[0] >= 2

    def test_multiple_tables_logged(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT table_name) FROM tbAuditLog")
        assert cur.fetchone()[0] >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
