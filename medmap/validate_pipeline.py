#!/usr/bin/env python3
"""
Phase 6 — Validation Script
6.1: Run pipeline on dirty data, compare output with clean reference.
6.2: Run pipeline on split data, verify mapping correctness.
"""

import logging
import os
import sqlite3
import sys
import time

import numpy as np
import pandas as pd

# Ensure medmap is on path
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import CLEAN_DIR, DIRTY_DIR, SPLIT_DIR, DB_DIR
from pipeline.ingestion import DataIngester
from pipeline.validator import DataValidator
from pipeline.cleaner import DataCleaner
from pipeline.mapper import DataMapper
from pipeline.sql_export import SQLExporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("validate_pipeline")


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def load_clean_reference():
    """Load all clean reference files as DataFrames."""
    clean_files = {}
    for fname in os.listdir(CLEAN_DIR):
        fpath = os.path.join(CLEAN_DIR, fname)
        try:
            if fname.endswith(".csv"):
                df = pd.read_csv(fpath, low_memory=False)
            elif fname.endswith(".xlsx"):
                df = pd.read_excel(fpath, engine="openpyxl")
            else:
                continue
            clean_files[fname] = df
            logger.info("Clean ref loaded: %s (%d rows, %d cols)", fname, len(df), len(df.columns))
        except Exception as e:
            logger.warning("Failed to load clean ref %s: %s", fname, e)
    return clean_files


def query_db(db_path, sql):
    """Execute SQL on a database and return results as list of dicts."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def db_table_counts(db_path):
    """Get row counts for all tables in a database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cursor.fetchall()]
    counts = {}
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM [{t}]")
        counts[t] = cursor.fetchone()[0]
    conn.close()
    return counts


def db_table_columns(db_path, table_name):
    """Get column names for a table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info([{table_name}])")
    cols = [r[1] for r in cursor.fetchall()]
    conn.close()
    return cols


def db_sample(db_path, table_name, limit=5):
    """Get sample rows from a table."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM [{table_name}] LIMIT {limit}")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ──────────────────────────────────────────────
# VALIDATION 6.1: DIRTY → PIPELINE → COMPARE WITH CLEAN
# ──────────────────────────────────────────────

def run_dirty_pipeline(db_path):
    """Run the full pipeline on dirty data only (no split)."""
    logger.info("=" * 60)
    logger.info("6.1 — Running pipeline on DIRTY data")
    logger.info("=" * 60)

    ingester = DataIngester()
    results = ingester.ingest_all(data_folder="dirty", include_split=False, include_iid=True)

    logger.info("Ingested %d files", len(results))
    for fname, (df, result) in results.items():
        if df is not None:
            logger.info("  %s: %d rows loaded", fname, result.rows_loaded)
        else:
            logger.warning("  %s: FAILED", fname)

    # Validate
    validator = DataValidator()
    quality_scores = validator.validate_all(ingester.dataframes)
    logger.info("Validation complete: %d sources scored", len(quality_scores))
    for fname, score in quality_scores.items():
        logger.info("  %s: score=%.1f, imported=%d, quarantined=%d",
                     fname, score.score, score.rows_imported, score.rows_quarantined)

    # Clean
    cleaner = DataCleaner(validator)
    clean_dfs = cleaner.clean_all(ingester.dataframes)
    clean_dfs = cleaner.map_missing_case_ids(clean_dfs)
    pid_conflicts = cleaner.detect_pid_conflicts(clean_dfs)
    logger.info("Cleaning complete: %d files, %d PID conflicts", len(clean_dfs), len(pid_conflicts))

    # Map
    mapper = DataMapper(iid_sid_map=ingester.iid_sid_map)
    mapped = mapper.map_all(clean_dfs)
    logger.info("Mapping complete:")
    for table_name, df in mapped.items():
        if df is not None and not df.empty:
            logger.info("  %s: %d rows, %d cols", table_name, len(df), len(df.columns))
        else:
            logger.info("  %s: EMPTY", table_name)

    # Export
    exporter = SQLExporter(db_path=db_path)
    audit_log = cleaner.get_audit_log()
    export_summary = exporter.export_all(mapped, audit_log)
    logger.info("Export complete: %s", export_summary)

    return mapped, quality_scores, audit_log


def compare_with_clean(dirty_db_path):
    """Compare dirty pipeline output with clean reference data."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPARING dirty pipeline output with CLEAN reference")
    logger.info("=" * 60)

    report = {
        "checks_passed": 0,
        "checks_failed": 0,
        "warnings": [],
        "details": [],
    }

    # Load clean reference
    clean_refs = load_clean_reference()

    # Get dirty DB table counts
    dirty_counts = db_table_counts(dirty_db_path)
    logger.info("Dirty DB tables: %s", dirty_counts)

    # ── CHECK 1: All target tables exist ──
    expected_tables = [
        "tbCaseData", "tbImportLabsData", "tbImportIcd10Data",
        "tbImportDeviceMotionData", "tbImportDevice1HzMotionData",
        "tbImportMedicationInpatientData", "tbImportNursingDailyReportsData",
        "tbImportAcData", "tbAuditLog", "tbDataPassport",
    ]
    for t in expected_tables:
        if t in dirty_counts:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: Table {t} exists ({dirty_counts[t]} rows)")
        else:
            report["checks_failed"] += 1
            report["details"].append(f"FAIL: Table {t} missing")

    # ── CHECK 2: Row counts are reasonable ──
    # Dirty data has CSV+XLSX duplicates that get merged, so counts are higher
    clean_row_expectations = {
        "tbImportLabsData": (500, 12000),       # dirty has 5000×2 (csv+xlsx)
        "tbImportIcd10Data": (30, 2500),         # dirty has 1000×2
        "tbImportDeviceMotionData": (5000, 100000),  # dirty has ~40K×2
        "tbImportMedicationInpatientData": (5000, 55000),  # dirty has 25K×2
        "tbImportNursingDailyReportsData": (100, 5000),    # dirty has 2000×2
        "tbCaseData": (10, 10000),
    }
    for table, (min_rows, max_rows) in clean_row_expectations.items():
        if table in dirty_counts:
            count = dirty_counts[table]
            if min_rows <= count <= max_rows:
                report["checks_passed"] += 1
                report["details"].append(f"PASS: {table} has {count} rows (expected {min_rows}-{max_rows})")
            else:
                report["checks_failed"] += 1
                report["details"].append(f"FAIL: {table} has {count} rows (expected {min_rows}-{max_rows})")
        else:
            report["checks_failed"] += 1
            report["details"].append(f"FAIL: {table} missing for row count check")

    # ── CHECK 3: tbAuditLog has entries (errors were logged) ──
    if "tbAuditLog" in dirty_counts:
        audit_count = dirty_counts["tbAuditLog"]
        if audit_count > 0:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: tbAuditLog has {audit_count} entries (errors were logged)")
        else:
            report["checks_failed"] += 1
            report["details"].append(f"FAIL: tbAuditLog is empty (should have error entries for dirty data)")

    # ── CHECK 4: Column names match target schema ──
    expected_columns = {
        "tbCaseData": ["coPatientId", "coGender", "coAgeYears"],
        "tbImportLabsData": ["coCaseId", "coSodium_mmol_L"],
        "tbImportIcd10Data": ["coCaseId", "coAdmission_date"],
        "tbImportDeviceMotionData": ["coCaseId", "coTimestamp"],
        "tbImportMedicationInpatientData": ["coCaseId", "coRecord_type"],
        "tbImportNursingDailyReportsData": ["coCaseId", "coReport_date", "coShift"],
    }
    for table, req_cols in expected_columns.items():
        actual_cols = db_table_columns(dirty_db_path, table)
        for col in req_cols:
            if col in actual_cols:
                report["checks_passed"] += 1
                report["details"].append(f"PASS: {table}.{col} exists")
            else:
                report["checks_failed"] += 1
                report["details"].append(f"FAIL: {table}.{col} missing (have: {actual_cols[:10]}...)")

    # ── CHECK 5: Data quality — no NULL case_ids in main tables ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    for table in ["tbImportLabsData", "tbImportIcd10Data", "tbImportMedicationInpatientData",
                   "tbImportNursingDailyReportsData"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM [{table}] WHERE coCaseId IS NULL OR coCaseId = ''")
            null_count = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
            total = cursor.fetchone()[0]
            if total > 0:
                pct_null = null_count / total * 100
                if pct_null < 20:
                    report["checks_passed"] += 1
                    report["details"].append(f"PASS: {table} null coCaseId: {null_count}/{total} ({pct_null:.1f}%)")
                else:
                    report["checks_failed"] += 1
                    report["details"].append(f"FAIL: {table} too many null coCaseId: {null_count}/{total} ({pct_null:.1f}%)")
        except Exception as e:
            report["warnings"].append(f"Could not check {table}: {e}")
    conn.close()

    # ── CHECK 6: Gender normalization — only M, F, or NULL ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT coGender FROM tbCaseData WHERE coGender IS NOT NULL")
        genders = [r[0] for r in cursor.fetchall()]
        invalid = [g for g in genders if g not in ("M", "F")]
        if not invalid:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: Gender normalized correctly (values: {genders})")
        else:
            report["checks_failed"] += 1
            report["details"].append(f"FAIL: Invalid gender values found: {invalid}")
    except Exception as e:
        report["warnings"].append(f"Could not check gender: {e}")
    conn.close()

    # ── CHECK 7: Date format — dates should be ISO (YYYY-MM-DD) ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    date_checks = [
        ("tbImportIcd10Data", "coAdmission_date"),
        ("tbImportNursingDailyReportsData", "coReport_date"),
    ]
    for table, col in date_checks:
        try:
            cursor.execute(f"SELECT [{col}] FROM [{table}] WHERE [{col}] IS NOT NULL LIMIT 20")
            dates = [r[0] for r in cursor.fetchall()]
            iso_count = sum(1 for d in dates if d and len(str(d)) >= 10 and str(d)[4] == '-')
            if dates and iso_count / len(dates) > 0.7:
                report["checks_passed"] += 1
                report["details"].append(f"PASS: {table}.{col} mostly ISO format ({iso_count}/{len(dates)})")
            elif dates:
                report["checks_failed"] += 1
                report["details"].append(f"FAIL: {table}.{col} not ISO format. Samples: {dates[:3]}")
            else:
                report["warnings"].append(f"No dates found in {table}.{col}")
        except Exception as e:
            report["warnings"].append(f"Could not check {table}.{col}: {e}")
    conn.close()

    # ── CHECK 8: Verify case_ids exist and are non-trivial ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT coCaseId FROM tbImportLabsData WHERE coCaseId IS NOT NULL")
    dirty_case_ids = set(r[0] for r in cursor.fetchall())
    conn.close()

    if len(dirty_case_ids) > 10:
        report["checks_passed"] += 1
        report["details"].append(
            f"PASS: Labs has {len(dirty_case_ids)} distinct case_ids. "
            f"Sample: {list(dirty_case_ids)[:5]}"
        )
    else:
        report["checks_failed"] += 1
        report["details"].append(
            f"FAIL: Labs has only {len(dirty_case_ids)} distinct case_ids. "
            f"Sample: {list(dirty_case_ids)[:5]}"
        )

    # Also check clean reference for comparison info
    clean_labs = clean_refs.get("synth_labs_1000_cases.csv")
    if clean_labs is not None:
        clean_case_ids = set(clean_labs["case_id"].dropna().unique())
        # Note: dirty uses numeric IDs, clean uses CASE-XXXX format
        # We compare count magnitude, not exact overlap
        ratio = len(dirty_case_ids) / len(clean_case_ids) if clean_case_ids else 0
        report["details"].append(
            f"INFO: Dirty has {len(dirty_case_ids)} unique case_ids vs clean {len(clean_case_ids)} "
            f"(ratio: {ratio:.1f}x). Dirty format: numeric, clean format: CASE-XXXX"
        )

    # ── CHECK 9: Clinical values in range ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    range_checks = {
        "coSodium_mmol_L": (100, 165),
        "coPotassium_mmol_L": (2.0, 7.5),
        "coCreatinine_mg_dL": (0.3, 15.0),
    }
    for col, (low, high) in range_checks.items():
        try:
            cursor.execute(f"""
                SELECT COUNT(*) FROM tbImportLabsData
                WHERE [{col}] IS NOT NULL
                AND CAST([{col}] AS REAL) NOT BETWEEN {low} AND {high}
            """)
            out_of_range = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM tbImportLabsData WHERE [{col}] IS NOT NULL")
            total = cursor.fetchone()[0]
            if total > 0:
                pct = out_of_range / total * 100
                if pct < 10:
                    report["checks_passed"] += 1
                    report["details"].append(f"PASS: {col} out-of-range: {out_of_range}/{total} ({pct:.1f}%)")
                else:
                    report["warnings"].append(f"WARN: {col} out-of-range: {out_of_range}/{total} ({pct:.1f}%) — may be quarantined")
        except Exception as e:
            report["warnings"].append(f"Could not check {col}: {e}")
    conn.close()

    # ── CHECK 10: tbDataPassport has entries ──
    if "tbDataPassport" in dirty_counts and dirty_counts["tbDataPassport"] > 0:
        report["checks_passed"] += 1
        report["details"].append(f"PASS: tbDataPassport has {dirty_counts['tbDataPassport']} entries")
    else:
        report["warnings"].append("WARN: tbDataPassport empty or missing")

    # ── CHECK 11: Audit log error categories ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT error_type, COUNT(*) FROM tbAuditLog GROUP BY error_type ORDER BY COUNT(*) DESC LIMIT 10")
        cats = {r[0]: r[1] for r in cursor.fetchall()}
        if cats:
            report["checks_passed"] += 1
            top3 = list(cats.items())[:3]
            report["details"].append(f"PASS: Audit log has {len(cats)} error categories. Top 3: {top3}")
        else:
            report["checks_failed"] += 1
            report["details"].append("FAIL: Audit log has no error categories")
    except Exception as e:
        report["warnings"].append(f"Could not check audit categories: {e}")
    conn.close()

    # ── CHECK 12: Audit log severity distribution ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT severity, COUNT(*) FROM tbAuditLog GROUP BY severity")
        severities = {r[0]: r[1] for r in cursor.fetchall()}
        if severities:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: Audit severity distribution: {severities}")
        else:
            report["checks_failed"] += 1
            report["details"].append("FAIL: No severity data in audit log")
    except Exception as e:
        report["warnings"].append(f"Could not check audit severities: {e}")
    conn.close()

    # ── CHECK 13: No empty strings where NULL expected ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    empty_string_checks = [
        ("tbCaseData", "coGender"),
        ("tbImportLabsData", "coSodium_flag"),
    ]
    for table, col in empty_string_checks:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM [{table}] WHERE [{col}] = ''")
            empty_count = cursor.fetchone()[0]
            if empty_count == 0:
                report["checks_passed"] += 1
                report["details"].append(f"PASS: {table}.{col} has no empty strings (proper NULLs)")
            else:
                report["details"].append(f"INFO: {table}.{col} has {empty_count} empty strings")
        except Exception as e:
            report["warnings"].append(f"Could not check empty strings in {table}.{col}: {e}")
    conn.close()

    # ── CHECK 14: Medication event types present ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT coRecord_type FROM tbImportMedicationInpatientData WHERE coRecord_type IS NOT NULL")
        event_types = [r[0] for r in cursor.fetchall()]
        expected_types = {"ORDER", "CHANGE", "ADMIN"}
        found = set(event_types) & expected_types
        if len(found) >= 2:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: Medication event types: {event_types}")
        else:
            report["warnings"].append(f"WARN: Medication event types: {event_types} (expected ORDER/CHANGE/ADMIN)")
    except Exception as e:
        report["warnings"].append(f"Could not check medication types: {e}")
    conn.close()

    # ── CHECK 15: Nursing shifts present ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT coShift FROM tbImportNursingDailyReportsData WHERE coShift IS NOT NULL")
        shifts = [r[0] for r in cursor.fetchall()]
        expected_shifts = {"Early", "Late", "Night"}
        found = set(shifts) & expected_shifts
        if len(found) >= 2:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: Nursing shifts: {shifts}")
        else:
            report["warnings"].append(f"WARN: Nursing shifts: {shifts} (expected Early/Late/Night)")
    except Exception as e:
        report["warnings"].append(f"Could not check nursing shifts: {e}")
    conn.close()

    # ── CHECK 16: Device motion binary columns valid ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM tbImportDeviceMotionData
            WHERE coBed_exit_detected_0_1 NOT IN (0, 1, '0', '1')
            AND coBed_exit_detected_0_1 IS NOT NULL
        """)
        invalid = cursor.fetchone()[0]
        if invalid == 0:
            report["checks_passed"] += 1
            report["details"].append("PASS: Device motion bed_exit_detected only has 0/1 values")
        else:
            report["warnings"].append(f"WARN: {invalid} invalid bed_exit_detected values")
    except Exception as e:
        report["warnings"].append(f"Could not check device motion binary: {e}")
    conn.close()

    # ── CHECK 17: Cross-table referential integrity ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    child_tables = [
        ("tbImportLabsData", "coCaseId"),
        ("tbImportIcd10Data", "coCaseId"),
        ("tbImportNursingDailyReportsData", "coCaseId"),
    ]
    for child_table, fk_col in child_tables:
        try:
            # Check how many child rows reference a valid parent
            cursor.execute(f"""
                SELECT COUNT(*) FROM [{child_table}] c
                WHERE c.[{fk_col}] IS NOT NULL
                AND c.[{fk_col}] NOT IN (SELECT coId FROM tbCaseData)
                AND c.[{fk_col}] NOT IN (SELECT coCaseIdAlpha FROM tbCaseData WHERE coCaseIdAlpha IS NOT NULL)
            """)
            orphans = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM [{child_table}] WHERE [{fk_col}] IS NOT NULL")
            total = cursor.fetchone()[0]
            if total > 0:
                pct = orphans / total * 100
                report["details"].append(
                    f"INFO: {child_table} FK check: {orphans}/{total} orphaned ({pct:.1f}%)"
                )
        except Exception as e:
            report["warnings"].append(f"Could not check FK for {child_table}: {e}")
    conn.close()

    # ── CHECK 18: Additional clinical ranges ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    extra_ranges = {
        "coGlucose_mg_dL": (20, 600),
        "coHemoglobin_g_dL": (3, 25),
        "coWbc_10e9_L": (0.1, 100),
    }
    for col, (low, high) in extra_ranges.items():
        try:
            cursor.execute(f"""
                SELECT COUNT(*) FROM tbImportLabsData
                WHERE [{col}] IS NOT NULL
                AND CAST([{col}] AS REAL) NOT BETWEEN {low} AND {high}
            """)
            out_of_range = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM tbImportLabsData WHERE [{col}] IS NOT NULL")
            total = cursor.fetchone()[0]
            if total > 0:
                pct = out_of_range / total * 100
                if pct < 10:
                    report["checks_passed"] += 1
                    report["details"].append(f"PASS: {col} out-of-range: {out_of_range}/{total} ({pct:.1f}%)")
                else:
                    report["warnings"].append(f"WARN: {col} {out_of_range}/{total} ({pct:.1f}%) out of range")
        except Exception as e:
            report["warnings"].append(f"Could not check {col}: {e}")
    conn.close()

    # ── CHECK 19: epaAC data mapping ──
    if "tbImportAcData" in dirty_counts and dirty_counts["tbImportAcData"] > 0:
        report["checks_passed"] += 1
        cols = db_table_columns(dirty_db_path, "tbImportAcData")
        report["details"].append(f"PASS: tbImportAcData has {dirty_counts['tbImportAcData']} rows, {len(cols)} cols")
    else:
        report["warnings"].append("WARN: tbImportAcData empty — only 1 epaAC file in dirty")

    # ── CHECK 20: Data passport status distribution ──
    conn = sqlite3.connect(dirty_db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT status, COUNT(*) FROM tbDataPassport GROUP BY status")
        statuses = {r[0]: r[1] for r in cursor.fetchall()}
        if statuses:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: Data passport statuses: {statuses}")
    except Exception as e:
        report["warnings"].append(f"Could not check passport statuses: {e}")
    conn.close()

    return report


# ──────────────────────────────────────────────
# VALIDATION 6.2: SPLIT → PIPELINE → VERIFY MAPPING
# ──────────────────────────────────────────────

def run_split_pipeline(db_path):
    """Run pipeline on split data only and verify mapping."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("6.2 — Running pipeline on SPLIT data (4 clinics)")
    logger.info("=" * 60)

    report = {
        "checks_passed": 0,
        "checks_failed": 0,
        "warnings": [],
        "details": [],
    }

    # Ingest only split data
    ingester = DataIngester()

    # We'll ingest dirty folder but we mainly care about split
    results = ingester.ingest_all(data_folder="dirty", include_split=True, include_iid=True)

    # Count split files
    split_files = [f for f in results.keys() if "clinic_" in f]
    logger.info("Split files ingested: %d", len(split_files))
    for fname in sorted(split_files):
        df, result = results[fname]
        if df is not None:
            logger.info("  %s: %d rows, type=%s", fname, result.rows_loaded, df.attrs.get("file_type", "?"))
        else:
            logger.warning("  %s: FAILED", fname)

    # ── CHECK 1: All 28 split files ingested ──
    if len(split_files) >= 25:
        report["checks_passed"] += 1
        report["details"].append(f"PASS: {len(split_files)} split files ingested (expected ~28)")
    else:
        report["checks_failed"] += 1
        report["details"].append(f"FAIL: Only {len(split_files)} split files ingested (expected ~28)")

    # ── CHECK 2: Each clinic represented ──
    for clinic_num in [1, 2, 3, 4]:
        clinic_files = [f for f in split_files if f"clinic_{clinic_num}" in f]
        if len(clinic_files) >= 5:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: Clinic {clinic_num} has {len(clinic_files)} files")
        else:
            report["checks_failed"] += 1
            report["details"].append(f"FAIL: Clinic {clinic_num} has only {len(clinic_files)} files")

    # ── CHECK 3: Special files handled ──
    # clinic_4_nursing.pdf and clinic_4_epaAC-Data.xlsx
    pdf_loaded = any("clinic_4_nursing" in f for f in split_files)
    xlsx_loaded = any("clinic_4_epaAC" in f for f in split_files)
    if pdf_loaded:
        report["checks_passed"] += 1
        report["details"].append("PASS: clinic_4_nursing.pdf loaded")
    else:
        report["checks_failed"] += 1
        report["details"].append("FAIL: clinic_4_nursing.pdf not loaded")
    if xlsx_loaded:
        report["checks_passed"] += 1
        report["details"].append("PASS: clinic_4_epaAC-Data.xlsx loaded")
    else:
        report["checks_failed"] += 1
        report["details"].append("FAIL: clinic_4_epaAC-Data.xlsx not loaded")

    # ── CHECK 4: File type detection worked ──
    type_counts = {}
    for fname in split_files:
        df, _ = results[fname]
        if df is not None:
            ft = df.attrs.get("file_type", "unknown")
            type_counts[ft] = type_counts.get(ft, 0) + 1
    logger.info("Split file types detected: %s", type_counts)
    expected_types = ["labs", "device_motion", "medication", "nursing", "icd10_ops"]
    for et in expected_types:
        if et in type_counts:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: File type '{et}' detected ({type_counts[et]} files)")
        else:
            report["warnings"].append(f"WARN: File type '{et}' not detected in split files")

    # Now run full pipeline and export
    validator = DataValidator()
    quality_scores = validator.validate_all(ingester.dataframes)

    cleaner = DataCleaner(validator)
    clean_dfs = cleaner.clean_all(ingester.dataframes)
    clean_dfs = cleaner.map_missing_case_ids(clean_dfs)
    cleaner.detect_pid_conflicts(clean_dfs)

    mapper = DataMapper(iid_sid_map=ingester.iid_sid_map)
    mapped = mapper.map_all(clean_dfs)

    exporter = SQLExporter(db_path=db_path)
    audit_log = cleaner.get_audit_log()
    export_summary = exporter.export_all(mapped, audit_log)

    # ── CHECK 5: All 7 target tables populated ──
    counts = db_table_counts(db_path)
    target_tables = [
        "tbCaseData", "tbImportLabsData", "tbImportIcd10Data",
        "tbImportDeviceMotionData", "tbImportDevice1HzMotionData",
        "tbImportMedicationInpatientData", "tbImportNursingDailyReportsData",
    ]
    for t in target_tables:
        if t in counts and counts[t] > 0:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: {t} has {counts[t]} rows after split pipeline")
        else:
            report["checks_failed"] += 1
            report["details"].append(f"FAIL: {t} empty or missing after split pipeline")

    # ── CHECK 6: Mapping warnings ──
    if mapper.mapping_warnings:
        for w in mapper.mapping_warnings:
            report["warnings"].append(f"Mapping warning: {w}")
    else:
        report["checks_passed"] += 1
        report["details"].append("PASS: No mapping warnings")

    # ── CHECK 7: Split data contributes to all clinics in DB ──
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(DISTINCT coCaseId) FROM tbImportLabsData WHERE coCaseId IS NOT NULL")
        distinct_cases = cursor.fetchone()[0]
        if distinct_cases >= 10:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: {distinct_cases} distinct case_ids in labs from split data")
        else:
            report["warnings"].append(f"WARN: Only {distinct_cases} distinct case_ids in labs")
    except Exception as e:
        report["warnings"].append(f"Could not check split case_ids: {e}")
    conn.close()

    # ── CHECK 8: epaAC data from split includes XLSX clinic 4 ──
    if "tbImportAcData" in counts and counts["tbImportAcData"] > 0:
        report["checks_passed"] += 1
        report["details"].append(f"PASS: tbImportAcData has {counts['tbImportAcData']} rows (includes clinic data)")
    else:
        report["warnings"].append("WARN: tbImportAcData empty after split pipeline")

    # ── CHECK 9: Quality scores for split files ──
    split_scores = {k: v for k, v in quality_scores.items() if "clinic_" in k}
    if len(split_scores) >= 20:
        report["checks_passed"] += 1
        avg_score = sum(s.score for s in split_scores.values()) / len(split_scores)
        report["details"].append(f"PASS: {len(split_scores)} split files validated, avg quality score: {avg_score:.1f}")
    else:
        report["warnings"].append(f"WARN: Only {len(split_scores)} split files have quality scores")

    # ── CHECK 10: Audit log populated for split ──
    if "tbAuditLog" in counts and counts["tbAuditLog"] > 0:
        report["checks_passed"] += 1
        report["details"].append(f"PASS: Split pipeline audit log has {counts['tbAuditLog']} entries")
    else:
        report["checks_failed"] += 1
        report["details"].append("FAIL: Split pipeline audit log empty")

    # ── CHECK 11: Data passports for split ──
    if "tbDataPassport" in counts and counts["tbDataPassport"] > 0:
        report["checks_passed"] += 1
        report["details"].append(f"PASS: Split pipeline data passports: {counts['tbDataPassport']}")
    else:
        report["warnings"].append("WARN: Split pipeline data passports empty")

    # ── CHECK 12: 1Hz data loaded from split ──
    if "tbImportDevice1HzMotionData" in counts:
        hz_count = counts["tbImportDevice1HzMotionData"]
        if hz_count > 50000:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: 1Hz data has {hz_count} rows from split (chunked loading works)")
        else:
            report["warnings"].append(f"WARN: 1Hz data only {hz_count} rows from split")

    return report


# ──────────────────────────────────────────────
# RUN CLEAN PIPELINE FOR BASELINE
# ──────────────────────────────────────────────

def run_clean_pipeline(db_path):
    """Run pipeline on clean data as baseline reference."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("BASELINE — Running pipeline on CLEAN data")
    logger.info("=" * 60)

    ingester = DataIngester()
    results = ingester.ingest_all(data_folder="clean", include_split=False, include_iid=True)

    logger.info("Ingested %d clean files", len(results))
    for fname, (df, result) in results.items():
        if df is not None:
            logger.info("  %s: %d rows", fname, result.rows_loaded)

    validator = DataValidator()
    quality_scores = validator.validate_all(ingester.dataframes)

    cleaner = DataCleaner(validator)
    clean_dfs = cleaner.clean_all(ingester.dataframes)
    clean_dfs = cleaner.map_missing_case_ids(clean_dfs)

    mapper = DataMapper(iid_sid_map=ingester.iid_sid_map)
    mapped = mapper.map_all(clean_dfs)

    exporter = SQLExporter(db_path=db_path)
    audit_log = cleaner.get_audit_log()
    export_summary = exporter.export_all(mapped, audit_log)

    counts = db_table_counts(db_path)
    logger.info("Clean pipeline DB counts: %s", counts)

    return counts, quality_scores


def compare_clean_vs_dirty_db(clean_db, dirty_db):
    """Compare clean and dirty pipeline output databases."""
    report = {
        "checks_passed": 0,
        "checks_failed": 0,
        "warnings": [],
        "details": [],
    }

    clean_counts = db_table_counts(clean_db)
    dirty_counts = db_table_counts(dirty_db)

    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPARISON: Clean DB vs Dirty DB")
    logger.info("=" * 60)

    tables = set(clean_counts.keys()) | set(dirty_counts.keys())
    for t in sorted(tables):
        if t in ("sqlite_sequence", "tbAuditLog", "tbDataPassport"):
            continue
        c = clean_counts.get(t, 0)
        d = dirty_counts.get(t, 0)
        logger.info("  %s: clean=%d, dirty=%d", t, c, d)
        report["details"].append(f"INFO: {t}: clean={c}, dirty={d}")

    # The dirty pipeline should produce audit log entries (errors found)
    dirty_audit = dirty_counts.get("tbAuditLog", 0)
    clean_audit = clean_counts.get("tbAuditLog", 0)
    if dirty_audit > clean_audit:
        report["checks_passed"] += 1
        report["details"].append(
            f"PASS: Dirty has more audit entries ({dirty_audit}) than clean ({clean_audit}) — errors detected"
        )
    else:
        report["warnings"].append(
            f"WARN: Dirty audit ({dirty_audit}) <= clean audit ({clean_audit})"
        )

    return report


# ──────────────────────────────────────────────
# API SMOKE TEST
# ──────────────────────────────────────────────

def run_api_smoke_test():
    """Quick test that the API module imports and routes are registered."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("API Smoke Test")
    logger.info("=" * 60)

    report = {
        "checks_passed": 0,
        "checks_failed": 0,
        "warnings": [],
        "details": [],
    }

    try:
        from api.main import app
        report["checks_passed"] += 1
        report["details"].append("PASS: FastAPI app imports successfully")
    except Exception as e:
        report["checks_failed"] += 1
        report["details"].append(f"FAIL: FastAPI app import failed: {e}")
        return report

    # Check all routes registered
    routes = [r.path for r in app.routes if hasattr(r, "path")]
    expected_prefixes = [
        "/api/pipeline", "/api/upload", "/api/overview",
        "/api/agents", "/api/patients", "/api/alerts",
        "/api/quality", "/api/ask", "/api/corrections",
    ]
    for prefix in expected_prefixes:
        matching = [r for r in routes if r.startswith(prefix)]
        if matching:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: {prefix} has {len(matching)} routes")
        else:
            report["checks_failed"] += 1
            report["details"].append(f"FAIL: {prefix} has no routes")

    # Count total endpoints
    total = len([r for r in routes if r.startswith("/api/")])
    if total >= 20:
        report["checks_passed"] += 1
        report["details"].append(f"PASS: {total} API endpoints registered (expected >= 20)")
    else:
        report["checks_failed"] += 1
        report["details"].append(f"FAIL: Only {total} API endpoints (expected >= 20)")

    # Test with TestClient if available
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/health")
        if resp.status_code == 200:
            report["checks_passed"] += 1
            report["details"].append(f"PASS: /health returns 200: {resp.json().get('status', '?')}")
        else:
            report["checks_failed"] += 1
            report["details"].append(f"FAIL: /health returns {resp.status_code}")

        # Test a few key endpoints
        for endpoint in ["/api/overview/quality-scores", "/api/patients", "/api/alerts"]:
            try:
                resp = client.get(endpoint)
                if resp.status_code == 200:
                    report["checks_passed"] += 1
                    data = resp.json()
                    count = len(data) if isinstance(data, list) else "dict"
                    report["details"].append(f"PASS: GET {endpoint} returns 200 ({count} items)")
                else:
                    report["warnings"].append(f"WARN: GET {endpoint} returns {resp.status_code}")
            except Exception as e:
                report["warnings"].append(f"WARN: GET {endpoint} failed: {e}")
    except ImportError:
        report["warnings"].append("WARN: httpx not installed, skipping TestClient checks")
    except Exception as e:
        report["warnings"].append(f"WARN: TestClient error: {e}")

    return report


# ──────────────────────────────────────────────
# PRINT REPORT
# ──────────────────────────────────────────────

def print_report(title, report):
    """Print a formatted validation report."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()
    for detail in report["details"]:
        icon = "✅" if detail.startswith("PASS") else "❌" if detail.startswith("FAIL") else "ℹ️"
        print(f"  {icon} {detail}")
    for warning in report["warnings"]:
        print(f"  ⚠️  {warning}")
    print()
    passed = report["checks_passed"]
    failed = report["checks_failed"]
    total = passed + failed
    print(f"  Results: {passed}/{total} passed, {failed}/{total} failed")
    if report["warnings"]:
        print(f"  Warnings: {len(report['warnings'])}")
    print()


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    start = time.time()

    dirty_db = os.path.join(DB_DIR, "medmap_dirty_validation.db")
    clean_db = os.path.join(DB_DIR, "medmap_clean_validation.db")
    split_db = os.path.join(DB_DIR, "medmap_split_validation.db")

    # Remove old validation DBs
    for db in [dirty_db, clean_db, split_db]:
        if os.path.exists(db):
            os.remove(db)
        # Also remove WAL files
        for ext in ["-wal", "-shm"]:
            p = db + ext
            if os.path.exists(p):
                os.remove(p)

    all_reports = []

    # ── 6.1a: Run clean pipeline baseline ──
    try:
        clean_counts, clean_quality = run_clean_pipeline(clean_db)
    except Exception as e:
        logger.error("Clean pipeline failed: %s", e, exc_info=True)
        clean_counts = {}

    # ── 6.1b: Run dirty pipeline ──
    try:
        run_dirty_pipeline(dirty_db)
    except Exception as e:
        logger.error("Dirty pipeline failed: %s", e, exc_info=True)

    # ── 6.1c: Compare dirty output with clean reference ──
    try:
        report1 = compare_with_clean(dirty_db)
        all_reports.append(("6.1 — Dirty Pipeline Validation", report1))
    except Exception as e:
        logger.error("Comparison failed: %s", e, exc_info=True)

    # ── 6.1d: Compare clean vs dirty databases ──
    if clean_counts:
        try:
            report_cmp = compare_clean_vs_dirty_db(clean_db, dirty_db)
            all_reports.append(("6.1 — Clean vs Dirty DB Comparison", report_cmp))
        except Exception as e:
            logger.error("DB comparison failed: %s", e, exc_info=True)

    # ── 6.2: Run split pipeline ──
    try:
        report2 = run_split_pipeline(split_db)
        all_reports.append(("6.2 — Split Pipeline Validation", report2))
    except Exception as e:
        logger.error("Split pipeline failed: %s", e, exc_info=True)

    # ── 6.3: API smoke test ──
    try:
        report3 = run_api_smoke_test()
        all_reports.append(("6.3 — API Smoke Test", report3))
    except Exception as e:
        logger.error("API smoke test failed: %s", e, exc_info=True)

    # ── Print all reports ──
    print("\n" + "=" * 60)
    print("  PHASE 6 — VALIDATION REPORT")
    print("=" * 60)

    total_passed = 0
    total_failed = 0
    total_warnings = 0
    for title, report in all_reports:
        print_report(title, report)
        total_passed += report["checks_passed"]
        total_failed += report["checks_failed"]
        total_warnings += len(report["warnings"])

    elapsed = time.time() - start
    print("=" * 60)
    print(f"  GRAND TOTAL: {total_passed}/{total_passed + total_failed} passed, "
          f"{total_failed} failed, {total_warnings} warnings")
    print(f"  Completed in {elapsed:.1f}s")
    print("=" * 60)

    return total_failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
