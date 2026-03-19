"""
Alerts router — clinical alerts from cross-dataset anomaly detection.
GET   /api/alerts
PATCH /api/alerts/{case_id}/{rule_name}
GET   /api/alerts/summary
GET   /api/alerts/export
"""

import logging
import threading
from datetime import datetime
from fastapi import APIRouter, Query, Body

from typing import Optional

from api.dependencies import get_db
from contracts import Severity

logger = logging.getLogger(__name__)

router = APIRouter(responses={200: {"description": "Alerts data"}})

# In-memory alert store (populated on first access, cached)
_alerts_cache: Optional[list[dict]] = None
_alerts_lock = threading.Lock()


def _build_sbar(cid: str, rule_name: str, sources: list, message: str) -> dict:
    """Build a simple SBAR template for clinical alerts."""
    src_str = ", ".join(sources[:3])
    return {
        "S": f"Patient {cid} — {rule_name.replace('_', ' ').title()}",
        "B": f"Sources involved: {src_str}",
        "A": message,
        "R": "Review patient data, confirm findings, and take clinical action",
    }


def _build_alerts(db: object) -> list[dict]:
    """Build clinical alerts from anomaly detection + audit log."""
    alerts = []

    # ── Part 1: Clinical anomaly detection (6 rules) ──
    try:
        from pipeline.anomaly import AnomalyDetector
        detector = AnomalyDetector(conn=db)
        clinical_alerts = detector.detect_all()

        for ca in clinical_alerts:
            sev = ca.severity.value if isinstance(ca.severity, Severity) else str(ca.severity)
            alerts.append({
                "case_id": ca.case_id,
                "rule_name": ca.rule_name,
                "severity": sev,
                "message": ca.message,
                "sources_involved": ca.sources_involved,
                "triggered_values": ca.triggered_values,
                "timestamp_generated": ca.timestamp_generated.isoformat() if ca.timestamp_generated else datetime.now().isoformat(),
                "sbar": _build_sbar(ca.case_id, ca.rule_name, ca.sources_involved, ca.message),
                "is_treated": False,
                "treated_by": None,
                "treated_at": None,
            })

        logger.info("Clinical anomaly detection: %d alerts", len(clinical_alerts))
    except Exception as e:
        logger.warning("Clinical anomaly detection failed: %s", e)

    # ── Part 2: Data quality alerts from audit log ──
    try:
        critical = db.execute(
            """SELECT case_id, error_type, column_name, original_value, source_file, table_name
               FROM tbAuditLog
               WHERE severity = 'CRITICAL' AND case_id IS NOT NULL AND case_id != ''
               ORDER BY case_id"""
        ).fetchall()

        by_case: dict[str, list] = {}
        for row in critical:
            cid = row["case_id"]
            by_case.setdefault(cid, []).append(dict(row))

        for cid, entries in by_case.items():
            sources = list({e["source_file"] for e in entries if e["source_file"]})
            triggered = {}
            for e in entries[:5]:
                triggered[e["column_name"] or "unknown"] = e["original_value"]

            error_types = {e["error_type"] for e in entries}

            rule = "DATA_QUALITY_CRITICAL"
            message = f"Critical data quality issues: {', '.join(error_types)}"

            if "CLINICAL_OUTLIER" in error_types:
                rule = "CLINICAL_OUTLIER"
                message = f"Clinical outlier values detected in {len(entries)} fields"

            alerts.append({
                "case_id": cid,
                "rule_name": rule,
                "severity": "CRITICAL",
                "message": message,
                "sources_involved": sources,
                "triggered_values": triggered,
                "timestamp_generated": datetime.now().isoformat(),
                "sbar": _build_sbar(cid, rule, sources, message) if len(entries) > 2 else None,
                "is_treated": False,
                "treated_by": None,
                "treated_at": None,
            })
    except Exception as e:
        logger.warning("Data quality alerts failed: %s", e)

    # Sort by severity (CRITICAL first), then case_id
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts.sort(key=lambda a: (sev_order.get(a["severity"], 9), a["case_id"]))

    return alerts


def _get_alerts(db: object) -> list[dict]:
    global _alerts_cache
    with _alerts_lock:
        if _alerts_cache is None:
            _alerts_cache = _build_alerts(db)
        return _alerts_cache


def invalidate_alerts_cache():
    """Reset alerts cache so next access rebuilds from DB."""
    global _alerts_cache
    with _alerts_lock:
        _alerts_cache = None


@router.get("")
async def list_alerts(
    severity: str = Query(None, description="Filter severity (comma-separated)"),
    treated: bool = Query(None, description="Filter by treated status"),
    rule: str = Query(None, description="Filter by rule name (comma-separated)"),
    limit: int = Query(200, ge=1, le=10000, description="Max results"),
):
    """List clinical alerts with optional severity, treated, and rule filters."""
    db = get_db()
    try:
        alerts = _get_alerts(db)
        result = list(alerts)

        if severity:
            sev_set = set(severity.upper().split(","))
            result = [a for a in result if a["severity"] in sev_set]

        if treated is not None:
            result = [a for a in result if a["is_treated"] == treated]

        if rule:
            rule_set = set(rule.upper().split(","))
            result = [a for a in result if a["rule_name"] in rule_set]

        result = result[:limit]
        logger.info("Returning %d alerts", len(result))
        return result
    except Exception as e:
        logger.error("list_alerts error: %s", e)
        return []


@router.get("/summary")
async def alerts_summary() -> dict:
    """Get summary of all alerts by rule and severity."""
    db = get_db()
    try:
        alerts = _get_alerts(db)
        by_rule: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for a in alerts:
            by_rule[a["rule_name"]] = by_rule.get(a["rule_name"], 0) + 1
            by_severity[a["severity"]] = by_severity.get(a["severity"], 0) + 1

        return {
            "total_alerts": len(alerts),
            "by_rule": by_rule,
            "by_severity": by_severity,
            "treated_count": sum(1 for a in alerts if a["is_treated"]),
            "untreated_count": sum(1 for a in alerts if not a["is_treated"]),
        }
    except Exception as e:
        logger.error("alerts_summary error: %s", e)
        return {"total_alerts": 0, "by_rule": {}, "by_severity": {}}


@router.patch("/{case_id}/{rule_name}")
async def mark_alert_treated(case_id: str, rule_name: str, body: dict = Body(default={})) -> dict:
    """Mark an alert as treated by a specific user."""
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

        logger.warning("Alert not found: case_id=%s, rule_name=%s", case_id, rule_name)
        return {"error": "Alert not found", "case_id": case_id, "rule_name": rule_name}
    except Exception as e:
        logger.error("mark_alert_treated error: %s", e)
        return {"error": str(e)}


@router.get("/export")
async def export_alerts(
    severity: str = Query(None, description="Filter severity (comma-separated)"),
    treated: bool = Query(None, description="Filter by treated status"),
) -> list[dict]:
    """Export all alerts in a flat format suitable for CSV/spreadsheet use.

    Returns simplified alert records with SBAR fields flattened."""
    db = get_db()
    try:
        alerts = _get_alerts(db)
        result = list(alerts)

        if severity:
            sev_set = set(severity.upper().split(","))
            result = [a for a in result if a["severity"] in sev_set]

        if treated is not None:
            result = [a for a in result if a["is_treated"] == treated]

        export = []
        for a in result:
            row = {
                "case_id": a["case_id"],
                "rule_name": a["rule_name"],
                "severity": a["severity"],
                "message": a["message"],
                "sources": ", ".join(a.get("sources_involved") or []),
                "is_treated": a["is_treated"],
                "treated_by": a.get("treated_by"),
                "timestamp": a.get("timestamp_generated"),
            }
            sbar = a.get("sbar")
            if sbar:
                row["sbar_situation"] = sbar.get("S", "")
                row["sbar_background"] = sbar.get("B", "")
                row["sbar_assessment"] = sbar.get("A", "")
                row["sbar_recommendation"] = sbar.get("R", "")
            export.append(row)

        return export
    except Exception as e:
        logger.error("export_alerts error: %s", e)
        return []
