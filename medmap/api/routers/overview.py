from fastapi import APIRouter

router = APIRouter()


@router.get("/quality-scores")
async def get_quality_scores():
    """Get quality scores per source file."""
    return []


@router.get("/ward-scores")
async def get_ward_scores():
    """Get ward quality scores."""
    return []


@router.post("/generate-report")
async def generate_report():
    """Generate a quality report."""
    return {"report": "Not implemented yet"}
