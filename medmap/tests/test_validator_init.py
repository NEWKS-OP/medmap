"""Test DataValidator initialization and helpers."""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.validator import DataValidator


class TestDataValidatorInit:
    """Test DataValidator initialization."""

    def test_audit_log_empty(self):
        v = DataValidator()
        assert v.audit_log == []

    def test_quality_scores_empty(self):
        v = DataValidator()
        assert v.quality_scores == {}


class TestValidatorMissing:
    """Test _is_missing detection."""

    def test_none_is_missing(self):
        v = DataValidator()
        assert v._is_missing(None)

    def test_nan_is_missing(self):
        import numpy as np
        v = DataValidator()
        assert v._is_missing(float('nan'))

    def test_empty_string_is_missing(self):
        v = DataValidator()
        assert v._is_missing("")

    def test_na_string_is_missing(self):
        v = DataValidator()
        assert v._is_missing("n/a")

    def test_null_string_is_missing(self):
        v = DataValidator()
        assert v._is_missing("null")

    def test_valid_value_not_missing(self):
        v = DataValidator()
        assert not v._is_missing("hello")

    def test_number_not_missing(self):
        v = DataValidator()
        assert not v._is_missing(42)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
