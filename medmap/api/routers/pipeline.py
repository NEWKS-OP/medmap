from fastapi import APIRouter

router = APIRouter()


@router.post("/start")
async def start_pipeline(body: dict = None):
    """Launch the pipeline in background."""
    return {"status": "IDLE", "message": "Not implemented yet"}


@router.get("/progress")
async def get_progress():
    """Get current pipeline progress."""
    return {"status": "IDLE", "current_step": "", "step_number": 0, "total_steps": 0, "progress_pct": 0.0, "errors": []}


@router.get("/stats")
async def get_stats():
    """Get pipeline stats after completion."""
    return {"sources_processed": 0, "total_rows": 0, "rows_imported": 0, "rows_quarantined": 0, "errors_by_category": {}, "errors_by_dataset": {}, "processing_time_seconds": 0.0}


@router.get("/streaming-progress")
async def get_streaming_progress():
    """Get 1Hz streaming progress."""
    return {"processed": 0, "total": 0, "pct": 0.0, "falls": 0, "anomalies": 0, "patients": 0}
