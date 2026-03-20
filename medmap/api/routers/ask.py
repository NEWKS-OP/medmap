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
    (["age", "old", "alter", "elderly"], "SELECT c.coAgeYears as age, COUNT(*) as nb_patients FROM tbCaseData c WHERE c.coAgeYears IS NOT NULL GROUP BY c.coAgeYears ORDER BY c.coAgeYears"),
    (["gender", "sex", "geschlecht", "male", "female"], "SELECT coGender as gender, COUNT(*) as nb_patients FROM tbCaseData WHERE coGender IS NOT NULL GROUP BY coGender"),
    (["risk", "risque", "risiko", "convergence", "score"], "SELECT c.coCaseIdAlpha, c.coAgeYears, c.coGender, i.coWard FROM tbCaseData c LEFT JOIN tbImportIcd10Data i ON i.coCaseId = c.coId LEFT JOIN tbImportDeviceMotionData d ON d.coCaseId = c.coId WHERE d.coFall_event_0_1 = '1' GROUP BY c.coId LIMIT 50"),
    (["anticoag", "warfarin", "inr", "phenprocoumon"], "SELECT m.coCaseId, c.coCaseIdAlpha, m.coMedication_name, l.coInr, l.coInr_flag FROM tbImportMedicationInpatientData m LEFT JOIN tbCaseData c ON c.coId = m.coCaseId LEFT JOIN tbImportLabsData l ON l.coCaseId = m.coCaseId WHERE LOWER(m.coMedication_name) LIKE '%warfarin%' OR LOWER(m.coMedication_name) LIKE '%phenprocoumon%' LIMIT 50"),
    (["refused", "refus", "not given", "verweigert"], "SELECT m.coCaseId, c.coCaseIdAlpha, m.coMedication_name, m.administration_status FROM tbImportMedicationInpatientData m LEFT JOIN tbCaseData c ON c.coId = m.coCaseId WHERE LOWER(m.administration_status) LIKE '%refused%' OR LOWER(m.administration_status) LIKE '%not_given%' LIMIT 50"),
    (["corrected", "repair", "fix", "korrektur"], "SELECT error_type, action_taken, COUNT(*) as cnt FROM tbAuditLog WHERE action_taken IN ('AUTO_CORRECT', 'MANUAL_CORRECT') GROUP BY error_type, action_taken ORDER BY cnt DESC"),
    (["assessment", "epaac", "epa", "bewertung"], "SELECT a.coCaseId, c.coCaseIdAlpha, COUNT(*) as nb_assessments FROM tbImportAcData a LEFT JOIN tbCaseData c ON c.coId = a.coCaseId GROUP BY a.coCaseId ORDER BY nb_assessments DESC LIMIT 50"),
    (["motion", "movement", "bewegung", "device", "sensor"], "SELECT d.coCaseId, c.coCaseIdAlpha, AVG(CAST(d.coMovement_index_0_100 AS FLOAT)) as avg_movement, SUM(CASE WHEN d.coFall_event_0_1 = '1' THEN 1 ELSE 0 END) as falls FROM tbImportDeviceMotionData d LEFT JOIN tbCaseData c ON c.coId = d.coCaseId GROUP BY d.coCaseId ORDER BY falls DESC LIMIT 50"),
    (["deteriorat", "verschlecht"], "SELECT n.coCaseId, c.coCaseIdAlpha, n.coReport_date, n.coShift, n.coDeterioration_signs, SUBSTR(n.coNursing_note_free_text, 1, 80) as note FROM tbImportNursingDailyReportsData n LEFT JOIN tbCaseData c ON c.coId = n.coCaseId WHERE n.coDeterioration_flag = 1 LIMIT 50"),
    (["pain", "schmerz", "douleur"], "SELECT n.coCaseId, c.coCaseIdAlpha, n.coReport_date, n.coPain_level_extracted, SUBSTR(n.coNursing_note_free_text, 1, 80) as note FROM tbImportNursingDailyReportsData n LEFT JOIN tbCaseData c ON c.coId = n.coCaseId WHERE n.coPain_level_extracted IS NOT NULL ORDER BY n.coPain_level_extracted DESC LIMIT 50"),
]

DEFAULT_SQL = (
    "SELECT 'tbCaseData' as tbl, COUNT(*) as cnt FROM tbCaseData "
    "UNION ALL SELECT 'tbImportLabsData', COUNT(*) FROM tbImportLabsData "
    "UNION ALL SELECT 'tbAuditLog', COUNT(*) FROM tbAuditLog"
)


def _question_to_sql(question: str) -> str:
    """Match question keywords to predefined SQL queries (offline fallback)."""
    q_lower = question.lower()
    for keywords, sql in SQL_PATTERNS:
        if any(kw in q_lower for kw in keywords):
            return sql
    return DEFAULT_SQL


@router.post("")
async def ask_data(body: dict = Body(default={"question": ""})):
    """Ask a natural language question about the data.

    Uses Claude API for SQL generation when available, falls back to keyword matching."""
    db = get_db()
    question = body.get("question", "") if body else ""

    if not question or not question.strip():
        return {
            "question": "", "sql_generated": "", "results_as_dicts": None,
            "narrative_answer": None, "error": "No question provided",
            "row_count": 0, "execution_time_ms": 0.0, "used_llm": False,
        }

    start = time.time()

    try:
        # Use LLM-powered agent
        from pipeline.agents.data_analyst_agent import ask_data as llm_ask
        entry = llm_ask(question, db)
        add_ask_history(entry)
        logger.info("Ask query: %s -> %d results in %.1fms (llm=%s)",
                     question[:50], entry["row_count"], entry["execution_time_ms"], entry.get("used_llm"))
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
            "used_llm": False,
        }
        add_ask_history(entry)
        return entry


@router.get("/history")
async def get_history() -> list[dict]:
    """Get ask-your-data query history, most recent first."""
    return list(reversed(get_ask_history_list()))
