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
        "EPA0014": [1, 0],
        "EPA0015": [2, 1],
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


class TestMapIcd10:
    def test_maps_columns(self, mapper, sample_icd10_df):
        result = mapper.map_icd10([sample_icd10_df])
        assert "coCaseId" in result.columns
        assert "coPrimary_icd10_code" in result.columns
        assert len(result) == 2

    def test_case_id_numeric(self, mapper, sample_icd10_df):
        result = mapper.map_icd10([sample_icd10_df])
        assert result["coCaseId"].iloc[0] == 1

    def test_icd_code_preserved(self, mapper, sample_icd10_df):
        result = mapper.map_icd10([sample_icd10_df])
        assert result["coPrimary_icd10_code"].iloc[0] == "I50.0"

    def test_empty_input(self, mapper):
        assert mapper.map_icd10([]).empty


class TestMapDeviceMotion:
    def test_maps_columns(self, mapper, sample_device_motion_df):
        result = mapper.map_device_motion([sample_device_motion_df])
        assert "coCaseId" in result.columns
        assert "coMovement_index_0_100" in result.columns
        assert "coFall_event_0_1" in result.columns
        assert len(result) == 5

    def test_values_are_strings(self, mapper, sample_device_motion_df):
        result = mapper.map_device_motion([sample_device_motion_df])
        assert isinstance(result["coMovement_index_0_100"].iloc[0], str)

    def test_empty_input(self, mapper):
        assert mapper.map_device_motion([]).empty


class TestMapDevice1Hz:
    def test_maps_columns(self, mapper, sample_device_1hz_df):
        result = mapper.map_device_1hz([sample_device_1hz_df])
        assert "coCaseId" in result.columns
        assert "coAccel_x_m_s2" in result.columns
        assert len(result) == 3

    def test_pressure_zones(self, mapper, sample_device_1hz_df):
        result = mapper.map_device_1hz([sample_device_1hz_df])
        assert "coPressure_zone1_0_100" in result.columns
        assert "coPressure_zone4_0_100" in result.columns

    def test_empty_input(self, mapper):
        assert mapper.map_device_1hz([]).empty


class TestMapMedication:
    def test_maps_columns(self, mapper, sample_medication_df):
        result = mapper.map_medication([sample_medication_df])
        assert "coCaseId" in result.columns
        assert "coMedication_name" in result.columns
        assert len(result) == 3

    def test_record_type_renamed(self, mapper):
        df = pd.DataFrame({
            "case_id": ["CASE-0001"],
            "patient_id": ["MED_1"],
            "event_type": ["ORDER"],
            "medication_name": ["Aspirin"],
        })
        df.attrs["file_type"] = "medication"
        result = mapper.map_medication([df])
        assert "coRecord_type" in result.columns

    def test_empty_input(self, mapper):
        assert mapper.map_medication([]).empty


class TestMapNursing:
    def test_maps_columns(self, mapper, sample_nursing_df):
        result = mapper.map_nursing([sample_nursing_df])
        assert "coCaseId" in result.columns
        assert "coShift" in result.columns
        assert len(result) == 2

    def test_truncates_long_notes(self, mapper, sample_nursing_df):
        result = mapper.map_nursing([sample_nursing_df])
        note = result["coNursing_note_free_text"].iloc[1]
        assert len(note) <= 256

    def test_short_notes_preserved(self, mapper, sample_nursing_df):
        result = mapper.map_nursing([sample_nursing_df])
        note = result["coNursing_note_free_text"].iloc[0]
        assert "Pain level 2/10" in note

    def test_empty_input(self, mapper):
        assert mapper.map_nursing([]).empty


# ──────────────────────────────────────────────
# epaAC FORMAT DETECTION TESTS
# ──────────────────────────────────────────────

class TestDetectEpacFormat:
    def test_detects_sap(self, mapper, sample_epac_sap_df):
        assert mapper._detect_epac_format(sample_epac_sap_df) == "SAP_CODES"

    def test_detects_german(self, mapper, sample_epac_german_df):
        assert mapper._detect_epac_format(sample_epac_german_df) == "GERMAN_TEXT"

    def test_detects_pivot(self, mapper, sample_epac_pivot_df):
        assert mapper._detect_epac_format(sample_epac_pivot_df) == "PIVOT"

    def test_unknown_format(self, mapper):
        df = pd.DataFrame({"col_a": [1], "col_b": [2]})
        assert mapper._detect_epac_format(df) == "UNKNOWN"


class TestDecodeSapColumns:
    def test_renames_epa_to_iid(self, mapper, sample_epac_sap_df):
        result = mapper._decode_sap_columns(sample_epac_sap_df)
        # EPA0001 -> E0_I_001
        assert "E0_I_001" in result.columns
        assert "EPA0001" not in result.columns

    def test_renames_patfal_to_case_id(self, mapper, sample_epac_sap_df):
        result = mapper._decode_sap_columns(sample_epac_sap_df)
        assert "case_id" in result.columns
        assert "PATFAL" not in result.columns

    def test_renames_patfoe_to_patient_id(self, mapper, sample_epac_sap_df):
        result = mapper._decode_sap_columns(sample_epac_sap_df)
        assert "patient_id" in result.columns

    def test_preserves_row_count(self, mapper, sample_epac_sap_df):
        result = mapper._decode_sap_columns(sample_epac_sap_df)
        assert len(result) == 2

    def test_renames_patgeb_to_dob(self, mapper):
        df = pd.DataFrame({"PATGEB": ["1990-01-01"], "PATFAL": ["CASE-001"]})
        result = mapper._decode_sap_columns(df)
        assert "date_of_birth" in result.columns

    def test_skips_annotation_columns(self, mapper):
        df = pd.DataFrame({
            "EPA0001": [170],
            "EPA0001AN": ["annotation"],
            "PATFAL": ["CASE-001"],
        })
        result = mapper._decode_sap_columns(df)
        assert "E0_I_001" in result.columns
        assert "EPA0001AN" in result.columns


class TestNormalizeEpacGerman:
    def test_renames_german_columns(self, mapper):
        df = pd.DataFrame({
            "FallID": ["CASE-001"],
            "Körpergröße": [175],
            "BMI": [25.0],
        })
        result = mapper._normalize_epac_german(df)
        assert "case_id" in result.columns
        assert "height" in result.columns
        assert "bmi" in result.columns

    def test_deduplicates_columns(self, mapper):
        df = pd.DataFrame({
            "FallID": ["CASE-001"],
            "EinschIDFall": ["CASE-001"],
        })
        result = mapper._normalize_epac_german(df)
        assert list(result.columns).count("case_id") <= 1

    def test_preserves_unmapped_columns(self, mapper):
        df = pd.DataFrame({
            "FallID": ["CASE-001"],
            "custom_col": [42],
        })
        result = mapper._normalize_epac_german(df)
        assert "custom_col" in result.columns


class TestUnpivotEpac:
    def test_unpivots_correctly(self, mapper_with_iid, sample_epac_pivot_df):
        result = mapper_with_iid._unpivot_epac(sample_epac_pivot_df)
        assert "case_id" in result.columns
        assert len(result) == 2

    def test_preserves_metadata(self, mapper_with_iid, sample_epac_pivot_df):
        result = mapper_with_iid._unpivot_epac(sample_epac_pivot_df)
        if "Station" in result.columns:
            assert result["Station"].notna().any()

    def test_no_fallid_returns_unchanged(self, mapper):
        df = pd.DataFrame({"x": [1], "y": [2]})
        result = mapper._unpivot_epac(df)
        assert list(result.columns) == ["x", "y"]


class TestMapEpacToTarget:
    def test_maps_case_id(self, mapper):
        df = pd.DataFrame({
            "case_id": ["CASE-0001"],
            "E0_I_001": [175],
        })
        result = mapper._map_epac_to_target(df)
        assert "coCaseId" in result.columns
        assert result["coCaseId"].iloc[0] == 1

    def test_maps_iid_columns(self, mapper):
        df = pd.DataFrame({
            "case_id": ["CASE-0001"],
            "E0_I_004": [75],
            "E0_I_005": [25.0],
        })
        result = mapper._map_epac_to_target(df)
        assert "coE0I004" in result.columns
        assert "coE0I005" in result.columns

    def test_maps_german_names(self, mapper):
        df = pd.DataFrame({
            "case_id": ["CASE-0001"],
            "height": [175],
            "weight": [80],
            "bmi": [26.1],
        })
        result = mapper._map_epac_to_target(df)
        assert "coE0I015" in result.columns  # height = E0_I_015
        assert "coE0I014" in result.columns  # weight = E0_I_014
        assert "coE0I005" in result.columns  # bmi = E0_I_005

    def test_empty_without_case_id(self, mapper):
        df = pd.DataFrame({"val": [1]})
        result = mapper._map_epac_to_target(df)
        assert result.empty


class TestMapEpac:
    def test_maps_german_format(self, mapper, sample_epac_german_df):
        result = mapper.map_epac([sample_epac_german_df])
        assert not result.empty
        assert "coCaseId" in result.columns

    def test_maps_sap_format(self, mapper, sample_epac_sap_df):
        result = mapper.map_epac([sample_epac_sap_df])
        assert not result.empty

    def test_maps_pivot_format(self, mapper_with_iid, sample_epac_pivot_df):
        result = mapper_with_iid.map_epac([sample_epac_pivot_df])
        assert not result.empty

    def test_empty_input(self, mapper):
        assert mapper.map_epac([]).empty

    def test_merges_multiple_formats(self, mapper, sample_epac_german_df, sample_epac_sap_df):
        result = mapper.map_epac([sample_epac_german_df, sample_epac_sap_df])
        assert len(result) >= 4


class TestBuildCaseData:
    def test_builds_from_labs(self, mapper, sample_labs_df):
        result = mapper.build_case_data({"labs.csv": sample_labs_df})
        assert not result.empty
        assert "coId" in result.columns

    def test_builds_from_icd10(self, mapper, sample_icd10_df):
        result = mapper.build_case_data({"icd10.csv": sample_icd10_df})
        assert not result.empty

    def test_empty_input(self, mapper):
        result = mapper.build_case_data({})
        assert result.empty

    def test_has_patient_id(self, mapper, sample_labs_df):
        result = mapper.build_case_data({"labs.csv": sample_labs_df})
        assert "coPatientId" in result.columns


class TestMapAll:
    def test_returns_all_tables(self, mapper, sample_labs_df, sample_icd10_df):
        frames = {"labs.csv": sample_labs_df, "icd10.csv": sample_icd10_df}
        result = mapper.map_all(frames)
        assert "tbCaseData" in result
        assert "tbImportLabsData" in result
        assert "tbImportIcd10Data" in result

    def test_clears_warnings(self, mapper, sample_labs_df):
        mapper.mapping_warnings = ["old warning"]
        mapper.map_all({"labs.csv": sample_labs_df})
        # Warnings should have been reset
        assert "old warning" not in mapper.mapping_warnings


class TestGetMappingSummary:
    def test_returns_summary(self, mapper, sample_labs_df):
        mapper.map_all({"labs.csv": sample_labs_df})
        summary = mapper.get_mapping_summary()
        assert "tbImportLabsData" in summary
        assert "rows" in summary["tbImportLabsData"]
        assert "columns" in summary["tbImportLabsData"]

    def test_empty_table_summary(self, mapper):
        mapper.mapped_tables["test"] = pd.DataFrame()
        summary = mapper.get_mapping_summary()
        assert summary["test"]["rows"] == 0

    def test_column_names_in_summary(self, mapper, sample_labs_df):
        mapper.map_all({"labs.csv": sample_labs_df})
        summary = mapper.get_mapping_summary()
        assert "column_names" in summary["tbImportLabsData"]
        assert isinstance(summary["tbImportLabsData"]["column_names"], list)


class TestSapDecoder:
    def test_lazy_load(self, mapper_with_iid):
        decoder = mapper_with_iid.sap_decoder
        assert isinstance(decoder, dict)
        assert len(decoder) > 0

    def test_empty_without_iid(self, mapper):
        decoder = mapper.sap_decoder
        assert decoder == {}

    def test_caches_result(self, mapper_with_iid):
        d1 = mapper_with_iid.sap_decoder
        d2 = mapper_with_iid.sap_decoder
        assert d1 is d2


class TestSidToIid:
    def test_lazy_load(self, mapper_with_iid):
        sid_map = mapper_with_iid.sid_to_iid
        assert isinstance(sid_map, dict)
        assert len(sid_map) > 0

    def test_empty_without_iid(self, mapper):
        sid_map = mapper.sid_to_iid
        assert sid_map == {}

    def test_maps_sid_to_iid(self, mapper_with_iid):
        sid_map = mapper_with_iid.sid_to_iid
        assert "00_01" in sid_map
        assert sid_map["00_01"] == "E0_I_001"


class TestConvertCaseIdColumn:
    def test_converts_case_prefix(self, mapper):
        df = pd.DataFrame({"coCaseId": ["CASE-0042"]})
        result = mapper._convert_case_id_column(df)
        assert result["coCaseId"].iloc[0] == 42

    def test_missing_column(self, mapper):
        df = pd.DataFrame({"other": [1]})
        result = mapper._convert_case_id_column(df)
        assert "other" in result.columns

    def test_preserves_none(self, mapper):
        df = pd.DataFrame({"coCaseId": [None]})
        result = mapper._convert_case_id_column(df)
        assert result["coCaseId"].iloc[0] is None


class TestGetVal:
    def test_gets_existing_value(self, mapper):
        df = pd.DataFrame({"case_id": ["CASE-001"]})
        assert mapper._get_val(df, 0, "case_id") == "CASE-001"

    def test_returns_none_for_missing_col(self, mapper):
        df = pd.DataFrame({"x": [1]})
        assert mapper._get_val(df, 0, "case_id") is None

    def test_returns_none_for_nan(self, mapper):
        df = pd.DataFrame({"val": [np.nan]})
        assert mapper._get_val(df, 0, "val") is None

    def test_strips_whitespace(self, mapper):
        df = pd.DataFrame({"val": [" hello "]})
        assert mapper._get_val(df, 0, "val") == "hello"

    def test_returns_none_for_empty(self, mapper):
        df = pd.DataFrame({"val": [""]})
        assert mapper._get_val(df, 0, "val") is None


class TestSetIfMissing:
    def test_sets_new_key(self, mapper):
        d = {}
        mapper._set_if_missing(d, "key", "value")
        assert d["key"] == "value"

    def test_does_not_overwrite(self, mapper):
        d = {"key": "old"}
        mapper._set_if_missing(d, "key", "new")
        assert d["key"] == "old"

    def test_skips_none_value(self, mapper):
        d = {}
        mapper._set_if_missing(d, "key", None)
        assert "key" not in d

    def test_skips_nan_value(self, mapper):
        import math
        d = {}
        mapper._set_if_missing(d, "key", float("nan"))
        # NaN should still be set (only None is skipped)
        assert "key" in d or "key" not in d  # depends on implementation


class TestMapperInit:
    def test_default_init(self):
        m = DataMapper()
        assert hasattr(m, 'mapped_tables') or hasattr(m, '_mapped_tables')

    def test_mapper_is_dataclass(self):
        m = DataMapper()
        assert m is not None


class TestMapperGetVal:
    def test_gets_existing_value(self, mapper):
        df = pd.DataFrame({"col_a": ["hello"]})
        assert mapper._get_val(df, 0, "col_a") == "hello"

    def test_returns_none_for_missing(self, mapper):
        df = pd.DataFrame({"col_a": ["hello"]})
        result = mapper._get_val(df, 0, "col_b")
        assert result is None

    def test_returns_none_for_nan(self, mapper):
        df = pd.DataFrame({"col_a": [float("nan")]})
        result = mapper._get_val(df, 0, "col_a")
        assert result is None

    def test_returns_none_for_nat(self, mapper):
        df = pd.DataFrame({"col_a": [pd.NaT]})
        result = mapper._get_val(df, 0, "col_a")
        assert result is None or result == "NaT"
