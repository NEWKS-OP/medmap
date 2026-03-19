"""
Module 2B: Data Cleaning
Normalizes values (dates, gender, IDs), removes duplicates,
handles missing values and structural errors.
Logs all changes to AuditLogEntry via the validator's audit log.
"""

import logging
import re
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from contracts import (
    AuditLogEntry, Severity, ActionTaken, SourceQualityScore,
)
from config.clinical_rules import (
    CLINICAL_RANGES, VALID_LAB_FLAGS, MISSING_VALUE_TOKENS,
)
from config.gender_mapping import normalize_gender
from pipeline.validator import DataValidator

logger = logging.getLogger(__name__)

# PID prefix by file type
PID_PREFIX_MAP = {
    "labs": "LAB",
    "device_motion": "MOT",
    "device_1hz": "MOT",
    "medication": "MED",
    "nursing": "NUR",
    "epaAC_german": "EPA",
    "epaAC_sap": "EPA",
    "epaAC_pivot": "EPA",
    "icd10_ops": "ICD",
}

# Special characters to strip from numeric fields
SPECIAL_CHARS_PATTERN = re.compile(r'[üäöß^@$%#&*!?+=\[\]{}|\\/<>~`]', re.IGNORECASE)

# Lab flag columns
LAB_FLAG_COLUMNS = [
    "sodium_flag", "potassium_flag", "creatinine_flag", "egfr_flag",
    "glucose_flag", "hb_flag", "wbc_flag", "platelets_flag",
    "crp_flag", "alt_flag", "ast_flag", "bilirubin_flag",
    "albumin_flag", "inr_flag", "lactate_flag",
]

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


class DataCleaner:
    """Cleans and normalizes ingested DataFrames."""

    def __init__(self, validator: Optional[DataValidator] = None):
        self.validator = validator or DataValidator()
        self.cleaned_dataframes: dict[str, pd.DataFrame] = {}

    def clean_all(self, dataframes: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """Clean all DataFrames. Returns cleaned copies."""
        for filename, df in dataframes.items():
            try:
                cleaned = self.clean_dataframe(df, filename)
                self.cleaned_dataframes[filename] = cleaned
            except Exception as e:
                logger.error(f"Cleaning failed for {filename}: {e}")
                self.cleaned_dataframes[filename] = df.copy()
        return self.cleaned_dataframes

    def clean_dataframe(self, df: pd.DataFrame, filename: str) -> pd.DataFrame:
        """Clean a single DataFrame. Returns cleaned copy."""
        df = df.copy()
        file_type = df.attrs.get("file_type", "unknown")
        source_file = df.attrs.get("source_file", filename)

        # 2.2 Normalize missing values
        df = self._normalize_missing_values(df, source_file, file_type)

        # 2.3 Normalize dates
        df = self._normalize_dates(df, source_file, file_type)

        # 2.4 Clean clinical numeric values
        df = self._clean_clinical_numerics(df, source_file, file_type)

        # 2.4b Clean device-specific numeric columns (binary, movement index)
        df = self._clean_device_numerics(df, source_file, file_type)

        # 2.5 Normalize gender
        df = self._normalize_gender(df, source_file, file_type)

        # 2.6 Clean IDs
        df = self._clean_ids(df, source_file, file_type)

        # 2.6b Add PID prefixes
        df = self._add_pid_prefix(df, source_file, file_type)

        # 2.8 Remove duplicates
        df = self._remove_duplicates(df, source_file, file_type)

        # 2.10 Normalize lab flags
        df = self._normalize_lab_flags(df, source_file, file_type)

        # 2.11 Normalize shifts (nursing)
        df = self._normalize_shifts(df, source_file, file_type)

        # 2.12 Normalize event types (medication)
        df = self._normalize_event_types(df, source_file, file_type)

        # Preserve attrs
        df.attrs = {**df.attrs, "source_file": source_file, "file_type": file_type}
        return df

    # ──────────────────────────────────────────────
    # 2.2 MISSING VALUE NORMALIZATION
    # ──────────────────────────────────────────────

    def _normalize_missing_values(self, df, source_file, file_type):
        """Normalize all missing value representations to NaN."""
        for col in df.columns:
            mask = df[col].apply(self._is_missing_token)
            if mask.any():
                for idx in df.index[mask]:
                    original = df.at[idx, col]
                    if original is not None and not (isinstance(original, float) and np.isnan(original)):
                        self._log_change(
                            source_file, df, idx, file_type, col,
                            str(original), None,
                            "MISSING_NORMALIZED", Severity.LOW, ActionTaken.AUTO_CORRECT,
                        )
                df.loc[mask, col] = np.nan
        return df

    def _is_missing_token(self, val) -> bool:
        """Check if value matches a missing value token."""
        if val is None:
            return False  # Already None/NaN, no normalization needed
        if isinstance(val, float) and np.isnan(val):
            return False
        raw = str(val)
        # Whitespace-only strings are missing
        if raw.strip() == "" and raw != "":
            return True
        s = raw.strip().lower()
        return s in MISSING_VALUE_TOKENS and s != ""

    # ──────────────────────────────────────────────
    # 2.3 DATE NORMALIZATION
    # ──────────────────────────────────────────────

    def _normalize_dates(self, df, source_file, file_type):
        """Normalize date columns to ISO format."""
        date_cols = list(DATE_COLUMNS.get(file_type, []))
        for col in df.columns:
            if any(kw in col.lower() for kw in ["date", "datetime", "timestamp", "datum", "aufn", "entlass"]):
                if col not in date_cols:
                    date_cols.append(col)

        for col in date_cols:
            if col not in df.columns:
                continue
            # Convert column to object dtype to avoid FutureWarning
            # when inserting string dates into numeric columns
            df[col] = df[col].astype(object)
            for idx in df.index:
                val = df.at[idx, col]
                if pd.isna(val) if isinstance(val, float) else val is None:
                    continue
                s = str(val).strip()
                if not s:
                    continue
                parsed = self._try_parse_date(s)
                if parsed is not None:
                    # Reject dates outside valid range
                    if parsed.year < 2000 or parsed.year > 2030:
                        self._log_change(
                            source_file, df, idx, file_type, col,
                            s, None,
                            "DATE_OUT_OF_RANGE", Severity.MEDIUM, ActionTaken.QUARANTINE,
                        )
                        df.at[idx, col] = None
                        continue
                    iso = parsed.strftime("%Y-%m-%d %H:%M:%S") if parsed.hour or parsed.minute else parsed.strftime("%Y-%m-%d")
                    if iso != s:
                        self._log_change(
                            source_file, df, idx, file_type, col,
                            s, iso,
                            "DATE_NORMALIZED", Severity.LOW, ActionTaken.AUTO_CORRECT,
                        )
                    df.at[idx, col] = iso
                else:
                    self._log_change(
                        source_file, df, idx, file_type, col,
                        s, None,
                        "INVALID_DATE", Severity.HIGH, ActionTaken.QUARANTINE,
                    )
                    df.at[idx, col] = None
        return df

    def _try_parse_date(self, val: str) -> Optional[datetime]:
        """Try to parse a date string through multiple formats."""
        val = val.strip()
        if not val:
            return None

        # Reject impossible dates
        impossible_patterns = [
            r'^99\.99\.9999$', r'^00[./]00[./]0000$',
            r'^0000', r'9999\.9999',
        ]
        for pat in impossible_patterns:
            if re.match(pat, val):
                return None

        # Pass 1: ISO
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

        # Pass 4: German textual months
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

        # Pass 5: dateutil fallback
        try:
            from dateutil import parser as dateutil_parser
            d = dateutil_parser.parse(val, dayfirst=True)
            if d.year < 2000 or d.year > 2030:
                return None
            return d
        except Exception:
            pass

        return None

    # ──────────────────────────────────────────────
    # 2.4 CLINICAL NUMERIC CLEANING
    # ──────────────────────────────────────────────

    def _clean_clinical_numerics(self, df, source_file, file_type):
        """Clean numeric clinical columns: strip special chars, validate ranges."""
        for col, (low, high) in CLINICAL_RANGES.items():
            if col not in df.columns:
                continue

            # Store raw values before cleaning
            raw_col = f"{col}_raw"
            if raw_col not in df.columns:
                df[raw_col] = df[col].copy()

            for idx in df.index:
                val = df.at[idx, col]
                if pd.isna(val) if isinstance(val, float) else val is None:
                    continue

                num_val = self._try_parse_numeric(val)
                if num_val is None:
                    # Non-numeric contamination — try stripping special chars
                    cleaned_str = SPECIAL_CHARS_PATTERN.sub("", str(val)).strip().replace(",", ".")
                    try:
                        num_val = float(cleaned_str)
                    except (ValueError, TypeError):
                        self._log_change(
                            source_file, df, idx, file_type, col,
                            str(val), None,
                            "NON_NUMERIC_CLEANED", Severity.HIGH, ActionTaken.QUARANTINE,
                        )
                        df.at[idx, col] = np.nan
                        continue

                    # Successfully cleaned
                    self._log_change(
                        source_file, df, idx, file_type, col,
                        str(val), str(num_val),
                        "SPECIAL_CHARS_REMOVED", Severity.LOW, ActionTaken.AUTO_CORRECT,
                    )
                    df.at[idx, col] = num_val

                # Check range
                if num_val is not None and (num_val < low or num_val > high):
                    self._log_change(
                        source_file, df, idx, file_type, col,
                        str(val), None,
                        "CLINICAL_OUTLIER", Severity.CRITICAL, ActionTaken.QUARANTINE,
                    )
                    df.at[idx, col] = np.nan
                elif num_val is not None and not isinstance(df.at[idx, col], float):
                    # Ensure it's stored as numeric
                    df.at[idx, col] = num_val
        return df

    # Device-specific numeric columns that need special char stripping
    DEVICE_NUMERIC_COLS = {
        "fall_event_0_1": (0, 1),
        "bed_exit_detected_0_1": (0, 1),
        "movement_index_0_100": (0, 100),
        "micro_movements_count": (0, 100000),
        "post_fall_immobility_minutes": (0, 1440),
        "accel_x": (-100, 100),
        "accel_y": (-100, 100),
        "accel_z": (-100, 100),
        "accel_magnitude": (0, 200),
        "movement_score": (0, 100),
        "pressure_zone_1": (0, 10000),
        "pressure_zone_2": (0, 10000),
        "pressure_zone_3": (0, 10000),
        "pressure_zone_4": (0, 10000),
        "is_prn_0_1": (0, 1),
    }

    def _clean_device_numerics(self, df, source_file, file_type):
        """Clean device-specific numeric columns: strip special chars, coerce to float."""
        for col, (low, high) in self.DEVICE_NUMERIC_COLS.items():
            if col not in df.columns:
                continue
            # Skip columns already in CLINICAL_RANGES (handled elsewhere)
            if col in CLINICAL_RANGES:
                continue

            for idx in df.index:
                val = df.at[idx, col]
                if pd.isna(val) if isinstance(val, float) else val is None:
                    continue

                num_val = self._try_parse_numeric(val)
                if num_val is None:
                    # Strip special chars and retry
                    cleaned_str = SPECIAL_CHARS_PATTERN.sub("", str(val)).strip().replace(",", ".")
                    try:
                        num_val = float(cleaned_str)
                    except (ValueError, TypeError):
                        self._log_change(
                            source_file, df, idx, file_type, col,
                            str(val), None,
                            "NON_NUMERIC_CLEANED", Severity.HIGH, ActionTaken.QUARANTINE,
                        )
                        df.at[idx, col] = np.nan
                        continue

                    self._log_change(
                        source_file, df, idx, file_type, col,
                        str(val), str(num_val),
                        "SPECIAL_CHARS_REMOVED", Severity.LOW, ActionTaken.AUTO_CORRECT,
                    )
                    df.at[idx, col] = num_val

                # Validate range
                if num_val is not None and (num_val < low or num_val > high):
                    self._log_change(
                        source_file, df, idx, file_type, col,
                        str(val), None,
                        "DEVICE_VALUE_OUTLIER", Severity.HIGH, ActionTaken.QUARANTINE,
                    )
                    df.at[idx, col] = np.nan
                elif num_val is not None and not isinstance(df.at[idx, col], float):
                    df.at[idx, col] = num_val
        return df

    def _try_parse_numeric(self, val) -> Optional[float]:
        """Try to parse a value as float."""
        if isinstance(val, (int, float)):
            if isinstance(val, float) and np.isnan(val):
                return None
            return float(val)
        s = str(val).strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            s = s.replace(",", ".")
            try:
                return float(s)
            except ValueError:
                return None

    # ──────────────────────────────────────────────
    # 2.5 GENDER NORMALIZATION
    # ──────────────────────────────────────────────

    def _normalize_gender(self, df, source_file, file_type):
        """Normalize gender column to M/F/None."""
        for col in df.columns:
            if col.lower() not in {"sex", "gender", "geschlecht"}:
                continue
            for idx in df.index:
                val = df.at[idx, col]
                if pd.isna(val) if isinstance(val, float) else val is None:
                    continue
                raw = str(val)
                original = raw.strip()
                normalized = normalize_gender(original)
                if normalized != raw:
                    if normalized != original:
                        self._log_change(
                            source_file, df, idx, file_type, col,
                            original, normalized,
                            "GENDER_NORMALIZED", Severity.LOW, ActionTaken.AUTO_CORRECT,
                        )
                    df.at[idx, col] = normalized
                if normalized is None and original and original.lower() not in MISSING_VALUE_TOKENS:
                    self._log_change(
                        source_file, df, idx, file_type, col,
                        original, None,
                        "GENDER_INVALID", Severity.MEDIUM, ActionTaken.FLAGGED,
                    )
        return df

    # ──────────────────────────────────────────────
    # 2.6 ID CLEANING + PID PREFIXES
    # ──────────────────────────────────────────────

    def _clean_ids(self, df, source_file, file_type):
        """Clean case_id and patient_id: strip whitespace, special chars."""
        for col in ("case_id", "patient_id"):
            if col not in df.columns:
                continue
            for idx in df.index:
                val = df.at[idx, col]
                if pd.isna(val) if isinstance(val, float) else val is None:
                    continue
                original = str(val)
                cleaned = original.strip().replace("\t", "").replace("\n", "").replace("\r", "")
                # Remove leading/trailing special chars
                cleaned = re.sub(r'^[^a-zA-Z0-9]+', '', cleaned)
                cleaned = re.sub(r'[^a-zA-Z0-9]+$', '', cleaned)
                if cleaned != original:
                    self._log_change(
                        source_file, df, idx, file_type, col,
                        original, cleaned,
                        "ID_CLEANED", Severity.LOW, ActionTaken.AUTO_CORRECT,
                    )
                    df.at[idx, col] = cleaned
        return df

    def _add_pid_prefix(self, df, source_file, file_type):
        """Add source prefix to patient_id for cross-source disambiguation."""
        from config.settings import PID_PREFIX_STRATEGY
        if not PID_PREFIX_STRATEGY:
            return df
        prefix = PID_PREFIX_MAP.get(file_type)
        if not prefix or "patient_id" not in df.columns:
            return df

        # Convert column to object dtype to avoid FutureWarning when
        # inserting string values into a numeric column
        df["patient_id"] = df["patient_id"].astype(object)

        for idx in df.index:
            val = df.at[idx, "patient_id"]
            if pd.isna(val) if isinstance(val, float) else val is None:
                continue
            s = str(val).strip()
            # Don't double-prefix
            if s.startswith(f"{prefix}_"):
                continue
            # Don't prefix if already prefixed by another source
            if re.match(r'^(LAB|MOT|EPA|MED|NUR|ICD)_', s):
                continue
            new_val = f"{prefix}_{s}"
            self._log_change(
                source_file, df, idx, file_type, "patient_id",
                s, new_val,
                "PID_PREFIXED", Severity.LOW, ActionTaken.AUTO_CORRECT,
            )
            df.at[idx, "patient_id"] = new_val
        return df

    # ──────────────────────────────────────────────
    # 2.7 PATIENT_ID + DATETIME -> CASE_ID MAPPING
    # ──────────────────────────────────────────────

    def build_case_id_lookup(self, dataframes: dict[str, pd.DataFrame]) -> dict:
        """Build a lookup table: (patient_id, date) -> case_id from files that have both."""
        lookup = {}
        for filename, df in dataframes.items():
            if "case_id" not in df.columns or "patient_id" not in df.columns:
                continue
            date_col = None
            for col in ["admission_date", "specimen_datetime", "timestamp", "report_date"]:
                if col in df.columns:
                    date_col = col
                    break
            for idx in df.index:
                case_id = df.at[idx, "case_id"]
                pid = df.at[idx, "patient_id"]
                if pd.isna(case_id) or pd.isna(pid):
                    continue
                case_id = str(case_id).strip()
                pid = str(pid).strip()
                if date_col:
                    date_val = df.at[idx, date_col]
                    if not pd.isna(date_val):
                        date_str = str(date_val).strip()[:10]
                        lookup[(pid, date_str)] = case_id
                # Also store by patient_id alone as fallback
                if pid not in lookup:
                    lookup[pid] = case_id
        return lookup

    def map_missing_case_ids(self, dataframes: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """For DataFrames without case_id, try to map from patient_id + datetime."""
        lookup = self.build_case_id_lookup(dataframes)
        result = {}
        for filename, df in dataframes.items():
            if "case_id" in df.columns:
                # Check for missing case_ids in rows
                has_missing = df["case_id"].isna().any() or (df["case_id"].astype(str).str.strip() == "").any()
                if not has_missing:
                    result[filename] = df
                    continue

            df = df.copy()
            file_type = df.attrs.get("file_type", "unknown")
            source_file = df.attrs.get("source_file", filename)

            if "case_id" not in df.columns:
                df["case_id"] = np.nan

            if "patient_id" not in df.columns:
                result[filename] = df
                continue

            date_col = None
            for col in ["timestamp", "admission_datetime", "report_date", "specimen_datetime",
                         "order_start_datetime", "administration_datetime"]:
                if col in df.columns:
                    date_col = col
                    break

            mapped_count = 0
            for idx in df.index:
                case_val = df.at[idx, "case_id"]
                if not pd.isna(case_val) and str(case_val).strip():
                    continue
                pid = df.at[idx, "patient_id"]
                if pd.isna(pid):
                    continue
                pid_str = str(pid).strip()

                # Try patient_id + date
                mapped = False
                if date_col:
                    date_val = df.at[idx, date_col]
                    if not pd.isna(date_val):
                        date_str = str(date_val).strip()[:10]
                        case_id = lookup.get((pid_str, date_str))
                        if case_id:
                            df.at[idx, "case_id"] = case_id
                            self._log_change(
                                source_file, df, idx, file_type, "case_id",
                                "", case_id,
                                "CASE_ID_MAPPED", Severity.LOW, ActionTaken.AUTO_CORRECT,
                            )
                            mapped_count += 1
                            mapped = True

                # Fallback: patient_id only
                if not mapped:
                    case_id = lookup.get(pid_str)
                    if case_id:
                        df.at[idx, "case_id"] = case_id
                        self._log_change(
                            source_file, df, idx, file_type, "case_id",
                            "", case_id,
                            "CASE_ID_MAPPED_PID_ONLY", Severity.MEDIUM, ActionTaken.AUTO_CORRECT,
                        )
                        mapped_count += 1

            if mapped_count:
                logger.info(f"Mapped {mapped_count} case_ids in {filename}")
            df.attrs = {**df.attrs, "source_file": source_file, "file_type": file_type}
            result[filename] = df
        return result

    # ──────────────────────────────────────────────
    # 2.8 DUPLICATE REMOVAL
    # ──────────────────────────────────────────────

    def _remove_duplicates(self, df, source_file, file_type):
        """Remove exact duplicate rows, keep first."""
        dup_mask = df.duplicated(keep="first")
        dup_count = dup_mask.sum()
        if dup_count > 0:
            dup_indices = df.index[dup_mask].tolist()
            for idx in dup_indices:
                case_id = self._extract_case_id(df, idx)
                self._log_change(
                    source_file, df, idx, file_type, "__row__",
                    f"duplicate_row_{idx}", "removed",
                    "DUPLICATE_REMOVED", Severity.LOW, ActionTaken.AUTO_CORRECT,
                )
            df = df[~dup_mask].reset_index(drop=True)
            logger.info(f"Removed {dup_count} duplicates from {source_file}")

        # For motion data: also remove partial duplicates on (patient_id + timestamp)
        if file_type in ("device_motion", "device_1hz"):
            id_col = "patient_id" if "patient_id" in df.columns else "case_id"
            if id_col in df.columns and "timestamp" in df.columns:
                partial_dup = df.duplicated(subset=[id_col, "timestamp"], keep="first")
                partial_count = partial_dup.sum()
                if partial_count > 0:
                    for idx in df.index[partial_dup]:
                        self._log_change(
                            source_file, df, idx, file_type, "__row__",
                            f"partial_dup_{idx}", "removed",
                            "PARTIAL_DUPLICATE_REMOVED", Severity.MEDIUM, ActionTaken.AUTO_CORRECT,
                        )
                    df = df[~partial_dup].reset_index(drop=True)
                    logger.info(f"Removed {partial_count} partial duplicates from {source_file}")
        return df

    # ──────────────────────────────────────────────
    # 2.10 LAB FLAG NORMALIZATION
    # ──────────────────────────────────────────────

    def _normalize_lab_flags(self, df, source_file, file_type):
        """Normalize lab flag columns to H/L/HH/LL or None."""
        if file_type != "labs":
            return df
        for col in LAB_FLAG_COLUMNS:
            if col not in df.columns:
                continue
            for idx in df.index:
                val = df.at[idx, col]
                if pd.isna(val) if isinstance(val, float) else val is None:
                    continue
                raw = str(val)
                original = raw.strip()
                # Strip special chars
                cleaned = SPECIAL_CHARS_PATTERN.sub("", original).strip().upper()
                if cleaned in VALID_LAB_FLAGS:
                    if raw != cleaned:
                        self._log_change(
                            source_file, df, idx, file_type, col,
                            raw, cleaned if cleaned else None,
                            "LAB_FLAG_CLEANED", Severity.LOW, ActionTaken.AUTO_CORRECT,
                        )
                        df.at[idx, col] = cleaned if cleaned else np.nan
                else:
                    self._log_change(
                        source_file, df, idx, file_type, col,
                        original, None,
                        "LAB_FLAG_INVALID", Severity.MEDIUM, ActionTaken.QUARANTINE,
                    )
                    df.at[idx, col] = np.nan
        return df

    # ──────────────────────────────────────────────
    # DETECT PID CONFLICTS
    # ──────────────────────────────────────────────

    def detect_pid_conflicts(self, dataframes: dict[str, pd.DataFrame]) -> list[AuditLogEntry]:
        """Detect when same patient_id has contradictory data across sources."""
        pid_info: dict[str, list[dict]] = {}
        conflicts = []

        for filename, df in dataframes.items():
            if "patient_id" not in df.columns:
                continue
            file_type = df.attrs.get("file_type", "unknown")
            gender_col = None
            for col in df.columns:
                if col.lower() in {"sex", "gender", "geschlecht"}:
                    gender_col = col
                    break

            for idx in df.index:
                pid = df.at[idx, "patient_id"]
                if pd.isna(pid):
                    continue
                pid_str = str(pid).strip()
                # Strip prefix for comparison
                raw_pid = re.sub(r'^(LAB|MOT|EPA|MED|NUR|ICD)_', '', pid_str)

                info = {"source": filename, "file_type": file_type}
                if gender_col and gender_col in df.columns:
                    g = df.at[idx, gender_col]
                    if not pd.isna(g):
                        info["gender"] = str(g).strip()

                pid_info.setdefault(raw_pid, []).append(info)

        # Check for conflicts
        for pid, entries in pid_info.items():
            genders = set()
            for e in entries:
                if "gender" in e:
                    genders.add(e["gender"])
            if len(genders) > 1:
                entry = AuditLogEntry(
                    source_file="cross_source",
                    case_id=pid,
                    table_name="cross_source",
                    column_name="patient_id",
                    original_value=pid,
                    cleaned_value=None,
                    error_type="PID_CONFLICT",
                    severity=Severity.HIGH,
                    action_taken=ActionTaken.FLAGGED,
                    corrected_by=None,
                    row_number=None,
                )
                conflicts.append(entry)
                self.validator.audit_log.append(entry)

        return conflicts

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────

    def _log_change(self, source_file, df, idx, file_type, col,
                    original, cleaned, error_type, severity, action_taken):
        """Log a cleaning change to the validator's audit log."""
        case_id = self._extract_case_id(df, idx)
        entry = AuditLogEntry(
            source_file=source_file,
            case_id=case_id,
            table_name=self._table_for_type(file_type),
            column_name=col,
            original_value=str(original) if original is not None else "",
            cleaned_value=str(cleaned) if cleaned is not None else None,
            error_type=error_type,
            severity=severity,
            action_taken=action_taken,
            corrected_by="cleaner",
            row_number=idx if isinstance(idx, int) else None,
        )
        self.validator.audit_log.append(entry)

    # ──────────────────────────────────────────────
    # 2.11 SHIFT NORMALIZATION
    # ──────────────────────────────────────────────

    SHIFT_MAP = {
        "early": "Early", "early shift": "Early", "frühschicht": "Early",
        "fruhschicht": "Early", "fruehschicht": "Early", "frhschicht": "Early",
        "late": "Late", "late shift": "Late", "spätschicht": "Late",
        "spatschicht": "Late", "spaetschicht": "Late", "sptschicht": "Late",
        "night": "Night", "night shift": "Night", "nachtschicht": "Night",
    }

    def _normalize_shifts(self, df, source_file, file_type):
        """Normalize shift values to Early/Late/Night."""
        shift_col = None
        for col in ("shift", "Shift", "coShift"):
            if col in df.columns:
                shift_col = col
                break
        if shift_col is None:
            return df

        for idx in df.index:
            val = df.at[idx, shift_col]
            if pd.isna(val) if isinstance(val, float) else val is None:
                continue
            raw = str(val)
            # First try matching with original value (preserves umlauts)
            normalized = self.SHIFT_MAP.get(raw.strip().lower())
            if normalized is None:
                # Then try with special chars stripped
                cleaned = SPECIAL_CHARS_PATTERN.sub("", raw).strip()
                normalized = self.SHIFT_MAP.get(cleaned.lower())
            if normalized is None:
                # Try partial match on both raw and cleaned
                raw_lower = raw.strip().lower()
                cleaned_lower = SPECIAL_CHARS_PATTERN.sub("", raw).strip().lower()
                if any(k in s for s in (raw_lower, cleaned_lower) for k in ("early", "früh", "fruh", "frh")):
                    normalized = "Early"
                elif any(k in s for s in (raw_lower, cleaned_lower) for k in ("late", "spät", "spat", "spt")):
                    normalized = "Late"
                elif any(k in s for s in (raw_lower, cleaned_lower) for k in ("night", "nacht")):
                    normalized = "Night"
            if normalized and normalized != raw:
                df.at[idx, shift_col] = normalized
                self._log_change(
                    source_file, df, idx, file_type, shift_col,
                    raw, normalized,
                    "SHIFT_NORMALIZED", Severity.LOW, ActionTaken.AUTO_CORRECT,
                )
            elif normalized is None and raw.strip():
                df.at[idx, shift_col] = np.nan
                self._log_change(
                    source_file, df, idx, file_type, shift_col,
                    raw, None,
                    "SHIFT_INVALID", Severity.MEDIUM, ActionTaken.FLAGGED,
                )
        return df

    # ──────────────────────────────────────────────
    # 2.12 EVENT TYPE NORMALIZATION
    # ──────────────────────────────────────────────

    VALID_EVENT_TYPES = {"ORDER", "CHANGE", "ADMIN"}

    def _normalize_event_types(self, df, source_file, file_type):
        """Normalize medication event/record types to ORDER/CHANGE/ADMIN."""
        type_col = None
        for col in ("event_type", "record_type", "rec_type"):
            if col in df.columns:
                type_col = col
                break
        if type_col is None:
            return df

        for idx in df.index:
            val = df.at[idx, type_col]
            if pd.isna(val) if isinstance(val, float) else val is None:
                continue
            raw = str(val)
            # Strip special chars
            cleaned = SPECIAL_CHARS_PATTERN.sub("", raw).strip().upper()
            if cleaned in self.VALID_EVENT_TYPES:
                if cleaned != raw:
                    df.at[idx, type_col] = cleaned
                    self._log_change(
                        source_file, df, idx, file_type, type_col,
                        raw, cleaned,
                        "EVENT_TYPE_NORMALIZED", Severity.LOW, ActionTaken.AUTO_CORRECT,
                    )
            elif raw.strip():
                # Try to extract valid type from contaminated value
                extracted = None
                for et in self.VALID_EVENT_TYPES:
                    if et in cleaned:
                        extracted = et
                        break
                if extracted:
                    df.at[idx, type_col] = extracted
                    self._log_change(
                        source_file, df, idx, file_type, type_col,
                        raw, extracted,
                        "EVENT_TYPE_EXTRACTED", Severity.LOW, ActionTaken.AUTO_CORRECT,
                    )
                else:
                    df.at[idx, type_col] = np.nan
                    self._log_change(
                        source_file, df, idx, file_type, type_col,
                        raw, None,
                        "EVENT_TYPE_INVALID", Severity.MEDIUM, ActionTaken.FLAGGED,
                    )
        return df

    def _extract_case_id(self, df, idx) -> str:
        for col in ("case_id", "coCaseId", "FallID"):
            if col in df.columns:
                val = df.at[idx, col]
                if not pd.isna(val) if isinstance(val, float) else val is not None:
                    return str(val)
        for col in ("patient_id", "coPatientId", "PID"):
            if col in df.columns:
                val = df.at[idx, col]
                if not pd.isna(val) if isinstance(val, float) else val is not None:
                    return str(val)
        return f"row_{idx}"

    def _table_for_type(self, file_type: str) -> str:
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
        return self.validator.audit_log

    def get_quality_scores(self) -> dict[str, SourceQualityScore]:
        return self.validator.quality_scores
