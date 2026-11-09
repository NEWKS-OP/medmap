"""
Aggregates for the MediFlow dashboard.

The other routers expose one resource each. The dashboard needs a few
pre-computed views (KPIs, hourly sensor profile, admissions per day, a
patient monitor table) that would otherwise take dozens of requests, so they
are computed here in a handful of SQL queries and cached until the pipeline
runs again.
"""

import logging
import threading
from typing import Any, Optional

from fastapi import APIRouter, Query

from api.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(responses={200: {"description": "Dashboard aggregates"}})

CLINICAL_RULES = {
    "MULTI_SOURCE_DETERIORATION",
    "DANGEROUS_MED_AKI",
    "HIGH_FALL_RISK",
    "AKI_PROBABLE",
    "SEPSIS_POSSIBLE",
    "ANTICOAG_INR_ABNORMAL",
}

RULE_LABELS = {
    "MULTI_SOURCE_DETERIORATION": "Multi-source deterioration",
    "DANGEROUS_MED_AKI": "Nephrotoxic drug + kidney injury",
    "HIGH_FALL_RISK": "High fall risk",
    "AKI_PROBABLE": "Probable acute kidney injury",
    "SEPSIS_POSSIBLE": "Possible sepsis",
    "ANTICOAG_INR_ABNORMAL": "Anticoagulant with abnormal INR",
}

_cache: dict[str, Any] = {}
_cache_lock = threading.Lock()


def invalidate_dashboard_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _cached(key: str, fn):
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    value = fn()
    with _cache_lock:
        _cache[key] = value
    return value


def _source_group(source_file: Optional[str]) -> str:
    s = source_file or ""
    if s.startswith("clinic_"):
        return f"Clinic {s.split('_')[1]}"
    if s == "cross_source":
        return "Cross-source"
    return "Central export"


def _clinical_alerts() -> list[dict]:
    from api.routers.alerts import _get_alerts

    return [a for a in _get_alerts(get_db()) if a["rule_name"] in CLINICAL_RULES]


# ──────────────────────────────────────────────
# Overview
# ──────────────────────────────────────────────


def _build_overview(quality_scores: list[dict]) -> dict:
    db = get_db()

    cases = db.execute("SELECT COUNT(*) FROM tbCaseData").fetchone()[0]
    auto_corrected = db.execute(
        "SELECT COUNT(*) FROM tbAuditLog WHERE action_taken = 'AUTO_CORRECT'"
    ).fetchone()[0]
    pending = db.execute(
        "SELECT COUNT(*) FROM tbDataPassport WHERE status = 'PENDING_REVIEW'"
    ).fetchone()[0]

    # Share of imported rows that needed no quarantine
    imported = sum(
        db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in (
            "tbImportLabsData",
            "tbImportIcd10Data",
            "tbImportDeviceMotionData",
            "tbImportMedicationInpatientData",
            "tbImportNursingDailyReportsData",
            "tbImportAcData",
        )
    )
    quarantined = db.execute(
        "SELECT COUNT(*) FROM tbAuditLog WHERE action_taken = 'QUARANTINE'"
    ).fetchone()[0]
    sources = db.execute(
        "SELECT COUNT(DISTINCT source_file) FROM tbAuditLog WHERE source_file != 'cross_source'"
    ).fetchone()[0]

    alerts = _clinical_alerts()
    alert_cases = {a["case_id"] for a in alerts}

    # Average movement and falls by hour of day (hourly motion sensor)
    movement_by_hour = [
        {
            "time": f"{r['h']}:00",
            "avg_movement": round(r["avg_m"] or 0, 1),
            "falls": r["falls"] or 0,
            "bed_exits": r["exits"] or 0,
        }
        for r in db.execute(
            """SELECT substr(coTimestamp, 12, 2) AS h,
                      AVG(CAST(coMovement_index_0_100 AS REAL)) AS avg_m,
                      SUM(CAST(coFall_event_0_1 AS REAL)) AS falls,
                      SUM(CAST(coBed_exit_detected_0_1 AS REAL)) AS exits
               FROM tbImportDeviceMotionData
               WHERE length(coTimestamp) >= 13
               GROUP BY h ORDER BY h"""
        ).fetchall()
        if r["h"] and r["h"].isdigit()
    ]

    # Admissions / discharges per day, last 14 days with data
    adm = dict(
        db.execute(
            """SELECT substr(coAdmission_date, 1, 10), COUNT(DISTINCT coCaseId)
               FROM tbImportIcd10Data WHERE coAdmission_date IS NOT NULL GROUP BY 1"""
        ).fetchall()
    )
    dis = dict(
        db.execute(
            """SELECT substr(coDischarge_date, 1, 10), COUNT(DISTINCT coCaseId)
               FROM tbImportIcd10Data WHERE coDischarge_date IS NOT NULL GROUP BY 1"""
        ).fetchall()
    )
    days = sorted(d for d in set(adm) | set(dis) if d and len(d) == 10)
    # Pick the densest 14-day window rather than the sparse tail of the data
    best, best_sum = days[-14:], -1
    for i in range(max(1, len(days) - 13)):
        window = days[i : i + 14]
        s = sum(adm.get(d, 0) for d in window)
        if s > best_sum:
            best, best_sum = window, s
    admissions_by_day = [
        {"date": d[5:], "admissions": adm.get(d, 0), "discharges": dis.get(d, 0)} for d in best
    ]

    # Issues by source group and severity
    sev_rows = db.execute(
        "SELECT source_file, severity, COUNT(*) AS n FROM tbAuditLog GROUP BY source_file, severity"
    ).fetchall()
    groups: dict[str, dict] = {}
    for r in sev_rows:
        g = groups.setdefault(
            _source_group(r["source_file"]),
            {"group": _source_group(r["source_file"]), "critical": 0, "high": 0, "medium": 0, "low": 0},
        )
        key = (r["severity"] or "LOW").lower()
        if key in g:
            g[key] += r["n"]
    order = ["Central export", "Clinic 1", "Clinic 2", "Clinic 3", "Clinic 4", "Cross-source"]
    issues_by_group = sorted(groups.values(), key=lambda g: order.index(g["group"]) if g["group"] in order else 99)

    # Ward data quality (share of fields without problems, per ward)
    ward_rows = db.execute(
        """SELECT i.coWard AS ward, COUNT(DISTINCT i.coCaseId) AS patients
           FROM tbImportIcd10Data i WHERE i.coWard IS NOT NULL AND i.coWard != ''
           GROUP BY i.coWard ORDER BY patients DESC"""
    ).fetchall()
    wards = [{"ward": r["ward"], "patients": r["patients"]} for r in ward_rows]

    return {
        "kpis": {
            "cases": cases,
            "clinical_alerts": len(alerts),
            "patients_with_alerts": len(alert_cases),
            # Source quality scores (0-100) weighted by rows imported from each source
            "data_quality_pct": round(
                sum(q["score"] * q["rows_imported"] for q in quality_scores)
                / max(1, sum(q["rows_imported"] for q in quality_scores)),
                1,
            ),
            "auto_corrected": auto_corrected,
            "pending_review": pending,
            "sources": sources,
            "rows_imported": imported,
            "rows_quarantined": quarantined,
        },
        "movement_by_hour": movement_by_hour,
        "admissions_by_day": admissions_by_day,
        "issues_by_group": issues_by_group,
        "wards": wards,
    }


@router.get("/overview")
async def dashboard_overview() -> dict:
    """KPIs, hourly sensor profile, admissions per day, issues by source group, wards."""
    try:
        from api.routers.overview import get_quality_scores

        with _cache_lock:
            if "overview" in _cache:
                return _cache["overview"]
        scores = [q for q in await get_quality_scores() if q.get("source_file") != "cross_source"]
        return _cached("overview", lambda: _build_overview(scores))
    except Exception as e:
        logger.error("dashboard overview error: %s", e, exc_info=True)
        return {"kpis": {}, "movement_by_hour": [], "admissions_by_day": [], "issues_by_group": [], "wards": []}


@router.get("/alerts")
async def dashboard_alerts(limit: int = Query(20, ge=1, le=500)) -> list[dict]:
    """Clinical (non data-quality) alerts, most severe first, joined with case info."""
    db = get_db()
    out = []
    for a in _clinical_alerts()[:limit]:
        row = db.execute(
            "SELECT coCaseIdAlpha, coAgeYears, coGender FROM tbCaseData WHERE CAST(coId AS TEXT) = ? OR coCaseIdAlpha = ? LIMIT 1",
            (a["case_id"], a["case_id"]),
        ).fetchone()
        out.append({
            **a,
            "case_label": (row["coCaseIdAlpha"] if row and row["coCaseIdAlpha"] else f"Case {a['case_id']}"),
            "rule_label": RULE_LABELS.get(a["rule_name"], a["rule_name"]),
            "age": row["coAgeYears"] if row else None,
            "gender": row["coGender"] if row else None,
        })
    return out


# ──────────────────────────────────────────────
# Patient monitor
# ──────────────────────────────────────────────

_LAB_COLS = {
    "creatinine": ("coCreatinine_mg_dL", "coCreatinine_flag"),
    "crp": ("coCrp_mg_L", "coCrp_flag"),
    "hemoglobin": ("coHemoglobin_g_dL", "coHb_flag"),
    "potassium": ("coPotassium_mmol_L", "coPotassium_flag"),
    "sodium": ("coSodium_mmol_L", "coSodium_flag"),
}


def _build_monitor() -> list[dict]:
    db = get_db()
    sev_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

    alerts_by_case: dict[str, list[dict]] = {}
    for a in _clinical_alerts():
        alerts_by_case.setdefault(str(a["case_id"]), []).append(a)

    # First lab panel per case (same row the /patients/{id}/labs endpoint shows)
    lab_select = ", ".join(f"l.{v}, l.{f}" for v, f in _LAB_COLS.values())
    labs = {
        r["coCaseId"]: r
        for r in db.execute(
            f"""SELECT l.coCaseId, {lab_select}
                FROM tbImportLabsData l
                JOIN (SELECT coCaseId, MIN(coId) AS mid FROM tbImportLabsData GROUP BY coCaseId) m
                  ON m.mid = l.coId"""
        ).fetchall()
    }
    falls = {
        r[0]: (r[1] or 0, r[2] or 0)
        for r in db.execute(
            """SELECT coCaseId, SUM(CAST(coFall_event_0_1 AS REAL)), COUNT(*)
               FROM tbImportDeviceMotionData GROUP BY coCaseId"""
        ).fetchall()
    }
    nursing = {
        r[0]: (r[1] or 0, r[2] or 0)
        for r in db.execute(
            """SELECT coCaseId,
                      SUM(CASE WHEN coDeterioration_flag IN (1, '1', 'True', 'true') THEN 1 ELSE 0 END),
                      COUNT(*)
               FROM tbImportNursingDailyReportsData GROUP BY coCaseId"""
        ).fetchall()
    }
    meds = dict(
        db.execute("SELECT coCaseId, COUNT(*) FROM tbImportMedicationInpatientData GROUP BY coCaseId").fetchall()
    )
    issues = dict(
        db.execute(
            "SELECT case_id, COUNT(*) FROM tbDataPassport WHERE status != 'CLEAN' GROUP BY case_id"
        ).fetchall()
    )

    rows = db.execute(
        """SELECT c.coId, c.coCaseIdAlpha, c.coPatientId, c.coGender, c.coAgeYears, c.coIcd,
                  i.coWard, i.coAdmission_date, i.coDischarge_date,
                  i.coPrimary_icd10_code, i.coPrimary_icd10_description_en
           FROM tbCaseData c
           LEFT JOIN (SELECT coCaseId, coWard, coAdmission_date, coDischarge_date,
                             coPrimary_icd10_code, coPrimary_icd10_description_en
                      FROM tbImportIcd10Data GROUP BY coCaseId) i ON i.coCaseId = c.coId"""
    ).fetchall()

    out = []
    for r in rows:
        cid = r["coId"]
        sources = sum(1 for d in (labs, falls, nursing, meds) if cid in d)
        if sources == 0 and not r["coPrimary_icd10_code"]:
            continue  # ID-only fragments with no clinical data
        case_alerts = alerts_by_case.get(str(cid), [])
        top = max((sev_rank.get(a["severity"], 0) for a in case_alerts), default=0)
        level = {4: "critical", 3: "high", 2: "medium", 1: "low"}.get(top, "none")
        lab = labs.get(cid)
        lab_values = {}
        if lab is not None:
            for name, (vcol, fcol) in _LAB_COLS.items():
                lab_values[name] = {"value": lab[vcol], "flag": lab[fcol]}
        case_label = r["coCaseIdAlpha"] or str(cid)
        n_issues = issues.get(case_label, 0) or issues.get(str(cid), 0)
        fall_count, motion_rows = falls.get(cid, (0, 0))
        det, notes = nursing.get(cid, (0, 0))
        status = (
            "critical" if level == "critical"
            else "monitoring" if level in ("high", "medium") or det > 0
            else "discharged" if r["coDischarge_date"]
            else "stable"
        )
        out.append({
            "id": str(cid),
            "case_id": case_label,
            "patient_id": str(r["coPatientId"]) if r["coPatientId"] else None,
            "age": r["coAgeYears"],
            "gender": r["coGender"],
            "ward": r["coWard"],
            "admission_date": r["coAdmission_date"],
            "discharge_date": r["coDischarge_date"],
            "diagnosis_code": r["coPrimary_icd10_code"] or r["coIcd"],
            "diagnosis": r["coPrimary_icd10_description_en"],
            "labs": lab_values,
            "falls": int(fall_count),
            "motion_records": motion_rows,
            "deterioration_notes": int(det),
            "nursing_notes": notes,
            "medication_events": meds.get(cid, 0),
            "sources": sources,
            "anomaly_level": level,
            "anomaly_flags": [RULE_LABELS.get(a["rule_name"], a["rule_name"]) for a in case_alerts],
            "issues": n_issues,
            "data_quality": "complete" if n_issues == 0 else "inconsistent" if n_issues > 5 else "missing",
            "status": status,
        })

    level_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
    out.sort(key=lambda p: (-level_rank[p["anomaly_level"]], -p["sources"], p["case_id"]))
    return out


@router.get("/patients")
async def dashboard_patients(
    q: str = Query(None, description="Search case, patient ID, ward or diagnosis"),
    level: str = Query(None, description="Filter by anomaly level"),
    limit: int = Query(100, ge=1, le=2000),
) -> dict:
    """Patient monitor table: latest labs, falls, nursing deterioration, alerts, data issues."""
    try:
        rows = _cached("monitor", _build_monitor)
    except Exception as e:
        logger.error("dashboard patients error: %s", e, exc_info=True)
        return {"total": 0, "counts": {}, "patients": []}

    counts = {k: 0 for k in ("critical", "high", "medium", "low", "none")}
    for p in rows:
        counts[p["anomaly_level"]] += 1
    counts["stable"] = sum(1 for p in rows if p["status"] == "stable")

    filtered = rows
    if level and level != "all":
        filtered = [p for p in filtered if p["anomaly_level"] == level]
    if q:
        ql = q.lower()
        filtered = [
            p for p in filtered
            if ql in (p["case_id"] or "").lower()
            or ql in (p["patient_id"] or "").lower()
            or ql in (p["ward"] or "").lower()
            or ql in (p["diagnosis"] or "").lower()
            or ql in (p["diagnosis_code"] or "").lower()
        ]
    return {"total": len(rows), "matched": len(filtered), "counts": counts, "patients": filtered[:limit]}
