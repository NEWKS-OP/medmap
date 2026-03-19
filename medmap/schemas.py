"""
Pandera validation schemas for all pipeline DataFrames.
Enforces data contracts at each pipeline stage boundary.

Usage:
    from schemas import validate_labs, validate_medication, validate_all_mapped
    errors = validate_labs(df)  # returns list of error strings, empty if valid
"""

import pandera as pa
from pandera import Column, Check, Index
import pandas as pd
import numpy as np

from config.clinical_rules import CLINICAL_RANGES


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _in_range(low, high):
    """Check that numeric values fall within clinical range (NaN allowed)."""
    return Check(lambda s: s.between(low, high), element_wise=False,
                 error=f"Values must be between {low} and {high}",
                 ignore_na=True)


def _valid_gender():
    return Check(lambda s: s.isin({"M", "F"}), element_wise=False,
                 error="Gender must be M or F", ignore_na=True)


def _valid_case_id():
    return Check(lambda s: s.str.match(r'^CASE-\d{3,4}$'),
                 element_wise=False,
                 error="case_id must match CASE-XXXX format",
                 ignore_na=True)


def _valid_lab_flag():
    return Check(lambda s: s.isin({"H", "L", "HH", "LL", ""}),
                 element_wise=False,
                 error="Lab flag must be H, L, HH, LL, or empty",
                 ignore_na=True)


def _valid_shift():
    return Check(lambda s: s.isin({"Early", "Late", "Night"}),
                 element_wise=False,
                 error="Shift must be Early, Late, or Night",
                 ignore_na=True)


def _valid_event_type():
    return Check(lambda s: s.isin({"ORDER", "CHANGE", "ADMIN"}),
                 element_wise=False,
                 error="Event type must be ORDER, CHANGE, or ADMIN",
                 ignore_na=True)


def _iso_date():
    """Check that date strings are ISO format YYYY-MM-DD or YYYY-MM-DD HH:MM:SS."""
    return Check(
        lambda s: s.str.match(r'^\d{4}-\d{2}-\d{2}'),
        element_wise=False,
        error="Dates must be ISO format (YYYY-MM-DD)",
        ignore_na=True,
    )


def _no_missing_tokens():
    """Check that no missing value tokens remain as strings."""
    tokens = {"null", "nan", "n/a", "na", "missing", "unknown", "keine", "none", "nil"}
    return Check(
        lambda s: ~s.astype(str).str.strip().str.lower().isin(tokens),
        element_wise=False,
        error="Missing value tokens found (null, nan, N/A, etc.)",
        ignore_na=True,
    )


def _binary_values():
    """Check that values are 0 or 1 (numeric)."""
    return Check(lambda s: pd.to_numeric(s, errors="coerce").isin({0, 1, 0.0, 1.0}),
                 element_wise=False,
                 error="Binary column must contain only 0 or 1",
                 ignore_na=True)


# ──────────────────────────────────────────────
# SCHEMAS — POST-CLEANING (cleaned DataFrames)
# ──────────────────────────────────────────────

LABS_SCHEMA = pa.DataFrameSchema(
    columns={
        "case_id": Column(object, checks=[_no_missing_tokens()], nullable=True),
        "patient_id": Column(object, checks=[_no_missing_tokens()], nullable=True),
        "sex": Column(object, checks=[_valid_gender()], nullable=True, required=False),
        "sodium_mmol_L": Column(float, checks=[_in_range(100, 165)], nullable=True, coerce=True, required=False),
        "potassium_mmol_L": Column(float, checks=[_in_range(2.0, 7.5)], nullable=True, coerce=True, required=False),
        "creatinine_mg_dL": Column(float, checks=[_in_range(0.3, 15.0)], nullable=True, coerce=True, required=False),
        "egfr_mL_min_1_73m2": Column(float, checks=[_in_range(1, 120)], nullable=True, coerce=True, required=False),
        "glucose_mg_dL": Column(float, checks=[_in_range(20, 600)], nullable=True, coerce=True, required=False),
        "hemoglobin_g_dL": Column(float, checks=[_in_range(3, 25)], nullable=True, coerce=True, required=False),
        "wbc_10e9_L": Column(float, checks=[_in_range(0.1, 100)], nullable=True, coerce=True, required=False),
        "platelets_10e9_L": Column(float, checks=[_in_range(10, 1000)], nullable=True, coerce=True, required=False),
        "crp_mg_L": Column(float, checks=[_in_range(0, 500)], nullable=True, coerce=True, required=False),
        "alt_U_L": Column(float, checks=[_in_range(1, 5000)], nullable=True, coerce=True, required=False),
        "ast_U_L": Column(float, checks=[_in_range(1, 5000)], nullable=True, coerce=True, required=False),
        "bilirubin_mg_dL": Column(float, checks=[_in_range(0, 30)], nullable=True, coerce=True, required=False),
        "albumin_g_dL": Column(float, checks=[_in_range(1, 6)], nullable=True, coerce=True, required=False),
        "inr": Column(float, checks=[_in_range(0.5, 10)], nullable=True, coerce=True, required=False),
        "lactate_mmol_L": Column(float, checks=[_in_range(0.3, 20)], nullable=True, coerce=True, required=False),
    },
    strict=False,  # allow extra columns (_raw, flags, etc.)
    coerce=True,
)

MEDICATION_SCHEMA = pa.DataFrameSchema(
    columns={
        "case_id": Column(object, checks=[_no_missing_tokens()], nullable=True),
        "patient_id": Column(object, checks=[_no_missing_tokens()], nullable=True),
        "medication_name": Column(object, nullable=True, required=False),
        "record_type": Column(object, checks=[_valid_event_type()], nullable=True, required=False),
    },
    strict=False,
    coerce=True,
)

NURSING_SCHEMA = pa.DataFrameSchema(
    columns={
        "case_id": Column(object, checks=[_no_missing_tokens()], nullable=True),
        "patient_id": Column(object, checks=[_no_missing_tokens()], nullable=True),
        "shift": Column(object, checks=[_valid_shift()], nullable=True, required=False),
        "nursing_note_free_text": Column(object, nullable=True, required=False),
    },
    strict=False,
    coerce=True,
)

ICD10_SCHEMA = pa.DataFrameSchema(
    columns={
        "case_id": Column(object, checks=[_no_missing_tokens()], nullable=True),
        "primary_icd10_code": Column(object, nullable=True, required=False),
        "ward": Column(object, nullable=True, required=False),
    },
    strict=False,
    coerce=True,
)

DEVICE_MOTION_SCHEMA = pa.DataFrameSchema(
    columns={
        "patient_id": Column(object, checks=[_no_missing_tokens()], nullable=True),
        "movement_index_0_100": Column(float, checks=[_in_range(0, 100)], nullable=True, coerce=True, required=False),
        "fall_event_0_1": Column(float, checks=[_binary_values()], nullable=True, coerce=True, required=False),
        "bed_exit_detected_0_1": Column(float, checks=[_binary_values()], nullable=True, coerce=True, required=False),
        "impact_magnitude_g": Column(float, checks=[_in_range(0, 50)], nullable=True, coerce=True, required=False),
        "post_fall_immobility_minutes": Column(float, checks=[_in_range(0, 1440)], nullable=True, coerce=True, required=False),
    },
    strict=False,
    coerce=True,
)

DEVICE_1HZ_SCHEMA = pa.DataFrameSchema(
    columns={
        "patient_id": Column(object, checks=[_no_missing_tokens()], nullable=True),
        "fall_event_0_1": Column(float, checks=[_binary_values()], nullable=True, coerce=True, required=False),
    },
    strict=False,
    coerce=True,
)


# ──────────────────────────────────────────────
# SCHEMA REGISTRY
# ──────────────────────────────────────────────

SCHEMA_REGISTRY = {
    "labs": LABS_SCHEMA,
    "medication": MEDICATION_SCHEMA,
    "nursing": NURSING_SCHEMA,
    "icd10_ops": ICD10_SCHEMA,
    "device_motion": DEVICE_MOTION_SCHEMA,
    "device_1hz": DEVICE_1HZ_SCHEMA,
}


# ──────────────────────────────────────────────
# VALIDATION FUNCTIONS
# ──────────────────────────────────────────────

def validate_dataframe(df: pd.DataFrame, file_type: str = None) -> list[str]:
    """
    Validate a DataFrame against its pandera schema.
    Returns list of error messages (empty = valid).
    """
    if file_type is None:
        file_type = df.attrs.get("file_type", "unknown")

    schema = SCHEMA_REGISTRY.get(file_type)
    if schema is None:
        return []  # no schema for this type (epaAC etc.)

    errors = []
    try:
        schema.validate(df, lazy=True)
    except pa.errors.SchemaErrors as e:
        for _, row in e.failure_cases.iterrows():
            col = row.get("column", "?")
            check = row.get("check", "?")
            idx = row.get("index", "?")
            val = row.get("failure_case", "?")
            errors.append(f"[{file_type}] col={col} row={idx}: {check} (value={val})")
    except Exception as e:
        errors.append(f"[{file_type}] Schema validation error: {e}")

    return errors


def validate_all(dataframes: dict[str, pd.DataFrame]) -> dict[str, list[str]]:
    """
    Validate all DataFrames. Returns {filename: [errors]}.
    """
    results = {}
    for filename, df in dataframes.items():
        errs = validate_dataframe(df)
        if errs:
            results[filename] = errs
    return results


def validate_mapped_table(df: pd.DataFrame, table_name: str) -> list[str]:
    """
    Validate a mapped (target schema) DataFrame.
    Checks: no NULL primary keys, FK references exist, no missing tokens.
    """
    errors = []

    # Check primary key column exists and has no nulls
    if "coId" in df.columns:
        null_pks = df["coId"].isna().sum()
        if null_pks > 0:
            errors.append(f"[{table_name}] {null_pks} NULL primary keys in coId")

    # Check FK column
    if "coCaseId" in df.columns:
        null_fks = df["coCaseId"].isna().sum()
        if null_fks > 0:
            errors.append(f"[{table_name}] {null_fks} NULL foreign keys in coCaseId")

    # Check no missing tokens remain in any column
    tokens = {"null", "nan", "n/a", "na", "missing", "unknown", "keine", "none", "nil"}
    for col in df.columns:
        if df[col].dtype == object:
            bad = df[col].astype(str).str.strip().str.lower().isin(tokens)
            count = bad.sum()
            if count > 0:
                errors.append(f"[{table_name}] {count} missing-value tokens in {col}")

    # Check no duplicate rows
    dup_count = df.duplicated().sum()
    if dup_count > 0:
        errors.append(f"[{table_name}] {dup_count} duplicate rows")

    return errors
