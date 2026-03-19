"""
Module 2A: Data Validation
Validates clinical values, dates, IDs, and detects anomalies.
Logs all findings to AuditLogEntry.
"""

import logging
import re
from datetime import datetime
from typing import Optional

from dateutil import parser as dateutil_parser

import numpy as np
import pandas as pd

from contracts import (
    AuditLogEntry, SourceQualityScore, Severity, ActionTaken,
)
from config.clinical_rules import (
    CLINICAL_RANGES, VALID_LAB_FLAGS, MISSING_VALUE_TOKENS,
)

logger = logging.getLogger(__name__)

# Regex patterns for ID validation
CASE_ID_PATTERN = re.compile(r'^CASE-\d{3,4}$')
PATIENT_ID_PATTERN = re.compile(r'^(PAT-)?\d{4,6}$')

# Date columns by file type
DATE_COLUMNS = {
    "labs": ["specimen_datetime"],
    "icd10_ops": ["admission_date", "discharge_date"],
    "device_motion": ["timestamp"],
    "device_1hz": ["timestamp"],
    "medication": [
        "admission_datetime", "discharge_datetime",
        "order_start_datetime", "order_stop_datetime",
        "administration_datetime",
    ],
    "nursing": ["report_date"],
    "epaAC_german": ["AufnDat"],
    "epaAC_sap": [],
    "epaAC_pivot": [],
}

# Columns that contain clinical numeric values (subset of CLINICAL_RANGES keys)
NUMERIC_CLINICAL_COLS = set(CLINICAL_RANGES.keys())

# Lab flag columns (column name -> associated value column)
LAB_FLAG_COLUMNS = [
    "sodium_flag", "potassium_flag", "creatinine_flag", "egfr_flag",
    "glucose_flag", "hb_flag", "wbc_flag", "platelets_flag",
    "crp_flag", "alt_flag", "ast_flag", "bilirubin_flag",
    "albumin_flag", "inr_flag", "lactate_flag",
]

# Gender columns
GENDER_COLUMNS = {"sex", "gender", "coGender", "Geschlecht"}

# Special characters to strip from numeric fields
SPECIAL_CHARS_PATTERN = re.compile(r'[üäöß^@$%#&*!?+=\[\]{}|\\/<>~`]', re.IGNORECASE)


class DataValidator:
    """Validates ingested DataFrames and produces audit log entries."""

    def __init__(self):
        self.audit_log: list[AuditLogEntry] = []
        self.quality_scores: dict[str, SourceQualityScore] = {}

    def validate_all(self, dataframes: dict[str, pd.DataFrame]) -> dict[str, SourceQualityScore]:
        """Validate all ingested DataFrames. Returns quality scores per source."""
        for filename, df in dataframes.items():
            try:
                score = self.validate_dataframe(df, filename)
                self.quality_scores[filename] = score
            except Exception as e:
                logger.error(f"Validation failed for {filename}: {e}")
                self.quality_scores[filename] = SourceQualityScore(
                    source_file=filename, score=0,
                    rows_imported=0, rows_quarantined=len(df),
                    values_auto_corrected=0,
                    errors_by_category={"VALIDATION_ERROR": 1},
                )
        return self.quality_scores

    def validate_dataframe(self, df: pd.DataFrame, filename: str) -> SourceQualityScore:
        """Validate a single DataFrame. Returns SourceQualityScore."""
        file_type = df.attrs.get("file_type", "unknown")
        source_file = df.attrs.get("source_file", filename)
        errors_by_cat: dict[str, int] = {}
        initial_log_len = len(self.audit_log)

        # 2.2 Missing values
        self._validate_missing_values(df, source_file, file_type, errors_by_cat)

        # 2.3 Date validation
        self._validate_dates(df, source_file, file_type, errors_by_cat)

        # 2.4 Clinical range validation
        self._validate_clinical_ranges(df, source_file, file_type, errors_by_cat)

        # 2.5 Gender validation
        self._validate_gender(df, source_file, file_type, errors_by_cat)

        # 2.6 ID validation
        self._validate_ids(df, source_file, file_type, errors_by_cat)

        # 2.8 Duplicate detection
        self._validate_duplicates(df, source_file, file_type, errors_by_cat)

        # 2.10 Lab flag validation
        self._validate_lab_flags(df, source_file, file_type, errors_by_cat)

        # Compute quality score
        entries_added = len(self.audit_log) - initial_log_len
        total_cells = df.shape[0] * df.shape[1] if df.shape[1] > 0 else 1
        quarantined = sum(
            1 for e in self.audit_log[initial_log_len:]
            if e.action_taken == ActionTaken.QUARANTINE
        )
        score = max(0, int(100 - (entries_added / max(total_cells, 1)) * 100))

        return SourceQualityScore(
            source_file=source_file,
            score=score,
            rows_imported=len(df) - quarantined,
            rows_quarantined=quarantined,
            values_auto_corrected=0,
            errors_by_category=errors_by_cat,
        )

    # ──────────────────────────────────────────────
    # 2.2 MISSING VALUES
    # ──────────────────────────────────────────────

    def _validate_missing_values(self, df, source_file, file_type, errors):
        """Detect missing values and log them."""
        count = 0
        for col in df.columns:
            for idx, val in df[col].items():
                if self._is_missing(val):
                    severity = self._missing_severity(col, file_type)
                    case_id = self._extract_case_id(df, idx)
                    self._log(
                        source_file=source_file,
                        case_id=case_id,
                        table_name=self._table_for_type(file_type),
                        column_name=col,
                        original_value=str(val) if val is not None else "",
                        cleaned_value=None,
                        error_type="MISSING_VALUE",
                        severity=severity,
                        action_taken=ActionTaken.FLAGGED,
                        row_number=idx,
                    )
                    count += 1
        if count:
            errors["MISSING_VALUES"] = errors.get("MISSING_VALUES", 0) + count

    def _is_missing(self, val) -> bool:
        """Check if a value is missing."""
        if val is None:
            return True
        if isinstance(val, float) and np.isnan(val):
            return True
        s = str(val).strip().lower()
        return s in MISSING_VALUE_TOKENS

    def _missing_severity(self, col, file_type) -> Severity:
        """Determine severity of a missing value based on column."""
        critical_cols = {"case_id", "patient_id", "coCaseId", "coPatientId"}
        high_cols = {"timestamp", "specimen_datetime", "admission_date", "report_date"}
        if col in critical_cols:
            return Severity.CRITICAL
        if col in high_cols:
            return Severity.HIGH
        if col in NUMERIC_CLINICAL_COLS:
            return Severity.MEDIUM
        return Severity.LOW

    # ──────────────────────────────────────────────
    # 2.3 DATE VALIDATION
    # ──────────────────────────────────────────────

    def _validate_dates(self, df, source_file, file_type, errors):
        """Validate date columns for impossible/out-of-range dates."""
        date_cols = DATE_COLUMNS.get(file_type, [])
        # Also detect date columns by name pattern
        for col in df.columns:
            if any(kw in col.lower() for kw in ["date", "datetime", "timestamp", "datum", "aufn", "entlass"]):
                if col not in date_cols:
                    date_cols.append(col)

        count = 0
        for col in date_cols:
            if col not in df.columns:
                continue
            for idx, val in df[col].items():
                if self._is_missing(val):
                    continue
                parsed = self._try_parse_date(str(val).strip())
                if parsed is None:
                    case_id = self._extract_case_id(df, idx)
                    self._log(
                        source_file=source_file,
                        case_id=case_id,
                        table_name=self._table_for_type(file_type),
                        column_name=col,
                        original_value=str(val),
                        cleaned_value=None,
                        error_type="INVALID_DATE",
                        severity=Severity.HIGH,
                        action_taken=ActionTaken.QUARANTINE,
                        row_number=idx,
                    )
                    count += 1
                elif parsed.year < 2000 or parsed.year > 2030:
                    case_id = self._extract_case_id(df, idx)
                    self._log(
                        source_file=source_file,
                        case_id=case_id,
                        table_name=self._table_for_type(file_type),
                        column_name=col,
                        original_value=str(val),
                        cleaned_value=None,
                        error_type="DATE_OUT_OF_RANGE",
                        severity=Severity.MEDIUM,
                        action_taken=ActionTaken.FLAGGED,
                        row_number=idx,
                    )
                    count += 1
        if count:
            errors["INVALID_DATE"] = errors.get("INVALID_DATE", 0) + count

    def _try_parse_date(self, val: str) -> Optional[datetime]:
        """Try to parse a date string through multiple formats."""
        val = val.strip()
        if not val:
            return None

        # Reject obviously impossible dates
        impossible_patterns = [
            r'^99\.99\.9999$', r'^00[./]00[./]0000$',
            r'^0000', r'9999\.9999',
        ]
        for pat in impossible_patterns:
            if re.match(pat, val):
                return None

        # Pass 1: ISO YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                     "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f"]:
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue

        # Pass 2: German DD.MM.YYYY
        for fmt in ["%d.%m.%Y", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M"]:
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue

        # Pass 3: US MM/DD/YYYY
        for fmt in ["%m/%d/%Y", "%m/%d/%Y %H:%M:%S"]:
            try:
                d = datetime.strptime(val, fmt)
                if d.month > 12:
                    return None
                return d
            except ValueError:
                continue

        # Pass 4: Textual months (German and English)
        german_months = {
            "januar": "01", "februar": "02", "märz": "03", "april": "04",
            "mai": "05", "juni": "06", "juli": "07", "august": "08",
            "september": "09", "oktober": "10", "november": "11", "dezember": "12",
        }
        val_lower = val.lower()
        for de_month, num in german_months.items():
            if de_month in val_lower:
                val_replaced = val_lower.replace(de_month, num).replace(".", "").strip()
                match = re.search(r'(\d{1,2})\s*' + num + r'\s*(\d{4})', val_replaced)
                if match:
                    try:
                        return datetime.strptime(
                            f"{match.group(1).zfill(2)}.{num}.{match.group(2)}",
                            "%d.%m.%Y"
                        )
                    except ValueError:
                        pass

        # English textual months via dateutil as last resort
        try:
            return dateutil_parser.parse(val, dayfirst=True)
        except Exception:
            pass

        return None

    # ──────────────────────────────────────────────
    # 2.4 CLINICAL RANGE VALIDATION
    # ──────────────────────────────────────────────

    def _validate_clinical_ranges(self, df, source_file, file_type, errors):
        """Validate numeric clinical values against defined ranges."""
        count = 0
        for col, (low, high) in CLINICAL_RANGES.items():
            if col not in df.columns:
                continue
            for idx, val in df[col].items():
                if self._is_missing(val):
                    continue
                num_val = self._try_parse_numeric(val)
                if num_val is None:
                    # Non-numeric contamination
                    case_id = self._extract_case_id(df, idx)
                    self._log(
                        source_file=source_file,
                        case_id=case_id,
                        table_name=self._table_for_type(file_type),
                        column_name=col,
                        original_value=str(val),
                        cleaned_value=None,
                        error_type="NON_NUMERIC",
                        severity=Severity.HIGH,
                        action_taken=ActionTaken.QUARANTINE,
                        row_number=idx,
                    )
                    count += 1
                elif num_val < low or num_val > high:
                    case_id = self._extract_case_id(df, idx)
                    self._log(
                        source_file=source_file,
                        case_id=case_id,
                        table_name=self._table_for_type(file_type),
                        column_name=col,
                        original_value=str(val),
                        cleaned_value=None,
                        error_type="CLINICAL_OUTLIER",
                        severity=Severity.CRITICAL,
                        action_taken=ActionTaken.QUARANTINE,
                        row_number=idx,
                    )
                    count += 1
        if count:
            errors["CLINICAL_OUTLIER"] = errors.get("CLINICAL_OUTLIER", 0) + count

    def _try_parse_numeric(self, val) -> Optional[float]:
        """Try to parse a value as float, stripping special chars if needed."""
        if isinstance(val, (int, float)):
            if isinstance(val, float) and np.isnan(val):
                return None
            return float(val)
        s = str(val).strip()
        if not s:
            return None
        # Try direct conversion
        try:
            return float(s)
        except ValueError:
            pass
        # Strip special characters and retry
        cleaned = SPECIAL_CHARS_PATTERN.sub("", s).strip()
        cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None

    # ──────────────────────────────────────────────
    # 2.5 GENDER VALIDATION
    # ──────────────────────────────────────────────

    def _validate_gender(self, df, source_file, file_type, errors):
        """Validate gender column values."""
        from config.gender_mapping import GENDER_MAP
        count = 0
        for col in df.columns:
            if col.lower() not in {"sex", "gender", "geschlecht"}:
                continue
            for idx, val in df[col].items():
                if self._is_missing(val):
                    continue
                cleaned = str(val).strip()
                if cleaned not in GENDER_MAP and cleaned.lower() not in GENDER_MAP:
                    case_id = self._extract_case_id(df, idx)
                    self._log(
                        source_file=source_file,
                        case_id=case_id,
                        table_name=self._table_for_type(file_type),
                        column_name=col,
                        original_value=str(val),
                        cleaned_value=None,
                        error_type="GENDER_INVALID",
                        severity=Severity.MEDIUM,
                        action_taken=ActionTaken.FLAGGED,
                        row_number=idx,
                    )
                    count += 1
        if count:
            errors["GENDER_INVALID"] = errors.get("GENDER_INVALID", 0) + count

    # ──────────────────────────────────────────────
    # 2.6 ID VALIDATION
    # ──────────────────────────────────────────────

    def _validate_ids(self, df, source_file, file_type, errors):
        """Validate case_id and patient_id format."""
        count = 0
        if "case_id" in df.columns:
            for idx, val in df["case_id"].items():
                if self._is_missing(val):
                    continue
                cleaned = str(val).strip()
                if not CASE_ID_PATTERN.match(cleaned):
                    self._log(
                        source_file=source_file,
                        case_id=cleaned,
                        table_name=self._table_for_type(file_type),
                        column_name="case_id",
                        original_value=cleaned,
                        cleaned_value=None,
                        error_type="ID_INVALID",
                        severity=Severity.HIGH,
                        action_taken=ActionTaken.FLAGGED,
                        row_number=idx,
                    )
                    count += 1

        if "patient_id" in df.columns:
            for idx, val in df["patient_id"].items():
                if self._is_missing(val):
                    continue
                cleaned = str(val).strip()
                # Accept 6-digit, PAT-XXXX, or already prefixed IDs
                if not PATIENT_ID_PATTERN.match(cleaned) and not re.match(r'^(LAB|MOT|EPA|MED|NUR|ICD)_', cleaned):
                    self._log(
                        source_file=source_file,
                        case_id=self._extract_case_id(df, idx),
                        table_name=self._table_for_type(file_type),
                        column_name="patient_id",
                        original_value=cleaned,
                        cleaned_value=None,
                        error_type="ID_INVALID",
                        severity=Severity.HIGH,
                        action_taken=ActionTaken.FLAGGED,
                        row_number=idx,
                    )
                    count += 1

        if count:
            errors["ID_INVALID"] = errors.get("ID_INVALID", 0) + count

    # ──────────────────────────────────────────────
    # 2.8 DUPLICATE DETECTION
    # ──────────────────────────────────────────────

    def _validate_duplicates(self, df, source_file, file_type, errors):
        """Detect exact duplicates and partial duplicates."""
        count = 0

        # Exact duplicates
        dup_mask = df.duplicated(keep="first")
        dup_indices = df.index[dup_mask].tolist()
        for idx in dup_indices:
            case_id = self._extract_case_id(df, idx)
            self._log(
                source_file=source_file,
                case_id=case_id,
                table_name=self._table_for_type(file_type),
                column_name="__row__",
                original_value=f"duplicate_row_{idx}",
                cleaned_value=None,
                error_type="DUPLICATE",
                severity=Severity.LOW,
                action_taken=ActionTaken.FLAGGED,
                row_number=idx,
            )
            count += 1

        # Partial duplicates on (case_id/patient_id + timestamp) for motion data
        if file_type in ("device_motion", "device_1hz"):
            id_col = "patient_id" if "patient_id" in df.columns else "case_id"
            if id_col in df.columns and "timestamp" in df.columns:
                partial_dup = df.duplicated(subset=[id_col, "timestamp"], keep="first")
                partial_indices = df.index[partial_dup & ~dup_mask].tolist()
                for idx in partial_indices:
                    case_id = self._extract_case_id(df, idx)
                    self._log(
                        source_file=source_file,
                        case_id=case_id,
                        table_name=self._table_for_type(file_type),
                        column_name="__row__",
                        original_value=f"partial_duplicate_{idx}",
                        cleaned_value=None,
                        error_type="DUPLICATE_PARTIAL",
                        severity=Severity.MEDIUM,
                        action_taken=ActionTaken.FLAGGED,
                        row_number=idx,
                    )
                    count += 1

        if count:
            errors["DUPLICATE"] = errors.get("DUPLICATE", 0) + count

    # ──────────────────────────────────────────────
    # 2.10 LAB FLAG VALIDATION
    # ──────────────────────────────────────────────

    def _validate_lab_flags(self, df, source_file, file_type, errors):
        """Validate lab flag columns contain only valid values."""
        if file_type != "labs":
            return
        count = 0
        for col in LAB_FLAG_COLUMNS:
            if col not in df.columns:
                continue
            for idx, val in df[col].items():
                if self._is_missing(val):
                    continue
                cleaned = str(val).strip().upper()
                # Strip special characters
                cleaned_stripped = SPECIAL_CHARS_PATTERN.sub("", cleaned).strip()
                if cleaned_stripped not in VALID_LAB_FLAGS and cleaned_stripped not in {"H", "L", "HH", "LL", ""}:
                    case_id = self._extract_case_id(df, idx)
                    self._log(
                        source_file=source_file,
                        case_id=case_id,
                        table_name=self._table_for_type(file_type),
                        column_name=col,
                        original_value=str(val),
                        cleaned_value=None,
                        error_type="LAB_FLAG_INVALID",
                        severity=Severity.MEDIUM,
                        action_taken=ActionTaken.FLAGGED,
                        row_number=idx,
                    )
                    count += 1
        if count:
            errors["LAB_FLAG_INVALID"] = errors.get("LAB_FLAG_INVALID", 0) + count

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────

    def _log(self, source_file, case_id, table_name, column_name,
             original_value, cleaned_value, error_type, severity,
             action_taken, row_number=None, corrected_by=None):
        """Create and store an AuditLogEntry."""
        entry = AuditLogEntry(
            source_file=source_file,
            case_id=str(case_id) if case_id else "",
            table_name=table_name,
            column_name=column_name,
            original_value=str(original_value) if original_value is not None else "",
            cleaned_value=cleaned_value,
            error_type=error_type,
            severity=severity,
            action_taken=action_taken,
            corrected_by=corrected_by,
            row_number=row_number,
        )
        self.audit_log.append(entry)

    def _extract_case_id(self, df, idx) -> str:
        """Extract case_id from a row, falling back to patient_id or index."""
        for col in ("case_id", "coCaseId", "FallID"):
            if col in df.columns:
                val = df.at[idx, col]
                if not self._is_missing(val):
                    return str(val)
        for col in ("patient_id", "coPatientId", "PID"):
            if col in df.columns:
                val = df.at[idx, col]
                if not self._is_missing(val):
                    return str(val)
        return f"row_{idx}"

    def _table_for_type(self, file_type: str) -> str:
        """Map file type to target SQL table name."""
        mapping = {
            "labs": "tbImportLabsData",
            "icd10_ops": "tbImportIcd10Data",
            "device_motion": "tbImportDeviceMotionData",
            "device_1hz": "tbImportDevice1HzMotionData",
            "medication": "tbImportMedicationInpatientData",
            "nursing": "tbImportNursingDailyReportsData",
            "epaAC_german": "tbImportAcData",
            "epaAC_sap": "tbImportAcData",
            "epaAC_pivot": "tbImportAcData",
        }
        return mapping.get(file_type, "unknown")

    def get_audit_log(self) -> list[AuditLogEntry]:
        """Return all audit log entries."""
        return self.audit_log

    def get_audit_log_df(self) -> pd.DataFrame:
        """Return audit log as DataFrame for easy analysis."""
        if not self.audit_log:
            return pd.DataFrame()
        return pd.DataFrame([
            {
                "source_file": e.source_file,
                "case_id": e.case_id,
                "table_name": e.table_name,
                "column_name": e.column_name,
                "original_value": e.original_value,
                "cleaned_value": e.cleaned_value,
                "error_type": e.error_type,
                "severity": e.severity.value if isinstance(e.severity, Severity) else e.severity,
                "action_taken": e.action_taken.value if isinstance(e.action_taken, ActionTaken) else e.action_taken,
                "corrected_by": e.corrected_by,
                "row_number": e.row_number,
            }
            for e in self.audit_log
        ])
