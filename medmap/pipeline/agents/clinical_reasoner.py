"""Clinical Reasoner: SBAR generation and anomaly explanation.

Uses Claude API to generate structured clinical narratives (SBAR format)
and physiological explanations for detected anomalies.
Falls back to template-based generation when no API key is available.
"""

import logging
import sqlite3
from typing import Optional

from config.settings import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)


def generate_sbar(case_id: str, db: sqlite3.Connection) -> dict:
    """Generate an SBAR clinical summary for a patient.

    Returns dict with keys: S (Situation), B (Background), A (Assessment), R (Recommendation).
    """
    # Gather patient context
    context = _gather_patient_context(case_id, db)
    if not context:
        return {"S": f"Patient {case_id} — no data available", "B": "", "A": "", "R": ""}

    # Try LLM
    sbar = _generate_sbar_with_llm(case_id, context)
    if sbar:
        return sbar

    # Fallback: template
    return _generate_sbar_template(case_id, context)


def explain_anomaly(rule_name: str, triggered_values: dict, case_id: str) -> str:
    """Generate a physiological explanation for a clinical alert.

    Returns a 2-3 sentence explanation.
    """
    explanation = _explain_with_llm(rule_name, triggered_values, case_id)
    if explanation:
        return explanation

    return _explain_template(rule_name, triggered_values)


# ─── Context gathering ────────────────────────────────────────────

def _gather_patient_context(case_id: str, db: sqlite3.Connection) -> Optional[dict]:
    """Gather patient data for SBAR generation."""
    try:
        # Find case
        case = db.execute(
            "SELECT * FROM tbCaseData WHERE coCaseIdAlpha = ? OR CAST(coId AS TEXT) = ? LIMIT 1",
            (case_id, case_id),
        ).fetchone()
        if not case:
            return None

        cid = case["coId"]
        context = {
            "case_id": case_id,
            "age": case["coAgeYears"],
            "gender": case["coGender"],
        }

        # ICD
        icd = db.execute(
            "SELECT coWard, coPrimary_icd10_code, coPrimary_icd10_description_en, coLength_of_stay_days FROM tbImportIcd10Data WHERE coCaseId = ? LIMIT 1",
            (cid,),
        ).fetchone()
        if icd:
            context["ward"] = icd["coWard"]
            context["icd10"] = icd["coPrimary_icd10_code"]
            context["diagnosis"] = icd["coPrimary_icd10_description_en"]
            context["los_days"] = icd["coLength_of_stay_days"]

        # Latest labs
        lab = db.execute(
            """SELECT coSodium_mmol_L, coPotassium_mmol_L, coCreatinine_mg_dL,
                      coEgfr_mL_min_1_73m2, coGlucose_mg_dL, coHemoglobin_g_dL,
                      coWbc_10e9_L, coCrp_mg_L, coInr, coLactate_mmol_L
               FROM tbImportLabsData WHERE coCaseId = ?
               ORDER BY coSpecimen_datetime DESC LIMIT 1""",
            (cid,),
        ).fetchone()
        if lab:
            context["labs"] = {k: lab[k] for k in lab.keys() if lab[k] is not None}

        # Falls
        falls = db.execute(
            "SELECT COUNT(*) as cnt FROM tbImportDeviceMotionData WHERE coCaseId = ? AND coFall_event_0_1 = '1'",
            (cid,),
        ).fetchone()["cnt"]
        context["fall_count"] = falls

        # Active meds (top 5)
        meds = db.execute(
            "SELECT DISTINCT coMedication_name FROM tbImportMedicationInpatientData WHERE coCaseId = ? LIMIT 5",
            (cid,),
        ).fetchall()
        context["medications"] = [m["coMedication_name"] for m in meds if m["coMedication_name"]]

        # Nursing NLP
        try:
            det_count = db.execute(
                "SELECT COUNT(*) as cnt FROM tbImportNursingDailyReportsData WHERE coCaseId = ? AND coDeterioration_flag = 1",
                (cid,),
            ).fetchone()["cnt"]
            context["deterioration_notes"] = det_count
        except sqlite3.OperationalError:
            context["deterioration_notes"] = 0

        return context

    except Exception as e:
        logger.error("Failed to gather context for %s: %s", case_id, e)
        return None


# ─── LLM-based generation ────────────────────────────────────────

def _generate_sbar_with_llm(case_id: str, context: dict) -> Optional[dict]:
    """Generate SBAR using Claude API."""
    if not ANTHROPIC_API_KEY:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        prompt = f"""Generate a clinical SBAR handoff note for this patient. Be concise and clinically precise.

Patient context:
{_format_context(context)}

Return EXACTLY this JSON format (no markdown):
{{"S": "situation text", "B": "background text", "A": "assessment text", "R": "recommendation text"}}"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system="You are a senior clinical nurse generating SBAR handoff notes. Be concise, specific, and clinically accurate. Return only valid JSON.",
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()

        # Parse JSON
        import json
        # Handle potential markdown wrapping
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        sbar = json.loads(text)
        if all(k in sbar for k in ("S", "B", "A", "R")):
            return sbar

        logger.warning("SBAR JSON missing keys: %s", list(sbar.keys()))
        return None

    except Exception as e:
        logger.warning("SBAR LLM generation failed: %s", e)
        return None


def _explain_with_llm(rule_name: str, triggered_values: dict, case_id: str) -> Optional[str]:
    """Generate physiological explanation using Claude API."""
    if not ANTHROPIC_API_KEY:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            system="You are a clinical pharmacologist. Explain why these lab/clinical values are concerning in 2-3 sentences. Use simple medical language.",
            messages=[{"role": "user", "content": f"Alert: {rule_name}\nPatient: {case_id}\nTriggered values: {triggered_values}"}],
        )

        return response.content[0].text.strip()

    except Exception as e:
        logger.warning("Anomaly explanation LLM failed: %s", e)
        return None


# ─── Template fallbacks ───────────────────────────────────────────

def _generate_sbar_template(case_id: str, ctx: dict) -> dict:
    """Generate SBAR using templates (offline fallback)."""
    age = ctx.get("age", "unknown")
    gender = ctx.get("gender", "unknown")
    ward = ctx.get("ward", "unknown ward")
    diagnosis = ctx.get("diagnosis", "unspecified")
    falls = ctx.get("fall_count", 0)
    meds = ctx.get("medications", [])
    det = ctx.get("deterioration_notes", 0)
    labs = ctx.get("labs", {})

    s = f"Patient {case_id}, {age}y {gender}, admitted to {ward}."
    if diagnosis:
        s += f" Primary diagnosis: {diagnosis}."

    b_parts = []
    if labs:
        abnormal = [f"{k.replace('co', '').replace('_', ' ')}={v}" for k, v in labs.items() if v]
        if abnormal:
            b_parts.append(f"Latest labs: {', '.join(abnormal[:5])}")
    if meds:
        b_parts.append(f"Active medications: {', '.join(meds[:3])}")
    b = ". ".join(b_parts) if b_parts else "No significant background noted."

    a_parts = []
    if falls > 0:
        a_parts.append(f"{falls} fall event(s) recorded")
    if det > 0:
        a_parts.append(f"{det} nursing notes flagged deterioration")
    a = ". ".join(a_parts) if a_parts else "Patient condition stable based on available data."

    r = "Continue monitoring. "
    if falls > 0:
        r += "Implement fall prevention protocol. "
    if det > 0:
        r += "Review deterioration trends and consider escalation. "

    return {"S": s, "B": b, "A": a, "R": r.strip()}


def _explain_template(rule_name: str, triggered_values: dict) -> str:
    """Template-based anomaly explanation."""
    explanations = {
        "AKI_PROBABLE": "Elevated creatinine with low eGFR and hyperkalemia suggests acute kidney injury. The kidneys are unable to adequately filter waste, leading to dangerous electrolyte imbalances.",
        "SEPSIS_POSSIBLE": "Markedly elevated CRP with raised lactate and leukocytosis indicates a systemic inflammatory response consistent with sepsis. Immediate clinical assessment is warranted.",
        "HIGH_FALL_RISK": "A documented fall event followed by prolonged immobility suggests significant injury risk. Post-fall immobility may indicate pain, fear of movement, or neurological compromise.",
        "DANGEROUS_MED_AKI": "This patient has severely reduced renal function (low eGFR) while receiving a nephrotoxic medication. Drug accumulation may worsen kidney damage and cause toxicity.",
        "MULTI_SOURCE_DETERIORATION": "Deterioration signals detected across multiple data sources (nursing assessments and device monitoring). Multi-source concordance increases the likelihood of genuine clinical decline.",
        "ANTICOAG_INR_ABNORMAL": "INR outside the therapeutic range in a patient on anticoagulant therapy indicates either under-anticoagulation (thrombosis risk) or over-anticoagulation (bleeding risk).",
    }
    return explanations.get(rule_name, f"Clinical alert {rule_name} triggered with values: {triggered_values}")


def _format_context(ctx: dict) -> str:
    """Format patient context for LLM prompt."""
    lines = [
        f"- Case ID: {ctx.get('case_id')}",
        f"- Age: {ctx.get('age', 'N/A')}, Gender: {ctx.get('gender', 'N/A')}",
        f"- Ward: {ctx.get('ward', 'N/A')}",
        f"- Diagnosis: {ctx.get('diagnosis', 'N/A')} ({ctx.get('icd10', '')})",
        f"- Length of stay: {ctx.get('los_days', 'N/A')} days",
    ]
    if ctx.get("labs"):
        labs_str = ", ".join(f"{k}={v}" for k, v in list(ctx["labs"].items())[:8])
        lines.append(f"- Latest labs: {labs_str}")
    if ctx.get("medications"):
        lines.append(f"- Medications: {', '.join(ctx['medications'][:5])}")
    if ctx.get("fall_count"):
        lines.append(f"- Fall events: {ctx['fall_count']}")
    if ctx.get("deterioration_notes"):
        lines.append(f"- Nursing deterioration notes: {ctx['deterioration_notes']}")
    return "\n".join(lines)
