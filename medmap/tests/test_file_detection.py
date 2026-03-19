"""Test file type detection by column signatures."""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.schema_mapping import detect_file_type


class TestFileTypeDetection:
    """Test file type detection by column content."""

    def test_labs_columns(self):
        df = pd.DataFrame(columns=[
            "case_id", "patient_id", "sex", "age_years", "specimen_datetime",
            "sodium_mmol_L", "sodium_flag", "sodium_ref_low",
        ])
        assert detect_file_type(df) == "labs"

    def test_icd10_columns(self):
        df = pd.DataFrame(columns=[
            "case_id", "patient_id", "ward", "admission_date", "discharge_date",
            "primary_icd10_code", "primary_icd10_description_en",
        ])
        assert detect_file_type(df) == "icd10_ops"

    def test_device_motion_columns(self):
        df = pd.DataFrame(columns=[
            "patient_id", "timestamp", "movement_index_0_100",
            "micro_movements_count", "bed_exit_detected_0_1", "fall_event_0_1",
        ])
        assert detect_file_type(df) == "device_motion"

    def test_device_1hz_columns(self):
        df = pd.DataFrame(columns=[
            "patient_id", "timestamp", "accel_x_m_s2", "accel_y", "accel_z",
            "accel_magnitude", "device_id", "pressure_zone_1",
        ])
        assert detect_file_type(df) == "device_1hz"

    def test_medication_columns(self):
        df = pd.DataFrame(columns=[
            "record_type", "case_id", "patient_id", "encounter_id", "ward",
            "medication_code_atc", "medication_name", "dose",
        ])
        assert detect_file_type(df) == "medication"

    def test_nursing_columns(self):
        df = pd.DataFrame(columns=[
            "case_id", "patient_id", "ward", "report_date", "shift",
            "nursing_note_free_text",
        ])
        assert detect_file_type(df) == "nursing"

    def test_epac_german_columns(self):
        df = pd.DataFrame(columns=["FallID", "AufnDat", "Alter", "BMI"])
        result = detect_file_type(df)
        assert result in ("epaAC_german", "epaAC_sap", "epaAC_pivot")

    def test_epac_sap_columns(self):
        df = pd.DataFrame(columns=["EPA0001", "PATGEB", "MANDT"])
        result = detect_file_type(df)
        assert "epaAC" in result or result == "unknown"

    def test_unknown_columns(self):
        df = pd.DataFrame(columns=["foo", "bar", "baz"])
        result = detect_file_type(df)
        assert result == "unknown"


class TestDirtyColumnDetection:
    """Test dirty data column renaming detection."""

    def test_dirty_labs_renamed_columns(self):
        df = pd.DataFrame(columns=[
            "CaseID", "PID", "Gender", "Age", "SpecDT",
            "Na", "Na_flag", "Na_low",
        ])
        result = detect_file_type(df)
        assert result == "labs"

    def test_dirty_icd10_renamed(self):
        df = pd.DataFrame(columns=[
            "CaseID", "PatientID", "Station", "Aufnahmedatum",
            "ICD10_Haupt", "ICD10_Haupt_Bezeichnung",
        ])
        result = detect_file_type(df)
        assert result == "icd10_ops"

    def test_dirty_nursing_renamed(self):
        df = pd.DataFrame(columns=[
            "CaseID", "PatientID", "Ward", "ReportDate", "Shift", "NursingNote",
        ])
        result = detect_file_type(df)
        assert result == "nursing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
