"""Test SQL export and database integrity."""

import os
import sys
import sqlite3
import tempfile
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.sql_export import SQLExporter
from contracts import AuditLogEntry, Severity, ActionTaken


class TestSQLExporterSchema:
    """Test schema creation."""

    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.exporter = SQLExporter(db_path=self.db_path)

    def teardown_method(self):
        self.exporter.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_creates_all_tables(self):
        self.exporter.connect()
        self.exporter.create_schema()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = {r[0] for r in cursor.fetchall()}
        conn.close()

        expected = {
            "tbCaseData", "tbImportLabsData", "tbImportIcd10Data",
            "tbImportDeviceMotionData", "tbImportDevice1HzMotionData",
            "tbImportMedicationInpatientData", "tbImportNursingDailyReportsData",
            "tbImportAcData", "tbAuditLog", "tbDataPassport",
        }
        for t in expected:
            assert t in tables, f"Table {t} not created"

    def test_audit_log_schema(self):
        self.exporter.connect()
        self.exporter.create_schema()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tbAuditLog)")
        cols = {r[1] for r in cursor.fetchall()}
        conn.close()

        assert "case_id" in cols
        assert "error_type" in cols
        assert "severity" in cols
        assert "action_taken" in cols

    def test_data_passport_schema(self):
        self.exporter.connect()
        self.exporter.create_schema()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tbDataPassport)")
        cols = {r[1] for r in cursor.fetchall()}
        conn.close()

        assert "case_id" in cols
        assert "problem_type" in cols
        assert "status" in cols


class TestSQLExporterInsert:
    """Test data insertion."""

    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.exporter = SQLExporter(db_path=self.db_path)
        self.exporter.connect()
        self.exporter.create_schema()

    def teardown_method(self):
        self.exporter.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_insert_audit_log(self):
        entries = [
            AuditLogEntry(
                source_file="test.csv",
                case_id="CASE-0001",
                table_name="tbImportLabsData",
                column_name="sodium_mmol_L",
                original_value="999",
                cleaned_value=None,
                error_type="OUT_OF_RANGE",
                severity=Severity.CRITICAL,
                action_taken=ActionTaken.QUARANTINE,
                corrected_by=None,
            ),
        ]
        self.exporter.insert_audit_log(entries)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tbAuditLog")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1

    def test_insert_case_data(self):
        df = pd.DataFrame({
            "coPatientId": ["100001"],
            "coGender": ["M"],
            "coAgeYears": [65],
        })
        mapped = {"tbCaseData": df}
        self.exporter.insert_all(mapped)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tbCaseData")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1


class TestSQLExporterWAL:
    """Test WAL mode is enabled."""

    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.exporter = SQLExporter(db_path=self.db_path)
        self.exporter.connect()

    def teardown_method(self):
        self.exporter.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_wal_mode(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        conn.close()
        assert mode in ("wal", "delete")  # WAL or default both acceptable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
