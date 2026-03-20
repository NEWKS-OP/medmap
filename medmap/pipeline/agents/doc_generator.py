"""Doc Generator: auto-documentation of pipeline results.

Uses Claude API to generate professional quality reports.
Falls back to template-based generation when no API key is available.
"""

import logging
import sqlite3
from typing import Optional

from config.settings import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)


def generate_report(db: sqlite3.Connection) -> str:
    """Generate a full pipeline quality report in Markdown.

    Gathers stats from the DB and formats a professional report.
    Uses LLM for narrative sections when available.
    """
    stats = _gather_stats(db)

    # Try LLM-enhanced report
    report = _generate_report_with_llm(stats)
    if report:
        return report

    # Fallback: template
    return _generate_report_template(stats)


def generate_executive_summary(db: sqlite3.Connection) -> str:
    """Generate a short executive summary (1 paragraph)."""
    stats = _gather_stats(db)

    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=256,
                system="You are a hospital data quality director. Write a 3-4 sentence executive summary of the data pipeline results. Be specific with numbers. Professional tone.",
                messages=[{"role": "user", "content": f"Pipeline statistics:\n{_format_stats(stats)}"}],
            )
            return response.content[0].text.strip()

        except Exception as e:
            logger.warning("Executive summary LLM failed: %s", e)

    # Fallback
    return (
        f"The MEDMAP pipeline processed {stats['total_patients']:,} patient cases across "
        f"{stats['total_rows']:,} total data rows. "
        f"{stats['audit_total']:,} data quality issues were detected, "
        f"of which {stats['critical_count']:,} were critical. "
        f"{stats['auto_corrected']:,} values were auto-corrected and "
        f"{stats['quarantined']:,} were quarantined for review."
    )


# ─── Stats gathering ──────────────────────────────────────────────

def _gather_stats(db: sqlite3.Connection) -> dict:
    """Gather pipeline statistics from the database."""
    stats = {}

    def _count(sql):
        try:
            return db.execute(sql).fetchone()[0] or 0
        except Exception:
            return 0

    stats["total_patients"] = _count("SELECT COUNT(*) FROM tbCaseData")
    stats["total_labs"] = _count("SELECT COUNT(*) FROM tbImportLabsData")
    stats["total_meds"] = _count("SELECT COUNT(*) FROM tbImportMedicationInpatientData")
    stats["total_nursing"] = _count("SELECT COUNT(*) FROM tbImportNursingDailyReportsData")
    stats["total_motion"] = _count("SELECT COUNT(*) FROM tbImportDeviceMotionData")
    stats["total_icd"] = _count("SELECT COUNT(*) FROM tbImportIcd10Data")
    stats["total_rows"] = sum([
        stats["total_patients"], stats["total_labs"], stats["total_meds"],
        stats["total_nursing"], stats["total_motion"], stats["total_icd"],
    ])

    # Audit stats
    stats["audit_total"] = _count("SELECT COUNT(*) FROM tbAuditLog")
    stats["critical_count"] = _count("SELECT COUNT(*) FROM tbAuditLog WHERE severity = 'CRITICAL'")
    stats["auto_corrected"] = _count("SELECT COUNT(*) FROM tbAuditLog WHERE action_taken = 'AUTO_CORRECT'")
    stats["quarantined"] = _count("SELECT COUNT(*) FROM tbAuditLog WHERE action_taken = 'QUARANTINE'")
    stats["flagged"] = _count("SELECT COUNT(*) FROM tbAuditLog WHERE action_taken = 'FLAGGED'")

    # Top error types
    try:
        rows = db.execute(
            "SELECT error_type, COUNT(*) as cnt FROM tbAuditLog GROUP BY error_type ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        stats["top_errors"] = [(r[0], r[1]) for r in rows]
    except Exception:
        stats["top_errors"] = []

    # Worst files
    try:
        rows = db.execute(
            "SELECT source_file, COUNT(*) as cnt FROM tbAuditLog WHERE source_file IS NOT NULL GROUP BY source_file ORDER BY cnt DESC LIMIT 5"
        ).fetchall()
        stats["worst_files"] = [(r[0], r[1]) for r in rows]
    except Exception:
        stats["worst_files"] = []

    # Ward stats
    try:
        rows = db.execute(
            "SELECT coWard, COUNT(DISTINCT coCaseId) as cnt FROM tbImportIcd10Data WHERE coWard IS NOT NULL GROUP BY coWard ORDER BY cnt DESC"
        ).fetchall()
        stats["wards"] = [(r[0], r[1]) for r in rows]
    except Exception:
        stats["wards"] = []

    # NLP stats
    stats["nursing_deterioration"] = _count(
        "SELECT COUNT(*) FROM tbImportNursingDailyReportsData WHERE coDeterioration_flag = 1"
    )
    stats["nursing_pain"] = _count(
        "SELECT COUNT(*) FROM tbImportNursingDailyReportsData WHERE coPain_level_extracted IS NOT NULL"
    )

    # Passport stats
    stats["passports_total"] = _count("SELECT COUNT(*) FROM tbDataPassport")
    stats["passports_pending"] = _count(
        "SELECT COUNT(*) FROM tbDataPassport WHERE status = 'PENDING_REVIEW'"
    )

    return stats


# ─── LLM-based report ────────────────────────────────────────────

def _generate_report_with_llm(stats: dict) -> Optional[str]:
    """Generate a professional report using Claude API."""
    if not ANTHROPIC_API_KEY:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system="""You are a hospital data quality director writing a professional pipeline quality report.
Use Markdown formatting. Include sections: Executive Summary, Data Volume, Quality Issues, NLP Analysis, Recommendations.
Be specific with numbers. Professional tone. Keep it concise but thorough.""",
            messages=[{"role": "user", "content": f"Generate a quality report from these pipeline statistics:\n{_format_stats(stats)}"}],
        )

        return response.content[0].text.strip()

    except Exception as e:
        logger.warning("Report LLM generation failed: %s", e)
        return None


# ─── Template fallback ────────────────────────────────────────────

def _generate_report_template(stats: dict) -> str:
    """Generate report using templates (offline fallback)."""
    top_errors_str = "\n".join(
        f"  - {etype}: {cnt:,}" for etype, cnt in stats.get("top_errors", [])[:5]
    ) or "  - No errors recorded"

    worst_files_str = "\n".join(
        f"  - `{fname}`: {cnt:,} issues" for fname, cnt in stats.get("worst_files", [])[:5]
    ) or "  - No problematic files"

    ward_str = "\n".join(
        f"  - {w}: {cnt} patients" for w, cnt in stats.get("wards", [])
    ) or "  - No ward data"

    return f"""# MEDMAP Data Quality Report

## Executive Summary
The MEDMAP pipeline processed **{stats['total_patients']:,}** patient cases with **{stats['total_rows']:,}** total data records. {stats['audit_total']:,} data quality issues were identified, with {stats['critical_count']:,} critical issues requiring attention. {stats['auto_corrected']:,} values were automatically corrected.

## Data Volume
| Table | Records |
|-------|---------|
| Patients (Cases) | {stats['total_patients']:,} |
| Lab Results | {stats['total_labs']:,} |
| Medications | {stats['total_meds']:,} |
| Nursing Notes | {stats['total_nursing']:,} |
| Motion Data | {stats['total_motion']:,} |
| ICD-10 Diagnoses | {stats['total_icd']:,} |

## Quality Issues
- **Total audit entries:** {stats['audit_total']:,}
- **Critical issues:** {stats['critical_count']:,}
- **Auto-corrected:** {stats['auto_corrected']:,}
- **Quarantined:** {stats['quarantined']:,}
- **Flagged for review:** {stats['flagged']:,}

### Top Error Categories
{top_errors_str}

### Most Problematic Files
{worst_files_str}

## NLP Analysis (Nursing Notes)
- **Deterioration flags:** {stats.get('nursing_deterioration', 0):,} notes
- **Pain mentions extracted:** {stats.get('nursing_pain', 0):,} notes

## Ward Distribution
{ward_str}

## Data Passports
- **Total lineage records:** {stats.get('passports_total', 0):,}
- **Pending review:** {stats.get('passports_pending', 0):,}

## Recommendations
1. Review all {stats['critical_count']:,} critical issues in the Alerts page
2. Validate quarantined values ({stats['quarantined']:,}) in the Corrections page
3. Investigate the most problematic source files listed above
4. Monitor patients with deterioration flags ({stats.get('nursing_deterioration', 0):,}) for clinical escalation

---
*Report generated by MEDMAP pipeline.*
"""


def _format_stats(stats: dict) -> str:
    """Format stats dict for LLM prompt."""
    lines = [
        f"Total patients: {stats['total_patients']:,}",
        f"Total data rows: {stats['total_rows']:,}",
        f"Lab records: {stats['total_labs']:,}",
        f"Medications: {stats['total_meds']:,}",
        f"Nursing notes: {stats['total_nursing']:,}",
        f"Motion records: {stats['total_motion']:,}",
        f"ICD-10 records: {stats['total_icd']:,}",
        f"Audit log entries: {stats['audit_total']:,}",
        f"Critical issues: {stats['critical_count']:,}",
        f"Auto-corrected: {stats['auto_corrected']:,}",
        f"Quarantined: {stats['quarantined']:,}",
        f"Nursing deterioration flags: {stats.get('nursing_deterioration', 0):,}",
        f"Pain mentions: {stats.get('nursing_pain', 0):,}",
    ]
    if stats.get("top_errors"):
        lines.append("Top errors: " + ", ".join(f"{e}={c}" for e, c in stats["top_errors"][:5]))
    if stats.get("wards"):
        lines.append("Wards: " + ", ".join(f"{w}={c}" for w, c in stats["wards"]))
    return "\n".join(lines)
