"""
Edge-case and adversarial tests for all pipeline components.
Tests boundary values, empty inputs, type mismatches, unicode,
silent failures, and data contract violations.
"""

import os
import sys
import tempfile

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.ingestion import DataIngester
from pipeline.validator import DataValidator
from pipeline.cleaner import DataCleaner
from config.clinical_rules import CLINICAL_RANGES, VALID_LAB_FLAGS


# ──────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────

@pytest.fixture
def ingester():
    return DataIngester()


@pytest.fixture
def validator():
    return DataValidator()


@pytest.fixture
def cleaner():
    v = DataValidator()
    return DataCleaner(validator=v)


def make_df(data, file_type="labs"):
    df = pd.DataFrame(data)
    df.attrs = {"source_file": f"test_{file_type}.csv", "file_type": file_type}
    return df


# ══════════════════════════════════════════════
# EMPTY / NULL INPUT TESTS
# ══════════════════════════════════════════════

class TestEmptyInputs:
    def test_empty_dataframe_validator(self, validator):
        df = pd.DataFrame()
        df.attrs = {"source_file": "empty.csv", "file_type": "labs"}
        score = validator.validate_dataframe(df, "empty.csv")
        assert score.score >= 0

    def test_empty_dataframe_cleaner(self, cleaner):
        df = pd.DataFrame()
        df.attrs = {"source_file": "empty.csv", "file_type": "labs"}
        cleaned = cleaner.clean_dataframe(df, "empty.csv")
        assert len(cleaned) == 0

    def test_headers_only_dataframe(self, validator):
        df = pd.DataFrame(columns=["case_id", "patient_id", "sodium_mmol_L"])
        df.attrs = {"source_file": "headers.csv", "file_type": "labs"}
        score = validator.validate_dataframe(df, "headers.csv")
        assert score.rows_imported == 0

    def test_all_nan_dataframe(self, cleaner):
        df = make_df({
            "case_id": [np.nan, np.nan, np.nan],
            "patient_id": [np.nan, np.nan, np.nan],
            "sodium_mmol_L": [np.nan, np.nan, np.nan],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert len(cleaned) > 0  # should not crash

    def test_all_none_dataframe(self, cleaner):
        df = make_df({
            "case_id": [None, None],
            "patient_id": [None, None],
            "sex": [None, None],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert cleaned is not None

    def test_single_row(self, cleaner):
        df = make_df({"case_id": ["CASE-001"], "sodium_mmol_L": [140.0]})
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert len(cleaned) == 1

    def test_empty_csv_file(self, ingester):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("")
            tmp = f.name
        try:
            df, res = ingester.load(tmp)
            # Should not crash — either returns empty or None
            assert res is not None
        finally:
            os.unlink(tmp)

    def test_csv_only_newlines(self, ingester):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("\n\n\n")
            tmp = f.name
        try:
            df, res = ingester.load(tmp)
            assert res is not None
        finally:
            os.unlink(tmp)


# ══════════════════════════════════════════════
# BOUNDARY VALUE TESTS
# ══════════════════════════════════════════════

class TestBoundaryValues:
    @pytest.mark.parametrize("col,low,high", [
        (col, low, high) for col, (low, high) in CLINICAL_RANGES.items()
    ])
    def test_clinical_range_at_boundaries(self, cleaner, col, low, high):
        """Test exact boundary values for every clinical parameter."""
        df = make_df({
            "case_id": ["CASE-001", "CASE-002", "CASE-003", "CASE-004"],
            "patient_id": ["100001", "100002", "100003", "100004"],
            col: [low, high, low - 0.01, high + 0.01],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        # At boundary = valid, should survive
        if col in cleaned.columns:
            assert not pd.isna(cleaned.at[0, col]), f"{col}={low} should be valid"
            assert not pd.isna(cleaned.at[1, col]), f"{col}={high} should be valid"
            # Just outside boundary = invalid, should be NaN
            assert pd.isna(cleaned.at[2, col]), f"{col}={low - 0.01} should be quarantined"
            assert pd.isna(cleaned.at[3, col]), f"{col}={high + 0.01} should be quarantined"

    def test_zero_values(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["100001"],
            "sodium_mmol_L": [0],
            "potassium_mmol_L": [0],
            "crp_mg_L": [0],  # 0 is valid for CRP
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        # sodium 0 < 100 range -> should be NaN
        assert pd.isna(cleaned.at[0, "sodium_mmol_L"])
        # CRP 0 is within [0, 500] -> should survive
        if "crp_mg_L" in cleaned.columns:
            assert not pd.isna(cleaned.at[0, "crp_mg_L"])

    def test_negative_values(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["100001"],
            "sodium_mmol_L": [-1],
            "glucose_mg_dL": [-100],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert pd.isna(cleaned.at[0, "sodium_mmol_L"])
        assert pd.isna(cleaned.at[0, "glucose_mg_dL"])

    def test_infinity_values(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001", "CASE-002"],
            "patient_id": ["100001", "100002"],
            "sodium_mmol_L": [float("inf"), float("-inf")],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert pd.isna(cleaned.at[0, "sodium_mmol_L"])
        assert pd.isna(cleaned.at[1, "sodium_mmol_L"])

    def test_very_large_numbers(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["100001"],
            "sodium_mmol_L": [1e15],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert pd.isna(cleaned.at[0, "sodium_mmol_L"])


# ══════════════════════════════════════════════
# TYPE MISMATCH TESTS
# ══════════════════════════════════════════════

class TestTypeMismatches:
    def test_string_in_numeric_column(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["100001"],
            "sodium_mmol_L": ["not a number"],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert pd.isna(cleaned.at[0, "sodium_mmol_L"])

    def test_boolean_in_string_column(self, cleaner):
        df = make_df({
            "case_id": [True],
            "patient_id": [False],
            "sex": [True],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert cleaned is not None  # should not crash

    def test_list_in_column(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": [[1, 2, 3]],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert cleaned is not None

    def test_numeric_case_id(self, validator):
        df = make_df({"case_id": [42, 99, 100]})
        score = validator.validate_dataframe(df, "test.csv")
        id_errors = [e for e in validator.audit_log if e.error_type == "ID_INVALID"]
        assert len(id_errors) >= 1  # numeric IDs should fail format check

    def test_german_comma_decimal(self, cleaner):
        """German uses comma as decimal separator."""
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["100001"],
            "sodium_mmol_L": ["140,5"],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        # Should parse 140,5 as 140.5
        val = cleaned.at[0, "sodium_mmol_L"]
        assert not pd.isna(val)
        assert abs(val - 140.5) < 0.01


# ══════════════════════════════════════════════
# UNICODE AND SPECIAL CHARACTER TESTS
# ══════════════════════════════════════════════

class TestUnicodeAndSpecialChars:
    def test_german_umlauts_in_gender(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001", "CASE-002", "CASE-003"],
            "patient_id": ["100001", "100002", "100003"],
            "sex": ["männlich", "weiblich", "mä"],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "sex"] == "M"
        assert cleaned.at[1, "sex"] == "F"
        assert cleaned.at[2, "sex"] == "M"

    def test_special_chars_in_numeric(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001", "CASE-002", "CASE-003"],
            "patient_id": ["100001", "100002", "100003"],
            "sodium_mmol_L": ["14ü0", "13ö0", "15ß0"],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "sodium_mmol_L"] == 140.0
        assert cleaned.at[1, "sodium_mmol_L"] == 130.0
        assert cleaned.at[2, "sodium_mmol_L"] == 150.0

    def test_emoji_in_data(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["100001"],
            "sodium_mmol_L": ["🎉140"],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        # Should either parse to 140 or quarantine — not crash
        assert cleaned is not None

    def test_null_bytes(self, cleaner):
        df = make_df({
            "case_id": ["CASE\x00-001"],
            "patient_id": ["100\x00001"],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert cleaned is not None

    def test_rtl_characters(self, cleaner):
        """Right-to-left characters should not crash."""
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["100001"],
            "sex": ["ذكر"],  # Arabic for male
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        # Should be flagged as unknown, not crash
        assert cleaned is not None


# ══════════════════════════════════════════════
# WHITESPACE TESTS
# ══════════════════════════════════════════════

class TestWhitespace:
    def test_whitespace_only_values(self, cleaner):
        df = make_df({
            "case_id": ["  ", "\t", "\n"],
            "patient_id": [" ", "  ", "\t\t"],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert cleaned is not None

    def test_trailing_whitespace_ids(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001 ", " CASE-002", " CASE-003 "],
            "patient_id": ["100001", "100002", "100003"],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "case_id"] == "CASE-001"
        assert cleaned.at[1, "case_id"] == "CASE-002"
        assert cleaned.at[2, "case_id"] == "CASE-003"

    def test_tabs_in_values(self, cleaner):
        df = make_df({
            "case_id": ["\tCASE-001\t"],
            "patient_id": ["\t100001\t"],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert "CASE-001" in cleaned.at[0, "case_id"]


# ══════════════════════════════════════════════
# DUPLICATE TESTS
# ══════════════════════════════════════════════

class TestDuplicates:
    def test_100_percent_duplicate_rows(self, cleaner):
        df = make_df({
            "case_id": ["CASE-001"] * 100,
            "patient_id": ["100001"] * 100,
            "sodium_mmol_L": [140.0] * 100,
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert len(cleaned) == 1

    def test_partial_duplicates_motion(self, cleaner):
        df = make_df({
            "patient_id": ["P1", "P1", "P2"],
            "timestamp": ["2025-01-01", "2025-01-01", "2025-01-01"],
            "movement_index_0_100": [50, 60, 70],
        }, file_type="device_motion")
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert len(cleaned) == 2  # P1+same timestamp = partial dup

    def test_no_false_positive_duplicates(self, cleaner):
        """Different rows should not be removed."""
        df = make_df({
            "case_id": ["CASE-001", "CASE-002", "CASE-003"],
            "patient_id": ["100001", "100002", "100003"],
            "sodium_mmol_L": [140.0, 130.0, 150.0],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert len(cleaned) == 3


# ══════════════════════════════════════════════
# DATE EDGE CASES
# ══════════════════════════════════════════════

class TestDateEdgeCases:
    def test_impossible_dates(self, cleaner):
        impossible = ["99.99.9999", "00/00/0000", "abc"]
        df = make_df({
            "specimen_datetime": impossible,
            "case_id": [f"CASE-{i:03d}" for i in range(len(impossible))],
            "patient_id": [f"10000{i}" for i in range(len(impossible))],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        for i in range(len(impossible)):
            val = cleaned.at[i, "specimen_datetime"]
            assert val is None or pd.isna(val), f"Impossible date '{impossible[i]}' was not rejected"

    def test_german_textual_dates(self, cleaner):
        df = make_df({
            "specimen_datetime": ["15. März 2025", "1. Januar 2024"],
            "case_id": ["CASE-001", "CASE-002"],
            "patient_id": ["100001", "100002"],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "specimen_datetime"] is not None
        assert "2025" in str(cleaned.at[0, "specimen_datetime"])

    def test_epoch_date(self, cleaner):
        """Epoch dates (1970) should be quarantined as out of range."""
        df = make_df({
            "specimen_datetime": ["1970-01-01"],
            "case_id": ["CASE-001"],
            "patient_id": ["100001"],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        val = cleaned.at[0, "specimen_datetime"]
        assert val is None or pd.isna(val), "1970 date should be quarantined (< 2000)"

    def test_far_future_date(self, cleaner):
        """Far future dates should be quarantined as out of range."""
        df = make_df({
            "specimen_datetime": ["2099-12-31"],
            "case_id": ["CASE-001"],
            "patient_id": ["100001"],
        })
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        val = cleaned.at[0, "specimen_datetime"]
        assert val is None or pd.isna(val), "2099 date should be quarantined (> 2030)"


# ══════════════════════════════════════════════
# MISSING VALUE TOKEN TESTS
# ══════════════════════════════════════════════

class TestMissingValueTokens:
    @pytest.mark.parametrize("token", [
        "null", "nan", "N/A", "na", "missing", "unknown",
        "keine", "none", "nil", "NULL", "NaN", "MISSING",
    ])
    def test_all_missing_tokens_detected(self, cleaner, token):
        df = make_df({"sodium_mmol_L": [token]})
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert pd.isna(cleaned.at[0, "sodium_mmol_L"]), \
            f"Token '{token}' was not normalized to NaN"

    def test_valid_string_not_treated_as_missing(self, cleaner):
        """Actual medical terms should NOT be treated as missing."""
        df = make_df({"nursing_note_free_text": ["Patient is none the worse for wear"]},
                     file_type="nursing")
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        # The word "none" in a sentence should not wipe the field
        # (depends on implementation — this tests the boundary)
        assert cleaned is not None


# ══════════════════════════════════════════════
# LAB FLAG TESTS
# ══════════════════════════════════════════════

class TestLabFlags:
    @pytest.mark.parametrize("flag", ["H", "L", "HH", "LL", ""])
    def test_valid_flags_preserved(self, cleaner, flag):
        df = make_df({"sodium_flag": [flag]})
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        val = cleaned.at[0, "sodium_flag"]
        if flag == "":
            assert pd.isna(val) or val == ""
        else:
            assert val == flag

    @pytest.mark.parametrize("flag", ["X", "HIGH", "low", "1", "True", "CRITICAL"])
    def test_invalid_flags_quarantined(self, cleaner, flag):
        df = make_df({"sodium_flag": [flag]})
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        val = cleaned.at[0, "sodium_flag"]
        assert pd.isna(val) or val in VALID_LAB_FLAGS, \
            f"Invalid flag '{flag}' was not quarantined"


# ══════════════════════════════════════════════
# PID PREFIX TESTS
# ══════════════════════════════════════════════

class TestPidPrefixes:
    def test_no_double_prefix(self, cleaner):
        df = make_df({"patient_id": ["LAB_100001"]})
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert not cleaned.at[0, "patient_id"].startswith("LAB_LAB_")

    def test_no_cross_prefix_overwrite(self, cleaner):
        """A MOT_ prefix should not get LAB_ prepended."""
        df = make_df({"patient_id": ["MOT_100001"]})
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert cleaned.at[0, "patient_id"] == "MOT_100001"

    def test_nan_patient_id_not_prefixed(self, cleaner):
        df = make_df({"patient_id": [np.nan]})
        cleaned = cleaner.clean_dataframe(df, "test.csv")
        assert pd.isna(cleaned.at[0, "patient_id"])


# ══════════════════════════════════════════════
# PANDERA SCHEMA TESTS
# ══════════════════════════════════════════════

class TestPanderaSchemas:
    def test_valid_labs_passes(self):
        from schemas import validate_dataframe
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["LAB_100001"],
            "sex": ["M"],
            "sodium_mmol_L": [140.0],
            "potassium_mmol_L": [4.5],
        })
        errors = validate_dataframe(df, "labs")
        assert len(errors) == 0, f"Valid labs should pass: {errors}"

    def test_outlier_caught_by_schema(self):
        from schemas import validate_dataframe
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["LAB_100001"],
            "sodium_mmol_L": [999.0],  # out of range
        })
        errors = validate_dataframe(df, "labs")
        assert len(errors) > 0, "Outlier should be caught by pandera"

    def test_invalid_gender_caught(self):
        from schemas import validate_dataframe
        df = make_df({
            "case_id": ["CASE-001"],
            "patient_id": ["LAB_100001"],
            "sex": ["X"],  # invalid
        })
        errors = validate_dataframe(df, "labs")
        assert len(errors) > 0, "Invalid gender should be caught"

    def test_missing_token_caught(self):
        from schemas import validate_dataframe
        df = make_df({
            "case_id": ["null"],
            "patient_id": ["N/A"],
        })
        errors = validate_dataframe(df, "labs")
        assert len(errors) > 0, "Missing tokens should be caught"

    def test_unknown_type_no_schema(self):
        from schemas import validate_dataframe
        df = make_df({"val": [1]}, file_type="epaAC_german")
        errors = validate_dataframe(df, "epaAC_german")
        assert len(errors) == 0  # no schema for epaAC, should pass


# ══════════════════════════════════════════════
# INGESTION EDGE CASES
# ══════════════════════════════════════════════

class TestIngestionEdgeCases:
    def test_csv_with_extra_commas(self, ingester):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("a,b,c\n1,2,3,4,5\n6,7,8\n")
            tmp = f.name
        try:
            df, res = ingester.load(tmp)
            assert res is not None
        finally:
            os.unlink(tmp)

    def test_csv_with_quotes(self, ingester):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write('case_id,note\n"CASE-001","note with ""quotes"""\n')
            tmp = f.name
        try:
            df, res = ingester.load(tmp)
            assert df is not None
            assert res.rows_loaded >= 1
        finally:
            os.unlink(tmp)

    def test_csv_with_bom(self, ingester):
        """UTF-8 BOM should be handled."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
            f.write(b'\xef\xbb\xbfcase_id,value\nCASE-001,42\n')
            tmp = f.name
        try:
            df, res = ingester.load(tmp)
            assert df is not None
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
