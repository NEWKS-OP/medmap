"""Tests for pipeline/ingestion.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.ingestion import DataIngester
from config.settings import DIRTY_DIR, CLEAN_DIR, SPLIT_DIR


def test_iid_sid_item():
    ingester = DataIngester()
    df = ingester.load_iid_sid_item()
    assert df is not None, "IID-SID-ITEM.csv failed to load"
    assert len(df) > 7000, f"Expected 7000+ rows, got {len(df)}"
    assert "ItmIID" in df.columns
    assert "ItmName255_EN" in df.columns
    decoder = ingester.get_sap_decoder()
    assert len(decoder) > 1000, f"Expected 1000+ decoder entries, got {len(decoder)}"
    print("PASS: IID-SID-ITEM.csv")


def test_dirty_base_files():
    ingester = DataIngester()
    expected = {
        "synth_labs.csv": ("labs", 4000),
        "synth_cases_icd10_ops.csv": ("icd10_ops", 500),
        "synth_device_motion_fall.csv": ("device_motion", 30000),
        "synth_medication_raw_inpatient.csv": ("medication", 20000),
        "synth_nursing_daily_reports.csv": ("nursing", 1000),
        "epaAC-Data-3.csv": ("epaAC_german", 30),
    }

    for fname, (expected_type, min_rows) in expected.items():
        filepath = os.path.join(DIRTY_DIR, fname)
        df, res = ingester.load(filepath)
        assert df is not None, f"{fname}: failed to load"
        assert df.attrs["file_type"] == expected_type, (
            f"{fname}: expected type {expected_type}, got {df.attrs['file_type']}"
        )
        assert res.rows_loaded >= min_rows, (
            f"{fname}: expected >={min_rows} rows, got {res.rows_loaded}"
        )
        print(f"PASS: {fname} ({res.rows_loaded} rows, {expected_type})")


def test_dirty_xlsx_files():
    ingester = DataIngester()
    for fname in ["synth_labs.xlsx", "synth_cases_icd10_ops.xlsx"]:
        filepath = os.path.join(DIRTY_DIR, fname)
        df, res = ingester.load(filepath)
        assert df is not None, f"{fname}: failed to load"
        assert res.rows_loaded > 0, f"{fname}: 0 rows"
        # Should have standard columns after rename
        assert "case_id" in df.columns or "CaseID" in df.columns, (
            f"{fname}: missing case_id column"
        )
        print(f"PASS: {fname} ({res.rows_loaded} rows)")


def test_1hz_chunked():
    ingester = DataIngester()
    filepath = os.path.join(DIRTY_DIR, "synth_device_raw_1hz_motion_fall.csv")
    df, res = ingester.load(filepath)
    assert df is not None, "1Hz CSV failed to load"
    assert df.attrs["file_type"] == "device_1hz"
    assert res.rows_loaded > 100000, f"Expected 100k+ rows, got {res.rows_loaded}"
    assert "patient_id" in df.columns, "Missing patient_id after rename"
    assert any("Loaded in" in w for w in res.warnings), "Missing chunk loading warning"
    print(f"PASS: 1Hz chunked ({res.rows_loaded} rows)")


def test_pdf_nursing():
    ingester = DataIngester()
    filepath = os.path.join(SPLIT_DIR, "clinic_4_nursing.pdf")
    df, res = ingester.load(filepath)
    assert df is not None, "PDF failed to load"
    assert df.attrs["file_type"] == "nursing"
    assert "case_id" in df.columns, "Missing case_id"
    assert "nursing_note_free_text" in df.columns, "Missing nursing note"
    assert res.rows_loaded >= 10, f"Expected 10+ rows, got {res.rows_loaded}"
    print(f"PASS: PDF nursing ({res.rows_loaded} rows)")


def test_split_all_types():
    ingester = DataIngester()
    split_results = ingester.ingest_directory(SPLIT_DIR)
    types_found = set()
    for fname, (df, res) in split_results.items():
        if df is not None:
            ftype = df.attrs.get("file_type", "unknown")
            types_found.add(ftype)

    expected_types = {"labs", "icd10_ops", "device_motion", "device_1hz",
                      "medication", "nursing", "epaAC_pivot", "epaAC_sap",
                      "epaAC_german"}
    missing = expected_types - types_found
    assert not missing, f"Missing types in split: {missing}"
    print(f"PASS: split directory ({len(split_results)} files, types: {sorted(types_found)})")


def test_clean_files():
    ingester = DataIngester()
    results = ingester.ingest_directory(CLEAN_DIR)
    assert len(results) == 12, f"Expected 12 clean files, got {len(results)}"
    for fname, (df, res) in results.items():
        assert df is not None, f"{fname}: failed to load"
        assert res.rows_loaded > 0, f"{fname}: 0 rows"
    print(f"PASS: clean directory ({len(results)} files)")


def test_column_normalization():
    ingester = DataIngester()
    # Dirty labs should have standard column names
    df, _ = ingester.load(os.path.join(DIRTY_DIR, "synth_labs.csv"))
    assert "case_id" in df.columns, "Dirty labs missing 'case_id' after rename"
    assert "sodium_mmol_L" in df.columns, "Dirty labs missing 'sodium_mmol_L'"

    # Dirty medication should be renamed
    df, _ = ingester.load(os.path.join(DIRTY_DIR, "synth_medication_raw_inpatient.csv"))
    assert "medication_name" in df.columns, "Dirty meds missing 'medication_name'"
    assert "record_type" in df.columns, "Dirty meds missing 'record_type'"

    print("PASS: column normalization")


def test_encoding_detection():
    ingester = DataIngester()
    # epaAC-Data-3 should be detected as Latin-1
    df, res = ingester.load(os.path.join(DIRTY_DIR, "epaAC-Data-3.csv"))
    assert res.encoding_detected.lower() in ("iso-8859-1", "latin-1", "latin1"), (
        f"Expected Latin-1 encoding, got {res.encoding_detected}"
    )
    print(f"PASS: encoding detection ({res.encoding_detected})")


if __name__ == "__main__":
    test_iid_sid_item()
    test_dirty_base_files()
    test_dirty_xlsx_files()
    test_1hz_chunked()
    test_pdf_nursing()
    test_split_all_types()
    test_clean_files()
    test_column_normalization()
    test_encoding_detection()
    print("\n=== ALL TESTS PASSED ===")
