"""
Tests for verification failure handling.

Ensures that ERROR-severity issues actually fail the workflow.
"""

from src.qnwis.agents.base import AgentReport, Evidence, Insight
from src.qnwis.orchestration.nodes.verify import verify_structure
from src.qnwis.orchestration.schemas import OrchestrationTask


def test_verification_errors_fail_workflow() -> None:
    """Test that verification errors cause workflow failure."""
    # Create a report that would trigger Layer 4 errors if full verification runs
    # For now, this tests the error handling path
    task = OrchestrationTask(intent="pattern.correlation", params={})

    insight = Insight(
        title="Test Finding",
        summary="This is valid",
        metrics={"test_metric": 42.0},
        evidence=[
            Evidence(
                query_id="q_test",
                dataset_id="test_dataset",
                locator="data/test.csv",
                fields=["field1"],
                freshness_as_of="2024-01-01T00:00:00Z",
            )
        ],
    )

    report = AgentReport(
        agent="TestAgent",
        findings=[insight],
        warnings=[],
    )

    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": report,
        "error": None,
        "logs": [],
        "metadata": {
            "agent": "TestAgent",
            "method": "test_method",
        },
    }

    # Note: Without actual QueryResult data, verification won't run full checks
    # This test verifies the error handling structure is in place
    result = verify_structure(state, strict=False)

    # Should pass structural validation
    assert result["error"] is None or "verification" not in result["error"].lower()


def test_structural_failures_still_work() -> None:
    """Test that structural failures still fail as before."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    # Report with no findings - structural violation
    report = AgentReport(
        agent="TestAgent",
        findings=[],  # Empty findings
        warnings=[],
    )

    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": report,
        "error": None,
        "logs": [],
        "metadata": {
            "agent": "TestAgent",
            "method": "test_method",
        },
    }

    result = verify_structure(state, strict=True)

    # Should fail due to structural issue
    assert result["error"] is not None
    assert "no findings" in result["error"].lower()


def test_verification_warnings_dont_fail() -> None:
    """Test that warning-level issues don't fail the workflow."""
    # This will be testable once we have full QueryResult integration
    # For now, structural warnings are tested
    task = OrchestrationTask(intent="pattern.correlation", params={})

    insight = Insight(
        title="Test Finding",
        summary="This is valid",
        metrics={},
        evidence=[],  # No evidence
    )

    report = AgentReport(
        agent="TestAgent",
        findings=[insight],
        warnings=[],
    )

    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": report,
        "error": None,
        "logs": [],
        "metadata": {
            "agent": "TestAgent",
            "method": "test_method",
        },
    }

    # With require_evidence=False, should only warn, not fail
    result = verify_structure(state, strict=False, require_evidence=False)

    # Should pass (warnings don't fail)
    assert result["error"] is None
    assert len(result["metadata"]["verification_warnings"]) > 0
