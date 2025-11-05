"""
Unit tests for Data API client analytics methods.

Tests derived analytics including top-N lists, YoY calculations, and trends.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.data.api.client import DataAPI
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis


@pytest.fixture
def synthetic_data_api(tmp_path, monkeypatch):
    """Fixture providing DataAPI with synthetic data."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    api = DataAPI("src/qnwis/data/queries", ttl_s=60)
    yield api
    csvcat.BASE = old_base


class TestTopLists:
    """Test top-N ranking methods."""

    def test_top_lists_and_derived(self, tmp_path, monkeypatch):
        """Test top lists return properly ranked results."""
        generate_synthetic_lmis(str(tmp_path))
        old = csvcat.BASE
        csvcat.BASE = Path(tmp_path)
        try:
            api = DataAPI("src/qnwis/data/queries", ttl_s=60)

            # Test top employment sectors
            top_emp = api.top_sectors_by_employment(2024, top_n=3)
            assert len(top_emp) == 3, "Should return exactly 3 sectors"
            assert (
                top_emp[0]["employees"] >= top_emp[-1]["employees"]
            ), "Should be sorted descending"

            # Test YoY employment growth
            yoy = api.yoy_employment_growth_by_sector("Energy")
            assert yoy, "Should return YoY data"
            assert yoy[0]["year"] <= yoy[-1]["year"], "Should be chronologically ordered"

            # Test early warning hotlist
            hot = api.early_warning_hotlist(2024, threshold=3.0, top_n=5)
            assert all(h["drop_percent"] >= 0.0 for h in hot), "Drop percents should be >= 0"
        finally:
            csvcat.BASE = old

    def test_top_sectors_by_employment_ordering(self, synthetic_data_api):
        """Test that top sectors by employment are properly ordered."""
        top_emp = synthetic_data_api.top_sectors_by_employment(2024, top_n=5)
        assert len(top_emp) <= 5, "Should return at most 5 sectors"

        # Verify descending order
        for i in range(len(top_emp) - 1):
            assert (
                top_emp[i]["employees"] >= top_emp[i + 1]["employees"]
            ), "Should be sorted descending by employees"

    def test_top_sectors_by_salary_ordering(self, synthetic_data_api):
        """Test that top sectors by salary are properly ordered."""
        top_sal = synthetic_data_api.top_sectors_by_salary(2024, top_n=5)
        assert len(top_sal) <= 5, "Should return at most 5 sectors"

        # Verify descending order
        for i in range(len(top_sal) - 1):
            assert (
                top_sal[i]["avg_salary_qr"] >= top_sal[i + 1]["avg_salary_qr"]
            ), "Should be sorted descending by salary"

    def test_attrition_hotspots_ordering(self, synthetic_data_api):
        """Test that attrition hotspots are properly ordered."""
        hotspots = synthetic_data_api.attrition_hotspots(2024, top_n=5)
        assert len(hotspots) <= 5, "Should return at most 5 sectors"

        # Verify descending order
        for i in range(len(hotspots) - 1):
            assert (
                hotspots[i]["attrition_percent"] >= hotspots[i + 1]["attrition_percent"]
            ), "Should be sorted descending by attrition"


class TestYoYCalculations:
    """Test year-over-year growth calculations."""

    def test_yoy_salary_by_sector(self, synthetic_data_api):
        """Test YoY salary growth calculation."""
        yoy = synthetic_data_api.yoy_salary_by_sector("Energy")

        assert len(yoy) > 0, "Should return YoY data"
        assert yoy[0]["sector"] == "Energy", "Should be for Energy sector"

        # First year should have None YoY (no prior year)
        if len(yoy) > 1:
            # Verify chronological order
            for i in range(len(yoy) - 1):
                assert yoy[i]["year"] < yoy[i + 1]["year"], "Should be chronological"

    def test_yoy_employment_growth_by_sector(self, synthetic_data_api):
        """Test YoY employment growth calculation."""
        yoy = synthetic_data_api.yoy_employment_growth_by_sector("Healthcare")

        assert len(yoy) > 0, "Should return YoY data"
        assert yoy[0]["sector"] == "Healthcare", "Should be for Healthcare sector"

        # Verify structure
        for entry in yoy:
            assert "year" in entry, "Should have year"
            assert "sector" in entry, "Should have sector"
            assert "yoy_percent" in entry, "Should have yoy_percent"

    def test_yoy_handles_single_year(self, synthetic_data_api):
        """Test that YoY calculation handles single year gracefully."""
        # This depends on synthetic data having multiple years
        # Just verify it doesn't crash
        yoy = synthetic_data_api.yoy_salary_by_sector("Finance")
        assert isinstance(yoy, list), "Should return a list"


class TestDerivedMetrics:
    """Test derived metric calculations."""

    def test_qatarization_gap_by_sector(self, synthetic_data_api):
        """Test Qatarization gap calculation."""
        gaps = synthetic_data_api.qatarization_gap_by_sector(year=2024)

        assert len(gaps) > 0, "Should return gap data"
        for gap in gaps:
            assert "year" in gap, "Should have year"
            assert "sector" in gap, "Should have sector"
            assert "gap_percent" in gap, "Should have gap_percent"
            # Gap can be positive or negative
            assert isinstance(gap["gap_percent"], float), "Gap should be float"

    def test_early_warning_hotlist_threshold(self, synthetic_data_api):
        """Test early warning hotlist filtering by threshold."""
        # Test with low threshold
        hot_low = synthetic_data_api.early_warning_hotlist(2024, threshold=0.0, top_n=10)

        # Test with high threshold
        hot_high = synthetic_data_api.early_warning_hotlist(2024, threshold=10.0, top_n=10)

        # High threshold should have fewer or equal results
        assert len(hot_high) <= len(hot_low), "Higher threshold should filter more"

        # All results should meet threshold
        for entry in hot_high:
            assert (
                entry["drop_percent"] >= 10.0
            ), "All entries should meet threshold"

    def test_early_warning_hotlist_top_n_limit(self, synthetic_data_api):
        """Test early warning hotlist respects top_n limit."""
        hot = synthetic_data_api.early_warning_hotlist(2024, threshold=0.0, top_n=3)

        assert len(hot) <= 3, "Should return at most top_n entries"

        # Verify descending order
        for i in range(len(hot) - 1):
            assert (
                hot[i]["drop_percent"] >= hot[i + 1]["drop_percent"]
            ), "Should be sorted descending"


class TestEmptyResults:
    """Test handling of empty result sets."""

    def test_top_lists_with_zero_results(self, synthetic_data_api):
        """Test that top lists handle zero results gracefully."""
        # Use a future year that might not have data
        # Note: DDL raises ValueError for non-existent year filters
        with pytest.raises(ValueError, match="No rows matched"):
            synthetic_data_api.top_sectors_by_employment(2099, top_n=5)

    def test_yoy_with_no_historical_data(self, synthetic_data_api):
        """Test YoY calculation with no historical data."""
        # Use a sector that might not exist
        yoy = synthetic_data_api.yoy_salary_by_sector("NonexistentSector")

        # Should return empty list
        assert isinstance(yoy, list), "Should return a list"
        assert len(yoy) == 0, "Should be empty for nonexistent sector"
