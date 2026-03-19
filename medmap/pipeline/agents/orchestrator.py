"""
Orchestrator: coordinates the full pipeline execution.
Yields PipelineProgress for streaming updates.
"""

import logging
import time
from typing import Generator, Optional

from contracts import (
    PipelineProgress, PipelineStatus, PipelineStats,
)
from pipeline.ingestion import DataIngester
from pipeline.validator import DataValidator
from pipeline.cleaner import DataCleaner
from pipeline.mapper import DataMapper
from pipeline.sql_export import SQLExporter
from pipeline.nlp import NursingNLPAnalyzer

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Coordinates the full data pipeline: ingest -> validate -> clean -> map -> export."""

    def __init__(self, db_path: Optional[str] = None):
        self.ingester = DataIngester()
        self.validator = DataValidator()
        self.cleaner = DataCleaner(self.validator)
        self.mapper: Optional[DataMapper] = None
        self.exporter = SQLExporter(db_path=db_path)
        self.nlp_analyzer = NursingNLPAnalyzer()
        self.nlp_results: dict = {}
        self.stats: Optional[PipelineStats] = None
        self._streaming_progress = None

    def run_pipeline(self, data_folder: str = "dirty",
                      include_split: bool = True) -> Generator[PipelineProgress, None, None]:
        """Run the full pipeline, yielding progress updates."""
        start_time = time.time()
        total_steps = 6
        errors = []

        try:
            # Step 1: Ingestion
            yield PipelineProgress(
                status=PipelineStatus.RUNNING,
                current_step="Ingesting data files",
                step_number=1,
                total_steps=total_steps,
                progress_pct=0.0,
                step_detail=f"Loading from {data_folder}/ + split/",
            )

            results = self.ingester.ingest_all(
                data_folder=data_folder,
                include_split=include_split,
                include_iid=True,
            )

            total_files = len(results)
            failed_files = sum(1 for df, _ in results.values() if df is None)
            if failed_files:
                errors.append(f"{failed_files}/{total_files} files failed to load")

            yield PipelineProgress(
                status=PipelineStatus.RUNNING,
                current_step="Ingestion complete",
                step_number=1,
                total_steps=total_steps,
                progress_pct=0.2,
                step_detail=f"Loaded {total_files} files",
                errors=errors.copy(),
            )

            # Step 2: Validation
            yield PipelineProgress(
                status=PipelineStatus.RUNNING,
                current_step="Validating data",
                step_number=2,
                total_steps=total_steps,
                progress_pct=0.2,
                step_detail="Running validation rules",
            )

            quality_scores = self.validator.validate_all(self.ingester.dataframes)

            yield PipelineProgress(
                status=PipelineStatus.RUNNING,
                current_step="Validation complete",
                step_number=2,
                total_steps=total_steps,
                progress_pct=0.4,
                step_detail=f"Validated {len(quality_scores)} sources",
                errors=errors.copy(),
            )

            # Step 3: Cleaning
            yield PipelineProgress(
                status=PipelineStatus.RUNNING,
                current_step="Cleaning data",
                step_number=3,
                total_steps=total_steps,
                progress_pct=0.4,
                step_detail="Normalizing dates, IDs, values",
            )

            clean_dfs = self.cleaner.clean_all(self.ingester.dataframes)
            clean_dfs = self.cleaner.map_missing_case_ids(clean_dfs)
            pid_conflicts = self.cleaner.detect_pid_conflicts(clean_dfs)

            yield PipelineProgress(
                status=PipelineStatus.RUNNING,
                current_step="Cleaning complete",
                step_number=3,
                total_steps=total_steps,
                progress_pct=0.5,
                step_detail=f"Cleaned {len(clean_dfs)} files, {len(pid_conflicts)} PID conflicts",
                errors=errors.copy(),
            )

            # Step 4: NLP Analysis (nursing notes)
            yield PipelineProgress(
                status=PipelineStatus.RUNNING,
                current_step="Analyzing nursing notes (NLP)",
                step_number=4,
                total_steps=total_steps,
                progress_pct=0.5,
                step_detail="Extracting pain, mobility, wounds, deterioration",
            )

            try:
                self.nlp_results = self.nlp_analyzer.analyze_all(self.ingester.dataframes)
                nlp_stats = self.nlp_analyzer.get_summary_stats(self.nlp_results)
                nlp_detail = (
                    f"{nlp_stats['total_notes_analyzed']} notes, "
                    f"{nlp_stats['total_patients']} patients, "
                    f"{nlp_stats['extraction_rate']}% extraction rate"
                )
            except Exception as e:
                logger.warning("NLP analysis failed (non-fatal): %s", e)
                self.nlp_results = {}
                nlp_detail = f"NLP skipped: {e}"
                errors.append(f"NLP: {e}")

            yield PipelineProgress(
                status=PipelineStatus.RUNNING,
                current_step="NLP analysis complete",
                step_number=4,
                total_steps=total_steps,
                progress_pct=0.6,
                step_detail=nlp_detail,
                errors=errors.copy(),
            )

            # Step 5: Mapping
            yield PipelineProgress(
                status=PipelineStatus.RUNNING,
                current_step="Mapping to target schema",
                step_number=5,
                total_steps=total_steps,
                progress_pct=0.6,
                step_detail="Mapping to 7 SQL tables",
            )

            self.mapper = DataMapper(iid_sid_map=self.ingester.iid_sid_map)
            mapped = self.mapper.map_all(clean_dfs)

            if self.mapper.mapping_warnings:
                for w in self.mapper.mapping_warnings:
                    errors.append(f"Mapping: {w}")

            yield PipelineProgress(
                status=PipelineStatus.RUNNING,
                current_step="Mapping complete",
                step_number=5,
                total_steps=total_steps,
                progress_pct=0.8,
                step_detail=f"Mapped {sum(len(df) for df in mapped.values() if df is not None and not df.empty)} total rows",
                errors=errors.copy(),
            )

            # Step 6: SQL Export
            yield PipelineProgress(
                status=PipelineStatus.RUNNING,
                current_step="Exporting to SQLite",
                step_number=6,
                total_steps=total_steps,
                progress_pct=0.8,
                step_detail="Creating database and inserting data",
            )

            audit_log = self.cleaner.get_audit_log()
            export_summary = self.exporter.export_all(mapped, audit_log)

            elapsed = time.time() - start_time

            # Build final stats
            total_rows = sum(
                r.rows_loaded for _, r in self.ingester.ingestion_results.items()
            )
            errors_by_cat = {}
            errors_by_dataset = {}
            for fname, score in quality_scores.items():
                for cat, count in score.errors_by_category.items():
                    errors_by_cat[cat] = errors_by_cat.get(cat, 0) + count
                total_errors = sum(score.errors_by_category.values())
                if total_errors:
                    errors_by_dataset[fname] = total_errors

            self.stats = PipelineStats(
                sources_processed=total_files,
                total_rows=total_rows,
                rows_imported=export_summary.get("total_rows", 0),
                rows_quarantined=sum(
                    s.rows_quarantined for s in quality_scores.values()
                ),
                errors_by_category=errors_by_cat,
                errors_by_dataset=errors_by_dataset,
                processing_time_seconds=elapsed,
            )

            yield PipelineProgress(
                status=PipelineStatus.COMPLETED,
                current_step="Pipeline complete",
                step_number=6,
                total_steps=total_steps,
                progress_pct=1.0,
                step_detail=f"Exported {export_summary.get('total_rows', 0)} rows in {elapsed:.1f}s",
                errors=errors.copy(),
            )

        except Exception as e:
            logger.error("Pipeline failed: %s", e, exc_info=True)
            errors.append(f"Pipeline error: {e}")
            yield PipelineProgress(
                status=PipelineStatus.ERROR,
                current_step="Pipeline failed",
                step_number=0,
                total_steps=total_steps,
                progress_pct=0.0,
                step_detail=str(e),
                errors=errors,
            )

    def run_pipeline_sync(self, data_folder: str = "dirty",
                           include_split: bool = True) -> PipelineStats:
        """Run the pipeline synchronously, returning final stats."""
        for progress in self.run_pipeline(data_folder, include_split):
            logger.info(
                "Pipeline [%d/%d] %s: %s",
                progress.step_number, progress.total_steps,
                progress.current_step, progress.step_detail or "",
            )
        return self.stats
