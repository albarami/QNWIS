"""Tests for dataset catalog registry."""

from __future__ import annotations

from src.qnwis.data.catalog.registry import DatasetCatalog


def test_catalog_match(tmp_path):
    """Test that catalog matches patterns correctly."""
    p = tmp_path / "datasets.yaml"
    p.write_text(
        "datasets:\n  - pattern: 'x*.csv'\n    license: 'Test Lic'\n",
        encoding="utf-8",
    )
    cat = DatasetCatalog(str(p))
    m = cat.match("x123.csv")
    assert m and m["license"] == "Test Lic"


def test_catalog_no_match(tmp_path):
    """Test that catalog returns None when no pattern matches."""
    p = tmp_path / "datasets.yaml"
    p.write_text(
        "datasets:\n  - pattern: 'x*.csv'\n    license: 'Test Lic'\n",
        encoding="utf-8",
    )
    cat = DatasetCatalog(str(p))
    m = cat.match("y123.csv")
    assert m is None


def test_catalog_multiple_entries(tmp_path):
    """Test that catalog returns first matching entry."""
    p = tmp_path / "datasets.yaml"
    p.write_text(
        """datasets:
  - pattern: 'x*.csv'
    license: 'License A'
  - pattern: '*.csv'
    license: 'License B'
""",
        encoding="utf-8",
    )
    cat = DatasetCatalog(str(p))
    m = cat.match("x123.csv")
    assert m and m["license"] == "License A"


def test_catalog_wildcard_pattern(tmp_path):
    """Test wildcard pattern matching."""
    p = tmp_path / "datasets.yaml"
    p.write_text(
        "datasets:\n  - pattern: '*unemployment*.csv'\n    license: 'WB License'\n",
        encoding="utf-8",
    )
    cat = DatasetCatalog(str(p))
    m = cat.match("unemployment_rate_gcc.csv")
    assert m and m["license"] == "WB License"


def test_catalog_empty_list(tmp_path):
    """Test catalog with empty dataset list."""
    p = tmp_path / "datasets.yaml"
    p.write_text("datasets: []\n", encoding="utf-8")
    cat = DatasetCatalog(str(p))
    m = cat.match("any.csv")
    assert m is None


def test_catalog_missing_file_safe(tmp_path):
    """Missing catalog file should not raise and yield no matches."""
    missing_path = tmp_path / "missing.yaml"
    cat = DatasetCatalog(missing_path)
    assert cat.match("anything.csv") is None


def test_catalog_invalid_yaml_safe(tmp_path):
    """Invalid YAML content falls back to empty catalog."""
    p = tmp_path / "datasets.yaml"
    p.write_text("datasets: [\n", encoding="utf-8")
    cat = DatasetCatalog(str(p))
    assert cat.match("any.csv") is None
