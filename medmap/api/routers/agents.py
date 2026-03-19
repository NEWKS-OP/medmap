"""
Agents router — agent stats, column mappings, decisions.
GET  /api/agents/stats
GET  /api/agents/mappings
GET  /api/agents/decisions
"""

import logging
from fastapi import APIRouter, Query

from api.dependencies import get_db
from pipeline.nlp import analyze_note

logger = logging.getLogger(__name__)

router = APIRouter(responses={200: {"description": "Agent data"}})


def _compute_agent_stats(db: object) -> dict:
    """Compute agent statistics from the audit log.

    Counts auto-corrected, flagged, and quarantined columns.
    """
    try:
        total_cols = db.execute(
            "SELECT COUNT(DISTINCT column_name) as cnt FROM tbAuditLog WHERE column_name IS NOT NULL"
        ).fetchone()["cnt"]

        auto_corrected = db.execute(
            "SELECT COUNT(DISTINCT column_name) as cnt FROM tbAuditLog WHERE action_taken = 'AUTO_CORRECT'"
        ).fetchone()["cnt"]

        flagged = db.execute(
            "SELECT COUNT(DISTINCT column_name) as cnt FROM tbAuditLog WHERE action_taken = 'FLAGGED'"
        ).fetchone()["cnt"]

        quarantined = db.execute(
            "SELECT COUNT(DISTINCT column_name) as cnt FROM tbAuditLog WHERE action_taken = 'QUARANTINE'"
        ).fetchone()["cnt"]

        # Count nursing notes for NLP stats
        try:
            nursing_total = db.execute(
                "SELECT COUNT(*) as cnt FROM tbImportNursingDailyReportsData"
            ).fetchone()["cnt"]
        except Exception:
            nursing_total = 0

        return {
            "total_columns": total_cols,
            "auto_mapped": auto_corrected,
            "conflicts": quarantined,
            "escalated": flagged,
            "agent_progress": {
                "Schema Detective": {"processed": total_cols, "total": total_cols},
                "Validation Agent": {"processed": total_cols, "total": total_cols},
                "Clinical Reasoner": {"processed": auto_corrected, "total": total_cols},
                "Nursing Analyst": {"processed": nursing_total, "total": nursing_total},
                "Data Repair": {"processed": quarantined, "total": quarantined or 1},
                "Supervisor": {"processed": total_cols, "total": total_cols},
            },
        }
    except Exception as e:
        logger.error("compute agent stats error: %s", e)
        return {"total_columns": 0, "auto_mapped": 0, "conflicts": 0, "escalated": 0, "agent_progress": {}}


def _get_column_mappings(db: object, badge: str = None, source: str = None, status: str = None, limit: int = 100) -> list[dict]:
    """Get column mappings derived from audit log entries.

    Maps action_taken to confidence/badge/status values.
    """
    try:
        conditions = ["action_taken IN ('AUTO_CORRECT', 'QUARANTINE', 'FLAGGED')"]
        params = []

        if source:
            conditions.append("source_file LIKE ?")
            params.append(f"%{source}%")

        where = "WHERE " + " AND ".join(conditions)

        rows = db.execute(
            f"""SELECT DISTINCT source_file, column_name, error_type, action_taken,
                       COUNT(*) as occurrences
                FROM tbAuditLog {where}
                GROUP BY source_file, column_name, action_taken
                ORDER BY occurrences DESC
                LIMIT ?""",
            params + [limit],
        ).fetchall()

        mappings = []
        for r in rows:
            action = r["action_taken"]
            if action == "AUTO_CORRECT":
                confidence, bdg, st = 0.95, "AUTO", "CONSENSUS"
            elif action == "QUARANTINE":
                confidence, bdg, st = 0.4, "REVIEW", "CONFLICT"
            else:
                confidence, bdg, st = 0.75, "CHECK", "UNCERTAIN"

            if badge and bdg not in badge.upper().split(","):
                continue
            if status and st not in status.upper().split(","):
                continue

            mappings.append({
                "source_file": r["source_file"],
                "source_column": r["column_name"],
                "target_column": f"co{(r['column_name'] or '').title().replace('_', '')}",
                "confidence": confidence,
                "badge": bdg,
                "status": st,
                "detective_result": None,
                "validation_result": None,
                "supervisor_decision": action,
                "alternative_target": None,
            })

        return mappings
    except Exception as e:
        logger.error("get_column_mappings error: %s", e)
        return []


@router.get("/stats")
async def get_agent_stats() -> dict:
    """Get agent statistics including column counts and progress."""
    db = get_db()
    return _compute_agent_stats(db)


@router.get("/mappings")
async def get_mappings(
    badge: str = Query(None, description="Filter by confidence badge"),
    source: str = Query(None, description="Filter by source file"),
    status: str = Query(None, description="Filter by mapping status"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
):
    """Get column mappings with optional badge, source, and status filters."""
    db = get_db()
    return _get_column_mappings(db, badge=badge, source=source, status=status, limit=limit)


@router.get("/decisions")
async def get_decisions(limit: int = Query(20, ge=1, le=200, description="Max decisions to return")):
    """Get recent agent decisions, ordered by occurrence count."""
    db = get_db()
    return _get_column_mappings(db, limit=limit)


@router.get("/nlp-stats")
async def get_nlp_stats() -> dict:
    """Get NLP analysis statistics across all nursing notes in the DB."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT coNursing_note_free_text FROM tbImportNursingDailyReportsData WHERE coNursing_note_free_text IS NOT NULL"
        ).fetchall()

        total = len(rows)
        pain_count = 0
        mobility_counts: dict[str, int] = {}
        wound_count = 0
        det_count = 0
        sign_counts: dict[str, int] = {}

        for r in rows:
            note = r["coNursing_note_free_text"] or ""
            if not note:
                continue
            nlp = analyze_note(note)
            if nlp["pain_level"] is not None:
                pain_count += 1
            if nlp["mobility_status"]:
                mob = nlp["mobility_status"]
                mobility_counts[mob] = mobility_counts.get(mob, 0) + 1
            if nlp["wound_grade"]:
                wound_count += 1
            if nlp["deterioration_flag"]:
                det_count += 1
                for sign in nlp["deterioration_signs"]:
                    sign_counts[sign] = sign_counts.get(sign, 0) + 1

        return {
            "total_notes": total,
            "pain_extracted": pain_count,
            "mobility_breakdown": mobility_counts,
            "wound_extracted": wound_count,
            "deterioration_flagged": det_count,
            "top_signs": dict(sorted(sign_counts.items(), key=lambda x: -x[1])[:10]),
            "extraction_rate_pct": round(
                (pain_count + sum(mobility_counts.values()) + wound_count + det_count)
                / max(total * 4, 1) * 100, 1
            ),
        }
    except Exception as e:
        logger.error("NLP stats error: %s", e)
        return {"total_notes": 0, "error": str(e)}
