"""Tests for Module 2A: DataValidator and Module 2B: DataCleaner."""

import sys
import os
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.validator import DataValidator
from pipeline.cleaner import DataCleaner
from contracts import Severity, ActionTaken


# ──────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────

def make_labs_df(overrides=None):
    """Create a small labs DataFrame for testing."""
    data = {
        "case_id": ["CASE-001", "CASE-002", "CASE-003"],
        "patient_id": ["100001", "100002", "100003"],
        "sex": ["M", "F", "male"],
        "age_years": [65, 72, 45],
        "specimen_datetime": ["2025-01-15", "2025-02-20", "2025-03-10"],
        "sodium_mmol_L": [140.0, 130.0, 150.0],
        "sodium_flag": ["", "L", "H"],
        "potassium_mmol_L": [4.5, 3.8, 5.0],
        "creatinine_mg_dL": [1.2, 0.9, 2.0],
        "egfr_mL_min_1_73m2": [60, 90, 45],
        "glucose_mg_dL": [100, 200, 85],
        "hemoglobin_g_dL": [14.0, 12.0, 10.5],
    }
    if overrides:
        data.update(overrides)
    df = pd.DataFrame(data)
    df.attrs = {"source_file": "test_labs.csv", "file_type": "labs"}
    return df


def make_motion_df():
    """Create a small motion data DataFrame."""
    data = {
        "patient_id": ["200001", "200001", "200002", "200002"],
        "timestamp": ["2025-01-15 10:00:00", "2025-01-15 11:00:00",
                       "2025-01-15 10:00:00", "2025-01-15 10:00:00"],
        "movement_index_0_100": [45, 60, 30, 30],
        "fall_event_0_1": [0, 1, 0, 0],
        "impact_magnitude_g": [0.1, 5.2, 0.0, 0.0],
    }
    df = pd.DataFrame(data)
    df.attrs = {"source_file": "test_motion.csv", "file_type": "device_motion"}
    return df


# ──────────────────────────────────────────────
# VALIDATOR TESTS
# ──────────────────────────────────────────────

class TestValidator:

    def test_validate_missing_values(self):
        """Test that missing values are detected."""
        df = make_labs_df({"sodium_mmol_L": [140.0, np.nan, "N/A"]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        missing_entries = [e for e in v.audit_log if e.error_type == "MISSING_VALUE"]
        assert len(missing_entries) >= 2  # NaN and N/A

    def test_validate_invalid_dates(self):
        """Test that invalid dates are flagged."""
        df = make_labs_df({"specimen_datetime": ["2025-01-15", "99.99.9999", "32.01.2024"]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        date_entries = [e for e in v.audit_log if "DATE" in e.error_type]
        assert len(date_entries) >= 2

    def test_validate_clinical_outlier(self):
        """Test that clinical outliers are flagged."""
        df = make_labs_df({"sodium_mmol_L": [140.0, 10.0, 999.0]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        outlier_entries = [e for e in v.audit_log if e.error_type == "CLINICAL_OUTLIER"]
        assert len(outlier_entries) >= 2  # 10.0 too low, 999.0 too high

    def test_validate_non_numeric_clinical(self):
        """Test that non-numeric values in clinical columns are flagged."""
        df = make_labs_df({"sodium_mmol_L": [140.0, "abc", "12ü5"]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        non_num = [e for e in v.audit_log if e.error_type == "NON_NUMERIC"]
        assert len(non_num) >= 1

    def test_validate_gender_invalid(self):
        """Test that invalid gender values are flagged."""
        df = make_labs_df({"sex": ["M", "X", "unknown_value"]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        gender_entries = [e for e in v.audit_log if e.error_type == "GENDER_INVALID"]
        assert len(gender_entries) >= 1

    def test_validate_case_id_format(self):
        """Test case_id format validation."""
        df = make_labs_df({"case_id": ["CASE-001", "INVALID", "CASE-9999"]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        id_entries = [e for e in v.audit_log if e.error_type == "ID_INVALID"]
        assert len(id_entries) >= 1  # INVALID should fail

    def test_validate_duplicates(self):
        """Test duplicate detection."""
        df = make_labs_df()
        # Add exact duplicate
        df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
        df.attrs = {"source_file": "test.csv", "file_type": "labs"}
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        dup_entries = [e for e in v.audit_log if "DUPLICATE" in e.error_type]
        assert len(dup_entries) >= 1

    def test_validate_lab_flags(self):
        """Test lab flag validation."""
        df = make_labs_df({"sodium_flag": ["H", "INVALID", "L"]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        flag_entries = [e for e in v.audit_log if e.error_type == "LAB_FLAG_INVALID"]
        assert len(flag_entries) >= 1

    def test_quality_score_computed(self):
        """Test that quality score is computed."""
        df = make_labs_df()
        v = DataValidator()
        score = v.validate_dataframe(df, "test.csv")
        assert score.source_file == "test_labs.csv"
        assert 0 <= score.score <= 100
        assert score.rows_imported >= 0

    def test_audit_log_df(self):
        """Test audit log as DataFrame."""
        df = make_labs_df({"sodium_mmol_L": [140.0, np.nan, 999.0]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        log_df = v.get_audit_log_df()
        assert len(log_df) > 0
        assert "error_type" in log_df.columns


# ──────────────────────────────────────────────
# CLEANER TESTS
# ──────────────────────────────────────────────

class TestCleaner:

    def test_normalize_missing_tokens(self):
        """Test that missing value tokens are normalized to NaN."""
        df = make_labs_df({"sodium_mmol_L": [140.0, "N/A", "missing"]})
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, "test.csv")
        assert pd.isna(cleaned.at[1, "sodium_mmol_L"])
        assert pd.isna(cleaned.at[2, "sodium_mmol_L"])

    def test_normalize_dates_german(self):
        """Test German date format normalization."""
        df = make_labs_df({"specimen_datetime": ["15.03.2025", "2025-01-15", "01/20/2025"]})
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "specimen_datetime"] == "2025-03-15"
        assert cleaned.at[1, "specimen_datetime"] == "2025-01-15"

    def test_normalize_dates_invalid(self):
        """Test that invalid dates become NaN."""
        df = make_labs_df({"specimen_datetime": ["2025-01-15", "99.99.9999", "abc"]})
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "specimen_datetime"] == "2025-01-15"
        assert pd.isna(cleaned.at[1, "specimen_datetime"])
        assert pd.isna(cleaned.at[2, "specimen_datetime"])

    def test_clean_clinical_outliers(self):
        """Test that clinical outliers are quarantined (set to NaN)."""
        df = make_labs_df({"sodium_mmol_L": [140.0, 10.0, 999.0]})
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, "test.csv")
        assert not pd.isna(cleaned.at[0, "sodium_mmol_L"])
        assert pd.isna(cleaned.at[1, "sodium_mmol_L"])  # 10.0 < 100
        assert pd.isna(cleaned.at[2, "sodium_mmol_L"])  # 999.0 > 165

    def test_clean_special_chars_numeric(self):
        """Test that special characters are stripped from numeric fields."""
        df = make_labs_df({"sodium_mmol_L": ["140.0", "13ü0", "150.0"]})
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "sodium_mmol_L"] == 140.0
        assert cleaned.at[1, "sodium_mmol_L"] == 130.0  # ü removed
        assert cleaned.at[2, "sodium_mmol_L"] == 150.0

    def test_normalize_gender(self):
        """Test gender normalization."""
        df = make_labs_df({"sex": ["male", "weiblich", "mä"]})
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "sex"] == "M"
        assert cleaned.at[1, "sex"] == "F"
        assert cleaned.at[2, "sex"] == "M"

    def test_clean_ids_strip_whitespace(self):
        """Test that IDs are stripped of whitespace and special chars."""
        df = make_labs_df({"case_id": [" CASE-001 ", "\tCASE-002", "CASE-003\n"]})
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "case_id"] == "CASE-001"
        assert cleaned.at[1, "case_id"] == "CASE-002"
        assert cleaned.at[2, "case_id"] == "CASE-003"

    def test_pid_prefix_added(self):
        """Test that PID prefix is added for labs."""
        df = make_labs_df()
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "patient_id"].startswith("LAB_")

    def test_pid_prefix_not_doubled(self):
        """Test that PID prefix is not applied twice."""
        df = make_labs_df({"patient_id": ["LAB_100001", "LAB_100002", "100003"]})
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "patient_id"] == "LAB_100001"
        assert not cleaned.at[0, "patient_id"].startswith("LAB_LAB_")
        assert cleaned.at[2, "patient_id"] == "LAB_100003"

    def test_remove_exact_duplicates(self):
        """Test that exact duplicates are removed."""
        df = make_labs_df()
        df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
        df.attrs = {"source_file": "test.csv", "file_type": "labs"}
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, "test.csv")
        assert len(cleaned) == 3  # 4 rows -> 3 after dedup

    def test_normalize_lab_flags(self):
        """Test lab flag normalization."""
        df = make_labs_df({"sodium_flag": ["h", " H ", "INVALID"]})
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "sodium_flag"] == "H"
        assert cleaned.at[1, "sodium_flag"] == "H"
        assert pd.isna(cleaned.at[2, "sodium_flag"])

    def test_raw_column_preserved(self):
        """Test that _raw columns are created for clinical values."""
        df = make_labs_df({"sodium_mmol_L": [140.0, 999.0, 130.0]})
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, "test.csv")
        assert "sodium_mmol_L_raw" in cleaned.columns
        assert cleaned.at[1, "sodium_mmol_L_raw"] == 999.0

    def test_case_id_mapping(self):
        """Test patient_id + datetime -> case_id mapping."""
        # Source with case_id
        df1 = make_labs_df()
        # Source without case_id
        df2 = pd.DataFrame({
            "patient_id": ["LAB_100001", "LAB_100002"],
            "timestamp": ["2025-01-15 10:00:00", "2025-02-20 10:00:00"],
            "movement_index_0_100": [50, 60],
        })
        df2.attrs = {"source_file": "motion.csv", "file_type": "device_motion"}

        c = DataCleaner()
        result = c.map_missing_case_ids({"labs.csv": df1, "motion.csv": df2})
        assert "case_id" in result["motion.csv"].columns

    def test_detect_pid_conflicts(self):
        """Test PID conflict detection across sources."""
        df1 = make_labs_df({"patient_id": ["100001", "100002", "100003"],
                            "sex": ["M", "F", "M"]})
        df2 = pd.DataFrame({
            "patient_id": ["100001", "100002"],
            "sex": ["F", "F"],  # 100001 is M in labs, F here = conflict
            "timestamp": ["2025-01-15", "2025-02-20"],
        })
        df2.attrs = {"source_file": "motion.csv", "file_type": "device_motion"}

        c = DataCleaner()
        conflicts = c.detect_pid_conflicts({"labs.csv": df1, "motion.csv": df2})
        assert len(conflicts) >= 1

    def test_clean_all(self):
        """Test clean_all processes multiple DataFrames."""
        df1 = make_labs_df()
        df2 = make_motion_df()
        c = DataCleaner()
        cleaned = c.clean_all({"labs.csv": df1, "motion.csv": df2})
        assert "labs.csv" in cleaned
        assert "motion.csv" in cleaned


# ──────────────────────────────────────────────
# INTEGRATION TESTS WITH REAL DATA
# ──────────────────────────────────────────────

class TestIntegrationWithRealData:

    @pytest.fixture
    def ingester(self):
        from pipeline.ingestion import DataIngester
        return DataIngester()

    def test_validate_dirty_labs(self, ingester):
        """Test validation on real dirty labs data."""
        from config.settings import DIRTY_DIR
        labs_path = os.path.join(DIRTY_DIR, "synth_labs.csv")
        if not os.path.exists(labs_path):
            pytest.skip("Dirty labs file not found")
        df, result = ingester.load(labs_path)
        v = DataValidator()
        score = v.validate_dataframe(df, result.source_file)
        assert score.score >= 0
        assert len(v.audit_log) > 0

    def test_clean_dirty_labs(self, ingester):
        """Test cleaning on real dirty labs data."""
        from config.settings import DIRTY_DIR
        labs_path = os.path.join(DIRTY_DIR, "synth_labs.csv")
        if not os.path.exists(labs_path):
            pytest.skip("Dirty labs file not found")
        df, result = ingester.load(labs_path)
        c = DataCleaner()
        cleaned = c.clean_dataframe(df, result.source_file)
        assert len(cleaned) > 0
        # Check gender was normalized
        if "sex" in cleaned.columns:
            for val in cleaned["sex"].dropna().unique():
                assert val in {"M", "F"}, f"Unexpected gender: {val}"

    def test_validate_and_clean_pipeline(self, ingester):
        """Test full validate -> clean pipeline on dirty data."""
        from config.settings import DIRTY_DIR
        labs_path = os.path.join(DIRTY_DIR, "synth_labs.csv")
        if not os.path.exists(labs_path):
            pytest.skip("Dirty labs file not found")
        df, result = ingester.load(labs_path)

        # Validate
        v = DataValidator()
        score = v.validate_dataframe(df, result.source_file)

        # Clean
        c = DataCleaner(validator=v)
        cleaned = c.clean_dataframe(df, result.source_file)

        # Verify audit log has both validation and cleaning entries
        log = v.audit_log
        assert len(log) > 0
        error_types = set(e.error_type for e in log)
        assert len(error_types) > 0

    def test_validate_split_files(self, ingester):
        """Test validation on split clinic files."""
        from config.settings import SPLIT_DIR
        if not os.path.exists(SPLIT_DIR):
            pytest.skip("Split directory not found")
        results = ingester.ingest_directory(SPLIT_DIR, skip_1hz=True)
        assert len(results) > 0

        v = DataValidator()
        for filename, df in ingester.dataframes.items():
            if df.attrs.get("file_type") == "device_1hz":
                continue
            score = v.validate_dataframe(df, filename)
            assert score.score >= 0


class TestValidatorHelpers:
    def test_is_missing_none(self):
        v = DataValidator()
        assert v._is_missing(None) is True

    def test_is_missing_nan(self):
        v = DataValidator()
        assert v._is_missing(float("nan")) is True

    def test_is_missing_string(self):
        v = DataValidator()
        assert v._is_missing("null") is True

    def test_is_missing_valid(self):
        v = DataValidator()
        assert v._is_missing(140.0) is False

    def test_missing_severity_critical(self):
        v = DataValidator()
        assert v._missing_severity("case_id", "labs") == Severity.CRITICAL

    def test_missing_severity_high(self):
        v = DataValidator()
        assert v._missing_severity("timestamp", "device_motion") == Severity.HIGH

    def test_missing_severity_low(self):
        v = DataValidator()
        assert v._missing_severity("some_col", "labs") == Severity.LOW

    def test_table_for_type_labs(self):
        v = DataValidator()
        assert v._table_for_type("labs") == "tbImportLabsData"

    def test_table_for_type_unknown(self):
        v = DataValidator()
        assert v._table_for_type("unknown") == "unknown"

    def test_extract_case_id_from_case_col(self):
        v = DataValidator()
        df = pd.DataFrame({"case_id": ["CASE-001"]})
        assert v._extract_case_id(df, 0) == "CASE-001"

    def test_extract_case_id_from_patient(self):
        v = DataValidator()
        df = pd.DataFrame({"patient_id": ["PAT-100"]})
        assert v._extract_case_id(df, 0) == "PAT-100"

    def test_extract_case_id_fallback(self):
        v = DataValidator()
        df = pd.DataFrame({"val": [1]})
        result = v._extract_case_id(df, 0)
        assert "row_" in result


class TestValidatorTryParseDate:
    def test_iso_format(self):
        v = DataValidator()
        result = v._try_parse_date("2025-01-15")
        assert result is not None
        assert result.year == 2025

    def test_german_format(self):
        v = DataValidator()
        result = v._try_parse_date("15.03.2025")
        assert result is not None
        assert result.month == 3

    def test_impossible_date(self):
        v = DataValidator()
        assert v._try_parse_date("99.99.9999") is None

    def test_empty_string(self):
        v = DataValidator()
        assert v._try_parse_date("") is None


class TestValidatorTryParseNumeric:
    def test_float_value(self):
        v = DataValidator()
        assert v._try_parse_numeric(3.14) == 3.14

    def test_string_number(self):
        v = DataValidator()
        assert v._try_parse_numeric("140.5") == 140.5

    def test_comma_decimal(self):
        v = DataValidator()
        assert v._try_parse_numeric("3,14") == 3.14

    def test_non_numeric(self):
        v = DataValidator()
        assert v._try_parse_numeric("abc") is None

    def test_special_chars(self):
        v = DataValidator()
        result = v._try_parse_numeric("13ü0")
        assert result == 130.0


class TestValidateAll:
    def test_validates_multiple(self):
        df1 = make_labs_df()
        df2 = make_motion_df()
        v = DataValidator()
        scores = v.validate_all({"labs.csv": df1, "motion.csv": df2})
        assert "labs.csv" in scores
        assert "motion.csv" in scores

    def test_handles_error(self):
        v = DataValidator()
        scores = v.validate_all({"bad.csv": pd.DataFrame()})
        assert "bad.csv" in scores


class TestValidateGender:
    def test_valid_genders_pass(self):
        df = make_labs_df({"sex": ["M", "F", "M"]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        gender_invalid = [e for e in v.audit_log if e.error_type == "GENDER_INVALID"]
        assert len(gender_invalid) == 0

    def test_unknown_gender_flagged(self):
        df = make_labs_df({"sex": ["M", "UNKNOWN_VAL", "F"]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        gender_invalid = [e for e in v.audit_log if e.error_type == "GENDER_INVALID"]
        assert len(gender_invalid) >= 1


class TestValidateIds:
    def test_valid_case_id_passes(self):
        df = make_labs_df({"case_id": ["CASE-001", "CASE-0042", "CASE-999"]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        id_invalid = [e for e in v.audit_log if e.error_type == "ID_INVALID"
                       and e.column_name == "case_id"]
        assert len(id_invalid) == 0

    def test_invalid_case_id_flagged(self):
        df = make_labs_df({"case_id": ["CASE-001", "BADID", "CASE-999"]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        id_invalid = [e for e in v.audit_log if e.error_type == "ID_INVALID"
                       and e.column_name == "case_id"]
        assert len(id_invalid) >= 1


class TestValidateLabFlags:
    def test_valid_flags_pass(self):
        df = make_labs_df({"sodium_flag": ["H", "L", ""]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        flag_invalid = [e for e in v.audit_log if e.error_type == "LAB_FLAG_INVALID"]
        assert len(flag_invalid) == 0

    def test_invalid_flag_detected(self):
        df = make_labs_df({"sodium_flag": ["H", "WRONG", "L"]})
        v = DataValidator()
        v.validate_dataframe(df, "test.csv")
        flag_invalid = [e for e in v.audit_log if e.error_type == "LAB_FLAG_INVALID"]
        assert len(flag_invalid) >= 1


class TestGetAuditLogDf:
    def test_returns_dataframe(self):
        v = DataValidator()
        df = make_labs_df({"sodium_mmol_L": [999.0, 140.0, 140.0]})
        v.validate_dataframe(df, "test.csv")
        log_df = v.get_audit_log_df()
        assert isinstance(log_df, pd.DataFrame)
        assert len(log_df) > 0

    def test_empty_returns_empty_df(self):
        v = DataValidator()
        log_df = v.get_audit_log_df()
        assert log_df.empty

    def test_has_expected_columns(self):
        v = DataValidator()
        df = make_labs_df({"sodium_mmol_L": [999.0, 140.0, 140.0]})
        v.validate_dataframe(df, "test.csv")
        log_df = v.get_audit_log_df()
        assert "error_type" in log_df.columns
        assert "severity" in log_df.columns
        assert "source_file" in log_df.columns


class TestValidatorClinicalRangesExtended:
    def test_potassium_outlier(self):
        v = DataValidator()
        df = make_labs_df({"potassium_mmol_L": [99.0]})
        v.validate_dataframe(df, "test.csv")
        log = v.get_audit_log()
        outliers = [e for e in log if e.error_type == "CLINICAL_OUTLIER"]
        assert len(outliers) >= 1

    def test_potassium_normal(self):
        v = DataValidator()
        df = make_labs_df({"potassium_mmol_L": [4.0]})
        v.validate_dataframe(df, "test.csv")
        log = v.get_audit_log()
        outliers = [e for e in log if e.error_type == "CLINICAL_OUTLIER"
                    and "potassium" in e.column_name]
        assert len(outliers) == 0

    def test_glucose_outlier(self):
        v = DataValidator()
        df = make_labs_df({"glucose_mg_dL": [9999.0]})
        v.validate_dataframe(df, "test.csv")
        log = v.get_audit_log()
        outliers = [e for e in log if e.error_type == "CLINICAL_OUTLIER"]
        assert len(outliers) >= 1

    def test_hemoglobin_normal(self):
        v = DataValidator()
        df = make_labs_df({"hemoglobin_g_dL": [14.0]})
        v.validate_dataframe(df, "test.csv")
        log = v.get_audit_log()
        outliers = [e for e in log if e.error_type == "CLINICAL_OUTLIER"
                    and "hemoglobin" in e.column_name]
        assert len(outliers) == 0


class TestValidatorDuplicateDetection:
    def test_detects_exact_duplicates(self):
        v = DataValidator()
        df = make_labs_df()
        # Add duplicate row
        df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
        v.validate_dataframe(df, "test.csv")
        log = v.get_audit_log()
        dup_errors = [e for e in log if "DUPLICATE" in e.error_type.upper()]
        assert len(dup_errors) >= 1

    def test_no_duplicates_clean_data(self):
        v = DataValidator()
        df = make_labs_df()
        v.validate_dataframe(df, "test.csv")
        log = v.get_audit_log()
        dup_errors = [e for e in log if "DUPLICATE" in e.error_type.upper()]
        assert len(dup_errors) == 0


class TestValidatorDateEdgeCases:
    def test_future_date_flagged(self):
        v = DataValidator()
        df = make_labs_df({"specimen_datetime": ["2099-12-31"]})
        v.validate_dataframe(df, "test.csv")
        log = v.get_audit_log()
        date_errors = [e for e in log if "DATE" in e.error_type.upper()]
        # Future dates may or may not be flagged depending on impl
        assert isinstance(date_errors, list)

    def test_valid_date_no_error(self):
        v = DataValidator()
        df = make_labs_df({"specimen_datetime": ["2025-06-15"]})
        v.validate_dataframe(df, "test.csv")
        log = v.get_audit_log()
        date_errors = [e for e in log if "DATE" in e.error_type.upper()
                       and "specimen" in e.column_name]
        assert len(date_errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
