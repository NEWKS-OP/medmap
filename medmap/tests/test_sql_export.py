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
