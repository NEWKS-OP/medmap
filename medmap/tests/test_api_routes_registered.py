"""Test that all API routes are properly registered."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.main import app


class TestRouteRegistration:
    """Verify all expected routes are registered in the app."""

    def _get_routes(self):
        # Use the OpenAPI schema rather than app.routes: recent FastAPI
        # versions keep included routers as lazy objects without a .path.
        return list(app.openapi()["paths"].keys())

    def test_health_route(self):
        assert "/health" in self._get_routes()

    def test_root_route(self):
        assert "/" in self._get_routes()

    def test_overview_routes(self):
        routes = self._get_routes()
        assert any("/api/overview" in r for r in routes)

    def test_patients_routes(self):
        routes = self._get_routes()
        assert any("/api/patients" in r for r in routes)

    def test_alerts_routes(self):
        routes = self._get_routes()
        assert any("/api/alerts" in r for r in routes)

    def test_quality_routes(self):
        routes = self._get_routes()
        assert any("/api/quality" in r for r in routes)

    def test_agents_routes(self):
        routes = self._get_routes()
        assert any("/api/agents" in r for r in routes)

    def test_pipeline_routes(self):
        routes = self._get_routes()
        assert any("/api/pipeline" in r for r in routes)

    def test_ask_routes(self):
        routes = self._get_routes()
        assert any("/api/ask" in r for r in routes)

    def test_corrections_routes(self):
        routes = self._get_routes()
        assert any("/api/corrections" in r for r in routes)

    def test_upload_routes(self):
        routes = self._get_routes()
        assert any("/api/upload" in r for r in routes)

    def test_new_bonus_routes(self):
        routes = self._get_routes()
        assert "/api/quality/before-after" in routes
        assert "/api/quality/error-categories" in routes
        assert "/api/overview/summary" in routes
        assert "/api/alerts/export" in routes
        assert "/api/patients/search" in routes

    def test_total_route_count(self):
        routes = self._get_routes()
        assert len(routes) >= 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
