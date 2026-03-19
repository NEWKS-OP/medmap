"""Test DataCleaner ID normalization and PID prefix."""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import DataCleaner
from pipeline.validator import DataValidator


class TestCleanerIDNormalization:
    """Test ID cleaning through the cleaner."""

    def setup_method(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner()

    def test_whitespace_stripped_from_case_id(self):
        df = pd.DataFrame({
            "case_id": [" CASE-001 "],
            "patient_id": ["100001"],
        })
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test.csv"
        result = self.cleaner.clean_dataframe(df, "test.csv")
        assert result["case_id"].iloc[0].strip() == "CASE-001"

    def test_pid_prefix_added_for_labs(self):
        df = pd.DataFrame({
            "case_id": ["1"],
            "patient_id": ["100001"],
        })
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test.csv"
        result = self.cleaner.clean_dataframe(df, "test.csv")
        pid = str(result["patient_id"].iloc[0])
        assert pid.startswith("LAB_")

    def test_pid_prefix_added_for_nursing(self):
        df = pd.DataFrame({
            "case_id": ["1"],
            "patient_id": ["100001"],
            "shift": ["Early"],
            "nursing_note_free_text": ["ok"],
        })
        df.attrs["file_type"] = "nursing"
        df.attrs["source_file"] = "test.csv"
        result = self.cleaner.clean_dataframe(df, "test.csv")
        pid = str(result["patient_id"].iloc[0])
        assert pid.startswith("NUR_")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
