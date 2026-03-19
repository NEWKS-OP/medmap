"""Test mapper output matches target schema expectations."""

import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.mapper import DataMapper


class TestLabsMapping:
    """Test labs data mapping to tbImportLabsData."""

    def setup_method(self):
        self.mapper = DataMapper()

    def test_labs_basic_mapping(self):
        df = pd.DataFrame({
            "case_id": ["CASE-0001", "CASE-0002"],
            "patient_id": ["LAB_100001", "LAB_100002"],
            "sex": ["M", "F"],
            "age_years": [65, 72],
            "specimen_datetime": ["2024-01-15", "2024-01-16"],
            "sodium_mmol_L": [138, 142],
            "sodium_flag": [None, "H"],
            "sodium_ref_low": [136, 136],
            "sodium_ref_high": [145, 145],
        })
        df.attrs["file_type"] = "labs"
        df.attrs["source_file"] = "test_labs.csv"
        result = self.mapper.map_labs([df])
        assert result is not None
        assert len(result) == 2
        assert "coCaseId" in result.columns

    def test_labs_empty_input(self):
        result = self.mapper.map_labs([])
        assert result.empty


class TestICD10Mapping:
    """Test ICD10 data mapping."""

    def setup_method(self):
        self.mapper = DataMapper()

    def test_icd10_basic(self):
        df = pd.DataFrame({
            "case_id": ["CASE-0001"],
            "patient_id": ["ICD_100001"],
            "ward": ["Cardiology"],
            "admission_date": ["2024-01-15"],
            "discharge_date": ["2024-01-20"],
            "primary_icd10_code": ["I50.0"],
            "primary_icd10_description_en": ["Heart failure"],
        })
        df.attrs["file_type"] = "icd10_ops"
        df.attrs["source_file"] = "test_icd.csv"
        result = self.mapper.map_icd10([df])
        assert result is not None
        assert "coCaseId" in result.columns
        assert "coAdmission_date" in result.columns

    def test_icd10_empty(self):
        result = self.mapper.map_icd10([])
        assert result.empty


class TestNursingMapping:
    """Test nursing data mapping."""

    def setup_method(self):
        self.mapper = DataMapper()

    def test_nursing_basic(self):
        df = pd.DataFrame({
            "case_id": ["CASE-0001"],
            "patient_id": ["NUR_100001"],
            "ward": ["Geriatrics"],
            "report_date": ["2024-01-15"],
            "shift": ["Early"],
            "nursing_note_free_text": ["Patient resting well"],
        })
        df.attrs["file_type"] = "nursing"
        df.attrs["source_file"] = "test_nursing.csv"
        result = self.mapper.map_nursing([df])
        assert result is not None
        assert "coCaseId" in result.columns
        assert "coShift" in result.columns

    def test_nursing_empty(self):
        result = self.mapper.map_nursing([])
        assert result.empty


class TestMedicationMapping:
    """Test medication data mapping."""

    def setup_method(self):
        self.mapper = DataMapper()

    def test_medication_basic(self):
        df = pd.DataFrame({
            "case_id": ["CASE-0001"],
            "patient_id": ["MED_100001"],
            "record_type": ["ORDER"],
            "medication_name": ["Aspirin"],
            "medication_code_atc": ["B01AC06"],
            "dose": ["100mg"],
        })
        df.attrs["file_type"] = "medication"
        df.attrs["source_file"] = "test_med.csv"
        result = self.mapper.map_medication([df])
        assert result is not None
        assert "coCaseId" in result.columns

    def test_medication_empty(self):
        result = self.mapper.map_medication([])
        assert result.empty


class TestDeviceMotionMapping:
    """Test device motion data mapping."""

    def setup_method(self):
        self.mapper = DataMapper()

    def test_device_motion_basic(self):
        df = pd.DataFrame({
            "patient_id": ["MOT_100001"],
            "timestamp": ["2024-01-15 10:00:00"],
            "movement_index_0_100": [75],
            "micro_movements_count": [120],
            "bed_exit_detected_0_1": [0],
            "fall_event_0_1": [0],
            "impact_magnitude_g": [0.5],
            "post_fall_immobility_minutes": [0],
        })
        df.attrs["file_type"] = "device_motion"
        df.attrs["source_file"] = "test_motion.csv"
        result = self.mapper.map_device_motion([df])
        assert result is not None
        assert "coCaseId" in result.columns
        assert "coTimestamp" in result.columns


class TestMergedSources:
    """Test merging multiple sources of same type."""

    def setup_method(self):
        self.mapper = DataMapper()

    def test_merge_two_labs(self):
        df1 = pd.DataFrame({"case_id": ["CASE-0001"], "sodium_mmol_L": [138]})
        df1.attrs["file_type"] = "labs"
        df2 = pd.DataFrame({"case_id": ["CASE-0002"], "sodium_mmol_L": [140]})
        df2.attrs["file_type"] = "labs"
        merged = self.mapper._merge_sources([df1, df2])
        assert len(merged) == 2

    def test_merge_empty_list(self):
        merged = self.mapper._merge_sources([])
        assert len(merged) == 0

    def test_merge_preserves_data(self):
        df1 = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        df2 = pd.DataFrame({"a": [3], "b": ["z"]})
        merged = self.mapper._merge_sources([df1, df2])
        assert len(merged) == 3
        assert list(merged["a"]) == [1, 2, 3]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
