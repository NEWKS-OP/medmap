"""Test API corrections endpoints in detail."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestPendingCorrections:
    """Test pending corrections endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/corrections/pending")
        assert resp.status_code == 200


class TestCorrectionHistory:
    """Test correction history endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/corrections/history")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/corrections/history")
        data = resp.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
