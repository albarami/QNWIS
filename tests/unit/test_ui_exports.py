"""
Unit tests for UI export functions.

Tests matplotlib PNG generation and CSV export functions.
"""

from __future__ import annotations

from pathlib import Path

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.data.api.client import DataAPI
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis
from src.qnwis.ui.export import (
    b64img,
    csv_sector_employment,
    csv_top_sectors,
    png_salary_yoy,
    png_sector_employment_bar,
)


def test_png_and_csv_exports(tmp_path: Path, monkeypatch: object) -> None:
    """Test PNG and CSV export functions produce valid outputs."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        api = DataAPI("src/qnwis/data/queries", ttl_s=120)

        # Test PNG exports
        png1, et1 = png_salary_yoy(api, "Energy")
        assert png1.startswith(b"\x89PNG"), "PNG should start with PNG magic bytes"
        assert len(et1) > 0, "ETag should be non-empty"

        png2, et2 = png_sector_employment_bar(
            api, api.latest_year("sector_employment") or 2024
        )
        assert png2.startswith(b"\x89PNG"), "PNG should start with PNG magic bytes"
        assert len(et2) > 0, "ETag should be non-empty"

        # Test CSV exports
        csvb, etc = csv_sector_employment(api, api.latest_year("sector_employment") or 2024)
        assert b"year,sector,employees" in csvb, "CSV should have header"
        assert len(etc) > 0, "ETag should be non-empty"

        # Test all ETags are unique (different content)
        assert et1 != et2, "Different PNGs should have different ETags"
        assert et1 != etc, "PNG and CSV should have different ETags"

    finally:
        csvcat.BASE = old


def test_csv_top_sectors(tmp_path: Path, monkeypatch: object) -> None:
    """Test CSV export for top sectors."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        api = DataAPI("src/qnwis/data/queries", ttl_s=60)
        year = api.latest_year("sector_employment") or 2024

        csvb, etag = csv_top_sectors(api, year, top_n=3)
        assert b"year,sector,employees" in csvb
        assert len(etag) > 0

        # Check that we get at most 3 rows (plus header)
        lines = csvb.decode("utf-8").strip().split("\n")
        assert 1 <= len(lines) <= 4  # header + up to 3 data rows

    finally:
        csvcat.BASE = old


def test_b64img_encoding() -> None:
    """Test base64 image encoding function."""
    test_data = b"test_image_data"
    result = b64img(test_data)
    assert result.startswith("data:image/png;base64,")
    assert len(result) > len("data:image/png;base64,")


def test_png_exports_deterministic(tmp_path: Path, monkeypatch: object) -> None:
    """Test that PNG exports are deterministic."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        api = DataAPI("src/qnwis/data/queries", ttl_s=60)
        year = api.latest_year("sector_employment") or 2024

        # Generate same PNG twice
        png1, etag1 = png_sector_employment_bar(api, year)
        png2, etag2 = png_sector_employment_bar(api, year)

        # Should produce identical output
        assert png1 == png2, "Same parameters should produce identical PNG"
        assert etag1 == etag2, "Same parameters should produce identical ETag"

    finally:
        csvcat.BASE = old


def test_csv_exports_deterministic(tmp_path: Path, monkeypatch: object) -> None:
    """Test that CSV exports are deterministic."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        api = DataAPI("src/qnwis/data/queries", ttl_s=60)
        year = api.latest_year("sector_employment") or 2024

        # Generate same CSV twice
        csv1, etag1 = csv_sector_employment(api, year)
        csv2, etag2 = csv_sector_employment(api, year)

        # Should produce identical output
        assert csv1 == csv2, "Same parameters should produce identical CSV"
        assert etag1 == etag2, "Same parameters should produce identical ETag"

    finally:
        csvcat.BASE = old
