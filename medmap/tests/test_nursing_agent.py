"""Tests for NursingAnalystAgent."""

import pytest
import pandas as pd
from pipeline.agents.nursing_analyst import NursingAnalystAgent


@pytest.fixture
def agent():
    return NursingAnalystAgent()


@pytest.fixture
def context_with_nursing():
    df = pd.DataFrame({
        "CaseID": ["C1", "C2"],
        "NursingNote": ["Pain level 7/10. confused.", "stable condition."],
        "Shift": ["Early shift", "Late shift"],
        "ReportDate": ["2025-01-01", "2025-01-02"],
    })
    return {"dataframes": {"nursing_data.csv": df}}


class TestNursingAnalystAgent:
    def test_run_success(self, agent, context_with_nursing):
        result = agent.run(context_with_nursing)
        assert result.success is True
        assert result.agent_name == "NursingAnalyst"

    def test_run_populates_context(self, agent, context_with_nursing):
        agent.run(context_with_nursing)
        assert "nlp_results" in context_with_nursing
        assert "C1" in context_with_nursing["nlp_results"]

    def test_run_stats(self, agent, context_with_nursing):
        result = agent.run(context_with_nursing)
        assert result.stats["total_notes"] == 2
        assert result.stats["total_patients"] == 2
        assert result.stats["pain_extracted"] == 1
        assert result.stats["deterioration_flagged"] == 1

    def test_run_empty_context(self, agent):
        result = agent.run({})
        assert result.success is False
        assert "No dataframes" in result.errors[0]

    def test_run_no_nursing_data(self, agent):
        context = {"dataframes": {"labs.csv": pd.DataFrame({"col1": [1]})}}
        result = agent.run(context)
        assert result.success is True
        assert result.stats["total_notes"] == 0
