"""Test production database column names match expected schema."""

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


def get_columns(conn, table):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return {r[1] for r in cur.fetchall()}


class TestCaseDataColumns:
    """Test tbCaseData columns."""

    def test_has_coPatientId(self, db_conn):
        cols = get_columns(db_conn, "tbCaseData")
        assert "coPatientId" in cols

    def test_has_coGender(self, db_conn):
        cols = get_columns(db_conn, "tbCaseData")
        assert "coGender" in cols

    def test_has_coAgeYears(self, db_conn):
        cols = get_columns(db_conn, "tbCaseData")
        assert "coAgeYears" in cols


class TestLabsColumns:
    """Test tbImportLabsData columns."""

    def test_has_coCaseId(self, db_conn):
        cols = get_columns(db_conn, "tbImportLabsData")
        assert "coCaseId" in cols

    def test_has_coSodium(self, db_conn):
        cols = get_columns(db_conn, "tbImportLabsData")
        assert "coSodium_mmol_L" in cols

    def test_has_coPotassium(self, db_conn):
        cols = get_columns(db_conn, "tbImportLabsData")
        assert "coPotassium_mmol_L" in cols

    def test_has_coCreatinine(self, db_conn):
        cols = get_columns(db_conn, "tbImportLabsData")
        assert "coCreatinine_mg_dL" in cols


class TestICD10Columns:
    """Test tbImportIcd10Data columns."""

    def test_has_coCaseId(self, db_conn):
        cols = get_columns(db_conn, "tbImportIcd10Data")
        assert "coCaseId" in cols

    def test_has_coAdmission_date(self, db_conn):
        cols = get_columns(db_conn, "tbImportIcd10Data")
        assert "coAdmission_date" in cols

    def test_has_coPrimary_icd10_code(self, db_conn):
        cols = get_columns(db_conn, "tbImportIcd10Data")
        assert "coPrimary_icd10_code" in cols


class TestNursingColumns:
    """Test tbImportNursingDailyReportsData columns."""

    def test_has_coCaseId(self, db_conn):
        cols = get_columns(db_conn, "tbImportNursingDailyReportsData")
        assert "coCaseId" in cols

    def test_has_coShift(self, db_conn):
        cols = get_columns(db_conn, "tbImportNursingDailyReportsData")
        assert "coShift" in cols


class TestMedicationColumns:
    """Test tbImportMedicationInpatientData columns."""

    def test_has_coCaseId(self, db_conn):
        cols = get_columns(db_conn, "tbImportMedicationInpatientData")
        assert "coCaseId" in cols

    def test_has_coRecord_type(self, db_conn):
        cols = get_columns(db_conn, "tbImportMedicationInpatientData")
        assert "coRecord_type" in cols

    def test_has_coMedication_name(self, db_conn):
        cols = get_columns(db_conn, "tbImportMedicationInpatientData")
        assert "coMedication_name" in cols


class TestDeviceMotionColumns:
    """Test tbImportDeviceMotionData columns."""

    def test_has_coCaseId(self, db_conn):
        cols = get_columns(db_conn, "tbImportDeviceMotionData")
        assert "coCaseId" in cols

    def test_has_coTimestamp(self, db_conn):
        cols = get_columns(db_conn, "tbImportDeviceMotionData")
        assert "coTimestamp" in cols


class TestAuditLogColumns:
    """Test tbAuditLog columns."""

    def test_has_case_id(self, db_conn):
        cols = get_columns(db_conn, "tbAuditLog")
        assert "case_id" in cols

    def test_has_severity(self, db_conn):
        cols = get_columns(db_conn, "tbAuditLog")
        assert "severity" in cols

    def test_has_action_taken(self, db_conn):
        cols = get_columns(db_conn, "tbAuditLog")
        assert "action_taken" in cols

    def test_has_error_type(self, db_conn):
        cols = get_columns(db_conn, "tbAuditLog")
        assert "error_type" in cols


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
