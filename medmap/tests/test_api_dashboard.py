"""Smoke tests for the dashboard aggregate endpoints."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_overview_shape():
    r = client.get("/api/dashboard/overview")
    assert r.status_code == 200
    body = r.json()
    for key in ("kpis", "movement_by_hour", "admissions_by_day", "issues_by_group", "wards"):
        assert key in body


def test_patients_monitor_shape():
    r = client.get("/api/dashboard/patients?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert {"total", "matched", "counts", "patients"} <= set(body)
    assert len(body["patients"]) <= 5
    for p in body["patients"]:
        assert p["anomaly_level"] in {"critical", "high", "medium", "low", "none"}


def test_patients_monitor_filters():
    r = client.get("/api/dashboard/patients?level=critical&limit=50")
    assert r.status_code == 200
    assert all(p["anomaly_level"] == "critical" for p in r.json()["patients"])


def test_clinical_alerts_exclude_data_quality():
    r = client.get("/api/dashboard/alerts?limit=50")
    assert r.status_code == 200
    assert all(a["rule_name"] != "DATA_QUALITY_CRITICAL" for a in r.json())
