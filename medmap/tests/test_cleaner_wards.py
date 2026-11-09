"""Tests for ward / station normalization in the cleaner."""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.cleaner import DataCleaner


def _clean(values, col="Station"):
    df = pd.DataFrame({col: values, "CaseID": [str(i) for i in range(len(values))]})
    return DataCleaner()._normalize_wards(df, "test.csv", "icd10_ops")[col].tolist()


def test_strips_trailing_noise_characters():
    out = _clean(["Chirurgie@", "Kardiologieü", "Innere Medizin%", "Neurologie$", "Geriatrieß"])
    assert out == ["Chirurgie", "Kardiologie", "Innere Medizin", "Neurologie", "Geriatrie"]


def test_strips_whitespace():
    assert _clean(["Chirurgie\t", "  Pneumologie "]) == ["Chirurgie", "Pneumologie"]


def test_keeps_clean_values():
    assert _clean(["Intensivstation", "Neurologie"]) == ["Intensivstation", "Neurologie"]


def test_rejects_icd_codes_from_shifted_columns():
    out = _clean(["I50.1", "G20^", "J44.1"])
    assert all(isinstance(v, float) and np.isnan(v) for v in out)


def test_handles_lowercase_and_uppercase_headers():
    assert _clean(["Chirurgie#"], col="ward") == ["Chirurgie"]
    assert _clean(["Chirurgie#"], col="WARD") == ["Chirurgie"]


def test_ignores_missing_values():
    out = _clean([None, np.nan, "Chirurgie"])
    assert out[0] is None
    assert isinstance(out[1], float) and np.isnan(out[1])
    assert out[2] == "Chirurgie"
