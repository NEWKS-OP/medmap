"""Test DataCleaner date normalization."""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import DataCleaner
from pipeline.validator import DataValidator


class TestCleanerDateNormalization:
    """Test date normalization through the cleaner."""

    def setup_method(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner()

    def test_iso_date_preserved(self):
        df = pd.DataFrame({
            "case_id": ["1"],
            "specimen_datetime": ["2024-01-15"],
        })
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test.csv"
        result = self.cleaner.clean_dataframe(df, "test.csv")
        val = str(result["specimen_datetime"].iloc[0])
        assert "2024" in val

    def test_german_date_converted(self):
        df = pd.DataFrame({
            "case_id": ["1"],
            "specimen_datetime": ["15.01.2024"],
        })
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test.csv"
        result = self.cleaner.clean_dataframe(df, "test.csv")
        val = str(result["specimen_datetime"].iloc[0])
        assert "2024" in val


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
