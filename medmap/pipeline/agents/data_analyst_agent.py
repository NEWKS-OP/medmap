"""Data Analyst Agent: Ask Your Data (question -> SQL -> results).

Uses Claude API to convert natural language questions into SQL queries,
executes them against the SQLite database, and generates narrative answers.
Falls back to keyword matching when no API key is available.
"""

import logging
import time
import sqlite3
from typing import Optional

from config.settings import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# Compact schema for the prompt (only key tables, not epaAC with 200+ columns)
DB_SCHEMA = """
Tables in SQLite database:

tbCaseData (6124 rows) — Patient/case master
  coId INTEGER PK, coCaseIdAlpha TEXT, coPatientId TEXT, coGender TEXT, coAgeYears TEXT,
  coDateOfBirth TEXT, coIcd TEXT, coDrgName TEXT, coTypeOfStay TEXT, coState TEXT

tbImportLabsData (10648 rows) — Lab results
  coId PK, coCaseId FK->tbCaseData.coId, coSpecimen_datetime TEXT,
  coSodium_mmol_L, coPotassium_mmol_L, coCreatinine_mg_dL, coEgfr_mL_min_1_73m2,
  coGlucose_mg_dL, coHemoglobin_g_dL, coWbc_10e9_L, coPlatelets_10e9_L,
  coCrp_mg_L, coAlt_U_L, coAst_U_L, coBilirubin_mg_dL, coAlbumin_g_dL,
  coInr, coLactate_mmol_L
  (each has _flag column: H=high, L=low, HH=critical high, LL=critical low)
  (values stored as TEXT — CAST to REAL for numeric comparisons)

tbImportIcd10Data (1908 rows) — Diagnoses
  coId PK, coCaseId FK, coWard TEXT, coAdmission_date TEXT, coDischarge_date TEXT,
  coLength_of_stay_days, coPrimary_icd10_code TEXT, coPrimary_icd10_description_en TEXT

tbImportDeviceMotionData (93887 rows) — Motion sensor summary
  coId PK, coCaseId FK, coTimestamp TEXT, coMovement_index_0_100,
  coBed_exit_detected_0_1, coFall_event_0_1, coImpact_magnitude_g,
  coPost_fall_immobility_minutes

tbImportMedicationInpatientData (51816 rows) — Medications
  coId PK, coCaseId FK, coMedication_name TEXT, coMedication_code_atc TEXT,
  coRoute TEXT, coDose TEXT, coFrequency TEXT, coIndication TEXT, administration_status TEXT

tbImportNursingDailyReportsData (4200 rows) — Nursing notes + NLP
  coId PK, coCaseId FK, coReport_date TEXT, coShift TEXT,
  coNursing_note_free_text TEXT, coPain_level_extracted INTEGER,
  coMobility_extracted TEXT, coWound_grade_extracted TEXT,
  coDeterioration_flag INTEGER, coDeterioration_signs TEXT

tbAuditLog — Data quality audit trail
  source_file, case_id, column_name, original_value, cleaned_value,
  error_type, severity (LOW/MEDIUM/HIGH/CRITICAL), action_taken

tbDataPassport — Data lineage
  passport_id PK, case_id, field_name, raw_value, cleaned_value,
  problem_type, problem_detail, status
""".strip()

SYSTEM_PROMPT = f"""You are a medical data analyst SQL expert. Given a natural language question about hospital patient data, generate a SQLite query.

{DB_SCHEMA}

Rules:
- Output ONLY the SQL query, nothing else. No markdown, no explanation.
- Use SQLite syntax (no TOP, use LIMIT instead).
- Always LIMIT to 100 rows max unless the user asks for aggregates.
- Join through coCaseId FK when crossing tables.
- Lab values are stored as TEXT — CAST to REAL for comparisons.
- For patient lookups, join tbCaseData to get coCaseIdAlpha (human-readable ID).
- Never modify data (no INSERT/UPDATE/DELETE/DROP).
"""


def question_to_sql_with_llm(question: str) -> Optional[str]:
    """Use Claude API to convert a question to SQL."""
    if not ANTHROPIC_API_KEY:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": question}],
        )

        sql = response.content[0].text.strip()

        # Strip markdown code blocks if present
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        # Safety: reject non-SELECT queries
        first_word = sql.strip().split()[0].upper() if sql.strip() else ""
        if first_word not in ("SELECT", "WITH"):
            logger.warning("LLM returned non-SELECT query: %s", sql[:100])
            return None

        return sql.strip()

    except Exception as e:
        logger.warning("Claude API call failed for SQL gen: %s", e)
        return None


def generate_narrative_with_llm(question: str, sql: str, results: list[dict]) -> Optional[str]:
    """Use Claude API to generate a narrative answer from query results."""
    if not ANTHROPIC_API_KEY or not results:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Limit results in prompt to avoid token explosion
        sample = results[:20]
        results_str = str(sample)
        if len(results_str) > 3000:
            results_str = results_str[:3000] + "..."

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system="You are a medical data analyst. Given a question, the SQL used, and the results, write a concise 2-4 sentence summary. Be specific with numbers. Use clinical language when appropriate.",
            messages=[{"role": "user", "content": f"Question: {question}\nSQL: {sql}\nResults ({len(results)} rows): {results_str}"}],
        )

        return response.content[0].text.strip()

    except Exception as e:
        logger.warning("Narrative generation failed: %s", e)
        return None


def ask_data(question: str, db: sqlite3.Connection) -> dict:
    """Full Ask Your Data pipeline: question -> SQL -> execute -> narrative."""
    start = time.time()

    # Try LLM first, fall back to keyword matching
    sql = question_to_sql_with_llm(question)
    used_llm = sql is not None

    if not sql:
        from api.routers.ask import _question_to_sql
        sql = _question_to_sql(question)

    # Execute
    results = None
    error = None
    try:
        rows = db.execute(sql).fetchall()
        results = [dict(r) for r in rows]
    except Exception as e:
        error = str(e)
        logger.error("SQL execution failed: %s — SQL: %s", e, sql[:200])

    # Generate narrative
    narrative = None
    if results and used_llm:
        narrative = generate_narrative_with_llm(question, sql, results)

    if not narrative and results:
        narrative = f"Found {len(results)} results."
        if results and len(results[0]) == 2 and "cnt" in results[0]:
            lines = [f"- {list(r.values())[0]}: {r.get('cnt', 'N/A'):,}" for r in results[:15]]
            narrative = "Here are the counts:\n" + "\n".join(lines)

    elapsed = (time.time() - start) * 1000

    return {
        "question": question,
        "sql_generated": sql,
        "results_as_dicts": results,
        "narrative_answer": narrative,
        "error": error,
        "row_count": len(results) if results else 0,
        "execution_time_ms": round(elapsed, 1),
        "used_llm": used_llm,
    }
