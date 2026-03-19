"""Tests for pipeline/nlp.py — NLP extraction from nursing notes."""

import pytest
from pipeline.nlp import (
    extract_pain_level,
    extract_mobility_status,
    extract_wound_grade,
    extract_deterioration_signs,
    normalize_shift,
    analyze_note,
)


# ─── Pain level extraction ────────────────────────────────────────

class TestExtractPainLevel:
    def test_numeric_pain_level(self):
        assert extract_pain_level("pain level 5/10") == 5

    def test_numeric_pain_score(self):
        assert extract_pain_level("pain score 7") == 7

    def test_vas_score(self):
        assert extract_pain_level("VAS 3") == 3

    def test_pain_without_qualifier(self):
        assert extract_pain_level("pain 8/10") == 8

    def test_qualitative_mild_pain(self):
        assert extract_pain_level("mild pain") == 3

    def test_qualitative_severe_pain(self):
        assert extract_pain_level("severe pain") == 8

    def test_qualitative_no_pain(self):
        assert extract_pain_level("no pain") == 0

    def test_german_schmerzen(self):
        assert extract_pain_level("Schmerzen") == 4

    def test_german_schmerzfrei(self):
        assert extract_pain_level("schmerzfrei") == 0

    def test_no_pain_mention(self):
        assert extract_pain_level("stable condition") is None

    def test_empty_string(self):
        assert extract_pain_level("") is None

    def test_none_input(self):
        assert extract_pain_level(None) is None

    def test_numeric_clamped_to_10(self):
        assert extract_pain_level("pain level 15/10") == 10

    def test_pain_level_zero(self):
        assert extract_pain_level("pain level 0/10") == 0


# ─── Mobility extraction ─────────────────────────────────────────

class TestExtractMobilityStatus:
    def test_mobilized_to_corridor(self):
        assert extract_mobility_status("mobilized to corridor") == "INDEPENDENT"

    def test_bed_bound(self):
        assert extract_mobility_status("bed-bound") == "BED_BOUND"

    def test_wheelchair(self):
        assert extract_mobility_status("wheelchair") == "WHEELCHAIR"

    def test_ambulating(self):
        assert extract_mobility_status("ambulating") == "INDEPENDENT"

    def test_walker(self):
        assert extract_mobility_status("walker") == "ASSISTED"

    def test_german_bettlagerig(self):
        assert extract_mobility_status("bettlägerig") == "BED_BOUND"

    def test_no_mobility_mention(self):
        assert extract_mobility_status("stable condition") is None

    def test_empty(self):
        assert extract_mobility_status("") is None

    def test_none(self):
        assert extract_mobility_status(None) is None

    def test_mobilised_with_assistance(self):
        assert extract_mobility_status("mobilised with assistance") == "ASSISTED"


# ─── Wound grade extraction ──────────────────────────────────────

class TestExtractWoundGrade:
    def test_wound_grade_numeric(self):
        assert extract_wound_grade("wound grade 3") == "3"

    def test_stage_pressure(self):
        assert extract_wound_grade("stage 2 pressure") == "2"

    def test_healing_well(self):
        assert extract_wound_grade("healing well") == "HEALING"

    def test_wound_without_irritation(self):
        assert extract_wound_grade("wound without irritation") == "HEALING"

    def test_no_wound_mention(self):
        assert extract_wound_grade("stable condition") is None

    def test_empty(self):
        assert extract_wound_grade("") is None

    def test_none(self):
        assert extract_wound_grade(None) is None

    def test_grade_out_of_range(self):
        assert extract_wound_grade("wound grade 7") is None

    def test_german_wunde_reizlos(self):
        assert extract_wound_grade("Wunde reizlos") == "HEALING"


# ─── Deterioration signs ─────────────────────────────────────────

class TestExtractDeteriorationSigns:
    def test_confused(self):
        flag, signs = extract_deterioration_signs("Patient confused")
        assert flag is True
        assert "confused" in signs

    def test_multiple_signs(self):
        flag, signs = extract_deterioration_signs("confused and agitated")
        assert flag is True
        assert "confused" in signs
        assert "agitated" in signs

    def test_german_verschlechtert(self):
        flag, signs = extract_deterioration_signs("Bewertung: verschlechtert")
        assert flag is True
        assert "deteriorating" in signs

    def test_no_signs(self):
        flag, signs = extract_deterioration_signs("stable condition")
        assert flag is False
        assert signs == []

    def test_empty(self):
        flag, signs = extract_deterioration_signs("")
        assert flag is False
        assert signs == []

    def test_none(self):
        flag, signs = extract_deterioration_signs(None)
        assert flag is False
        assert signs == []

    def test_dyspnea(self):
        flag, signs = extract_deterioration_signs("dyspnea on exertion")
        assert flag is True
        assert "dyspnea" in signs

    def test_german_atemnot(self):
        flag, signs = extract_deterioration_signs("Atemnot")
        assert flag is True
        assert "dyspnea" in signs

    def test_refused_medication(self):
        flag, signs = extract_deterioration_signs("refused medication")
        assert flag is True
        assert "refused_medication" in signs

    def test_elevated_temperature(self):
        flag, signs = extract_deterioration_signs("elevated temperature")
        assert flag is True
        assert "fever" in signs


# ─── Shift normalization ─────────────────────────────────────────

class TestNormalizeShift:
    def test_early_shift(self):
        assert normalize_shift("Early shift") == "Early"

    def test_german_fruhschicht(self):
        assert normalize_shift("Frühschicht") == "Early"

    def test_late_shift(self):
        assert normalize_shift("Late shift") == "Late"

    def test_german_spatschicht(self):
        assert normalize_shift("Spätschicht") == "Late"

    def test_night_shift(self):
        assert normalize_shift("Night shift") == "Night"

    def test_german_nachtschicht(self):
        assert normalize_shift("Nachtschicht") == "Night"

    def test_garbage_chars(self):
        assert normalize_shift("Nachtschichtö") == "Night"

    def test_night_shift_with_umlaut(self):
        assert normalize_shift("Night shiftä") == "Night"

    def test_missing(self):
        assert normalize_shift("missing") == "Early"

    def test_empty(self):
        assert normalize_shift("") == "Early"

    def test_none(self):
        assert normalize_shift(None) == "Early"


# ─── analyze_note integration ────────────────────────────────────

class TestAnalyzeNote:
    def test_full_note(self):
        result = analyze_note("Pain level 5/10. mobilized to corridor. wound grade 2. confused.")
        assert result["pain_level"] == 5
        assert result["mobility_status"] == "INDEPENDENT"
        assert result["wound_grade"] == "2"
        assert result["deterioration_flag"] is True
        assert "confused" in result["deterioration_signs"]

    def test_benign_note(self):
        result = analyze_note("Patient stable condition. No complications.")
        assert result["pain_level"] is None
        assert result["mobility_status"] is None
        assert result["wound_grade"] is None
        assert result["deterioration_flag"] is False

    def test_german_mixed(self):
        result = analyze_note("Schmerzen. Bewertung: verschlechtert. Lagerung.")
        assert result["pain_level"] == 4
        assert result["deterioration_flag"] is True
