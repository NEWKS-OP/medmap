"""Test API endpoints return correct data."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test health check."""

    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_root_returns_200(self):
        resp = client.get("/")
        assert resp.status_code == 200


class TestOverviewEndpoints:
    """Test overview endpoints."""

    def test_quality_scores(self):
        resp = client.get("/api/overview/quality-scores")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_ward_scores(self):
        resp = client.get("/api/overview/ward-scores")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestPatientsEndpoints:
    """Test patient endpoints."""

    def test_list_patients(self):
        resp = client.get("/api/patients")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_patients_with_limit(self):
        resp = client.get("/api/patients?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) <= 5


class TestAlertsEndpoints:
    """Test alerts endpoints."""

    def test_list_alerts(self):
        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_alerts_with_severity_filter(self):
        resp = client.get("/api/alerts?severity=CRITICAL")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestQualityEndpoints:
    """Test quality endpoints."""

    def test_audit_log(self):
        resp = client.get("/api/quality/audit-log?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_passports(self):
        resp = client.get("/api/quality/passports?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_completeness(self):
        resp = client.get("/api/quality/completeness")
        assert resp.status_code == 200


class TestAgentsEndpoints:
    """Test agents endpoints."""

    def test_agents_stats(self):
        resp = client.get("/api/agents/stats")
        assert resp.status_code == 200

    def test_agents_mappings(self):
        resp = client.get("/api/agents/mappings")
        assert resp.status_code == 200

    def test_agents_decisions(self):
        resp = client.get("/api/agents/decisions")
        assert resp.status_code == 200


class TestPipelineEndpoints:
    """Test pipeline endpoints."""

    def test_pipeline_progress(self):
        resp = client.get("/api/pipeline/progress")
        assert resp.status_code == 200

    def test_pipeline_stats(self):
        resp = client.get("/api/pipeline/stats")
        assert resp.status_code == 200

    def test_streaming_progress(self):
        resp = client.get("/api/pipeline/streaming-progress")
        assert resp.status_code == 200


class TestAskEndpoints:
    """Test Ask Your Data endpoints."""

    def test_ask_history(self):
        resp = client.get("/api/ask/history")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestCorrectionsEndpoints:
    """Test corrections endpoints."""

    def test_pending_corrections(self):
        resp = client.get("/api/corrections/pending")
        assert resp.status_code == 200

    def test_correction_history(self):
        resp = client.get("/api/corrections/history")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
