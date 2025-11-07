"""
Integration tests for verification engine.

Tests the complete workflow from config loading through
all three verification layers.
"""

import pytest

from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.verification import (
    CrossCheckRule,
    PrivacyRule,
    SanityRule,
    VerificationConfig,
    VerificationEngine,
)


def create_test_query_result(
    query_id: str,
    data_rows: list[dict],
    asof_date: str = "2024-01-01",
) -> QueryResult:
    """Create a test QueryResult."""
    return QueryResult(
        query_id=query_id,
        rows=[Row(data=row) for row in data_rows],
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id="test_dataset",
            locator="data/test.csv",
            fields=list(data_rows[0].keys()) if data_rows else [],
        ),
        freshness=Freshness(asof_date=asof_date),
        warnings=[],
    )


def test_verification_engine_basic_flow() -> None:
    """Test basic verification engine flow."""
    config = VerificationConfig(
        crosschecks=[],
        privacy=PrivacyRule(redact_email=True, redact_ids_min_digits=10),
        sanity=[],
        freshness_max_hours=72,
    )

    engine = VerificationEngine(config, user_roles=[])

    narrative = "Test narrative with john.doe@example.com and ID 1234567890"
    primary = create_test_query_result("q1", [{"value": 100}])

    summary = engine.run(narrative, primary, [])

    # Should have redactions
    assert summary.applied_redactions > 0
    assert "[REDACTED_EMAIL]" in summary.redacted_text
    assert "[REDACTED_ID]" in summary.redacted_text

    # Should have PII issues
    assert any(issue.code == "PII_EMAIL" for issue in summary.issues)
    assert any(issue.code == "PII_ID" for issue in summary.issues)
    assert "PII_EMAIL" in summary.redaction_reason_codes
    assert summary.summary_md is not None


def test_cross_check_layer() -> None:
    """Test Layer 2 cross-check functionality."""
    config = VerificationConfig(
        crosschecks=[
            CrossCheckRule(metric="retention_rate", tolerance_pct=2.0, prefer="LMIS")
        ],
        privacy=PrivacyRule(redact_email=False),
        sanity=[],
        freshness_max_hours=720,
    )

    engine = VerificationEngine(config)

    # Primary has retention_rate = 0.85
    primary = create_test_query_result(
        "q_primary", [{"retention_rate": 0.85, "segment": "ALL"}]
    )

    # Reference has retention_rate = 0.90 (5.88% difference - exceeds 2%)
    reference = create_test_query_result(
        "q_ref", [{"retention_rate": 0.90, "segment": "ALL"}]
    )

    narrative = "Test narrative"
    summary = engine.run(narrative, primary, [reference])

    # Should have cross-check issue
    xchk_issues = [i for i in summary.issues if i.layer == "L2"]
    assert len(xchk_issues) > 0
    assert xchk_issues[0].code == "XCHK_TOLERANCE_EXCEEDED"
    assert "retention_rate" in xchk_issues[0].message.lower()


def test_sanity_checks_layer() -> None:
    """Test Layer 4 sanity checks."""
    config = VerificationConfig(
        crosschecks=[],
        privacy=PrivacyRule(redact_email=False),
        sanity=[
            SanityRule(metric="retention_rate", rate_0_1=True),
            SanityRule(metric="headcount", must_be_non_negative=True),
        ],
        freshness_max_hours=24,
    )

    engine = VerificationEngine(config)

    # Invalid data: retention_rate > 1.0, negative headcount, old data
    primary = create_test_query_result(
        "q_bad",
        [
            {"retention_rate": 1.5, "headcount": -10, "segment": "ALL"},
        ],
        asof_date="2020-01-01",  # Very old
    )

    narrative = "Test narrative"
    summary = engine.run(narrative, primary, [])

    # Should have multiple issues
    assert not summary.ok  # Should fail due to errors
    assert len(summary.issues) >= 3

    # Check for specific issues
    codes = {issue.code for issue in summary.issues}
    assert "RATE_OUT_OF_RANGE" in codes
    assert "NEGATIVE_VALUE" in codes
    assert "STALE_DATA" in codes


def test_rbac_role_based_redaction() -> None:
    """Test that RBAC roles affect name redaction."""
    config = VerificationConfig(
        privacy=PrivacyRule(
            redact_email=True,
            allow_names_when_role=["allow_names"],
        ),
        crosschecks=[],
        sanity=[],
        freshness_max_hours=720,
    )

    narrative = "Contact John Smith at john@example.com"

    # Without allow_names role
    engine_restricted = VerificationEngine(config, user_roles=[])
    primary = create_test_query_result("q1", [{"value": 1}])
    summary_restricted = engine_restricted.run(narrative, primary, [])

    # Should redact both email and name
    assert "[REDACTED_EMAIL]" in summary_restricted.redacted_text
    assert "[REDACTED_NAME]" in summary_restricted.redacted_text

    # With allow_names role
    engine_privileged = VerificationEngine(config, user_roles=["allow_names"])
    summary_privileged = engine_privileged.run(narrative, primary, [])

    # Should still redact email, but name handling depends on implementation
    assert "[REDACTED_EMAIL]" in summary_privileged.redacted_text
    assert "[REDACTED_NAME]" not in summary_privileged.redacted_text
    assert "PII_NAME" not in summary_privileged.redaction_reason_codes


def test_issue_severity_classification() -> None:
    """Test that issues are classified by severity correctly."""
    config = VerificationConfig(
        crosschecks=[CrossCheckRule(metric="test_metric", tolerance_pct=1.0)],
        privacy=PrivacyRule(redact_email=True),
        sanity=[SanityRule(metric="test_metric", rate_0_1=True)],
        freshness_max_hours=720,
    )

    engine = VerificationEngine(config)

    # Data with rate violation (error) and PII (warning)
    primary = create_test_query_result(
        "q1", [{"test_metric": 2.0, "segment": "ALL"}]  # Out of [0,1] bounds
    )

    narrative = "Contact admin@example.com for details"
    summary = engine.run(narrative, primary, [])

    # Should have both warnings and errors
    warnings = [i for i in summary.issues if i.severity == "warning"]
    errors = [i for i in summary.issues if i.severity == "error"]

    assert len(warnings) > 0  # PII redaction
    assert len(errors) > 0  # Rate violation

    # Overall status should be not OK due to errors
    assert not summary.ok


def test_empty_results_handling() -> None:
    """Test that empty query results are handled gracefully."""
    config = VerificationConfig(
        crosschecks=[],
        privacy=PrivacyRule(redact_email=True),
        sanity=[],
        freshness_max_hours=72,
    )

    engine = VerificationEngine(config)

    narrative = "Test with no data"
    summary = engine.run_with_agent_report(narrative, [])

    # Should succeed with no issues
    assert summary.ok
    assert len(summary.issues) == 0
    assert summary.applied_redactions == 0


def test_stats_aggregation() -> None:
    """Test that issue stats are aggregated correctly by layer and severity."""
    config = VerificationConfig(
        crosschecks=[CrossCheckRule(metric="value", tolerance_pct=1.0)],
        privacy=PrivacyRule(redact_email=True),
        sanity=[SanityRule(metric="value", must_be_non_negative=True)],
        freshness_max_hours=720,
    )

    engine = VerificationEngine(config)

    # Create data that will trigger multiple issues
    primary = create_test_query_result("q1", [{"value": -5, "segment": "ALL"}])
    reference = create_test_query_result("q2", [{"value": 10, "segment": "ALL"}])

    narrative = "Email: test@example.com, another@example.com"
    summary = engine.run(narrative, primary, [reference])

    # Check stats structure
    assert isinstance(summary.stats, dict)
    assert "L2:warning" in summary.stats or "L3:warning" in summary.stats
    assert sum(summary.stats.values()) == len(summary.issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
