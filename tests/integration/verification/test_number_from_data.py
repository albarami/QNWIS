"""
Integration tests for number verification from data.

Tests that pipeline rejects fabricated metrics with clear warnings.
"""

import pytest
from src.qnwis.llm.parser import LLMResponseParser, AgentFinding
from src.qnwis.data.deterministic.models import QueryResult, Row, Provenance


def test_reject_fabricated_metric():
    """Test that fabricated metrics are rejected."""
    parser = LLMResponseParser()
    
    # Create finding with fabricated metric
    finding = AgentFinding(
        title="Fabricated Finding",
        summary="This contains made-up numbers.",
        metrics={"fabricated_rate": 99.99},  # Not in source data
        analysis="The fabricated rate of 99.99% is alarming.",
        recommendations=[],
        confidence=0.9,
        citations=[],
        data_quality_notes=""
    )
    
    # Create allowed numbers from real data
    provenance = Provenance(
        source_id="test",
        api_version="v1",
        query_timestamp="2025-01-15T10:00:00Z"
    )
    
    query_results = {
        "real_query": QueryResult(
            query_id="real_query",
            rows=[
                Row(row_id="r1", data={"real_rate": 5.5, "count": 1000})
            ],
            total_rows=1,
            provenance=provenance
        )
    }
    
    allowed_numbers = parser.extract_numbers_from_query_results(query_results)
    
    # Validate - should fail
    is_valid, violations = parser.validate_numbers(finding, allowed_numbers)
    
    assert not is_valid, "Should reject fabricated metrics"
    assert len(violations) > 0, "Should have violation warnings"
    assert any("99.99" in v for v in violations), "Should mention fabricated value"


def test_accept_valid_metric_from_data():
    """Test that metrics from actual data are accepted."""
    parser = LLMResponseParser()
    
    # Create finding with metrics from source data
    finding = AgentFinding(
        title="Valid Finding",
        summary="This uses real numbers from data.",
        metrics={"unemployment_rate": 5.5},  # In source data
        analysis="The unemployment rate is 5.5%.",
        recommendations=[],
        confidence=0.9,
        citations=[],
        data_quality_notes=""
    )
    
    # Create allowed numbers from real data
    provenance = Provenance(
        source_id="test",
        api_version="v1",
        query_timestamp="2025-01-15T10:00:00Z"
    )
    
    query_results = {
        "real_query": QueryResult(
            query_id="real_query",
            rows=[
                Row(row_id="r1", data={"unemployment_rate": 5.5, "count": 1000})
            ],
            total_rows=1,
            provenance=provenance
        )
    }
    
    allowed_numbers = parser.extract_numbers_from_query_results(query_results)
    
    # Validate - should pass
    is_valid, violations = parser.validate_numbers(finding, allowed_numbers)
    
    assert is_valid, f"Should accept valid metrics, got violations: {violations}"
    assert len(violations) == 0


def test_clear_warning_message_for_fabrication():
    """Test that fabrication violations have clear warning messages."""
    parser = LLMResponseParser()
    
    finding = AgentFinding(
        title="Test",
        summary="Summary",
        metrics={"fake": 999.0},
        analysis="Analysis",
        recommendations=[],
        confidence=0.9,
        citations=[],
        data_quality_notes=""
    )
    
    allowed = {1.0, 2.0, 3.0}
    
    is_valid, violations = parser.validate_numbers(finding, allowed)
    
    assert not is_valid
    assert len(violations) > 0
    
    # Violation should be clear and actionable
    violation_text = violations[0]
    assert "fake" in violation_text.lower() or "999" in violation_text
    assert "not found" in violation_text.lower() or "source data" in violation_text.lower()
