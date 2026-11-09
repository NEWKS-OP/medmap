"""
Pipeline router — start, progress, stats, streaming-progress.
POST /api/pipeline/start
GET  /api/pipeline/progress
GET  /api/pipeline/stats
GET  /api/pipeline/streaming-progress
"""

import threading
import logging
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Body

from api.dependencies import pipeline_state, get_db_path
from contracts import PipelineStatus, PipelineProgress

logger = logging.getLogger(__name__)

router = APIRouter(responses={200: {"description": "Success"}})


def _run_pipeline_thread(data_folder: str):
    """Run the full data pipeline in a background thread.

    Calls the orchestrator and updates shared state as it progresses.
    """
    try:
        from pipeline.agents.orchestrator import PipelineOrchestrator

        db_path = get_db_path()

        orchestrator = PipelineOrchestrator(db_path=db_path)
        for progress in orchestrator.run_pipeline(
            data_folder=data_folder, include_split=True
        ):
            pipeline_state.update_progress(progress)

        if orchestrator.stats:
            pipeline_state.update_stats(orchestrator.stats)

        # Invalidate caches that depend on DB data
        try:
            from api.routers.alerts import invalidate_alerts_cache
            invalidate_alerts_cache()
        except Exception as cache_err:
            logger.warning("Failed to invalidate alerts cache: %s", cache_err)
        try:
            from api.routers.dashboard import invalidate_dashboard_cache
            invalidate_dashboard_cache()
        except Exception as cache_err:
            logger.warning("Failed to invalidate dashboard cache: %s", cache_err)

    except Exception as e:
        logger.error("Pipeline thread failed: %s", e, exc_info=True)
        pipeline_state.update_progress(PipelineProgress(
            status=PipelineStatus.ERROR,
            current_step="Pipeline failed",
            step_number=0,
            total_steps=5,
            progress_pct=0.0,
            step_detail=str(e),
            errors=[str(e)],
        ))
    finally:
        pipeline_state.is_running = False


@router.post("/start")
async def start_pipeline(body: dict = Body(default={"data_folder": "dirty"})):
    """Launch the data pipeline in a background thread.

    Accepts data_folder as 'clean' or 'dirty'."""
    if pipeline_state.is_running:
        logger.warning("Pipeline start rejected - already running")
        return {
            "status": "RUNNING",
            "message": "Pipeline is already running",
        }

    data_folder = body.get("data_folder", "dirty") if body else "dirty"
    logger.info("Pipeline start requested for folder: %s", data_folder)
    pipeline_state.is_running = True
    pipeline_state.update_progress(PipelineProgress(
        status=PipelineStatus.RUNNING,
        current_step="Starting pipeline",
        step_number=0,
        total_steps=5,
        progress_pct=0.0,
        step_detail=f"Loading from {data_folder}/",
    ))

    thread = threading.Thread(
        target=_run_pipeline_thread,
        args=(data_folder,),
        daemon=True,
    )
    thread.start()
    logger.info("Pipeline thread started for folder: %s", data_folder)

    return asdict(pipeline_state.get_progress())


@router.get("/progress")
async def get_progress() -> dict:
    """Get current pipeline progress status and step information."""
    return asdict(pipeline_state.get_progress())


@router.get("/stats")
async def get_stats() -> dict:
    """Get pipeline statistics after completion including error counts.

    If no pipeline has been run in this session, reads actual row counts
    from the database so the stats reflect the current DB state.
    """
    stats = pipeline_state.get_stats()
    if stats is not None:
        return asdict(stats)

    # No pipeline run this session — read stats from the existing DB
    try:
        from api.dependencies import get_db
        db = get_db()
        cursor = db.cursor()

        table_counts = {}
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for row in cursor.fetchall():
            name = row["name"]
            if name.startswith("tb") and name != "sqlite_sequence":
                count = cursor.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
                table_counts[name] = count

        total_rows = sum(table_counts.values())
        rows_imported = total_rows - table_counts.get("tbAuditLog", 0) - table_counts.get("tbDataPassport", 0)
        sources_processed = table_counts.get("tbCaseData", 0)

        return {
            "sources_processed": sources_processed,
            "total_rows": total_rows,
            "rows_imported": rows_imported,
            "rows_quarantined": 0,
            "errors_by_category": {},
            "errors_by_dataset": {},
            "critical_alerts": [],
            "ward_scores": {},
            "processing_time_seconds": 0.0,
            "top_patient_risk": None,
            "table_counts": table_counts,
        }
    except Exception as e:
        logger.warning("Failed to read DB stats: %s", e)
        return {
            "sources_processed": 0, "total_rows": 0,
            "rows_imported": 0, "rows_quarantined": 0,
            "errors_by_category": {}, "errors_by_dataset": {},
            "critical_alerts": [], "ward_scores": {},
            "processing_time_seconds": 0.0, "top_patient_risk": None,
        }


@router.get("/streaming-progress")
async def get_streaming_progress() -> dict:
    """Get 1Hz device data streaming progress during pipeline execution."""
    return asdict(pipeline_state.get_streaming())
