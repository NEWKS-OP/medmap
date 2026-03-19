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

from api.dependencies import pipeline_state, get_db_path, close_db
from contracts import PipelineStatus, PipelineProgress

logger = logging.getLogger(__name__)

router = APIRouter(responses={200: {"description": "Success"}})


def _run_pipeline_thread(data_folder: str):
    """Run the pipeline in a background thread."""
    try:
        from pipeline.agents.orchestrator import PipelineOrchestrator

        db_path = get_db_path()
        close_db()

        orchestrator = PipelineOrchestrator(db_path=db_path)
        for progress in orchestrator.run_pipeline(
            data_folder=data_folder, include_split=True
        ):
            pipeline_state.update_progress(progress)

        if orchestrator.stats:
            pipeline_state.update_stats(orchestrator.stats)

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
    """Launch the pipeline in background."""
    if pipeline_state.is_running:
        return {
            "status": "RUNNING",
            "message": "Pipeline is already running",
        }

    data_folder = body.get("data_folder", "dirty") if body else "dirty"
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
    """Get current pipeline progress."""
    return asdict(pipeline_state.get_progress())


@router.get("/stats")
async def get_stats() -> dict:
    """Get pipeline stats after completion."""
    stats = pipeline_state.get_stats()
    if stats is None:
        return {
            "sources_processed": 0, "total_rows": 0,
            "rows_imported": 0, "rows_quarantined": 0,
            "errors_by_category": {}, "errors_by_dataset": {},
            "critical_alerts": [], "ward_scores": {},
            "processing_time_seconds": 0.0, "top_patient_risk": None,
        }
    return asdict(stats)


@router.get("/streaming-progress")
async def get_streaming_progress() -> dict:
    """Get 1Hz streaming progress."""
    return asdict(pipeline_state.get_streaming())
