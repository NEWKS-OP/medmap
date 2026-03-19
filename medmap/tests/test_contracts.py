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


class TestAgentResultEdgeCases:
    def test_boundary_090(self):
        r = AgentResult(agent_name="t", decision="ok", confidence=0.90, reasoning="r")
        assert r.badge == AgentConfidenceBadge.AUTO

    def test_boundary_089(self):
        r = AgentResult(agent_name="t", decision="ok", confidence=0.89, reasoning="r")
        assert r.badge == AgentConfidenceBadge.CHECK

    def test_boundary_070(self):
        r = AgentResult(agent_name="t", decision="ok", confidence=0.70, reasoning="r")
        assert r.badge == AgentConfidenceBadge.CHECK

    def test_boundary_069(self):
        r = AgentResult(agent_name="t", decision="ok", confidence=0.69, reasoning="r")
        assert r.badge == AgentConfidenceBadge.REVIEW

    def test_zero_confidence(self):
        r = AgentResult(agent_name="t", decision="ok", confidence=0.0, reasoning="r")
        assert r.badge == AgentConfidenceBadge.REVIEW

    def test_full_confidence(self):
        r = AgentResult(agent_name="t", decision="ok", confidence=1.0, reasoning="r")
        assert r.badge == AgentConfidenceBadge.AUTO

    def test_default_metadata(self):
        r = AgentResult(agent_name="t", decision="ok", confidence=0.5, reasoning="r")
        assert r.metadata == {}
        assert r.needs_human_review is False
        assert r.alternative is None


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


class TestInitSessionState:
    def test_initializes_all_keys(self):
        class FakeState:
            session_state = {}
        st = FakeState()
        init_session_state(st)
        assert st.session_state["pipeline_status"] == PipelineStatus.IDLE
        assert st.session_state["dataframes"] == {}
        assert st.session_state["audit_log"] == []

    def test_does_not_overwrite_existing(self):
        class FakeState:
            session_state = {"pipeline_status": PipelineStatus.RUNNING}
        st = FakeState()
        init_session_state(st)
        assert st.session_state["pipeline_status"] == PipelineStatus.RUNNING

    def test_sets_db_path(self):
        class FakeState:
            session_state = {}
        st = FakeState()
        init_session_state(st)
        assert st.session_state["db_path"] == "data/db/medmap.db"

    def test_sets_empty_lists(self):
        class FakeState:
            session_state = {}
        st = FakeState()
        init_session_state(st)
        assert st.session_state["clinical_alerts"] == []
        assert st.session_state["column_mappings"] == []
        assert st.session_state["chat_history"] == []
        assert st.session_state["pending_corrections"] == []
        assert st.session_state["correction_history"] == []


class TestSessionKeys:
    def test_has_pipeline_status(self):
        assert "pipeline_status" in SESSION_KEYS

    def test_has_dataframes(self):
        assert "dataframes" in SESSION_KEYS

    def test_has_db_conn(self):
        assert "db_conn" in SESSION_KEYS

    def test_has_quality_scores(self):
        assert "quality_scores" in SESSION_KEYS

    def test_has_audit_log(self):
        assert "audit_log" in SESSION_KEYS

    def test_has_clinical_alerts(self):
        assert "clinical_alerts" in SESSION_KEYS

    def test_has_selected_case(self):
        assert "selected_case" in SESSION_KEYS


class TestColumnMapping:
    def test_creation(self):
        cm = ColumnMapping(
            source_file="test.csv",
            source_column="sodium",
            target_column="coSodium_mmol_L",
            confidence=0.95,
            badge=AgentConfidenceBadge.AUTO,
            status="CONSENSUS",
        )
        assert cm.confidence == 0.95
        assert cm.status == "CONSENSUS"

    def test_optional_fields(self):
        cm = ColumnMapping(
            source_file="t", source_column="s", target_column="t",
            confidence=0.5, badge=AgentConfidenceBadge.REVIEW, status="UNCERTAIN",
        )
        assert cm.detective_result is None
        assert cm.validation_result is None


class TestWardScore:
    def test_creation(self):
        w = WardScore(
            ward_name="Cardio", score=85,
            nb_patients=50, nb_errors=10, rank=1,
        )
        assert w.ward_name == "Cardio"
        assert w.rank == 1

    def test_default_axes(self):
        w = WardScore(
            ward_name="t", score=0, nb_patients=0, nb_errors=0, rank=1,
        )
        assert w.axes == {}


class TestClinicalAlert:
    def test_creation(self):
        from datetime import datetime
        a = ClinicalAlert(
            case_id="CASE-001",
            rule_name="AKI_PROBABLE",
            severity=Severity.CRITICAL,
            message="AKI detected",
            sources_involved=["labs", "medication"],
            triggered_values={"creatinine": 4.2},
        )
        assert a.rule_name == "AKI_PROBABLE"
        assert len(a.sources_involved) == 2

    def test_default_sbar(self):
        a = ClinicalAlert(
            case_id="c", rule_name="r", severity=Severity.LOW,
            message="m", sources_involved=[], triggered_values={},
        )
        assert a.sbar is None
        assert a.is_treated is False


class TestLabResult:
    def test_creation(self):
        lr = LabResult(
            parameter_name="Sodium",
            value="140",
            flag="H",
            ref_low="136",
            ref_high="145",
            original_value="140ü",
            was_corrected=True,
        )
        assert lr.parameter_name == "Sodium"
        assert lr.was_corrected is True


class TestCorrectionRequest:
    def test_creation(self):
        cr = CorrectionRequest(
            audit_log_id=1,
            case_id="CASE-001",
            table_name="tbImportLabsData",
            column_name="sodium",
            original_value="999",
            current_value=None,
            new_value="140",
            action=ActionTaken.MANUAL_CORRECT,
        )
        assert cr.corrected_by == "manual"


class TestCorrectionResult:
    def test_success(self):
        cr = CorrectionResult(
            success=True,
            audit_log_id=1,
            previous_value="999",
            new_value="140",
            action=ActionTaken.MANUAL_CORRECT,
        )
        assert cr.success is True
        assert cr.error is None


class TestStreamingProgress:
    def test_creation(self):
        sp = StreamingProgress(
            processed=1000, total=10000, pct=0.1,
            falls=2, anomalies=5, patients=3,
        )
        assert sp.processed == 1000
        assert sp.pct == 0.1


class TestAskDataResult:
    def test_creation(self):
        r = AskDataResult(
            question="How many patients?",
            sql_generated="SELECT COUNT(*) FROM tbCaseData",
            row_count=1,
        )
        assert r.question == "How many patients?"
        assert r.error is None

    def test_with_error(self):
        r = AskDataResult(
            question="Bad query",
            sql_generated="INVALID SQL",
            error="SQL error",
        )
        assert r.error == "SQL error"


class TestDataPassport:
    def test_creation(self):
        dp = DataPassport(
            passport_id=1,
            case_id="CASE-001",
            table_name="tbImportLabsData",
            field_name="sodium",
            raw_value="999",
            cleaned_value=None,
            detected_by="cleaner",
            problem_type=ProblemType.OUTLIER,
            problem_detail="Value out of range",
            action_taken=ActionTaken.QUARANTINE,
            confidence=0.95,
            validated_by=None,
            fhir_alignment=None,
            status=PassportStatus.QUARANTINE,
        )
        assert dp.passport_id == 1
        assert dp.problem_type == ProblemType.OUTLIER


class TestPatientSummary:
    def test_creation(self):
        ps = PatientSummary(
            case_id="CASE-001",
            patient_id="PAT-100",
            age=65,
            gender="M",
            ward="Cardio",
            admission_date="2025-01-15",
            discharge_date="2025-01-25",
            primary_icd10="I50.0",
            primary_icd10_desc="Heart failure",
        )
        assert ps.case_id == "CASE-001"
        assert ps.convergence_score is None


class TestNursingNLPResult:
    def test_creation(self):
        r = NursingNLPResult(
            case_id="CASE-001",
            shift=Shift.EARLY,
            report_date="2025-01-15",
            pain_level=3,
            mobility_status=MobilityStatus.ASSISTED,
            wound_grade="2",
        )
        assert r.pain_level == 3
        assert r.deterioration_flag is False


class TestAgentConfidenceBadgeEnum:
    def test_auto(self):
        assert AgentConfidenceBadge.AUTO.value == "AUTO"

    def test_check(self):
        assert AgentConfidenceBadge.CHECK.value == "CHECK"

    def test_review(self):
        assert AgentConfidenceBadge.REVIEW.value == "REVIEW"

    def test_is_string(self):
        assert isinstance(AgentConfidenceBadge.AUTO, str)


class TestEventTypeEnum:
    def test_order(self):
        assert EventType.ORDER.value == "ORDER"

    def test_change(self):
        assert EventType.CHANGE.value == "CHANGE"

    def test_admin(self):
        assert EventType.ADMIN.value == "ADMIN"


class TestTimelineEventTypeEnum:
    def test_lab(self):
        assert TimelineEventType.LAB.value == "LAB"

    def test_motion_hourly(self):
        assert TimelineEventType.MOTION_HOURLY.value == "MOTION_HOURLY"

    def test_medication(self):
        assert TimelineEventType.MEDICATION.value == "MEDICATION"

    def test_nursing(self):
        assert TimelineEventType.NURSING.value == "NURSING"

    def test_alert(self):
        assert TimelineEventType.ALERT.value == "ALERT"

    def test_assessment(self):
        assert TimelineEventType.ASSESSMENT.value == "ASSESSMENT"


class TestPassportStatusEnum:
    def test_quarantine(self):
        assert PassportStatus.QUARANTINE.value == "QUARANTINE"

    def test_clean(self):
        assert PassportStatus.CLEAN.value == "CLEAN"

    def test_pending_review(self):
        assert PassportStatus.PENDING_REVIEW.value == "PENDING_REVIEW"

    def test_is_string(self):
        assert isinstance(PassportStatus.CLEAN, str)


class TestConvergenceScore:
    def test_creation(self):
        cs = ConvergenceScore(
            case_id="CASE-001",
            total_score=75,
            risk_level=RiskLevel.HIGH,
            breakdown={"labs": 30, "motion": 20},
            top_contributors=["creatinine", "falls", "pain"],
        )
        assert cs.total_score == 75
        assert len(cs.top_contributors) == 3

    def test_risk_level(self):
        cs = ConvergenceScore(
            case_id="C", total_score=50, risk_level=RiskLevel.MODERATE,
            breakdown={}, top_contributors=[],
        )
        assert cs.risk_level == RiskLevel.MODERATE

    def test_empty_breakdown(self):
        cs = ConvergenceScore(
            case_id="C", total_score=0, risk_level=RiskLevel.LOW,
            breakdown={}, top_contributors=[],
        )
        assert cs.breakdown == {}


class TestAgentStats:
    def test_defaults(self):
        s = AgentStats()
        assert s.total_columns == 0
        assert s.auto_mapped == 0
        assert s.conflicts == 0
        assert s.escalated == 0
        assert s.agent_progress == {}

    def test_custom_values(self):
        s = AgentStats(total_columns=50, auto_mapped=40, conflicts=5, escalated=5)
        assert s.total_columns == 50
        assert s.auto_mapped == 40

    def test_agent_progress(self):
        s = AgentStats(agent_progress={"detective": {"processed": 10, "total": 20}})
        assert s.agent_progress["detective"]["processed"] == 10


class TestTimelineEvent:
    def test_creation(self):
        te = TimelineEvent(
            event_type=TimelineEventType.LAB,
            timestamp="2025-01-15T10:00:00",
            data={"sodium": "140"},
        )
        assert te.event_type == TimelineEventType.LAB
        assert te.source_file is None

    def test_with_alert(self):
        te = TimelineEvent(
            event_type=TimelineEventType.ALERT,
            timestamp="2025-01-15T10:00:00",
            data={"rule": "AKI"},
            alert_message="AKI detected",
        )
        assert te.alert_message == "AKI detected"

    def test_medication_event(self):
        te = TimelineEvent(
            event_type=TimelineEventType.MEDICATION,
            timestamp="2025-01-15T10:00:00",
            data={"name": "Metformin", "dose": "500mg"},
            source_file="meds.csv",
        )
        assert te.source_file == "meds.csv"
