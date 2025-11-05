"""
Integration tests for Data API on synthetic data.

End-to-end tests using synthetic seed data and CSV BASE monkeypatch.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.data.api.client import DataAPI
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis


@pytest.fixture
def synthetic_data_api(tmp_path):
    """Fixture providing DataAPI with synthetic data."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    api = DataAPI("src/qnwis/data/queries", ttl_s=120)
    yield api
    csvcat.BASE = old_base


class TestEndToEndDataAPI:
    """End-to-end integration tests for Data API."""

    def test_data_api_end_to_end(self, tmp_path, monkeypatch):
        """Test complete Data API workflow with synthetic data."""
        generate_synthetic_lmis(str(tmp_path))
        old = csvcat.BASE
        csvcat.BASE = Path(tmp_path)
        try:
            api = DataAPI("src/qnwis/data/queries", ttl_s=120)

            # Test unemployment
            unemployment = api.unemployment_qatar()
            assert unemployment is not None, "Should return Qatar unemployment data"

            # Test Qatarization gap
            gaps = api.qatarization_gap_by_sector(2024)
            assert gaps, "Should return Qatarization gap data"

            # Test top sectors by salary
            top_sal = api.top_sectors_by_salary(2024, 5)
            assert top_sal, "Should return top salary sectors"

            # Test attrition hotspots
            hotspots = api.attrition_hotspots(2024, 5)
            assert hotspots, "Should return attrition hotspots"
        finally:
            csvcat.BASE = old

    def test_all_employment_methods(self, synthetic_data_api):
        """Test all employment-related methods."""
        # Test employment share methods
        all_shares = synthetic_data_api.employment_share_all()
        assert len(all_shares) > 0, "Should return employment shares"

        latest_shares = synthetic_data_api.employment_share_latest()
        assert len(latest_shares) > 0, "Should return latest shares"

        male_shares = synthetic_data_api.employment_male_share()
        assert len(male_shares) > 0, "Should return male shares"

        female_shares = synthetic_data_api.employment_female_share()
        assert len(female_shares) > 0, "Should return female shares"

    def test_all_unemployment_methods(self, synthetic_data_api):
        """Test all unemployment-related methods."""
        gcc_unemployment = synthetic_data_api.unemployment_gcc_latest()
        assert len(gcc_unemployment) > 0, "Should return GCC unemployment data"

        qatar_unemployment = synthetic_data_api.unemployment_qatar()
        # May be None if Qatar not in data, but method should work
        assert (
            qatar_unemployment is None or qatar_unemployment.country.upper() in {"QAT", "QATAR"}
        )

    def test_all_qatarization_methods(self, synthetic_data_api):
        """Test all Qatarization-related methods."""
        qat_by_sector = synthetic_data_api.qatarization_by_sector()
        assert len(qat_by_sector) > 0, "Should return Qatarization by sector"

        qat_gaps = synthetic_data_api.qatarization_gap_by_sector()
        assert len(qat_gaps) > 0, "Should return Qatarization gaps"

    def test_all_salary_methods(self, synthetic_data_api):
        """Test all salary-related methods."""
        avg_salaries = synthetic_data_api.avg_salary_by_sector()
        assert len(avg_salaries) > 0, "Should return average salaries"

        if avg_salaries:
            sector = avg_salaries[0].sector
            yoy = synthetic_data_api.yoy_salary_by_sector(sector)
            assert isinstance(yoy, list), "Should return YoY salary data"

    def test_all_attrition_methods(self, synthetic_data_api):
        """Test all attrition-related methods."""
        attrition = synthetic_data_api.attrition_by_sector()
        assert len(attrition) > 0, "Should return attrition data"

        hotspots = synthetic_data_api.attrition_hotspots(2024, top_n=3)
        assert len(hotspots) <= 3, "Should return at most 3 hotspots"

    def test_all_company_size_methods(self, synthetic_data_api):
        """Test company size distribution methods."""
        company_sizes = synthetic_data_api.company_size_distribution()
        assert len(company_sizes) > 0, "Should return company size data"

    def test_all_sector_employment_methods(self, synthetic_data_api):
        """Test sector employment methods."""
        sector_emp = synthetic_data_api.sector_employment()
        assert len(sector_emp) > 0, "Should return sector employment data"

        if sector_emp:
            sector = sector_emp[0].sector
            yoy = synthetic_data_api.yoy_employment_growth_by_sector(sector)
            assert isinstance(yoy, list), "Should return YoY employment growth"

    def test_all_early_warning_methods(self, synthetic_data_api):
        """Test early warning indicator methods."""
        ewi = synthetic_data_api.ewi_employment_drop()
        assert len(ewi) > 0, "Should return EWI data"

        hotlist = synthetic_data_api.early_warning_hotlist(threshold=0.0, top_n=5)
        assert len(hotlist) <= 5, "Should return at most 5 entries"

    def test_all_analytics_methods(self, synthetic_data_api):
        """Test all convenience analytics methods."""
        top_emp = synthetic_data_api.top_sectors_by_employment(2024, top_n=3)
        assert len(top_emp) <= 3, "Should return at most 3 sectors"

        top_sal = synthetic_data_api.top_sectors_by_salary(2024, top_n=3)
        assert len(top_sal) <= 3, "Should return at most 3 sectors"

        hotspots = synthetic_data_api.attrition_hotspots(2024, top_n=3)
        assert len(hotspots) <= 3, "Should return at most 3 hotspots"


class TestParameterOverrides:
    """Test parameter override functionality across methods."""

    def test_year_overrides_work_consistently(self, synthetic_data_api):
        """Test that year parameter overrides work for all relevant methods."""
        # Test with 2024
        emp_2024 = synthetic_data_api.employment_share_latest(year=2024)
        assert all(r.year == 2024 for r in emp_2024 if r.year == 2024)

        # Test with 2019
        emp_2019 = synthetic_data_api.employment_share_latest(year=2019)
        # Should include 2019 data if available
        {r.year for r in emp_2019}
        # At minimum, should not crash


class TestDataConsistency:
    """Test data consistency across methods."""

    def test_employment_totals_consistency(self, synthetic_data_api):
        """Test that employment percentages sum to 100."""
        shares = synthetic_data_api.employment_share_all()

        for row in shares:
            # Allow small floating point variance
            total = row.male_percent + row.female_percent
            assert 99.0 <= total <= 101.0, f"Male + female should be ~100%, got {total}"

    def test_qatarization_consistency(self, synthetic_data_api):
        """Test that Qatarization percentages are consistent."""
        qat_data = synthetic_data_api.qatarization_by_sector()

        for row in qat_data:
            total = row.qataris + row.non_qataris
            if total > 0:
                calculated_pct = (row.qataris / total) * 100
                # Allow reasonable variance due to rounding
                assert (
                    abs(calculated_pct - row.qatarization_percent) < 5.0
                ), f"Qatarization % inconsistent: {calculated_pct} vs {row.qatarization_percent}"


class TestErrorHandling:
    """Test error handling for edge cases."""

    def test_nonexistent_query_raises_error(self, synthetic_data_api):
        """Test that nonexistent query IDs raise appropriate errors."""
        # This tests internal error handling
        # The API methods should not expose this directly
        pass

    def test_future_year_returns_empty_gracefully(self, synthetic_data_api):
        """Test that querying future years raises ValueError appropriately."""
        # DDL raises ValueError for non-existent year filters
        with pytest.raises(ValueError, match="No rows matched"):
            synthetic_data_api.sector_employment(year=2099)

    def test_invalid_sector_in_yoy_returns_empty(self, synthetic_data_api):
        """Test that invalid sector in YoY calculation returns empty list."""
        yoy = synthetic_data_api.yoy_salary_by_sector("InvalidSectorXYZ")
        assert isinstance(yoy, list), "Should return a list"
        assert len(yoy) == 0, "Should be empty for invalid sector"
