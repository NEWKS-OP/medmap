"""Test column signature configuration for file type detection."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.schema_mapping import COLUMN_SIGNATURES


class TestColumnSignatureStructure:
    """Test all column signatures have valid structure."""

    def test_labs_signature_exists(self):
        assert "labs" in COLUMN_SIGNATURES

    def test_icd10_signature_exists(self):
        assert "icd10_ops" in COLUMN_SIGNATURES

    def test_device_motion_signature_exists(self):
        assert "device_motion" in COLUMN_SIGNATURES

    def test_device_1hz_signature_exists(self):
        assert "device_1hz" in COLUMN_SIGNATURES

    def test_medication_signature_exists(self):
        assert "medication" in COLUMN_SIGNATURES

    def test_nursing_signature_exists(self):
        assert "nursing" in COLUMN_SIGNATURES

    def test_epac_pivot_signature_exists(self):
        assert "epaAC_pivot" in COLUMN_SIGNATURES

    def test_epac_sap_signature_exists(self):
        assert "epaAC_sap" in COLUMN_SIGNATURES

    def test_epac_german_signature_exists(self):
        assert "epaAC_german" in COLUMN_SIGNATURES

    def test_all_signatures_count(self):
        assert len(COLUMN_SIGNATURES) >= 9


class TestLabsSignature:
    """Test labs column signature details."""

    def test_has_required_set(self):
        assert "required" in COLUMN_SIGNATURES["labs"]

    def test_required_includes_case_id(self):
        assert "case_id" in COLUMN_SIGNATURES["labs"]["required"]

    def test_required_includes_patient_id(self):
        assert "patient_id" in COLUMN_SIGNATURES["labs"]["required"]

    def test_required_includes_sodium(self):
        assert "sodium_mmol_L" in COLUMN_SIGNATURES["labs"]["required"]

    def test_has_alt_required(self):
        assert "alt_required" in COLUMN_SIGNATURES["labs"]

    def test_has_alt_required_2(self):
        assert "alt_required_2" in COLUMN_SIGNATURES["labs"]


class TestICD10Signature:
    """Test ICD10 column signature."""

    def test_has_required(self):
        assert "required" in COLUMN_SIGNATURES["icd10_ops"]

    def test_requires_icd10_code(self):
        assert "primary_icd10_code" in COLUMN_SIGNATURES["icd10_ops"]["required"]

    def test_requires_ward(self):
        assert "ward" in COLUMN_SIGNATURES["icd10_ops"]["required"]


class TestMedicationSignature:
    """Test medication column signature."""

    def test_has_required(self):
        assert "required" in COLUMN_SIGNATURES["medication"]

    def test_requires_medication_name(self):
        assert "medication_name" in COLUMN_SIGNATURES["medication"]["required"]

    def test_requires_record_type(self):
        assert "record_type" in COLUMN_SIGNATURES["medication"]["required"]


class TestNursingSignature:
    """Test nursing column signature."""

    def test_has_required(self):
        assert "required" in COLUMN_SIGNATURES["nursing"]

    def test_requires_shift(self):
        assert "shift" in COLUMN_SIGNATURES["nursing"]["required"]

    def test_requires_nursing_note(self):
        assert "nursing_note_free_text" in COLUMN_SIGNATURES["nursing"]["required"]


class TestEpaACSignatures:
    """Test epaAC lambda-based signatures."""

    def test_pivot_has_check(self):
        assert "check" in COLUMN_SIGNATURES["epaAC_pivot"]
        assert callable(COLUMN_SIGNATURES["epaAC_pivot"]["check"])

    def test_sap_has_check(self):
        assert "check" in COLUMN_SIGNATURES["epaAC_sap"]
        assert callable(COLUMN_SIGNATURES["epaAC_sap"]["check"])

    def test_german_has_check(self):
        assert "check" in COLUMN_SIGNATURES["epaAC_german"]
        assert callable(COLUMN_SIGNATURES["epaAC_german"]["check"])

    def test_pivot_check_with_valid_cols(self):
        cols = {"SID", "SID_value", "FallID", "other"}
        assert COLUMN_SIGNATURES["epaAC_pivot"]["check"](cols)

    def test_pivot_check_with_invalid_cols(self):
        cols = {"foo", "bar"}
        assert not COLUMN_SIGNATURES["epaAC_pivot"]["check"](cols)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
