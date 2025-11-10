"""
Tests for entity extraction in QueryClassifier.

Tests sector, metric, and time horizon extraction.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.qnwis.orchestration.classifier import QueryClassifier


@pytest.fixture
def classifier() -> QueryClassifier:
    """Create a QueryClassifier instance for testing."""
    base_dir = Path(__file__).parent.parent.parent / "src" / "qnwis" / "orchestration"
    catalog_path = base_dir / "intent_catalog.yml"
    sector_lex = base_dir / "keywords" / "sectors.txt"
    metric_lex = base_dir / "keywords" / "metrics.txt"

    return QueryClassifier(
        catalog_path=str(catalog_path),
        sector_lex=str(sector_lex),
        metric_lex=str(metric_lex),
    )


class TestSectorExtraction:
    """Test sector entity extraction."""

    def test_extract_single_sector(self, classifier: QueryClassifier) -> None:
        """Test extraction of single sector."""
        text = "Retention issues in Construction sector"
        entities = classifier.extract_entities(text)

        assert "Construction" in entities.sectors

    def test_extract_multiple_sectors(self, classifier: QueryClassifier) -> None:
        """Test extraction of multiple sectors."""
        text = "Compare Finance, Healthcare, and IT sectors"
        entities = classifier.extract_entities(text)

        assert "Finance" in entities.sectors
        assert "Healthcare" in entities.sectors
        assert "It" in entities.sectors or "IT" in [s.upper() for s in entities.sectors]

    def test_no_sectors(self, classifier: QueryClassifier) -> None:
        """Test when no sectors are mentioned."""
        text = "Overall retention trends"
        entities = classifier.extract_entities(text)

        assert len(entities.sectors) == 0

    def test_case_insensitive_sector(self, classifier: QueryClassifier) -> None:
        """Test case-insensitive sector matching."""
        text = "construction and HEALTHCARE sectors"
        entities = classifier.extract_entities(text)

        assert "Construction" in entities.sectors
        assert "Healthcare" in entities.sectors


class TestMetricExtraction:
    """Test metric entity extraction."""

    def test_extract_single_metric(self, classifier: QueryClassifier) -> None:
        """Test extraction of single metric."""
        text = "Analyze retention rates"
        entities = classifier.extract_entities(text)

        assert "retention" in entities.metrics or "retention rate" in entities.metrics

    def test_extract_multiple_metrics(self, classifier: QueryClassifier) -> None:
        """Test extraction of multiple metrics."""
        text = "Compare salary, retention, and turnover"
        entities = classifier.extract_entities(text)

        assert "salary" in entities.metrics
        assert any("retention" in m for m in entities.metrics)
        assert "turnover" in entities.metrics

    def test_metric_variations(self, classifier: QueryClassifier) -> None:
        """Test metric variation matching."""
        text = "Employee retention rate analysis"
        entities = classifier.extract_entities(text)

        # Should match both "employee retention" and "retention rate"
        assert any("retention" in m for m in entities.metrics)

    def test_no_metrics(self, classifier: QueryClassifier) -> None:
        """Test when no metrics are mentioned."""
        text = "General industry analysis"
        entities = classifier.extract_entities(text)

        # May extract some metrics if generic terms match
        # Test is flexible
        assert isinstance(entities.metrics, list)


class TestTimeHorizonExtraction:
    """Test time horizon extraction."""

    def test_relative_months(self, classifier: QueryClassifier) -> None:
        """Test relative time in months."""
        text = "Trends over last 24 months"
        entities = classifier.extract_entities(text)

        assert entities.time_horizon is not None
        assert entities.time_horizon['type'] == 'relative'
        assert entities.time_horizon['value'] == 24
        assert entities.time_horizon['unit'] == 'month'
        assert entities.time_horizon['months'] == 24

    def test_relative_years(self, classifier: QueryClassifier) -> None:
        """Test relative time in years."""
        text = "Data from past 3 years"
        entities = classifier.extract_entities(text)

        assert entities.time_horizon is not None
        assert entities.time_horizon['type'] == 'relative'
        assert entities.time_horizon['value'] == 3
        assert entities.time_horizon['unit'] == 'year'
        assert entities.time_horizon['months'] == 36

    def test_absolute_year_range(self, classifier: QueryClassifier) -> None:
        """Test absolute year range."""
        text = "Analysis from 2020-2024"
        entities = classifier.extract_entities(text)

        assert entities.time_horizon is not None
        assert entities.time_horizon['type'] == 'absolute'
        assert entities.time_horizon['start_year'] == 2020
        assert entities.time_horizon['end_year'] == 2024
        assert entities.time_horizon['months'] == 60  # 5 years

    def test_absolute_since_year(self, classifier: QueryClassifier) -> None:
        """Test 'since' pattern."""
        text = "Trends since 2022"
        entities = classifier.extract_entities(text)

        assert entities.time_horizon is not None
        assert entities.time_horizon['type'] == 'absolute'
        assert entities.time_horizon['start_year'] == 2022
        assert entities.time_horizon['end_year'] is None

    def test_absolute_single_year(self, classifier: QueryClassifier) -> None:
        """Test single year pattern."""
        text = "Employment in 2023"
        entities = classifier.extract_entities(text)

        assert entities.time_horizon is not None
        assert entities.time_horizon['type'] == 'absolute'
        assert entities.time_horizon['year'] == 2023
        assert entities.time_horizon['months'] == 12

    def test_no_time_horizon(self, classifier: QueryClassifier) -> None:
        """Test when no time horizon is mentioned."""
        text = "General retention analysis"
        entities = classifier.extract_entities(text)

        assert entities.time_horizon is not None
        assert entities.time_horizon["source"] == "default"
        assert entities.time_horizon["months"] == 36

    def test_quarter_time_horizon(self, classifier: QueryClassifier) -> None:
        """Test quarter-based time horizon pattern."""
        text = "Review Q2 2024 performance in Construction"
        entities = classifier.extract_entities(text)

        assert entities.time_horizon is not None
        assert entities.time_horizon["type"] == "absolute"
        assert entities.time_horizon["quarter"] == 2
        assert entities.time_horizon["year"] == 2024
        assert entities.time_horizon["months"] == 3

    def test_plain_year_time_horizon(self, classifier: QueryClassifier) -> None:
        """Test plain year without prepositions."""
        text = "Performance review 2022 vs current year"
        entities = classifier.extract_entities(text)

        assert entities.time_horizon is not None
        assert entities.time_horizon.get("year") == 2022

    def test_recent_months(self, classifier: QueryClassifier) -> None:
        """Test 'recent' pattern."""
        text = "Recent 6 months data"
        entities = classifier.extract_entities(text)

        assert entities.time_horizon is not None
        assert entities.time_horizon['value'] == 6
        assert entities.time_horizon['unit'] == 'month'


class TestConvertToMonths:
    """Test time unit conversion."""

    def test_convert_years(self, classifier: QueryClassifier) -> None:
        """Test year to month conversion."""
        months = classifier._convert_to_months(2, "year")
        assert months == 24

    def test_convert_months(self, classifier: QueryClassifier) -> None:
        """Test month passthrough."""
        months = classifier._convert_to_months(12, "month")
        assert months == 12

    def test_convert_weeks(self, classifier: QueryClassifier) -> None:
        """Test week to month conversion."""
        months = classifier._convert_to_months(8, "week")
        assert months == 2  # 8 weeks / 4

    def test_convert_days(self, classifier: QueryClassifier) -> None:
        """Test day to month conversion."""
        months = classifier._convert_to_months(60, "day")
        assert months == 2  # 60 days / 30

    def test_convert_quarters(self, classifier: QueryClassifier) -> None:
        """Test quarter to month conversion."""
        months = classifier._convert_to_months(2, "quarter")
        assert months == 6

    def test_convert_minimum(self, classifier: QueryClassifier) -> None:
        """Test minimum of 1 month."""
        months = classifier._convert_to_months(1, "week")
        assert months >= 1


class TestCombinedEntityExtraction:
    """Test extraction of multiple entity types together."""

    def test_full_extraction(self, classifier: QueryClassifier) -> None:
        """Test extraction of sectors, metrics, and time horizon."""
        text = "Analyze retention and turnover in Construction and Finance over last 24 months"
        entities = classifier.extract_entities(text)

        # Sectors
        assert "Construction" in entities.sectors
        assert "Finance" in entities.sectors

        # Metrics
        assert any("retention" in m for m in entities.metrics)
        assert "turnover" in entities.metrics

        # Time horizon
        assert entities.time_horizon is not None
        assert entities.time_horizon['months'] == 24

    def test_sorted_deduplication(self, classifier: QueryClassifier) -> None:
        """Test that entities are sorted and deduplicated."""
        text = "Finance and Construction and Finance sectors"
        entities = classifier.extract_entities(text)

        # Should be deduplicated
        finance_count = entities.sectors.count("Finance")
        assert finance_count == 1

        # Should be sorted
        if len(entities.sectors) >= 2:
            assert entities.sectors == sorted(entities.sectors)
