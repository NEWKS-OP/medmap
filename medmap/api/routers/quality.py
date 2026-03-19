"""
Quality router — audit log, data passports, completeness, before/after.
GET  /api/quality/audit-log
GET  /api/quality/passports
GET  /api/quality/completeness
GET  /api/quality/before-after
GET  /api/quality/error-categories
"""

import csv
import io
import logging
from typing import Any
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from api.dependencies import get_db, rows_to_dicts

logger = logging.getLogger(__name__)

router = APIRouter(responses={200: {"description": "Quality data"}})


@router.get("/audit-log")
async def get_audit_log(
    source: str = Query(None, description="Filter by source file"),
    severity: str = Query(None, description="Filter by severity (comma-separated)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Results offset"),
):
    """Get audit log entries with optional filters.

    Supports filtering by source file and severity level."""
    db = get_db()
    try:
        conditions = []
        params = []

        if source:
            conditions.append("source_file = ?")
            params.append(source)

        if severity:
            sev_list = severity.upper().split(",")
            placeholders = ",".join("?" for _ in sev_list)
            conditions.append(f"severity IN ({placeholders})")
            params.extend(sev_list)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        query = f"SELECT * FROM tbAuditLog {where} ORDER BY coId DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = db.execute(query, params).fetchall()
        return rows_to_dicts(rows)
    except Exception as e:
        logger.error("audit-log error: %s", e)
        return []


@router.get("/passports")
async def get_passports(
    status: str = Query(None, description="Filter by passport status"),
    problem_type: str = Query(None, description="Filter by problem type"),
    limit: int = Query(200, ge=1, le=1000, description="Max results"),
):
    """Get data passports with optional filters.

    Supports filtering by status and problem type."""
    db = get_db()
    try:
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if problem_type:
            conditions.append("problem_type = ?")
            params.append(problem_type)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        query = f"SELECT * FROM tbDataPassport {where} ORDER BY passport_id DESC LIMIT ?"
        params.append(limit)

        rows = db.execute(query, params).fetchall()
        return rows_to_dicts(rows)
    except Exception as e:
        logger.error("passports error: %s", e)
        return []


@router.get("/completeness")
async def get_completeness() -> dict:
    """Get completeness matrix.

    Returns table_name -> column_name -> percentage complete."""
    db = get_db()
    try:
        # All import tables to check completeness for
        tables = [
            "tbImportLabsData",
            "tbImportIcd10Data",
            "tbImportDeviceMotionData",
            "tbImportMedicationInpatientData",
            "tbImportNursingDailyReportsData",
            "tbImportAcData",
        ]

        result = {}
        for table in tables:
            try:
                total = db.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()["cnt"]
                if total == 0:
                    continue

                cols_info = db.execute(f"PRAGMA table_info({table})").fetchall()
                col_names = [c["name"] for c in cols_info if c["name"] != "coId"]

                completeness = {}
                for col in col_names:
                    non_null = db.execute(
                        f"SELECT COUNT(*) as cnt FROM {table} WHERE [{col}] IS NOT NULL AND [{col}] != ''",
                    ).fetchone()["cnt"]
                    completeness[col] = round(non_null / total * 100, 1)

                result[table] = completeness
            except Exception:
                continue

        logger.info("Computed completeness for %d tables", len(result))
        return result
    except Exception as e:
        logger.error("completeness error: %s", e)
        return {}


@router.get("/before-after")
async def get_before_after(
    source: str = Query(None, description="Filter by source file"),
    error_type: str = Query(None, description="Filter by error type"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Results offset"),
) -> list[dict]:
    """Get before/after repair comparisons from the audit log.

    Returns entries where a value was auto-corrected or manually corrected,
    showing the original and cleaned values side by side."""
    db = get_db()
    try:
        conditions = ["cleaned_value IS NOT NULL", "original_value IS NOT NULL", "original_value != cleaned_value"]
        params: list = []

        if source:
            conditions.append("source_file = ?")
            params.append(source)

        if error_type:
            conditions.append("error_type = ?")
            params.append(error_type)

        where = "WHERE " + " AND ".join(conditions)

        rows = db.execute(
            f"""SELECT coId, source_file, case_id, table_name, column_name,
                       original_value, cleaned_value, error_type, severity,
                       action_taken, corrected_by, correction_timestamp
                FROM tbAuditLog {where}
                ORDER BY coId DESC LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()

        return [
            {
                "audit_log_id": r["coId"],
                "source_file": r["source_file"],
                "case_id": r["case_id"],
                "table_name": r["table_name"],
                "column_name": r["column_name"],
                "before": r["original_value"],
                "after": r["cleaned_value"],
                "error_type": r["error_type"],
                "severity": r["severity"],
                "action": r["action_taken"],
                "corrected_by": r["corrected_by"] or "auto",
                "timestamp": r["correction_timestamp"],
            }
            for r in rows
        ]
    except Exception as e:
        logger.error("before-after error: %s", e)
        return []


@router.get("/error-categories")
async def get_error_categories() -> list[dict]:
    """Get error counts grouped by category for chart visualization.

    Returns error_type, count, and severity breakdown."""
    db = get_db()
    try:
        rows = db.execute(
            """SELECT error_type, severity, COUNT(*) as cnt
               FROM tbAuditLog
               WHERE error_type IS NOT NULL
               GROUP BY error_type, severity
               ORDER BY cnt DESC"""
        ).fetchall()

        # Aggregate by error_type with severity breakdown
        categories: dict[str, dict] = {}
        for r in rows:
            et = r["error_type"]
            if et not in categories:
                categories[et] = {"error_type": et, "total": 0, "by_severity": {}}
            categories[et]["total"] += r["cnt"]
            categories[et]["by_severity"][r["severity"]] = r["cnt"]

        result = sorted(categories.values(), key=lambda x: x["total"], reverse=True)
        logger.info("Computed error categories: %d types", len(result))
        return result
    except Exception as e:
        logger.error("error-categories error: %s", e)
        return []


@router.get("/before-after/stats")
async def get_before_after_stats() -> dict:
    """Get aggregate statistics for the before/after repair view.

    Returns total corrections, breakdown by error type, and by source file."""
    db = get_db()
    try:
        total = db.execute(
            "SELECT COUNT(*) as cnt FROM tbAuditLog WHERE cleaned_value IS NOT NULL AND original_value IS NOT NULL AND original_value != cleaned_value"
        ).fetchone()["cnt"]

        by_error_type = db.execute(
            """SELECT error_type, COUNT(*) as cnt
               FROM tbAuditLog
               WHERE cleaned_value IS NOT NULL AND original_value IS NOT NULL AND original_value != cleaned_value
               GROUP BY error_type ORDER BY cnt DESC"""
        ).fetchall()

        by_source = db.execute(
            """SELECT source_file, COUNT(*) as cnt
               FROM tbAuditLog
               WHERE cleaned_value IS NOT NULL AND original_value IS NOT NULL AND original_value != cleaned_value
               GROUP BY source_file ORDER BY cnt DESC"""
        ).fetchall()

        by_action = db.execute(
            """SELECT action_taken, COUNT(*) as cnt
               FROM tbAuditLog
               WHERE cleaned_value IS NOT NULL AND original_value IS NOT NULL AND original_value != cleaned_value
               GROUP BY action_taken ORDER BY cnt DESC"""
        ).fetchall()

        return {
            "total_repairs": total,
            "by_error_type": {r["error_type"]: r["cnt"] for r in by_error_type},
            "by_source_file": {r["source_file"]: r["cnt"] for r in by_source},
            "by_action": {r["action_taken"]: r["cnt"] for r in by_action},
        }
    except Exception as e:
        logger.error("before-after stats error: %s", e)
        return {"total_repairs": 0, "by_error_type": {}, "by_source_file": {}, "by_action": {}}


@router.get("/export/{table_name}")
async def export_table_csv(table_name: str, limit: int = Query(10000, ge=1, le=100000)):
    """Export a database table as a CSV download.

    Only allows exporting known import tables and audit/passport tables."""
    allowed_tables = {
        "tbCaseData", "tbImportLabsData", "tbImportIcd10Data",
        "tbImportDeviceMotionData", "tbImportMedicationInpatientData",
        "tbImportNursingDailyReportsData", "tbImportAcData",
        "tbAuditLog", "tbDataPassport",
    }
    if table_name not in allowed_tables:
        return {"error": f"Table '{table_name}' not allowed for export"}

    db = get_db()
    try:
        rows = db.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,)).fetchall()
        if not rows:
            return {"error": "No data found"}

        output = io.StringIO()
        col_names = rows[0].keys()
        writer = csv.writer(output)
        writer.writerow(col_names)
        for r in rows:
            writer.writerow([r[c] for c in col_names])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={table_name}.csv"},
        )
    except Exception as e:
        logger.error("export error for %s: %s", table_name, e)
        return {"error": str(e)}
