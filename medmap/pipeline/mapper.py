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

    def __init__(self, iid_sid_map: Optional[pd.DataFrame] = None):
        self.iid_sid_map = iid_sid_map
        self._sap_decoder: Optional[dict] = None
        self._sid_to_iid: Optional[dict] = None
        self.mapped_tables: dict[str, pd.DataFrame] = {}
        self.mapping_warnings: list[str] = []

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
        """Extract numeric part from case_id (e.g., 'CASE-0042' -> 42)."""
        if pd.isna(val) if isinstance(val, float) else val is None:
            return None
        s = str(val).strip()
        # Extract digits from CASE-XXXX format
        m = re.search(r'(\d+)', s)
        if m:
            try:
                return int(m.group(1))
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
        for col in df.columns:
            if col in exclude:
                continue
            df[col] = df[col].apply(
                lambda v: str(v) if v is not None and not (isinstance(v, float) and np.isnan(v)) else None
            )
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

        result = self._convert_case_id_column(result)
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

        result = self._convert_case_id_column(result)
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

        result = self._convert_case_id_column(result)
        result = self._to_string_columns(result, exclude={"coCaseId"})

        logger.info("Mapped tbImportMedicationInpatientData: %d rows, %d columns",
                     len(result), len(result.columns))
        return result

    def map_nursing(self, dfs: list[pd.DataFrame]) -> pd.DataFrame:
        """Map nursing sources to tbImportNursingDailyReportsData."""
        merged = self._merge_sources(dfs)
        if merged.empty:
            return pd.DataFrame()

        result = self._apply_column_mapping(
            merged, NURSING_MAPPING, "tbImportNursingDailyReportsData"
        )
        if result.empty:
            return result

        result = self._convert_case_id_column(result)

        # Truncate nursing notes to 256 chars (nvarchar(256) in schema)
        if "coNursing_note_free_text" in result.columns:
            result["coNursing_note_free_text"] = result["coNursing_note_free_text"].apply(
                lambda v: str(v)[:256] if v is not None and not (isinstance(v, float) and np.isnan(v)) else None
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
        """
        rename_map = {}
        # Known SAP metadata columns
        sap_meta = {
            "PATFAL": "case_id",
            "PATFOE": "patient_id",
            "PATADT": "admission_date",
            "PATDOE": "discharge_date",
            "PATGEB": "date_of_birth",
        }

        for col in df.columns:
            # Metadata columns
            if col in sap_meta:
                rename_map[col] = sap_meta[col]
                continue

            # EPA numeric columns: EPA0001 -> E0_I_001
            m = re.match(r'^EPA(\d{4,})$', col)
            if m:
                num = m.group(1)
                # First digit is always 0 (section E0), rest is item number
                iid = f"E0_I_{num[1:]}"
                rename_map[col] = iid
                continue

        if rename_map:
            df = df.rename(columns=rename_map)
            logger.info("Converted %d SAP columns to IID/standard names", len(rename_map))
        return df

    def _normalize_epac_german(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize German epaAC column names to internal standard."""
        rename_map = {}
        for col in df.columns:
            if col in EPAC_GERMAN_MAPPING:
                rename_map[col] = EPAC_GERMAN_MAPPING[col]
        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    def _unpivot_epac(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert pivot-format epaAC (FallID, SID, SID_value) to wide format."""
        if "FallID" not in df.columns or "SID" not in df.columns:
            return df

        # Collect extra columns to preserve (PID, Station, etc.)
        meta_cols = [c for c in df.columns
                     if c not in ("SID", "SID_value")]
        # Keep first occurrence of meta per FallID
        try:
            # Pivot: each SID becomes a column with SID_value as value
            pivoted = df.pivot_table(
                index="FallID",
                columns="SID",
                values="SID_value",
                aggfunc="first",
            ).reset_index()
            pivoted.columns.name = None

            # Merge back metadata columns
            if len(meta_cols) > 1:
                meta = df[meta_cols].drop_duplicates(subset=["FallID"], keep="first")
                pivoted = pivoted.merge(meta, on="FallID", how="left",
                                        suffixes=("", "_meta"))

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

            # Rename FallID to case_id
            pivoted = pivoted.rename(columns={"FallID": "case_id"})
            if "PID" in pivoted.columns:
                pivoted = pivoted.rename(columns={"PID": "patient_id"})

            return pivoted
        except Exception as e:
            self.mapping_warnings.append(f"epaAC pivot failed: {e}")
            return df

    def _map_epac_to_target(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map epaAC DataFrame columns to tbImportAcData target columns."""
        # Build column mapping dict first, then construct DataFrame at once
        col_map = {}

        # Extract case_id
        for col in ["case_id", "FallID", "PATFAL"]:
            if col in df.columns:
                col_map["coCaseId"] = df[col].apply(self._extract_case_id_numeric)
                break

        # Map columns that match target schema pattern (E0_I_XXX -> coE0IXXX)
        # SQL schema uses exact digit count from IID (no padding): E0_I_001 -> coE0I001
        for col in df.columns:
            m = re.match(r'^(E\d+)_I_(\d+)$', col)
            if m:
                target = f"co{m.group(1)}I{m.group(2)}"
                col_map[target] = df[col]
                continue
            if col.startswith("co"):
                col_map[col] = df[col]

        # Map known German columns to target
        german_to_target = {
            "height": "coE0I005",
            "weight": "coE0I004",
            "bmi": "coE0I005",
            "admission_date": "coE2I223",
            "discharge_date": "coE2I228",
            "age_years": "coE2I224",
            "ward": "coE2I230",
            "assessment_date": "coE2I225",
        }
        for src, tgt in german_to_target.items():
            if src in df.columns and tgt not in col_map:
                col_map[tgt] = df[src]

        # Add coCaseIdAlpha for string case_id
        for col in ["case_id", "FallID", "PATFAL"]:
            if col in df.columns:
                col_map["coCaseIdAlpha"] = df[col].apply(
                    lambda v: str(v).strip() if v is not None and not (
                        isinstance(v, float) and np.isnan(v)) else None
                )
                break

        if not col_map or "coCaseId" not in col_map:
            self.mapping_warnings.append("epaAC mapping produced no valid rows")
            return pd.DataFrame()

        result = pd.DataFrame(col_map)
        return result

    def map_epac(self, dfs: list[pd.DataFrame]) -> pd.DataFrame:
        """Map epaAC sources (all formats) to tbImportAcData."""
        if not dfs:
            return pd.DataFrame()

        all_mapped = []
        for df in dfs:
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

        if not cases:
            self.mapping_warnings.append("No case data could be assembled")
            return pd.DataFrame()

        rows = []
        for case_id, info in cases.items():
            row = {"coCaseIdAlpha": case_id}
            row["coId"] = self._extract_case_id_numeric(case_id)
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

        # Convert age to int
        if "coAgeYears" in result.columns:
            result["coAgeYears"] = pd.to_numeric(
                result["coAgeYears"], errors="coerce"
            ).astype("Int64")

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
        if pd.isna(val) if isinstance(val, float) else val is None:
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

    def map_all(self, dataframes: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """
        Map all cleaned DataFrames to the 7 target SQL tables.
        Returns dict of {table_name: DataFrame}.
        """
        by_type = self._group_by_type(dataframes)
        self.mapping_warnings = []

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
