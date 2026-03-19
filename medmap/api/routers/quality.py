"""
Quality router — audit log, data passports, completeness.
GET  /api/quality/audit-log
GET  /api/quality/passports
GET  /api/quality/completeness
"""

import logging
from fastapi import APIRouter, Query

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
