"""
Integration tests for UI export endpoints.

Tests CSV, SVG, and PNG export functionality using synthetic data.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.app import app
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis


def test_export_csv_top_sectors(tmp_path: Path, monkeypatch: object) -> None:
    """Test CSV export for top sectors resource."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        response = client.get("/v1/ui/export/csv?resource=top-sectors&n=3")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "ETag" in response.headers
        assert "Cache-Control" in response.headers
        # Check CSV structure
        lines = response.text.strip().split("\n")
        assert len(lines) >= 2  # Header + at least one data row
        assert "title" in lines[0] or "sector" in lines[0]
    finally:
        csvcat.BASE = old_base


def test_export_csv_ewi(tmp_path: Path, monkeypatch: object) -> None:
    """Test CSV export for early warning indicators."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        response = client.get(
            "/v1/ui/export/csv?resource=ewi&n=3&threshold=2.5"
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
    finally:
        csvcat.BASE = old_base


def test_export_csv_sector_employment(tmp_path: Path, monkeypatch: object) -> None:
    """Test CSV export for sector employment."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        response = client.get(
            "/v1/ui/export/csv?resource=sector-employment&year=2024"
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        # Check for sector and employees columns
        lines = response.text.strip().split("\n")
        assert "sector" in lines[0]
        assert "employees" in lines[0]
    finally:
        csvcat.BASE = old_base


def test_export_csv_salary_yoy(tmp_path: Path, monkeypatch: object) -> None:
    """Test CSV export for salary year-over-year."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        response = client.get(
            "/v1/ui/export/csv?resource=salary-yoy&sector=Energy"
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
    finally:
        csvcat.BASE = old_base


def test_export_csv_employment_share(tmp_path: Path, monkeypatch: object) -> None:
    """Test CSV export for employment share."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        response = client.get(
            "/v1/ui/export/csv?resource=employment-share&year=2024"
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
    finally:
        csvcat.BASE = old_base


def test_export_csv_etag_short_circuit(tmp_path: Path, monkeypatch: object) -> None:
    """ETag should short-circuit repeated CSV requests."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        first = client.get("/v1/ui/export/csv?resource=top-sectors&n=2")
        assert first.status_code == 200
        etag = first.headers.get("ETag")
        assert etag, "First response should include ETag"

        cached = client.get(
            "/v1/ui/export/csv?resource=top-sectors&n=2",
            headers={"If-None-Match": etag},
        )
        assert cached.status_code == 304
        assert cached.text == ""
        assert cached.headers.get("ETag") == etag
        assert cached.headers.get("Cache-Control") == "public, max-age=60"
    finally:
        csvcat.BASE = old_base


def test_export_svg_sector_employment(tmp_path: Path, monkeypatch: object) -> None:
    """Test SVG export for sector employment chart."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        response = client.get(
            "/v1/ui/export/svg?chart=sector-employment&year=2024"
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        assert "ETag" in response.headers
        # Verify SVG structure
        assert response.text.startswith("<svg")
        assert "</svg>" in response.text
        assert "rect" in response.text  # Bar chart should have rectangles
    finally:
        csvcat.BASE = old_base


def test_export_svg_etag_short_circuit(tmp_path: Path, monkeypatch: object) -> None:
    """ETag should short-circuit repeated SVG requests."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        first = client.get("/v1/ui/export/svg?chart=sector-employment")
        assert first.status_code == 200
        etag = first.headers.get("ETag")
        assert etag

        cached = client.get(
            "/v1/ui/export/svg?chart=sector-employment",
            headers={"If-None-Match": etag},
        )
        assert cached.status_code == 304
        assert cached.text == ""
        assert cached.headers.get("ETag") == etag
    finally:
        csvcat.BASE = old_base


def test_export_svg_salary_yoy(tmp_path: Path, monkeypatch: object) -> None:
    """Test SVG export for salary YoY line chart."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        response = client.get(
            "/v1/ui/export/svg?chart=salary-yoy&sector=Energy"
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        # Verify SVG structure
        assert response.text.startswith("<svg")
        assert "</svg>" in response.text
        # Line chart may have path (with data) or fall back to empty chart (without data)
        assert ("path" in response.text or "Salary YoY" in response.text)
    finally:
        csvcat.BASE = old_base


def test_export_csv_ttl_validation(tmp_path: Path, monkeypatch: object) -> None:
    """TTL outside 60-86400 should be rejected for exports."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        too_low = client.get("/v1/ui/export/csv?resource=top-sectors&ttl_s=5")
        assert too_low.status_code == 422
        too_high = client.get(
            "/v1/ui/export/csv?resource=top-sectors&ttl_s=1000000"
        )
        assert too_high.status_code == 422
        ok = client.get("/v1/ui/export/csv?resource=top-sectors&ttl_s=60")
        assert ok.status_code == 200
    finally:
        csvcat.BASE = old_base


def test_export_svg_deterministic(tmp_path: Path, monkeypatch: object) -> None:
    """Test that SVG export produces deterministic output."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        r1 = client.get("/v1/ui/export/svg?chart=sector-employment&year=2024")
        r2 = client.get("/v1/ui/export/svg?chart=sector-employment&year=2024")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.text == r2.text
        assert r1.headers["ETag"] == r2.headers["ETag"]
    finally:
        csvcat.BASE = old_base


def test_export_png_disabled_by_default(tmp_path: Path, monkeypatch: object) -> None:
    """Test that PNG export returns 406 when disabled."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        response = client.get(
            "/v1/ui/export/png?chart=sector-employment&year=2024"
        )
        # Should return 406 when QNWIS_ENABLE_PNG_EXPORT is not set
        assert response.status_code == 406
        assert "PNG export disabled" in response.json()["detail"]
    finally:
        csvcat.BASE = old_base


def test_export_png_enabled(tmp_path: Path, monkeypatch: object) -> None:
    """PNG export should succeed when explicitly enabled and Pillow is available."""
    pil = pytest.importorskip("PIL")
    assert pil is not None

    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    monkeypatch.setenv("QNWIS_ENABLE_PNG_EXPORT", "1")
    try:
        client = TestClient(app)
        response = client.get(
            "/v1/ui/export/png?chart=salary-yoy&sector=Energy"
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/png")
        assert response.headers.get("ETag")
    finally:
        monkeypatch.delenv("QNWIS_ENABLE_PNG_EXPORT", raising=False)
        csvcat.BASE = old_base


def test_csv_export_invalid_resource(tmp_path: Path, monkeypatch: object) -> None:
    """Test that invalid resource returns validation error."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        response = client.get("/v1/ui/export/csv?resource=invalid")
        assert response.status_code == 422  # Validation error
    finally:
        csvcat.BASE = old_base


def test_svg_export_invalid_chart(tmp_path: Path, monkeypatch: object) -> None:
    """Test that invalid chart type returns validation error."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(str(tmp_path))
    try:
        client = TestClient(app)
        response = client.get("/v1/ui/export/svg?chart=invalid")
        assert response.status_code == 422  # Validation error
    finally:
        csvcat.BASE = old_base
