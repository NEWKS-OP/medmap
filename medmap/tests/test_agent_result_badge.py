"""Test AgentResult confidence badge computation."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from contracts import AgentResult, AgentConfidenceBadge


class TestAgentResultBadge:
    """Test badge property on AgentResult."""

    def test_auto_badge_at_90(self):
        r = AgentResult(agent_name="test", decision="ok", confidence=0.90, reasoning="x")
        assert r.badge == AgentConfidenceBadge.AUTO

    def test_auto_badge_at_95(self):
        r = AgentResult(agent_name="test", decision="ok", confidence=0.95, reasoning="x")
        assert r.badge == AgentConfidenceBadge.AUTO

    def test_auto_badge_at_100(self):
        r = AgentResult(agent_name="test", decision="ok", confidence=1.0, reasoning="x")
        assert r.badge == AgentConfidenceBadge.AUTO

    def test_check_badge_at_70(self):
        r = AgentResult(agent_name="test", decision="ok", confidence=0.70, reasoning="x")
        assert r.badge == AgentConfidenceBadge.CHECK

    def test_check_badge_at_89(self):
        r = AgentResult(agent_name="test", decision="ok", confidence=0.89, reasoning="x")
        assert r.badge == AgentConfidenceBadge.CHECK

    def test_review_badge_at_69(self):
        r = AgentResult(agent_name="test", decision="ok", confidence=0.69, reasoning="x")
        assert r.badge == AgentConfidenceBadge.REVIEW

    def test_review_badge_at_50(self):
        r = AgentResult(agent_name="test", decision="ok", confidence=0.50, reasoning="x")
        assert r.badge == AgentConfidenceBadge.REVIEW

    def test_review_badge_at_0(self):
        r = AgentResult(agent_name="test", decision="ok", confidence=0.0, reasoning="x")
        assert r.badge == AgentConfidenceBadge.REVIEW

    def test_needs_human_review_default(self):
        r = AgentResult(agent_name="test", decision="ok", confidence=0.5, reasoning="x")
        assert r.needs_human_review is False

    def test_metadata_default_empty(self):
        r = AgentResult(agent_name="test", decision="ok", confidence=0.5, reasoning="x")
        assert r.metadata == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
