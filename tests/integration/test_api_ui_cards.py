"""
Integration tests for UI card endpoints.

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


def test_ui_cards_top_sectors(tmp_path, monkeypatch):
    """
    Test /v1/ui/cards/top-sectors endpoint.

    Verifies:
        - Endpoint returns 200 status
        - Response contains "cards" key
        - Cards have correct structure
        - Query parameters work correctly
    """
    # Generate synthetic data
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")

    try:
        client = TestClient(app)
        api = DataAPI("src/qnwis/data/queries")

        # Test with year and n parameters
        response = client.get("/v1/ui/cards/top-sectors?year=2024&n=5")
        assert response.status_code == 200, "Should return 200 OK"
        assert "ETag" in response.headers and response.headers["ETag"], "ETag header should be set"
        assert (
            response.headers.get("Cache-Control") == "public, max-age=60"
        ), "Cache-Control header should be public, max-age=60"
        data = response.json()
        assert "cards" in data, "Response should have 'cards' key"
        assert isinstance(data["cards"], list), "Cards should be a list"
        assert len(data["cards"]) <= 5, "Should return at most 5 cards"

        if data["cards"]:
            card = data["cards"][0]
            assert "title" in card, "Card should have title"
            assert "subtitle" in card, "Card should have subtitle"
            assert "kpi" in card, "Card should have kpi"
            assert "unit" in card, "Card should have unit"
            assert "meta" in card, "Card should have meta"
            assert card["unit"] == "persons", "Unit should be 'persons'"
            assert card["meta"]["year"] == 2024, "Meta should have year 2024"

        # Test with default parameters
        response = client.get("/v1/ui/cards/top-sectors")
        assert response.status_code == 200, "Should work with defaults"
        default_data = response.json()
        assert "cards" in default_data, "Should have cards key"
        latest_year = api.latest_year("sector_employment")
        if default_data["cards"] and latest_year is not None:
            assert (
                default_data["cards"][0]["meta"]["year"] == latest_year
            ), "Default response should use latest sector employment year"

        # Test with different n value
        response = client.get("/v1/ui/cards/top-sectors?n=3")
        assert response.status_code == 200, "Should work with n=3"
        data = response.json()
        assert len(data["cards"]) <= 3, "Should return at most 3 cards"

    finally:
        csvcat.BASE = old


def test_ui_cards_ewi(tmp_path, monkeypatch):
    """
    Test /v1/ui/cards/ewi endpoint.

    Verifies:
        - Endpoint returns 200 status
        - Response contains "cards" key
        - Cards have EWI-specific structure
        - Threshold parameter works correctly
    """
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")

    try:
        client = TestClient(app)
        api = DataAPI("src/qnwis/data/queries")

        # Test with threshold parameter
        response = client.get("/v1/ui/cards/ewi?threshold=3.5&n=5")
        assert response.status_code == 200, "Should return 200 OK"
        assert "ETag" in response.headers and response.headers["ETag"], "ETag header should be set"
        assert (
            response.headers.get("Cache-Control") == "public, max-age=60"
        ), "Cache-Control header should be public, max-age=60"
        data = response.json()
        assert "cards" in data, "Response should have 'cards' key"
        assert isinstance(data["cards"], list), "Cards should be a list"
        assert len(data["cards"]) <= 5, "Should return at most 5 cards"

        if data["cards"]:
            card = data["cards"][0]
            assert "title" in card, "Card should have title"
            assert "kpi" in card, "Card should have kpi (drop percent)"
            assert "unit" in card, "Card should have unit"
            assert card["unit"] == "percent", "Unit should be 'percent'"
            assert "threshold" in card["meta"], "Meta should have threshold"
            assert (
                card["meta"]["threshold"] == 3.5
            ), "Meta should have correct threshold"

        # Test with default threshold
        response = client.get("/v1/ui/cards/ewi")
        assert response.status_code == 200, "Should work with defaults"
        default_cards = response.json()
        assert "cards" in default_cards, "Should have cards key"
        latest_year = api.latest_year("ewi_employment_drop")
        if default_cards["cards"] and latest_year is not None:
            assert (
                default_cards["cards"][0]["meta"]["year"] == latest_year
            ), "Default response should use latest EWI year"

        # Test with different year
        response = client.get("/v1/ui/cards/ewi?year=2023&threshold=2.0")
        assert response.status_code == 200, "Should work with year parameter"

    finally:
        csvcat.BASE = old


def test_ui_cards_parameter_validation(tmp_path, monkeypatch):
    """
    Test parameter validation for card endpoints.

    Verifies:
        - Invalid n values are rejected
        - Parameters are correctly clamped
    """
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")

    try:
        client = TestClient(app)

        # Test n parameter validation (should reject values outside 1-20)
        response = client.get("/v1/ui/cards/top-sectors?n=0")
        assert (
            response.status_code == 422
        ), "Should reject n=0 (below minimum)"

        response = client.get("/v1/ui/cards/top-sectors?n=21")
        assert (
            response.status_code == 422
        ), "Should reject n=21 (above maximum)"

        # Test valid boundary values
        response = client.get("/v1/ui/cards/top-sectors?n=1")
        assert response.status_code == 200, "Should accept n=1 (minimum)"

        response = client.get("/v1/ui/cards/top-sectors?n=20")
        assert response.status_code == 200, "Should accept n=20 (maximum)"

    finally:
        csvcat.BASE = old
