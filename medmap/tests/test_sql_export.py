"""Tests for pipeline/sql_export.py — SQLExporter class."""

import sys
import os
import sqlite3
import tempfile
import pytest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.sql_export import SQLExporter, TABLE_INSERT_ORDER, TSQL_TO_SQLITE
from contracts import AuditLogEntry, Severity, ActionTaken


@pytest.fixture
def tmp_db():
    """Create a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def exporter(tmp_db):
    return SQLExporter(db_path=tmp_db)


class TestConnect:
    def test_creates_connection(self, exporter):
        conn = exporter.connect()
        assert conn is not None
        assert exporter.conn is not None
        exporter.close()

    def test_creates_db_file(self, exporter):
        exporter.connect()
        assert os.path.exists(exporter.db_path)
        exporter.close()

    def test_wal_mode_enabled(self, exporter):
        exporter.connect()
        cursor = exporter.conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode == "wal"
        exporter.close()


class TestClose:
    def test_closes_connection(self, exporter):
        exporter.connect()
        exporter.close()
        assert exporter.conn is None

    def test_close_without_connect(self, exporter):
        exporter.close()
        assert exporter.conn is None


class TestConvertTsqlToSqlite:
    def test_converts_create_table(self, exporter):
        tsql = "CREATE TABLE TestTable (coId bigint IDENTITY(1,1), coName nvarchar(255))"
        stmts = exporter._convert_tsql_to_sqlite(tsql)
        assert len(stmts) == 1
        assert "TestTable" in stmts[0]

    def test_identity_to_autoincrement(self, exporter):
        tsql = "CREATE TABLE T (coId bigint IDENTITY(1,1))"
        stmts = exporter._convert_tsql_to_sqlite(tsql)
        assert "AUTOINCREMENT" in stmts[0]
        assert "PRIMARY KEY" in stmts[0]

    def test_nvarchar_to_text(self, exporter):
        tsql = "CREATE TABLE T (coId bigint IDENTITY(1,1), coName nvarchar(255))"
        stmts = exporter._convert_tsql_to_sqlite(tsql)
        assert "TEXT" in stmts[0]

    def test_bigint_to_integer(self, exporter):
        tsql = "CREATE TABLE T (coId bigint IDENTITY(1,1), coVal bigint)"
        stmts = exporter._convert_tsql_to_sqlite(tsql)
        assert "INTEGER" in stmts[0]

    def test_drops_not_null(self, exporter):
        tsql = "CREATE TABLE T (coId bigint IDENTITY(1,1), coName nvarchar(255) NOT NULL)"
        stmts = exporter._convert_tsql_to_sqlite(tsql)
        assert "NOT NULL" not in stmts[0] or "AUTOINCREMENT" in stmts[0]

    def test_skips_constraints(self, exporter):
        tsql = "CREATE TABLE T (coId bigint IDENTITY(1,1), coName nvarchar(255), CONSTRAINT pk PRIMARY KEY(coId))"
        stmts = exporter._convert_tsql_to_sqlite(tsql)
        assert "CONSTRAINT" not in stmts[0]

    def test_multiple_tables(self, exporter):
        tsql = """
        CREATE TABLE T1 (coId bigint IDENTITY(1,1), coName nvarchar(255))
        CREATE TABLE T2 (coId bigint IDENTITY(1,1), coVal int)
        """
        stmts = exporter._convert_tsql_to_sqlite(tsql)
        assert len(stmts) == 2

    def test_removes_bom(self, exporter):
        tsql = "\ufeffCREATE TABLE T (coId bigint IDENTITY(1,1))"
        stmts = exporter._convert_tsql_to_sqlite(tsql)
        assert len(stmts) == 1

    def test_datetime_to_text(self, exporter):
        tsql = "CREATE TABLE T (coId bigint IDENTITY(1,1), coDate datetime)"
        stmts = exporter._convert_tsql_to_sqlite(tsql)
        assert "TEXT" in stmts[0]


class TestCreateSchema:
    def test_creates_audit_log_table(self, exporter):
        exporter.connect()
        exporter._create_audit_log_table()
        exporter.conn.commit()
        cursor = exporter.conn.execute("PRAGMA table_info(tbAuditLog)")
        cols = [row[1] for row in cursor.fetchall()]
        assert "source_file" in cols
        assert "error_type" in cols
        exporter.close()

    def test_creates_data_passport_table(self, exporter):
        exporter.connect()
        exporter._create_data_passport_table()
        exporter.conn.commit()
        cursor = exporter.conn.execute("PRAGMA table_info(tbDataPassport)")
        cols = [row[1] for row in cursor.fetchall()]
        assert "case_id" in cols
        assert "problem_type" in cols
        exporter.close()

    def test_create_schema_from_file(self, exporter):
        exporter.connect()
        exporter.create_schema()
        # Should have created tables
        cursor = exporter.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        assert "tbAuditLog" in tables
        assert "tbDataPassport" in tables
        exporter.close()


class TestGetTableColumns:
    def test_returns_columns(self, exporter):
        exporter.connect()
        exporter.conn.execute("CREATE TABLE test_t (id INTEGER, name TEXT)")
        exporter.conn.commit()
        cols = exporter._get_table_columns("test_t")
        assert "id" in cols
        assert "name" in cols
        exporter.close()

    def test_nonexistent_table(self, exporter):
        exporter.connect()
        cols = exporter._get_table_columns("nonexistent")
        assert cols == []
        exporter.close()


class TestInsertDataframe:
    def test_inserts_rows(self, exporter):
        exporter.connect()
        exporter.conn.execute(
            "CREATE TABLE test_t (coId INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, val REAL)"
        )
        exporter.conn.commit()
        df = pd.DataFrame({"name": ["a", "b"], "val": [1.0, 2.0]})
        count = exporter._insert_dataframe("test_t", df)
        assert count == 2
        exporter.close()

    def test_inserts_none_df(self, exporter):
        exporter.connect()
        count = exporter._insert_dataframe("test_t", None)
        assert count == 0
        exporter.close()

    def test_inserts_empty_df(self, exporter):
        exporter.connect()
        count = exporter._insert_dataframe("test_t", pd.DataFrame())
        assert count == 0
        exporter.close()

    def test_handles_numpy_types(self, exporter):
        exporter.connect()
        exporter.conn.execute(
            "CREATE TABLE test_t (coId INTEGER PRIMARY KEY AUTOINCREMENT, val INTEGER)"
        )
        exporter.conn.commit()
        df = pd.DataFrame({"val": [np.int64(42), np.int64(99)]})
        count = exporter._insert_dataframe("test_t", df)
        assert count == 2
        exporter.close()

    def test_handles_nan_values(self, exporter):
        exporter.connect()
        exporter.conn.execute(
            "CREATE TABLE test_t (coId INTEGER PRIMARY KEY AUTOINCREMENT, val TEXT)"
        )
        exporter.conn.commit()
        df = pd.DataFrame({"val": ["hello", None, float("nan")]})
        count = exporter._insert_dataframe("test_t", df)
        assert count == 3
        exporter.close()

    def test_matches_only_existing_columns(self, exporter):
        exporter.connect()
        exporter.conn.execute(
            "CREATE TABLE test_t (coId INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)"
        )
        exporter.conn.commit()
        df = pd.DataFrame({"name": ["a"], "extra_col": ["b"]})
        count = exporter._insert_dataframe("test_t", df)
        assert count == 1
        exporter.close()


class TestInsertAll:
    def test_inserts_in_order(self, exporter):
        exporter.connect()
        for table in TABLE_INSERT_ORDER:
            exporter.conn.execute(
                f"CREATE TABLE {table} (coId INTEGER PRIMARY KEY AUTOINCREMENT, val TEXT)"
            )
        exporter.conn.commit()
        mapped = {
            "tbCaseData": pd.DataFrame({"val": ["a"]}),
            "tbImportLabsData": pd.DataFrame({"val": ["b"]}),
        }
        results = exporter.insert_all(mapped)
        assert results["tbCaseData"] == 1
        assert results["tbImportLabsData"] == 1
        exporter.close()

    def test_skips_empty_tables(self, exporter):
        exporter.connect()
        for table in TABLE_INSERT_ORDER:
            exporter.conn.execute(
                f"CREATE TABLE {table} (coId INTEGER PRIMARY KEY AUTOINCREMENT, val TEXT)"
            )
        exporter.conn.commit()
        mapped = {"tbCaseData": pd.DataFrame()}
        results = exporter.insert_all(mapped)
        assert results["tbCaseData"] == 0
        exporter.close()


class TestInsertAuditLog:
    def test_inserts_entries(self, exporter):
        exporter.connect()
        exporter._create_audit_log_table()
        exporter.conn.commit()
        entries = [
            AuditLogEntry(
                source_file="test.csv",
                case_id="CASE-001",
                table_name="tbImportLabsData",
                column_name="sodium",
                original_value="999",
                cleaned_value=None,
                error_type="CLINICAL_OUTLIER",
                severity=Severity.CRITICAL,
                action_taken=ActionTaken.QUARANTINE,
                corrected_by=None,
                row_number=0,
            )
        ]
        count = exporter.insert_audit_log(entries)
        assert count == 1
        exporter.close()

    def test_empty_entries(self, exporter):
        exporter.connect()
        count = exporter.insert_audit_log([])
        assert count == 0
        exporter.close()

    def test_handles_tuple_row_number(self, exporter):
        exporter.connect()
        exporter._create_audit_log_table()
        exporter.conn.commit()
        entries = [
            AuditLogEntry(
                source_file="test.csv",
                case_id="CASE-001",
                table_name="t",
                column_name="c",
                original_value="v",
                cleaned_value=None,
                error_type="ERR",
                severity=Severity.LOW,
                action_taken=ActionTaken.FLAGGED,
                corrected_by=None,
                row_number=(5, 10),
            )
        ]
        count = exporter.insert_audit_log(entries)
        assert count == 1
        exporter.close()

    def test_handles_numpy_row_number(self, exporter):
        exporter.connect()
        exporter._create_audit_log_table()
        exporter.conn.commit()
        entries = [
            AuditLogEntry(
                source_file="test.csv",
                case_id="CASE-001",
                table_name="t",
                column_name="c",
                original_value="v",
                cleaned_value=None,
                error_type="ERR",
                severity=Severity.LOW,
                action_taken=ActionTaken.FLAGGED,
                corrected_by=None,
                row_number=np.int64(42),
            )
        ]
        count = exporter.insert_audit_log(entries)
        assert count == 1
        exporter.close()


class TestInsertDataPassports:
    def test_inserts_passports(self, exporter):
        exporter.connect()
        exporter._create_data_passport_table()
        exporter.conn.commit()
        entries = [
            AuditLogEntry(
                source_file="test.csv",
                case_id="CASE-001",
                table_name="tbImportLabsData",
                column_name="sodium",
                original_value="999",
                cleaned_value=None,
                error_type="CLINICAL_OUTLIER",
                severity=Severity.CRITICAL,
                action_taken=ActionTaken.QUARANTINE,
                corrected_by=None,
                row_number=0,
            )
        ]
        count = exporter.insert_data_passports(entries)
        assert count == 1
        exporter.close()

    def test_empty_entries(self, exporter):
        exporter.connect()
        count = exporter.insert_data_passports([])
        assert count == 0
        exporter.close()

    def test_auto_correct_confidence(self, exporter):
        exporter.connect()
        exporter._create_data_passport_table()
        exporter.conn.commit()
        entries = [
            AuditLogEntry(
                source_file="test.csv",
                case_id="CASE-001",
                table_name="t",
                column_name="c",
                original_value="v",
                cleaned_value="fixed",
                error_type="SPECIAL_CHARS_REMOVED",
                severity=Severity.LOW,
                action_taken=ActionTaken.AUTO_CORRECT,
                corrected_by="cleaner",
                row_number=0,
            )
        ]
        count = exporter.insert_data_passports(entries)
        assert count == 1
        cursor = exporter.conn.execute("SELECT confidence FROM tbDataPassport")
        row = cursor.fetchone()
        assert row[0] == 0.95
        exporter.close()


class TestGetConnection:
    def test_creates_if_needed(self, exporter):
        conn = exporter.get_connection()
        assert conn is not None
        exporter.close()

    def test_returns_existing(self, exporter):
        exporter.connect()
        conn1 = exporter.get_connection()
        conn2 = exporter.get_connection()
        assert conn1 is conn2
        exporter.close()


class TestTsqlToSqliteMapping:
    def test_all_types_mapped(self):
        expected = ["bigint", "int", "smallint", "nvarchar", "varchar",
                     "datetime", "float", "real", "text"]
        for t in expected:
            assert t in TSQL_TO_SQLITE

    def test_integer_types(self):
        for t in ["bigint", "int", "smallint", "tinyint", "bit"]:
            assert TSQL_TO_SQLITE[t] == "INTEGER"

    def test_text_types(self):
        for t in ["nvarchar", "varchar", "nchar", "char", "text", "ntext"]:
            assert TSQL_TO_SQLITE[t] == "TEXT"

    def test_real_types(self):
        for t in ["numeric", "decimal", "float", "real"]:
            assert TSQL_TO_SQLITE[t] == "REAL"

    def test_datetime_types(self):
        for t in ["datetime", "datetime2", "date", "time"]:
            assert TSQL_TO_SQLITE[t] == "TEXT"


class TestTableInsertOrder:
    def test_case_data_first(self):
        assert TABLE_INSERT_ORDER[0] == "tbCaseData"

    def test_all_8_tables(self):
        assert len(TABLE_INSERT_ORDER) == 8

    def test_labs_before_icd10(self):
        labs_idx = TABLE_INSERT_ORDER.index("tbImportLabsData")
        icd10_idx = TABLE_INSERT_ORDER.index("tbImportIcd10Data")
        assert labs_idx < icd10_idx
