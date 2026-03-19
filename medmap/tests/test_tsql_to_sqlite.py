"""Test T-SQL to SQLite type conversion map."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.sql_export import TSQL_TO_SQLITE


class TestTSQLToSQLiteMap:
    """Verify type conversion mappings."""

    def test_bigint_to_integer(self):
        assert TSQL_TO_SQLITE["bigint"] == "INTEGER"

    def test_int_to_integer(self):
        assert TSQL_TO_SQLITE["int"] == "INTEGER"

    def test_smallint_to_integer(self):
        assert TSQL_TO_SQLITE["smallint"] == "INTEGER"

    def test_tinyint_to_integer(self):
        assert TSQL_TO_SQLITE["tinyint"] == "INTEGER"

    def test_bit_to_integer(self):
        assert TSQL_TO_SQLITE["bit"] == "INTEGER"

    def test_numeric_to_real(self):
        assert TSQL_TO_SQLITE["numeric"] == "REAL"

    def test_decimal_to_real(self):
        assert TSQL_TO_SQLITE["decimal"] == "REAL"

    def test_float_to_real(self):
        assert TSQL_TO_SQLITE["float"] == "REAL"

    def test_real_to_real(self):
        assert TSQL_TO_SQLITE["real"] == "REAL"

    def test_nvarchar_to_text(self):
        assert TSQL_TO_SQLITE["nvarchar"] == "TEXT"

    def test_varchar_to_text(self):
        assert TSQL_TO_SQLITE["varchar"] == "TEXT"

    def test_nchar_to_text(self):
        assert TSQL_TO_SQLITE["nchar"] == "TEXT"

    def test_char_to_text(self):
        assert TSQL_TO_SQLITE["char"] == "TEXT"

    def test_text_to_text(self):
        assert TSQL_TO_SQLITE["text"] == "TEXT"

    def test_datetime_to_text(self):
        assert TSQL_TO_SQLITE["datetime"] == "TEXT"

    def test_datetime2_to_text(self):
        assert TSQL_TO_SQLITE["datetime2"] == "TEXT"

    def test_date_to_text(self):
        assert TSQL_TO_SQLITE["date"] == "TEXT"

    def test_all_values_are_sqlite_types(self):
        valid_types = {"INTEGER", "REAL", "TEXT", "BLOB", "NULL"}
        for tsql, sqlite_type in TSQL_TO_SQLITE.items():
            assert sqlite_type in valid_types, f"{tsql} maps to invalid {sqlite_type}"

    def test_map_is_complete(self):
        assert len(TSQL_TO_SQLITE) >= 17


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
