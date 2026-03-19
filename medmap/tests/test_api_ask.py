"""Test API ask endpoints in detail."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestAskHistory:
    """Test ask history endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/ask/history")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/ask/history")
        data = resp.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
