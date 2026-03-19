"""Tests for contracts.py — shared data structures."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from contracts import (
    Severity, RiskLevel, ActionTaken, ProblemType, PassportStatus,
    AgentConfidenceBadge, PipelineStatus, MobilityStatus, EventType,
    Shift, TimelineEventType,
    IngestionResult, SourceQualityScore, AuditLogEntry, AgentResult,
    ColumnMapping, AgentStats, ClinicalAlert, NursingNLPResult,
    ConvergenceScore, PatientSummary, LabResult, TimelineEvent,
    DataPassport, WardScore, AskDataResult, CorrectionRequest,
    CorrectionResult, PipelineProgress, StreamingProgress, PipelineStats,
    ROIInputs, ROIOutputs, SESSION_KEYS, init_session_state,
)


class TestSeverityEnum:
    def test_critical(self):
        assert Severity.CRITICAL.value == "CRITICAL"

    def test_high(self):
        assert Severity.HIGH.value == "HIGH"

    def test_medium(self):
        assert Severity.MEDIUM.value == "MEDIUM"

    def test_low(self):
        assert Severity.LOW.value == "LOW"

    def test_is_string(self):
        assert isinstance(Severity.CRITICAL, str)


class TestActionTakenEnum:
    def test_quarantine(self):
        assert ActionTaken.QUARANTINE.value == "QUARANTINE"

    def test_auto_correct(self):
        assert ActionTaken.AUTO_CORRECT.value == "AUTO_CORRECT"

    def test_flagged(self):
        assert ActionTaken.FLAGGED.value == "FLAGGED"

    def test_accepted(self):
        assert ActionTaken.ACCEPTED.value == "ACCEPTED"

    def test_rollback(self):
        assert ActionTaken.ROLLBACK.value == "ROLLBACK"


class TestRiskLevelEnum:
    def test_low(self):
        assert RiskLevel.LOW.value == "LOW"

    def test_critical(self):
        assert RiskLevel.CRITICAL.value == "CRITICAL"


class TestPipelineStatusEnum:
    def test_idle(self):
        assert PipelineStatus.IDLE.value == "IDLE"

    def test_running(self):
        assert PipelineStatus.RUNNING.value == "RUNNING"

    def test_completed(self):
        assert PipelineStatus.COMPLETED.value == "COMPLETED"

    def test_error(self):
        assert PipelineStatus.ERROR.value == "ERROR"


class TestProblemTypeEnum:
    def test_invalid(self):
        assert ProblemType.INVALID.value == "INVALID"

    def test_missing(self):
        assert ProblemType.MISSING.value == "MISSING"

    def test_outlier(self):
        assert ProblemType.OUTLIER.value == "OUTLIER"

    def test_duplicate(self):
        assert ProblemType.DUPLICATE.value == "DUPLICATE"


class TestShiftEnum:
    def test_early(self):
        assert Shift.EARLY.value == "Early"

    def test_late(self):
        assert Shift.LATE.value == "Late"

    def test_night(self):
        assert Shift.NIGHT.value == "Night"


class TestMobilityStatusEnum:
    def test_independent(self):
        assert MobilityStatus.INDEPENDENT.value == "INDEPENDENT"

    def test_bed_bound(self):
        assert MobilityStatus.BED_BOUND.value == "BED_BOUND"


class TestIngestionResult:
    def test_creation(self):
        r = IngestionResult(
            source_file="test.csv",
            rows_total=100,
            rows_loaded=95,
            encoding_detected="utf-8",
            delimiter_detected=",",
        )
        assert r.source_file == "test.csv"
        assert r.rows_total == 100
        assert r.rows_loaded == 95

    def test_default_warnings(self):
        r = IngestionResult(
            source_file="t", rows_total=0, rows_loaded=0,
            encoding_detected="utf-8", delimiter_detected=",",
        )
        assert r.warnings == []

    def test_with_warnings(self):
        r = IngestionResult(
            source_file="t", rows_total=0, rows_loaded=0,
            encoding_detected="utf-8", delimiter_detected=",",
            warnings=["warn1"],
        )
        assert len(r.warnings) == 1


class TestSourceQualityScore:
    def test_creation(self):
        s = SourceQualityScore(
            source_file="test.csv", score=85,
            rows_imported=100, rows_quarantined=5,
            values_auto_corrected=10,
            errors_by_category={"MISSING_VALUES": 5},
        )
        assert s.score == 85
        assert s.rows_quarantined == 5


class TestAuditLogEntry:
    def test_creation(self):
        e = AuditLogEntry(
            source_file="test.csv",
            case_id="CASE-001",
            table_name="tbImportLabsData",
            column_name="sodium",
            original_value="999",
            cleaned_value=None,
            error_type="CLINICAL_OUTLIER",
            severity=Severity.CRITICAL,
            action_taken=ActionTaken.QUARANTINE,
            corrected_by=None,
        )
        assert e.error_type == "CLINICAL_OUTLIER"
        assert e.severity == Severity.CRITICAL

    def test_optional_fields(self):
        e = AuditLogEntry(
            source_file="t", case_id="c", table_name="t",
            column_name="c", original_value="v", cleaned_value=None,
            error_type="e", severity=Severity.LOW,
            action_taken=ActionTaken.FLAGGED, corrected_by=None,
        )
        assert e.correction_timestamp is None
        assert e.row_number is None


class TestAgentResult:
    def test_badge_auto(self):
        r = AgentResult(
            agent_name="test", decision="ok",
            confidence=0.95, reasoning="high confidence",
        )
        assert r.badge == AgentConfidenceBadge.AUTO

    def test_badge_check(self):
        r = AgentResult(
            agent_name="test", decision="ok",
            confidence=0.80, reasoning="mid confidence",
        )
        assert r.badge == AgentConfidenceBadge.CHECK

    def test_badge_review(self):
        r = AgentResult(
            agent_name="test", decision="ok",
            confidence=0.50, reasoning="low confidence",
        )
        assert r.badge == AgentConfidenceBadge.REVIEW


class TestPipelineProgress:
    def test_creation(self):
        p = PipelineProgress(
            status=PipelineStatus.RUNNING,
            current_step="Ingesting",
            step_number=1,
            total_steps=5,
            progress_pct=0.2,
        )
        assert p.progress_pct == 0.2
        assert p.errors == []

    def test_with_errors(self):
        p = PipelineProgress(
            status=PipelineStatus.ERROR,
            current_step="Failed",
            step_number=0,
            total_steps=5,
            progress_pct=0.0,
            errors=["Error 1"],
        )
        assert len(p.errors) == 1


class TestPipelineStats:
    def test_creation(self):
        s = PipelineStats(
            sources_processed=10,
            total_rows=1000,
            rows_imported=950,
            rows_quarantined=50,
            errors_by_category={"MISSING_VALUES": 20},
            errors_by_dataset={"labs.csv": 20},
        )
        assert s.sources_processed == 10
        assert s.processing_time_seconds == 0.0

    def test_default_lists(self):
        s = PipelineStats(
            sources_processed=0, total_rows=0, rows_imported=0,
            rows_quarantined=0, errors_by_category={}, errors_by_dataset={},
        )
        assert s.critical_alerts == []
        assert s.ward_scores == {}


class TestROIInputsOutputs:
    def test_roi_inputs_defaults(self):
        r = ROIInputs()
        assert r.nb_institutions == 1400
        assert r.complication_rate == 0.05

    def test_roi_outputs_defaults(self):
        r = ROIOutputs()
        assert r.cases_total == 0
        assert r.savings_per_year == 0


class TestSessionKeys:
    def test_has_pipeline_status(self):
        assert "pipeline_status" in SESSION_KEYS

    def test_has_dataframes(self):
        assert "dataframes" in SESSION_KEYS

    def test_has_db_conn(self):
        assert "db_conn" in SESSION_KEYS
