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
