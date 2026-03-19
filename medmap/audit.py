#!/usr/bin/env python3
"""
Comprehensive Bug Hunt & Audit Script for MEDMAP Pipeline.

Runs adversarial tests against every pipeline stage:
1. Pandera schema validation on all cleaned DataFrames
2. Edge-case / adversarial input tests (empty files, unicode, boundaries)
3. API endpoint smoke tests (if server is running)
4. Cross-stage consistency checks (ingestion -> validation -> cleaning -> mapping -> export)
5. Database integrity checks (FK, nulls, duplicates, missing tokens)

Usage:
    python -m audit                    # full audit on dirty data
    python -m audit --folder clean     # audit clean data
    python -m audit --quick            # skip 1Hz and API tests
    python -m audit --api-only         # only test API endpoints
"""

import argparse
import io
import logging
import os
import sqlite3
import sys
import tempfile
import traceback
from collections import defaultdict
from datetime import datetime

import numpy as np
import pandas as pd

# Ensure medmap is on path
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import DIRTY_DIR, CLEAN_DIR, SPLIT_DIR, DB_PATH
from config.clinical_rules import CLINICAL_RANGES, VALID_LAB_FLAGS, MISSING_VALUE_TOKENS

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger("audit")


# ══════════════════════════════════════════════
# RESULT TRACKING
# ══════════════════════════════════════════════

class AuditResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.errors_by_category = defaultdict(list)

    def ok(self, msg):
        self.passed += 1
        print(f"  \033[92mPASS\033[0m {msg}")

    def fail(self, category, msg):
        self.failed += 1
        self.errors_by_category[category].append(msg)
        print(f"  \033[91mFAIL\033[0m [{category}] {msg}")

    def warn(self, msg):
        self.warnings += 1
        print(f"  \033[93mWARN\033[0m {msg}")

    def summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print(f"AUDIT SUMMARY: {self.passed}/{total} passed, "
              f"{self.failed} failed, {self.warnings} warnings")
        if self.errors_by_category:
            print("\nFailures by category:")
            for cat, errs in sorted(self.errors_by_category.items()):
                print(f"  {cat}: {len(errs)}")
                for e in errs[:5]:
                    print(f"    - {e}")
                if len(errs) > 5:
                    print(f"    ... and {len(errs) - 5} more")
        print("=" * 60)
        return self.failed == 0


# ══════════════════════════════════════════════
# 1. PANDERA SCHEMA VALIDATION
# ══════════════════════════════════════════════

def audit_pandera_schemas(dataframes, result):
    """Run pandera schemas against all cleaned DataFrames."""
    print("\n--- PANDERA SCHEMA VALIDATION ---")
    try:
        from schemas import validate_all
        errors = validate_all(dataframes)
        if not errors:
            result.ok("All DataFrames pass pandera schemas")
        else:
            for fname, errs in errors.items():
                for e in errs:
                    result.fail("PANDERA", f"{fname}: {e}")
    except ImportError:
        result.warn("pandera not installed — skipping schema validation")
    except Exception as e:
        result.fail("PANDERA", f"Schema validation crashed: {e}")


# ══════════════════════════════════════════════
# 2. ADVERSARIAL INPUT TESTS
# ══════════════════════════════════════════════

def audit_adversarial_inputs(result):
    """Test pipeline components with adversarial inputs."""
    print("\n--- ADVERSARIAL INPUT TESTS ---")

    from pipeline.ingestion import DataIngester
    from pipeline.validator import DataValidator
    from pipeline.cleaner import DataCleaner

    ingester = DataIngester()
    validator = DataValidator()
    cleaner = DataCleaner(validator=validator)

    # Test 1: Empty DataFrame
    try:
        empty_df = pd.DataFrame()
        empty_df.attrs = {"source_file": "empty.csv", "file_type": "labs"}
        score = validator.validate_dataframe(empty_df, "empty.csv")
        result.ok(f"Empty DataFrame: validation OK (score={score.score})")
    except Exception as e:
        result.fail("EMPTY_DF", f"Validator crashed on empty DataFrame: {e}")

    try:
        empty_df = pd.DataFrame()
        empty_df.attrs = {"source_file": "empty.csv", "file_type": "labs"}
        cleaned = cleaner.clean_dataframe(empty_df, "empty.csv")
        result.ok("Empty DataFrame: cleaning OK")
    except Exception as e:
        result.fail("EMPTY_DF", f"Cleaner crashed on empty DataFrame: {e}")

    # Test 2: Headers only, no rows
    try:
        headers_only = pd.DataFrame(columns=["case_id", "patient_id", "sodium_mmol_L", "sex"])
        headers_only.attrs = {"source_file": "headers.csv", "file_type": "labs"}
        score = validator.validate_dataframe(headers_only, "headers.csv")
        result.ok(f"Headers-only DataFrame: validation OK (score={score.score})")
    except Exception as e:
        result.fail("HEADERS_ONLY", f"Validator crashed on headers-only: {e}")

    # Test 3: All NaN DataFrame
    try:
        all_nan = pd.DataFrame({
            "case_id": [np.nan, np.nan],
            "patient_id": [np.nan, np.nan],
            "sodium_mmol_L": [np.nan, np.nan],
        })
        all_nan.attrs = {"source_file": "allnan.csv", "file_type": "labs"}
        score = validator.validate_dataframe(all_nan, "allnan.csv")
        cleaned = cleaner.clean_dataframe(all_nan, "allnan.csv")
        result.ok("All-NaN DataFrame: handled without crash")
    except Exception as e:
        result.fail("ALL_NAN", f"Crashed on all-NaN DataFrame: {e}")

    # Test 4: Unicode and special characters
    try:
        unicode_df = pd.DataFrame({
            "case_id": ["CASE-001", "CASE-002", "CASE-003"],
            "patient_id": ["100001", "100002", "100003"],
            "sex": ["männlich", "weiblich", "日本語"],
            "sodium_mmol_L": ["14ü0", "13ö0", "∞"],
            "specimen_datetime": ["15. März 2025", "2025-01-15", "abc🎉def"],
        })
        unicode_df.attrs = {"source_file": "unicode.csv", "file_type": "labs"}
        cleaned = cleaner.clean_dataframe(unicode_df, "unicode.csv")
        result.ok("Unicode/special chars: handled without crash")
    except Exception as e:
        result.fail("UNICODE", f"Crashed on unicode data: {e}")

    # Test 5: Extremely large and negative numbers
    try:
        extreme_df = pd.DataFrame({
            "case_id": ["CASE-001", "CASE-002", "CASE-003", "CASE-004"],
            "patient_id": ["100001", "100002", "100003", "100004"],
            "sodium_mmol_L": [1e15, -999999, 0, float("inf")],
            "potassium_mmol_L": [-1e10, 1e10, 0.0, float("-inf")],
        })
        extreme_df.attrs = {"source_file": "extreme.csv", "file_type": "labs"}
        cleaned = cleaner.clean_dataframe(extreme_df, "extreme.csv")
        # After cleaning, extreme values should be NaN
        for col in ["sodium_mmol_L", "potassium_mmol_L"]:
            if col in cleaned.columns:
                non_nan = cleaned[col].dropna()
                for val in non_nan:
                    low, high = CLINICAL_RANGES[col]
                    if val < low or val > high:
                        result.fail("EXTREME_VALUES",
                                    f"Outlier {val} in {col} survived cleaning")
        result.ok("Extreme values: cleaned correctly")
    except Exception as e:
        result.fail("EXTREME_VALUES", f"Crashed on extreme values: {e}")

    # Test 6: Whitespace-only values
    try:
        ws_df = pd.DataFrame({
            "case_id": ["  ", "\t", "\n", "   \t\n  "],
            "patient_id": [" ", "  ", "\t\t", ""],
            "sodium_mmol_L": [" ", "\t", "  140  ", ""],
        })
        ws_df.attrs = {"source_file": "whitespace.csv", "file_type": "labs"}
        cleaned = cleaner.clean_dataframe(ws_df, "whitespace.csv")
        result.ok("Whitespace-only values: handled without crash")
    except Exception as e:
        result.fail("WHITESPACE", f"Crashed on whitespace-only values: {e}")

    # Test 7: Duplicate rows (100% identical)
    try:
        dup_df = pd.DataFrame({
            "case_id": ["CASE-001"] * 10,
            "patient_id": ["100001"] * 10,
            "sodium_mmol_L": [140.0] * 10,
        })
        dup_df.attrs = {"source_file": "dupes.csv", "file_type": "labs"}
        cleaned = cleaner.clean_dataframe(dup_df, "dupes.csv")
        if len(cleaned) > 1:
            result.fail("DUPLICATES", f"Duplicates not removed: {len(cleaned)} rows remain")
        else:
            result.ok("Duplicate removal: 10 identical rows -> 1")
    except Exception as e:
        result.fail("DUPLICATES", f"Crashed on duplicate data: {e}")

    # Test 8: Mixed types in single column
    try:
        mixed_df = pd.DataFrame({
            "case_id": ["CASE-001", 42, None, True, 3.14],
            "patient_id": [100001, "text", np.nan, False, []],
            "sodium_mmol_L": ["140", 130, "abc", None, ""],
        })
        mixed_df.attrs = {"source_file": "mixed.csv", "file_type": "labs"}
        cleaned = cleaner.clean_dataframe(mixed_df, "mixed.csv")
        result.ok("Mixed types: handled without crash")
    except Exception as e:
        result.fail("MIXED_TYPES", f"Crashed on mixed-type columns: {e}")

    # Test 9: Adversarial CSV file (temp file)
    try:
        csv_content = (
            "case_id,patient_id,sodium_mmol_L,sex\n"
            ",,,\n"
            "null,nan,N/A,missing\n"
            'CASE-001,100001,"14""0",M\n'
            "CASE-002,100002,130.0,F\n"
            ",,,,extra_col\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            tmp_path = f.name
        try:
            df, res = ingester.load(tmp_path)
            if df is not None:
                result.ok(f"Adversarial CSV: loaded {res.rows_loaded} rows")
            else:
                result.warn("Adversarial CSV: returned None (acceptable)")
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        result.fail("ADVERSARIAL_CSV", f"Crashed on adversarial CSV: {e}")

    # Test 10: Empty CSV file
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("")
            tmp_path = f.name
        try:
            df, res = ingester.load(tmp_path)
            result.ok("Empty CSV file: handled without crash")
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        result.fail("EMPTY_FILE", f"Crashed on empty CSV file: {e}")


# ══════════════════════════════════════════════
# 3. PIPELINE CONSISTENCY CHECKS
# ══════════════════════════════════════════════

def audit_pipeline_consistency(dataframes, cleaned, result):
    """Check cross-stage consistency."""
    print("\n--- PIPELINE CONSISTENCY CHECKS ---")

    # Check that cleaning didn't ADD rows
    for fname in dataframes:
        if fname in cleaned:
            orig_rows = len(dataframes[fname])
            clean_rows = len(cleaned[fname])
            if clean_rows > orig_rows:
                result.fail("CONSISTENCY",
                            f"{fname}: cleaning added rows ({orig_rows} -> {clean_rows})")
            else:
                result.ok(f"{fname}: row count OK ({orig_rows} -> {clean_rows})")

    # Check that file_type attrs are preserved
    for fname, df in cleaned.items():
        ft = df.attrs.get("file_type")
        if not ft:
            result.fail("CONSISTENCY", f"{fname}: missing file_type attr after cleaning")
        else:
            result.ok(f"{fname}: file_type preserved ({ft})")

    # Check no missing value tokens survive cleaning
    # Skip _raw columns (they preserve original values intentionally)
    # Skip actual NaN values (str(NaN) -> "nan" is a false positive)
    tokens = MISSING_VALUE_TOKENS - {"", " "}
    for fname, df in cleaned.items():
        for col in df.columns:
            if col.endswith("_raw"):
                continue
            if df[col].dtype == object:
                # Only check non-null values to avoid NaN -> "nan" false positives
                non_null = df[col].dropna()
                if len(non_null) == 0:
                    continue
                bad_mask = non_null.astype(str).str.strip().str.lower().isin(tokens)
                count = bad_mask.sum()
                if count > 0:
                    result.fail("MISSING_TOKENS",
                                f"{fname}.{col}: {count} missing tokens survived cleaning")

    # Check gender normalization
    for fname, df in cleaned.items():
        for col in ("sex", "gender"):
            if col in df.columns:
                valid = {"M", "F"}
                bad = df[col].dropna()
                bad = bad[~bad.isin(valid)]
                if len(bad) > 0:
                    result.fail("GENDER",
                                f"{fname}.{col}: {len(bad)} invalid gender values: {bad.unique()[:5]}")
                else:
                    result.ok(f"{fname}.{col}: all genders normalized")

    # Check clinical ranges post-cleaning
    for fname, df in cleaned.items():
        for col, (low, high) in CLINICAL_RANGES.items():
            if col not in df.columns:
                continue
            numeric = pd.to_numeric(df[col], errors="coerce").dropna()
            outliers = numeric[(numeric < low) | (numeric > high)]
            if len(outliers) > 0:
                result.fail("CLINICAL_RANGE",
                            f"{fname}.{col}: {len(outliers)} values outside [{low}, {high}]")

    # Check date normalization
    for fname, df in cleaned.items():
        for col in df.columns:
            if "date" in col.lower() or "timestamp" in col.lower():
                if df[col].dtype == object:
                    non_null = df[col].dropna().astype(str)
                    non_iso = non_null[~non_null.str.match(r'^\d{4}-\d{2}-\d{2}')]
                    if len(non_iso) > 0:
                        result.fail("DATE_FORMAT",
                                    f"{fname}.{col}: {len(non_iso)} non-ISO dates: "
                                    f"{non_iso.head(3).tolist()}")

    # Check lab flags normalization
    for fname, df in cleaned.items():
        if df.attrs.get("file_type") != "labs":
            continue
        for col in df.columns:
            if col.endswith("_flag"):
                valid = VALID_LAB_FLAGS | {np.nan}
                bad = df[col].dropna()
                bad = bad[~bad.isin(VALID_LAB_FLAGS)]
                if len(bad) > 0:
                    result.fail("LAB_FLAGS",
                                f"{fname}.{col}: {len(bad)} invalid flags: {bad.unique()[:5]}")

    # Check shift normalization
    for fname, df in cleaned.items():
        if "shift" in df.columns:
            valid_shifts = {"Early", "Late", "Night"}
            bad = df["shift"].dropna()
            bad = bad[~bad.isin(valid_shifts)]
            if len(bad) > 0:
                result.fail("SHIFT",
                            f"{fname}.shift: {len(bad)} invalid shifts: {bad.unique()[:5]}")

    # Check event type normalization
    for fname, df in cleaned.items():
        for col in ("record_type", "event_type"):
            if col in df.columns:
                valid_types = {"ORDER", "CHANGE", "ADMIN"}
                bad = df[col].dropna()
                bad = bad[~bad.isin(valid_types)]
                if len(bad) > 0:
                    result.fail("EVENT_TYPE",
                                f"{fname}.{col}: {len(bad)} invalid event types: {bad.unique()[:5]}")


# ══════════════════════════════════════════════
# 4. DATABASE INTEGRITY CHECKS
# ══════════════════════════════════════════════

def audit_database(result):
    """Check database integrity after export."""
    print("\n--- DATABASE INTEGRITY CHECKS ---")

    if not os.path.exists(DB_PATH):
        result.warn(f"Database not found at {DB_PATH} — skipping DB checks")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Check all expected tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row["name"] for row in cursor.fetchall()}
        expected = {
            "tbCaseData", "tbImportLabsData", "tbImportIcd10Data",
            "tbImportDeviceMotionData", "tbImportDevice1HzMotionData",
            "tbImportMedicationInpatientData", "tbImportNursingDailyReportsData",
            "tbAuditLog",
        }
        missing = expected - tables
        if missing:
            result.fail("DB_TABLES", f"Missing tables: {missing}")
        else:
            result.ok(f"All {len(expected)} expected tables exist")

        # Check row counts
        for table in sorted(tables):
            cursor.execute(f"SELECT COUNT(*) as cnt FROM [{table}]")
            count = cursor.fetchone()["cnt"]
            if count == 0 and table in expected:
                result.warn(f"{table}: 0 rows")
            else:
                result.ok(f"{table}: {count} rows")

        # Check FK integrity: coCaseId in child tables references tbCaseData
        if "tbCaseData" in tables:
            cursor.execute("SELECT DISTINCT coCaseIdAlpha FROM tbCaseData WHERE coCaseIdAlpha IS NOT NULL")
            valid_case_ids = {row["coCaseIdAlpha"] for row in cursor.fetchall()}

            fk_tables = [
                "tbImportLabsData", "tbImportIcd10Data",
                "tbImportDeviceMotionData", "tbImportMedicationInpatientData",
                "tbImportNursingDailyReportsData",
            ]
            for table in fk_tables:
                if table not in tables:
                    continue
                try:
                    cursor.execute(f"SELECT coCaseId FROM [{table}] WHERE coCaseId IS NOT NULL")
                    child_ids = {row["coCaseId"] for row in cursor.fetchall()}
                    orphans = child_ids - valid_case_ids
                    if orphans:
                        result.fail("FK_INTEGRITY",
                                    f"{table}: {len(orphans)} orphan coCaseId values")
                    else:
                        result.ok(f"{table}: FK integrity OK")
                except sqlite3.OperationalError:
                    pass  # table might not have coCaseId

        # Check for NULL case_ids in critical tables
        for table in ["tbImportLabsData", "tbImportIcd10Data"]:
            if table not in tables:
                continue
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM [{table}] WHERE coCaseId IS NULL")
                null_count = cursor.fetchone()["cnt"]
                if null_count > 0:
                    result.fail("NULL_FK", f"{table}: {null_count} NULL coCaseId values")
                else:
                    result.ok(f"{table}: no NULL coCaseId")
            except sqlite3.OperationalError:
                pass

        # Check for duplicate rows in each table
        for table in sorted(tables & expected):
            try:
                cursor.execute(f"SELECT *, COUNT(*) as cnt FROM [{table}] GROUP BY * HAVING cnt > 1")
                dups = cursor.fetchall()
                if dups:
                    result.fail("DB_DUPLICATES", f"{table}: {len(dups)} duplicate row groups")
            except sqlite3.OperationalError:
                pass  # GROUP BY * not always supported

        # Check gender values in tbCaseData
        if "tbCaseData" in tables:
            try:
                cursor.execute("SELECT DISTINCT coGender FROM tbCaseData WHERE coGender IS NOT NULL")
                genders = {row["coGender"] for row in cursor.fetchall()}
                invalid = genders - {"M", "F"}
                if invalid:
                    result.fail("DB_GENDER", f"Invalid genders in tbCaseData: {invalid}")
                else:
                    result.ok("tbCaseData: gender values OK (M/F only)")
            except sqlite3.OperationalError:
                pass

        # Check missing tokens in text columns
        tokens_sql = ",".join(f"'{t}'" for t in MISSING_VALUE_TOKENS if t.strip())
        for table in sorted(tables & expected):
            try:
                cursor.execute(f"PRAGMA table_info([{table}])")
                cols = [row["name"] for row in cursor.fetchall()]
                for col in cols:
                    cursor.execute(
                        f"SELECT COUNT(*) as cnt FROM [{table}] "
                        f"WHERE LOWER(TRIM([{col}])) IN ({tokens_sql})"
                    )
                    count = cursor.fetchone()["cnt"]
                    if count > 0:
                        result.fail("DB_MISSING_TOKENS",
                                    f"{table}.{col}: {count} missing value tokens in DB")
            except sqlite3.OperationalError:
                pass

    finally:
        conn.close()


# ══════════════════════════════════════════════
# 5. API SMOKE TESTS
# ══════════════════════════════════════════════

def audit_api(result):
    """Quick smoke test of API endpoints (requires running server)."""
    print("\n--- API SMOKE TESTS ---")

    try:
        import httpx
    except ImportError:
        result.warn("httpx not installed — skipping API tests")
        return

    base = "http://localhost:8000"
    endpoints = [
        ("GET", "/api/pipeline/stats"),
        ("GET", "/api/overview/quality-scores"),
        ("GET", "/api/overview/ward-scores"),
        ("GET", "/api/agents/stats"),
        ("GET", "/api/agents/mappings?limit=10"),
        ("GET", "/api/patients?limit=5"),
        ("GET", "/api/alerts?limit=5"),
        ("GET", "/api/quality/audit-log?limit=10"),
        ("GET", "/api/quality/passports?limit=10"),
        ("GET", "/api/quality/completeness"),
        ("GET", "/api/corrections/pending"),
        ("GET", "/api/corrections/history"),
        ("GET", "/api/ask/history"),
    ]

    try:
        with httpx.Client(timeout=10) as client:
            # Quick connectivity check
            try:
                client.get(f"{base}/docs")
            except httpx.ConnectError:
                result.warn("API server not running at localhost:8000 — skipping")
                return

            for method, path in endpoints:
                try:
                    if method == "GET":
                        resp = client.get(f"{base}{path}")
                    elif method == "POST":
                        resp = client.post(f"{base}{path}", json={})

                    if resp.status_code < 400:
                        result.ok(f"{method} {path}: {resp.status_code}")
                    elif resp.status_code == 404:
                        result.warn(f"{method} {path}: 404 (endpoint not found)")
                    else:
                        result.fail("API",
                                    f"{method} {path}: {resp.status_code} {resp.text[:100]}")
                except Exception as e:
                    result.fail("API", f"{method} {path}: {e}")

    except Exception as e:
        result.fail("API", f"API test setup failed: {e}")


# ══════════════════════════════════════════════
# 6. SILENT FAILURE DETECTION
# ══════════════════════════════════════════════

def audit_silent_failures(result):
    """Check for bare except, pass, or swallowed errors in pipeline code."""
    print("\n--- SILENT FAILURE DETECTION ---")

    pipeline_dir = os.path.join(os.path.dirname(__file__), "pipeline")
    api_dir = os.path.join(os.path.dirname(__file__), "api")

    patterns = [
        ("except: pass", r"except\s*:\s*pass"),
        ("except Exception: pass", r"except\s+\w+\s*:\s*pass"),
        ("bare except", r"except\s*:"),
    ]

    import re
    for search_dir in [pipeline_dir, api_dir]:
        if not os.path.isdir(search_dir):
            continue
        for root, _, files in os.walk(search_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, "r") as f:
                    lines = f.readlines()
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped == "pass" and i > 1:
                        prev = lines[i - 2].strip()
                        if prev.startswith("except"):
                            rel_path = os.path.relpath(fpath, os.path.dirname(__file__))
                            result.warn(f"Silent failure: {rel_path}:{i} — except/pass")


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="MEDMAP Pipeline Audit")
    parser.add_argument("--folder", default="dirty", choices=["dirty", "clean"])
    parser.add_argument("--quick", action="store_true", help="Skip 1Hz and API tests")
    parser.add_argument("--api-only", action="store_true", help="Only test API endpoints")
    args = parser.parse_args()

    result = AuditResult()
    print(f"MEDMAP Audit — {datetime.now().isoformat()}")
    print(f"Data folder: {args.folder}")

    if args.api_only:
        audit_api(result)
        result.summary()
        sys.exit(0 if result.failed == 0 else 1)

    # Run adversarial tests (no data dependency)
    audit_adversarial_inputs(result)

    # Run silent failure detection
    audit_silent_failures(result)

    # Load and process data through pipeline
    print("\n--- LOADING DATA ---")
    try:
        from pipeline.ingestion import DataIngester
        from pipeline.validator import DataValidator
        from pipeline.cleaner import DataCleaner

        ingester = DataIngester()
        base_dir = DIRTY_DIR if args.folder == "dirty" else CLEAN_DIR
        base_results = ingester.ingest_directory(base_dir, skip_1hz=args.quick)

        if not args.quick:
            split_results = ingester.ingest_directory(SPLIT_DIR, skip_1hz=args.quick)

        dataframes = ingester.dataframes
        if not dataframes:
            result.fail("INGESTION", "No DataFrames loaded")
            result.summary()
            sys.exit(1)

        result.ok(f"Loaded {len(dataframes)} DataFrames")

        # Validate
        validator = DataValidator()
        scores = validator.validate_all(dataframes)
        result.ok(f"Validated {len(scores)} files, "
                  f"audit log: {len(validator.audit_log)} entries")

        # Clean
        cleaner = DataCleaner(validator=validator)
        cleaned = cleaner.clean_all(dataframes)
        result.ok(f"Cleaned {len(cleaned)} DataFrames")

        # Run pandera schemas
        audit_pandera_schemas(cleaned, result)

        # Run consistency checks
        audit_pipeline_consistency(dataframes, cleaned, result)

        # Check database if it exists
        audit_database(result)

        # API smoke tests
        if not args.quick:
            audit_api(result)

    except Exception as e:
        result.fail("PIPELINE", f"Pipeline crashed: {e}\n{traceback.format_exc()}")

    success = result.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
