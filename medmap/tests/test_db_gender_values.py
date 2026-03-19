"""Test gender values in production database."""

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


class TestGenderNormalization:
    """Verify gender values are normalized in DB."""

    def test_case_data_gender_values(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT DISTINCT coGender FROM tbCaseData WHERE coGender IS NOT NULL")
        values = {r[0] for r in cur.fetchall()}
        assert values <= {"M", "F"}, f"Unexpected gender values: {values}"

    def test_labs_has_case_ids(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT coCaseId) FROM tbImportLabsData WHERE coCaseId IS NOT NULL")
        count = cur.fetchone()[0]
        assert count > 0, "No case IDs found in labs data"


class TestShiftNormalization:
    """Verify shift values are normalized in DB."""

    def test_nursing_shift_values(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT DISTINCT coShift FROM tbImportNursingDailyReportsData WHERE coShift IS NOT NULL")
        values = {r[0] for r in cur.fetchall()}
        assert values <= {"Early", "Late", "Night"}, f"Unexpected shift values: {values}"


class TestEventTypeNormalization:
    """Verify event types are normalized in DB."""

    def test_medication_event_types(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT DISTINCT coRecord_type FROM tbImportMedicationInpatientData WHERE coRecord_type IS NOT NULL")
        values = {r[0] for r in cur.fetchall()}
        assert values <= {"ORDER", "CHANGE", "ADMIN"}, f"Unexpected event types: {values}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
