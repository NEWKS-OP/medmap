"""Test gender mapping configuration and normalization."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.gender_mapping import normalize_gender, GENDER_MAP


class TestGenderMapKeys:
    """Test all gender map entries exist."""

    def test_male_uppercase(self):
        assert GENDER_MAP["M"] == "M"

    def test_male_lowercase(self):
        assert GENDER_MAP["m"] == "M"

    def test_male_english(self):
        assert GENDER_MAP["male"] == "M"

    def test_male_german(self):
        assert GENDER_MAP["männlich"] == "M"

    def test_female_uppercase(self):
        assert GENDER_MAP["F"] == "F"

    def test_female_lowercase(self):
        assert GENDER_MAP["f"] == "F"

    def test_female_english(self):
        assert GENDER_MAP["female"] == "F"

    def test_female_german(self):
        assert GENDER_MAP["weiblich"] == "F"

    def test_na_values(self):
        assert GENDER_MAP["N/A"] is None
        assert GENDER_MAP["n/a"] is None
        assert GENDER_MAP["na"] is None
        assert GENDER_MAP["unknown"] is None
        assert GENDER_MAP["keine"] is None


class TestNormalizeGender:
    """Test normalize_gender function."""

    def test_none_input(self):
        assert normalize_gender(None) is None

    def test_male_variants(self):
        assert normalize_gender("M") == "M"
        assert normalize_gender("m") == "M"
        assert normalize_gender("male") == "M"
        assert normalize_gender("männlich") == "M"

    def test_female_variants(self):
        assert normalize_gender("F") == "F"
        assert normalize_gender("f") == "F"
        assert normalize_gender("female") == "F"
        assert normalize_gender("weiblich") == "F"

    def test_whitespace_stripped(self):
        assert normalize_gender(" M ") == "M"
        assert normalize_gender(" F ") == "F"

    def test_unknown_returns_none(self):
        result = normalize_gender("xyz_invalid")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
