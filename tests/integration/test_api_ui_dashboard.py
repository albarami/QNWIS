"""
Integration tests for UI dashboard and export endpoints.

Tests the complete flow from HTTP request to response including
HTML dashboard, PNG charts, and CSV tables.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.app import app
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis


def test_dashboard_and_exports(tmp_path: Path, monkeypatch: object) -> None:
    """Test dashboard HTML and all export endpoints."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")
    try:
        c = TestClient(app)

        # Test HTML dashboard
        r = c.get("/v1/ui/dashboard/summary")
        assert r.status_code == 200
        assert r.headers.get("ETag"), "Should have ETag header"
        assert "QNWIS Dashboard" in r.text
        assert "data:image/png;base64," in r.text

        # Test CSV exports
        r = c.get("/v1/ui/export/sector-employment.csv?year=2024")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert b"year,sector,employees" in r.content

        r = c.get("/v1/ui/export/top-sectors.csv?year=2024&n=5")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]

        # Test PNG exports
        r = c.get("/v1/ui/export/salary-yoy.png?sector=Energy")
        assert r.status_code == 200
        assert r.content.startswith(b"\x89PNG")

        r = c.get("/v1/ui/export/sector-employment.png?year=2024")
        assert r.status_code == 200
        assert r.content.startswith(b"\x89PNG")

    finally:
        csvcat.BASE = old


def test_dashboard_with_params(tmp_path: Path, monkeypatch: object) -> None:
    """Test dashboard with custom year and sector parameters."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        c = TestClient(app)

        r = c.get("/v1/ui/dashboard/summary?year=2024&sector=Technology")
        assert r.status_code == 200
        assert "Technology" in r.text
        assert "2024" in r.text

    finally:
        csvcat.BASE = old


def test_export_etags(tmp_path: Path, monkeypatch: object) -> None:
    """Test that exports include ETag headers."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        c = TestClient(app)

        # All endpoints should have ETag and Cache-Control
        endpoints = [
            "/v1/ui/dashboard/summary",
            "/v1/ui/export/sector-employment.csv?year=2024",
            "/v1/ui/export/top-sectors.csv?year=2024",
            "/v1/ui/export/salary-yoy.png?sector=Energy",
            "/v1/ui/export/sector-employment.png?year=2024",
        ]

        for endpoint in endpoints:
            r = c.get(endpoint)
            assert r.status_code == 200, f"Endpoint {endpoint} failed"
            assert r.headers.get("ETag"), f"No ETag for {endpoint}"
            assert (
                r.headers.get("Cache-Control") == "public, max-age=60"
            ), f"Wrong cache headers for {endpoint}"

    finally:
        csvcat.BASE = old


def test_dashboard_etag_short_circuit(tmp_path: Path, monkeypatch: object) -> None:
    """Test that dashboard endpoints honour If-None-Match and return 304."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        c = TestClient(app)

        # HTML endpoint
        r1 = c.get("/v1/ui/dashboard/summary?sector=Energy")
        assert r1.status_code == 200
        etag = r1.headers["ETag"]
        r2 = c.get(
            "/v1/ui/dashboard/summary?sector=Energy",
            headers={"If-None-Match": etag},
        )
        assert r2.status_code == 304
        assert r2.text == ""
        assert r2.headers.get("Cache-Control") == "public, max-age=60"

        # PNG endpoint
        p1 = c.get("/v1/ui/export/sector-employment.png?year=2024")
        p_etag = p1.headers["ETag"]
        p2 = c.get(
            "/v1/ui/export/sector-employment.png?year=2024",
            headers={"If-None-Match": p_etag},
        )
        assert p2.status_code == 304
        assert p2.content == b""
        assert p2.headers.get("Cache-Control") == "public, max-age=60"

    finally:
        csvcat.BASE = old


def test_export_deterministic(tmp_path: Path, monkeypatch: object) -> None:
    """Test that exports produce deterministic output."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        c = TestClient(app)

        # Request same endpoint twice
        r1 = c.get("/v1/ui/export/sector-employment.png?year=2024")
        r2 = c.get("/v1/ui/export/sector-employment.png?year=2024")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.content == r2.content, "Same request should produce same PNG"
        assert r1.headers["ETag"] == r2.headers["ETag"], "ETags should match"

    finally:
        csvcat.BASE = old


def test_csv_export_validation(tmp_path: Path, monkeypatch: object) -> None:
    """Test CSV export parameter validation."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        c = TestClient(app)

        # Test invalid year
        r = c.get("/v1/ui/export/sector-employment.csv?year=1800")
        assert r.status_code == 422

        # Test missing required year
        r = c.get("/v1/ui/export/sector-employment.csv")
        assert r.status_code == 422

        # Test valid request
        r = c.get("/v1/ui/export/sector-employment.csv?year=2024")
        assert r.status_code == 200

    finally:
        csvcat.BASE = old


def test_png_export_validation(tmp_path: Path, monkeypatch: object) -> None:
    """Test PNG export parameter validation."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        c = TestClient(app)

        # Test missing required sector
        r = c.get("/v1/ui/export/salary-yoy.png")
        assert r.status_code == 422

        # Test sector too short
        r = c.get("/v1/ui/export/salary-yoy.png?sector=E")
        assert r.status_code == 422

        # Test valid request
        r = c.get("/v1/ui/export/salary-yoy.png?sector=Energy")
        assert r.status_code == 200

    finally:
        csvcat.BASE = old


def test_top_sectors_csv_with_n(tmp_path: Path, monkeypatch: object) -> None:
    """Test top sectors CSV with different n values."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        c = TestClient(app)

        # Test with n=3
        r = c.get("/v1/ui/export/top-sectors.csv?year=2024&n=3")
        assert r.status_code == 200
        lines = r.text.strip().split("\n")
        assert 1 <= len(lines) <= 4  # header + up to 3 rows

        # Test with n=10
        r = c.get("/v1/ui/export/top-sectors.csv?year=2024&n=10")
        assert r.status_code == 200

        # Test invalid n
        r = c.get("/v1/ui/export/top-sectors.csv?year=2024&n=100")
        assert r.status_code == 422

    finally:
        csvcat.BASE = old


def test_dashboard_default_year(tmp_path: Path, monkeypatch: object) -> None:
    """Test dashboard uses latest year when not specified."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        c = TestClient(app)

        # Request without year parameter
        r = c.get("/v1/ui/dashboard/summary?sector=Energy")
        assert r.status_code == 200
        assert "QNWIS Dashboard" in r.text

    finally:
        csvcat.BASE = old
