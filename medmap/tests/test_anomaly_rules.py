"""Test anomaly rule configuration."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.clinical_rules import ANOMALY_RULES


class TestAnomalyRuleStructure:
    """Verify anomaly rules have required fields."""

    def test_aki_rule_exists(self):
        assert "AKI_PROBABLE" in ANOMALY_RULES

    def test_sepsis_rule_exists(self):
        assert "SEPSIS_POSSIBLE" in ANOMALY_RULES

    def test_fall_risk_rule_exists(self):
        assert "HIGH_FALL_RISK" in ANOMALY_RULES

    def test_dangerous_med_rule_exists(self):
        assert "DANGEROUS_MED_AKI" in ANOMALY_RULES

    def test_multi_source_rule_exists(self):
        assert "MULTI_SOURCE_DETERIORATION" in ANOMALY_RULES

    def test_anticoag_rule_exists(self):
        assert "ANTICOAG_INR_ABNORMAL" in ANOMALY_RULES

    def test_all_rules_have_severity(self):
        for name, rule in ANOMALY_RULES.items():
            assert "severity" in rule, f"{name} missing severity"

    def test_all_rules_have_message(self):
        for name, rule in ANOMALY_RULES.items():
            assert "message" in rule, f"{name} missing message"

    def test_all_rules_have_conditions(self):
        for name, rule in ANOMALY_RULES.items():
            assert "conditions" in rule, f"{name} missing conditions"

    def test_severity_values_valid(self):
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        for name, rule in ANOMALY_RULES.items():
            assert rule["severity"] in valid, f"{name} has invalid severity {rule['severity']}"


class TestAKIRule:
    """Test AKI rule conditions."""

    def test_creatinine_threshold(self):
        cond = ANOMALY_RULES["AKI_PROBABLE"]["conditions"]
        assert "creatinine_mg_dL" in cond
        op, val = cond["creatinine_mg_dL"]
        assert op == ">"
        assert val == 3.0

    def test_egfr_threshold(self):
        cond = ANOMALY_RULES["AKI_PROBABLE"]["conditions"]
        assert "egfr_mL_min_1_73m2" in cond
        op, val = cond["egfr_mL_min_1_73m2"]
        assert op == "<"
        assert val == 20

    def test_potassium_threshold(self):
        cond = ANOMALY_RULES["AKI_PROBABLE"]["conditions"]
        assert "potassium_mmol_L" in cond
        op, val = cond["potassium_mmol_L"]
        assert op == ">"
        assert val == 5.5


class TestSepsisRule:
    """Test sepsis rule conditions."""

    def test_crp_threshold(self):
        cond = ANOMALY_RULES["SEPSIS_POSSIBLE"]["conditions"]
        assert "crp_mg_L" in cond
        op, val = cond["crp_mg_L"]
        assert op == ">"
        assert val == 100

    def test_lactate_threshold(self):
        cond = ANOMALY_RULES["SEPSIS_POSSIBLE"]["conditions"]
        assert "lactate_mmol_L" in cond
        op, val = cond["lactate_mmol_L"]
        assert op == ">"
        assert val == 2.0

    def test_wbc_threshold(self):
        cond = ANOMALY_RULES["SEPSIS_POSSIBLE"]["conditions"]
        assert "wbc_10e9_L" in cond


class TestDangerousMedRule:
    """Test dangerous medication rule."""

    def test_has_med_names(self):
        rule = ANOMALY_RULES["DANGEROUS_MED_AKI"]
        assert "med_names" in rule
        assert len(rule["med_names"]) > 0

    def test_metformin_listed(self):
        meds = ANOMALY_RULES["DANGEROUS_MED_AKI"]["med_names"]
        assert "metformin" in meds

    def test_ibuprofen_listed(self):
        meds = ANOMALY_RULES["DANGEROUS_MED_AKI"]["med_names"]
        assert "ibuprofen" in meds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
