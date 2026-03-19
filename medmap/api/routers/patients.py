from fastapi import APIRouter, Query

router = APIRouter()


@router.get("")
async def list_patients(ward: str = Query(None), limit: int = Query(50)):
    """List patients with optional ward filter."""
    return []


@router.get("/{case_id}")
async def get_patient(case_id: str):
    """Get patient summary."""
    return {"case_id": case_id, "patient_id": None, "age": None, "gender": None, "ward": None}


@router.get("/{case_id}/labs")
async def get_patient_labs(case_id: str):
    """Get lab results for a patient."""
    return []


@router.get("/{case_id}/timeline")
async def get_patient_timeline(case_id: str):
    """Get merged timeline events for a patient."""
    return []


@router.get("/{case_id}/medications")
async def get_patient_medications(case_id: str):
    """Get medication events for a patient."""
    return []


@router.get("/{case_id}/nursing")
async def get_patient_nursing(case_id: str):
    """Get nursing NLP results for a patient."""
    return []


@router.get("/{case_id}/convergence")
async def get_patient_convergence(case_id: str):
    """Get convergence score for a patient."""
    return {"case_id": case_id, "total_score": 0, "risk_level": "LOW", "breakdown": {}, "top_contributors": []}


@router.get("/{case_id}/passports")
async def get_patient_passports(case_id: str):
    """Get data passports for a patient."""
    return []
