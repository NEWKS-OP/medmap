"""Test missing value token configuration."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.clinical_rules import MISSING_VALUE_TOKENS


class TestMissingTokenSet:
    """Verify missing value tokens are correctly defined."""

    def test_null_token(self):
        assert "null" in MISSING_VALUE_TOKENS

    def test_nan_token(self):
        assert "nan" in MISSING_VALUE_TOKENS

    def test_na_token(self):
        assert "na" in MISSING_VALUE_TOKENS

    def test_n_a_token(self):
        assert "n/a" in MISSING_VALUE_TOKENS

    def test_missing_token(self):
        assert "missing" in MISSING_VALUE_TOKENS

    def test_unknown_token(self):
        assert "unknown" in MISSING_VALUE_TOKENS

    def test_keine_token(self):
        assert "keine" in MISSING_VALUE_TOKENS

    def test_none_token(self):
        assert "none" in MISSING_VALUE_TOKENS

    def test_nil_token(self):
        assert "nil" in MISSING_VALUE_TOKENS

    def test_empty_string_token(self):
        assert "" in MISSING_VALUE_TOKENS

    def test_space_token(self):
        assert " " in MISSING_VALUE_TOKENS

    def test_all_tokens_lowercase(self):
        for token in MISSING_VALUE_TOKENS:
            assert token == token.lower(), f"Token '{token}' is not lowercase"

    def test_token_count(self):
        assert len(MISSING_VALUE_TOKENS) >= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
