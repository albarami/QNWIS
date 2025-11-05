"""
Unit tests for Data API Pydantic models.

Tests validation, serialization, and type safety of all row models.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.qnwis.data.api.models import (
    AttritionRow,
    AvgSalaryRow,
    CompanySizeRow,
    EmploymentShareRow,
    EwiRow,
    QatarizationRow,
    SectorEmploymentRow,
    UnemploymentRow,
)


class TestEmploymentShareRow:
    """Test EmploymentShareRow model validation."""

    def test_employment_share_row_validates(self):
        """Test valid employment share row creation."""
        r = EmploymentShareRow(
            year=2024, male_percent=60.0, female_percent=40.0, total_percent=100.0
        )
        assert r.year == 2024
        assert r.male_percent == 60.0
        assert r.female_percent == 40.0
        assert r.total_percent == 100.0

    def test_employment_share_row_rejects_missing_field(self):
        """Test that missing required fields cause validation error."""
        with pytest.raises(ValidationError):
            # Missing total_percent
            EmploymentShareRow(year=2024, male_percent=60.0, female_percent=40.0)  # type: ignore

    def test_employment_share_row_serialization(self):
        """Test model serialization to dict."""
        r = EmploymentShareRow(
            year=2024, male_percent=60.0, female_percent=40.0, total_percent=100.0
        )
        d = r.model_dump()
        assert d == {
            "year": 2024,
            "male_percent": 60.0,
            "female_percent": 40.0,
            "total_percent": 100.0,
        }


class TestUnemploymentRow:
    """Test UnemploymentRow model validation."""

    def test_unemployment_row_validates(self):
        """Test valid unemployment row creation."""
        r = UnemploymentRow(country="Qatar", year=2024, value=3.5)
        assert r.country == "Qatar"
        assert r.year == 2024
        assert r.value == 3.5

    def test_unemployment_row_rejects_missing_country(self):
        """Test that missing country causes validation error."""
        with pytest.raises(ValidationError):
            UnemploymentRow(year=2024, value=3.5)  # type: ignore


class TestQatarizationRow:
    """Test QatarizationRow model validation."""

    def test_qatarization_row_validates(self):
        """Test valid Qatarization row creation."""
        r = QatarizationRow(
            year=2024,
            sector="Energy",
            qataris=1000,
            non_qataris=5000,
            qatarization_percent=16.7,
        )
        assert r.year == 2024
        assert r.sector == "Energy"
        assert r.qataris == 1000
        assert r.non_qataris == 5000
        assert r.qatarization_percent == 16.7

    def test_qatarization_row_rejects_negative_counts(self):
        """Test that negative counts are rejected."""
        with pytest.raises(ValidationError):
            QatarizationRow(
                year=2024,
                sector="Energy",
                qataris=-100,
                non_qataris=5000,
                qatarization_percent=16.7,
            )


class TestAvgSalaryRow:
    """Test AvgSalaryRow model validation."""

    def test_avg_salary_row_validates(self):
        """Test valid average salary row creation."""
        r = AvgSalaryRow(year=2024, sector="Finance", avg_salary_qr=25000)
        assert r.year == 2024
        assert r.sector == "Finance"
        assert r.avg_salary_qr == 25000

    def test_avg_salary_row_rejects_negative_salary(self):
        """Test that negative salary is rejected."""
        with pytest.raises(ValidationError):
            AvgSalaryRow(year=2024, sector="Finance", avg_salary_qr=-1000)


class TestAttritionRow:
    """Test AttritionRow model validation."""

    def test_attrition_row_validates(self):
        """Test valid attrition row creation."""
        r = AttritionRow(year=2024, sector="Retail", attrition_percent=12.5)
        assert r.year == 2024
        assert r.sector == "Retail"
        assert r.attrition_percent == 12.5


class TestCompanySizeRow:
    """Test CompanySizeRow model validation."""

    def test_company_size_row_validates(self):
        """Test valid company size row creation."""
        r = CompanySizeRow(year=2024, size_band="50-99", companies=450)
        assert r.year == 2024
        assert r.size_band == "50-99"
        assert r.companies == 450


class TestSectorEmploymentRow:
    """Test SectorEmploymentRow model validation."""

    def test_sector_employment_row_validates(self):
        """Test valid sector employment row creation."""
        r = SectorEmploymentRow(year=2024, sector="Healthcare", employees=25000)
        assert r.year == 2024
        assert r.sector == "Healthcare"
        assert r.employees == 25000


class TestEwiRow:
    """Test EwiRow model validation."""

    def test_ewi_row_validates(self):
        """Test valid EWI row creation."""
        r = EwiRow(year=2024, sector="Construction", drop_percent=5.2)
        assert r.year == 2024
        assert r.sector == "Construction"
        assert r.drop_percent == 5.2

    def test_ewi_row_accepts_zero_drop(self):
        """Test that zero drop percentage is valid."""
        r = EwiRow(year=2024, sector="Education", drop_percent=0.0)
        assert r.drop_percent == 0.0
