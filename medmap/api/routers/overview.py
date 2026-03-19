"""
Overview router — quality scores, ward scores, report generation.
GET  /api/overview/quality-scores
GET  /api/overview/ward-scores
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
