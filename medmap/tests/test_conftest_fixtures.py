"""Test that conftest fixtures work correctly."""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestSampleLabsDf:
    """Test sample_labs_df fixture."""

    def test_has_2_rows(self, sample_labs_df):
        assert len(sample_labs_df) == 2

    def test_has_case_id_column(self, sample_labs_df):
        assert "case_id" in sample_labs_df.columns

    def test_has_sodium_column(self, sample_labs_df):
        assert "sodium_mmol_L" in sample_labs_df.columns

    def test_file_type_is_labs(self, sample_labs_df):
        assert sample_labs_df.attrs["file_type"] == "labs"

    def test_source_file_set(self, sample_labs_df):
        assert sample_labs_df.attrs["source_file"] == "test_labs.csv"


class TestSampleNursingDf:
    """Test sample_nursing_df fixture."""

    def test_has_1_row(self, sample_nursing_df):
        assert len(sample_nursing_df) == 1

    def test_has_shift_column(self, sample_nursing_df):
        assert "shift" in sample_nursing_df.columns

    def test_file_type_is_nursing(self, sample_nursing_df):
        assert sample_nursing_df.attrs["file_type"] == "nursing"


class TestTempDb:
    """Test temp_db fixture."""

    def test_connection_works(self, temp_db):
        conn, path = temp_db
        cur = conn.cursor()
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1

    def test_path_exists(self, temp_db):
        conn, path = temp_db
        assert os.path.exists(path)

    def test_path_is_db(self, temp_db):
        conn, path = temp_db
        assert path.endswith(".db")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
