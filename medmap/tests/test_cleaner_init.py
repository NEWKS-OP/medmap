"""Test DataCleaner initialization and special char pattern."""

import os
import sys
import re
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import DataCleaner, SPECIAL_CHARS_PATTERN, PID_PREFIX_MAP


class TestDataCleanerInit:
    """Test DataCleaner construction."""

    def test_creates_instance(self):
        c = DataCleaner()
        assert c is not None


class TestSpecialCharsPattern:
    """Test special characters regex pattern."""

    def test_matches_umlaut_u(self):
        assert SPECIAL_CHARS_PATTERN.search("ü")

    def test_matches_umlaut_a(self):
        assert SPECIAL_CHARS_PATTERN.search("ä")

    def test_matches_umlaut_o(self):
        assert SPECIAL_CHARS_PATTERN.search("ö")

    def test_matches_eszett(self):
        assert SPECIAL_CHARS_PATTERN.search("ß")

    def test_matches_at_sign(self):
        assert SPECIAL_CHARS_PATTERN.search("@")

    def test_matches_dollar(self):
        assert SPECIAL_CHARS_PATTERN.search("$")

    def test_matches_percent(self):
        assert SPECIAL_CHARS_PATTERN.search("%")

    def test_matches_hash(self):
        assert SPECIAL_CHARS_PATTERN.search("#")

    def test_matches_ampersand(self):
        assert SPECIAL_CHARS_PATTERN.search("&")

    def test_no_match_normal_text(self):
        assert not SPECIAL_CHARS_PATTERN.search("hello123")

    def test_no_match_digits(self):
        assert not SPECIAL_CHARS_PATTERN.search("42")

    def test_no_match_underscore(self):
        assert not SPECIAL_CHARS_PATTERN.search("_")

    def test_no_match_dash(self):
        assert not SPECIAL_CHARS_PATTERN.search("-")

    def test_strips_from_value(self):
        cleaned = SPECIAL_CHARS_PATTERN.sub("", "138ü")
        assert cleaned == "138"

    def test_strips_multiple(self):
        cleaned = SPECIAL_CHARS_PATTERN.sub("", "Na%138@")
        assert cleaned == "Na138"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
