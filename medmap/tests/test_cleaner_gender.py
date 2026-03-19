"""Test DataCleaner gender normalization on actual data."""

import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import DataCleaner
from pipeline.validator import DataValidator


class TestCleanerGenderNormalization:
    """Test gender normalization through the cleaner."""

    def setup_method(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner()

    def test_male_normalized(self):
        df = pd.DataFrame({"sex": ["male"], "case_id": ["1"]})
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test.csv"
        result = self.cleaner.clean_dataframe(df, "test.csv")
        assert result["sex"].iloc[0] == "M"

    def test_female_normalized(self):
        df = pd.DataFrame({"sex": ["female"], "case_id": ["1"]})
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test.csv"
        result = self.cleaner.clean_dataframe(df, "test.csv")
        assert result["sex"].iloc[0] == "F"

    def test_german_male(self):
        df = pd.DataFrame({"sex": ["männlich"], "case_id": ["1"]})
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test.csv"
        result = self.cleaner.clean_dataframe(df, "test.csv")
        assert result["sex"].iloc[0] == "M"

    def test_german_female(self):
        df = pd.DataFrame({"sex": ["weiblich"], "case_id": ["1"]})
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test.csv"
        result = self.cleaner.clean_dataframe(df, "test.csv")
        assert result["sex"].iloc[0] == "F"

    def test_uppercase_preserved(self):
        df = pd.DataFrame({"sex": ["M"], "case_id": ["1"]})
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test.csv"
        result = self.cleaner.clean_dataframe(df, "test.csv")
        assert result["sex"].iloc[0] == "M"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
