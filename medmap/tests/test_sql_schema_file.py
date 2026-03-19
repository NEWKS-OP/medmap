"""Test SQL schema file exists and contains expected content."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import SQL_SCHEMA_PATH


class TestSQLSchemaFile:
    """Test CreateImportTables.sql file."""

    def test_file_exists(self):
        assert os.path.exists(SQL_SCHEMA_PATH)

    def test_is_sql(self):
        assert SQL_SCHEMA_PATH.endswith(".sql")

    def test_contains_create_table(self):
        with open(SQL_SCHEMA_PATH) as f:
            content = f.read()
        assert "CREATE TABLE" in content.upper()

    def test_contains_tbCaseData(self):
        with open(SQL_SCHEMA_PATH) as f:
            content = f.read()
        assert "tbCaseData" in content

    def test_contains_tbImportLabsData(self):
        with open(SQL_SCHEMA_PATH) as f:
            content = f.read()
        assert "tbImportLabsData" in content

    def test_contains_tbImportIcd10Data(self):
        with open(SQL_SCHEMA_PATH) as f:
            content = f.read()
        assert "tbImportIcd10Data" in content

    def test_contains_tbImportMedicationInpatientData(self):
        with open(SQL_SCHEMA_PATH) as f:
            content = f.read()
        assert "tbImportMedicationInpatientData" in content

    def test_contains_tbImportNursingDailyReportsData(self):
        with open(SQL_SCHEMA_PATH) as f:
            content = f.read()
        assert "tbImportNursingDailyReportsData" in content

    def test_file_not_empty(self):
        assert os.path.getsize(SQL_SCHEMA_PATH) > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
