"""
Unit tests for LLM response parser.

Tests JSON extraction, number validation, and malformed input rejection.
"""

import pytest
from src.qnwis.llm.parser import LLMResponseParser, AgentFinding, LLMParseError
from src.qnwis.data.deterministic.models import QueryResult, Row, Provenance


def test_parse_clean_json():
    """Test parsing clean JSON response."""
    parser = LLMResponseParser()

    response = """{
        "title": "Employment Analysis",
        "summary": "Employment has grown significantly.",
        "metrics": {"growth_rate": 5.2},
        "analysis": "Detailed analysis here.",
        "recommendations": ["Recommendation 1"],
        "confidence": 0.85,
        "citations": ["query_1"],
        "data_quality_notes": "High quality data."
    }"""

    finding = parser.parse_agent_response(response)

    assert finding.title == "Employment Analysis"
    assert finding.confidence == 0.85
    assert "growth_rate" in finding.metrics
    assert finding.metrics["growth_rate"] == 5.2


def test_parse_json_in_markdown_code_block():
    """Test extracting JSON from markdown code block."""
    parser = LLMResponseParser()

    response = """
Here's my analysis:

```json
{
    "title": "Test Finding",
    "summary": "Summary text.",
    "metrics": {"value": 42.0},
    "analysis": "Analysis text.",
    "recommendations": [],
    "confidence": 0.9,
    "citations": [],
    "data_quality_notes": ""
}
```

That's the result.
"""

    finding = parser.parse_agent_response(response)

    assert finding.title == "Test Finding"
    assert finding.metrics["value"] == 42.0
    assert finding.confidence == 0.9


def test_parse_json_embedded_in_text():
    """Test extracting JSON embedded in explanatory text."""
    parser = LLMResponseParser()

    response = """
I've analyzed the data and here's what I found:
{"title": "Finding", "summary": "Summary", "metrics": {}, "analysis": "Analysis", "recommendations": [], "confidence": 0.8, "citations": [], "data_quality_notes": ""}
As you can see, the findings are significant.
"""

    finding = parser.parse_agent_response(response)

    assert finding.title == "Finding"
    assert finding.confidence == 0.8


def test_parse_rejects_malformed_json():
    """Test parser rejects malformed JSON."""
    parser = LLMResponseParser()

    malformed = """{
        "title": "Test",
        "summary": "Missing closing brace",
        "confidence": 0.5
    """

    with pytest.raises(LLMParseError):
        parser.parse_agent_response(malformed)


def test_parse_rejects_missing_required_fields():
    """Test parser rejects JSON missing required fields."""
    parser = LLMResponseParser()

    incomplete = """{
        "title": "Test",
        "summary": "Missing other fields"
    }"""

    with pytest.raises(LLMParseError):
        parser.parse_agent_response(incomplete)


def test_parse_rejects_no_json():
    """Test parser rejects response with no JSON."""
    parser = LLMResponseParser()

    text_only = "This is just plain text with no JSON structure."

    with pytest.raises(LLMParseError, match="No JSON found"):
        parser.parse_agent_response(text_only)


def test_extract_numbers_from_text():
    """Test number extraction from text."""
    parser = LLMResponseParser()

    text = "The rate is 5.2%, with 1,234 total and 42 new cases."

    numbers = parser.extract_numbers(text)

    assert 5.2 in numbers
    assert 1234.0 in numbers
    assert 42.0 in numbers


def test_extract_numbers_handles_commas():
    """Test number extraction with comma thousands separators."""
    parser = LLMResponseParser()

    text = "Total: 1,234,567 units"

    numbers = parser.extract_numbers(text)

    assert 1234567.0 in numbers


def test_validate_numbers_accepts_valid_metrics():
    """Test number validation accepts valid metrics."""
    parser = LLMResponseParser()

    finding = AgentFinding(
        title="Test",
        summary="Summary",
        metrics={"value": 42.0},
        analysis="Analysis with 42 mentioned.",
        recommendations=[],
        confidence=0.9,
        citations=[],
        data_quality_notes=""
    )

    allowed = {42.0, 100.0, 5.2}

    is_valid, violations = parser.validate_numbers(finding, allowed)

    assert is_valid
    assert len(violations) == 0


def test_validate_numbers_rejects_hallucinated_metrics():
    """Test number validation rejects hallucinated metrics."""
    parser = LLMResponseParser()

    finding = AgentFinding(
        title="Test",
        summary="Summary",
        metrics={"fake_value": 999.0},  # Not in allowed set
        analysis="Analysis",
        recommendations=[],
        confidence=0.9,
        citations=[],
        data_quality_notes=""
    )

    allowed = {42.0, 100.0, 5.2}

    is_valid, violations = parser.validate_numbers(finding, allowed)

    assert not is_valid
    assert len(violations) > 0
    assert "fake_value" in violations[0]
    assert "999" in violations[0]


def test_validate_numbers_checks_analysis_text():
    """Test number validation checks analysis text."""
    parser = LLMResponseParser()

    finding = AgentFinding(
        title="Test",
        summary="Summary",
        metrics={},
        analysis="The value is 999 which is significant.",  # 999 not allowed
        recommendations=[],
        confidence=0.9,
        citations=[],
        data_quality_notes=""
    )

    allowed = {42.0, 100.0, 5.2}

    is_valid, violations = parser.validate_numbers(finding, allowed)

    assert not is_valid
    assert any("999" in v for v in violations)


def test_validate_numbers_with_tolerance():
    """Test number validation uses tolerance for floating point."""
    parser = LLMResponseParser()

    finding = AgentFinding(
        title="Test",
        summary="Summary",
        metrics={"value": 42.01},  # Slightly different from 42.0
        analysis="Analysis",
        recommendations=[],
        confidence=0.9,
        citations=[],
        data_quality_notes=""
    )

    allowed = {42.0}

    # Should pass with default tolerance
    is_valid, violations = parser.validate_numbers(finding, allowed, tolerance=0.01)

    assert is_valid


def test_extract_numbers_from_query_results():
    """Test extracting numbers from QueryResult objects."""
    parser = LLMResponseParser()

    provenance = Provenance(
        source_id="test_source",
        api_version="v1",
        query_timestamp="2025-01-15T10:00:00Z"
    )

    query_results = {
        "query1": QueryResult(
            query_id="query1",
            rows=[
                Row(row_id="r1", data={"value": 42.0, "rate": 5.2}),
                Row(row_id="r2", data={"value": 100.0, "rate": 3.1})
            ],
            total_rows=2,
            provenance=provenance
        )
    }

    numbers = parser.extract_numbers_from_query_results(query_results)

    assert 42.0 in numbers
    assert 5.2 in numbers
    assert 100.0 in numbers
    assert 3.1 in numbers


def test_agent_finding_validates_confidence_bounds():
    """Test AgentFinding validates confidence is 0-1."""
    with pytest.raises(ValueError, match="Confidence must be between"):
        AgentFinding(
            title="Test",
            summary="Summary",
            metrics={},
            analysis="Analysis",
            recommendations=[],
            confidence=1.5,  # Invalid
            citations=[],
            data_quality_notes=""
        )


def test_agent_finding_validates_metric_types():
    """Test AgentFinding validates metrics are numeric."""
    with pytest.raises(ValueError, match="must be numeric"):
        AgentFinding(
            title="Test",
            summary="Summary",
            metrics={"bad_metric": "not a number"},  # Invalid
            analysis="Analysis",
            recommendations=[],
            confidence=0.9,
            citations=[],
            data_quality_notes=""
        )
