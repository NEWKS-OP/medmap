"""Test clinical values in production database are within expected ranges."""

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


class TestLabsClinicalRanges:
    """Verify clinical values are within expected ranges in DB."""

    def test_sodium_min_reasonable(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT MIN(CAST(coSodium_mmol_L AS REAL)) FROM tbImportLabsData WHERE coSodium_mmol_L IS NOT NULL AND coSodium_mmol_L != ''")
        val = cur.fetchone()[0]
        if val is not None:
            assert val >= 80, f"Sodium min {val} too low"

    def test_sodium_max_reasonable(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT MAX(CAST(coSodium_mmol_L AS REAL)) FROM tbImportLabsData WHERE coSodium_mmol_L IS NOT NULL AND coSodium_mmol_L != ''")
        val = cur.fetchone()[0]
        if val is not None:
            assert val <= 200, f"Sodium max {val} too high"

    def test_potassium_min_reasonable(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT MIN(CAST(coPotassium_mmol_L AS REAL)) FROM tbImportLabsData WHERE coPotassium_mmol_L IS NOT NULL AND coPotassium_mmol_L != ''")
        val = cur.fetchone()[0]
        if val is not None:
            assert val >= 1.0, f"Potassium min {val} too low"

    def test_potassium_max_reasonable(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT MAX(CAST(coPotassium_mmol_L AS REAL)) FROM tbImportLabsData WHERE coPotassium_mmol_L IS NOT NULL AND coPotassium_mmol_L != ''")
        val = cur.fetchone()[0]
        if val is not None:
            assert val <= 10.0, f"Potassium max {val} too high"

    def test_creatinine_positive(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT MIN(CAST(coCreatinine_mg_dL AS REAL)) FROM tbImportLabsData WHERE coCreatinine_mg_dL IS NOT NULL AND coCreatinine_mg_dL != ''")
        val = cur.fetchone()[0]
        if val is not None:
            assert val > 0, f"Creatinine min {val} not positive"


class TestCaseDataRanges:
    """Verify case data ranges."""

    def test_age_min_reasonable(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT MIN(CAST(coAgeYears AS INTEGER)) FROM tbCaseData WHERE coAgeYears IS NOT NULL AND coAgeYears != ''")
        val = cur.fetchone()[0]
        if val is not None:
            assert val >= 0, f"Age min {val} negative"

    def test_age_max_reasonable(self, db_conn):
        cur = db_conn.cursor()
        cur.execute("SELECT MAX(CAST(coAgeYears AS INTEGER)) FROM tbCaseData WHERE coAgeYears IS NOT NULL AND coAgeYears != ''")
        val = cur.fetchone()[0]
        if val is not None:
            assert val <= 120, f"Age max {val} too high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
