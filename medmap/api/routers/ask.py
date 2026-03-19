"""
Ask Your Data router — natural language to SQL queries.
POST /api/ask
GET  /api/ask/history
"""

import logging
import time
from fastapi import APIRouter, Body

from api.dependencies import get_db, add_ask_history, get_ask_history_list

logger = logging.getLogger(__name__)

router = APIRouter(responses={200: {"description": "Query results"}})

# Simple keyword-to-SQL patterns for offline fallback
SQL_PATTERNS = [
    (["fall", "chute", "sturz"], "SELECT d.coCaseId, c.coCaseIdAlpha, d.coTimestamp, d.coFall_event_0_1, d.coImpact_magnitude_g, d.coPost_fall_immobility_minutes FROM tbImportDeviceMotionData d LEFT JOIN tbCaseData c ON c.coId = d.coCaseId WHERE d.coFall_event_0_1 = '1' LIMIT 50"),
    (["medication", "medic", "drug"], "SELECT m.coCaseId, c.coCaseIdAlpha, m.coMedication_name, m.coDose, m.coFrequency, m.administration_status FROM tbImportMedicationInpatientData m LEFT JOIN tbCaseData c ON c.coId = m.coCaseId LIMIT 50"),
    (["lab", "labo", "sodium", "creatinine", "egfr"], "SELECT l.coCaseId, c.coCaseIdAlpha, l.coSodium_mmol_L, l.coPotassium_mmol_L, l.coCreatinine_mg_dL, l.coEgfr_mL_min_1_73m2, l.coCrp_mg_L FROM tbImportLabsData l LEFT JOIN tbCaseData c ON c.coId = l.coCaseId LIMIT 50"),
    (["error", "erreur", "quality", "qualit"], "SELECT error_type, severity, COUNT(*) as count FROM tbAuditLog GROUP BY error_type, severity ORDER BY count DESC"),
    (["ward", "service", "station"], "SELECT coWard, COUNT(DISTINCT coCaseId) as nb_patients FROM tbImportIcd10Data WHERE coWard IS NOT NULL GROUP BY coWard ORDER BY nb_patients DESC"),
    (["critical", "critique"], "SELECT case_id, error_type, column_name, original_value, source_file FROM tbAuditLog WHERE severity = 'CRITICAL' LIMIT 50"),
    (["nursing", "infirm", "note"], "SELECT n.coCaseId, c.coCaseIdAlpha, n.coReport_date, n.coShift, SUBSTR(n.coNursing_note_free_text, 1, 100) as note FROM tbImportNursingDailyReportsData n LEFT JOIN tbCaseData c ON c.coId = n.coCaseId LIMIT 50"),
    (["icd", "diagnos"], "SELECT i.coCaseId, c.coCaseIdAlpha, i.coPrimary_icd10_code, i.coPrimary_icd10_description_en, i.coWard FROM tbImportIcd10Data i LEFT JOIN tbCaseData c ON c.coId = i.coCaseId LIMIT 50"),
    (["quarantine", "quarantaine"], "SELECT case_id, field_name, raw_value, problem_detail, status FROM tbDataPassport WHERE status = 'QUARANTINE' LIMIT 50"),
    (["patient", "case"], "SELECT c.coId, c.coCaseIdAlpha, c.coPatientId, c.coGender, c.coAgeYears, c.coIcd, i.coWard FROM tbCaseData c LEFT JOIN tbImportIcd10Data i ON i.coCaseId = c.coId LIMIT 50"),
    (["count", "combien", "total", "how many"], "SELECT 'tbCaseData' as tbl, COUNT(*) as cnt FROM tbCaseData UNION ALL SELECT 'tbImportLabsData', COUNT(*) FROM tbImportLabsData UNION ALL SELECT 'tbImportIcd10Data', COUNT(*) FROM tbImportIcd10Data UNION ALL SELECT 'tbImportDeviceMotionData', COUNT(*) FROM tbImportDeviceMotionData UNION ALL SELECT 'tbImportMedicationInpatientData', COUNT(*) FROM tbImportMedicationInpatientData UNION ALL SELECT 'tbImportNursingDailyReportsData', COUNT(*) FROM tbImportNursingDailyReportsData UNION ALL SELECT 'tbAuditLog', COUNT(*) FROM tbAuditLog"),
]

DEFAULT_SQL = (
    "SELECT 'tbCaseData' as tbl, COUNT(*) as cnt FROM tbCaseData "
    "UNION ALL SELECT 'tbImportLabsData', COUNT(*) FROM tbImportLabsData "
    "UNION ALL SELECT 'tbAuditLog', COUNT(*) FROM tbAuditLog"
)


def _question_to_sql(question: str) -> str:
    """Simple keyword matching to generate SQL. Offline fallback."""
    q_lower = question.lower()
    for keywords, sql in SQL_PATTERNS:
        if any(kw in q_lower for kw in keywords):
            return sql
    return DEFAULT_SQL


@router.post("")
async def ask_data(body: dict = Body(default={"question": ""})):
    """Ask a natural language question about the data.

    Uses keyword matching to generate SQL (offline fallback).
    Returns SQL, results, and narrative answer."""
    db = get_db()
    question = body.get("question", "") if body else ""

    if not question or not question.strip():
        return {
            "question": "", "sql_generated": "", "results_as_dicts": None,
            "narrative_answer": None, "error": "No question provided",
            "row_count": 0, "execution_time_ms": 0.0,
        }

    start = time.time()

    try:
        sql = _question_to_sql(question)
        rows = db.execute(sql).fetchall()
        results = [dict(r) for r in rows]
        elapsed_ms = (time.time() - start) * 1000

        # Simple narrative
        narrative = f"Found {len(results)} results."
        if results:
            first_keys = list(results[0].keys())
            if len(first_keys) == 2 and "cnt" in first_keys:
                lines = [f"- {r[first_keys[0]]}: {r['cnt']:,}" for r in results]
                narrative = "Here are the counts:\n" + "\n".join(lines)

        entry = {
            "question": question,
            "sql_generated": sql,
            "results_as_dicts": results,
            "narrative_answer": narrative,
            "error": None,
            "row_count": len(results),
            "execution_time_ms": round(elapsed_ms, 1),
        }
        add_ask_history(entry)
        logger.info("Ask query: %s -> %d results in %.1fms", question[:50], len(results), elapsed_ms)
        return entry

    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        logger.error("ask_data error: %s", e)
        entry = {
            "question": question,
            "sql_generated": _question_to_sql(question),
            "results_as_dicts": None,
            "narrative_answer": None,
            "error": str(e),
            "row_count": 0,
            "execution_time_ms": round(elapsed_ms, 1),
        }
        add_ask_history(entry)
        return entry


@router.get("/history")
async def get_history() -> list[dict]:
    """Get ask-your-data query history, most recent first."""
    return get_ask_history_list()
