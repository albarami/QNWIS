"""Integration tests for SLO API endpoints."""
from __future__ import annotations

import json
from pathlib import Path


def test_slo_list_endpoint(api_client, tmp_path, monkeypatch):
    """Test GET /api/v1/slo returns SLO definitions."""
    # Create temporary SLO directory
    slo_dir = tmp_path / "slo"
    slo_dir.mkdir()
    slo_data = {
        "slos": [
            {"id": "test_slo", "sli": "availability_pct", "objective": 99.9, "window_days": 14, "windows": {"fast_minutes": 5, "slow_minutes": 60}}
        ]
    }
    (slo_dir / "test.yaml").write_text(json.dumps(slo_data), encoding="utf-8")

    # Monkeypatch load_directory to use tmp_path
    from src.qnwis.slo import loader
    original_load = loader.load_directory

    def _mock_load(directory: str | Path = "slo"):
        return original_load(slo_dir)

    monkeypatch.setattr(loader, "load_directory", _mock_load)

    response = api_client.get("/api/v1/slo/")
    assert response.status_code == 200
    body = response.json()
    assert "slos" in body
    assert len(body["slos"]) == 1
    assert body["slos"][0]["id"] == "test_slo"


def test_slo_budget_endpoint_requires_windows(api_client, tmp_path, monkeypatch):
    """Test GET /api/v1/slo/budget requires sli_windows.json."""
    from src.qnwis.slo import loader

    slo_dir = tmp_path / "slo"
    slo_dir.mkdir()
    slo_data = {"slos": [{"id": "s1", "sli": "availability_pct", "objective": 99.9, "window_days": 14, "windows": {"fast_minutes": 5, "slow_minutes": 60}}]}
    (slo_dir / "test.yaml").write_text(json.dumps(slo_data), encoding="utf-8")

    def _mock_load(directory: str | Path = "slo"):
        return loader.load_file(slo_dir / "test.yaml")

    monkeypatch.setattr(loader, "load_directory", _mock_load)

    response = api_client.get("/api/v1/slo/budget")
    assert response.status_code == 400
    assert "sli_windows.json" in response.json()["detail"]


def test_slo_simulate_requires_admin(api_client, analyst_headers):
    """Test POST /api/v1/slo/simulate requires admin/service role."""
    payload = {"fast": {"bad": 10, "total": 1000}, "slow": {"bad": 100, "total": 10000}, "window_error_fraction": 0.0001}
    response = api_client.post("/api/v1/slo/simulate", json=payload, headers=analyst_headers)
    # analyst role should be rejected (requires admin or service)
    assert response.status_code == 403


def test_slo_simulate_with_admin(api_client, tmp_path, monkeypatch):
    """Test POST /api/v1/slo/simulate with admin role."""
    from src.qnwis.slo import loader

    slo_dir = tmp_path / "slo"
    slo_dir.mkdir()
    slo_data = {"slos": [{"id": "s1", "sli": "availability_pct", "objective": 99.9, "window_days": 14, "windows": {"fast_minutes": 5, "slow_minutes": 60}}]}
    (slo_dir / "test.yaml").write_text(json.dumps(slo_data), encoding="utf-8")

    def _mock_load(directory: str | Path = "slo"):
        return loader.load_file(slo_dir / "test.yaml")

    monkeypatch.setattr(loader, "load_directory", _mock_load)

    admin_headers = {"X-API-Key": "admin-key"}
    payload = {"fast": {"bad": 10, "total": 1000}, "slow": {"bad": 100, "total": 10000}, "window_error_fraction": 0.0001}
    response = api_client.post("/api/v1/slo/simulate", json=payload, headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "budgets" in body
    assert len(body["budgets"]) == 1
    assert body["budgets"][0]["id"] == "s1"
    assert "remaining_pct" in body["budgets"][0]
    assert "burn_fast" in body["budgets"][0]
