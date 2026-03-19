"""Tests for pipeline/mapper.py — DataMapper class."""

import sys
import os
import pytest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.mapper import DataMapper


# ──────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────

@pytest.fixture
def mapper():
    """DataMapper with no IID-SID-ITEM map."""
    return DataMapper()


@pytest.fixture
def iid_sid_df():
    """Minimal IID-SID-ITEM.csv DataFrame."""
    return pd.DataFrame({
        "ItmIID": ["E0_I_001", "E0_I_004", "E0_I_005", "E2_I_223", "E2_I_228"],
        "ItmName255_EN": ["Height cm", "Weight kg", "BMI", "Admission Date", "Discharge Date"],
        "ItmSID": ["00_01", "00_04", "00_05", "02_23", "02_28"],
    })


@pytest.fixture
def mapper_with_iid(iid_sid_df):
    """DataMapper with IID-SID-ITEM map loaded."""
    return DataMapper(iid_sid_map=iid_sid_df)


@pytest.fixture
def sample_labs_df():
    """Sample labs DataFrame with file_type attr."""
    df = pd.DataFrame({
        "case_id": ["CASE-0001", "CASE-0002", "CASE-0003"],
        "patient_id": ["LAB_100", "LAB_200", "LAB_300"],
        "sex": ["M", "F", "M"],
        "age_years": [45, 67, 32],
        "specimen_datetime": ["2025-01-01", "2025-01-02", "2025-01-03"],
        "sodium_mmol_L": [140.0, 135.0, 145.0],
        "sodium_flag": ["N", "L", "H"],
        "potassium_mmol_L": [4.0, 3.5, 5.0],
    })
    df.attrs["file_type"] = "labs"
    df.attrs["source_file"] = "test_labs.csv"
    return df


@pytest.fixture
def sample_icd10_df():
    """Sample icd10_ops DataFrame."""
    df = pd.DataFrame({
        "case_id": ["CASE-0001", "CASE-0002"],
        "patient_id": ["ICD_100", "ICD_200"],
        "admission_date": ["2025-01-01", "2025-01-05"],
        "discharge_date": ["2025-01-10", "2025-01-15"],
        "primary_icd10_code": ["I50.0", "J18.9"],
        "primary_icd10_description_en": ["Heart failure", "Pneumonia"],
        "secondary_icd10_codes": ["E11.9", ""],
        "ops_codes": ["5-353", ""],
        "ward": ["Cardio", "Pulmo"],
    })
    df.attrs["file_type"] = "icd10_ops"
    df.attrs["source_file"] = "test_icd10.csv"
    return df


@pytest.fixture
def sample_device_motion_df():
    """Sample device_motion DataFrame."""
    df = pd.DataFrame({
        "case_id": ["CASE-0010"] * 5,
        "patient_id": ["MOT_500"] * 5,
        "timestamp": pd.date_range("2025-01-01", periods=5, freq="s"),
        "movement_index_0_100": [50, 60, 70, 30, 10],
        "micro_movements_count": [5, 3, 8, 2, 0],
        "bed_exit_detected_0_1": [0, 0, 1, 0, 0],
        "fall_event_0_1": [0, 0, 0, 0, 1],
        "impact_magnitude_g": [0.1, 0.2, 0.5, 0.1, 3.2],
        "post_fall_immobility_minutes": [0, 0, 0, 0, 15],
    })
    df.attrs["file_type"] = "device_motion"
    df.attrs["source_file"] = "test_motion.csv"
    return df


@pytest.fixture
def sample_device_1hz_df():
    """Sample device_1hz DataFrame."""
    df = pd.DataFrame({
        "case_id": ["CASE-0010"] * 3,
        "patient_id": ["MOT_500"] * 3,
        "device_id": ["DEV001"] * 3,
        "timestamp": pd.date_range("2025-01-01", periods=3, freq="s"),
        "accel_x_m_s2": [0.1, -0.2, 0.3],
        "accel_y_m_s2": [0.5, 0.3, -0.1],
        "accel_z_m_s2": [9.8, 9.7, 9.9],
        "accel_magnitude_g": [1.0, 1.0, 1.01],
        "pressure_zone1_0_100": [50, 55, 60],
        "pressure_zone2_0_100": [40, 42, 38],
        "pressure_zone3_0_100": [30, 28, 35],
        "pressure_zone4_0_100": [20, 25, 22],
        "movement_score_0_100": [45, 50, 55],
        "fall_event_0_1": [0, 0, 0],
        "bed_occupied_0_1": [1, 1, 1],
        "bed_exit_event_0_1": [0, 0, 0],
        "bed_return_event_0_1": [0, 0, 0],
        "impact_magnitude_g": [0.1, 0.1, 0.1],
        "event_id": [None, None, None],
    })
    df.attrs["file_type"] = "device_1hz"
    df.attrs["source_file"] = "test_1hz.csv"
    return df


@pytest.fixture
def sample_medication_df():
    """Sample medication DataFrame."""
    df = pd.DataFrame({
        "case_id": ["CASE-0020", "CASE-0020", "CASE-0021"],
        "patient_id": ["MED_600", "MED_600", "MED_700"],
        "record_type": ["ORDER", "ADMIN", "ORDER"],
        "medication_name": ["Aspirin", "Aspirin", "Metformin"],
        "medication_code_atc": ["B01AC06", "B01AC06", "A10BA02"],
        "route": ["oral", "oral", "oral"],
        "dose": ["100mg", "100mg", "500mg"],
        "frequency": ["QD", "QD", "BID"],
        "prescriber_role": ["Physician", "Nurse", "Physician"],
    })
    df.attrs["file_type"] = "medication"
    df.attrs["source_file"] = "test_med.csv"
    return df


@pytest.fixture
def sample_nursing_df():
    """Sample nursing DataFrame."""
    df = pd.DataFrame({
        "case_id": ["CASE-0030", "CASE-0030"],
        "patient_id": ["NUR_800", "NUR_800"],
        "report_date": ["2025-01-01", "2025-01-02"],
        "shift": ["Early", "Late"],
        "nursing_note_free_text": [
            "Patient resting comfortably. Pain level 2/10.",
            "A" * 300,  # Long note to test truncation
        ],
    })
    df.attrs["file_type"] = "nursing"
    df.attrs["source_file"] = "test_nursing.csv"
    return df


@pytest.fixture
def sample_epac_german_df():
    """Sample epaAC German-format DataFrame."""
    df = pd.DataFrame({
        "EinschIDFall": ["CASE-0040", "CASE-0041"],
        "EinschIDPat": ["EPA_900", "EPA_901"],
        "Körpergröße": [175, 160],
        "Gewicht": [80, 55],
        "BMI": [26.1, 21.5],
        "AufnDat": ["2025-01-01", "2025-01-10"],
        "EntlDat": ["2025-01-10", "2025-01-20"],
        "Alter": [55, 72],
        "Station": ["Ward A", "Ward B"],
    })
    df.attrs["file_type"] = "epaAC_german"
    df.attrs["source_file"] = "test_epac_german.csv"
    return df


@pytest.fixture
def sample_epac_sap_df():
    """Sample epaAC SAP-format DataFrame."""
    df = pd.DataFrame({
        "MANDT": [100, 100],
        "PATFAL": ["CASE-0050", "CASE-0051"],
        "PATFOE": ["SAP_1000", "SAP_1001"],
        "PATADT": ["2025-02-01", "2025-02-15"],
        "PATDOE": ["2025-02-10", "2025-02-25"],
        "EPA0001": [170, 165],
        "EPA0004": [75, 60],
        "EPA0005": [26.0, 22.0],
        "EPA0043": ["Y", "N"],
    })
    df.attrs["file_type"] = "epaAC_sap"
    df.attrs["source_file"] = "test_epac_sap.csv"
    return df


@pytest.fixture
def sample_epac_pivot_df(iid_sid_df):
    """Sample epaAC Pivot-format DataFrame."""
    df = pd.DataFrame({
        "FallID": ["CASE-0060", "CASE-0060", "CASE-0060", "CASE-0061", "CASE-0061"],
        "PID": ["PIV_200", "PIV_200", "PIV_200", "PIV_201", "PIV_201"],
        "SID": ["00_01", "00_04", "00_05", "00_01", "00_04"],
        "SID_value": [180, 90, 27.8, 155, 50],
        "Station": ["Ward C", "Ward C", "Ward C", "Ward D", "Ward D"],
    })
    df.attrs["file_type"] = "epaAC_pivot"
    df.attrs["source_file"] = "test_epac_pivot.csv"
    return df


# ──────────────────────────────────────────────
# HELPER TESTS
# ──────────────────────────────────────────────

class TestExtractCaseIdNumeric:
    def test_case_prefix(self, mapper):
        assert mapper._extract_case_id_numeric("CASE-0042") == 42

    def test_plain_number(self, mapper):
        assert mapper._extract_case_id_numeric("123") == 123

    def test_zero_padded(self, mapper):
        assert mapper._extract_case_id_numeric("CASE-0001") == 1

    def test_none(self, mapper):
        assert mapper._extract_case_id_numeric(None) is None

    def test_nan(self, mapper):
        assert mapper._extract_case_id_numeric(float("nan")) is None

    def test_no_digits(self, mapper):
        assert mapper._extract_case_id_numeric("ABC") is None


class TestExtractPidNumeric:
    def test_lab_prefix(self, mapper):
        assert mapper._extract_pid_numeric("LAB_123456") == 123456

    def test_mot_prefix(self, mapper):
        assert mapper._extract_pid_numeric("MOT_500") == 500

    def test_epa_prefix(self, mapper):
        assert mapper._extract_pid_numeric("EPA_900") == 900

    def test_pat_prefix(self, mapper):
        assert mapper._extract_pid_numeric("PAT-999") == 999

    def test_plain_number(self, mapper):
        assert mapper._extract_pid_numeric("42") == 42

    def test_none(self, mapper):
        assert mapper._extract_pid_numeric(None) is None


class TestGroupByType:
    def test_groups_by_file_type(self, mapper, sample_labs_df, sample_icd10_df):
        frames = {"labs.csv": sample_labs_df, "icd10.csv": sample_icd10_df}
        grouped = mapper._group_by_type(frames)
        assert "labs" in grouped
        assert "icd10_ops" in grouped
        assert len(grouped["labs"]) == 1
        assert len(grouped["icd10_ops"]) == 1

    def test_multiple_same_type(self, mapper, sample_labs_df):
        lab2 = sample_labs_df.copy()
        lab2.attrs["file_type"] = "labs"
        frames = {"labs1.csv": sample_labs_df, "labs2.csv": lab2}
        grouped = mapper._group_by_type(frames)
        assert len(grouped["labs"]) == 2

    def test_empty_dict(self, mapper):
        assert mapper._group_by_type({}) == {}


class TestMergeSources:
    def test_merge_two(self, mapper, sample_labs_df):
        lab2 = sample_labs_df.copy()
        merged = mapper._merge_sources([sample_labs_df, lab2])
        assert len(merged) == 6

    def test_single(self, mapper, sample_labs_df):
        merged = mapper._merge_sources([sample_labs_df])
        assert len(merged) == 3

    def test_empty(self, mapper):
        merged = mapper._merge_sources([])
        assert merged.empty


class TestApplyColumnMapping:
    def test_renames_columns(self, mapper, sample_labs_df):
        mapping = {"case_id": "coCaseId", "sex": "coSex"}
        result = mapper._apply_column_mapping(sample_labs_df, mapping, "test")
        assert "coCaseId" in result.columns
        assert "coSex" in result.columns
        assert "case_id" not in result.columns

    def test_drops_unmapped_columns(self, mapper, sample_labs_df):
        mapping = {"case_id": "coCaseId"}
        result = mapper._apply_column_mapping(sample_labs_df, mapping, "test")
        assert list(result.columns) == ["coCaseId"]

    def test_no_match_returns_empty(self, mapper, sample_labs_df):
        mapping = {"nonexistent": "coNope"}
        result = mapper._apply_column_mapping(sample_labs_df, mapping, "test")
        assert result.empty
        assert len(mapper.mapping_warnings) == 1


class TestToStringColumns:
    def test_converts_to_string(self, mapper):
        df = pd.DataFrame({"val": [1.5, 2.0, 3.0], "id": [1, 2, 3]})
        result = mapper._to_string_columns(df, exclude={"id"})
        assert result["val"].iloc[0] == "1.5"
        assert result["id"].dtype != object

    def test_preserves_none(self, mapper):
        df = pd.DataFrame({"val": [1.0, None, float("nan")]})
        result = mapper._to_string_columns(df)
        assert result["val"].iloc[0] == "1.0"
        assert result["val"].iloc[1] is None
        assert result["val"].iloc[2] is None


# ──────────────────────────────────────────────
# TABLE MAPPER TESTS
# ──────────────────────────────────────────────

class TestMapLabs:
    def test_maps_columns(self, mapper, sample_labs_df):
        result = mapper.map_labs([sample_labs_df])
        assert "coCaseId" in result.columns
        assert "coSodium_mmol_L" in result.columns
        assert len(result) == 3

    def test_case_id_is_numeric(self, mapper, sample_labs_df):
        result = mapper.map_labs([sample_labs_df])
        assert result["coCaseId"].iloc[0] == 1

    def test_values_are_strings(self, mapper, sample_labs_df):
        result = mapper.map_labs([sample_labs_df])
        assert isinstance(result["coSodium_mmol_L"].iloc[0], str)

    def test_empty_input(self, mapper):
        result = mapper.map_labs([])
        assert result.empty

    def test_merge_multiple_labs(self, mapper, sample_labs_df):
        lab2 = sample_labs_df.copy()
        lab2["case_id"] = ["CASE-0004", "CASE-0005", "CASE-0006"]
        lab2.attrs["file_type"] = "labs"
        result = mapper.map_labs([sample_labs_df, lab2])
        assert len(result) == 6
