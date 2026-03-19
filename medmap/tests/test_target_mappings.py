"""Test target SQL column mapping configurations."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.schema_mapping import (
    LABS_MAPPING, ICD10_MAPPING, DEVICE_MOTION_MAPPING,
    MEDICATION_MAPPING, NURSING_MAPPING, CASE_DATA_MAPPING,
)


class TestLabsMapping:
    """Test labs source->target mapping."""

    def test_case_id_maps_to_coCaseId(self):
        assert LABS_MAPPING["case_id"] == "coCaseId"

    def test_sodium_maps_correctly(self):
        assert LABS_MAPPING["sodium_mmol_L"] == "coSodium_mmol_L"

    def test_potassium_maps_correctly(self):
        assert LABS_MAPPING["potassium_mmol_L"] == "coPotassium_mmol_L"

    def test_creatinine_maps_correctly(self):
        assert LABS_MAPPING["creatinine_mg_dL"] == "coCreatinine_mg_dL"

    def test_all_targets_start_with_co(self):
        for src, tgt in LABS_MAPPING.items():
            assert tgt.startswith("co"), f"{src} -> {tgt} doesn't start with 'co'"

    def test_mapping_count(self):
        assert len(LABS_MAPPING) >= 50


class TestICD10Mapping:
    """Test ICD10 source->target mapping."""

    def test_case_id_maps(self):
        assert ICD10_MAPPING["case_id"] == "coCaseId"

    def test_ward_maps(self):
        assert ICD10_MAPPING["ward"] == "coWard"

    def test_admission_date_maps(self):
        assert ICD10_MAPPING["admission_date"] == "coAdmission_date"

    def test_primary_icd10_maps(self):
        assert ICD10_MAPPING["primary_icd10_code"] == "coPrimary_icd10_code"

    def test_all_targets_start_with_co(self):
        for src, tgt in ICD10_MAPPING.items():
            assert tgt.startswith("co"), f"{src} -> {tgt} doesn't start with 'co'"


class TestDeviceMotionMapping:
    """Test device motion mapping."""

    def test_timestamp_maps(self):
        assert DEVICE_MOTION_MAPPING["timestamp"] == "coTimestamp"

    def test_movement_index_maps(self):
        assert DEVICE_MOTION_MAPPING["movement_index_0_100"] == "coMovement_index_0_100"

    def test_fall_event_maps(self):
        assert DEVICE_MOTION_MAPPING["fall_event_0_1"] == "coFall_event_0_1"


class TestMedicationMapping:
    """Test medication mapping."""

    def test_case_id_maps(self):
        assert MEDICATION_MAPPING["case_id"] == "coCaseId"

    def test_medication_name_maps(self):
        assert MEDICATION_MAPPING["medication_name"] == "coMedication_name"


class TestNursingMapping:
    """Test nursing mapping."""

    def test_case_id_maps(self):
        assert NURSING_MAPPING["case_id"] == "coCaseId"

    def test_shift_maps(self):
        assert NURSING_MAPPING["shift"] == "coShift"

    def test_nursing_note_maps(self):
        assert "coNursing_note_free_text" in NURSING_MAPPING.values()


class TestCaseDataMapping:
    """Test case data mapping."""

    def test_has_mappings(self):
        assert len(CASE_DATA_MAPPING) > 0

    def test_all_targets_start_with_co(self):
        for src, tgt in CASE_DATA_MAPPING.items():
            assert tgt.startswith("co"), f"{src} -> {tgt} doesn't start with 'co'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
