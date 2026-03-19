"""Test API agents endpoints in detail."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestAgentsStats:
    """Test agents stats endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/agents/stats")
        assert resp.status_code == 200

    def test_returns_json(self):
        resp = client.get("/api/agents/stats")
        data = resp.json()
        assert isinstance(data, dict)


class TestAgentsMappings:
    """Test agents mappings endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/agents/mappings")
        assert resp.status_code == 200


class TestAgentsDecisions:
    """Test agents decisions endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/agents/decisions")
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
