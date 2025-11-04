"""Tests for freshness verification."""

from __future__ import annotations

from datetime import datetime

from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    QuerySpec,
    Row,
)
from src.qnwis.data.freshness.verifier import verify_freshness


def test_freshness_no_sla_no_warnings():
    """Test that no warnings are generated when no SLA is set."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"year": 2020})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["year"]
        ),
        freshness=Freshness(asof_date="auto"),
    )
    warnings = verify_freshness(spec, res)
    assert warnings == []


def test_freshness_sla_violation():
    """Test that stale_data warning is generated when SLA is violated."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 30},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"year": 2020})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["year"]
        ),
        freshness=Freshness(asof_date="auto"),
    )
    now = datetime(2025, 1, 1)
    warnings = verify_freshness(spec, res, now=now)
    assert any(w.startswith("stale_data:") for w in warnings)


def test_freshness_sla_passes():
    """Test that no warning when data is fresh enough."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 365},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"date": "2024-12-15"})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["date"]
        ),
        freshness=Freshness(asof_date="auto"),
    )
    now = datetime(2025, 1, 1)
    warnings = verify_freshness(spec, res, now=now)
    assert warnings == []


def test_freshness_unknown_when_no_date():
    """Test that freshness_unknown is returned when as-of date cannot be derived."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 30},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"value": 100})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["value"]
        ),
        freshness=Freshness(asof_date="auto"),
    )
    warnings = verify_freshness(spec, res)
    assert "freshness_unknown" in warnings


def test_freshness_derives_from_year():
    """Test that freshness derives as-of date from year column."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 365},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"year": 2024}), Row(data={"year": 2023})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["year"]
        ),
        freshness=Freshness(asof_date="auto"),
    )
    now = datetime(2025, 6, 1)
    warnings = verify_freshness(spec, res, now=now)
    # Should derive 2024-12-31, which is within 365 days of 2025-06-01
    assert warnings == []


def test_freshness_explicit_asof_date():
    """Test that explicit asof_date is used when provided."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 30},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"year": 2020})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["year"]
        ),
        freshness=Freshness(asof_date="2024-12-15"),
    )
    now = datetime(2025, 1, 1)
    warnings = verify_freshness(spec, res, now=now)
    # 2024-12-15 is within 30 days of 2025-01-01
    assert warnings == []


def test_freshness_year_string_deduces_year_end():
    """Year-only as-of dates are normalized to year-end for SLA checks."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 30},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"value": 1})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["value"]
        ),
        freshness=Freshness(asof_date="2023"),
    )
    now = datetime(2024, 2, 1)
    warnings = verify_freshness(spec, res, now=now)
    assert any(w.startswith("stale_data:32>30") for w in warnings)


def test_freshness_handles_iso_datetime_strings():
    """Datetime strings with Z suffix should parse correctly."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 365},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"date": "2024-12-15T00:00:00Z"})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["date"]
        ),
        freshness=Freshness(asof_date="auto"),
    )
    now = datetime(2025, 1, 1)
    warnings = verify_freshness(spec, res, now=now)
    assert warnings == []


def test_freshness_year_column_float_parses():
    """Year column values as floats are supported."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 365},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"year": "2024.0"})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["year"]
        ),
        freshness=Freshness(asof_date="auto"),
    )
    now = datetime(2025, 6, 1)
    warnings = verify_freshness(spec, res, now=now)
    assert warnings == []


def test_freshness_invalid_sla_value():
    """Invalid SLA constraint produces configuration warning."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": "not-a-number"},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"year": 2024})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["year"]
        ),
        freshness=Freshness(asof_date="auto"),
    )
    warnings = verify_freshness(spec, res)
    assert warnings == ["freshness_invalid_sla"]


def test_freshness_parse_error_warning():
    """Unparseable as-of date triggers parse error warning."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 10},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"value": 1})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["value"]
        ),
        freshness=Freshness(asof_date="not-a-date"),
    )
    warnings = verify_freshness(spec, res)
    assert warnings == ["freshness_parse_error"]


def test_freshness_year_column_string(monkeypatch=None):
    """String year values in rows derive year-end date."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 90},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"year": "2024"})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["year"]
        ),
        freshness=Freshness(asof_date="auto"),
    )
    now = datetime(2024, 3, 31)
    warnings = verify_freshness(spec, res, now=now)
    assert warnings == []


def test_freshness_iso_asof_string():
    """Explicit ISO strings are honoured without warnings."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 10},
    )
    res = QueryResult(
        query_id="q",
        rows=[Row(data={"value": 123})],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="x", locator="x.csv", fields=["value"]
        ),
        freshness=Freshness(asof_date="2024-04-20"),
    )
    now = datetime(2024, 4, 25)
    warnings = verify_freshness(spec, res, now=now)
    assert warnings == []
