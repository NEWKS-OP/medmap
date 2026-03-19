"""Test API overview endpoints in detail."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestQualityScoresEndpoint:
    """Test quality scores endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/overview/quality-scores")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/overview/quality-scores")
        data = resp.json()
        assert isinstance(data, list)

    def test_scores_have_fields(self):
        resp = client.get("/api/overview/quality-scores")
        data = resp.json()
        if data:
            item = data[0]
            assert "source_file" in item or "name" in item


class TestWardScoresEndpoint:
    """Test ward scores endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/overview/ward-scores")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/overview/ward-scores")
        data = resp.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
