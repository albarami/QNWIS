"""Tests for freshness edge cases and error handling."""

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


def _mk_res(data, asof="auto"):
    """Helper to create QueryResult with given data."""
    return QueryResult(
        query_id="q",
        rows=[Row(data=data)],
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id="x",
            locator="x.csv",
            fields=list(data.keys()),
        ),
        freshness=Freshness(asof_date=asof),
    )


def test_freshness_bad_date_string():
    """Invalid date string triggers parse error warning."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 10},
    )
    res = _mk_res({"date": "2021-13-99"})  # invalid date
    w = verify_freshness(spec, res, now=datetime(2025, 1, 1))
    # Should get parse error or unknown
    assert "freshness_parse_error" in w or "freshness_unknown" in w


def test_freshness_string_year_normalized():
    """String year values are parsed correctly."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 365},
    )
    res = _mk_res({"year": "2023"})
    w = verify_freshness(spec, res, now=datetime(2025, 1, 1))
    # 2023-12-31 to 2025-01-01 is about 367 days, should be stale
    assert any(msg.startswith("stale_data:") for msg in w)


def test_freshness_float_year_supported():
    """Float year values (e.g., 2024.0) are supported."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 365},
    )
    res = _mk_res({"year": 2024.0})
    w = verify_freshness(spec, res, now=datetime(2025, 6, 1))
    # 2024-12-31 to 2025-06-01 is about 152 days, should be fresh
    assert w == []


def test_freshness_invalid_sla_value():
    """Invalid SLA constraint produces warning."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": "not-a-number"},
    )
    res = _mk_res({"year": 2024})
    w = verify_freshness(spec, res)
    assert "freshness_invalid_sla" in w


def test_freshness_negative_sla_invalid():
    """Negative SLA days treated as invalid."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": -10},
    )
    res = _mk_res({"year": 2024})
    w = verify_freshness(spec, res)
    assert "freshness_invalid_sla" in w


def test_freshness_explicit_unparseable_date():
    """Explicit unparseable as-of date triggers parse error."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 10},
    )
    res = _mk_res({"value": 1}, asof="not-a-date")
    w = verify_freshness(spec, res)
    assert "freshness_parse_error" in w


def test_freshness_datetime_with_z_suffix():
    """Datetime strings with Z suffix are parsed correctly."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 365},
    )
    res = _mk_res({"date": "2024-12-15T00:00:00Z"})
    w = verify_freshness(spec, res, now=datetime(2025, 1, 1))
    # 2024-12-15 to 2025-01-01 is 17 days, should be fresh
    assert w == []


def test_freshness_year_only_string():
    """Four-digit year string is normalized to year-end."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 30},
    )
    res = _mk_res({"value": 1}, asof="2023")
    w = verify_freshness(spec, res, now=datetime(2024, 2, 1))
    # 2023-12-31 to 2024-02-01 is 32 days
    assert any("stale_data:32>30" in msg for msg in w)


def test_freshness_empty_string_asof():
    """Empty string as-of date triggers parse error or unknown."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 10},
    )
    res = _mk_res({"value": 1}, asof="")
    w = verify_freshness(spec, res)
    # Empty string can trigger parse error or unknown depending on normalization
    assert "freshness_parse_error" in w or "freshness_unknown" in w


def test_freshness_multiple_rows_takes_max_year():
    """When multiple rows have years, uses max year for as-of."""
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
        rows=[
            Row(data={"year": 2020}),
            Row(data={"year": 2024}),
            Row(data={"year": 2022}),
        ],
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id="x",
            locator="x.csv",
            fields=["year"],
        ),
        freshness=Freshness(asof_date="auto"),
    )
    w = verify_freshness(spec, res, now=datetime(2025, 6, 1))
    # Should use 2024-12-31, which is about 152 days old
    assert w == []


def test_freshness_year_below_supported_range():
    """Years below 1000 are ignored leading to unknown freshness."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 30},
    )
    res = _mk_res({"year": 999})
    warnings = verify_freshness(spec, res)
    assert "freshness_unknown" in warnings


def test_freshness_non_numeric_year_string():
    """Non-numeric year strings do not trigger parse errors."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 30},
    )
    res = _mk_res({"year": "twenty-twenty"})
    warnings = verify_freshness(spec, res)
    assert "freshness_unknown" in warnings


def test_freshness_auto_sentinel_skips_parse_error():
    """Explicit 'API' sentinel behaves as auto without warnings."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 30},
    )
    res = _mk_res({"value": 1}, asof="API")
    warnings = verify_freshness(spec, res)
    assert "freshness_parse_error" not in warnings
    assert "freshness_unknown" in warnings


def test_freshness_guess_invalid_asof_triggers_parse(monkeypatch):
    """If guess returns invalid ISO date, parse guard emits warning."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={},
        constraints={"freshness_sla_days": 30},
    )
    res = _mk_res({"value": 1})

    from src.qnwis.data.freshness import verifier as freshness_module

    monkeypatch.setattr(freshness_module, "_guess_asof_date", lambda _: ("2024-13-01", False))

    warnings = verify_freshness(spec, res, now=datetime(2024, 12, 1))
    assert "freshness_parse_error" in warnings
