"""
Patients router — 8 endpoints for patient data.
GET  /api/patients
GET  /api/patients/{case_id}
GET  /api/patients/{case_id}/labs
GET  /api/patients/{case_id}/timeline
GET  /api/patients/{case_id}/medications
GET  /api/patients/{case_id}/nursing
GET  /api/patients/{case_id}/convergence
GET  /api/patients/{case_id}/passports
"""

import logging
from typing import Any, Optional
from datetime import datetime
from fastapi import APIRouter, Query

from api.dependencies import get_db, rows_to_dicts

logger = logging.getLogger(__name__)

router = APIRouter(responses={200: {"description": "Patient data"}})


def _find_case(db: object, case_id: str):
    """Find a case by coCaseIdAlpha or coId.

    Returns the first matching sqlite3.Row or None.
    """
    return db.execute(
        "SELECT * FROM tbCaseData WHERE coCaseIdAlpha = ? OR CAST(coId AS TEXT) = ? LIMIT 1",
        (case_id, case_id),
    ).fetchone()


def _build_patient_summary(db: object, case: object) -> dict:
    """Build a patient summary dict from a case row.

    Joins ICD-10 data for ward and diagnosis information.
    """
    internal_id = case["coId"]
    icd = db.execute(
        "SELECT * FROM tbImportIcd10Data WHERE coCaseId = ? LIMIT 1",
        (internal_id,),
    ).fetchone()

    return {
        "case_id": case["coCaseIdAlpha"] or str(internal_id),
        "patient_id": str(case["coPatientId"]) if case["coPatientId"] else None,
        "age": case["coAgeYears"],
        "gender": case["coGender"],
        "ward": icd["coWard"] if icd else None,
        "admission_date": icd["coAdmission_date"] if icd else None,
        "discharge_date": icd["coDischarge_date"] if icd else None,
        "primary_icd10": icd["coPrimary_icd10_code"] if icd else case["coIcd"],
        "primary_icd10_desc": icd["coPrimary_icd10_description_en"] if icd else None,
        "convergence_score": None,
    }


@router.get("")
async def list_patients(ward: str = Query(None, description="Filter by ward name"), limit: int = Query(50, ge=1, le=500, description="Max results")):
    """List patients with optional ward filter and pagination."""
    db = get_db()
    try:
        if ward:
            rows = db.execute(
                """SELECT c.coId, c.coCaseIdAlpha, c.coPatientId, c.coGender, c.coAgeYears, c.coIcd,
                          i.coWard, i.coAdmission_date, i.coDischarge_date,
                          i.coPrimary_icd10_code, i.coPrimary_icd10_description_en
                   FROM tbCaseData c
                   LEFT JOIN (SELECT coCaseId, coWard, coAdmission_date, coDischarge_date,
                              coPrimary_icd10_code, coPrimary_icd10_description_en
                              FROM tbImportIcd10Data GROUP BY coCaseId) i ON i.coCaseId = c.coId
                   WHERE i.coWard = ?
                   LIMIT ?""",
                (ward, limit),
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT c.coId, c.coCaseIdAlpha, c.coPatientId, c.coGender, c.coAgeYears, c.coIcd,
                          i.coWard, i.coAdmission_date, i.coDischarge_date,
                          i.coPrimary_icd10_code, i.coPrimary_icd10_description_en
                   FROM tbCaseData c
                   LEFT JOIN (SELECT coCaseId, coWard, coAdmission_date, coDischarge_date,
                              coPrimary_icd10_code, coPrimary_icd10_description_en
                              FROM tbImportIcd10Data GROUP BY coCaseId) i ON i.coCaseId = c.coId
                   LIMIT ?""",
                (limit,),
            ).fetchall()

        logger.info("Listing patients: %d results", len(rows))
        return [
            {
                "case_id": r["coCaseIdAlpha"] or str(r["coId"]),
                "patient_id": str(r["coPatientId"]) if r["coPatientId"] else None,
                "age": r["coAgeYears"],
                "gender": r["coGender"],
                "ward": r["coWard"],
                "admission_date": r["coAdmission_date"],
                "discharge_date": r["coDischarge_date"],
                "primary_icd10": r["coPrimary_icd10_code"] or r["coIcd"],
                "primary_icd10_desc": r["coPrimary_icd10_description_en"],
                "convergence_score": None,
            }
            for r in rows
        ]
    except Exception as e:
        logger.error("list_patients error: %s", e)
        return []


@router.get("/{case_id}")
async def get_patient(case_id: str) -> dict:
    """Get detailed patient summary including demographics and ICD data."""
    db = get_db()
    try:
        case = _find_case(db, case_id)
        if not case:
            return {"case_id": case_id, "patient_id": None, "age": None, "gender": None, "ward": None}
        return _build_patient_summary(db, case)
    except Exception as e:
        logger.error("get_patient error: %s", e)
        return {"case_id": case_id, "patient_id": None, "age": None, "gender": None, "ward": None}


# Lab parameter mappings: (display_name, value_col, flag_col, ref_low_col, ref_high_col)
LAB_PARAMS = [
    ("Sodium", "coSodium_mmol_L", "coSodium_flag", "cosodium_ref_low", "cosodium_ref_high"),
    ("Potassium", "coPotassium_mmol_L", "coPotassium_flag", "coPotassium_ref_low", "coPotassium_ref_high"),
    ("Creatinine", "coCreatinine_mg_dL", "coCreatinine_flag", "coCreatinine_ref_low", "coCreatinine_ref_high"),
    ("eGFR", "coEgfr_mL_min_1_73m2", "coEgfr_flag", "coEgfr_ref_low", "coEgfr_ref_high"),
    ("Glucose", "coGlucose_mg_dL", "coGlucose_flag", "coGlucose_ref_low", "coGlucose_ref_high"),
    ("Hemoglobin", "coHemoglobin_g_dL", "coHb_flag", "coHb_ref_low", "coHb_ref_high"),
    ("WBC", "coWbc_10e9_L", "coWbc_flag", "coWbc_ref_low", "coWbc_ref_high"),
    ("Platelets", "coPlatelets_10e9_L", "coPlatelets_flag", "coPlt_ref_low", "coPlt_ref_high"),
    ("CRP", "coCrp_mg_L", "coCrp_flag", "coCrp_ref_low", "coCrp_ref_high"),
    ("ALT", "coAlt_U_L", "coAlt_flag", "coAlt_ref_low", "coAlt_ref_high"),
    ("AST", "coAst_U_L", "coAst_flag", "coAst_ref_low", "coAst_ref_high"),
    ("Bilirubin", "coBilirubin_mg_dL", "coBilirubin_flag", "coBili_ref_low", "coBili_ref_high"),
    ("Albumin", "coAlbumin_g_dL", "coAlbumin_flag", "coAlbumin_ref_low", "coAlbumin_ref_high"),
    ("INR", "coInr", "coInr_flag", "coInr_ref_low", "coInr_ref_high"),
    ("Lactate", "coLactate_mmol_L", "coLactate_flag", "coLactate_ref_low", "coLactate_ref_high"),
]


@router.get("/{case_id}/labs")
async def get_patient_labs(case_id: str) -> list[dict]:
    """Get lab results for a patient across 15 parameters."""
    db = get_db()
    try:
        case = _find_case(db, case_id)
        if not case:
            return []

        labs = db.execute(
            "SELECT * FROM tbImportLabsData WHERE coCaseId = ?", (case["coId"],)
        ).fetchall()
        if not labs:
            return []

        lab_row = labs[0]
        return [
            {
                "parameter_name": name,
                "value": lab_row[val_col],
                "flag": lab_row[flag_col],
                "ref_low": lab_row[low_col],
                "ref_high": lab_row[high_col],
                "original_value": None,
                "was_corrected": False,
            }
            for name, val_col, flag_col, low_col, high_col in LAB_PARAMS
        ]
    except Exception as e:
        logger.error("get_patient_labs error: %s", e)
        return []


@router.get("/{case_id}/timeline")
async def get_patient_timeline(case_id: str) -> list[dict]:
    """Get merged timeline events for a patient from all sources, sorted by timestamp."""
    db = get_db()
    try:
        case = _find_case(db, case_id)
        if not case:
            return []

        cid = case["coId"]
        events: list[dict] = []

        # Labs
        for r in db.execute(
            "SELECT coSpecimen_datetime, coSodium_mmol_L, coCreatinine_mg_dL, coCrp_mg_L, coEgfr_mL_min_1_73m2 FROM tbImportLabsData WHERE coCaseId = ?",
            (cid,),
        ).fetchall():
            events.append({
                "event_type": "LAB", "timestamp": r["coSpecimen_datetime"] or "",
                "data": {"sodium": r["coSodium_mmol_L"], "creatinine": r["coCreatinine_mg_dL"], "crp": r["coCrp_mg_L"], "egfr": r["coEgfr_mL_min_1_73m2"]},
                "source_file": None, "alert_message": None,
            })

        # Device motion (limit 100)
        for r in db.execute(
            "SELECT coTimestamp, coMovement_index_0_100, coFall_event_0_1, coBed_exit_detected_0_1 FROM tbImportDeviceMotionData WHERE coCaseId = ? LIMIT 100",
            (cid,),
        ).fetchall():
            events.append({
                "event_type": "MOTION_HOURLY", "timestamp": r["coTimestamp"] or "",
                "data": {"movement_index": r["coMovement_index_0_100"], "fall_event": r["coFall_event_0_1"], "bed_exit": r["coBed_exit_detected_0_1"]},
                "source_file": None, "alert_message": None,
            })

        # Medications (limit 200)
        for r in db.execute(
            "SELECT coAdmission_datetime, coMedication_name, coDose, coRoute, administration_status, coRecord_type FROM tbImportMedicationInpatientData WHERE coCaseId = ? LIMIT 200",
            (cid,),
        ).fetchall():
            events.append({
                "event_type": "MEDICATION", "timestamp": r["coAdmission_datetime"] or "",
                "data": {"name": r["coMedication_name"], "dose": r["coDose"], "route": r["coRoute"], "status": r["administration_status"], "event_type": r["coRecord_type"]},
                "source_file": None, "alert_message": None,
            })

        # Nursing
        for r in db.execute(
            "SELECT coReport_date, coShift, coNursing_note_free_text FROM tbImportNursingDailyReportsData WHERE coCaseId = ?",
            (cid,),
        ).fetchall():
            events.append({
                "event_type": "NURSING", "timestamp": r["coReport_date"] or "",
                "data": {"shift": r["coShift"], "note": (r["coNursing_note_free_text"] or "")[:200]},
                "source_file": None, "alert_message": None,
            })

        events.sort(key=lambda e: e["timestamp"] or "")
        return events
    except Exception as e:
        logger.error("get_patient_timeline error: %s", e)
        return []


@router.get("/{case_id}/medications")
async def get_patient_medications(case_id: str) -> list[dict]:
    """Get medication events for a patient including orders, changes, and administrations."""
    db = get_db()
    try:
        case = _find_case(db, case_id)
        if not case:
            return []

        meds = db.execute(
            """SELECT coRecord_type, coMedication_code_atc, coMedication_name,
                      coRoute, coDose, coDose_unit, coFrequency,
                      coOrder_start_datetime, coOrder_stop_datetime,
                      prescriber_role, administration_status, administration_datetime
               FROM tbImportMedicationInpatientData WHERE coCaseId = ?""",
            (case["coId"],),
        ).fetchall()

        return [
            {
                "event_type": "MEDICATION",
                "timestamp": r["coOrder_start_datetime"] or r["administration_datetime"] or "",
                "data": {
                    "event_type": r["coRecord_type"],
                    "medication_code_atc": r["coMedication_code_atc"],
                    "medication_name": r["coMedication_name"],
                    "route": r["coRoute"],
                    "dose": r["coDose"],
                    "dose_unit": r["coDose_unit"],
                    "frequency": r["coFrequency"],
                    "prescriber_role": r["prescriber_role"],
                    "administration_status": r["administration_status"],
                },
                "source_file": None, "alert_message": None,
            }
            for r in meds
        ]
    except Exception as e:
        logger.error("get_patient_medications error: %s", e)
        return []


@router.get("/{case_id}/nursing")
async def get_patient_nursing(case_id: str) -> list[dict]:
    """Get nursing reports for a patient with shift and date information."""
    db = get_db()
    try:
        case = _find_case(db, case_id)
        if not case:
            return []

        rows = db.execute(
            "SELECT coReport_date, coShift, coNursing_note_free_text FROM tbImportNursingDailyReportsData WHERE coCaseId = ?",
            (case["coId"],),
        ).fetchall()

        return [
            {
                "case_id": case_id,
                "shift": r["coShift"] or "Early",
                "report_date": r["coReport_date"] or "",
                "pain_level": None,
                "mobility_status": None,
                "wound_grade": None,
                "deterioration_flag": False,
                "deterioration_signs": [],
            }
            for r in rows
        ]
    except Exception as e:
        logger.error("get_patient_nursing error: %s", e)
        return []


@router.get("/{case_id}/convergence")
async def get_patient_convergence(case_id: str) -> dict:
    """Get convergence score for a patient.

    Score is computed on-the-fly from labs (0-35), motion (0-25),
    medication (0-20), nursing (0-15), assessment (0-5)."""
    db = get_db()
    try:
        case = _find_case(db, case_id)
        if not case:
            return {"case_id": case_id, "total_score": 0, "risk_level": "LOW", "breakdown": {}, "top_contributors": [], "computed_at": ""}

        cid = case["coId"]

        # Labs score (0-35): based on flagged values
        labs_score = 0
        lab = db.execute("SELECT * FROM tbImportLabsData WHERE coCaseId = ? LIMIT 1", (cid,)).fetchone()
        if lab:
            flag_cols = ["coSodium_flag", "coPotassium_flag", "coCreatinine_flag", "coEgfr_flag",
                         "coGlucose_flag", "coHb_flag", "coWbc_flag", "coPlatelets_flag",
                         "coCrp_flag", "coAlt_flag", "coAst_flag", "coBilirubin_flag",
                         "coAlbumin_flag", "coInr_flag", "coLactate_flag"]
            flagged = sum(1 for c in flag_cols if lab[c] and lab[c] in ("H", "HH", "L", "LL"))
            labs_score = min(35, int(flagged * 2.5))

        # Motion score (0-25): based on falls
        falls = db.execute(
            "SELECT COUNT(*) as cnt FROM tbImportDeviceMotionData WHERE coCaseId = ? AND coFall_event_0_1 = '1'",
            (cid,),
        ).fetchone()["cnt"]
        motion_score = min(25, falls * 10)

        # Medication score (0-20)
        med_count = db.execute(
            "SELECT COUNT(DISTINCT coMedication_name) as cnt FROM tbImportMedicationInpatientData WHERE coCaseId = ?",
            (cid,),
        ).fetchone()["cnt"]
        medication_score = min(20, med_count)

        # Nursing score (0-15)
        nursing_count = db.execute(
            "SELECT COUNT(*) as cnt FROM tbImportNursingDailyReportsData WHERE coCaseId = ?",
            (cid,),
        ).fetchone()["cnt"]
        nursing_score = min(15, int(nursing_count * 0.5))

        # Assessment (0-5)
        assessment_score = min(5, db.execute(
            "SELECT COUNT(*) as cnt FROM tbImportAcData WHERE coCaseId = ?", (cid,)
        ).fetchone()["cnt"])

        total = labs_score + motion_score + medication_score + nursing_score + assessment_score

        # Risk thresholds: 76+=CRITICAL, 51+=HIGH, 26+=MODERATE, else LOW
        if total >= 76:
            risk = "CRITICAL"
        elif total >= 51:
            risk = "HIGH"
        elif total >= 26:
            risk = "MODERATE"
        else:
            risk = "LOW"

        contributors = []
        if labs_score > 10:
            contributors.append("Abnormal lab values")
        if motion_score > 10:
            contributors.append("Fall events detected")
        if medication_score > 10:
            contributors.append("High medication count")

        return {
            "case_id": case_id,
            "total_score": total,
            "risk_level": risk,
            "breakdown": {
                "labs": labs_score, "motion": motion_score,
                "medication": medication_score, "nursing": nursing_score,
                "assessment": assessment_score,
            },
            "top_contributors": contributors[:3],
            "computed_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("get_patient_convergence error: %s", e)
        return {"case_id": case_id, "total_score": 0, "risk_level": "LOW", "breakdown": {}, "top_contributors": [], "computed_at": ""}


@router.get("/{case_id}/passports")
async def get_patient_passports(case_id: str) -> list[dict]:
    """Get data passports (data lineage records) for a patient."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM tbDataPassport WHERE case_id = ? OR case_id LIKE ? ORDER BY passport_id DESC LIMIT 200",
            (case_id, f"%{case_id}%"),
        ).fetchall()
        return rows_to_dicts(rows)
    except Exception as e:
        logger.error("get_patient_passports error: %s", e)
        return []
