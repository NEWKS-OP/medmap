"""
Module 6: SQL Export
Creates SQLite database from schema, inserts mapped data respecting FK order.
Also creates tbAuditLog and tbDataPassport tables.
"""

import logging
import os
import re
import sqlite3
from typing import Optional

import numpy as np
import pandas as pd

from config.settings import DB_PATH, DB_DIR, SQL_SCHEMA_PATH, DB_TYPE, MSSQL_CONNECTION_STRING
from contracts import AuditLogEntry, Severity, ActionTaken

logger = logging.getLogger(__name__)

# Insertion order respecting FK constraints
TABLE_INSERT_ORDER = [
    "tbCaseData",
    "tbImportLabsData",
    "tbImportIcd10Data",
    "tbImportAcData",
    "tbImportDeviceMotionData",
    "tbImportDevice1HzMotionData",
    "tbImportMedicationInpatientData",
    "tbImportNursingDailyReportsData",
]

# T-SQL -> SQLite type conversion
TSQL_TO_SQLITE = {
    "bigint": "INTEGER",
    "int": "INTEGER",
    "smallint": "INTEGER",
    "tinyint": "INTEGER",
    "bit": "INTEGER",
    "numeric": "REAL",
    "decimal": "REAL",
    "float": "REAL",
    "real": "REAL",
    "nvarchar": "TEXT",
    "varchar": "TEXT",
    "nchar": "TEXT",
    "char": "TEXT",
    "text": "TEXT",
    "ntext": "TEXT",
    "datetime": "TEXT",
    "datetime2": "TEXT",
    "date": "TEXT",
    "time": "TEXT",
}


class SQLExporter:
    """Exports mapped DataFrames to SQLite database."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Create or connect to SQLite database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        logger.info("Connected to SQLite: %s", self.db_path)
        return self.conn

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    # ──────────────────────────────────────────────
    # SCHEMA CREATION
    # ──────────────────────────────────────────────

    def _convert_tsql_to_sqlite(self, sql: str) -> list[str]:
        """Convert T-SQL CREATE TABLE statements to SQLite-compatible SQL."""
        statements = []

        # Remove BOM
        sql = sql.lstrip("\ufeff")

        # Split by 'create table' (case-insensitive)
        parts = re.split(r'(?i)\bcreate\s+table\b', sql)

        for part in parts[1:]:  # Skip text before first CREATE TABLE
            # Extract table name and body
            m = re.match(r'\s+(\w+)\s*\((.*)\)', part, re.DOTALL)
            if not m:
                continue

            table_name = m.group(1)
            body = m.group(2)

            # Process each column/constraint line
            columns = []
            for line in body.split(","):
                line = line.strip()
                if not line:
                    continue

                # Skip constraint lines
                if re.match(r'(?i)\s*constraint\s+', line):
                    continue

                # Parse column definition
                col_match = re.match(
                    r'(\w+)\s+(\w+)(?:\(([^)]+)\))?\s*(.*)',
                    line, re.IGNORECASE
                )
                if not col_match:
                    continue

                col_name = col_match.group(1)
                col_type = col_match.group(2).lower()
                modifiers = col_match.group(4).strip().lower() if col_match.group(4) else ""

                # Convert type
                sqlite_type = TSQL_TO_SQLITE.get(col_type, "TEXT")

                # Handle identity -> autoincrement for primary key
                if "identity" in modifiers:
                    columns.append(
                        f"    {col_name} INTEGER PRIMARY KEY AUTOINCREMENT"
                    )
                    continue

                # Drop NOT NULL constraints to allow partial data inserts
                columns.append(f"    {col_name} {sqlite_type}")

            if columns:
                create_sql = (
                    f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
                    + ",\n".join(columns)
                    + "\n)"
                )
                statements.append(create_sql)

        return statements

    def create_schema(self):
        """Create all tables from the SQL schema file."""
        if not self.conn:
            self.connect()

        if os.path.exists(SQL_SCHEMA_PATH):
            with open(SQL_SCHEMA_PATH, "r", encoding="utf-8-sig") as f:
                tsql = f.read()
            statements = self._convert_tsql_to_sqlite(tsql)
            for stmt in statements:
                try:
                    self.conn.execute(stmt)
                except sqlite3.Error as e:
                    logger.error("Schema creation error: %s\nSQL: %s", e, stmt[:200])
            logger.info("Created %d tables from schema", len(statements))
        else:
            logger.warning("Schema file not found: %s", SQL_SCHEMA_PATH)
            self._create_tables_from_mapped()

        # Add missing columns that the mapper produces but aren't in the schema
        self._add_column_if_missing("tbCaseData", "coCaseIdAlpha", "TEXT")

        # Always create extra tables
        self._create_audit_log_table()
        self._create_data_passport_table()
        self.conn.commit()

    def _add_column_if_missing(self, table_name: str, col_name: str,
                                col_type: str = "TEXT"):
        """Add a column to a table if it doesn't already exist."""
        try:
            existing = self._get_table_columns(table_name)
            if col_name not in existing:
                self.conn.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                )
                logger.info("Added column %s to %s", col_name, table_name)
        except sqlite3.Error as e:
            logger.warning("Could not add column %s to %s: %s",
                           col_name, table_name, e)

    def _create_tables_from_mapped(self):
        """Fallback: create tables dynamically from mapped DataFrames."""
        logger.warning("No schema file found — tables must be created manually")

    def _create_audit_log_table(self):
        """Create the tbAuditLog table."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tbAuditLog (
                coId INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT,
                case_id TEXT,
                table_name TEXT,
                column_name TEXT,
                original_value TEXT,
                cleaned_value TEXT,
                error_type TEXT,
                severity TEXT,
                action_taken TEXT,
                corrected_by TEXT,
                correction_timestamp TEXT,
                row_number INTEGER
            )
        """)

    def _create_data_passport_table(self):
        """Create the tbDataPassport table."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tbDataPassport (
                passport_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                table_name TEXT,
                field_name TEXT,
                raw_value TEXT,
                cleaned_value TEXT,
                detected_by TEXT,
                problem_type TEXT,
                problem_detail TEXT,
                action_taken TEXT,
                confidence REAL,
                validated_by TEXT,
                fhir_alignment TEXT,
                status TEXT,
                source_file TEXT,
                row_number INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        """)

    def _create_indexes(self):
        """Create indexes on frequently queried columns for API performance."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_audit_source ON tbAuditLog(source_file)",
            "CREATE INDEX IF NOT EXISTS idx_audit_case ON tbAuditLog(case_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_severity ON tbAuditLog(severity)",
            "CREATE INDEX IF NOT EXISTS idx_audit_action ON tbAuditLog(action_taken)",
            "CREATE INDEX IF NOT EXISTS idx_passport_case ON tbDataPassport(case_id)",
            "CREATE INDEX IF NOT EXISTS idx_passport_status ON tbDataPassport(status)",
            "CREATE INDEX IF NOT EXISTS idx_labs_case ON tbImportLabsData(coCaseId)",
            "CREATE INDEX IF NOT EXISTS idx_icd_case ON tbImportIcd10Data(coCaseId)",
            "CREATE INDEX IF NOT EXISTS idx_icd_ward ON tbImportIcd10Data(coWard)",
            "CREATE INDEX IF NOT EXISTS idx_motion_case ON tbImportDeviceMotionData(coCaseId)",
            "CREATE INDEX IF NOT EXISTS idx_med_case ON tbImportMedicationInpatientData(coCaseId)",
            "CREATE INDEX IF NOT EXISTS idx_nursing_case ON tbImportNursingDailyReportsData(coCaseId)",
            "CREATE INDEX IF NOT EXISTS idx_ac_case ON tbImportAcData(coCaseId)",
            "CREATE INDEX IF NOT EXISTS idx_case_alpha ON tbCaseData(coCaseIdAlpha)",
        ]
        for idx_sql in indexes:
            try:
                self.conn.execute(idx_sql)
            except sqlite3.Error as e:
                logger.warning("Index creation failed: %s — %s", idx_sql[:50], e)
        self.conn.commit()
        logger.info("Created %d database indexes", len(indexes))

    # ──────────────────────────────────────────────
    # DATA INSERTION
    # ──────────────────────────────────────────────

    def _get_table_columns(self, table_name: str) -> list[str]:
        """Get existing column names for a table."""
        try:
            cursor = self.conn.execute(f"PRAGMA table_info({table_name})")
            return [row[1] for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def _insert_dataframe(self, table_name: str, df: pd.DataFrame,
                           chunk_size: int = 1000) -> int:
        """Insert a DataFrame into a table, matching only existing columns."""
        if df is None or df.empty:
            return 0

        # Get existing table columns (exclude autoincrement PK)
        table_cols = self._get_table_columns(table_name)
        if not table_cols:
            logger.warning("Table %s has no columns or doesn't exist", table_name)
            return 0

        # Exclude autoincrement PK only if the DataFrame doesn't provide it
        # (e.g., tbCaseData provides coId as the numeric case_id for FK references)
        pk_col = "coId"
        if pk_col in df.columns:
            insert_cols = list(table_cols)
        else:
            insert_cols = [c for c in table_cols if c != pk_col]

        # Match DataFrame columns to table columns (case-sensitive first)
        df_cols = set(df.columns)
        matched_cols = [c for c in insert_cols if c in df_cols]

        # Also try case-insensitive matching for remaining unmatched columns
        unmatched_schema = [c for c in insert_cols if c not in df_cols]
        if unmatched_schema:
            df_cols_lower = {c.lower(): c for c in df.columns}
            for tc in unmatched_schema:
                df_col = df_cols_lower.get(tc.lower())
                if df_col and df_col not in [c for c in matched_cols]:
                    df = df.rename(columns={df_col: tc})
                    matched_cols.append(tc)

        if not matched_cols:
            logger.warning("No matching columns for %s", table_name)
            return 0

        # Prepare insert statement (use OR IGNORE when inserting explicit PKs)
        placeholders = ", ".join(["?"] * len(matched_cols))
        col_names = ", ".join(matched_cols)
        ignore = " OR IGNORE" if pk_col in df.columns else ""
        sql = f"INSERT{ignore} INTO {table_name} ({col_names}) VALUES ({placeholders})"

        # Convert DataFrame to list of tuples (vectorized for performance)
        # Convert numpy types and NaN to Python-native types for sqlite3
        insert_df = df[matched_cols].copy()

        total_inserted = 0
        for start in range(0, len(insert_df), chunk_size):
            chunk = insert_df.iloc[start:start + chunk_size]
            rows = [
                tuple(self._to_sqlite_value(v) for v in record)
                for record in chunk.itertuples(index=False, name=None)
            ]

            try:
                cursor = self.conn.executemany(sql, rows)
                # Use rowcount for accurate count (handles OR IGNORE)
                total_inserted += cursor.rowcount if cursor.rowcount >= 0 else len(rows)
            except sqlite3.Error as e:
                logger.error("Insert error for %s (chunk %d): %s",
                             table_name, start // chunk_size, e)
                # Try row-by-row as fallback
                failed_count = 0
                for row_data in rows:
                    try:
                        self.conn.execute(sql, row_data)
                        total_inserted += 1
                    except sqlite3.Error as row_err:
                        failed_count += 1
                        if failed_count <= 3:
                            logger.warning("Row insert failed for %s: %s",
                                           table_name, row_err)
                if failed_count > 3:
                    logger.warning("Suppressed %d more row insert errors for %s",
                                   failed_count - 3, table_name)

        logger.info("Inserted %d rows into %s", total_inserted, table_name)
        return total_inserted

    def insert_all(self, mapped_tables: dict[str, pd.DataFrame]) -> dict[str, int]:
        """Insert all mapped tables in FK-respecting order."""
        if not self.conn:
            self.connect()

        # Child tables that require a valid coCaseId (FK to tbCaseData)
        fk_required_tables = {
            "tbImportLabsData", "tbImportIcd10Data",
            "tbImportDeviceMotionData", "tbImportDevice1HzMotionData",
            "tbImportMedicationInpatientData", "tbImportNursingDailyReportsData",
        }

        valid_case_ids = None  # Populated after tbCaseData is inserted

        results = {}
        for table_name in TABLE_INSERT_ORDER:
            df = mapped_tables.get(table_name)
            if df is not None and not df.empty:
                # After inserting tbCaseData, collect valid IDs for FK filtering
                if table_name == "tbCaseData":
                    count = self._insert_dataframe(table_name, df)
                    results[table_name] = count
                    # Build set of valid case IDs (coId, coCaseIdAlpha, coPatientId, coE2I222)
                    valid_case_ids = set()
                    for id_col in ("coId", "coE2I222"):
                        if id_col in df.columns:
                            valid_case_ids.update(df[id_col].dropna().unique())
                            valid_case_ids.update(str(v) for v in df[id_col].dropna().unique())
                    if "coCaseIdAlpha" in df.columns:
                        valid_case_ids.update(df["coCaseIdAlpha"].dropna().unique())
                    if "coPatientId" in df.columns:
                        valid_case_ids.update(df["coPatientId"].dropna().unique())
                        valid_case_ids.update(str(v) for v in df["coPatientId"].dropna().unique())
                    continue

                # Drop rows with NULL or orphan coCaseId in child tables
                if table_name in fk_required_tables and "coCaseId" in df.columns:
                    if df["coCaseId"].isna().any():
                        null_count = df["coCaseId"].isna().sum()
                        logger.info("Dropping %d rows with NULL coCaseId from %s",
                                    null_count, table_name)
                        df = df.dropna(subset=["coCaseId"])
                    if valid_case_ids is not None:
                        orphan_mask = ~df["coCaseId"].isin(valid_case_ids)
                        if orphan_mask.any():
                            orphan_count = orphan_mask.sum()
                            logger.info("Dropping %d rows with orphan coCaseId from %s",
                                        orphan_count, table_name)
                            df = df[~orphan_mask]
                count = self._insert_dataframe(table_name, df)
                results[table_name] = count
            else:
                results[table_name] = 0
                logger.info("Skipped %s (empty or missing)", table_name)

        self.conn.commit()
        return results

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────

    @staticmethod
    def _to_sqlite_value(v):
        """Convert a single value to a sqlite3-compatible Python type."""
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
        if isinstance(v, (int, float)):
            return v
        return str(v)

    @staticmethod
    def _normalize_row_number(rn) -> Optional[int]:
        """Normalize row_number from tuple/list/numpy to int or None."""
        if rn is None:
            return None
        if isinstance(rn, (tuple, list)):
            rn = rn[0] if rn else None
        try:
            return int(rn) if rn is not None else None
        except (ValueError, TypeError):
            return None

    # ──────────────────────────────────────────────
    # AUDIT LOG EXPORT
    # ──────────────────────────────────────────────

    def insert_audit_log(self, entries: list[AuditLogEntry],
                          chunk_size: int = 5000) -> int:
        """Insert audit log entries into tbAuditLog."""
        if not self.conn:
            self.connect()
        if not entries:
            return 0

        sql = """
            INSERT INTO tbAuditLog
            (source_file, case_id, table_name, column_name,
             original_value, cleaned_value, error_type, severity,
             action_taken, corrected_by, correction_timestamp, row_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        total = 0
        for start in range(0, len(entries), chunk_size):
            chunk = entries[start:start + chunk_size]
            rows = []
            for e in chunk:
                severity = e.severity.value if isinstance(e.severity, Severity) else str(e.severity)
                action = e.action_taken.value if isinstance(e.action_taken, ActionTaken) else str(e.action_taken)
                ts = e.correction_timestamp.isoformat() if e.correction_timestamp else None
                rn = self._normalize_row_number(e.row_number)
                rows.append((
                    e.source_file, e.case_id, e.table_name, e.column_name,
                    e.original_value, e.cleaned_value, e.error_type,
                    severity, action, e.corrected_by, ts, rn,
                ))

            try:
                self.conn.executemany(sql, rows)
                total += len(rows)
            except sqlite3.Error as err:
                logger.error("Audit log insert error: %s", err)

        self.conn.commit()
        logger.info("Inserted %d audit log entries", total)
        return total

    # ──────────────────────────────────────────────
    # DATA PASSPORT EXPORT
    # ──────────────────────────────────────────────

    def insert_data_passports(self, entries: list[AuditLogEntry],
                               chunk_size: int = 5000) -> int:
        """Convert audit log entries to data passports and insert."""
        if not self.conn:
            self.connect()
        if not entries:
            return 0

        sql = """
            INSERT INTO tbDataPassport
            (case_id, table_name, field_name, raw_value, cleaned_value,
             detected_by, problem_type, problem_detail, action_taken,
             confidence, validated_by, fhir_alignment, status,
             source_file, row_number, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """

        # Map error types to problem types
        error_to_problem = {
            "MISSING_VALUE": "MISSING",
            "MISSING_NORMALIZED": "MISSING",
            "INVALID_DATE": "INVALID",
            "DATE_OUT_OF_RANGE": "INVALID",
            "CLINICAL_OUTLIER": "OUTLIER",
            "NON_NUMERIC": "INVALID",
            "NON_NUMERIC_CLEANED": "CORRECTED",
            "SPECIAL_CHARS_REMOVED": "CORRECTED",
            "GENDER_INVALID": "INVALID",
            "GENDER_NORMALIZED": "CORRECTED",
            "ID_INVALID": "INVALID",
            "ID_CLEANED": "CORRECTED",
            "PID_PREFIXED": "CORRECTED",
            "PID_CONFLICT": "DUPLICATE",
            "DUPLICATE": "DUPLICATE",
            "DUPLICATE_REMOVED": "DUPLICATE",
            "PARTIAL_DUPLICATE_REMOVED": "DUPLICATE",
            "LAB_FLAG_INVALID": "INVALID",
            "LAB_FLAG_CLEANED": "CORRECTED",
            "DATE_NORMALIZED": "CORRECTED",
            "CASE_ID_MAPPED": "CORRECTED",
            "CASE_ID_MAPPED_PID_ONLY": "CORRECTED",
        }

        # Map action to passport status
        action_to_status = {
            "QUARANTINE": "QUARANTINE",
            "AUTO_CORRECT": "CLEAN",
            "FLAGGED": "PENDING_REVIEW",
            "ACCEPTED": "CLEAN",
            "MANUAL_CORRECT": "CLEAN",
        }

        total = 0
        for start in range(0, len(entries), chunk_size):
            chunk = entries[start:start + chunk_size]
            rows = []
            for e in chunk:
                action = e.action_taken.value if isinstance(e.action_taken, ActionTaken) else str(e.action_taken)
                problem_type = error_to_problem.get(e.error_type, "INVALID")
                status = action_to_status.get(action, "PENDING_REVIEW")
                confidence = 0.95 if action == "AUTO_CORRECT" else 0.5
                rn = self._normalize_row_number(e.row_number)
                rows.append((
                    e.case_id, e.table_name, e.column_name,
                    e.original_value, e.cleaned_value,
                    e.corrected_by or "auto",
                    problem_type, e.error_type, action,
                    confidence, None, None, status,
                    e.source_file, rn,
                ))

            try:
                self.conn.executemany(sql, rows)
                total += len(rows)
            except sqlite3.Error as err:
                logger.error("Data passport insert error: %s", err)

        self.conn.commit()
        logger.info("Inserted %d data passport entries", total)
        return total

    # ──────────────────────────────────────────────
    # FULL EXPORT
    # ──────────────────────────────────────────────

    def export_all(self, mapped_tables: dict[str, pd.DataFrame],
                    audit_log: list[AuditLogEntry] = None) -> dict:
        """Full export: create schema, insert data, insert audit log."""
        if not self.conn:
            self.connect()

        # Remove existing DB and recreate
        if os.path.exists(self.db_path):
            self.close()
            os.remove(self.db_path)
            self.connect()

        self.create_schema()

        # Insert mapped data
        insert_results = self.insert_all(mapped_tables)

        # Insert audit log
        audit_count = 0
        passport_count = 0
        if audit_log:
            audit_count = self.insert_audit_log(audit_log)
            # Only create passports for non-trivial entries
            significant = [
                e for e in audit_log
                if e.error_type not in ("MISSING_VALUE", "PID_PREFIXED", "MISSING_NORMALIZED")
            ]
            passport_count = self.insert_data_passports(significant)

        # Create indexes for API query performance
        self._create_indexes()

        summary = {
            "db_path": self.db_path,
            "tables": insert_results,
            "audit_log_entries": audit_count,
            "data_passports": passport_count,
            "total_rows": sum(insert_results.values()),
        }

        logger.info("Export complete: %s", summary)
        return summary

    def get_connection(self) -> sqlite3.Connection:
        """Get or create the database connection."""
        if not self.conn:
            self.connect()
        return self.conn


class MSSQLExporter:
    """Exports mapped DataFrames to SQL Server via SQLAlchemy + pyodbc."""

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or MSSQL_CONNECTION_STRING
        self.engine = None

    def connect(self):
        """Create SQLAlchemy engine for SQL Server."""
        try:
            from sqlalchemy import create_engine
            self.engine = create_engine(self.connection_string)
            logger.info("Connected to SQL Server")
            return self.engine
        except ImportError:
            logger.error("sqlalchemy/pyodbc not installed for SQL Server support")
            raise
        except Exception as e:
            logger.error("SQL Server connection failed: %s", e)
            raise

    def close(self):
        """Dispose of the engine."""
        if self.engine:
            self.engine.dispose()
            self.engine = None

    def create_schema(self):
        """Execute the T-SQL schema file directly on SQL Server."""
        if not self.engine:
            self.connect()

        if os.path.exists(SQL_SCHEMA_PATH):
            from sqlalchemy import text

            with open(SQL_SCHEMA_PATH, "r", encoding="utf-8-sig") as f:
                tsql = f.read()

            # Split on 'go' statements
            batches = re.split(r'(?mi)^\s*go\s*$', tsql)
            with self.engine.connect() as conn:
                for batch in batches:
                    batch = batch.strip()
                    if batch:
                        try:
                            conn.execute(text(batch))
                        except Exception as e:
                            logger.warning("Schema batch error: %s", e)
                conn.commit()
            logger.info("SQL Server schema created")

    def insert_all(self, mapped_tables: dict[str, pd.DataFrame]) -> dict[str, int]:
        """Insert all mapped tables using pandas to_sql."""
        if not self.engine:
            self.connect()

        results = {}
        for table_name in TABLE_INSERT_ORDER:
            df = mapped_tables.get(table_name)
            if df is not None and not df.empty:
                try:
                    # Remove coId if present (let SQL Server handle IDENTITY)
                    insert_df = df.drop(columns=["coId"], errors="ignore")
                    insert_df.to_sql(
                        table_name, self.engine,
                        if_exists="append", index=False,
                        chunksize=1000, method="multi",
                    )
                    results[table_name] = len(insert_df)
                except Exception as e:
                    logger.error("MSSQL insert error for %s: %s", table_name, e)
                    results[table_name] = 0
            else:
                results[table_name] = 0

        return results

    def export_all(self, mapped_tables: dict[str, pd.DataFrame],
                    audit_log: list[AuditLogEntry] = None) -> dict:
        """Full export to SQL Server."""
        if not self.engine:
            self.connect()

        self.create_schema()
        insert_results = self.insert_all(mapped_tables)

        # Insert audit log as DataFrame
        audit_count = 0
        if audit_log:
            audit_df = pd.DataFrame([
                {
                    "source_file": e.source_file,
                    "case_id": e.case_id,
                    "table_name": e.table_name,
                    "column_name": e.column_name,
                    "original_value": e.original_value,
                    "cleaned_value": e.cleaned_value,
                    "error_type": e.error_type,
                    "severity": e.severity.value if isinstance(e.severity, Severity) else str(e.severity),
                    "action_taken": e.action_taken.value if isinstance(e.action_taken, ActionTaken) else str(e.action_taken),
                    "corrected_by": e.corrected_by,
                    "correction_timestamp": e.correction_timestamp,
                    "row_number": e.row_number,
                }
                for e in audit_log
            ])
            try:
                audit_df.to_sql(
                    "tbAuditLog", self.engine,
                    if_exists="append", index=False,
                    chunksize=5000, method="multi",
                )
                audit_count = len(audit_df)
            except Exception as e:
                logger.error("MSSQL audit log insert error: %s", e)

        return {
            "connection": self.connection_string,
            "tables": insert_results,
            "audit_log_entries": audit_count,
            "total_rows": sum(insert_results.values()),
        }


def create_exporter(db_type: Optional[str] = None,
                     **kwargs) -> "SQLExporter | MSSQLExporter":
    """Factory: create the appropriate exporter based on config."""
    db_type = db_type or DB_TYPE
    if db_type == "mssql" and MSSQL_CONNECTION_STRING:
        return MSSQLExporter(**kwargs)
    return SQLExporter(**kwargs)
