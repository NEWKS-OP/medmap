"""Test API pipeline endpoints in detail."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestPipelineProgress:
    """Test pipeline progress endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/pipeline/progress")
        assert resp.status_code == 200

    def test_returns_json(self):
        resp = client.get("/api/pipeline/progress")
        data = resp.json()
        assert isinstance(data, dict)


class TestPipelineStats:
    """Test pipeline stats endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/pipeline/stats")
        assert resp.status_code == 200


class TestStreamingProgress:
    """Test streaming progress endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/pipeline/streaming-progress")
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
