"""Test API quality endpoints in detail."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestAuditLogEndpoint:
    """Test audit log endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/quality/audit-log?limit=10")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/quality/audit-log?limit=10")
        data = resp.json()
        assert isinstance(data, list)

    def test_limit_works(self):
        resp = client.get("/api/quality/audit-log?limit=5")
        data = resp.json()
        assert len(data) <= 5


class TestPassportsEndpoint:
    """Test passports endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/quality/passports?limit=10")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/quality/passports?limit=10")
        data = resp.json()
        assert isinstance(data, list)


class TestCompletenessEndpoint:
    """Test completeness endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/quality/completeness")
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
