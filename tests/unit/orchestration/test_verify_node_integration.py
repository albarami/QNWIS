"""Tests for orchestration verify node integrations."""

from __future__ import annotations

from typing import Any

import pytest

from src.qnwis.agents.base import AgentReport, Evidence, Insight
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row
from src.qnwis.orchestration.nodes import verify as verify_module
from src.qnwis.orchestration.nodes.verify import verify_structure
from src.qnwis.orchestration.schemas import OrchestrationTask
from src.qnwis.verification.schemas import (
    Issue,
    PrivacyRule,
    VerificationConfig,
    VerificationSummary,
)


def _qr(query_id: str, rows: list[dict[str, Any]]) -> QueryResult:
    return QueryResult(
        query_id=query_id,
        rows=[Row(data=row) for row in rows],
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id=f"{query_id}_dataset",
            locator=f"data/{query_id}.csv",
            fields=list(rows[0].keys()) if rows else [],
        ),
        freshness=Freshness(asof_date="2024-01-01"),
        warnings=[],
    )


def _report() -> AgentReport:
    evidence_primary = Evidence(
        query_id="q_primary",
        dataset_id="ds_primary",
        locator="data/q_primary.csv",
        fields=["retention_rate", "segment"],
        freshness_as_of="2024-01-01T00:00:00Z",
    )
    evidence_ref = Evidence(
        query_id="q_reference",
        dataset_id="ds_reference",
        locator="data/q_reference.csv",
        fields=["retention_rate", "segment"],
        freshness_as_of="2024-01-01T00:00:00Z",
    )
    insight = Insight(
        title="Test",
        summary="Summary body",
        metrics={"retention_rate": 0.9},
        evidence=[evidence_primary, evidence_ref],
    )
    return AgentReport(agent="TestAgent", findings=[insight], warnings=[])


def test_verify_node_attaches_summary_and_reasons(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify node should pass verification summary metadata to downstream nodes."""
    config = VerificationConfig(
        crosschecks=[],
        privacy=PrivacyRule(),
        sanity=[],
        freshness_max_hours=72,
    )
    monkeypatch.setattr(verify_module, "_load_verification_config", lambda: config)
    monkeypatch.setattr(verify_module, "_load_citation_rules", lambda: None)

    fake_summary = VerificationSummary(
        ok=True,
        issues=[],
        redacted_text="clean body",
        applied_redactions=2,
        stats={"L3:warning": 2},
        summary_md="Status: PASS",
        redaction_reason_codes=["PII_EMAIL", "PII_ID"],
    )

    class DummyEngine:
        def __init__(
            self,
            cfg: VerificationConfig,
            user_roles: list[str] | None = None,
            citation_rules: Any | None = None,
        ) -> None:
            self.cfg = cfg
            self.user_roles = user_roles or []
            self.citation_rules = citation_rules

        def run_with_agent_report(
            self,
            narrative_md: str,
            query_results: list[QueryResult],
        ) -> VerificationSummary:
            assert narrative_md
            assert query_results
            return fake_summary

    monkeypatch.setattr(verify_module, "VerificationEngine", DummyEngine)

    prefetch_cache = {
        "primary": _qr("q_primary", [{"retention_rate": 0.9, "segment": "ALL"}]),
        "reference": _qr("q_reference", [{"retention_rate": 0.92, "segment": "ALL"}]),
    }

    task = OrchestrationTask(intent="pattern.correlation", params={})
    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": _report(),
        "error": None,
        "logs": [],
        "metadata": {
            "agent": "TestAgent",
            "method": "run",
        },
        "prefetch_cache": prefetch_cache,
    }

    result = verify_structure(state, strict=False)

    assert result["error"] is None
    metadata = result["metadata"]
    assert metadata["verification_summary_md"] == "Status: PASS"
    assert metadata["verification_redaction_codes"] == ["PII_EMAIL", "PII_ID"]
    assert metadata["verification_redactions"] == 2
    assert metadata["verification_available"] is True
    logs = result["logs"]
    assert any("Verification summary attached" in entry for entry in logs)


def test_verify_node_warning_issues_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Warnings should annotate metadata but not fail verification."""
    config = VerificationConfig(
        crosschecks=[],
        privacy=PrivacyRule(),
        sanity=[],
        freshness_max_hours=72,
    )
    monkeypatch.setattr(verify_module, "_load_verification_config", lambda: config)
    monkeypatch.setattr(verify_module, "_load_citation_rules", lambda: None)

    warning_issue = Issue(
        layer="L2",
        code="MISSING_QID",
        message="QID optional for this metric",
        severity="warning",
        details={},
    )
    fake_summary = VerificationSummary(
        ok=True,
        issues=[warning_issue],
        redacted_text="body",
        applied_redactions=0,
        stats={"L2:warning": 1},
        summary_md="Status: PASS",
    )

    class DummyEngine:
        def __init__(
            self,
            cfg: VerificationConfig,
            user_roles: list[str] | None = None,
            citation_rules: Any | None = None,
        ) -> None:
            self.cfg = cfg
            self.user_roles = user_roles or []
            self.citation_rules = citation_rules

        def run_with_agent_report(
            self,
            narrative_md: str,
            query_results: list[QueryResult],
        ) -> VerificationSummary:
            return fake_summary

    monkeypatch.setattr(verify_module, "VerificationEngine", DummyEngine)

    prefetch_cache = {
        "primary": _qr("q_primary", [{"value": 1}]),
        "reference": _qr("q_reference", [{"value": 1}]),
    }
    task = OrchestrationTask(intent="pattern.correlation", params={})
    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": _report(),
        "error": None,
        "logs": [],
        "metadata": {"agent": "TestAgent", "method": "run"},
        "prefetch_cache": prefetch_cache,
    }

    result = verify_structure(state, strict=False)
    assert result["error"] is None
    metadata = result["metadata"]
    assert metadata["verification_available"] is True
    issues = metadata["verification_issues"]
    assert issues[0]["severity"] == "warning"


def test_verify_node_errors_fail_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Error-severity issues should fail the workflow."""
    config = VerificationConfig(
        crosschecks=[],
        privacy=PrivacyRule(),
        sanity=[],
        freshness_max_hours=72,
    )
    monkeypatch.setattr(verify_module, "_load_verification_config", lambda: config)
    monkeypatch.setattr(verify_module, "_load_citation_rules", lambda: None)

    error_issue = Issue(
        layer="L2",
        code="UNCITED_NUMBER",
        message="Missing source",
        severity="error",
        details={},
    )
    fake_summary = VerificationSummary(
        ok=False,
        issues=[error_issue],
        redacted_text="body",
        applied_redactions=0,
        stats={"L2:error": 1},
    )

    class DummyEngine:
        def __init__(
            self,
            cfg: VerificationConfig,
            user_roles: list[str] | None = None,
            citation_rules: Any | None = None,
        ) -> None:
            self.cfg = cfg
            self.user_roles = user_roles or []
            self.citation_rules = citation_rules

        def run_with_agent_report(
            self,
            narrative_md: str,
            query_results: list[QueryResult],
        ) -> VerificationSummary:
            return fake_summary

    monkeypatch.setattr(verify_module, "VerificationEngine", DummyEngine)

    prefetch_cache = {
        "primary": _qr("q_primary", [{"value": 1}]),
        "reference": _qr("q_reference", [{"value": 1}]),
    }
    task = OrchestrationTask(intent="pattern.correlation", params={})
    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": _report(),
        "error": None,
        "logs": [],
        "metadata": {"agent": "TestAgent", "method": "run"},
        "prefetch_cache": prefetch_cache,
    }

    result = verify_structure(state, strict=False)
    assert result["error"].startswith("Verification failed with 1 error")
    metadata = result["metadata"]
    assert metadata["verification_available"] is True
