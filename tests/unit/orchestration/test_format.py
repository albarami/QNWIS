"""
Unit tests for format node.

Tests cover:
- PII redaction (names, emails, IDs)
- Section order stability
- TOP-N truncation with "... and N more" messaging
- Citation deduplication
- Freshness metadata extraction
"""



from src.qnwis.agents.base import AgentReport, Evidence, Insight
from src.qnwis.orchestration.nodes.format import format_report
from src.qnwis.orchestration.schemas import OrchestrationResult, OrchestrationTask


def create_report_with_pii() -> AgentReport:
    """Create a report with PII for redaction testing."""
    insight1 = Insight(
        title="Analysis for John Smith",
        summary="Employee John Smith (john.smith@example.com) has ID 1234567890123",
        metrics={"employee_count": 1},
        evidence=[
            Evidence(
                query_id="q_pii",
                dataset_id="employees",
                locator="data/employees.csv",
                fields=["name", "email", "id"],
                freshness_as_of="2024-01-01T00:00:00Z",
            )
        ],
    )

    return AgentReport(
        agent="TestAgent",
        findings=[insight1],
        warnings=[],
    )


def create_report_with_many_findings(count: int) -> AgentReport:
    """Create a report with many findings for truncation testing."""
    findings = []
    for i in range(count):
        insight = Insight(
            title=f"Finding {i+1}",
            summary=f"This is finding number {i+1}",
            metrics={f"metric_{i}": float(i)},
            evidence=[
                Evidence(
                    query_id=f"q_{i}",
                    dataset_id=f"dataset_{i}",
                    locator=f"data/file_{i}.csv",
                    fields=["field1"],
                    freshness_as_of="2024-01-01T00:00:00Z",
                )
            ],
        )
        findings.append(insight)

    return AgentReport(
        agent="TestAgent",
        findings=findings,
        warnings=[],
    )


def test_format_pii_redaction_names() -> None:
    """Test that PII names are redacted."""
    task = OrchestrationTask(intent="pattern.correlation", params={})
    report = create_report_with_pii()

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

    result = format_report(state)

    # Should have formatted result
    assert result["error"] is None
    formatted = result["agent_output"]
    assert isinstance(formatted, OrchestrationResult)

    # Check that name is redacted in sections
    all_text = " ".join(section.body_md for section in formatted.sections)
    assert "John Smith" not in all_text
    assert "[REDACTED_NAME]" in all_text


def test_format_pii_redaction_emails() -> None:
    """Test that PII emails are redacted."""
    task = OrchestrationTask(intent="pattern.correlation", params={})
    report = create_report_with_pii()

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

    result = format_report(state)

    formatted = result["agent_output"]
    all_text = " ".join(section.body_md for section in formatted.sections)

    # Email should be redacted
    assert "john.smith@example.com" not in all_text
    assert "[REDACTED_EMAIL]" in all_text


def test_format_pii_redaction_long_ids() -> None:
    """Test that long numeric IDs (10+ digits) are redacted."""
    task = OrchestrationTask(intent="pattern.correlation", params={})
    report = create_report_with_pii()

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

    result = format_report(state)

    formatted = result["agent_output"]
    all_text = " ".join(section.body_md for section in formatted.sections)

    # Long ID should be redacted
    assert "1234567890123" not in all_text
    assert "[REDACTED_ID]" in all_text


def test_format_section_order_stable() -> None:
    """Test that sections appear in consistent order."""
    task = OrchestrationTask(intent="pattern.correlation", params={})
    report = create_report_with_many_findings(3)

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

    result = format_report(state)

    formatted = result["agent_output"]
    section_titles = [section.title for section in formatted.sections]

    # Verify expected order
    assert section_titles[0] == "Executive Summary"
    assert section_titles[1] == "Key Findings"
    assert section_titles[2] == "Evidence (Top Sources)"


def test_format_truncation_with_message() -> None:
    """Test that TOP-N truncation adds '... and N more' message."""
    task = OrchestrationTask(intent="pattern.correlation", params={})
    report = create_report_with_many_findings(15)  # More than max_findings

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

    # Configure to show max 10 findings
    config = {"max_findings": 10}
    result = format_report(state, formatting_config=config)

    formatted = result["agent_output"]

    # Find Key Findings section
    key_findings = next(s for s in formatted.sections if s.title == "Key Findings")

    # Should have truncation message
    assert "5 additional findings omitted" in key_findings.body_md

    # Should only have 10 findings in the text
    finding_count = key_findings.body_md.count("### ")
    assert finding_count == 10


def test_format_evidence_truncation() -> None:
    """Test that evidence is truncated with omission message."""
    task = OrchestrationTask(intent="pattern.correlation", params={})
    report = create_report_with_many_findings(20)  # Lots of evidence

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

    # Configure to show top 5 evidence items
    config = {"top_evidence": 5}
    result = format_report(state, formatting_config=config)

    formatted = result["agent_output"]

    # Find Evidence section
    evidence_section = next(s for s in formatted.sections if "Evidence" in s.title)

    # Should have omission message
    assert "additional sources omitted" in evidence_section.body_md


def test_format_citations_deduplication() -> None:
    """Test that citations are deduplicated by query_id."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    # Create findings with duplicate evidence query_ids
    insight1 = Insight(
        title="Finding 1",
        summary="First finding",
        metrics={},
        evidence=[
            Evidence(
                query_id="q_shared",
                dataset_id="dataset1",
                locator="data/file1.csv",
                fields=["field1"],
                freshness_as_of="2024-01-01T00:00:00Z",
            )
        ],
    )

    insight2 = Insight(
        title="Finding 2",
        summary="Second finding",
        metrics={},
        evidence=[
            Evidence(
                query_id="q_shared",  # Same query_id
                dataset_id="dataset1",
                locator="data/file1.csv",
                fields=["field1"],
                freshness_as_of="2024-01-01T00:00:00Z",
            )
        ],
    )

    report = AgentReport(
        agent="TestAgent",
        findings=[insight1, insight2],
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

    result = format_report(state)

    formatted = result["agent_output"]

    # Should only have one citation for the shared query_id
    assert len(formatted.citations) == 1
    assert formatted.citations[0].query_id == "q_shared"


def test_format_freshness_extraction() -> None:
    """Test that freshness metadata is correctly extracted."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    insight = Insight(
        title="Test Finding",
        summary="Test",
        metrics={},
        evidence=[
            Evidence(
                query_id="q_test",
                dataset_id="test_dataset",
                locator="data/test.csv",
                fields=["field1"],
                freshness_as_of="2024-01-15T12:00:00Z",
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

    result = format_report(state)

    formatted = result["agent_output"]

    # Should have freshness for the dataset
    assert "test_dataset" in formatted.freshness
    freshness_entry = formatted.freshness["test_dataset"]
    assert freshness_entry.source == "test_dataset"
    assert "2024-01-15" in freshness_entry.last_updated
    assert freshness_entry.age_days is not None


def test_format_missing_agent_output_fails() -> None:
    """Test that format fails gracefully with missing output."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": None,  # Missing output
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = format_report(state)

    # Should have error
    assert result["error"] is not None
    assert "No agent output to format" in result["error"]


def test_format_missing_task_fails() -> None:
    """Test that format fails with missing task."""
    report = create_report_with_many_findings(3)

    state = {
        "task": None,  # Missing task
        "route": "pattern.correlation",
        "agent_output": report,
        "error": None,
        "logs": [],
        "metadata": {
            "agent": "TestAgent",
            "method": "test_method",
        },
    }

    result = format_report(state)

    # Should have error
    assert result["error"] is not None
    assert "No task available for formatting" in result["error"]


def test_format_reproducibility_metadata() -> None:
    """Test that reproducibility metadata is included."""
    task = OrchestrationTask(
        intent="pattern.correlation",
        params={"sector": "Construction", "months": 24},
    )

    insight = Insight(
        title="Test",
        summary="Test",
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
            "method": "find_correlations",
        },
    }

    result = format_report(state)

    formatted = result["agent_output"]

    # Should have reproducibility metadata
    repro = formatted.reproducibility
    assert repro.method == "TestAgent.find_correlations"
    assert "sector" in repro.params
    assert "months" in repro.params
    assert repro.params["sector"] == "Construction"
    assert repro.params["months"] == 24


def test_format_warnings_combined() -> None:
    """Test that verification warnings are combined with agent warnings."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    report = AgentReport(
        agent="TestAgent",
        findings=[
            Insight(
                title="Test",
                summary="Test",
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
        ],
        warnings=["Agent warning 1", "Agent warning 2"],
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
            "verification_warnings": ["Verification warning"],
        },
    }

    result = format_report(state)

    formatted = result["agent_output"]

    # Should combine all warnings
    assert len(formatted.warnings) == 3
    assert "Agent warning 1" in formatted.warnings
    assert "Agent warning 2" in formatted.warnings
    assert "Verification warning" in formatted.warnings


def test_format_metric_redaction() -> None:
    """Test that metrics with sensitive keys are redacted."""
    task = OrchestrationTask(intent="pattern.correlation", params={})

    insight = Insight(
        title="Test",
        summary="Test",
        metrics={
            "employee_name": 123,  # Should be redacted
            "user_id": 456,  # Should be redacted
            "total_count": 789,  # Should NOT be redacted
        },
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

    result = format_report(state)

    formatted = result["agent_output"]

    # Find Key Findings section
    key_findings = next(s for s in formatted.sections if s.title == "Key Findings")

    # Sensitive metrics should be redacted
    assert "[REDACTED]" in key_findings.body_md
    # Non-sensitive metric should be visible
    assert "789" in key_findings.body_md
