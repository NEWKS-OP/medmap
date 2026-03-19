"""
Agents router — agent stats, column mappings, decisions.
GET  /api/agents/stats
GET  /api/agents/mappings
GET  /api/agents/decisions
"""

import logging
from fastapi import APIRouter, Query

from api.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(responses={200: {"description": "Agent data"}})


def _compute_agent_stats(db) -> dict:
    """Compute agent statistics from the database."""
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

        return {
            "total_columns": total_cols,
            "auto_mapped": auto_corrected,
            "conflicts": quarantined,
            "escalated": flagged,
            "agent_progress": {
                "Schema Detective": {"processed": total_cols, "total": total_cols},
                "Validation Agent": {"processed": total_cols, "total": total_cols},
                "Clinical Reasoner": {"processed": auto_corrected, "total": total_cols},
                "Nursing Analyst": {"processed": flagged, "total": total_cols},
                "Data Repair": {"processed": quarantined, "total": quarantined or 1},
                "Supervisor": {"processed": total_cols, "total": total_cols},
            },
        }
    except Exception as e:
        logger.error("compute agent stats error: %s", e)
        return {"total_columns": 0, "auto_mapped": 0, "conflicts": 0, "escalated": 0, "agent_progress": {}}


def _get_column_mappings(db, badge=None, source=None, status=None, limit=100) -> list[dict]:
    """Get column mappings from audit log."""
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
    """Get agent statistics."""
    db = get_db()
    return _compute_agent_stats(db)


@router.get("/mappings")
async def get_mappings(
    badge: str = Query(None, description="Filter by confidence badge"),
    source: str = Query(None, description="Filter by source file"),
    status: str = Query(None, description="Filter by mapping status"),
):
    """Get column mappings with optional filters."""
    db = get_db()
    return _get_column_mappings(db, badge=badge, source=source, status=status)


@router.get("/decisions")
async def get_decisions(limit: int = Query(20)):
    """Get recent agent decisions."""
    db = get_db()
    return _get_column_mappings(db, limit=limit)
