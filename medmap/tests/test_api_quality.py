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


class TestBeforeAfterEndpoint:
    """Test before/after repair comparison endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/quality/before-after?limit=10")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/quality/before-after?limit=10")
        data = resp.json()
        assert isinstance(data, list)

    def test_entries_have_before_after_fields(self):
        resp = client.get("/api/quality/before-after?limit=5")
        data = resp.json()
        for entry in data:
            assert "before" in entry
            assert "after" in entry
            assert "error_type" in entry
            assert "case_id" in entry

    def test_filter_by_source(self):
        resp = client.get("/api/quality/before-after?source=nonexistent_file.csv")
        data = resp.json()
        assert isinstance(data, list)

    def test_filter_by_error_type(self):
        resp = client.get("/api/quality/before-after?error_type=INVALID_DATE")
        data = resp.json()
        assert isinstance(data, list)


class TestBeforeAfterStatsEndpoint:
    """Test before/after stats endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/quality/before-after/stats")
        assert resp.status_code == 200

    def test_returns_dict_with_required_keys(self):
        resp = client.get("/api/quality/before-after/stats")
        data = resp.json()
        assert isinstance(data, dict)
        assert "total_repairs" in data
        assert "by_error_type" in data
        assert "by_source_file" in data
        assert "by_action" in data


class TestErrorCategoriesEndpoint:
    """Test error categories endpoint."""

    def test_returns_200(self):
        resp = client.get("/api/quality/error-categories")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/quality/error-categories")
        data = resp.json()
        assert isinstance(data, list)

    def test_entries_have_required_fields(self):
        resp = client.get("/api/quality/error-categories")
        data = resp.json()
        for entry in data:
            assert "error_type" in entry
            assert "total" in entry
            assert "by_severity" in entry


class TestExportEndpoint:
    """Test CSV export endpoint."""

    def test_allowed_table_returns_200(self):
        resp = client.get("/api/quality/export/tbCaseData?limit=5")
        assert resp.status_code == 200

    def test_disallowed_table_returns_error(self):
        resp = client.get("/api/quality/export/sqlite_master")
        data = resp.json()
        assert "error" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
