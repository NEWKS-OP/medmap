"""Test API health endpoint in detail."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Detailed health endpoint tests."""

    def test_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_returns_json(self):
        resp = client.get("/health")
        assert resp.headers["content-type"].startswith("application/json")

    def test_status_ok(self):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"

    def test_has_api_version(self):
        resp = client.get("/health")
        data = resp.json()
        assert "api_version" in data

    def test_has_db_connected(self):
        resp = client.get("/health")
        data = resp.json()
        assert "db_connected" in data

    def test_has_cases_count(self):
        resp = client.get("/health")
        data = resp.json()
        assert "cases_count" in data


class TestRootEndpoint:
    """Test root endpoint."""

    def test_returns_200(self):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_returns_json(self):
        resp = client.get("/")
        data = resp.json()
        assert isinstance(data, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
