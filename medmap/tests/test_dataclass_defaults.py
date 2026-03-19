"""Test dataclass default values and optional fields."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from contracts import (
    IngestionResult, AgentResult, AgentStats,
    ColumnMapping, AgentConfidenceBadge,
    PipelineProgress, PipelineStatus, PipelineStats,
)


class TestIngestionResultDefaults:
    """Test IngestionResult default fields."""

    def test_warnings_default_empty(self):
        r = IngestionResult(
            source_file="test.csv", rows_total=100,
            rows_loaded=95, encoding_detected="utf-8",
            delimiter_detected=",",
        )
        assert r.warnings == []

    def test_warnings_can_be_set(self):
        r = IngestionResult(
            source_file="test.csv", rows_total=100,
            rows_loaded=95, encoding_detected="utf-8",
            delimiter_detected=",",
            warnings=["warn1"],
        )
        assert r.warnings == ["warn1"]


class TestAgentStatsDefaults:
    """Test AgentStats default fields."""

    def test_total_columns_default(self):
        s = AgentStats()
        assert s.total_columns == 0

    def test_auto_mapped_default(self):
        s = AgentStats()
        assert s.auto_mapped == 0

    def test_conflicts_default(self):
        s = AgentStats()
        assert s.conflicts == 0

    def test_escalated_default(self):
        s = AgentStats()
        assert s.escalated == 0

    def test_agent_progress_default_empty(self):
        s = AgentStats()
        assert s.agent_progress == {}


class TestColumnMappingDefaults:
    """Test ColumnMapping optional fields."""

    def test_minimal_creation(self):
        m = ColumnMapping(
            source_file="test.csv",
            source_column="Na",
            target_column="sodium_mmol_L",
            confidence=0.95,
            badge=AgentConfidenceBadge.AUTO,
            status="CONSENSUS",
        )
        assert m.detective_result is None
        assert m.validation_result is None
        assert m.supervisor_decision is None
        assert m.alternative_target is None


class TestPipelineStatsDefaults:
    """Test PipelineStats default fields."""

    def test_creation(self):
        s = PipelineStats(
            sources_processed=10,
            total_rows=1000,
            rows_imported=950,
            rows_quarantined=50,
            errors_by_category={"MISSING": 5},
            errors_by_dataset={"test.csv": 3},
        )
        assert s.sources_processed == 10
        assert s.total_rows == 1000

    def test_critical_alerts_default(self):
        s = PipelineStats(
            sources_processed=1, total_rows=10,
            rows_imported=10, rows_quarantined=0,
            errors_by_category={}, errors_by_dataset={},
        )
        assert s.critical_alerts == []

    def test_processing_time_default(self):
        s = PipelineStats(
            sources_processed=1, total_rows=10,
            rows_imported=10, rows_quarantined=0,
            errors_by_category={}, errors_by_dataset={},
        )
        assert s.processing_time_seconds == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
