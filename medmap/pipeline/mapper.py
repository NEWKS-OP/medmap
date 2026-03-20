"""
Module 3: Data Mapping
Maps cleaned source data to the 7 target SQL tables using hardcoded mappings.
Merges multiple sources of the same type (base + split clinic files).
"""

import logging
import re
from typing import Optional

import numpy as np
import pandas as pd

from config.schema_mapping import (
    LABS_MAPPING, ICD10_MAPPING, DEVICE_MOTION_MAPPING,
    DEVICE_1HZ_MAPPING, MEDICATION_MAPPING, NURSING_MAPPING,
    CASE_DATA_MAPPING, EPAC_GERMAN_MAPPING,
)

logger = logging.getLogger(__name__)


class DataMapper:
    """Maps cleaned DataFrames to the 7 target SQL tables."""

    NURSING_NOTE_MAX_LEN = 256

    def __init__(self, iid_sid_map: Optional[pd.DataFrame] = None):
        self.iid_sid_map = iid_sid_map
        self._sap_decoder: Optional[dict] = None
        self._sid_to_iid: Optional[dict] = None
        self._pid_lookup: Optional[dict] = None
        self.mapped_tables: dict[str, pd.DataFrame] = {}
        self.mapping_warnings: list[str] = []

    @staticmethod
    def _safe_isna(v) -> bool:
        """Check if value is NA/NaN/NaT, handling type errors."""
        if v is None:
            return True
        try:
            return bool(pd.isna(v))
        except (TypeError, ValueError):
            return False

    @property
    def sap_decoder(self) -> dict:
        """Lazy-load SAP IID -> English name decoder."""
        if self._sap_decoder is None:
            if self.iid_sid_map is not None:
                try:
                    self._sap_decoder = dict(zip(
                        self.iid_sid_map["ItmIID"],
                        self.iid_sid_map["ItmName255_EN"],
                    ))
                except KeyError:
                    self._sap_decoder = {}
            else:
                self._sap_decoder = {}
        return self._sap_decoder

    @property
    def sid_to_iid(self) -> dict:
        """Lazy-load SID -> IID decoder for pivot format."""
        if self._sid_to_iid is None:
            if self.iid_sid_map is not None:
                try:
                    self._sid_to_iid = dict(zip(
                        self.iid_sid_map["ItmSID"],
                        self.iid_sid_map["ItmIID"],
                    ))
                except KeyError:
                    self._sid_to_iid = {}
            else:
                self._sid_to_iid = {}
        return self._sid_to_iid

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────

    def _group_by_type(self, dataframes: dict[str, pd.DataFrame]) -> dict[str, list[pd.DataFrame]]:
        """Group DataFrames by their detected file type."""
        by_type: dict[str, list[pd.DataFrame]] = {}
        for fname, df in dataframes.items():
            file_type = df.attrs.get("file_type", "unknown")
            by_type.setdefault(file_type, []).append(df)
        return by_type

    def _merge_sources(self, dfs: list[pd.DataFrame]) -> pd.DataFrame:
        """Merge multiple DataFrames of the same type into one."""
        if not dfs:
            return pd.DataFrame()
        if len(dfs) == 1:
            return dfs[0].copy()
        merged = pd.concat(dfs, ignore_index=True)
        return merged

    def _apply_column_mapping(self, df: pd.DataFrame, mapping: dict,
                               table_name: str) -> pd.DataFrame:
        """Rename columns using mapping dict. Only keep mapped columns."""
        # Find which source columns exist in df
        rename_map = {}
        for src_col, tgt_col in mapping.items():
            if src_col in df.columns:
                rename_map[src_col] = tgt_col

        df = df.rename(columns=rename_map)
        # Drop any duplicate columns created by rename
        df = df.loc[:, ~df.columns.duplicated()]

        # Keep only target columns that exist after rename
        target_cols = set(mapping.values())
        existing = [c for c in df.columns if c in target_cols]
        if not existing:
            self.mapping_warnings.append(
                f"{table_name}: no columns matched mapping"
            )
            return pd.DataFrame()

        df = df[existing].copy()
        return df

    def _extract_case_id_numeric(self, val) -> Optional[int]:
        """Extract numeric part from case_id.

        Handles compound formats like 'CASE-0135-01' -> 13501
        and simple formats like 'CASE-0042' -> 42.
        """
        if self._safe_isna(val):
            return None
        s = str(val).strip()
        # Extract all digit groups and concatenate them
        # e.g., "CASE-0135-01" -> "013501" -> 13501
        # e.g., "CASE-0042" -> "0042" -> 42
        digits = re.findall(r'\d+', s)
        if digits:
            try:
                return int("".join(digits))
            except ValueError:
                return None
        return None

    def _convert_case_id_column(self, df: pd.DataFrame,
                                 col: str = "coCaseId") -> pd.DataFrame:
        """Convert coCaseId from 'CASE-XXXX' string to integer for FK."""
        if col not in df.columns:
            return df
        df[col] = df[col].apply(self._extract_case_id_numeric)
        return df

    def _to_string_columns(self, df: pd.DataFrame,
                            exclude: set = None) -> pd.DataFrame:
        """Convert all columns to string (for nvarchar storage), except excluded."""
        exclude = exclude or set()
        def _to_str(v):
            if DataMapper._safe_isna(v):
                return None
            # Convert float X.0 to integer string to preserve 0/1 binary values
            if isinstance(v, float) and v == int(v):
                return str(int(v))
            return str(v)
        for col in df.columns:
            if col in exclude:
                continue
            df[col] = df[col].apply(_to_str)
        return df

    # ──────────────────────────────────────────────
    # TABLE MAPPERS
    # ──────────────────────────────────────────────

    def map_labs(self, dfs: list[pd.DataFrame]) -> pd.DataFrame:
        """Map labs sources to tbImportLabsData."""
        merged = self._merge_sources(dfs)
        if merged.empty:
            return pd.DataFrame()

        result = self._apply_column_mapping(merged, LABS_MAPPING, "tbImportLabsData")
        if result.empty:
            return result

        result = self._convert_case_id_column(result)
        # All lab columns are nvarchar in target schema
        result = self._to_string_columns(result, exclude={"coCaseId"})

        logger.info("Mapped tbImportLabsData: %d rows, %d columns",
                     len(result), len(result.columns))
        return result

    def map_icd10(self, dfs: list[pd.DataFrame]) -> pd.DataFrame:
        """Map icd10_ops sources to tbImportIcd10Data."""
        merged = self._merge_sources(dfs)
        if merged.empty:
            return pd.DataFrame()

        result = self._apply_column_mapping(merged, ICD10_MAPPING, "tbImportIcd10Data")
        if result.empty:
            return result

        result = self._convert_case_id_column(result)
        result = self._to_string_columns(result, exclude={"coCaseId"})

        logger.info("Mapped tbImportIcd10Data: %d rows, %d columns",
                     len(result), len(result.columns))
        return result

    def map_device_motion(self, dfs: list[pd.DataFrame]) -> pd.DataFrame:
        """Map device_motion sources to tbImportDeviceMotionData."""
        merged = self._merge_sources(dfs)
        if merged.empty:
            return pd.DataFrame()

        result = self._apply_column_mapping(
            merged, DEVICE_MOTION_MAPPING, "tbImportDeviceMotionData"
        )
        if result.empty:
            return result

        # Per spec: coCaseId ← patient_id for device data
        if "coPatient_id" in result.columns:
            if "coCaseId" not in result.columns or result["coCaseId"].isna().all():
                result["coCaseId"] = result["coPatient_id"]

        result = self._convert_case_id_column(result)
        # Resolve missing coCaseId via patient_id lookup
        if self._pid_lookup:
            result = self._resolve_case_ids(result, self._pid_lookup)
        result = self._to_string_columns(result, exclude={"coCaseId"})

        logger.info("Mapped tbImportDeviceMotionData: %d rows, %d columns",
                     len(result), len(result.columns))
        return result

    def map_device_1hz(self, dfs: list[pd.DataFrame]) -> pd.DataFrame:
        """Map device_1hz sources to tbImportDevice1HzMotionData."""
        merged = self._merge_sources(dfs)
        if merged.empty:
            return pd.DataFrame()

        result = self._apply_column_mapping(
            merged, DEVICE_1HZ_MAPPING, "tbImportDevice1HzMotionData"
        )
        if result.empty:
            return result

        # Per spec: coCaseId ← patient_id for device data
        if "coPatient_id" in result.columns:
            if "coCaseId" not in result.columns or result["coCaseId"].isna().all():
                result["coCaseId"] = result["coPatient_id"]

        result = self._convert_case_id_column(result)
        # Resolve missing coCaseId via patient_id lookup
        if self._pid_lookup:
            result = self._resolve_case_ids(result, self._pid_lookup)
        result = self._to_string_columns(result, exclude={"coCaseId"})

        logger.info("Mapped tbImportDevice1HzMotionData: %d rows, %d columns",
                     len(result), len(result.columns))
        return result

    def map_medication(self, dfs: list[pd.DataFrame]) -> pd.DataFrame:
        """Map medication sources to tbImportMedicationInpatientData."""
        merged = self._merge_sources(dfs)
        if merged.empty:
            return pd.DataFrame()

        # Normalize event_type/record_type column name
        if "event_type" in merged.columns and "record_type" not in merged.columns:
            merged = merged.rename(columns={"event_type": "record_type"})

        result = self._apply_column_mapping(
            merged, MEDICATION_MAPPING, "tbImportMedicationInpatientData"
        )
        if result.empty:
            return result

        # Medication data often lacks case_id; fall back to patient_id or encounter_id
        needs_fallback = "coCaseId" not in result.columns or result["coCaseId"].isna().all()
        if needs_fallback:
            if "coPatient_id" in result.columns:
                result["coCaseId"] = result["coPatient_id"]
            elif "coEncounter_id" in result.columns:
                result["coCaseId"] = result["coEncounter_id"]

        result = self._convert_case_id_column(result)
        # Resolve missing coCaseId via patient_id lookup
        if self._pid_lookup:
            result = self._resolve_case_ids(result, self._pid_lookup)
        result = self._to_string_columns(result, exclude={"coCaseId"})

        logger.info("Mapped tbImportMedicationInpatientData: %d rows, %d columns",
                     len(result), len(result.columns))
        return result

    def map_nursing(self, dfs: list[pd.DataFrame]) -> pd.DataFrame:
        """Map nursing sources to tbImportNursingDailyReportsData."""
        merged = self._merge_sources(dfs)
        if merged.empty:
            return pd.DataFrame()

        # Also map note_text -> nursing_note_free_text if present
        if "note_text" in merged.columns and "nursing_note_free_text" not in merged.columns:
            merged = merged.rename(columns={"note_text": "nursing_note_free_text"})

        result = self._apply_column_mapping(
            merged, NURSING_MAPPING, "tbImportNursingDailyReportsData"
        )
        if result.empty:
            return result

        # Fall back to patient_id for coCaseId if missing or all-null
        if "coPatient_id" in result.columns:
            if "coCaseId" not in result.columns or result["coCaseId"].isna().all():
                result["coCaseId"] = result["coPatient_id"]

        result = self._convert_case_id_column(result)
        # Resolve missing coCaseId via patient_id lookup
        if self._pid_lookup:
            result = self._resolve_case_ids(result, self._pid_lookup)

        # Truncate nursing notes to 256 chars (nvarchar(256) in schema)
        if "coNursing_note_free_text" in result.columns:
            result["coNursing_note_free_text"] = result["coNursing_note_free_text"].apply(
                lambda v: None if self._safe_isna(v) else str(v)[:self.NURSING_NOTE_MAX_LEN]
            )

        result = self._to_string_columns(result, exclude={"coCaseId"})

        logger.info("Mapped tbImportNursingDailyReportsData: %d rows, %d columns",
                     len(result), len(result.columns))
        return result

    # ──────────────────────────────────────────────
    # epaAC MAPPING (complex: 3 formats)
    # ──────────────────────────────────────────────

    def _detect_epac_format(self, df: pd.DataFrame) -> str:
        """Detect epaAC format: SAP_CODES, GERMAN_TEXT, or PIVOT."""
        cols = set(df.columns)
        # Pivot format: has SID and SID_value columns
        if "SID" in cols and "SID_value" in cols:
            return "PIVOT"
        # SAP codes: columns starting with EPA or E0_I_ / E2_I_
        sap_count = sum(1 for c in cols if c.startswith("EPA") or
                        re.match(r'E\d+_I_\d+', c) or c == "MANDT")
        if sap_count > 5:
            return "SAP_CODES"
        # German text
        if any(c in cols for c in ["AufnDat", "Körpergröße", "Koerpergroesse",
                                    "EinschIDFall", "BMI"]):
            return "GERMAN_TEXT"
        return "UNKNOWN"

    def _decode_sap_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert SAP EPA-format columns to IID format for target mapping.

        EPA0001 -> E0_I_001
        EPA0043 -> E0_I_043
        PATFAL -> case_id
        PATFOE -> patient_id
        PATADT -> admission_date

        Only renames pure numeric EPA columns (EPA0001), skips annotation
        columns like EPA0001AN, EPA0001TX, EPAOLDDAT, EPAST0BTS, etc.
        """
        rename_map = {}
        seen_targets = set()

        # Known SAP metadata columns
        sap_meta = {
            "PATFAL": "case_id",
            "PATFOE": "patient_id",
            "PATADT": "admission_date",
            "PATDOE": "discharge_date",
            "PATGEB": "date_of_birth",
        }

        for col in df.columns:
            if col in sap_meta:
                rename_map[col] = sap_meta[col]
                continue

            # Only pure numeric EPA columns: EPA0001 (not EPA0001AN, EPAST0BTS)
            m = re.match(r'^EPA(\d{4,})$', col)
            if m:
                num = m.group(1)
                iid = f"E0_I_{num[1:]}"
                # Avoid duplicate target names
                if iid not in seen_targets:
                    rename_map[col] = iid
                    seen_targets.add(iid)
                continue

        if rename_map:
            df = df.rename(columns=rename_map)
            logger.info("Converted %d SAP columns to IID/standard names", len(rename_map))

        # Drop duplicate columns (keep first)
        df = df.loc[:, ~df.columns.duplicated()]
        return df

    def _normalize_epac_german(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize German epaAC column names to internal standard."""
        rename_map = {}
        seen_targets = set()
        for col in df.columns:
            if col in EPAC_GERMAN_MAPPING:
                target = EPAC_GERMAN_MAPPING[col]
                if target not in seen_targets:
                    rename_map[col] = target
                    seen_targets.add(target)
        if rename_map:
            df = df.rename(columns=rename_map)
        # Drop duplicate columns (keep first)
        df = df.loc[:, ~df.columns.duplicated()]
        return df

    def _unpivot_epac(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert pivot-format epaAC (FallID, SID, SID_value) to wide format."""
        if "FallID" not in df.columns or "SID" not in df.columns:
            return df

        try:
            # Pivot: each SID becomes a column with SID_value as value
            pivoted = df.pivot_table(
                index="FallID",
                columns="SID",
                values="SID_value",
                aggfunc="first",
            ).reset_index()
            pivoted.columns.name = None

            # Merge back metadata columns (PID, Station, etc.)
            # Only add columns not already in pivoted
            meta_cols = [c for c in df.columns
                         if c not in ("SID", "SID_value", "FallID")]
            if meta_cols:
                meta = df[["FallID"] + meta_cols].drop_duplicates(
                    subset=["FallID"], keep="first"
                )
                for col in meta_cols:
                    if col not in pivoted.columns:
                        meta_map = dict(zip(meta["FallID"], meta[col]))
                        pivoted[col] = pivoted["FallID"].map(meta_map)

            # Rename SID columns to IID codes using decoder
            sid_map = self.sid_to_iid
            if sid_map:
                rename = {}
                for col in pivoted.columns:
                    if col in sid_map:
                        rename[col] = sid_map[col]
                if rename:
                    pivoted = pivoted.rename(columns=rename)
                    logger.info("Decoded %d SID columns to IID codes", len(rename))

            # Rename FallID to case_id, PID to patient_id
            pivoted = pivoted.rename(columns={
                "FallID": "case_id",
                "PID": "patient_id",
            })

            # Drop any duplicate columns
            pivoted = pivoted.loc[:, ~pivoted.columns.duplicated()]
            return pivoted
        except Exception as e:
            self.mapping_warnings.append(f"epaAC pivot failed: {e}")
            return df

    def _map_epac_to_target(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map epaAC DataFrame columns to tbImportAcData target columns."""
        # Deduplicate df columns first
        df = df.loc[:, ~df.columns.duplicated()]
        n = len(df)

        # Build column mapping dict first, then construct DataFrame at once
        col_map = {}

        # Extract case_id
        for col in ["case_id", "FallID", "PATFAL"]:
            if col in df.columns:
                col_map["coCaseId"] = df[col].apply(self._extract_case_id_numeric).values
                break

        # Map columns that match target schema pattern (E0_I_XXX -> coE0IXXX)
        for col in df.columns:
            m = re.match(r'^(E\d+)_I_(\d+)$', col)
            if m:
                target = f"co{m.group(1)}I{m.group(2)}"
                if target not in col_map:
                    col_map[target] = df[col].values
                continue
            if col.startswith("co") and col not in col_map:
                col_map[col] = df[col].values

        # Map known German columns to target
        german_to_target = {
            "height": "coE0I015",
            "weight": "coE0I014",
            "bmi": "coE0I005",
            "admission_date": "coE2I223",
            "discharge_date": "coE2I228",
            "age_years": "coE2I224",
            "ward": "coE2I230",
            "assessment_date": "coE2I225",
        }
        for src, tgt in german_to_target.items():
            if src in df.columns and tgt not in col_map:
                col_map[tgt] = df[src].values

        # Map patient_id
        for col in ["patient_id", "PID", "PATFOE"]:
            if col in df.columns and "coPatientId" not in col_map:
                col_map["coPatientId"] = df[col].values
                break

        # Add coCaseIdAlpha for string case_id
        for col in ["case_id", "FallID", "PATFAL"]:
            if col in df.columns:
                col_map["coCaseIdAlpha"] = df[col].apply(
                    lambda v: str(v).strip() if v is not None and not (
                        isinstance(v, float) and np.isnan(v)) else None
                ).values
                break

        if not col_map or "coCaseId" not in col_map:
            self.mapping_warnings.append("epaAC mapping produced no valid rows")
            return pd.DataFrame()

        # Filter out any arrays that don't match expected length
        valid_map = {}
        for k, v in col_map.items():
            if hasattr(v, '__len__') and len(v) == n:
                valid_map[k] = v
            elif not hasattr(v, '__len__'):
                valid_map[k] = v

        result = pd.DataFrame(valid_map, index=range(n))
        return result

    def map_epac(self, dfs: list[pd.DataFrame]) -> pd.DataFrame:
        """Map epaAC sources (all formats) to tbImportAcData."""
        if not dfs:
            return pd.DataFrame()

        all_mapped = []
        for df in dfs:
            df = df.copy().reset_index(drop=True)
            fmt = self._detect_epac_format(df)
            source = df.attrs.get("source_file", "unknown")
            logger.info("epaAC format for %s: %s", source, fmt)

            if fmt == "SAP_CODES":
                df = self._decode_sap_columns(df)
                mapped = self._map_epac_to_target(df)
            elif fmt == "GERMAN_TEXT":
                df = self._normalize_epac_german(df)
                mapped = self._map_epac_to_target(df)
            elif fmt == "PIVOT":
                df = self._unpivot_epac(df)
                mapped = self._map_epac_to_target(df)
            else:
                self.mapping_warnings.append(
                    f"Unknown epaAC format for {source}, attempting best-effort"
                )
                df = self._normalize_epac_german(df)
                mapped = self._map_epac_to_target(df)

            if not mapped.empty:
                all_mapped.append(mapped)

        if not all_mapped:
            return pd.DataFrame()

        result = pd.concat(all_mapped, ignore_index=True)
        # Convert to string for nvarchar columns
        result = self._to_string_columns(result, exclude={"coCaseId"})

        logger.info("Mapped tbImportAcData: %d rows, %d columns",
                     len(result), len(result.columns))
        return result

    # ──────────────────────────────────────────────
    # tbCaseData (assembled from multiple sources)
    # ──────────────────────────────────────────────

    def build_case_data(self, dataframes: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Build tbCaseData by assembling patient info from labs, icd10, epaAC."""
        cases: dict[str, dict] = {}

        by_type = self._group_by_type(dataframes)

        # Extract from labs
        for df in by_type.get("labs", []):
            self._extract_case_info_from_labs(df, cases)

        # Extract from icd10_ops
        for df in by_type.get("icd10_ops", []):
            self._extract_case_info_from_icd10(df, cases)

        # Extract from epaAC (all formats)
        for ftype in ["epaAC_german", "epaAC_sap", "epaAC_pivot"]:
            for df in by_type.get(ftype, []):
                self._extract_case_info_from_epac(df, cases)

        # Extract from device_motion, medication, nursing to avoid FK orphans
        for ftype in ["device_motion", "device_1hz", "medication", "nursing"]:
            for df in by_type.get(ftype, []):
                self._extract_case_info_minimal(df, cases)

        if not cases:
            self.mapping_warnings.append("No case data could be assembled")
            return pd.DataFrame()

        rows = []
        for case_id, info in cases.items():
            row = {"coCaseIdAlpha": case_id}
            numeric_id = self._extract_case_id_numeric(case_id)
            row["coId"] = numeric_id
            row["coE2I222"] = numeric_id  # Fall/Case ID
            row["coPatientId"] = info.get("patient_id")
            row["coGender"] = info.get("gender")
            row["coAgeYears"] = info.get("age_years")
            row["coIcd"] = info.get("primary_icd10_code")
            row["coE2I223"] = info.get("admission_date")
            row["coE2I228"] = info.get("discharge_date")
            row["coLastname"] = info.get("lastname")
            row["coFirstname"] = info.get("firstname")
            row["coDateOfBirth"] = info.get("date_of_birth")
            row["coTypeOfStay"] = info.get("type_of_stay")
            row["coDrgName"] = info.get("drg_name")
            row["coRecliningType"] = info.get("reclining_type")
            row["coState"] = info.get("state")
            rows.append(row)

        result = pd.DataFrame(rows)

        # Convert patient_id numeric part
        if "coPatientId" in result.columns:
            result["coPatientId"] = result["coPatientId"].apply(
                lambda v: self._extract_pid_numeric(v) if v is not None else None
            )

        # Convert age to int and clamp to valid range (0-120)
        if "coAgeYears" in result.columns:
            result["coAgeYears"] = pd.to_numeric(
                result["coAgeYears"], errors="coerce"
            )
            result["coAgeYears"] = result["coAgeYears"].clip(lower=0, upper=120)
            result["coAgeYears"] = result["coAgeYears"].astype("Int64")

        logger.info("Built tbCaseData: %d cases", len(result))
        return result

    def _extract_pid_numeric(self, val) -> Optional[int]:
        """Extract numeric part from patient_id (strip prefix)."""
        if val is None:
            return None
        s = str(val).strip()
        # Strip source prefix (LAB_, MOT_, etc.)
        s = re.sub(r'^(LAB|MOT|EPA|MED|NUR|ICD)_', '', s)
        # Strip PAT- prefix
        s = re.sub(r'^PAT-', '', s)
        m = re.search(r'(\d+)', s)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return None
        return None

    def _extract_case_info_from_labs(self, df: pd.DataFrame, cases: dict):
        """Extract case info from labs DataFrame."""
        for idx in df.index:
            case_id = self._get_val(df, idx, "case_id")
            if not case_id:
                continue
            if case_id not in cases:
                cases[case_id] = {}
            info = cases[case_id]
            self._set_if_missing(info, "patient_id", self._get_val(df, idx, "patient_id"))
            self._set_if_missing(info, "gender", self._get_val(df, idx, "sex"))
            self._set_if_missing(info, "age_years", self._get_val(df, idx, "age_years"))

    def _extract_case_info_from_icd10(self, df: pd.DataFrame, cases: dict):
        """Extract case info from icd10_ops DataFrame."""
        for idx in df.index:
            case_id = self._get_val(df, idx, "case_id")
            if not case_id:
                continue
            if case_id not in cases:
                cases[case_id] = {}
            info = cases[case_id]
            self._set_if_missing(info, "patient_id", self._get_val(df, idx, "patient_id"))
            self._set_if_missing(info, "primary_icd10_code", self._get_val(df, idx, "primary_icd10_code"))
            self._set_if_missing(info, "admission_date", self._get_val(df, idx, "admission_date"))
            self._set_if_missing(info, "discharge_date", self._get_val(df, idx, "discharge_date"))

    def _extract_case_info_minimal(self, df: pd.DataFrame, cases: dict):
        """Extract minimal case info (case_id, patient_id) from any source."""
        if "case_id" not in df.columns:
            return
        cols = ["case_id"]
        if "patient_id" in df.columns:
            cols.append("patient_id")
        # Deduplicate to avoid iterating 150k+ 1Hz rows
        dedup = df[cols].dropna(subset=["case_id"]).drop_duplicates(subset=["case_id"], keep="first")
        for _, row in dedup.iterrows():
            case_id = str(row["case_id"]).strip()
            if not case_id:
                continue
            if case_id not in cases:
                cases[case_id] = {}
            if "patient_id" in cols and not self._safe_isna(row.get("patient_id")):
                pid = str(row["patient_id"]).strip()
                if pid:
                    self._set_if_missing(cases[case_id], "patient_id", pid)

    def _extract_case_info_from_epac(self, df: pd.DataFrame, cases: dict):
        """Extract case info from epaAC DataFrame."""
        # Normalize German column names first
        df_norm = self._normalize_epac_german(df.copy())
        for idx in df_norm.index:
            case_id = self._get_val(df_norm, idx, "case_id")
            if not case_id:
                continue
            if case_id not in cases:
                cases[case_id] = {}
            info = cases[case_id]
            self._set_if_missing(info, "patient_id", self._get_val(df_norm, idx, "patient_id"))
            self._set_if_missing(info, "age_years", self._get_val(df_norm, idx, "age_years"))
            self._set_if_missing(info, "admission_date", self._get_val(df_norm, idx, "admission_date"))
            self._set_if_missing(info, "discharge_date", self._get_val(df_norm, idx, "discharge_date"))

    def _get_val(self, df: pd.DataFrame, idx, col: str) -> Optional[str]:
        """Get string value from DataFrame, return None if missing."""
        if col not in df.columns:
            return None
        val = df.at[idx, col]
        if self._safe_isna(val):
            return None
        s = str(val).strip()
        return s if s else None

    def _set_if_missing(self, d: dict, key: str, val):
        """Set dict key only if not already set and val is not None."""
        if val is not None and key not in d:
            d[key] = val

    # ──────────────────────────────────────────────
    # ORCHESTRATOR
    # ──────────────────────────────────────────────

    def _build_pid_to_caseid_lookup(self, dataframes: dict[str, pd.DataFrame]) -> dict:
        """Build patient_id -> case_id lookup from sources that have both.

        Stores both prefixed and raw (unprefixed) patient_ids so cross-source
        resolution works even when source prefixes differ (LAB_ vs MOT_).
        """
        lookup = {}
        for fname, df in dataframes.items():
            if "case_id" not in df.columns or "patient_id" not in df.columns:
                continue
            valid = df[["patient_id", "case_id"]].dropna()
            if valid.empty:
                continue
            dedup = valid.drop_duplicates(subset=["patient_id"], keep="first")
            for pid, cid in zip(dedup["patient_id"], dedup["case_id"]):
                pid_s = str(pid).strip()
                cid_s = str(cid).strip()
                if pid_s and cid_s:
                    if pid_s not in lookup:
                        lookup[pid_s] = cid_s
                    # Also store by raw (unprefixed) PID for cross-source matching
                    raw_pid = re.sub(r'^(LAB|MOT|EPA|MED|NUR|ICD)_', '', pid_s)
                    if raw_pid != pid_s and raw_pid not in lookup:
                        lookup[raw_pid] = cid_s
        return lookup

    def _resolve_case_ids(self, result: pd.DataFrame,
                          pid_lookup: dict) -> pd.DataFrame:
        """For rows with patient_id but no valid case_id, look up case_id."""
        if "coCaseId" not in result.columns or "coPatient_id" not in result.columns:
            return result
        if not pid_lookup:
            return result
        mask = result["coCaseId"].isna()
        if not mask.any():
            return result

        def _lookup_pid(pid):
            if self._safe_isna(pid):
                return None
            pid_s = str(pid)
            case_id = pid_lookup.get(pid_s)
            if case_id is None:
                raw_pid = re.sub(r'^(LAB|MOT|EPA|MED|NUR|ICD)_', '', pid_s)
                case_id = pid_lookup.get(raw_pid)
            return self._extract_case_id_numeric(case_id) if case_id else None

        resolved = result.loc[mask, "coPatient_id"].apply(_lookup_pid)
        result.loc[mask, "coCaseId"] = resolved
        return result

    def map_all(self, dataframes: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """
        Map all cleaned DataFrames to the 7 target SQL tables.
        Returns dict of {table_name: DataFrame}.
        """
        by_type = self._group_by_type(dataframes)
        self.mapping_warnings = []

        # Build patient_id -> case_id lookup for FK resolution
        self._pid_lookup = self._build_pid_to_caseid_lookup(dataframes)

        # 1. tbCaseData (assembled from multiple sources)
        self.mapped_tables["tbCaseData"] = self.build_case_data(dataframes)

        # 2. tbImportLabsData
        self.mapped_tables["tbImportLabsData"] = self.map_labs(
            by_type.get("labs", [])
        )

        # 3. tbImportIcd10Data
        self.mapped_tables["tbImportIcd10Data"] = self.map_icd10(
            by_type.get("icd10_ops", [])
        )

        # 4. tbImportAcData
        epac_dfs = (
            by_type.get("epaAC_german", []) +
            by_type.get("epaAC_sap", []) +
            by_type.get("epaAC_pivot", [])
        )
        self.mapped_tables["tbImportAcData"] = self.map_epac(epac_dfs)

        # 5. tbImportDeviceMotionData
        self.mapped_tables["tbImportDeviceMotionData"] = self.map_device_motion(
            by_type.get("device_motion", [])
        )

        # 6. tbImportDevice1HzMotionData
        self.mapped_tables["tbImportDevice1HzMotionData"] = self.map_device_1hz(
            by_type.get("device_1hz", [])
        )

        # 7. tbImportMedicationInpatientData
        self.mapped_tables["tbImportMedicationInpatientData"] = self.map_medication(
            by_type.get("medication", [])
        )

        # 8. tbImportNursingDailyReportsData
        self.mapped_tables["tbImportNursingDailyReportsData"] = self.map_nursing(
            by_type.get("nursing", [])
        )

        # Validate FK integrity: drop rows with coCaseId not in tbCaseData
        case_df = self.mapped_tables.get("tbCaseData")
        if case_df is not None and not case_df.empty and "coId" in case_df.columns:
            valid_case_ids = set(case_df["coId"].dropna().unique())
            fk_tables = [t for t in self.mapped_tables if t != "tbCaseData"]
            for table_name in fk_tables:
                df = self.mapped_tables[table_name]
                if df is not None and not df.empty and "coCaseId" in df.columns:
                    before = len(df)
                    orphan_mask = df["coCaseId"].notna() & ~df["coCaseId"].isin(valid_case_ids)
                    n_orphans = orphan_mask.sum()
                    if n_orphans > 0:
                        self.mapped_tables[table_name] = df[~orphan_mask].copy()
                        logger.warning(
                            "FK cleanup: dropped %d rows from %s with orphan coCaseId values",
                            n_orphans, table_name,
                        )

        # Summary
        for table_name, df in self.mapped_tables.items():
            if df is not None and not df.empty:
                logger.info("  %s: %d rows", table_name, len(df))
            else:
                logger.warning("  %s: EMPTY", table_name)

        if self.mapping_warnings:
            for w in self.mapping_warnings:
                logger.warning("Mapping warning: %s", w)

        return self.mapped_tables

    def get_mapping_summary(self) -> dict:
        """Return a summary of the mapping results."""
        summary = {}
        for table_name, df in self.mapped_tables.items():
            if df is not None and not df.empty:
                summary[table_name] = {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": list(df.columns),
                }
            else:
                summary[table_name] = {"rows": 0, "columns": 0, "column_names": []}
        return summary
