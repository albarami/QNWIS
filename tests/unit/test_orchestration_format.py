"""
Unit tests for the orchestration format node.
"""

from __future__ import annotations

from src.qnwis.agents.base import AgentReport, Evidence, Insight
from src.qnwis.orchestration.metrics import NullMetricsObserver
from src.qnwis.orchestration.nodes.format import format_report
from src.qnwis.orchestration.schemas import OrchestrationTask


def test_format_report_redacts_and_enriches_metadata() -> None:
    """Formatter should redact PII, compute freshness, and redact sensitive params."""
    task = OrchestrationTask(
        intent="pattern.anomalies",
        params={"user_token": "super-secret", "sector": "Finance"},
    )

    evidence = Evidence(
        query_id="q_example",
        dataset_id="employment_dataset",
        locator="/data/employment.csv",
        fields=["sector", "attrition_rate"],
        freshness_as_of="2025-01-01",
        freshness_updated_at="2025-01-01T00:00:00Z",
    )

    report = AgentReport(
        agent="MockAgent",
        findings=[
            Insight(
                title="John Doe Attrition Spike",
                summary="John Doe observed a rise in attrition to 15%.",
                metrics={"attrition_rate": 15.0},
                evidence=[evidence],
            )
        ],
        warnings=[],
    )

    state = {
        "task": task,
        "route": task.intent,
        "agent_output": report,
        "logs": [],
        "metadata": {"agent": "MockAgent", "method": "run_analysis"},
    }

    result_state = format_report(
        state,
        formatting_config={"top_evidence": 1, "max_citations": 1, "max_findings": 1},
        observer=NullMetricsObserver(),
    )

    assert "error" not in result_state
    result = result_state["agent_output"]

    assert result.sections[0].title == "Executive Summary"
    assert "[REDACTED_NAME]" in result.sections[0].body_md
    assert result.reproducibility.params["user_token"] == "[REDACTED]"
    assert "employment_dataset" in result.freshness
    assert result.citations[0].query_id == "q_example"
