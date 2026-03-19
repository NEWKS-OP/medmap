"""
Phase 6 — Unit tests for validation checks.
Tests that the pipeline produces correct output for known inputs.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import DataCleaner
from pipeline.validator import DataValidator


class TestShiftNormalization:
    """Test shift value normalization."""

    def setup_method(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner(self.validator)

    def _make_nursing_df(self, shifts):
        df = pd.DataFrame({"shift": shifts, "case_id": ["CASE-0001"] * len(shifts)})
        df.attrs["file_type"] = "nursing"
        df.attrs["source_file"] = "test_nursing.csv"
        return df

    def test_english_shifts(self):
        df = self._make_nursing_df(["Early shift", "Late shift", "Night shift"])
        result = self.cleaner._normalize_shifts(df, "test.csv", "nursing")
        assert list(result["shift"]) == ["Early", "Late", "Night"]

    def test_german_shifts(self):
        df = self._make_nursing_df(["Frühschicht", "Spätschicht", "Nachtschicht"])
        result = self.cleaner._normalize_shifts(df, "test.csv", "nursing")
        assert list(result["shift"]) == ["Early", "Late", "Night"]

    def test_contaminated_shifts(self):
        df = self._make_nursing_df(["Early shiftä", "Late shift%", "Night shiftü"])
        result = self.cleaner._normalize_shifts(df, "test.csv", "nursing")
        assert list(result["shift"]) == ["Early", "Late", "Night"]

    def test_already_normalized_shifts(self):
        df = self._make_nursing_df(["Early", "Late", "Night"])
        result = self.cleaner._normalize_shifts(df, "test.csv", "nursing")
        assert list(result["shift"]) == ["Early", "Late", "Night"]

    def test_null_shift(self):
        df = self._make_nursing_df([None, "Early", np.nan])
        result = self.cleaner._normalize_shifts(df, "test.csv", "nursing")
        assert result["shift"].iloc[0] is None or pd.isna(result["shift"].iloc[0])
        assert result["shift"].iloc[1] == "Early"


class TestEventTypeNormalization:
    """Test medication event type normalization."""

    def setup_method(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner(self.validator)

    def _make_med_df(self, types):
        df = pd.DataFrame({"record_type": types, "case_id": ["CASE-0001"] * len(types)})
        df.attrs["file_type"] = "medication"
        df.attrs["source_file"] = "test_med.csv"
        return df

    def test_clean_types(self):
        df = self._make_med_df(["ORDER", "CHANGE", "ADMIN"])
        result = self.cleaner._normalize_event_types(df, "test.csv", "medication")
        assert list(result["record_type"]) == ["ORDER", "CHANGE", "ADMIN"]

    def test_contaminated_types(self):
        df = self._make_med_df(["ORDERä", "ADMINü", "ADMIN%"])
        result = self.cleaner._normalize_event_types(df, "test.csv", "medication")
        assert list(result["record_type"]) == ["ORDER", "ADMIN", "ADMIN"]

    def test_lowercase_types(self):
        df = self._make_med_df(["order", "admin", "change"])
        result = self.cleaner._normalize_event_types(df, "test.csv", "medication")
        assert list(result["record_type"]) == ["ORDER", "ADMIN", "CHANGE"]


class TestWhitespaceMissing:
    """Test whitespace-only values treated as missing."""

    def setup_method(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner(self.validator)

    def test_space_is_missing(self):
        assert self.cleaner._is_missing_token(" ") is True

    def test_tab_is_missing(self):
        assert self.cleaner._is_missing_token("\t") is True

    def test_multiple_spaces_missing(self):
        assert self.cleaner._is_missing_token("   ") is True

    def test_empty_string_is_missing(self):
        # Empty string is treated as a missing value
        assert self.cleaner._is_missing_token("") is True

    def test_none_not_flagged(self):
        assert self.cleaner._is_missing_token(None) is False

    def test_nan_not_flagged(self):
        assert self.cleaner._is_missing_token(np.nan) is False

    def test_real_value_not_missing(self):
        assert self.cleaner._is_missing_token("hello") is False
        assert self.cleaner._is_missing_token("42") is False

    def test_na_token_is_missing(self):
        assert self.cleaner._is_missing_token("N/A") is True
        assert self.cleaner._is_missing_token("n/a") is True
        assert self.cleaner._is_missing_token("NA") is True

    def test_missing_token_is_missing(self):
        assert self.cleaner._is_missing_token("missing") is True
        assert self.cleaner._is_missing_token("unknown") is True
        assert self.cleaner._is_missing_token("keine") is True


class TestGenderNormalization:
    """Test gender normalization."""

    def setup_method(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner(self.validator)

    def _make_labs_df(self, genders):
        df = pd.DataFrame({
            "sex": genders,
            "case_id": [f"CASE-{i:04d}" for i in range(len(genders))],
        })
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test_labs.csv"
        return df

    def test_standard_genders(self):
        df = self._make_labs_df(["M", "F", "M", "F"])
        result = self.cleaner._normalize_gender(df, "test.csv", "labs")
        assert list(result["sex"]) == ["M", "F", "M", "F"]

    def test_german_genders(self):
        df = self._make_labs_df(["männlich", "weiblich"])
        result = self.cleaner._normalize_gender(df, "test.csv", "labs")
        assert list(result["sex"]) == ["M", "F"]

    def test_english_genders(self):
        df = self._make_labs_df(["male", "female"])
        result = self.cleaner._normalize_gender(df, "test.csv", "labs")
        assert list(result["sex"]) == ["M", "F"]

    def test_lowercase_genders(self):
        df = self._make_labs_df(["m", "f"])
        result = self.cleaner._normalize_gender(df, "test.csv", "labs")
        assert list(result["sex"]) == ["M", "F"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
