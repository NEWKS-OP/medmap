from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/stats")
async def get_agent_stats():
    """Get agent statistics."""
    return {"total_columns": 0, "auto_mapped": 0, "conflicts": 0, "escalated": 0, "agent_progress": {}}


@router.get("/mappings")
async def get_mappings(badge: str = Query(None), source: str = Query(None), status: str = Query(None)):
    """Get column mappings with optional filters."""
    return []


@router.get("/decisions")
async def get_decisions(limit: int = Query(20)):
    """Get recent agent decisions."""
    return []
