"""
Overview router — quality scores, ward scores, report generation.
GET  /api/overview/quality-scores
GET  /api/overview/ward-scores
POST /api/overview/generate-report
"""

import logging
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
        sources = db.execute(
            "SELECT DISTINCT source_file FROM tbAuditLog WHERE source_file IS NOT NULL"
        ).fetchall()

        scores = []
        for row in sources:
            src = row["source_file"]

            total_errors = db.execute(
                "SELECT COUNT(*) as cnt FROM tbAuditLog WHERE source_file = ?", (src,)
            ).fetchone()["cnt"]

            quarantined = db.execute(
                "SELECT COUNT(*) as cnt FROM tbAuditLog WHERE source_file = ? AND action_taken = 'QUARANTINE'",
                (src,),
            ).fetchone()["cnt"]

            auto_corrected = db.execute(
                "SELECT COUNT(*) as cnt FROM tbAuditLog WHERE source_file = ? AND action_taken = 'AUTO_CORRECT'",
                (src,),
            ).fetchone()["cnt"]

            cats = db.execute(
                "SELECT error_type, COUNT(*) as cnt FROM tbAuditLog WHERE source_file = ? GROUP BY error_type",
                (src,),
            ).fetchall()
            errors_by_cat = {c["error_type"]: c["cnt"] for c in cats}

            score = max(0, 100 - min(100, int(total_errors * 0.01)))

            scores.append({
                "source_file": src,
                "score": score,
                "rows_imported": total_errors - quarantined,
                "rows_quarantined": quarantined,
                "values_auto_corrected": auto_corrected,
                "errors_by_category": errors_by_cat,
            })

        logger.info("Computed quality scores for %d sources", len(scores))
        return scores
    except Exception as e:
        logger.error("quality-scores error: %s", e)
        return []


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

            case_ids = db.execute(
                "SELECT DISTINCT coCaseId FROM tbImportIcd10Data WHERE coWard = ?",
                (ward,),
            ).fetchall()
            case_id_list = [str(c["coCaseId"]) for c in case_ids]

            nb_errors = 0
            if case_id_list:
                placeholders = ",".join("?" for _ in case_id_list)
                nb_errors = db.execute(
                    f"SELECT COUNT(*) as cnt FROM tbAuditLog WHERE case_id IN ({placeholders})",
                    case_id_list,
                ).fetchone()["cnt"]

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


@router.post("/generate-report")
async def generate_report() -> dict:
    """Generate a quality report in Markdown format."""
    db = get_db()
    try:
        total_cases = db.execute("SELECT COUNT(*) as cnt FROM tbCaseData").fetchone()["cnt"]
        total_labs = db.execute("SELECT COUNT(*) as cnt FROM tbImportLabsData").fetchone()["cnt"]
        total_audit = db.execute("SELECT COUNT(*) as cnt FROM tbAuditLog").fetchone()["cnt"]
        total_passports = db.execute("SELECT COUNT(*) as cnt FROM tbDataPassport").fetchone()["cnt"]

        critical = db.execute(
            "SELECT COUNT(*) as cnt FROM tbAuditLog WHERE severity = 'CRITICAL'"
        ).fetchone()["cnt"]

        quarantined = db.execute(
            "SELECT COUNT(*) as cnt FROM tbAuditLog WHERE action_taken = 'QUARANTINE'"
        ).fetchone()["cnt"]

        top_errors = db.execute(
            "SELECT error_type, COUNT(*) as cnt FROM tbAuditLog GROUP BY error_type ORDER BY cnt DESC LIMIT 5"
        ).fetchall()
        top_errors_str = "\n".join(
            f"  - {r['error_type']}: {r['cnt']:,}" for r in top_errors
        )

        report = f"""# MEDMAP Data Quality Report

## Summary
- **Total patients (cases):** {total_cases:,}
- **Total lab records:** {total_labs:,}
- **Total audit log entries:** {total_audit:,}
- **Data passport entries:** {total_passports:,}

## Issues Found
- **Critical issues:** {critical:,}
- **Quarantined values:** {quarantined:,}

## Top Error Categories
{top_errors_str}

## Recommendation
Review quarantined values in the Corrections page and validate critical alerts in the Alerts page.

---
*Report generated by MEDMAP pipeline.*
"""
        logger.info("Generated quality report: %d cases, %d critical", total_cases, critical)
        return {"report": report}
    except Exception as e:
        logger.error("generate-report error: %s", e)
        return {"report": f"Error generating report: {e}"}
