"""Test lab flag columns and valid flag values."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.clinical_rules import VALID_LAB_FLAGS
from pipeline.cleaner import LAB_FLAG_COLUMNS


class TestValidLabFlags:
    """Test valid lab flag values."""

    def test_high_flag(self):
        assert "H" in VALID_LAB_FLAGS

    def test_low_flag(self):
        assert "L" in VALID_LAB_FLAGS

    def test_critical_high_flag(self):
        assert "HH" in VALID_LAB_FLAGS

    def test_critical_low_flag(self):
        assert "LL" in VALID_LAB_FLAGS

    def test_empty_flag(self):
        assert "" in VALID_LAB_FLAGS

    def test_flag_count(self):
        assert len(VALID_LAB_FLAGS) == 5


class TestLabFlagColumns:
    """Test lab flag column list."""

    def test_sodium_flag(self):
        assert "sodium_flag" in LAB_FLAG_COLUMNS

    def test_potassium_flag(self):
        assert "potassium_flag" in LAB_FLAG_COLUMNS

    def test_creatinine_flag(self):
        assert "creatinine_flag" in LAB_FLAG_COLUMNS

    def test_egfr_flag(self):
        assert "egfr_flag" in LAB_FLAG_COLUMNS

    def test_glucose_flag(self):
        assert "glucose_flag" in LAB_FLAG_COLUMNS

    def test_hb_flag(self):
        assert "hb_flag" in LAB_FLAG_COLUMNS

    def test_wbc_flag(self):
        assert "wbc_flag" in LAB_FLAG_COLUMNS

    def test_platelets_flag(self):
        assert "platelets_flag" in LAB_FLAG_COLUMNS

    def test_crp_flag(self):
        assert "crp_flag" in LAB_FLAG_COLUMNS

    def test_alt_flag(self):
        assert "alt_flag" in LAB_FLAG_COLUMNS

    def test_ast_flag(self):
        assert "ast_flag" in LAB_FLAG_COLUMNS

    def test_bilirubin_flag(self):
        assert "bilirubin_flag" in LAB_FLAG_COLUMNS

    def test_albumin_flag(self):
        assert "albumin_flag" in LAB_FLAG_COLUMNS

    def test_inr_flag(self):
        assert "inr_flag" in LAB_FLAG_COLUMNS

    def test_lactate_flag(self):
        assert "lactate_flag" in LAB_FLAG_COLUMNS

    def test_flag_count(self):
        assert len(LAB_FLAG_COLUMNS) == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
