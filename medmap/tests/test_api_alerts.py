"""Test API alerts endpoints in detail."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestAlertsList:
    """Test alerts list endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/alerts")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/alerts")
        data = resp.json()
        assert isinstance(data, list)

    def test_critical_filter(self):
        resp = client.get("/api/alerts?severity=CRITICAL")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_high_filter(self):
        resp = client.get("/api/alerts?severity=HIGH")
        assert resp.status_code == 200

    def test_limit_param(self):
        resp = client.get("/api/alerts?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 5


class TestAlertsSummary:
    """Test alerts summary endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/alerts/summary")
        assert resp.status_code == 200

    def test_has_required_keys(self):
        resp = client.get("/api/alerts/summary")
        data = resp.json()
        assert "total_alerts" in data
        assert "by_rule" in data
        assert "by_severity" in data


class TestAlertsExport:
    """Test alerts export endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/alerts/export")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/alerts/export")
        data = resp.json()
        assert isinstance(data, list)

    def test_entries_have_flat_sbar(self):
        resp = client.get("/api/alerts/export")
        data = resp.json()
        for entry in data:
            assert "case_id" in entry
            assert "rule_name" in entry
            assert "severity" in entry

    def test_filter_by_severity(self):
        resp = client.get("/api/alerts/export?severity=CRITICAL")
        data = resp.json()
        for entry in data:
            assert entry["severity"] == "CRITICAL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
