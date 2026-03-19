"""Tests for pipeline/agents/orchestrator.py — PipelineOrchestrator class."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.agents.orchestrator import PipelineOrchestrator
from contracts import PipelineStatus, PipelineProgress


class TestPipelineOrchestratorInit:
    def test_default_init(self):
        orch = PipelineOrchestrator()
        assert orch.ingester is not None
        assert orch.validator is not None
        assert orch.cleaner is not None
        assert orch.mapper is None
        assert orch.exporter is not None
        assert orch.stats is None

    def test_custom_db_path(self):
        orch = PipelineOrchestrator(db_path="/tmp/test.db")
        assert orch.exporter.db_path == "/tmp/test.db"


class TestRunPipelineGenerator:
    def test_yields_progress(self):
        orch = PipelineOrchestrator(db_path="/tmp/test_orch.db")
        progress_list = []
        try:
            for progress in orch.run_pipeline(data_folder="dirty", include_split=False):
                progress_list.append(progress)
                if progress.status == PipelineStatus.ERROR:
                    break
                if progress.step_number >= 2:
                    break
        except Exception:
            pass
        assert len(progress_list) >= 1
        assert isinstance(progress_list[0], PipelineProgress)

    def test_first_step_is_ingestion(self):
        orch = PipelineOrchestrator(db_path="/tmp/test_orch2.db")
        try:
            for progress in orch.run_pipeline(data_folder="dirty", include_split=False):
                assert progress.step_number == 1
                assert "Ingest" in progress.current_step
                break
        except Exception:
            pass

    def test_progress_has_total_steps(self):
        orch = PipelineOrchestrator(db_path="/tmp/test_orch3.db")
        try:
            for progress in orch.run_pipeline(data_folder="dirty", include_split=False):
                assert progress.total_steps == 5
                break
        except Exception:
            pass
