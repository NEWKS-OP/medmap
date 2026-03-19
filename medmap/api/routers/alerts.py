"""
Alerts router — clinical alerts from cross-dataset anomaly detection.
GET   /api/alerts
PATCH /api/alerts/{case_id}/{rule_name}
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Query, Body

from api.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory alert store (populated from audit log on first access)
_alerts_cache: list[dict] | None = None


def _build_alerts(db) -> list[dict]:
    """Build clinical alerts from cross-source audit log entries."""
    alerts = []

    # Get critical audit entries grouped by case
    critical = db.execute(
        """SELECT case_id, error_type, column_name, original_value, source_file, table_name
           FROM tbAuditLog
           WHERE severity = 'CRITICAL' AND case_id IS NOT NULL AND case_id != ''
           ORDER BY case_id"""
    ).fetchall()

    by_case: dict[str, list] = {}
    for row in critical:
        cid = row["case_id"]
        if cid not in by_case:
            by_case[cid] = []
        by_case[cid].append(dict(row))

    for cid, entries in by_case.items():
        sources = list({e["source_file"] for e in entries if e["source_file"]})
        triggered = {}
        for e in entries[:5]:
            triggered[e["column_name"] or "unknown"] = e["original_value"]

        error_types = {e["error_type"] for e in entries}

        rule = "DATA_QUALITY_CRITICAL"
        message = f"Critical data quality issues: {', '.join(error_types)}"
        severity = "CRITICAL"

        if "CLINICAL_OUTLIER" in error_types:
            rule = "CLINICAL_OUTLIER"
            message = f"Clinical outlier values detected in {len(entries)} fields"

        alerts.append({
            "case_id": cid,
            "rule_name": rule,
            "severity": severity,
            "message": message,
            "sources_involved": sources,
            "triggered_values": triggered,
            "timestamp_generated": datetime.now().isoformat(),
            "sbar": None,
            "is_treated": False,
            "treated_by": None,
            "treated_at": None,
        })

    return alerts


def _get_alerts(db) -> list[dict]:
    global _alerts_cache
    if _alerts_cache is None:
        _alerts_cache = _build_alerts(db)
    return _alerts_cache


@router.get("")
async def list_alerts(severity: str = Query(None), treated: bool = Query(None)):
    """List clinical alerts with optional filters."""
    db = get_db()
    try:
        alerts = _get_alerts(db)
        result = list(alerts)

        if severity:
            sev_set = set(severity.upper().split(","))
            result = [a for a in result if a["severity"] in sev_set]

        if treated is not None:
            result = [a for a in result if a["is_treated"] == treated]

        return result
    except Exception as e:
        logger.error("list_alerts error: %s", e)
        return []


@router.patch("/{case_id}/{rule_name}")
async def mark_alert_treated(case_id: str, rule_name: str, body: dict = Body(default={})):
    """Mark an alert as treated."""
    db = get_db()
    try:
        alerts = _get_alerts(db)
        treated_by = body.get("treated_by", "manual") if body else "manual"

        for alert in alerts:
            if alert["case_id"] == case_id and alert["rule_name"] == rule_name:
                alert["is_treated"] = True
                alert["treated_by"] = treated_by
                alert["treated_at"] = datetime.now().isoformat()
                return alert

        return {"error": "Alert not found", "case_id": case_id, "rule_name": rule_name}
    except Exception as e:
        logger.error("mark_alert_treated error: %s", e)
        return {"error": str(e)}
