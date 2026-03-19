"""Shared test fixtures for medmap test suite."""

import os
import sys
import sqlite3
import tempfile
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import DB_DIR

DB_PATH = os.path.join(DB_DIR, "medmap.db")


@pytest.fixture
def production_db():
    """Connect to production database if available."""
    if not os.path.exists(DB_PATH):
        pytest.skip("Production DB not found")
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    conn = sqlite3.connect(path)
    yield conn, path
    conn.close()
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def sample_labs_df():
    """Create a sample labs DataFrame."""
    df = pd.DataFrame({
        "case_id": ["CASE-0001", "CASE-0002"],
        "patient_id": ["100001", "100002"],
        "sex": ["M", "F"],
        "age_years": [65, 72],
        "specimen_datetime": ["2024-01-15", "2024-01-16"],
        "sodium_mmol_L": [138.5, 142.0],
    })
    df.attrs["file_type"] = "labs"
    df.attrs["source_file"] = "test_labs.csv"
    return df


@pytest.fixture
def sample_nursing_df():
    """Create a sample nursing DataFrame."""
    df = pd.DataFrame({
        "case_id": ["CASE-0001"],
        "patient_id": ["100001"],
        "ward": ["Geriatrics"],
        "report_date": ["2024-01-15"],
        "shift": ["Early"],
        "nursing_note_free_text": ["Patient stable"],
    })
    df.attrs["file_type"] = "nursing"
    df.attrs["source_file"] = "test_nursing.csv"
    return df
