"""Test enum member counts and specific values."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from contracts import (
    Severity, RiskLevel, ActionTaken, ProblemType,
    PassportStatus, AgentConfidenceBadge, PipelineStatus,
    MobilityStatus, EventType, Shift, TimelineEventType,
)


class TestSeverityEnum:
    """Test Severity enum completeness."""

    def test_member_count(self):
        assert len(Severity) == 4

    def test_is_str_enum(self):
        assert isinstance(Severity.CRITICAL, str)


class TestRiskLevelEnum:
    """Test RiskLevel enum."""

    def test_member_count(self):
        assert len(RiskLevel) == 4

    def test_is_str_enum(self):
        assert isinstance(RiskLevel.LOW, str)


class TestActionTakenEnum:
    """Test ActionTaken enum."""

    def test_member_count(self):
        assert len(ActionTaken) == 6

    def test_manual_correct(self):
        assert ActionTaken.MANUAL_CORRECT == "MANUAL_CORRECT"

    def test_rollback(self):
        assert ActionTaken.ROLLBACK == "ROLLBACK"


class TestProblemTypeEnum:
    """Test ProblemType enum."""

    def test_member_count(self):
        assert len(ProblemType) == 6

    def test_corrected(self):
        assert ProblemType.CORRECTED == "CORRECTED"

    def test_structural(self):
        assert ProblemType.STRUCTURAL == "STRUCTURAL"

    def test_duplicate(self):
        assert ProblemType.DUPLICATE == "DUPLICATE"


class TestPassportStatusEnum:
    """Test PassportStatus enum."""

    def test_member_count(self):
        assert len(PassportStatus) == 3


class TestAgentConfidenceBadgeEnum:
    """Test AgentConfidenceBadge enum."""

    def test_auto(self):
        assert AgentConfidenceBadge.AUTO == "AUTO"

    def test_check(self):
        assert AgentConfidenceBadge.CHECK == "CHECK"

    def test_review(self):
        assert AgentConfidenceBadge.REVIEW == "REVIEW"

    def test_member_count(self):
        assert len(AgentConfidenceBadge) == 3


class TestMobilityStatusEnum:
    """Test MobilityStatus enum."""

    def test_independent(self):
        assert MobilityStatus.INDEPENDENT == "INDEPENDENT"

    def test_assisted(self):
        assert MobilityStatus.ASSISTED == "ASSISTED"

    def test_wheelchair(self):
        assert MobilityStatus.WHEELCHAIR == "WHEELCHAIR"

    def test_bed_bound(self):
        assert MobilityStatus.BED_BOUND == "BED_BOUND"

    def test_member_count(self):
        assert len(MobilityStatus) == 4


class TestEventTypeEnum:
    """Test EventType enum."""

    def test_order(self):
        assert EventType.ORDER == "ORDER"

    def test_change(self):
        assert EventType.CHANGE == "CHANGE"

    def test_admin(self):
        assert EventType.ADMIN == "ADMIN"

    def test_member_count(self):
        assert len(EventType) == 3


class TestTimelineEventTypeEnum:
    """Test TimelineEventType enum."""

    def test_lab(self):
        assert TimelineEventType.LAB == "LAB"

    def test_motion_hourly(self):
        assert TimelineEventType.MOTION_HOURLY == "MOTION_HOURLY"

    def test_medication(self):
        assert TimelineEventType.MEDICATION == "MEDICATION"

    def test_nursing(self):
        assert TimelineEventType.NURSING == "NURSING"

    def test_alert(self):
        assert TimelineEventType.ALERT == "ALERT"

    def test_member_count(self):
        assert len(TimelineEventType) == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
