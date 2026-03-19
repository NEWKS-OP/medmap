"""Test validator regex patterns and constants."""

import os
import sys
import re
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.validator import (
    CASE_ID_PATTERN, PATIENT_ID_PATTERN,
    DATE_COLUMNS, GENDER_COLUMNS,
    NUMERIC_CLINICAL_COLS, LAB_FLAG_COLUMNS,
)


class TestCaseIDPattern:
    """Test case ID regex pattern."""

    def test_valid_case_3_digits(self):
        assert CASE_ID_PATTERN.match("CASE-001")

    def test_valid_case_4_digits(self):
        assert CASE_ID_PATTERN.match("CASE-0001")

    def test_invalid_no_prefix(self):
        assert not CASE_ID_PATTERN.match("0001")

    def test_invalid_lowercase(self):
        assert not CASE_ID_PATTERN.match("case-001")

    def test_invalid_too_few_digits(self):
        assert not CASE_ID_PATTERN.match("CASE-01")

    def test_invalid_letters_after_dash(self):
        assert not CASE_ID_PATTERN.match("CASE-ABC")


class TestPatientIDPattern:
    """Test patient ID regex pattern."""

    def test_valid_4_digits(self):
        assert PATIENT_ID_PATTERN.match("1234")

    def test_valid_5_digits(self):
        assert PATIENT_ID_PATTERN.match("12345")

    def test_valid_6_digits(self):
        assert PATIENT_ID_PATTERN.match("123456")

    def test_valid_with_pat_prefix(self):
        assert PATIENT_ID_PATTERN.match("PAT-1234")

    def test_invalid_too_short(self):
        assert not PATIENT_ID_PATTERN.match("12")

    def test_invalid_letters(self):
        assert not PATIENT_ID_PATTERN.match("ABCD")


class TestDateColumns:
    """Test date columns configuration."""

    def test_labs_has_specimen_datetime(self):
        assert "specimen_datetime" in DATE_COLUMNS["labs"]

    def test_icd10_has_admission_date(self):
        assert "admission_date" in DATE_COLUMNS["icd10_ops"]

    def test_icd10_has_discharge_date(self):
        assert "discharge_date" in DATE_COLUMNS["icd10_ops"]

    def test_device_motion_has_timestamp(self):
        assert "timestamp" in DATE_COLUMNS["device_motion"]

    def test_device_1hz_has_timestamp(self):
        assert "timestamp" in DATE_COLUMNS["device_1hz"]

    def test_nursing_has_report_date(self):
        assert "report_date" in DATE_COLUMNS["nursing"]


class TestGenderColumns:
    """Test gender column set."""

    def test_sex_column(self):
        assert "sex" in GENDER_COLUMNS

    def test_gender_column(self):
        assert "gender" in GENDER_COLUMNS

    def test_coGender_column(self):
        assert "coGender" in GENDER_COLUMNS

    def test_geschlecht_column(self):
        assert "Geschlecht" in GENDER_COLUMNS


class TestNumericClinicalCols:
    """Test numeric clinical columns set."""

    def test_sodium_included(self):
        assert "sodium_mmol_L" in NUMERIC_CLINICAL_COLS

    def test_potassium_included(self):
        assert "potassium_mmol_L" in NUMERIC_CLINICAL_COLS

    def test_creatinine_included(self):
        assert "creatinine_mg_dL" in NUMERIC_CLINICAL_COLS

    def test_bmi_included(self):
        assert "bmi" in NUMERIC_CLINICAL_COLS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
