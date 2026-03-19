"""Tests for config modules: schema_mapping, clinical_rules, gender_mapping, settings."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.schema_mapping import (
    detect_file_type, infer_type_from_filename,
    LABS_MAPPING, ICD10_MAPPING, DEVICE_MOTION_MAPPING,
    DEVICE_1HZ_MAPPING, MEDICATION_MAPPING, NURSING_MAPPING,
    CASE_DATA_MAPPING, EPAC_GERMAN_MAPPING,
    COLUMN_SIGNATURES, PID_PREFIXES,
    DIRTY_LABS_RENAME, DIRTY_ICD10_RENAME,
)
from config.clinical_rules import (
    CLINICAL_RANGES, VALID_LAB_FLAGS, MISSING_VALUE_TOKENS, ANOMALY_RULES,
)
from config.gender_mapping import GENDER_MAP, normalize_gender


class TestDetectFileType:
    def test_detects_labs(self):
        cols = ["case_id", "patient_id", "sodium_mmol_L", "specimen_datetime"]
        assert detect_file_type(cols) == "labs"

    def test_detects_icd10(self):
        cols = ["case_id", "primary_icd10_code", "ward", "patient_id"]
        assert detect_file_type(cols) == "icd10_ops"

    def test_detects_device_motion(self):
        cols = ["patient_id", "timestamp", "movement_index_0_100", "fall_event_0_1"]
        assert detect_file_type(cols) == "device_motion"

    def test_detects_device_1hz(self):
        cols = ["patient_id", "timestamp", "accel_x_m_s2", "device_id"]
        assert detect_file_type(cols) == "device_1hz"

    def test_detects_medication(self):
        cols = ["case_id", "patient_id", "medication_name", "record_type"]
        assert detect_file_type(cols) == "medication"

    def test_detects_nursing(self):
        cols = ["case_id", "patient_id", "shift", "nursing_note_free_text"]
        assert detect_file_type(cols) == "nursing"

    def test_detects_epac_pivot(self):
        cols = ["FallID", "SID", "SID_value"]
        assert detect_file_type(cols) == "epaAC_pivot"

    def test_detects_epac_german(self):
        cols = ["AufnDat", "Körpergröße", "other"]
        assert detect_file_type(cols) == "epaAC_german"

    def test_detects_epac_sap(self):
        cols = ["MANDT", "PATFAL", "EPA0001", "EPA0004"]
        assert detect_file_type(cols) == "epaAC_sap"

    def test_unknown_columns(self):
        cols = ["x", "y", "z"]
        assert detect_file_type(cols) == "unknown"

    def test_alt_required_labs(self):
        cols = ["CaseID", "PID", "Na"]
        assert detect_file_type(cols) == "labs"

    def test_alt_required_medication(self):
        cols = ["case_id", "patient_id", "medication_name", "event_type"]
        assert detect_file_type(cols) == "medication"


class TestInferTypeFromFilename:
    def test_labs(self):
        assert infer_type_from_filename("synth_labs.csv") == "labs"

    def test_icd(self):
        assert infer_type_from_filename("synth_cases_icd10_ops.csv") == "icd10_ops"

    def test_device_1hz(self):
        assert infer_type_from_filename("synth_device_raw_1hz_motion_fall.csv") == "device_1hz"

    def test_device_motion(self):
        assert infer_type_from_filename("synth_device_motion_fall.csv") == "device_motion"

    def test_medication(self):
        assert infer_type_from_filename("clinic_1_medication.csv") == "medication"

    def test_nursing(self):
        assert infer_type_from_filename("clinic_1_nursing.csv") == "nursing"

    def test_epac(self):
        assert infer_type_from_filename("epaAC-Data-3.csv") == "epaAC_german"

    def test_unknown(self):
        assert infer_type_from_filename("random_file.csv") == "unknown"


class TestLabsMapping:
    def test_has_case_id(self):
        assert "case_id" in LABS_MAPPING
        assert LABS_MAPPING["case_id"] == "coCaseId"

    def test_has_patient_id(self):
        assert "patient_id" in LABS_MAPPING
        assert LABS_MAPPING["patient_id"] == "coPatient_id"

    def test_has_sodium(self):
        assert "sodium_mmol_L" in LABS_MAPPING
        assert LABS_MAPPING["sodium_mmol_L"] == "coSodium_mmol_L"

    def test_has_all_flags(self):
        flag_cols = [k for k in LABS_MAPPING if k.endswith("_flag")]
        assert len(flag_cols) >= 10

    def test_has_all_ref_ranges(self):
        ref_cols = [k for k in LABS_MAPPING if "ref_" in k]
        assert len(ref_cols) >= 20


class TestIcd10Mapping:
    def test_has_case_id(self):
        assert ICD10_MAPPING["case_id"] == "coCaseId"

    def test_has_primary_icd10(self):
        assert "primary_icd10_code" in ICD10_MAPPING

    def test_has_ward(self):
        assert "ward" in ICD10_MAPPING

    def test_has_admission_date(self):
        assert "admission_date" in ICD10_MAPPING


class TestDeviceMotionMapping:
    def test_has_timestamp(self):
        assert "timestamp" in DEVICE_MOTION_MAPPING

    def test_has_fall_event(self):
        assert "fall_event_0_1" in DEVICE_MOTION_MAPPING

    def test_has_movement_index(self):
        assert "movement_index_0_100" in DEVICE_MOTION_MAPPING


class TestDevice1HzMapping:
    def test_has_accel_x(self):
        assert "accel_x_m_s2" in DEVICE_1HZ_MAPPING

    def test_has_device_id(self):
        assert "device_id" in DEVICE_1HZ_MAPPING

    def test_has_pressure_zones(self):
        for i in range(1, 5):
            assert f"pressure_zone{i}_0_100" in DEVICE_1HZ_MAPPING


class TestMedicationMapping:
    def test_has_medication_name(self):
        assert "medication_name" in MEDICATION_MAPPING

    def test_has_record_type(self):
        assert "record_type" in MEDICATION_MAPPING

    def test_has_prescriber_role(self):
        assert "prescriber_role" in MEDICATION_MAPPING


class TestNursingMapping:
    def test_has_nursing_note(self):
        assert "nursing_note_free_text" in NURSING_MAPPING

    def test_has_shift(self):
        assert "shift" in NURSING_MAPPING

    def test_note_text_alias(self):
        assert "note_text" in NURSING_MAPPING
        assert NURSING_MAPPING["note_text"] == "coNursing_note_free_text"


class TestEpacGermanMapping:
    def test_has_fallid(self):
        assert "FallID" in EPAC_GERMAN_MAPPING

    def test_has_koerpergroesse(self):
        assert "Körpergröße" in EPAC_GERMAN_MAPPING

    def test_has_bmi(self):
        assert "BMI" in EPAC_GERMAN_MAPPING

    def test_maps_aufndat(self):
        assert EPAC_GERMAN_MAPPING["AufnDat"] == "admission_date"


class TestPidPrefixes:
    def test_labs_prefix(self):
        assert PID_PREFIXES["labs"] == "LAB"

    def test_device_motion_prefix(self):
        assert PID_PREFIXES["device_motion"] == "MOT"

    def test_medication_prefix(self):
        assert PID_PREFIXES["medication"] == "MED"

    def test_nursing_prefix(self):
        assert PID_PREFIXES["nursing"] == "NUR"

    def test_icd_prefix(self):
        assert PID_PREFIXES["icd10_ops"] == "ICD"

    def test_epa_prefix(self):
        assert PID_PREFIXES["epaAC_german"] == "EPA"


class TestClinicalRanges:
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

    def test_glucose_range(self):
        low, high = CLINICAL_RANGES["glucose_mg_dL"]
        assert low == 20
        assert high == 600

    def test_hemoglobin_range(self):
        low, high = CLINICAL_RANGES["hemoglobin_g_dL"]
        assert low == 3
        assert high == 25

    def test_bmi_range(self):
        low, high = CLINICAL_RANGES["bmi"]
        assert low == 10
        assert high == 70

    def test_all_ranges_have_two_values(self):
        for col, (low, high) in CLINICAL_RANGES.items():
            assert low < high, f"{col}: low >= high"


class TestValidLabFlags:
    def test_has_h(self):
        assert "H" in VALID_LAB_FLAGS

    def test_has_l(self):
        assert "L" in VALID_LAB_FLAGS

    def test_has_hh(self):
        assert "HH" in VALID_LAB_FLAGS

    def test_has_ll(self):
        assert "LL" in VALID_LAB_FLAGS

    def test_has_empty(self):
        assert "" in VALID_LAB_FLAGS


class TestMissingValueTokens:
    def test_has_null(self):
        assert "null" in MISSING_VALUE_TOKENS

    def test_has_nan(self):
        assert "nan" in MISSING_VALUE_TOKENS

    def test_has_na(self):
        assert "na" in MISSING_VALUE_TOKENS

    def test_has_missing(self):
        assert "missing" in MISSING_VALUE_TOKENS

    def test_has_none(self):
        assert "none" in MISSING_VALUE_TOKENS

    def test_has_keine(self):
        assert "keine" in MISSING_VALUE_TOKENS


class TestAnomalyRules:
    def test_has_aki_rule(self):
        assert "AKI_PROBABLE" in ANOMALY_RULES

    def test_has_sepsis_rule(self):
        assert "SEPSIS_POSSIBLE" in ANOMALY_RULES

    def test_has_fall_risk_rule(self):
        assert "HIGH_FALL_RISK" in ANOMALY_RULES

    def test_aki_conditions(self):
        rule = ANOMALY_RULES["AKI_PROBABLE"]
        assert "creatinine_mg_dL" in rule["conditions"]
        assert rule["severity"] == "CRITICAL"

    def test_all_rules_have_severity(self):
        for name, rule in ANOMALY_RULES.items():
            assert "severity" in rule, f"{name} missing severity"
            assert "message" in rule, f"{name} missing message"
