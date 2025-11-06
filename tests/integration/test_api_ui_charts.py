"""
Integration tests for UI chart endpoints.

Tests verify FastAPI endpoints return correct structure and status codes
using synthetic CSV data. All tests monkeypatch csv_catalog.BASE.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.app import app
from src.qnwis.data.api.client import DataAPI
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis


def test_ui_chart_salary_yoy(tmp_path, monkeypatch):
    """
    Test /v1/ui/charts/salary-yoy endpoint.

    Verifies:
        - Endpoint returns 200 status
        - Response contains series data
        - Sector parameter is required
        - Series structure is correct
    """
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")

    try:
        client = TestClient(app)

        # Test with Energy sector
        response = client.get("/v1/ui/charts/salary-yoy?sector=Energy")
        assert response.status_code == 200, "Should return 200 OK"
        assert "ETag" in response.headers and response.headers["ETag"], "ETag header should be set"
        assert (
            response.headers.get("Cache-Control") == "public, max-age=60"
        ), "Cache-Control header should be public, max-age=60"
        data = response.json()
        assert "series" in data, "Response should have 'series' key"
        assert "title" in data, "Response should have 'title' key"
        assert isinstance(data["series"], list), "Series should be a list"
        assert "Energy" in data["title"], "Title should include sector name"

        if data["series"]:
            point = data["series"][0]
            assert "x" in point, "Data point should have x (year)"
            assert "y" in point, "Data point should have y (yoy_percent)"
            assert isinstance(point["x"], int), "x should be integer year"

        # Test with different sector
        response = client.get("/v1/ui/charts/salary-yoy?sector=Construction")
        assert response.status_code == 200, "Should work with Construction sector"

        # Test missing sector parameter
        response = client.get("/v1/ui/charts/salary-yoy")
        assert (
            response.status_code == 422
        ), "Should reject missing sector parameter"

        # Test sector too short
        response = client.get("/v1/ui/charts/salary-yoy?sector=A")
        assert (
            response.status_code == 422
        ), "Should reject sector with < 2 chars"

    finally:
        csvcat.BASE = old


def test_ui_chart_sector_employment(tmp_path, monkeypatch):
    """
    Test /v1/ui/charts/sector-employment endpoint.

    Verifies:
        - Endpoint returns 200 status
        - Response contains categories and values
        - Year parameter defaults to latest and is validated
        - Data structure is correct
    """
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")

    try:
        client = TestClient(app)
        api = DataAPI("src/qnwis/data/queries")

        # Test with valid year
        response = client.get("/v1/ui/charts/sector-employment?year=2024")
        assert response.status_code == 200, "Should return 200 OK"
        data = response.json()
        assert "categories" in data, "Response should have 'categories' key"
        assert "values" in data, "Response should have 'values' key"
        assert "title" in data, "Response should have 'title' key"
        assert "year" in data, "Response should include resolved data year"
        assert isinstance(data["year"], int), "Year should be integer"
        assert isinstance(data["categories"], list), "Categories should be a list"
        assert isinstance(data["values"], list), "Values should be a list"
        assert len(data["categories"]) == len(
            data["values"]
        ), "Categories and values should align"
        assert "2024" in data["title"], "Title should include year"

        # Test missing year parameter
        response = client.get("/v1/ui/charts/sector-employment")
        assert response.status_code == 200, "Should default to latest year"
        default_data = response.json()
        latest_year = api.latest_year("sector_employment")
        if latest_year is not None:
            assert (
                f"{latest_year}" in default_data["title"]
            ), "Default title should include latest year"
            assert (
                default_data["year"] == latest_year
            ), "Default response should surface resolved year"

        # Test year out of range (too low)
        response = client.get("/v1/ui/charts/sector-employment?year=1999")
        assert (
            response.status_code == 422
        ), "Should reject year below 2000"

        # Test year out of range (too high)
        response = client.get("/v1/ui/charts/sector-employment?year=2101")
        assert (
            response.status_code == 422
        ), "Should reject year above 2100"

        # Test boundary values - use realistic years from synthetic data
        response = client.get("/v1/ui/charts/sector-employment?year=2023")
        assert response.status_code == 200, "Should accept year in valid range"

    finally:
        csvcat.BASE = old


def test_ui_chart_employment_share(tmp_path, monkeypatch):
    """
    Test /v1/ui/charts/employment-share endpoint.

    Verifies:
        - Endpoint returns 200 status
        - Response contains gauge data (male/female/total)
        - Year parameter is optional
        - Data structure is correct
    """
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")

    try:
        # Test without year (should default to latest)
        client = TestClient(app)
        api = DataAPI("src/qnwis/data/queries")

        response = client.get("/v1/ui/charts/employment-share")
        assert response.status_code == 200, "Should return 200 OK"
        data = response.json()
        assert "male" in data, "Response should have 'male' key"
        assert "female" in data, "Response should have 'female' key"
        assert "total" in data, "Response should have 'total' key"
        assert "year" in data, "Response should have 'year' key"
        assert isinstance(data["year"], int), "Year should be integer"

        # Test with explicit year
        response = client.get("/v1/ui/charts/employment-share?year=2024")
        assert response.status_code == 200, "Should work with year parameter"
        data_year = response.json()
        assert data_year["year"] == 2024, "Should return data for 2024"

        latest_year = api.latest_year("employment_share_all")
        if latest_year is not None:
            assert data["year"] == latest_year, "Default response should use latest employment share year"

    finally:
        csvcat.BASE = old


def test_ui_charts_ttl_clamping(tmp_path, monkeypatch):
    """
    Test that ttl_s parameter is correctly clamped to 60-86400 range.
    """
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")

    try:
        client = TestClient(app)

        # Test with very low TTL (should be clamped to 60)
        # TTL below minimum should be rejected
        response = client.get(
            "/v1/ui/charts/salary-yoy?sector=Energy&ttl_s=10"
        )
        assert response.status_code == 422, "Should reject TTL below 60 seconds"

        # TTL above maximum should be rejected
        response = client.get(
            "/v1/ui/charts/salary-yoy?sector=Energy&ttl_s=999999"
        )
        assert response.status_code == 422, "Should reject TTL above 86400 seconds"

        # Valid TTL boundaries should succeed
        response = client.get(
            "/v1/ui/charts/salary-yoy?sector=Energy&ttl_s=60"
        )
        assert response.status_code == 200, "Should accept TTL at lower bound"

        response = client.get(
            "/v1/ui/charts/salary-yoy?sector=Energy&ttl_s=86400"
        )
        assert response.status_code == 200, "Should accept TTL at upper bound"

    finally:
        csvcat.BASE = old
