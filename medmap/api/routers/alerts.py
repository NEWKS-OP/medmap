from fastapi import APIRouter, Query

router = APIRouter()


@router.get("")
async def list_alerts(severity: str = Query(None), treated: bool = Query(None)):
    """List clinical alerts with optional filters."""
    return []


@router.patch("/{case_id}/{rule_name}")
async def mark_alert_treated(case_id: str, rule_name: str, body: dict = None):
    """Mark an alert as treated."""
    return {"case_id": case_id, "rule_name": rule_name, "is_treated": True}
