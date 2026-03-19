"""Test date normalization and parsing."""

import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import DataCleaner
from pipeline.validator import DataValidator


class TestDateNormalization:
    """Test date parsing and normalization."""

    def setup_method(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner(self.validator)

    def _make_df(self, dates, col="admission_date"):
        df = pd.DataFrame({
            col: dates,
            "case_id": [f"CASE-{i:04d}" for i in range(len(dates))],
        })
        df.attrs["file_type"] = "icd10_ops"
        df.attrs["source_file"] = "test_dates.csv"
        return df

    def test_iso_format_preserved(self):
        df = self._make_df(["2024-01-15", "2024-06-30"])
        result = self.cleaner._normalize_dates(df, "test.csv", "icd10_ops")
        assert result["admission_date"].iloc[0] == "2024-01-15"

    def test_german_format(self):
        df = self._make_df(["15.01.2024", "30.06.2024"])
        result = self.cleaner._normalize_dates(df, "test.csv", "icd10_ops")
        assert result["admission_date"].iloc[0] == "2024-01-15"

    def test_us_format(self):
        df = self._make_df(["01/15/2024", "06/30/2024"])
        result = self.cleaner._normalize_dates(df, "test.csv", "icd10_ops")
        # US format parsing
        val = result["admission_date"].iloc[0]
        assert val is not None and "2024" in str(val)

    def test_invalid_date_flagged(self):
        df = self._make_df(["99.99.9999", "32.01.2024"])
        result = self.cleaner._normalize_dates(df, "test.csv", "icd10_ops")
        # Invalid dates should be None/NaN
        for i in range(len(result)):
            val = result["admission_date"].iloc[i]
            assert val is None or pd.isna(val) or val == ""

    def test_null_date_preserved(self):
        df = self._make_df([None, np.nan])
        result = self.cleaner._normalize_dates(df, "test.csv", "icd10_ops")
        assert pd.isna(result["admission_date"].iloc[0]) or result["admission_date"].iloc[0] is None


class TestClinicalRangeValidation:
    """Test clinical value range validation."""

    def setup_method(self):
        self.validator = DataValidator()

    def test_sodium_in_range(self):
        df = pd.DataFrame({
            "sodium_mmol_L": [135, 140, 145],
            "case_id": ["CASE-0001", "CASE-0002", "CASE-0003"],
        })
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test_labs.csv"
        self.validator.validate_dataframe(df, "test.csv")
        # No critical errors for in-range values
        critical_sodium = [
            e for e in self.validator.audit_log
            if e.column_name == "sodium_mmol_L" and e.severity == "CRITICAL"
        ]
        assert len(critical_sodium) == 0

    def test_sodium_out_of_range(self):
        df = pd.DataFrame({
            "sodium_mmol_L": [50, 200],
            "case_id": ["CASE-0001", "CASE-0002"],
        })
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test_labs.csv"
        self.validator.validate_dataframe(df, "test.csv")
        critical_sodium = [
            e for e in self.validator.audit_log
            if e.column_name == "sodium_mmol_L" and e.severity == "CRITICAL"
        ]
        assert len(critical_sodium) == 2

    def test_bmi_in_range(self):
        df = pd.DataFrame({
            "bmi": [22, 30, 18.5],
            "case_id": ["CASE-0001", "CASE-0002", "CASE-0003"],
        })
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test_labs.csv"
        self.validator.validate_dataframe(df, "test.csv")
        critical_bmi = [
            e for e in self.validator.audit_log
            if e.column_name == "bmi" and e.severity == "CRITICAL"
        ]
        assert len(critical_bmi) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
