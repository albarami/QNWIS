"""Unit tests for Layer 4 sanity checks."""

from __future__ import annotations

from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row
from src.qnwis.verification.layer4_sanity import sanity_checks
from src.qnwis.verification.schemas import SanityRule


def _qr(query_id: str, rows: list[dict]) -> QueryResult:
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


def test_negative_values_are_flagged() -> None:
    """must_be_non_negative should emit NEGATIVE_VALUE issues."""
    rules = [SanityRule(metric="headcount", must_be_non_negative=True)]
    result = _qr("q1", [{"headcount": -5}])

    issues = sanity_checks([result], rules, freshness_max_hours=72)

    assert any(issue.code == "NEGATIVE_VALUE" for issue in issues)


def test_rate_bounds_enforced() -> None:
    """rate_0_1 should clamp metrics to the [0,1] interval."""
    rules = [SanityRule(metric="retention_rate", rate_0_1=True)]
    result = _qr("q1", [{"retention_rate": 1.2}, {"retention_rate": -0.1}])

    issues = sanity_checks([result], rules, freshness_max_hours=72)

    codes = [issue.code for issue in issues]
    assert codes.count("RATE_OUT_OF_RANGE") == 2
