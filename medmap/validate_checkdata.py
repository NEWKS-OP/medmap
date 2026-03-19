#!/usr/bin/env python3
"""
Validate pipeline against Checkdata-final reference data.
Ingests error-free checkdata files, runs full pipeline, exports to separate DB.
Then runs pipeline on dirty data to verify errors ARE detected.
"""

import logging
import os
import sqlite3
import sys
import time

import pandas as pd

# Ensure medmap is on path
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import DB_DIR, DIRTY_DIR, IID_SID_ITEM_PATH
from pipeline.ingestion import DataIngester
from pipeline.validator import DataValidator
from pipeline.cleaner import DataCleaner
from pipeline.mapper import DataMapper
from pipeline.sql_export import SQLExporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("validate_checkdata")

CHECKDATA_DIR = os.path.join(os.path.dirname(__file__), "data", "checkdata", "Checkdata")
CHECKDATA_DB = os.path.join(DB_DIR, "checkdata_output.db")
DIRTY_DB = os.path.join(DB_DIR, "dirty_validation_checkdata.db")


def db_table_counts(db_path):
    """Get row counts for all tables in a database."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [r[0] for r in cursor.fetchall()]
        counts = {}
        for t in tables:
            cursor.execute(f"SELECT COUNT(*) FROM [{t}]")
            counts[t] = cursor.fetchone()[0]
        return counts
    finally:
        conn.close()


def run_pipeline_on_folder(data_dir, db_path, label="checkdata"):
    """Run full pipeline on a given folder, export to given DB."""
    logger.info("=" * 60)
    logger.info("Running pipeline on %s: %s", label, data_dir)
    logger.info("=" * 60)

    # 1. Ingest
    ingester = DataIngester()
    ingester.load_iid_sid_item()

    logger.info("Ingesting files from: %s", data_dir)
    results = ingester.ingest_directory(data_dir)

    logger.info("Ingested %d files:", len(results))
    for fname, (df, result) in results.items():
        if df is not None:
            file_type = df.attrs.get("file_type", "unknown")
            logger.info("  %s: %d rows, type=%s", fname, result.rows_loaded, file_type)
        else:
            logger.warning("  %s: FAILED — %s", fname, result.warnings)

    # 2. Validate
    validator = DataValidator()
    quality_scores = validator.validate_all(ingester.dataframes)
    logger.info("Validation scores:")
    for fname, score in quality_scores.items():
        logger.info("  %s: score=%.1f, imported=%d, quarantined=%d",
                     fname, score.score, score.rows_imported, score.rows_quarantined)

    # 3. Clean
    cleaner = DataCleaner(validator)
    clean_dfs = cleaner.clean_all(ingester.dataframes)
    clean_dfs = cleaner.map_missing_case_ids(clean_dfs)
    logger.info("Cleaned %d DataFrames", len(clean_dfs))

    # Show file_type for each cleaned df
    for fname, df in clean_dfs.items():
        ft = df.attrs.get("file_type", "unknown")
        logger.info("  %s: %d rows, type=%s", fname, len(df), ft)

    # 4. Map
    mapper = DataMapper(iid_sid_map=ingester.iid_sid_map)
    mapped = mapper.map_all(clean_dfs)
    logger.info("Mapping results:")
    for table_name, df in mapped.items():
        if df is not None and not df.empty:
            logger.info("  %s: %d rows, %d cols", table_name, len(df), len(df.columns))
        else:
            logger.info("  %s: EMPTY", table_name)

    # 5. Export
    exporter = SQLExporter(db_path=db_path)
    audit_log = cleaner.get_audit_log()
    export_summary = exporter.export_all(mapped, audit_log)
    logger.info("Export summary: %s", export_summary)

    # 6. Verify DB
    logger.info("")
    logger.info("--- DB Table Counts for %s ---", label)
    counts = db_table_counts(db_path)
    for table, count in sorted(counts.items()):
        logger.info("  %s: %d rows", table, count)

    return mapped, quality_scores, audit_log, counts


def main():
    # Part 1: Run on checkdata (error-free)
    print("\n" + "=" * 70)
    print("PART 1: CHECKDATA (error-free reference)")
    print("=" * 70 + "\n")

    if not os.path.isdir(CHECKDATA_DIR):
        logger.error("Checkdata directory not found: %s", CHECKDATA_DIR)
        logger.error("Download and extract Checkdata-final.zip first.")
        sys.exit(1)

    logger.info("Checkdata files:")
    for f in sorted(os.listdir(CHECKDATA_DIR)):
        fpath = os.path.join(CHECKDATA_DIR, f)
        if os.path.isfile(fpath):
            logger.info("  %s (%d bytes)", f, os.path.getsize(fpath))

    mapped_check, scores_check, audit_check, counts_check = run_pipeline_on_folder(
        CHECKDATA_DIR, CHECKDATA_DB, "checkdata"
    )

    # Verify all 7 import tables + tbCaseData are populated
    expected_tables = [
        "tbCaseData",
        "tbImportLabsData",
        "tbImportIcd10Data",
        "tbImportAcData",
        "tbImportDeviceMotionData",
        "tbImportDevice1HzMotionData",
        "tbImportMedicationInpatientData",
        "tbImportNursingDailyReportsData",
    ]

    print("\n--- CHECKDATA RESULTS ---")
    all_ok = True
    for t in expected_tables:
        count = counts_check.get(t, 0)
        status = "OK" if count > 0 else "EMPTY!"
        if count == 0:
            all_ok = False
        print(f"  {t}: {count} rows [{status}]")

    audit_count = counts_check.get("tbAuditLog", 0)
    print(f"\n  Audit log entries: {audit_count}")
    print(f"  (Checkdata is error-free, so fewer audit entries expected)")

    if all_ok:
        print("\n  ALL TABLES POPULATED — checkdata pipeline OK")
    else:
        print("\n  WARNING: Some tables are empty — investigate!")

    # Part 2: Run on dirty data
    print("\n" + "=" * 70)
    print("PART 2: DIRTY DATA (should detect errors)")
    print("=" * 70 + "\n")

    mapped_dirty, scores_dirty, audit_dirty, counts_dirty = run_pipeline_on_folder(
        DIRTY_DIR, DIRTY_DB, "dirty"
    )

    print("\n--- DIRTY DATA RESULTS ---")
    for t in expected_tables:
        count = counts_dirty.get(t, 0)
        print(f"  {t}: {count} rows")

    dirty_audit_count = counts_dirty.get("tbAuditLog", 0)
    print(f"\n  Audit log entries: {dirty_audit_count}")
    if dirty_audit_count > audit_count:
        print(f"  Dirty data has MORE audit entries ({dirty_audit_count}) than checkdata ({audit_count}) — CORRECT")
    else:
        print(f"  WARNING: Dirty data should have more errors than checkdata!")

    # Summary of errors per file type in dirty data
    print("\n--- DIRTY DATA: Errors per file ---")
    for fname, score in sorted(scores_dirty.items()):
        print(f"  {fname}: score={score.score:.1f}, "
              f"imported={score.rows_imported}, quarantined={score.rows_quarantined}")


if __name__ == "__main__":
    main()
