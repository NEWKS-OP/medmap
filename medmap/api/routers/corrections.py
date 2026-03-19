"""
Corrections router — pending corrections, apply, rollback, history.
GET  /api/corrections/pending
POST /api/corrections/apply
POST /api/corrections/rollback
GET  /api/corrections/history
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Body

from api.dependencies import (
    get_db, rows_to_dicts,
    add_correction_history, get_correction_history_list,
)

logger = logging.getLogger(__name__)

router = APIRouter(responses={200: {"description": "Correction results"}})


@router.get("/pending")
async def get_pending_corrections() -> list[dict]:
    """Get data passports pending review."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM tbDataPassport WHERE status = 'PENDING_REVIEW' ORDER BY passport_id DESC LIMIT 200"
        ).fetchall()
        return rows_to_dicts(rows)
    except Exception as e:
        logger.error("pending corrections error: %s", e)
        return []


@router.post("/apply")
async def apply_correction(body: dict = Body(default={})) -> dict:
    """Apply a manual correction."""
    db = get_db()
    try:
        audit_log_id = body.get("audit_log_id", 0)
        case_id = body.get("case_id", "")
        column_name = body.get("column_name", "")
        new_value = body.get("new_value")
        action = body.get("action", "MANUAL_CORRECT")
        corrected_by = body.get("corrected_by", "manual")

        # Get the current value from audit log
        audit_entry = db.execute(
            "SELECT * FROM tbAuditLog WHERE coId = ?", (audit_log_id,)
        ).fetchone()

        previous_value = None
        if audit_entry:
            previous_value = audit_entry["cleaned_value"] or audit_entry["original_value"]

            db.execute(
                """UPDATE tbAuditLog
                   SET cleaned_value = ?, action_taken = ?, corrected_by = ?, correction_timestamp = ?
                   WHERE coId = ?""",
                (new_value, action, corrected_by, datetime.now().isoformat(), audit_log_id),
            )

        # Update passport status if exists
        db.execute(
            """UPDATE tbDataPassport
               SET status = 'CLEAN', cleaned_value = ?, validated_by = ?, updated_at = ?
               WHERE case_id = ? AND field_name = ? AND status != 'CLEAN'""",
            (new_value, corrected_by, datetime.now().isoformat(), case_id, column_name),
        )

        db.commit()
        logger.info("Applied correction audit_log_id=%d by=%s", audit_log_id, corrected_by)

        result = {
            "success": True,
            "audit_log_id": audit_log_id,
            "previous_value": previous_value,
            "new_value": new_value,
            "action": action,
            "error": None,
        }
        add_correction_history(result)
        return result

    except Exception as e:
        logger.error("apply correction error: %s", e)
        return {
            "success": False,
            "audit_log_id": body.get("audit_log_id", 0),
            "previous_value": None,
            "new_value": None,
            "action": body.get("action", "MANUAL_CORRECT"),
            "error": str(e),
        }


@router.post("/rollback")
async def rollback_correction(body: dict = Body(default={})) -> dict:
    """Rollback a correction to original value."""
    db = get_db()
    try:
        audit_log_id = body.get("audit_log_id", 0)

        audit_entry = db.execute(
            "SELECT * FROM tbAuditLog WHERE coId = ?", (audit_log_id,)
        ).fetchone()

        if not audit_entry:
            return {
                "success": False, "audit_log_id": audit_log_id,
                "previous_value": None, "new_value": None,
                "action": "ROLLBACK", "error": "Audit log entry not found",
            }

        previous_value = audit_entry["cleaned_value"]
        original_value = audit_entry["original_value"]

        db.execute(
            """UPDATE tbAuditLog
               SET cleaned_value = NULL, action_taken = 'ROLLBACK',
                   corrected_by = 'rollback', correction_timestamp = ?
               WHERE coId = ?""",
            (datetime.now().isoformat(), audit_log_id),
        )

        db.execute(
            """UPDATE tbDataPassport
               SET status = 'QUARANTINE', cleaned_value = NULL, updated_at = ?
               WHERE case_id = ? AND field_name = ?""",
            (datetime.now().isoformat(), audit_entry["case_id"], audit_entry["column_name"]),
        )

        db.commit()
        logger.info("Applied correction audit_log_id=%d by=%s", audit_log_id, corrected_by)

        result = {
            "success": True,
            "audit_log_id": audit_log_id,
            "previous_value": previous_value,
            "new_value": original_value,
            "action": "ROLLBACK",
            "error": None,
        }
        add_correction_history(result)
        return result

    except Exception as e:
        logger.error("rollback error: %s", e)
        return {
            "success": False,
            "audit_log_id": body.get("audit_log_id", 0),
            "previous_value": None, "new_value": None,
            "action": "ROLLBACK", "error": str(e),
        }


@router.get("/history")
async def get_history() -> list[dict]:
    """Get correction history."""
    return get_correction_history_list()
