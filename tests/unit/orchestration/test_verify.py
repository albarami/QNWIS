"""
Unit tests for verify node.

Tests cover:
- Valid AgentReport structure passes verification
- Missing sections generate warnings or errors per config
- Evidence and freshness requirements
- Citation metadata validation
"""

from src.qnwis.agents.base import AgentReport, Evidence, Insight
from src.qnwis.orchestration.nodes.verify import verify_structure
from src.qnwis.orchestration.schemas import OrchestrationTask


def create_valid_report() -> AgentReport:
    """Create a valid agent report for testing."""
    insight = Insight(
        title="Test Finding",
        summary="This is a test finding with proper structure",
        metrics={"test_metric": 42.0},
        evidence=[
            Evidence(
                query_id="q_test",
                dataset_id="test_dataset",
                locator="data/test.csv",
                fields=["field1", "field2"],
                freshness_as_of="2024-01-01T00:00:00Z",
                freshness_updated_at="2024-01-01T00:00:00Z",
            )
        ],
    )

    return AgentReport(
        agent="TestAgent",
        findings=[insight],
        warnings=[],
    )


def test_verify_valid_structure_passes() -> None:
    """Test that a valid AgentReport passes verification."""
    task = OrchestrationTask(intent="pattern.correlation", params={})
    report = create_valid_report()

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

    result = verify_structure(state, strict=False)

    # Should pass verification
    assert result["error"] is None
    assert "verification_warnings" in result["metadata"]
    assert len(result["metadata"]["verification_warnings"]) == 0

    # Should have success log
    assert any("PASSED" in log for log in result["logs"])


def test_verify_missing_findings_fails() -> None:
    """Test that missing findings triggers validation failure."""
    task = OrchestrationTask(intent="pattern.correlation", params={})
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

    # Should fail
    assert result["error"] is not None
    assert "no findings" in result["error"].lower()


def test_verify_missing_evidence_with_requirement() -> None:
    """Test that missing evidence fails when required."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    insight = Insight(
        title="Finding without evidence",
        summary="This has no evidence",
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

    result = verify_structure(state, strict=True, require_evidence=True)

    # Should fail
    assert result["error"] is not None
    assert "evidence" in result["error"].lower()


def test_verify_missing_evidence_as_warning() -> None:
    """Test that missing evidence generates warning when not required."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    insight = Insight(
        title="Finding without evidence",
        summary="This has no evidence",
        metrics={},
        evidence=[],
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

    result = verify_structure(state, strict=False, require_evidence=False)

    # Should pass but with warnings
    assert result["error"] is None
    warnings = result["metadata"]["verification_warnings"]
    assert len(warnings) > 0
    assert any("evidence" in w.lower() for w in warnings)


def test_verify_missing_freshness_fails_when_required() -> None:
    """Test that missing freshness metadata fails when required."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    insight = Insight(
        title="Finding with no freshness",
        summary="Evidence lacks freshness",
        metrics={},
        evidence=[
            Evidence(
                query_id="q_test",
                dataset_id="test_dataset",
                locator="data/test.csv",
                fields=["field1"],
                freshness_as_of=None,  # No freshness
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

    result = verify_structure(state, strict=True, require_freshness=True)

    # Should fail
    assert result["error"] is not None
    assert "freshness" in result["error"].lower()


def test_verify_missing_title_fails() -> None:
    """Test that missing finding title fails verification."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    insight = Insight(
        title="",  # Empty title
        summary="Has summary but no title",
        metrics={},
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

    result = verify_structure(state, strict=True)

    # Should fail
    assert result["error"] is not None
    assert "title" in result["error"].lower()


def test_verify_missing_summary_fails() -> None:
    """Test that missing finding summary fails verification."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    insight = Insight(
        title="Has title",
        summary="",  # Empty summary
        metrics={},
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

    result = verify_structure(state, strict=True)

    # Should fail
    assert result["error"] is not None
    assert "summary" in result["error"].lower()


def test_verify_missing_query_id_fails() -> None:
    """Test that missing query_id in evidence fails."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    insight = Insight(
        title="Test",
        summary="Test",
        metrics={},
        evidence=[
            Evidence(
                query_id="",  # Empty query_id
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

    result = verify_structure(state, strict=True)

    # Should fail
    assert result["error"] is not None
    assert "query_id" in result["error"].lower()


def test_verify_missing_dataset_id_fails() -> None:
    """Test that missing dataset_id in evidence fails."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    insight = Insight(
        title="Test",
        summary="Test",
        metrics={},
        evidence=[
            Evidence(
                query_id="q_test",
                dataset_id="",  # Empty dataset_id
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

    result = verify_structure(state, strict=True)

    # Should fail
    assert result["error"] is not None
    assert "dataset_id" in result["error"].lower()


def test_verify_invalid_output_type_fails() -> None:
    """Test that non-AgentReport output fails."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": {"invalid": "output"},  # Wrong type
        "error": None,
        "logs": [],
        "metadata": {
            "agent": "TestAgent",
            "method": "test_method",
        },
    }

    result = verify_structure(state, strict=False)

    # Should fail
    assert result["error"] is not None
    assert "not an AgentReport" in result["error"]


def test_verify_missing_agent_output_fails() -> None:
    """Test that missing agent_output fails."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": None,  # No output
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = verify_structure(state, strict=False)

    # Should fail
    assert result["error"] is not None
    assert "No agent output to verify" in result["error"]


def test_verify_missing_invocation_metadata_fails() -> None:
    """Test that missing invocation metadata fails."""
    task = OrchestrationTask(intent="pattern.correlation", params={})
    report = create_valid_report()

    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": report,
        "error": None,
        "logs": [],
        "metadata": {},  # Missing agent/method
    }

    result = verify_structure(state, strict=True)

    # Should fail
    assert result["error"] is not None
    assert "metadata missing" in result["error"].lower()


def test_verify_with_agent_warnings() -> None:
    """Test that agent warnings are logged but don't fail verification."""
    task = OrchestrationTask(intent="pattern.correlation", params={})
    report = create_valid_report()
    report.warnings = ["Data quality issue", "Potential outlier"]

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

    result = verify_structure(state, strict=False)

    # Should pass despite warnings
    assert result["error"] is None

    # Should have verification warnings metadata
    assert "verification_warnings" in result["metadata"]
