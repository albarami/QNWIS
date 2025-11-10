"""
Unit tests for orchestration schemas.

Tests pydantic models for task inputs and result outputs.
"""

import pytest
from pydantic import ValidationError

from src.qnwis.orchestration.schemas import (
    Citation,
    Freshness,
    OrchestrationResult,
    OrchestrationTask,
    ReportSection,
    Reproducibility,
    WorkflowState,
)


def test_orchestration_task_minimal():
    """Test creating minimal task."""
    task = OrchestrationTask(intent="pattern.anomalies")

    assert task.intent == "pattern.anomalies"
    assert task.params == {}
    assert task.user_id is None
    assert task.request_id is None


def test_orchestration_task_full():
    """Test creating complete task."""
    task = OrchestrationTask(
        intent="pattern.correlation",
        params={"sector": "Construction", "months": 36},
        user_id="analyst@mol.qa",
        request_id="REQ-001",
    )

    assert task.intent == "pattern.correlation"
    assert task.params == {"sector": "Construction", "months": 36}
    assert task.user_id == "analyst@mol.qa"
    assert task.request_id == "REQ-001"


def test_orchestration_task_invalid_intent():
    """Test that invalid intent raises validation error."""
    with pytest.raises(ValidationError):
        OrchestrationTask(intent="invalid.intent")


def test_report_section():
    """Test creating report section."""
    section = ReportSection(
        title="Executive Summary",
        body_md="This is a **markdown** summary.",
    )

    assert section.title == "Executive Summary"
    assert "**markdown**" in section.body_md


def test_citation():
    """Test creating citation."""
    citation = Citation(
        query_id="q_employment_2023",
        dataset_id="employment",
        locator="/data/employment.csv",
        fields=["year", "count"],
        timestamp="2025-01-06T10:00:00Z",
    )

    assert citation.query_id == "q_employment_2023"
    assert citation.dataset_id == "employment"
    assert len(citation.fields) == 2


def test_freshness():
    """Test creating freshness metadata."""
    fresh = Freshness(
        source="employment_db",
        last_updated="2025-01-01T00:00:00Z",
        age_days=5.2,
    )

    assert fresh.source == "employment_db"
    assert fresh.age_days == 5.2


def test_reproducibility():
    """Test creating reproducibility metadata."""
    repro = Reproducibility(
        method="PatternDetective.find_correlations",
        params={"sector": "Construction"},
        timestamp="2025-01-06T10:00:00Z",
    )

    assert repro.method == "PatternDetective.find_correlations"
    assert repro.params["sector"] == "Construction"


def test_orchestration_result_success():
    """Test creating successful result."""
    section = ReportSection(title="Summary", body_md="Success!")
    citation = Citation(
        query_id="q_test",
        dataset_id="test",
        locator="/test",
        fields=["field1"],
    )
    repro = Reproducibility(
        method="test",
        params={},
        timestamp="2025-01-06T10:00:00Z",
    )

    result = OrchestrationResult(
        ok=True,
        intent="pattern.anomalies",
        sections=[section],
        citations=[citation],
        freshness={},
        reproducibility=repro,
        request_id="REQ-001",
    )

    assert result.ok is True
    assert result.intent == "pattern.anomalies"
    assert len(result.sections) == 1
    assert len(result.citations) == 1
    assert result.request_id == "REQ-001"
    assert result.timestamp  # Auto-generated


def test_orchestration_result_with_warnings():
    """Test creating result with warnings."""
    section = ReportSection(title="Summary", body_md="Warning!")
    repro = Reproducibility(method="test", params={}, timestamp="2025-01-06T10:00:00Z")

    result = OrchestrationResult(
        ok=True,
        intent="pattern.anomalies",
        sections=[section],
        citations=[],
        freshness={},
        reproducibility=repro,
        warnings=["Data may be stale", "Missing some fields"],
    )

    assert len(result.warnings) == 2
    assert "Data may be stale" in result.warnings


def test_orchestration_result_error():
    """Test creating error result."""
    section = ReportSection(title="Error", body_md="Failed!")
    repro = Reproducibility(method="error", params={}, timestamp="2025-01-06T10:00:00Z")

    result = OrchestrationResult(
        ok=False,
        intent="pattern.anomalies",
        sections=[section],
        citations=[],
        freshness={},
        reproducibility=repro,
        warnings=["Agent execution failed"],
    )

    assert result.ok is False
    assert len(result.warnings) == 1


def test_workflow_state():
    """Test creating workflow state."""
    task = OrchestrationTask(intent="pattern.anomalies")

    state = WorkflowState(
        task=task,
        route="pattern.anomalies",
        logs=["Started", "Routed"],
        metadata={"elapsed_ms": 123},
    )

    assert state.task.intent == "pattern.anomalies"
    assert state.route == "pattern.anomalies"
    assert len(state.logs) == 2
    assert state.metadata["elapsed_ms"] == 123
    assert state.error is None
    assert state.agent_output is None


def test_orchestration_task_invalid_year_range():
    """start_year must be less than or equal to end_year."""
    with pytest.raises(ValidationError):
        OrchestrationTask(
            intent="pattern.anomalies",
            params={"start_year": 2025, "end_year": 2024},
        )


def test_orchestration_task_invalid_top_n():
    """top_n must be an integer within the allowed bounds."""
    with pytest.raises(ValidationError):
        OrchestrationTask(
            intent="pattern.anomalies",
            params={"top_n": 0},
        )
    with pytest.raises(ValidationError):
        OrchestrationTask(
            intent="pattern.anomalies",
            params={"top_n": 999},
        )


def test_orchestration_task_invalid_months():
    """months parameter must match the allowed window sizes."""
    with pytest.raises(ValidationError):
        OrchestrationTask(
            intent="pattern.anomalies",
            params={"months": 18},
        )
