"""Test clinical range configuration values."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.clinical_rules import CLINICAL_RANGES


class TestClinicalRangesBounds:
    """Verify all clinical ranges have valid min < max bounds."""

    def test_sodium_range(self):
        low, high = CLINICAL_RANGES["sodium_mmol_L"]
        assert low == 100
        assert high == 165

    def test_potassium_range(self):
        low, high = CLINICAL_RANGES["potassium_mmol_L"]
        assert low == 2.0
        assert high == 7.5

    def test_creatinine_range(self):
        low, high = CLINICAL_RANGES["creatinine_mg_dL"]
        assert low == 0.3
        assert high == 15.0

    def test_egfr_range(self):
        low, high = CLINICAL_RANGES["egfr_mL_min_1_73m2"]
        assert low == 1
        assert high == 120

    def test_glucose_range(self):
        low, high = CLINICAL_RANGES["glucose_mg_dL"]
        assert low == 20
        assert high == 600

    def test_hemoglobin_range(self):
        low, high = CLINICAL_RANGES["hemoglobin_g_dL"]
        assert low == 3
        assert high == 25

    def test_wbc_range(self):
        low, high = CLINICAL_RANGES["wbc_10e9_L"]
        assert low == 0.1
        assert high == 100

    def test_platelets_range(self):
        low, high = CLINICAL_RANGES["platelets_10e9_L"]
        assert low == 10
        assert high == 1000

    def test_crp_range(self):
        low, high = CLINICAL_RANGES["crp_mg_L"]
        assert low == 0
        assert high == 500

    def test_alt_range(self):
        low, high = CLINICAL_RANGES["alt_U_L"]
        assert low == 1
        assert high == 5000

    def test_ast_range(self):
        low, high = CLINICAL_RANGES["ast_U_L"]
        assert low == 1
        assert high == 5000

    def test_bilirubin_range(self):
        low, high = CLINICAL_RANGES["bilirubin_mg_dL"]
        assert low == 0
        assert high == 30

    def test_albumin_range(self):
        low, high = CLINICAL_RANGES["albumin_g_dL"]
        assert low == 1
        assert high == 6

    def test_inr_range(self):
        low, high = CLINICAL_RANGES["inr"]
        assert low == 0.5
        assert high == 10

    def test_lactate_range(self):
        low, high = CLINICAL_RANGES["lactate_mmol_L"]
        assert low == 0.3
        assert high == 20

    def test_bmi_range(self):
        low, high = CLINICAL_RANGES["bmi"]
        assert low == 10
        assert high == 70

    def test_all_ranges_have_low_less_than_high(self):
        for col, (low, high) in CLINICAL_RANGES.items():
            assert low < high, f"{col}: {low} >= {high}"

    def test_all_ranges_are_numeric(self):
        for col, (low, high) in CLINICAL_RANGES.items():
            assert isinstance(low, (int, float)), f"{col} low is {type(low)}"
            assert isinstance(high, (int, float)), f"{col} high is {type(high)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
