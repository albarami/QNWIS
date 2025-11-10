"""
Unit tests for derived QueryResult wrapper utility.

Tests verify stable query_id generation, provenance tracking, and QueryResult structure.
"""

from __future__ import annotations

from datetime import datetime

from src.qnwis.agents.utils.derived_results import make_derived_query_result
from src.qnwis.data.deterministic.models import Freshness, QueryResult


class TestMakeDerivedQueryResult:
    """Test derived QueryResult creation and structure."""

    def test_basic_creation(self):
        """Should create valid QueryResult with all required fields."""
        result = make_derived_query_result(
            operation="test_operation",
            params={"key": "value"},
            rows=[{"col1": 10, "col2": 20}],
            sources=["query_id_1"],
        )

        assert isinstance(result, QueryResult)
        assert result.query_id.startswith("derived_test_operation_")
        assert len(result.rows) == 1
        assert result.rows[0].data == {"col1": 10, "col2": 20}
        assert result.metadata["operation"] == "test_operation"
        assert result.metadata["params"] == {"key": "value"}
        assert result.metadata["sources"] == ["query_id_1"]
        assert result.metadata["row_count"] == 1

    def test_stable_query_id(self):
        """Same inputs should produce same query_id (deterministic)."""
        params = {"method": "pearson", "threshold": 0.5}

        result1 = make_derived_query_result(
            operation="correlation",
            params=params,
            rows=[{"a": 1}],
            sources=["src1"],
        )

        result2 = make_derived_query_result(
            operation="correlation",
            params=params,
            rows=[{"a": 1}],
            sources=["src1"],
        )

        assert result1.query_id == result2.query_id

    def test_different_params_different_id(self):
        """Different params should produce different query_id."""
        result1 = make_derived_query_result(
            operation="correlation",
            params={"method": "pearson"},
            rows=[],
            sources=[],
        )

        result2 = make_derived_query_result(
            operation="correlation",
            params={"method": "spearman"},
            rows=[],
            sources=[],
        )

        assert result1.query_id != result2.query_id

    def test_different_operation_different_id(self):
        """Different operations should produce different query_id."""
        result1 = make_derived_query_result(
            operation="correlation",
            params={},
            rows=[],
            sources=[],
        )

        result2 = make_derived_query_result(
            operation="anomaly_detection",
            params={},
            rows=[],
            sources=[],
        )

        assert result1.query_id != result2.query_id

    def test_provenance_includes_sources(self):
        """Provenance locator should list source query IDs."""
        result = make_derived_query_result(
            operation="merge",
            params={},
            rows=[],
            sources=["query_a", "query_b", "query_c"],
        )

        assert "query_a" in result.provenance.locator
        assert "query_b" in result.provenance.locator
        assert "query_c" in result.provenance.locator

    def test_provenance_operation_documented(self):
        """Provenance should document the operation performed."""
        result = make_derived_query_result(
            operation="z_score_analysis",
            params={},
            rows=[],
            sources=["src"],
        )

        assert "z_score_analysis" in result.provenance.locator

    def test_empty_sources(self):
        """Should handle empty sources list."""
        result = make_derived_query_result(
            operation="synthetic",
            params={},
            rows=[{"value": 42}],
            sources=[],
        )

        assert result.provenance.locator
        assert "none" in result.provenance.locator.lower()

    def test_multiple_rows(self):
        """Should handle multiple data rows."""
        rows = [
            {"sector": "Finance", "value": 10.5},
            {"sector": "Energy", "value": 8.3},
            {"sector": "Healthcare", "value": 12.1},
        ]

        result = make_derived_query_result(
            operation="ranking",
            params={},
            rows=rows,
            sources=["src"],
        )

        assert len(result.rows) == 3
        assert result.rows[0].data["sector"] == "Finance"
        assert result.rows[2].data["value"] == 12.1

    def test_empty_rows(self):
        """Should handle empty rows list."""
        result = make_derived_query_result(
            operation="filtering",
            params={"threshold": 100},
            rows=[],
            sources=["src"],
        )

        assert result.rows == []
        assert result.provenance.fields == []

    def test_unit_parameter(self):
        """Should accept and use custom unit."""
        result = make_derived_query_result(
            operation="aggregation",
            params={},
            rows=[],
            sources=[],
            unit="percent",
        )

        assert result.unit == "percent"

    def test_default_unit_unknown(self):
        """Default unit should be 'unknown'."""
        result = make_derived_query_result(
            operation="test",
            params={},
            rows=[],
            sources=[],
        )

        assert result.unit == "unknown"

    def test_freshness_with_timestamps(self):
        """Should use oldest timestamp when freshness_like provided."""
        timestamps = {
            "source_a": datetime(2024, 1, 15),
            "source_b": datetime(2024, 1, 10),  # Oldest
            "source_c": datetime(2024, 1, 20),
        }

        result = make_derived_query_result(
            operation="merge",
            params={},
            rows=[],
            sources=["a", "b", "c"],
            freshness_like=timestamps,
        )

        assert result.freshness.asof_date == "2024-01-10"
        assert result.freshness.updated_at is not None

    def test_freshness_from_sources(self):
        """Should pass through asof/update metadata from Freshness inputs."""
        freshness_inputs = [
            Freshness(asof_date="2024-02-01", updated_at="2024-02-02T00:00:00"),
            Freshness(asof_date="2024-01-20", updated_at="2024-01-21T00:00:00"),
        ]

        result = make_derived_query_result(
            operation="merge",
            params={},
            rows=[],
            sources=["a", "b"],
            freshness_like=freshness_inputs,
        )

        assert result.freshness.asof_date == "2024-01-20"
        assert result.freshness.updated_at.startswith("2024-02-02")

    def test_freshness_without_timestamps(self):
        """Should use current date when no freshness_like provided."""
        result = make_derived_query_result(
            operation="test",
            params={},
            rows=[],
            sources=[],
        )

        # Should have today's date
        assert result.freshness.asof_date
        assert "-" in result.freshness.asof_date  # ISO format

    def test_fields_extracted_from_first_row(self):
        """Provenance fields should come from first row keys."""
        rows = [
            {"field_a": 1, "field_b": 2, "field_c": 3},
            {"field_a": 4, "field_b": 5, "field_c": 6},
        ]

        result = make_derived_query_result(
            operation="test",
            params={},
            rows=rows,
            sources=[],
        )

        assert set(result.provenance.fields) == {"field_a", "field_b", "field_c"}

    def test_dataset_id_format(self):
        """Dataset ID should be 'derived_{operation}'."""
        result = make_derived_query_result(
            operation="my_custom_operation",
            params={},
            rows=[],
            sources=[],
        )

        assert result.provenance.dataset_id == "derived_my_custom_operation"

    def test_source_type_csv(self):
        """Source type should be 'csv' (marker for computed data)."""
        result = make_derived_query_result(
            operation="test",
            params={},
            rows=[],
            sources=[],
        )

        assert result.provenance.source == "csv"

    def test_license_documented(self):
        """License should indicate computed from QNWIS layer."""
        result = make_derived_query_result(
            operation="test",
            params={},
            rows=[],
            sources=[],
        )

        assert "QNWIS" in result.provenance.license
        assert "deterministic" in result.provenance.license.lower()

    def test_warnings_empty_by_default(self):
        """Warnings should be empty list by default."""
        result = make_derived_query_result(
            operation="test",
            params={},
            rows=[],
            sources=[],
        )

        assert result.warnings == []

    def test_complex_params_in_query_id(self):
        """Complex params should be stably encoded in query_id."""
        params = {
            "method": "spearman",
            "threshold": 2.5,
            "min_samples": 10,
        }

        result1 = make_derived_query_result("test", params, [], [])
        result2 = make_derived_query_result("test", params, [], [])

        assert result1.query_id == result2.query_id

        # Order shouldn't matter
        params_reordered = {
            "threshold": 2.5,
            "min_samples": 10,
            "method": "spearman",
        }
        result3 = make_derived_query_result("test", params_reordered, [], [])
        assert result1.query_id == result3.query_id

    def test_query_id_hash_length(self):
        """Query ID hash should be 8 characters."""
        result = make_derived_query_result(
            operation="test_op",
            params={"key": "value"},
            rows=[],
            sources=[],
        )

        # Format: derived_{operation}_{hash8}
        parts = result.query_id.split("_")
        hash_part = parts[-1]
        assert len(hash_part) == 8

    def test_integration_example(self):
        """Integration example: correlation analysis result."""
        result = make_derived_query_result(
            operation="spearman_correlation",
            params={
                "variable_x": "qatarization_percent",
                "variable_y": "attrition_percent",
            },
            rows=[
                {"sector": "Finance", "qat": 45.2, "atr": 8.3, "rho": 0.68},
                {"sector": "Energy", "qat": 67.1, "atr": 4.2, "rho": 0.68},
            ],
            sources=["syn_qatarization_by_sector_latest", "syn_attrition_by_sector_latest"],
            unit="percent",
        )

        assert "spearman_correlation" in result.query_id
        assert len(result.rows) == 2
        # Provenance locator contains source query IDs
        assert "syn_qatarization_by_sector_latest" in result.provenance.locator
        assert "syn_attrition_by_sector_latest" in result.provenance.locator
        assert result.unit == "percent"
