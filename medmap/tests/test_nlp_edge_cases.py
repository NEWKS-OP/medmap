"""Edge case tests for NLP module."""

import pytest
from pipeline.nlp import (
    extract_pain_level,
    extract_mobility_status,
    extract_wound_grade,
    extract_deterioration_signs,
    normalize_shift,
    analyze_note,
    NursingNLPAnalyzer,
)
import pandas as pd


class TestPainEdgeCases:
    def test_pain_in_sentence(self):
        assert extract_pain_level("Patient reported mild pain during movement") == 3

    def test_pain_level_with_colon(self):
        assert extract_pain_level("pain: 6/10") == 6

    def test_pain_level_with_equals(self):
        assert extract_pain_level("pain=4") == 4

    def test_case_insensitive(self):
        assert extract_pain_level("PAIN LEVEL 3/10") == 3

    def test_integer_input(self):
        assert extract_pain_level(42) is None

    def test_float_nan(self):
        assert extract_pain_level(float("nan")) is None

    def test_leichte_schmerzen(self):
        assert extract_pain_level("leichte Schmerzen beim Aufstehen") == 3


class TestMobilityEdgeCases:
    def test_mobilized_in_sentence(self):
        result = extract_mobility_status("Patient was mobilized to corridor by nurse")
        assert result == "INDEPENDENT"

    def test_rollstuhl(self):
        assert extract_mobility_status("Rollstuhl benötigt") == "WHEELCHAIR"

    def test_immobil(self):
        assert extract_mobility_status("Patient immobil") == "BED_BOUND"

    def test_independent(self):
        assert extract_mobility_status("Patient independent") == "INDEPENDENT"

    def test_integer_input(self):
        assert extract_mobility_status(42) is None


class TestWoundEdgeCases:
    def test_stage_1_pressure(self):
        assert extract_wound_grade("stage 1 pressure ulcer") == "1"

    def test_grade_4(self):
        assert extract_wound_grade("wound grade 4") == "4"

    def test_granulating(self):
        assert extract_wound_grade("wound granulating well") == "HEALING"

    def test_grade_0_invalid(self):
        assert extract_wound_grade("wound grade 0") is None

    def test_integer_input(self):
        assert extract_wound_grade(42) is None


class TestDeteriorationEdgeCases:
    def test_nausea(self):
        flag, signs = extract_deterioration_signs("Patient Übelkeit")
        assert flag is True
        assert "nausea" in signs

    def test_dizziness(self):
        flag, signs = extract_deterioration_signs("Patient Schwindel")
        assert flag is True
        assert "dizziness" in signs

    def test_multiple_german(self):
        flag, signs = extract_deterioration_signs("Fieber und Atemnot")
        assert flag is True
        assert "fever" in signs
        assert "dyspnea" in signs

    def test_integer_input(self):
        flag, signs = extract_deterioration_signs(42)
        assert flag is False
        assert signs == []

    def test_signs_are_sorted(self):
        _, signs = extract_deterioration_signs("agitated confused deteriorating")
        assert signs == sorted(signs)


class TestShiftEdgeCases:
    def test_whitespace(self):
        assert normalize_shift("  Early shift  ") == "Early"

    def test_mixed_case(self):
        assert normalize_shift("NIGHT SHIFT") == "Night"

    def test_integer(self):
        assert normalize_shift(42) == "Early"

    def test_numeric_string(self):
        assert normalize_shift("123") == "Early"


class TestAnalyzeNoteEdgeCases:
    def test_empty_dict_on_empty(self):
        result = analyze_note("")
        assert result["pain_level"] is None
        assert result["deterioration_flag"] is False

    def test_priority_marker_ignored(self):
        result = analyze_note("stable condition @PRIORITY#")
        assert result["pain_level"] is None

    def test_mixed_en_de_note(self):
        result = analyze_note("Frühschicht: Atemnot. mobilized to corridor. Bewertung: verschlechtert.")
        assert result["mobility_status"] == "INDEPENDENT"
        assert result["deterioration_flag"] is True
        assert "dyspnea" in result["deterioration_signs"]
        assert "deteriorating" in result["deterioration_signs"]


class TestAnalyzerWithMappedColumns:
    def test_mapped_column_names(self):
        df = pd.DataFrame({
            "case_id": ["C1"],
            "shift": ["Early"],
            "report_date": ["2025-01-01"],
            "nursing_note_free_text": ["Pain 5/10. confused."],
        })
        analyzer = NursingNLPAnalyzer()
        results = analyzer.analyze_dataframe(df)
        assert len(results) == 1
        assert results[0]["pain_level"] == 5
        assert results[0]["deterioration_flag"] is True

    def test_co_prefixed_columns(self):
        df = pd.DataFrame({
            "coCaseId": ["C1"],
            "coShift": ["Late"],
            "coReport_date": ["2025-01-01"],
            "coNursing_note_free_text": ["mild pain"],
        })
        analyzer = NursingNLPAnalyzer()
        results = analyzer.analyze_dataframe(df)
        assert len(results) == 1
        assert results[0]["pain_level"] == 3
