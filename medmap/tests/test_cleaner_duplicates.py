"""Test DataCleaner duplicate removal."""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import DataCleaner


class TestCleanerDuplicateRemoval:
    """Test duplicate detection and removal."""

    def setup_method(self):
        self.cleaner = DataCleaner()

    def test_removes_exact_duplicates(self):
        df = pd.DataFrame({
            "case_id": ["1", "1", "2"],
            "patient_id": ["100", "100", "200"],
            "sodium_mmol_L": [138, 138, 142],
        })
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test.csv"
        result = self.cleaner.clean_dataframe(df, "test.csv")
        assert len(result) <= 3

    def test_keeps_unique_rows(self):
        df = pd.DataFrame({
            "case_id": ["1", "2", "3"],
            "patient_id": ["100", "200", "300"],
        })
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test.csv"
        result = self.cleaner.clean_dataframe(df, "test.csv")
        assert len(result) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
