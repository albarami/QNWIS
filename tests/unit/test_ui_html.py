"""
Unit tests for HTML dashboard renderer.

Tests the HTML generation with embedded PNG charts.
"""

from __future__ import annotations

from pathlib import Path

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.data.api.client import DataAPI
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis
from src.qnwis.ui.html import render_dashboard_html


def test_render_dashboard_html(tmp_path: Path, monkeypatch: object) -> None:
    """Test HTML dashboard rendering with embedded images."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        api = DataAPI("src/qnwis/data/queries", ttl_s=60)
        html = render_dashboard_html(api, sector="Energy")

        # Check basic HTML structure
        assert "<html>" in html, "Should contain HTML tag"
        assert "</html>" in html, "Should contain closing HTML tag"
        assert "QNWIS Dashboard" in html, "Should contain dashboard title"

        # Check embedded images
        assert "img src=" in html, "Should contain image tags"
        assert "data:image/png;base64," in html, "Should contain base64 embedded images"

        # Check sections
        assert "Salary YoY" in html, "Should contain salary YoY section"
        assert "Sector Employment" in html, "Should contain sector employment section"
        assert "Top sectors" in html, "Should contain top sectors section"
        assert "Early Warning Hotlist" in html, "Should contain EWI section"

    finally:
        csvcat.BASE = old


def test_render_dashboard_html_with_year(
    tmp_path: Path, monkeypatch: object
) -> None:
    """Test HTML dashboard rendering with specific year."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        api = DataAPI("src/qnwis/data/queries", ttl_s=60)
        year = api.latest_year("sector_employment") or 2024
        html = render_dashboard_html(api, year=year, sector="Energy")

        # Check year appears in output
        assert str(year) in html, f"Should contain year {year}"
        assert "<html>" in html

    finally:
        csvcat.BASE = old


def test_render_dashboard_html_deterministic(
    tmp_path: Path, monkeypatch: object
) -> None:
    """Test that HTML dashboard rendering is deterministic."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        api = DataAPI("src/qnwis/data/queries", ttl_s=60)

        # Generate same dashboard twice
        html1 = render_dashboard_html(api, year=2024, sector="Energy")
        html2 = render_dashboard_html(api, year=2024, sector="Energy")

        # Should produce identical output
        assert (
            html1 == html2
        ), "Same parameters should produce identical HTML"

    finally:
        csvcat.BASE = old


def test_render_dashboard_html_different_sectors(
    tmp_path: Path, monkeypatch: object
) -> None:
    """Test HTML dashboard with different sectors."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        api = DataAPI("src/qnwis/data/queries", ttl_s=60)

        # Generate dashboards with different sectors
        html1 = render_dashboard_html(api, sector="Energy")
        html2 = render_dashboard_html(api, sector="Technology")

        # Should produce different output
        assert html1 != html2, "Different sectors should produce different HTML"
        assert "Energy" in html1
        assert "Technology" in html2

    finally:
        csvcat.BASE = old


def test_render_dashboard_html_structure(
    tmp_path: Path, monkeypatch: object
) -> None:
    """Test HTML dashboard has correct structure."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        api = DataAPI("src/qnwis/data/queries", ttl_s=60)
        html = render_dashboard_html(api)

        # Check meta tags
        assert 'charset="utf-8"' in html
        assert 'name="viewport"' in html

        # Check CSS is embedded
        assert "<style>" in html
        assert "font-family" in html
        assert ".grid" in html
        assert ".card" in html

        # Check grid layout
        assert 'class="grid"' in html
        assert 'class="card"' in html

    finally:
        csvcat.BASE = old
