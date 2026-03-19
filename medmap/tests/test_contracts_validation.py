"""Test contracts dataclasses and enums."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from contracts import (
    Severity, RiskLevel, ActionTaken, ProblemType,
    PassportStatus, AgentConfidenceBadge, PipelineStatus,
    MobilityStatus, EventType, Shift,
    IngestionResult, SourceQualityScore, AuditLogEntry,
    PipelineProgress, PipelineStats, DataPassport,
    PatientSummary, ClinicalAlert, CorrectionRequest,
    CorrectionResult, ConvergenceScore,
)


class TestEnums:
    """Test enum values."""

    def test_severity_values(self):
        assert Severity.CRITICAL == "CRITICAL"
        assert Severity.HIGH == "HIGH"
        assert Severity.MEDIUM == "MEDIUM"
        assert Severity.LOW == "LOW"

    def test_action_taken_values(self):
        assert ActionTaken.QUARANTINE == "QUARANTINE"
        assert ActionTaken.AUTO_CORRECT == "AUTO_CORRECT"
        assert ActionTaken.FLAGGED == "FLAGGED"
        assert ActionTaken.ACCEPTED == "ACCEPTED"

    def test_pipeline_status_values(self):
        assert PipelineStatus.IDLE == "IDLE"
        assert PipelineStatus.RUNNING == "RUNNING"
        assert PipelineStatus.COMPLETED == "COMPLETED"
        assert PipelineStatus.ERROR == "ERROR"

    def test_problem_type_values(self):
        assert ProblemType.INVALID == "INVALID"
        assert ProblemType.MISSING == "MISSING"
        assert ProblemType.OUTLIER == "OUTLIER"

    def test_passport_status_values(self):
        assert PassportStatus.QUARANTINE == "QUARANTINE"
        assert PassportStatus.CLEAN == "CLEAN"
        assert PassportStatus.PENDING_REVIEW == "PENDING_REVIEW"

    def test_shift_values(self):
        assert Shift.EARLY == "Early"
        assert Shift.LATE == "Late"
        assert Shift.NIGHT == "Night"

    def test_risk_level_values(self):
        assert RiskLevel.LOW == "LOW"
        assert RiskLevel.MODERATE == "MODERATE"
        assert RiskLevel.HIGH == "HIGH"
        assert RiskLevel.CRITICAL == "CRITICAL"


class TestDataclasses:
    """Test dataclass construction."""

    def test_ingestion_result(self):
        r = IngestionResult(
            source_file="test.csv",
            rows_total=100,
            rows_loaded=95,
            encoding_detected="utf-8",
            delimiter_detected=",",
        )
        assert r.source_file == "test.csv"
        assert r.rows_loaded == 95

    def test_pipeline_progress(self):
        p = PipelineProgress(
            status=PipelineStatus.RUNNING,
            current_step="Ingesting",
            step_number=1,
            total_steps=5,
            progress_pct=0.2,
        )
        assert p.status == PipelineStatus.RUNNING
        assert p.progress_pct == 0.2

    def test_source_quality_score(self):
        s = SourceQualityScore(
            source_file="test.csv",
            score=85.0,
            rows_imported=100,
            rows_quarantined=5,
            values_auto_corrected=10,
            errors_by_category={"MISSING": 3, "INVALID": 2},
        )
        assert s.score == 85.0
        assert s.rows_quarantined == 5

    def test_audit_log_entry(self):
        e = AuditLogEntry(
            source_file="test.csv",
            case_id="CASE-0001",
            table_name="tbImportLabsData",
            column_name="sodium_mmol_L",
            original_value="999",
            cleaned_value=None,
            error_type="OUTLIER",
            severity=Severity.CRITICAL,
            action_taken=ActionTaken.QUARANTINE,
            corrected_by=None,
        )
        assert e.severity == Severity.CRITICAL

    def test_clinical_alert(self):
        a = ClinicalAlert(
            case_id="CASE-0001",
            rule_name="AKI_PROBABLE",
            severity=Severity.CRITICAL,
            message="Probable AKI detected",
            sources_involved=["labs", "medication"],
            triggered_values={"creatinine": 5.0},
            timestamp_generated="2024-01-15T10:00:00",
        )
        assert a.rule_name == "AKI_PROBABLE"

    def test_patient_summary(self):
        p = PatientSummary(
            case_id="CASE-0001",
            patient_id="LAB_100001",
            age=65,
            gender="M",
            ward="Cardiology",
            admission_date="2024-01-15",
            discharge_date="2024-01-20",
            primary_icd10="I50.0",
            primary_icd10_desc="Heart failure",
        )
        assert p.case_id == "CASE-0001"
        assert p.ward == "Cardiology"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
