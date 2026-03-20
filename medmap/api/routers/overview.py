"""
Overview router — quality scores, ward scores, report generation, summary.
GET  /api/overview/quality-scores
GET  /api/overview/ward-scores
GET  /api/overview/summary
POST /api/overview/generate-report
"""

import logging
from typing import Any
from fastapi import APIRouter

from api.dependencies import get_db, rows_to_dicts

logger = logging.getLogger(__name__)

router = APIRouter(responses={200: {"description": "Overview data"}})


@router.get("/quality-scores")
async def get_quality_scores() -> list[dict]:
    """Get quality scores per source file, computed from audit log.

    Returns a list of SourceQualityScore objects."""
    db = get_db()
    try:
        # Single aggregation query instead of N+1
        agg_rows = db.execute(
            """SELECT source_file,
                      COUNT(*) as total_errors,
                      SUM(CASE WHEN action_taken = 'QUARANTINE' THEN 1 ELSE 0 END) as quarantined,
                      SUM(CASE WHEN action_taken = 'AUTO_CORRECT' THEN 1 ELSE 0 END) as auto_corrected
               FROM tbAuditLog
               WHERE source_file IS NOT NULL
               GROUP BY source_file"""
        ).fetchall()

        # Error categories per source
        cat_rows = db.execute(
            """SELECT source_file, error_type, COUNT(*) as cnt
               FROM tbAuditLog
               WHERE source_file IS NOT NULL
               GROUP BY source_file, error_type"""
        ).fetchall()
        cats_by_source: dict[str, dict] = {}
        for c in cat_rows:
            src = c["source_file"]
            if src not in cats_by_source:
                cats_by_source[src] = {}
            cats_by_source[src][c["error_type"]] = c["cnt"]

        scores = []
        for row in agg_rows:
            src = row["source_file"]
            total_errors = row["total_errors"]
            quarantined = row["quarantined"]
            auto_corrected = row["auto_corrected"]

            if total_errors == 0:
                score = 100
            else:
                quarantine_ratio = quarantined / total_errors
                score = max(0, int(100 * (1 - quarantine_ratio)))

            scores.append({
                "source_file": src,
                "score": score,
                "rows_imported": total_errors,
                "rows_quarantined": quarantined,
                "values_auto_corrected": auto_corrected,
                "errors_by_category": cats_by_source.get(src, {}),
            })

        logger.info("Computed quality scores for %d sources", len(scores))
        return scores
    except Exception as e:
        logger.error("quality-scores error: %s", e)
        return []


@router.get("/summary")
async def get_summary() -> dict:
    """Get global dashboard summary in a single call.

    Returns patient count, table row counts, alert counts, and top-level stats
    so the frontend Overview page can render with one request."""
    db = get_db()
    try:
        tables = [
            "tbCaseData", "tbImportLabsData", "tbImportIcd10Data",
            "tbImportDeviceMotionData", "tbImportMedicationInpatientData",
            "tbImportNursingDailyReportsData", "tbImportAcData",
        ]
        table_counts = {}
        for t in tables:
            try:
                table_counts[t] = db.execute(f"SELECT COUNT(*) as cnt FROM {t}").fetchone()["cnt"]
            except Exception:
                table_counts[t] = 0

        audit_total = db.execute("SELECT COUNT(*) as cnt FROM tbAuditLog").fetchone()["cnt"]
        audit_critical = db.execute(
            "SELECT COUNT(*) as cnt FROM tbAuditLog WHERE severity = 'CRITICAL'"
        ).fetchone()["cnt"]
        quarantined = db.execute(
            "SELECT COUNT(*) as cnt FROM tbAuditLog WHERE action_taken = 'QUARANTINE'"
        ).fetchone()["cnt"]
        auto_corrected = db.execute(
            "SELECT COUNT(*) as cnt FROM tbAuditLog WHERE action_taken = 'AUTO_CORRECT'"
        ).fetchone()["cnt"]

        passports_total = 0
        passports_pending = 0
        try:
            passports_total = db.execute("SELECT COUNT(*) as cnt FROM tbDataPassport").fetchone()["cnt"]
            passports_pending = db.execute(
                "SELECT COUNT(*) as cnt FROM tbDataPassport WHERE status = 'PENDING_REVIEW'"
            ).fetchone()["cnt"]
        except Exception:
            pass

        return {
            "total_patients": table_counts.get("tbCaseData", 0),
            "table_counts": table_counts,
            "audit_log": {
                "total": audit_total,
                "critical": audit_critical,
                "quarantined": quarantined,
                "auto_corrected": auto_corrected,
            },
            "data_passports": {
                "total": passports_total,
                "pending_review": passports_pending,
            },
        }
    except Exception as e:
        logger.error("summary error: %s", e)
        return {"total_patients": 0, "table_counts": {}, "audit_log": {}, "data_passports": {}}


@router.get("/ward-scores")
async def get_ward_scores() -> list[dict]:
    """Get ward quality scores sorted by score descending."""
    db = get_db()
    try:
        wards = db.execute(
            "SELECT DISTINCT coWard FROM tbImportIcd10Data WHERE coWard IS NOT NULL AND coWard != ''"
        ).fetchall()

        results = []
        for i, row in enumerate(wards):
            ward = row["coWard"]

            nb_patients = db.execute(
                "SELECT COUNT(DISTINCT coCaseId) as cnt FROM tbImportIcd10Data WHERE coWard = ?",
                (ward,),
            ).fetchone()["cnt"]

            # Match via coCaseIdAlpha since audit log stores text case_id
            case_alphas = db.execute(
                """SELECT DISTINCT cd.coCaseIdAlpha
                   FROM tbImportIcd10Data icd
                   JOIN tbCaseData cd ON cd.coId = icd.coCaseId
                   WHERE icd.coWard = ? AND cd.coCaseIdAlpha IS NOT NULL""",
                (ward,),
            ).fetchall()
            case_id_list = [c["coCaseIdAlpha"] for c in case_alphas]

            nb_errors = 0
            if case_id_list:
                placeholders = ",".join("?" for _ in case_id_list)
                nb_errors = db.execute(
                    f"SELECT COUNT(*) as cnt FROM tbAuditLog WHERE case_id IN ({placeholders})",
                    case_id_list,
                ).fetchone()["cnt"]

            # Ward score: based on errors per patient ratio
            score = max(0, 100 - min(100, int(nb_errors / max(1, nb_patients) * 0.5)))

            results.append({
                "ward_name": ward,
                "score": score,
                "nb_patients": nb_patients,
                "nb_errors": nb_errors,
                "rank": i + 1,
                "axes": {
                    "completude": min(100, max(50, score + 5)),
                    "dates": min(100, max(40, score - 5)),
                    "valeurs_cliniques": min(100, max(45, score)),
                    "ids": min(100, max(60, score + 10)),
                    "encodage": min(100, max(70, score + 15)),
                },
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        for i, r in enumerate(results):
            r["rank"] = i + 1

        logger.info("Computed ward scores for %d wards", len(results))
        return results
    except Exception as e:
        logger.error("ward-scores error: %s", e)
        return []


def _nlp_report_section(db: object) -> str:
    """Generate NLP section for the quality report."""
    try:
        cols = {row[1] for row in db.execute("PRAGMA table_info(tbImportNursingDailyReportsData)").fetchall()}
        if "coPain_level_extracted" not in cols:
            return "- NLP enrichment not yet applied."

        total = db.execute("SELECT COUNT(*) as cnt FROM tbImportNursingDailyReportsData").fetchone()["cnt"]
        pain = db.execute("SELECT COUNT(*) as cnt FROM tbImportNursingDailyReportsData WHERE coPain_level_extracted IS NOT NULL").fetchone()["cnt"]
        det = db.execute("SELECT COUNT(*) as cnt FROM tbImportNursingDailyReportsData WHERE coDeterioration_flag = 1").fetchone()["cnt"]
        wound = db.execute("SELECT COUNT(*) as cnt FROM tbImportNursingDailyReportsData WHERE coWound_grade_extracted IS NOT NULL").fetchone()["cnt"]

        return (
            f"- **Total nursing notes:** {total:,}\n"
            f"- **Pain mentions extracted:** {pain:,}\n"
            f"- **Deterioration flagged:** {det:,}\n"
            f"- **Wound assessments:** {wound:,}"
        )
    except Exception:
        return "- NLP stats unavailable."


@router.post("/generate-report")
async def generate_report_endpoint() -> dict:
    """Generate a comprehensive quality report using AI (with template fallback)."""
    db = get_db()
    try:
        from pipeline.agents.doc_generator import generate_report
        report = generate_report(db)
        logger.info("Generated quality report")
        return {"report": report}
    except Exception as e:
        logger.error("generate-report error: %s", e)
        return {"report": f"Error generating report: {e}"}


@router.post("/executive-summary")
async def executive_summary_endpoint() -> dict:
    """Generate a short executive summary of pipeline results."""
    db = get_db()
    try:
        from pipeline.agents.doc_generator import generate_executive_summary
        summary = generate_executive_summary(db)
        return {"summary": summary}
    except Exception as e:
        logger.error("executive-summary error: %s", e)
        return {"summary": f"Error: {e}"}
