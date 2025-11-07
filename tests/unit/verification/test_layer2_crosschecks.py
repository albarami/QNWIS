"""Unit tests for Layer 2 cross-check helpers."""

from __future__ import annotations

from time import perf_counter

from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row
from src.qnwis.verification.layer2_crosschecks import cross_check
from src.qnwis.verification.schemas import CrossCheckRule


def _make_query_result(query_id: str, rows: list[dict]) -> QueryResult:
    """Helper to build a minimal QueryResult for tests."""
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


def test_cross_check_equal_values_no_issue() -> None:
    """Identical values, even with case differences in segments, should not raise issues."""
    rule = CrossCheckRule(metric="retention_rate", tolerance_pct=1.0)
    primary = _make_query_result(
        "primary",
        [{"retention_rate": 0.91, "segment": "Construction"}],
    )
    reference = _make_query_result(
        "reference",
        [{"retention_rate": 0.91, "segment": "construction"}],
    )

    issues = cross_check(primary, [reference], [rule])

    assert issues == []


def test_cross_check_within_tolerance() -> None:
    """Differences within tolerance should not emit L2 issues."""
    rule = CrossCheckRule(metric="retention_rate", tolerance_pct=2.0)
    primary = _make_query_result("primary", [{"retention_rate": 0.90, "segment": "Finance"}])
    reference = _make_query_result("reference", [{"retention_rate": 0.918, "segment": "finance"}])

    issues = cross_check(primary, [reference], [rule])

    assert issues == []


def test_cross_check_outside_tolerance_flags_issue() -> None:
    """Large divergences must produce an L2 warning with segment context."""
    rule = CrossCheckRule(metric="retention_rate", tolerance_pct=2.0)
    primary = _make_query_result("primary", [{"retention_rate": 0.80, "segment": "Energy"}])
    reference = _make_query_result("reference", [{"retention_rate": 0.90, "segment": " energy "}])

    issues = cross_check(primary, [reference], [rule])

    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "XCHK_TOLERANCE_EXCEEDED"
    assert issue.details["segment"] == "ENERGY"


def test_cross_check_metric_aliases_match() -> None:
    """Metric aliasing (qatarization -> qatarization_rate) should be supported."""
    rule = CrossCheckRule(metric="qatarization", tolerance_pct=1.0)
    primary = _make_query_result(
        "primary",
        [{"qatarization_rate": 0.35, "segment": "ALL"}],
    )
    reference = _make_query_result(
        "reference",
        [{"qatarization": 0.35, "segment": "all"}],
    )

    issues = cross_check(primary, [reference], [rule])

    assert issues == []


def test_cross_check_defaults_to_all_segment() -> None:
    """Rows without a declared segment should fall back to ALL for comparisons."""
    rule = CrossCheckRule(metric="retention_rate", tolerance_pct=1.0)
    primary = _make_query_result("primary", [{"retention_rate": 0.5}])
    reference = _make_query_result("reference", [{"retention_rate": 0.6}])

    issues = cross_check(primary, [reference], [rule])

    assert issues[0].details["segment"] == "ALL"


def test_cross_check_benchmark_under_20ms() -> None:
    """Ensure the cross-check loop stays under 20ms for typical inputs."""
    rule = CrossCheckRule(metric="retention_rate", tolerance_pct=5.0)
    primary_rows = [
        {"retention_rate": 0.80 + i / 1000, "segment": f"Sector {i}"}
        for i in range(20)
    ]
    reference_rows = [
        {"retention_rate": 0.802 + i / 1000, "segment": f"sector {i}"}
        for i in range(20)
    ]

    primary = _make_query_result("primary", primary_rows)
    reference = _make_query_result("reference", reference_rows)

    start = perf_counter()
    cross_check(primary, [reference], [rule])
    duration_ms = (perf_counter() - start) * 1000

    assert duration_ms <= 20.0, f"Cross-check took {duration_ms:.2f}ms"
