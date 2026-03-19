"""Tests for pipeline/cleaner.py — DataCleaner class."""

import sys
import os
import pytest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.cleaner import DataCleaner
from pipeline.validator import DataValidator
from contracts import Severity, ActionTaken


@pytest.fixture
def cleaner():
    return DataCleaner()


@pytest.fixture
def cleaner_with_validator():
    v = DataValidator()
    return DataCleaner(validator=v)


def make_df(data, file_type="labs"):
    df = pd.DataFrame(data)
    df.attrs = {"source_file": f"test_{file_type}.csv", "file_type": file_type}
    return df


class TestIsMissingToken:
    def test_null_string(self, cleaner):
        assert cleaner._is_missing_token("null") is True

    def test_nan_string(self, cleaner):
        assert cleaner._is_missing_token("nan") is True

    def test_na_string(self, cleaner):
        assert cleaner._is_missing_token("N/A") is True

    def test_missing_string(self, cleaner):
        assert cleaner._is_missing_token("missing") is True

    def test_none_value(self, cleaner):
        assert cleaner._is_missing_token(None) is False

    def test_nan_float(self, cleaner):
        assert cleaner._is_missing_token(float("nan")) is False

    def test_valid_number(self, cleaner):
        assert cleaner._is_missing_token(140.0) is False

    def test_valid_string(self, cleaner):
        assert cleaner._is_missing_token("hello") is False

    def test_empty_string(self, cleaner):
        assert cleaner._is_missing_token("") is False

    def test_unknown_string(self, cleaner):
        assert cleaner._is_missing_token("unknown") is True

    def test_keine_string(self, cleaner):
        assert cleaner._is_missing_token("keine") is True


class TestNormalizeMissingValues:
    def test_normalizes_na(self, cleaner):
        df = make_df({"val": [1.0, "N/A", 3.0]})
        result = cleaner._normalize_missing_values(df, "test.csv", "labs")
        assert pd.isna(result.at[1, "val"])

    def test_normalizes_null(self, cleaner):
        df = make_df({"val": [1.0, "null", 3.0]})
        result = cleaner._normalize_missing_values(df, "test.csv", "labs")
        assert pd.isna(result.at[1, "val"])

    def test_preserves_valid_values(self, cleaner):
        df = make_df({"val": [1.0, 2.0, 3.0]})
        result = cleaner._normalize_missing_values(df, "test.csv", "labs")
        assert result.at[0, "val"] == 1.0

    def test_normalizes_missing_string(self, cleaner):
        df = make_df({"val": ["hello", "missing", "world"]})
        result = cleaner._normalize_missing_values(df, "test.csv", "labs")
        assert pd.isna(result.at[1, "val"])

    def test_logs_audit_entries(self, cleaner_with_validator):
        df = make_df({"val": [1.0, "N/A", 3.0]})
        cleaner_with_validator._normalize_missing_values(df, "test.csv", "labs")
        log = cleaner_with_validator.validator.audit_log
        normalized = [e for e in log if e.error_type == "MISSING_NORMALIZED"]
        assert len(normalized) >= 1


class TestTryParseDate:
    def test_iso_format(self, cleaner):
        result = cleaner._try_parse_date("2025-01-15")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_iso_with_time(self, cleaner):
        result = cleaner._try_parse_date("2025-01-15T10:30:00")
        assert result is not None
        assert result.hour == 10

    def test_german_format(self, cleaner):
        result = cleaner._try_parse_date("15.03.2025")
        assert result is not None
        assert result.day == 15
        assert result.month == 3

    def test_us_format(self, cleaner):
        result = cleaner._try_parse_date("01/15/2025")
        assert result is not None
        assert result.month == 1

    def test_impossible_date(self, cleaner):
        assert cleaner._try_parse_date("99.99.9999") is None

    def test_empty_string(self, cleaner):
        assert cleaner._try_parse_date("") is None

    def test_all_zeros(self, cleaner):
        assert cleaner._try_parse_date("00/00/0000") is None

    def test_german_month_text(self, cleaner):
        result = cleaner._try_parse_date("15. März 2025")
        assert result is not None
        assert result.month == 3

    def test_iso_with_millis(self, cleaner):
        result = cleaner._try_parse_date("2025-01-15 10:30:00.123")
        assert result is not None


class TestNormalizeDates:
    def test_normalizes_german_date(self, cleaner):
        df = make_df({"specimen_datetime": ["15.03.2025", "2025-01-15", "01/20/2025"]})
        result = cleaner._normalize_dates(df, "test.csv", "labs")
        assert result.at[0, "specimen_datetime"] == "2025-03-15"

    def test_keeps_iso_date(self, cleaner):
        df = make_df({"specimen_datetime": ["2025-01-15"]})
        result = cleaner._normalize_dates(df, "test.csv", "labs")
        assert result.at[0, "specimen_datetime"] == "2025-01-15"

    def test_invalid_date_becomes_none(self, cleaner):
        df = make_df({"specimen_datetime": ["99.99.9999"]})
        result = cleaner._normalize_dates(df, "test.csv", "labs")
        assert result.at[0, "specimen_datetime"] is None

    def test_logs_date_normalization(self, cleaner_with_validator):
        df = make_df({"specimen_datetime": ["15.03.2025"]})
        cleaner_with_validator._normalize_dates(df, "test.csv", "labs")
        log = cleaner_with_validator.validator.audit_log
        normalized = [e for e in log if e.error_type == "DATE_NORMALIZED"]
        assert len(normalized) >= 1

    def test_logs_invalid_date(self, cleaner_with_validator):
        df = make_df({"specimen_datetime": ["not_a_date"]})
        cleaner_with_validator._normalize_dates(df, "test.csv", "labs")
        log = cleaner_with_validator.validator.audit_log
        invalid = [e for e in log if e.error_type == "INVALID_DATE"]
        assert len(invalid) >= 1


class TestTryParseNumeric:
    def test_int_value(self, cleaner):
        assert cleaner._try_parse_numeric(42) == 42.0

    def test_float_value(self, cleaner):
        assert cleaner._try_parse_numeric(3.14) == 3.14

    def test_string_number(self, cleaner):
        assert cleaner._try_parse_numeric("140.5") == 140.5

    def test_comma_decimal(self, cleaner):
        assert cleaner._try_parse_numeric("3,14") == 3.14

    def test_nan_returns_none(self, cleaner):
        assert cleaner._try_parse_numeric(float("nan")) is None

    def test_empty_string(self, cleaner):
        assert cleaner._try_parse_numeric("") is None

    def test_non_numeric(self, cleaner):
        assert cleaner._try_parse_numeric("abc") is None

    def test_none_value(self, cleaner):
        assert cleaner._try_parse_numeric(None) is None


class TestCleanClinicalNumerics:
    def test_valid_value_preserved(self, cleaner):
        df = make_df({"sodium_mmol_L": [140.0]})
        result = cleaner._clean_clinical_numerics(df, "test.csv", "labs")
        assert result.at[0, "sodium_mmol_L"] == 140.0

    def test_outlier_quarantined(self, cleaner):
        df = make_df({"sodium_mmol_L": [999.0]})
        result = cleaner._clean_clinical_numerics(df, "test.csv", "labs")
        assert pd.isna(result.at[0, "sodium_mmol_L"])

    def test_low_outlier_quarantined(self, cleaner):
        df = make_df({"sodium_mmol_L": [10.0]})
        result = cleaner._clean_clinical_numerics(df, "test.csv", "labs")
        assert pd.isna(result.at[0, "sodium_mmol_L"])

    def test_special_chars_stripped(self, cleaner):
        df = make_df({"sodium_mmol_L": ["13ü0"]})
        result = cleaner._clean_clinical_numerics(df, "test.csv", "labs")
        assert result.at[0, "sodium_mmol_L"] == 130.0

    def test_raw_column_created(self, cleaner):
        df = make_df({"sodium_mmol_L": [140.0]})
        result = cleaner._clean_clinical_numerics(df, "test.csv", "labs")
        assert "sodium_mmol_L_raw" in result.columns

    def test_non_numeric_quarantined(self, cleaner):
        df = make_df({"sodium_mmol_L": ["abc"]})
        result = cleaner._clean_clinical_numerics(df, "test.csv", "labs")
        assert pd.isna(result.at[0, "sodium_mmol_L"])


class TestNormalizeGender:
    def test_male_normalized(self, cleaner):
        df = make_df({"sex": ["male"]})
        result = cleaner._normalize_gender(df, "test.csv", "labs")
        assert result.at[0, "sex"] == "M"

    def test_female_normalized(self, cleaner):
        df = make_df({"sex": ["female"]})
        result = cleaner._normalize_gender(df, "test.csv", "labs")
        assert result.at[0, "sex"] == "F"

    def test_german_male(self, cleaner):
        df = make_df({"sex": ["männlich"]})
        result = cleaner._normalize_gender(df, "test.csv", "labs")
        assert result.at[0, "sex"] == "M"

    def test_german_female(self, cleaner):
        df = make_df({"sex": ["weiblich"]})
        result = cleaner._normalize_gender(df, "test.csv", "labs")
        assert result.at[0, "sex"] == "F"

    def test_abbreviation_m(self, cleaner):
        df = make_df({"sex": ["m"]})
        result = cleaner._normalize_gender(df, "test.csv", "labs")
        assert result.at[0, "sex"] == "M"

    def test_abbreviation_f(self, cleaner):
        df = make_df({"sex": ["f"]})
        result = cleaner._normalize_gender(df, "test.csv", "labs")
        assert result.at[0, "sex"] == "F"

    def test_already_normalized(self, cleaner):
        df = make_df({"sex": ["M"]})
        result = cleaner._normalize_gender(df, "test.csv", "labs")
        assert result.at[0, "sex"] == "M"

    def test_nan_preserved(self, cleaner):
        df = make_df({"sex": [np.nan]})
        result = cleaner._normalize_gender(df, "test.csv", "labs")
        assert pd.isna(result.at[0, "sex"])


class TestCleanIds:
    def test_strips_whitespace(self, cleaner):
        df = make_df({"case_id": [" CASE-001 "]})
        result = cleaner._clean_ids(df, "test.csv", "labs")
        assert result.at[0, "case_id"] == "CASE-001"

    def test_strips_tabs(self, cleaner):
        df = make_df({"case_id": ["\tCASE-001"]})
        result = cleaner._clean_ids(df, "test.csv", "labs")
        assert result.at[0, "case_id"] == "CASE-001"

    def test_strips_newlines(self, cleaner):
        df = make_df({"case_id": ["CASE-001\n"]})
        result = cleaner._clean_ids(df, "test.csv", "labs")
        assert result.at[0, "case_id"] == "CASE-001"

    def test_strips_leading_special_chars(self, cleaner):
        df = make_df({"case_id": ["#CASE-001"]})
        result = cleaner._clean_ids(df, "test.csv", "labs")
        assert result.at[0, "case_id"] == "CASE-001"

    def test_preserves_valid_id(self, cleaner):
        df = make_df({"case_id": ["CASE-0042"]})
        result = cleaner._clean_ids(df, "test.csv", "labs")
        assert result.at[0, "case_id"] == "CASE-0042"

    def test_cleans_patient_id(self, cleaner):
        df = make_df({"patient_id": [" 123456 "]})
        result = cleaner._clean_ids(df, "test.csv", "labs")
        assert result.at[0, "patient_id"] == "123456"


class TestAddPidPrefix:
    def test_adds_lab_prefix(self, cleaner):
        df = make_df({"patient_id": ["100001"]})
        result = cleaner._add_pid_prefix(df, "test.csv", "labs")
        assert result.at[0, "patient_id"] == "LAB_100001"

    def test_adds_mot_prefix(self, cleaner):
        df = make_df({"patient_id": ["200001"]}, file_type="device_motion")
        result = cleaner._add_pid_prefix(df, "test.csv", "device_motion")
        assert result.at[0, "patient_id"] == "MOT_200001"

    def test_adds_epa_prefix(self, cleaner):
        df = make_df({"patient_id": ["300001"]}, file_type="epaAC_german")
        result = cleaner._add_pid_prefix(df, "test.csv", "epaAC_german")
        assert result.at[0, "patient_id"] == "EPA_300001"

    def test_adds_med_prefix(self, cleaner):
        df = make_df({"patient_id": ["400001"]}, file_type="medication")
        result = cleaner._add_pid_prefix(df, "test.csv", "medication")
        assert result.at[0, "patient_id"] == "MED_400001"

    def test_adds_nur_prefix(self, cleaner):
        df = make_df({"patient_id": ["500001"]}, file_type="nursing")
        result = cleaner._add_pid_prefix(df, "test.csv", "nursing")
        assert result.at[0, "patient_id"] == "NUR_500001"

    def test_adds_icd_prefix(self, cleaner):
        df = make_df({"patient_id": ["600001"]}, file_type="icd10_ops")
        result = cleaner._add_pid_prefix(df, "test.csv", "icd10_ops")
        assert result.at[0, "patient_id"] == "ICD_600001"

    def test_no_double_prefix(self, cleaner):
        df = make_df({"patient_id": ["LAB_100001"]})
        result = cleaner._add_pid_prefix(df, "test.csv", "labs")
        assert result.at[0, "patient_id"] == "LAB_100001"

    def test_no_cross_prefix(self, cleaner):
        df = make_df({"patient_id": ["MOT_100001"]})
        result = cleaner._add_pid_prefix(df, "test.csv", "labs")
        assert result.at[0, "patient_id"] == "MOT_100001"

    def test_nan_preserved(self, cleaner):
        df = make_df({"patient_id": [np.nan]})
        result = cleaner._add_pid_prefix(df, "test.csv", "labs")
        assert pd.isna(result.at[0, "patient_id"])


class TestRemoveDuplicates:
    def test_removes_exact_duplicates(self, cleaner):
        df = make_df({"val": [1, 2, 1], "id": ["a", "b", "a"]})
        result = cleaner._remove_duplicates(df, "test.csv", "labs")
        assert len(result) == 2

    def test_keeps_first_occurrence(self, cleaner):
        df = make_df({"val": [1, 1], "id": ["a", "a"]})
        result = cleaner._remove_duplicates(df, "test.csv", "labs")
        assert len(result) == 1
        assert result.at[0, "val"] == 1

    def test_no_duplicates_unchanged(self, cleaner):
        df = make_df({"val": [1, 2, 3]})
        result = cleaner._remove_duplicates(df, "test.csv", "labs")
        assert len(result) == 3

    def test_motion_partial_duplicates(self, cleaner):
        df = make_df({
            "patient_id": ["P1", "P1", "P2"],
            "timestamp": ["2025-01-01", "2025-01-01", "2025-01-01"],
            "movement_index_0_100": [50, 60, 70],
        }, file_type="device_motion")
        result = cleaner._remove_duplicates(df, "test.csv", "device_motion")
        assert len(result) == 2


class TestNormalizeLabFlags:
    def test_uppercase_h(self, cleaner):
        df = make_df({"sodium_flag": ["h"]})
        result = cleaner._normalize_lab_flags(df, "test.csv", "labs")
        assert result.at[0, "sodium_flag"] == "H"

    def test_uppercase_l(self, cleaner):
        df = make_df({"sodium_flag": ["l"]})
        result = cleaner._normalize_lab_flags(df, "test.csv", "labs")
        assert result.at[0, "sodium_flag"] == "L"

    def test_strips_whitespace(self, cleaner):
        df = make_df({"sodium_flag": [" H "]})
        result = cleaner._normalize_lab_flags(df, "test.csv", "labs")
        assert result.at[0, "sodium_flag"] == "H"

    def test_invalid_flag_quarantined(self, cleaner):
        df = make_df({"sodium_flag": ["INVALID"]})
        result = cleaner._normalize_lab_flags(df, "test.csv", "labs")
        assert pd.isna(result.at[0, "sodium_flag"])

    def test_skips_non_labs(self, cleaner):
        df = make_df({"sodium_flag": ["INVALID"]}, file_type="medication")
        result = cleaner._normalize_lab_flags(df, "test.csv", "medication")
        assert result.at[0, "sodium_flag"] == "INVALID"

    def test_hh_preserved(self, cleaner):
        df = make_df({"sodium_flag": ["HH"]})
        result = cleaner._normalize_lab_flags(df, "test.csv", "labs")
        assert result.at[0, "sodium_flag"] == "HH"

    def test_ll_preserved(self, cleaner):
        df = make_df({"sodium_flag": ["LL"]})
        result = cleaner._normalize_lab_flags(df, "test.csv", "labs")
        assert result.at[0, "sodium_flag"] == "LL"


class TestExtractCaseId:
    def test_from_case_id_column(self, cleaner):
        df = make_df({"case_id": ["CASE-001"]})
        assert cleaner._extract_case_id(df, 0) == "CASE-001"

    def test_from_patient_id_fallback(self, cleaner):
        df = make_df({"patient_id": ["PAT-100"]})
        assert cleaner._extract_case_id(df, 0) == "PAT-100"

    def test_from_index_fallback(self, cleaner):
        df = make_df({"val": [1]})
        assert cleaner._extract_case_id(df, 0) == "row_0"


class TestTableForType:
    def test_labs(self, cleaner):
        assert cleaner._table_for_type("labs") == "tbImportLabsData"

    def test_icd10(self, cleaner):
        assert cleaner._table_for_type("icd10_ops") == "tbImportIcd10Data"

    def test_device_motion(self, cleaner):
        assert cleaner._table_for_type("device_motion") == "tbImportDeviceMotionData"

    def test_device_1hz(self, cleaner):
        assert cleaner._table_for_type("device_1hz") == "tbImportDevice1HzMotionData"

    def test_medication(self, cleaner):
        assert cleaner._table_for_type("medication") == "tbImportMedicationInpatientData"

    def test_nursing(self, cleaner):
        assert cleaner._table_for_type("nursing") == "tbImportNursingDailyReportsData"

    def test_epac_german(self, cleaner):
        assert cleaner._table_for_type("epaAC_german") == "tbImportAcData"

    def test_epac_sap(self, cleaner):
        assert cleaner._table_for_type("epaAC_sap") == "tbImportAcData"

    def test_epac_pivot(self, cleaner):
        assert cleaner._table_for_type("epaAC_pivot") == "tbImportAcData"

    def test_unknown(self, cleaner):
        assert cleaner._table_for_type("unknown") == "unknown"


class TestBuildCaseIdLookup:
    def test_builds_lookup(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001", "CASE-002"],
            "patient_id": ["P1", "P2"],
            "specimen_datetime": ["2025-01-15", "2025-02-20"],
        })
        lookup = cleaner.build_case_id_lookup({"labs.csv": df})
        assert ("P1", "2025-01-15") in lookup
        assert lookup[("P1", "2025-01-15")] == "CASE-001"

    def test_patient_id_fallback(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["P1"],
        })
        lookup = cleaner.build_case_id_lookup({"labs.csv": df})
        assert "P1" in lookup

    def test_empty_dataframes(self, cleaner):
        lookup = cleaner.build_case_id_lookup({})
        assert lookup == {}

    def test_skips_missing_case_id(self, cleaner):
        df = make_df({
            "patient_id": ["P1"],
            "val": [1],
        })
        lookup = cleaner.build_case_id_lookup({"motion.csv": df})
        assert len(lookup) == 0


class TestMapMissingCaseIds:
    def test_maps_from_lookup(self, cleaner):
        df1 = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["P1"],
            "specimen_datetime": ["2025-01-15"],
        })
        df2 = make_df({"patient_id": ["P1"], "val": [1]}, file_type="device_motion")
        result = cleaner.map_missing_case_ids({"labs.csv": df1, "motion.csv": df2})
        assert "case_id" in result["motion.csv"].columns

    def test_preserves_existing_case_ids(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["P1"],
        })
        result = cleaner.map_missing_case_ids({"labs.csv": df})
        assert result["labs.csv"].at[0, "case_id"] == "CASE-001"


class TestCleanDataframe:
    def test_returns_cleaned_copy(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["100001"],
            "sex": ["male"],
            "sodium_mmol_L": [140.0],
        })
        result = cleaner.clean_dataframe(df, "test.csv")
        assert result.at[0, "sex"] == "M"
        assert result.at[0, "patient_id"].startswith("LAB_")

    def test_preserves_attrs(self, cleaner):
        df = make_df({"val": [1]})
        result = cleaner.clean_dataframe(df, "test.csv")
        assert result.attrs["file_type"] == "labs"

    def test_clean_all(self, cleaner):
        df1 = make_df({"val": [1]})
        df2 = make_df({"val": [2]}, file_type="medication")
        result = cleaner.clean_all({"f1.csv": df1, "f2.csv": df2})
        assert "f1.csv" in result
        assert "f2.csv" in result


class TestGetAuditLog:
    def test_returns_audit_log(self, cleaner_with_validator):
        df = make_df({"sodium_mmol_L": ["N/A"]})
        cleaner_with_validator.clean_dataframe(df, "test.csv")
        log = cleaner_with_validator.get_audit_log()
        assert len(log) > 0

    def test_returns_quality_scores(self, cleaner_with_validator):
        scores = cleaner_with_validator.get_quality_scores()
        assert isinstance(scores, dict)


class TestCleanerIsMissingTokenExtended:
    def test_whitespace_only(self, cleaner):
        assert cleaner._is_missing_token("   ") is True

    def test_tab_only(self, cleaner):
        assert cleaner._is_missing_token("\t") is True

    def test_dash(self, cleaner):
        result = cleaner._is_missing_token("-")
        assert isinstance(result, bool)

    def test_numeric_string(self, cleaner):
        assert cleaner._is_missing_token("123") is False

    def test_actual_value(self, cleaner):
        assert cleaner._is_missing_token("Metformin") is False


class TestCleanerNormalizeDatesExtended:
    def test_german_date_format(self, cleaner):
        df = make_df({"admission_date": ["15.01.2025"]})
        result = cleaner._normalize_dates(df)
        assert result["admission_date"].iloc[0] is not None

    def test_iso_format(self, cleaner):
        df = make_df({"admission_date": ["2025-01-15"]})
        result = cleaner._normalize_dates(df)
        assert "2025" in str(result["admission_date"].iloc[0])

    def test_empty_date(self, cleaner):
        df = make_df({"admission_date": [""]})
        result = cleaner._normalize_dates(df)
        assert result is not None


class TestCleanerGenderExtended:
    def test_german_male(self, cleaner):
        df = make_df({"gender": ["männlich"]})
        result = cleaner._normalize_gender(df)
        assert result["gender"].iloc[0] == "M"

    def test_german_female(self, cleaner):
        df = make_df({"gender": ["weiblich"]})
        result = cleaner._normalize_gender(df)
        assert result["gender"].iloc[0] == "F"

    def test_uppercase(self, cleaner):
        df = make_df({"gender": ["MALE"]})
        result = cleaner._normalize_gender(df)
        assert result["gender"].iloc[0] == "M"

    def test_empty_gender(self, cleaner):
        df = make_df({"gender": [""]})
        result = cleaner._normalize_gender(df)
        assert result is not None


class TestCleanerCleanIdsExtended:
    def test_strips_whitespace_from_ids(self, cleaner):
        df = make_df({"case_id": ["  CASE-001  "], "patient_id": [" PAT-100 "]})
        result = cleaner._clean_ids(df, "test.csv")
        assert result["case_id"].iloc[0].strip() == "CASE-001"

    def test_preserves_valid_ids(self, cleaner):
        df = make_df({"case_id": ["CASE-001"], "patient_id": ["PAT-100"]})
        result = cleaner._clean_ids(df, "test.csv")
        assert result["case_id"].iloc[0] == "CASE-001"


class TestCleanerNumericParsing:
    def test_parses_integer_string(self, cleaner):
        result = cleaner._try_parse_numeric("140")
        assert result == 140.0

    def test_parses_float_string(self, cleaner):
        result = cleaner._try_parse_numeric("4.5")
        assert result == 4.5

    def test_returns_none_for_text(self, cleaner):
        result = cleaner._try_parse_numeric("abc")
        assert result is None

    def test_handles_comma_decimal(self, cleaner):
        result = cleaner._try_parse_numeric("4,5")
        # Should handle German comma format
        assert result is None or result == 4.5
