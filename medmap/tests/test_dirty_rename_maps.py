"""Test dirty column rename mappings."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.schema_mapping import (
    DIRTY_LABS_RENAME, DIRTY_ICD10_RENAME,
    DIRTY_1HZ_RENAME, DIRTY_MEDICATION_RENAME,
    DIRTY_NURSING_RENAME,
)


class TestDirtyLabsRename:
    """Test dirty labs column rename map."""

    def test_case_id_mapping(self):
        assert DIRTY_LABS_RENAME["CaseID"] == "case_id"

    def test_pid_mapping(self):
        assert DIRTY_LABS_RENAME["PID"] == "patient_id"

    def test_gender_mapping(self):
        assert DIRTY_LABS_RENAME["Gender"] == "sex"

    def test_age_mapping(self):
        assert DIRTY_LABS_RENAME["Age"] == "age_years"

    def test_sodium_mapping(self):
        assert DIRTY_LABS_RENAME["Na"] == "sodium_mmol_L"

    def test_potassium_mapping(self):
        assert DIRTY_LABS_RENAME["K"] == "potassium_mmol_L"

    def test_creatinine_mapping(self):
        assert DIRTY_LABS_RENAME["Creat"] == "creatinine_mg_dL"

    def test_egfr_mapping(self):
        assert DIRTY_LABS_RENAME["eGFR"] == "egfr_mL_min_1_73m2"

    def test_glucose_mapping(self):
        assert DIRTY_LABS_RENAME["Gluc"] == "glucose_mg_dL"

    def test_hemoglobin_mapping(self):
        assert DIRTY_LABS_RENAME["Hb"] == "hemoglobin_g_dL"

    def test_wbc_mapping(self):
        assert DIRTY_LABS_RENAME["WBC"] == "wbc_10e9_L"

    def test_platelets_mapping(self):
        assert DIRTY_LABS_RENAME["PLT"] == "platelets_10e9_L"

    def test_crp_mapping(self):
        assert DIRTY_LABS_RENAME["CRP"] == "crp_mg_L"

    def test_alt_mapping(self):
        assert DIRTY_LABS_RENAME["ALT"] == "alt_U_L"

    def test_ast_mapping(self):
        assert DIRTY_LABS_RENAME["AST"] == "ast_U_L"

    def test_bilirubin_mapping(self):
        assert DIRTY_LABS_RENAME["Bili"] == "bilirubin_mg_dL"

    def test_albumin_mapping(self):
        assert DIRTY_LABS_RENAME["Alb"] == "albumin_g_dL"

    def test_inr_mapping(self):
        assert DIRTY_LABS_RENAME["INR"] == "inr"

    def test_lactate_mapping(self):
        assert DIRTY_LABS_RENAME["Lact"] == "lactate_mmol_L"


class TestDirtyICD10Rename:
    """Test dirty ICD10 column rename map."""

    def test_case_id(self):
        assert DIRTY_ICD10_RENAME["CaseID"] == "case_id"

    def test_patient_id(self):
        assert DIRTY_ICD10_RENAME["PatientID"] == "patient_id"

    def test_station_to_ward(self):
        assert DIRTY_ICD10_RENAME["Station"] == "ward"

    def test_aufnahmedatum(self):
        assert DIRTY_ICD10_RENAME["Aufnahmedatum"] == "admission_date"

    def test_entlassungsdatum(self):
        assert DIRTY_ICD10_RENAME["Entlassungsdatum"] == "discharge_date"

    def test_icd10_haupt(self):
        assert DIRTY_ICD10_RENAME["ICD10_Haupt"] == "primary_icd10_code"

    def test_icd10_haupt_bezeichnung(self):
        assert DIRTY_ICD10_RENAME["ICD10_Haupt_Bezeichnung"] == "primary_icd10_description_en"


class TestDirtyNursingRename:
    """Test dirty nursing column rename map."""

    def test_exists(self):
        assert isinstance(DIRTY_NURSING_RENAME, dict)

    def test_has_entries(self):
        assert len(DIRTY_NURSING_RENAME) > 0


class TestDirtyMedicationRename:
    """Test dirty medication column rename map."""

    def test_exists(self):
        assert isinstance(DIRTY_MEDICATION_RENAME, dict)

    def test_has_entries(self):
        assert len(DIRTY_MEDICATION_RENAME) > 0


class TestDirty1HzRename:
    """Test dirty 1Hz column rename map."""

    def test_patient_id(self):
        assert DIRTY_1HZ_RENAME["PatientID"] == "patient_id"

    def test_device_id(self):
        assert DIRTY_1HZ_RENAME["DeviceID"] == "device_id"

    def test_timestamp(self):
        assert DIRTY_1HZ_RENAME["Timestamp"] == "timestamp"

    def test_accel_x(self):
        assert DIRTY_1HZ_RENAME["AccelX"] == "accel_x_m_s2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
