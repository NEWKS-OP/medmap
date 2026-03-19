"""Tests for NursingNLPAnalyzer batch processing."""

import pytest
import pandas as pd
from pipeline.nlp import NursingNLPAnalyzer


@pytest.fixture
def analyzer():
    return NursingNLPAnalyzer()


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "CaseID": ["C1", "C1", "C2", "C3"],
        "PatientID": ["P1", "P1", "P2", "P3"],
        "Ward": ["ICU", "ICU", "Geriatrics", "Neurology"],
        "ReportDate": ["2025-01-01", "2025-01-02", "2025-01-01", "2025-01-01"],
        "Shift": ["Early shift", "Nachtschicht", "Late shift", "Spätschicht"],
        "NursingNote": [
            "Pain level 5/10. mobilized to corridor.",
            "Bewertung: verschlechtert. Schmerzen.",
            "wound without irritation. stable condition.",
            "confused and agitated. bed-bound.",
        ],
    })


class TestNursingNLPAnalyzer:
    def test_analyze_dataframe_returns_list(self, analyzer, sample_df):
        results = analyzer.analyze_dataframe(sample_df)
        assert isinstance(results, list)
        assert len(results) == 4

    def test_analyze_dataframe_extracts_pain(self, analyzer, sample_df):
        results = analyzer.analyze_dataframe(sample_df)
        assert results[0]["pain_level"] == 5
        assert results[1]["pain_level"] == 4  # Schmerzen

    def test_analyze_dataframe_extracts_mobility(self, analyzer, sample_df):
        results = analyzer.analyze_dataframe(sample_df)
        assert results[0]["mobility_status"] == "INDEPENDENT"
        assert results[3]["mobility_status"] == "BED_BOUND"

    def test_analyze_dataframe_extracts_wound(self, analyzer, sample_df):
        results = analyzer.analyze_dataframe(sample_df)
        assert results[2]["wound_grade"] == "HEALING"

    def test_analyze_dataframe_extracts_deterioration(self, analyzer, sample_df):
        results = analyzer.analyze_dataframe(sample_df)
        assert results[1]["deterioration_flag"] is True
        assert results[3]["deterioration_flag"] is True

    def test_analyze_dataframe_normalizes_shifts(self, analyzer, sample_df):
        results = analyzer.analyze_dataframe(sample_df)
        assert results[0]["shift"] == "Early"
        assert results[1]["shift"] == "Night"
        assert results[2]["shift"] == "Late"
        assert results[3]["shift"] == "Late"

    def test_analyze_dataframe_empty(self, analyzer):
        results = analyzer.analyze_dataframe(pd.DataFrame())
        assert results == []

    def test_analyze_dataframe_none(self, analyzer):
        results = analyzer.analyze_dataframe(None)
        assert results == []

    def test_analyze_all_groups_by_case(self, analyzer, sample_df):
        grouped = analyzer.analyze_all({"nursing.csv": sample_df})
        assert "C1" in grouped
        assert len(grouped["C1"]) == 2
        assert "C2" in grouped
        assert len(grouped["C2"]) == 1

    def test_analyze_all_skips_non_nursing(self, analyzer):
        df = pd.DataFrame({"col1": [1], "col2": [2]})
        grouped = analyzer.analyze_all({"labs.csv": df})
        assert grouped == {}

    def test_is_nursing_data_by_filename(self, analyzer):
        df = pd.DataFrame({"CaseID": [], "NursingNote": []})
        assert NursingNLPAnalyzer._is_nursing_data("synth_nursing_daily_reports.csv", df) is True

    def test_is_nursing_data_by_column(self, analyzer):
        df = pd.DataFrame({"CaseID": [], "coNursing_note_free_text": []})
        assert NursingNLPAnalyzer._is_nursing_data("data.csv", df) is True

    def test_is_not_nursing_data(self, analyzer):
        df = pd.DataFrame({"CaseID": [], "LabValue": []})
        assert NursingNLPAnalyzer._is_nursing_data("labs.csv", df) is False

    def test_get_summary_stats(self, analyzer, sample_df):
        grouped = analyzer.analyze_all({"nursing.csv": sample_df})
        stats = analyzer.get_summary_stats(grouped)
        assert stats["total_notes_analyzed"] == 4
        assert stats["total_patients"] == 3
        assert stats["pain_extracted"] == 2
        assert stats["deterioration_flagged"] == 2

    def test_nan_notes_skipped(self, analyzer):
        df = pd.DataFrame({
            "CaseID": ["C1", "C2"],
            "NursingNote": ["nan", "Pain 5/10"],
            "Shift": ["Early", "Late"],
            "ReportDate": ["2025-01-01", "2025-01-02"],
        })
        results = analyzer.analyze_dataframe(df)
        assert len(results) == 1
        assert results[0]["pain_level"] == 5
