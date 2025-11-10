"""Tests for agent evidence formatting and verification utilities."""

import pytest

from src.qnwis.agents.base import AgentReport, Evidence, Insight
from src.qnwis.agents.utils.evidence import format_evidence_table
from src.qnwis.agents.utils.verification import AgentResponseVerifier, AgentVerificationError
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


def test_format_evidence_table_truncates_with_ellipsis():
    rows = [{"rank": idx + 1, "value": float(idx)} for idx in range(12)]
    formatted = format_evidence_table(rows, max_rows=10)
    assert len(formatted) == 11  # top 10 plus ellipsis row
    assert formatted[-1]["rank"] == "... and 2 more"
    assert list(formatted[0].keys()) == ["rank", "value"]


def test_format_evidence_table_respects_column_order():
    rows = [{"b": 2, "a": 1}]
    formatted = format_evidence_table(rows, column_order=["a", "b"])
    assert list(formatted[0].keys()) == ["a", "b"]


def test_format_evidence_table_requires_positive_max_rows():
    with pytest.raises(ValueError):
        format_evidence_table([{"a": 1}], max_rows=0)


def test_agent_response_verifier_flags_unknown_evidence():
    verifier = AgentResponseVerifier()
    report = AgentReport(
        agent="TestAgent",
        findings=[
            Insight(
                title="Mismatch",
                summary="Testing verification mismatch.",
                evidence=[Evidence(query_id="unknown", dataset_id="x", locator="x.csv", fields=[])],
            )
        ],
    )
    result = QueryResult(
        query_id="known",
        rows=[Row(data={"value": 1})],
        unit="count",
        provenance=Provenance(source="csv", dataset_id="known", locator="known.csv", fields=["value"]),
        freshness=Freshness(asof_date="2024-01-01"),
    )

    with pytest.raises(AgentVerificationError):
        verifier.verify(report, [result])
