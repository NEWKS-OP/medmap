"""Test SQLExporter initialization and connection."""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.sql_export import SQLExporter


class TestSQLExporterInit:
    """Test SQLExporter initialization."""

    def test_default_db_path(self):
        e = SQLExporter()
        assert e.db_path is not None
        assert "medmap.db" in e.db_path

    def test_custom_db_path(self):
        e = SQLExporter(db_path="/tmp/test.db")
        assert e.db_path == "/tmp/test.db"

    def test_conn_initially_none(self):
        e = SQLExporter()
        assert e.conn is None


class TestSQLExporterConnect:
    """Test connect and close."""

    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.exporter = SQLExporter(db_path=self.db_path)

    def teardown_method(self):
        self.exporter.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_connect_returns_connection(self):
        conn = self.exporter.connect()
        assert conn is not None

    def test_conn_attribute_set(self):
        self.exporter.connect()
        assert self.exporter.conn is not None

    def test_close_sets_none(self):
        self.exporter.connect()
        self.exporter.close()
        assert self.exporter.conn is None

    def test_close_idempotent(self):
        self.exporter.close()
        self.exporter.close()
        assert self.exporter.conn is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
