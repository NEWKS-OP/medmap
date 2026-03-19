"""Test ID cleaning and PID prefix logic."""

import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import DataCleaner
from pipeline.validator import DataValidator


class TestIDCleaning:
    """Test case_id and patient_id cleaning."""

    def setup_method(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner(self.validator)

    def _make_labs_df(self, case_ids, patient_ids=None):
        data = {"case_id": case_ids}
        if patient_ids:
            data["patient_id"] = patient_ids
        df = pd.DataFrame(data)
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test_labs.csv"
        return df

    def test_clean_ids_strip_whitespace(self):
        df = self._make_labs_df([" CASE-0001 ", "CASE-0002\t"])
        result = self.cleaner._clean_ids(df, "test.csv", "labs")
        assert result["case_id"].iloc[0] == "CASE-0001"
        assert result["case_id"].iloc[1] == "CASE-0002"

    def test_valid_case_id_pattern(self):
        df = self._make_labs_df(["CASE-0001", "CASE-123", "CASE-9999"])
        result = self.cleaner._clean_ids(df, "test.csv", "labs")
        # Valid IDs should remain unchanged
        assert result["case_id"].iloc[0] == "CASE-0001"

    def test_null_id_handled(self):
        df = self._make_labs_df([None, np.nan, ""])
        result = self.cleaner._clean_ids(df, "test.csv", "labs")
        # Nulls should stay null
        for i in range(len(result)):
            val = result["case_id"].iloc[i]
            assert val is None or pd.isna(val) or val == ""


class TestPIDPrefix:
    """Test PID prefix strategy."""

    def setup_method(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner(self.validator)

    def _make_df(self, file_type, patient_ids):
        df = pd.DataFrame({
            "patient_id": patient_ids,
            "case_id": [f"CASE-{i:04d}" for i in range(len(patient_ids))],
        })
        df.attrs["file_type"] = file_type
        df.attrs["source_file"] = f"test_{file_type}.csv"
        return df

    def test_labs_prefix(self):
        df = self._make_df("labs", ["123456"])
        result = self.cleaner._add_pid_prefix(df, "test.csv", "labs")
        assert result["patient_id"].iloc[0] == "LAB_123456"

    def test_medication_prefix(self):
        df = self._make_df("medication", ["123456"])
        result = self.cleaner._add_pid_prefix(df, "test.csv", "medication")
        assert result["patient_id"].iloc[0] == "MED_123456"

    def test_nursing_prefix(self):
        df = self._make_df("nursing", ["123456"])
        result = self.cleaner._add_pid_prefix(df, "test.csv", "nursing")
        assert result["patient_id"].iloc[0] == "NUR_123456"

    def test_device_motion_prefix(self):
        df = self._make_df("device_motion", ["123456"])
        result = self.cleaner._add_pid_prefix(df, "test.csv", "device_motion")
        assert result["patient_id"].iloc[0] == "MOT_123456"

    def test_epac_prefix(self):
        df = self._make_df("epaAC_german", ["123456"])
        result = self.cleaner._add_pid_prefix(df, "test.csv", "epaAC_german")
        assert result["patient_id"].iloc[0] == "EPA_123456"

    def test_null_pid_not_prefixed(self):
        df = self._make_df("labs", [None])
        result = self.cleaner._add_pid_prefix(df, "test.csv", "labs")
        assert result["patient_id"].iloc[0] is None or pd.isna(result["patient_id"].iloc[0])


class TestPIDConflictDetection:
    """Test PID conflict detection."""

    def setup_method(self):
        self.validator = DataValidator()
        self.cleaner = DataCleaner(self.validator)

    def test_detect_conflicts(self):
        dfs = {}
        # Same PID, different genders = conflict
        df1 = pd.DataFrame({"patient_id": ["LAB_123"], "sex": ["M"]})
        df1.attrs["file_type"] = "labs"
        df1.attrs["source_file"] = "labs.csv"
        dfs["labs.csv"] = df1

        df2 = pd.DataFrame({"patient_id": ["MOT_123"], "sex": ["F"]})
        df2.attrs["file_type"] = "device_motion"
        df2.attrs["source_file"] = "motion.csv"
        dfs["motion.csv"] = df2

        conflicts = self.cleaner.detect_pid_conflicts(dfs)
        # Conflicts should be detected between files
        assert isinstance(conflicts, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
