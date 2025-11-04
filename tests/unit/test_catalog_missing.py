"""Tests for catalog robustness with missing or invalid files."""

from __future__ import annotations

from src.qnwis.data.catalog.registry import DatasetCatalog


def test_catalog_missing_file_safe(tmp_path):
    """Missing catalog file should not crash and yield no matches."""
    missing_path = tmp_path / "does_not_exist.yaml"
    # Don't create the file - test that constructor handles missing file
    cat = DatasetCatalog(missing_path)
    # Should work without error
    assert cat.match("anything.csv") is None


def test_catalog_invalid_yaml_safe(tmp_path):
    """Invalid YAML content falls back to empty catalog."""
    p = tmp_path / "bad.yaml"
    p.write_text("datasets: [\n", encoding="utf-8")  # Invalid YAML
    cat = DatasetCatalog(str(p))
    # Should not crash, just return empty results
    assert cat.match("any.csv") is None


def test_catalog_non_dict_items_filtered(tmp_path):
    """Non-dictionary items in datasets list are filtered out."""
    p = tmp_path / "datasets.yaml"
    p.write_text(
        """datasets:
  - pattern: "*.csv"
    license: "Valid"
  - "invalid_string_entry"
  - 12345
  - pattern: "*.txt"
    license: "Also Valid"
""",
        encoding="utf-8",
    )
    cat = DatasetCatalog(str(p))
    # Should only load valid dict entries
    assert cat.match("test.csv") is not None
    assert cat.match("test.txt") is not None
