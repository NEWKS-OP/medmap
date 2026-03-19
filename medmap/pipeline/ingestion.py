"""
Module 1: Data Ingestion
Reads CSV, XLSX, PDF files with auto-detection of delimiter and encoding.
Returns IngestionResult per file and stores DataFrames for pipeline use.
"""

import csv
import io
import logging
import os
import re
from typing import Optional

import chardet
import pandas as pd

from contracts import IngestionResult
from config.settings import (
    CHUNK_SIZE, FILE_SIZE_THRESHOLD_1HZ,
    DIRTY_DIR, CLEAN_DIR, SPLIT_DIR, IID_SID_ITEM_PATH,
)
from config.schema_mapping import (
    detect_file_type, infer_type_from_filename,
    DIRTY_LABS_RENAME, DIRTY_ICD10_RENAME, DIRTY_1HZ_RENAME,
    DIRTY_MEDICATION_RENAME, DIRTY_NURSING_RENAME,
    CLINIC2_LABS_RENAME, CLINIC2_DEVICE_RENAME, CLINIC2_1HZ_RENAME,
    CLINIC2_ICD10_RENAME, CLINIC2_MEDICATION_RENAME, CLINIC2_NURSING_RENAME,
    POSITIONAL_HEADERS, CLINIC3_LABS_HEADERS, CLINIC3_MEDICATION_HEADERS,
    CLINIC4_LABS_HEADERS, CLINIC4_ICD10_HEADERS,
    CLINIC4_MEDICATION_HEADERS, CLINIC4_DEVICE_HEADERS, CLINIC4_1HZ_HEADERS,
)

logger = logging.getLogger(__name__)


class DataIngester:
    """Ingests multi-format medical data files with auto-detection."""

    def __init__(self):
        self.dataframes = {}
        self.ingestion_results = {}
        self.iid_sid_map = None
        self._streaming_callback = None

    def set_streaming_callback(self, callback):
        """Set callback for 1Hz streaming progress updates."""
        self._streaming_callback = callback

    # ──────────────────────────────────────────────
    # ENCODING DETECTION
    # ──────────────────────────────────────────────

    def _detect_encoding(self, filepath):
        """Detect file encoding using chardet with fallback chain."""
        try:
            with open(filepath, "rb") as f:
                raw = f.read(min(100_000, os.path.getsize(filepath)))
            result = chardet.detect(raw)
            encoding = result.get("encoding", "utf-8")
            confidence = result.get("confidence", 0)
            if encoding and confidence > 0.5:
                return encoding
        except (OSError, IOError) as e:
            logger.debug("chardet detection failed for %s: %s", filepath, e)

        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                with open(filepath, "r", encoding=enc) as f:
                    f.read(5000)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue
        return "utf-8"

    # ──────────────────────────────────────────────
    # DELIMITER DETECTION
    # ──────────────────────────────────────────────

    def _detect_delimiter(self, filepath, encoding="utf-8"):
        """Detect CSV delimiter (comma vs semicolon) with Sniffer fallback."""
        try:
            with open(filepath, "r", encoding=encoding, errors="replace") as f:
                header = f.readline()

            semicolons = header.count(";")
            commas = header.count(",")

            if semicolons > commas and semicolons > 1:
                return ";"
            if commas > semicolons and commas > 1:
                return ","

            # Sniffer fallback
            with open(filepath, "r", encoding=encoding, errors="replace") as f:
                sample = f.read(8192)
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            return dialect.delimiter
        except Exception:
            return ","

    # ──────────────────────────────────────────────
    # DELIMITER MISMATCH DETECTION (epaAC-Data-3)
    # ──────────────────────────────────────────────

    def _check_delimiter_mismatch(self, filepath, encoding, delimiter):
        """Check if header and data use different delimiters."""
        try:
            with open(filepath, "r", encoding=encoding, errors="replace") as f:
                header_line = f.readline()
                data_line = f.readline()

            if not data_line.strip():
                return delimiter, False

            header_cols_semi = len(header_line.split(";"))
            header_cols_comma = len(header_line.split(","))
            data_cols_semi = len(data_line.split(";"))
            data_cols_comma = len(data_line.split(","))

            # Header uses semicolons but data uses commas
            if header_cols_semi > header_cols_comma and data_cols_comma > data_cols_semi:
                return ",", True
            # Header uses commas but data uses semicolons
            if header_cols_comma > header_cols_semi and data_cols_semi > data_cols_comma:
                return ";", True

            return delimiter, False
        except Exception:
            return delimiter, False

    # ──────────────────────────────────────────────
    # CSV LOADING
    # ──────────────────────────────────────────────

    def _load_csv(self, filepath, encoding=None, delimiter=None):
        """Load a CSV file with auto-detected encoding and delimiter."""
        warnings = []

        if encoding is None:
            encoding = self._detect_encoding(filepath)
        if delimiter is None:
            delimiter = self._detect_delimiter(filepath, encoding)

        # Check for delimiter mismatch
        actual_delim, had_mismatch = self._check_delimiter_mismatch(
            filepath, encoding, delimiter
        )
        if had_mismatch:
            warnings.append(
                f"Delimiter mismatch detected: header={delimiter}, "
                f"data={actual_delim}. Reading with fix."
            )
            # Read header with original delimiter, data with actual
            df = self._load_csv_with_mismatch_fix(
                filepath, encoding, delimiter, actual_delim
            )
            return df, encoding, delimiter, warnings

        try:
            df = pd.read_csv(
                filepath,
                encoding=encoding,
                sep=delimiter,
                on_bad_lines="skip",
                low_memory=False,
            )
        except Exception as e:
            warnings.append(f"Error reading with {encoding}/{delimiter}: {e}")
            # Try alternative encoding
            for alt_enc in ["utf-8", "latin-1", "cp1252"]:
                if alt_enc == encoding:
                    continue
                try:
                    df = pd.read_csv(
                        filepath,
                        encoding=alt_enc,
                        sep=delimiter,
                        on_bad_lines="skip",
                        low_memory=False,
                    )
                    encoding = alt_enc
                    warnings.append(f"Fallback to encoding: {alt_enc}")
                    break
                except Exception:
                    continue
            else:
                raise

        return df, encoding, delimiter, warnings

    def _load_csv_with_mismatch_fix(self, filepath, encoding,
                                     header_delim, data_delim):
        """Handle files where header and data use different delimiters."""
        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            header_line = f.readline().strip()
            data_lines = f.readlines()

        headers = [h.strip().strip('"') for h in header_line.split(header_delim)]

        rows = []
        for line in data_lines:
            line = line.strip()
            if not line:
                continue
            values = line.split(data_delim)
            # Pad or truncate to match header length
            if len(values) < len(headers):
                values.extend([""] * (len(headers) - len(values)))
            elif len(values) > len(headers):
                values = values[:len(headers)]
            rows.append(values)

        return pd.DataFrame(rows, columns=headers)

    # ──────────────────────────────────────────────
    # XLSX LOADING
    # ──────────────────────────────────────────────

    def _load_xlsx(self, filepath):
        """Load an Excel file. Handles CSV-in-XLSX (single column with delimited data)."""
        warnings = []
        try:
            df = pd.read_excel(filepath, engine="openpyxl")
        except Exception as e:
            warnings.append(f"Error reading XLSX: {e}")
            raise

        # Check for CSV-in-XLSX: first column name contains many commas/semicolons
        first_col = str(df.columns[0])
        sep = None
        if first_col.count(";") > 2:
            sep = ";"
        elif first_col.count(",") > 2:
            sep = ","

        if sep:
            warnings.append(
                "XLSX contains CSV data — re-parsing with csv.reader"
            )
            # Reconstruct full CSV text: join all columns back per row
            lines = [first_col]
            for _, row in df.iterrows():
                parts = [str(v) if pd.notna(v) else "" for v in row]
                # Join all cell values with the separator
                line = sep.join(parts)
                lines.append(line)

            csv_text = "\n".join(lines)
            df = pd.read_csv(
                io.StringIO(csv_text),
                sep=sep,
                on_bad_lines="skip",
            )

        return df, "xlsx", "N/A", warnings

    # ──────────────────────────────────────────────
    # PDF LOADING (pdfplumber)
    # ──────────────────────────────────────────────

    def _load_pdf(self, filepath):
        """Load a PDF file using pdfplumber (for nursing notes)."""
        import pdfplumber

        warnings = []
        rows = []

        try:
            with pdfplumber.open(filepath) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            if not table:
                                continue
                            # First table on first page: use row 0 as header
                            if page_num == 0 and not rows:
                                header = [
                                    str(c).strip() if c else f"col_{i}"
                                    for i, c in enumerate(table[0])
                                ]
                                for row in table[1:]:
                                    if row:
                                        rows.append(dict(zip(header, row)))
                            else:
                                for row in table:
                                    if row and header:
                                        padded = row + [""] * (
                                            len(header) - len(row)
                                        )
                                        rows.append(
                                            dict(zip(header, padded[:len(header)]))
                                        )
                    else:
                        text = page.extract_text()
                        if text:
                            rows.append({
                                "raw_text": text,
                                "source_page": page_num + 1,
                            })
                            warnings.append(
                                f"Page {page_num+1}: no table found, "
                                "extracted as raw text"
                            )
        except Exception as e:
            warnings.append(f"Error reading PDF: {e}")
            raise

        if not rows:
            warnings.append("PDF contained no extractable data")
            return pd.DataFrame(), "pdf", "N/A", warnings

        df = pd.DataFrame(rows)

        # If raw text format (nursing notes), parse structured fields
        if "raw_text" in df.columns:
            df = self._parse_nursing_pdf_text(df)
            warnings.append("Parsed structured nursing fields from raw text")

        return df, "pdf", "N/A", warnings

    def _parse_nursing_pdf_text(self, df):
        """Parse structured nursing note fields from raw PDF text."""
        records = []
        for _, row in df.iterrows():
            text = str(row.get("raw_text", ""))
            record = {}

            # Extract Date
            m = re.search(r"Date:\s*(\S+)", text)
            record["report_date"] = m.group(1) if m else None

            # Extract Shift
            m = re.search(r"Shift:\s*(.+?)(?:\n|$)", text)
            record["shift"] = m.group(1).strip() if m else None

            # Extract Patient ID
            m = re.search(r"Patient ID:\s*(\S+)", text)
            record["patient_id"] = m.group(1) if m else None

            # Extract Case ID
            m = re.search(r"Case ID:\s*(\S+)", text)
            record["case_id"] = m.group(1) if m else None

            # Extract Ward
            m = re.search(r"Ward:\s*(.+?)(?:\n|$)", text)
            record["ward"] = m.group(1).strip() if m else None

            # Extract the nursing note (everything after "Report")
            m = re.search(r"Report\n(.+)", text, re.DOTALL)
            record["nursing_note_free_text"] = (
                m.group(1).strip().replace("\n", " ") if m else text
            )

            records.append(record)

        return pd.DataFrame(records)

    # ──────────────────────────────────────────────
    # epaAC TWO-LINE HEADER HANDLING
    # ──────────────────────────────────────────────

    def _handle_epac_two_line_header(self, filepath, encoding, delimiter):
        """Handle epaAC files that have German names on line 1 and SAP codes on line 2."""
        warnings = []
        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            line1 = f.readline().strip()
            line2 = f.readline().strip()

        headers1 = [h.strip() for h in line1.split(delimiter)]
        headers2 = [h.strip() for h in line2.split(delimiter)]

        # Check if line 2 looks like SAP codes (E0_I_*, E2_I_*, etc.)
        sap_pattern_count = sum(
            1 for h in headers2
            if h.startswith("E") and "_I_" in h
        )

        if sap_pattern_count > len(headers2) * 0.3:
            # Line 2 is SAP codes — use line 1 as readable headers, skip line 2
            warnings.append(
                "Two-line header detected: German names + SAP codes. "
                "Using German names as column headers."
            )
            # Skip line 2 (SAP codes row), keep line 1 as header
            df = pd.read_csv(
                filepath,
                encoding=encoding,
                sep=delimiter,
                header=0,
                skiprows=[1],
                on_bad_lines="skip",
                low_memory=False,
            )
            return df, warnings

        return None, warnings

    # ──────────────────────────────────────────────
    # IID-SID-ITEM.csv LOADING
    # ──────────────────────────────────────────────

    def load_iid_sid_item(self, filepath=None):
        """Load the SAP code decoder table."""
        if filepath is None:
            filepath = IID_SID_ITEM_PATH

        if not os.path.exists(filepath):
            logger.warning("IID-SID-ITEM.csv not found at %s", filepath)
            return None

        try:
            df = pd.read_csv(
                filepath,
                sep=";",
                encoding="utf-8-sig",
                on_bad_lines="skip",
            )
            self.iid_sid_map = df
            logger.info(
                "Loaded IID-SID-ITEM.csv: %d rows, columns: %s",
                len(df), list(df.columns),
            )
            return df
        except Exception:
            try:
                df = pd.read_csv(
                    filepath,
                    sep=";",
                    encoding="latin-1",
                    on_bad_lines="skip",
                )
                self.iid_sid_map = df
                return df
            except Exception as e:
                logger.error("Failed to load IID-SID-ITEM.csv: %s", e)
                return None

    def get_sap_decoder(self):
        """Return a dict mapping SAP IID codes to English names."""
        if self.iid_sid_map is None:
            self.load_iid_sid_item()
        if self.iid_sid_map is None:
            return {}
        try:
            return dict(zip(
                self.iid_sid_map["ItmIID"],
                self.iid_sid_map["ItmName255_EN"],
            ))
        except KeyError:
            return {}

    # ──────────────────────────────────────────────
    # 1Hz CHUNKED LOADING
    # ──────────────────────────────────────────────

    def _load_1hz_chunked(self, filepath, encoding=None, delimiter=None):
        """Load the large 1Hz motion file in chunks."""
        warnings = []

        if encoding is None:
            encoding = self._detect_encoding(filepath)
        if delimiter is None:
            delimiter = self._detect_delimiter(filepath, encoding)

        chunks = []
        total_rows = 0
        chunk_num = 0

        try:
            reader = pd.read_csv(
                filepath,
                encoding=encoding,
                sep=delimiter,
                chunksize=CHUNK_SIZE,
                on_bad_lines="skip",
                low_memory=False,
            )
            for chunk in reader:
                chunks.append(chunk)
                chunk_num += 1
                total_rows += len(chunk)

                if self._streaming_callback:
                    falls = 0
                    patients = 0
                    if "fall_event_0_1" in chunk.columns:
                        falls = int(chunk["fall_event_0_1"].sum())
                    elif "FallEvent" in chunk.columns:
                        try:
                            falls = int(
                                pd.to_numeric(
                                    chunk["FallEvent"], errors="coerce"
                                ).sum()
                            )
                        except (ValueError, TypeError) as e:
                            logger.debug("FallEvent sum failed in chunk %d: %s", chunk_num, e)
                    pid_col = None
                    for c in ["patient_id", "PatientID"]:
                        if c in chunk.columns:
                            pid_col = c
                            break
                    if pid_col:
                        patients = chunk[pid_col].nunique()

                    self._streaming_callback({
                        "processed": total_rows,
                        "chunk": chunk_num,
                        "falls": falls,
                        "patients": patients,
                    })

                if chunk_num % 10 == 0:
                    logger.info(
                        "1Hz loading: chunk %d, %d rows so far",
                        chunk_num, total_rows,
                    )

        except Exception as e:
            warnings.append(f"Error during chunked reading: {e}")
            if not chunks:
                raise

        df = pd.concat(chunks, ignore_index=True)
        warnings.append(
            f"Loaded in {chunk_num} chunks of {CHUNK_SIZE} rows each"
        )
        return df, encoding, delimiter, warnings

    # ──────────────────────────────────────────────
    # COLUMN NORMALIZATION
    # ──────────────────────────────────────────────

    def _detect_clinic(self, filename):
        """Detect which clinic a split file belongs to."""
        m = re.match(r"clinic_(\d+)_", filename.lower())
        return int(m.group(1)) if m else None

    def _is_headerless(self, df):
        """Check if a DataFrame has no real headers (data in first row)."""
        # If first column name looks like a date or patient ID, it's headerless
        first_col = str(df.columns[0])
        if re.match(r"\d{4}-\d{2}-\d{2}", first_col):
            return True
        if re.match(r"PAT-\d+", first_col):
            return True
        if re.match(r"CASE-\d+", first_col):
            return True
        if re.match(r"ORD-", first_col):
            return True
        return False

    def _is_generic_headers(self, df):
        """Check if a DataFrame has generic col1, col2... headers."""
        return all(
            str(c).startswith("col") and str(c)[3:].isdigit()
            for c in df.columns
        )

    def _apply_positional_headers(self, df, file_type, clinic_num, filename):
        """Apply positional headers to headerless or generic-header DataFrames."""
        warnings = []
        headers = None

        if clinic_num == 3:
            if file_type == "labs":
                headers = CLINIC3_LABS_HEADERS
            elif file_type == "medication":
                headers = CLINIC3_MEDICATION_HEADERS
            elif file_type in POSITIONAL_HEADERS:
                headers = POSITIONAL_HEADERS[file_type]
        elif clinic_num == 4:
            if file_type == "labs":
                headers = CLINIC4_LABS_HEADERS
            elif file_type == "icd10_ops":
                headers = CLINIC4_ICD10_HEADERS
            elif file_type == "medication":
                headers = CLINIC4_MEDICATION_HEADERS
            elif file_type == "device_motion":
                headers = CLINIC4_DEVICE_HEADERS
            elif file_type == "device_1hz":
                headers = CLINIC4_1HZ_HEADERS
            elif file_type in POSITIONAL_HEADERS:
                headers = POSITIONAL_HEADERS[file_type]

        if headers:
            ncols = len(df.columns)
            nheaders = len(headers)
            if ncols == nheaders:
                df.columns = headers
                warnings.append(
                    f"Applied {nheaders} positional headers for "
                    f"clinic_{clinic_num} {file_type}"
                )
            elif ncols < nheaders:
                df.columns = headers[:ncols]
                warnings.append(
                    f"Applied {ncols}/{nheaders} positional headers "
                    f"(file has fewer columns)"
                )
            else:
                df.columns = list(headers) + [
                    f"extra_{i}" for i in range(ncols - nheaders)
                ]
                warnings.append(
                    f"Applied {nheaders} positional headers + "
                    f"{ncols - nheaders} extra columns"
                )

        return df, warnings

    def _normalize_columns(self, df, file_type, source_file):
        """Rename dirty column names to standard clean names."""
        warnings = []
        clinic_num = self._detect_clinic(source_file)
        is_headerless = self._is_headerless(df)
        is_generic = self._is_generic_headers(df)

        # For headerless files (clinic_3), re-read with header=None
        # and prepend the data that was read as header
        if is_headerless and clinic_num:
            # The first row of data was used as column names
            # Reconstruct it as data
            first_row = pd.DataFrame([df.columns.tolist()], columns=range(len(df.columns)))
            df.columns = range(len(df.columns))
            df = pd.concat([first_row, df], ignore_index=True)
            warnings.append("Headerless file detected — re-added first row as data")

        # Apply positional headers for headerless/generic
        if (is_headerless or is_generic) and clinic_num:
            df, pos_warns = self._apply_positional_headers(
                df, file_type, clinic_num, source_file
            )
            warnings.extend(pos_warns)
            return df, warnings

        # Clinic 2 abbreviated names
        if clinic_num == 2:
            rename_map = {
                "labs": CLINIC2_LABS_RENAME,
                "device_motion": CLINIC2_DEVICE_RENAME,
                "device_1hz": CLINIC2_1HZ_RENAME,
                "icd10_ops": CLINIC2_ICD10_RENAME,
                "medication": CLINIC2_MEDICATION_RENAME,
                "nursing": CLINIC2_NURSING_RENAME,
            }.get(file_type)

            if rename_map:
                actual = {k: v for k, v in rename_map.items() if k in df.columns}
                if actual:
                    df = df.rename(columns=actual)
                    warnings.append(
                        f"Renamed {len(actual)} clinic_2 abbreviated "
                        "columns to standard names"
                    )
                    return df, warnings

        # Standard dirty renames
        rename_map = None
        if file_type == "labs":
            if "CaseID" in df.columns or "PID" in df.columns:
                rename_map = DIRTY_LABS_RENAME
        elif file_type == "icd10_ops":
            if "CaseID" in df.columns and "ICD10_Haupt" in df.columns:
                rename_map = DIRTY_ICD10_RENAME
        elif file_type == "device_1hz":
            if "PatientID" in df.columns and "AccelX" in df.columns:
                rename_map = DIRTY_1HZ_RENAME
        elif file_type == "medication":
            if "rec_type" in df.columns or "medikament" in df.columns:
                rename_map = DIRTY_MEDICATION_RENAME
        elif file_type == "nursing":
            if "NursingNote" in df.columns:
                rename_map = DIRTY_NURSING_RENAME

        if rename_map:
            actual_renames = {
                k: v for k, v in rename_map.items() if k in df.columns
            }
            if actual_renames:
                df = df.rename(columns=actual_renames)
                warnings.append(
                    f"Renamed {len(actual_renames)} dirty columns to "
                    "standard names"
                )

        return df, warnings

    # ──────────────────────────────────────────────
    # MAIN LOAD METHOD
    # ──────────────────────────────────────────────

    def load(self, filepath, force_type=None):
        """
        Load a single file and return (DataFrame, IngestionResult).
        Auto-detects format, encoding, delimiter, and file type.
        """
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filepath)[1].lower()
        warnings = []
        encoding_detected = "unknown"
        delimiter_detected = "N/A"
        df = None

        try:
            # Route by file extension
            if ext == ".pdf":
                df, encoding_detected, delimiter_detected, w = (
                    self._load_pdf(filepath)
                )
                warnings.extend(w)

            elif ext in (".xlsx", ".xls"):
                df, encoding_detected, delimiter_detected, w = (
                    self._load_xlsx(filepath)
                )
                warnings.extend(w)

            elif ext == ".csv":
                encoding_detected = self._detect_encoding(filepath)
                delimiter_detected = self._detect_delimiter(
                    filepath, encoding_detected
                )

                # Check for 1Hz file (large, needs chunked reading)
                file_size = os.path.getsize(filepath)
                is_1hz = file_size > FILE_SIZE_THRESHOLD_1HZ  # > 5MB likely 1Hz

                if is_1hz:
                    # Quick column check
                    peek = pd.read_csv(
                        filepath,
                        encoding=encoding_detected,
                        sep=delimiter_detected,
                        nrows=1,
                        on_bad_lines="skip",
                    )
                    peek_type = detect_file_type(list(peek.columns))
                    if peek_type == "device_1hz":
                        df, encoding_detected, delimiter_detected, w = (
                            self._load_1hz_chunked(
                                filepath, encoding_detected,
                                delimiter_detected,
                            )
                        )
                        warnings.extend(w)
                    else:
                        # Large file but not 1Hz — load normally
                        df, encoding_detected, delimiter_detected, w = (
                            self._load_csv(
                                filepath, encoding_detected,
                                delimiter_detected,
                            )
                        )
                        warnings.extend(w)
                else:
                    # Check for epaAC two-line header
                    result, w = self._handle_epac_two_line_header(
                        filepath, encoding_detected, delimiter_detected
                    )
                    warnings.extend(w)
                    if result is not None:
                        df = result
                    else:
                        df, encoding_detected, delimiter_detected, w = (
                            self._load_csv(
                                filepath, encoding_detected,
                                delimiter_detected,
                            )
                        )
                        warnings.extend(w)
            else:
                warnings.append(f"Unknown file extension: {ext}")
                return None, IngestionResult(
                    source_file=filename,
                    rows_total=0,
                    rows_loaded=0,
                    encoding_detected=encoding_detected,
                    delimiter_detected=delimiter_detected,
                    warnings=warnings,
                )

            if df is None:
                warnings.append("File loaded but DataFrame is None")
                return df, IngestionResult(
                    source_file=filename,
                    rows_total=0,
                    rows_loaded=0,
                    encoding_detected=encoding_detected,
                    delimiter_detected=delimiter_detected,
                    warnings=warnings,
                )

            # Strip whitespace from column names
            df.columns = [str(c).strip() for c in df.columns]

            # Detect file type by columns, with filename fallback
            file_type = force_type or detect_file_type(list(df.columns))
            if file_type == "unknown":
                file_type = infer_type_from_filename(filename)
                if file_type != "unknown":
                    warnings.append(
                        f"Type inferred from filename: {file_type}"
                    )

            # Normalize dirty column names to standard
            df, norm_warnings = self._normalize_columns(
                df, file_type, filename
            )
            warnings.extend(norm_warnings)

            rows_total = len(df)
            rows_loaded = len(df)

            # Store metadata
            df.attrs["source_file"] = filename
            df.attrs["file_type"] = file_type
            df.attrs["encoding"] = encoding_detected
            df.attrs["delimiter"] = delimiter_detected

            result = IngestionResult(
                source_file=filename,
                rows_total=rows_total,
                rows_loaded=rows_loaded,
                encoding_detected=encoding_detected,
                delimiter_detected=delimiter_detected,
                warnings=warnings,
            )

            self.dataframes[filename] = df
            self.ingestion_results[filename] = result

            logger.info(
                "Loaded %s: %d rows, type=%s, enc=%s, delim=%s",
                filename, rows_loaded, file_type,
                encoding_detected, delimiter_detected,
            )

            return df, result

        except Exception as e:
            logger.error("Failed to load %s: %s", filepath, e)
            warnings.append(f"FATAL: {e}")
            result = IngestionResult(
                source_file=filename,
                rows_total=0,
                rows_loaded=0,
                encoding_detected=encoding_detected,
                delimiter_detected=delimiter_detected,
                warnings=warnings,
            )
            self.ingestion_results[filename] = result
            return None, result

    # ──────────────────────────────────────────────
    # DIRECTORY INGESTION
    # ──────────────────────────────────────────────

    def ingest_directory(self, directory, skip_1hz=False):
        """
        Ingest all supported files from a directory.
        Returns dict of {filename: (DataFrame, IngestionResult)}.
        """
        results = {}
        supported_extensions = {".csv", ".xlsx", ".xls", ".pdf"}

        if not os.path.isdir(directory):
            logger.error("Directory not found: %s", directory)
            return results

        files = sorted(os.listdir(directory))
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in supported_extensions:
                continue

            filepath = os.path.join(directory, fname)

            # Optionally skip 1Hz files
            if skip_1hz and os.path.getsize(filepath) > FILE_SIZE_THRESHOLD_1HZ:
                logger.info("Skipping large file (1Hz): %s", fname)
                continue

            try:
                df, result = self.load(filepath)
                results[fname] = (df, result)
            except Exception as e:
                logger.error("Failed to ingest %s: %s", fname, e)
                results[fname] = (None, IngestionResult(
                    source_file=fname,
                    rows_total=0,
                    rows_loaded=0,
                    encoding_detected="unknown",
                    delimiter_detected="unknown",
                    warnings=[f"FATAL: {e}"],
                ))

        return results

    def ingest_all(self, data_folder="dirty", include_split=True,
                   include_iid=True):
        """
        Ingest all data: base files + split + IID-SID-ITEM.
        data_folder: 'dirty' or 'clean'
        """
        results = {}

        # Load IID-SID-ITEM first
        if include_iid:
            self.load_iid_sid_item()

        # Load base directory
        base_dir = DIRTY_DIR if data_folder == "dirty" else CLEAN_DIR
        logger.info("Ingesting base directory: %s", base_dir)
        base_results = self.ingest_directory(base_dir)
        results.update(base_results)

        # Load split directory
        if include_split and os.path.isdir(SPLIT_DIR):
            logger.info("Ingesting split directory: %s", SPLIT_DIR)
            split_results = self.ingest_directory(SPLIT_DIR)
            results.update(split_results)

        # Summary
        total_files = len(results)
        total_rows = sum(
            r.rows_loaded for _, r in results.values() if r is not None
        )
        failed = sum(
            1 for df, _ in results.values() if df is None
        )

        logger.info(
            "Ingestion complete: %d files, %d total rows, %d failures",
            total_files, total_rows, failed,
        )

        return results

    def get_dataframes_by_type(self):
        """Group loaded DataFrames by detected file type."""
        by_type = {}
        for fname, df in self.dataframes.items():
            file_type = df.attrs.get("file_type", "unknown")
            if file_type not in by_type:
                by_type[file_type] = []
            by_type[file_type].append((fname, df))
        return by_type
