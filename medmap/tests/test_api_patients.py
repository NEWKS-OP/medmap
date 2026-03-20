"""Test API patients endpoints in detail."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestPatientsList:
    """Test patient list endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/patients")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/patients")
        data = resp.json()
        assert isinstance(data, list)

    def test_limit_param(self):
        resp = client.get("/api/patients?limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 3

    def test_limit_10(self):
        resp = client.get("/api/patients?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 10

    def test_patient_has_case_id(self):
        resp = client.get("/api/patients?limit=1")
        data = resp.json()
        if data:
            assert "case_id" in data[0]


class TestPatientSearch:
    """Test patient search endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/patients/search?q=test")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/patients/search?q=test")
        data = resp.json()
        assert isinstance(data, list)

    def test_empty_query_returns_empty(self):
        resp = client.get("/api/patients/search?q=")
        data = resp.json()
        assert data == []


class TestPatientMotionSummary:
    """Test patient motion summary endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/patients/NONEXISTENT/motion-summary")
        assert resp.status_code == 200

    def test_not_found_returns_zero(self):
        resp = client.get("/api/patients/NONEXISTENT/motion-summary")
        data = resp.json()
        assert data["total_records"] == 0

    def test_has_required_keys(self):
        # Get a real case_id first
        patients = client.get("/api/patients?limit=1").json()
        if patients:
            cid = patients[0]["case_id"]
            resp = client.get(f"/api/patients/{cid}/motion-summary")
            data = resp.json()
            assert "total_records" in data
            assert "fall_events" in data
            assert "bed_exits" in data
            assert "avg_movement_index" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
