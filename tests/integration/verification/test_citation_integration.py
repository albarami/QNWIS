"""Integration tests for citation enforcement in verification pipeline."""

from __future__ import annotations

import pytest

from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.verification.engine import VerificationEngine
from src.qnwis.verification.schemas import CitationRules, VerificationConfig


@pytest.fixture
def citation_rules() -> CitationRules:
    """Create citation rules for testing."""
    return CitationRules(
        allowed_prefixes=[
            "Per LMIS:",
            "According to GCC-STAT:",
        ],
        require_query_id=True,
        ignore_years=True,
        ignore_numbers_below=1.0,
        source_mapping={
            "Per LMIS:": ["LMIS", "lmis"],
            "According to GCC-STAT:": ["GCC-STAT", "gcc_stat"],
        },
    )


@pytest.fixture
def verification_config() -> VerificationConfig:
    """Create minimal verification config."""
    return VerificationConfig(
        crosschecks=[],
        sanity=[],
        freshness_max_hours=72,
    )


@pytest.fixture
def lmis_query_result() -> QueryResult:
    """Create LMIS query result."""
    return QueryResult(
        query_id="lmis_ret_2024q3",
        rows=[Row(data={"retention_rate": 0.875})],
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id="LMIS_retention",
            locator="/data/lmis_retention.csv",
            fields=["retention_rate"],
        ),
        freshness=Freshness(
            asof_date="2024-09-30",
            updated_at="2024-10-01T00:00:00Z",
        ),
    )


@pytest.fixture
def gcc_query_result() -> QueryResult:
    """Create GCC-STAT query result."""
    return QueryResult(
        query_id="gcc_emp_2024q3",
        rows=[Row(data={"employment_count": 12500})],
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id="GCC-STAT_employment",
            locator="/data/gcc_employment.csv",
            fields=["employment_count"],
        ),
        freshness=Freshness(
            asof_date="2024-09-30",
            updated_at="2024-10-01T00:00:00Z",
        ),
    )


class TestCitationEnforcementIntegration:
    """Integration tests for citation enforcement."""

    def test_valid_citations_pass_verification(
        self,
        citation_rules,
        verification_config,
        lmis_query_result,
    ):
        """Test that valid citations pass full verification."""
        narrative = (
            "## Retention Analysis\n\n"
            "Per LMIS: The retention rate improved to 87.5% in Q3 2024 "
            "(QID: lmis_ret_2024q3)."
        )

        engine = VerificationEngine(
            verification_config,
            user_roles=[],
            citation_rules=citation_rules,
        )

        summary = engine.run_with_agent_report(narrative, [lmis_query_result])

        assert summary.ok is True
        assert summary.citation_report is not None
        assert summary.citation_report.ok is True
        assert summary.citation_report.total_numbers == 1
        assert summary.citation_report.cited_numbers == 1

    def test_uncited_claims_fail_verification(
        self,
        citation_rules,
        verification_config,
        lmis_query_result,
    ):
        """Test that uncited claims fail verification."""
        narrative = (
            "## Retention Analysis\n\n"
            "The retention rate improved to 87.5% in Q3 2024."
        )

        engine = VerificationEngine(
            verification_config,
            user_roles=[],
            citation_rules=citation_rules,
        )

        summary = engine.run_with_agent_report(narrative, [lmis_query_result])

        assert summary.ok is False
        assert summary.citation_report is not None
        assert summary.citation_report.ok is False
        assert len(summary.citation_report.uncited) == 1
        # Should have ERROR issues
        error_issues = [i for i in summary.issues if i.severity == "error"]
        assert len(error_issues) > 0

    def test_missing_qid_fails_verification(
        self,
        citation_rules,
        verification_config,
        lmis_query_result,
    ):
        """Test that missing QID fails verification."""
        narrative = (
            "## Retention Analysis\n\n"
            "Per LMIS: The retention rate improved to 87.5% in Q3 2024."
        )

        engine = VerificationEngine(
            verification_config,
            user_roles=[],
            citation_rules=citation_rules,
        )

        summary = engine.run_with_agent_report(narrative, [lmis_query_result])

        assert summary.ok is False
        assert summary.citation_report is not None
        assert len(summary.citation_report.missing_qid) == 1

    def test_multiple_sources(
        self,
        citation_rules,
        verification_config,
        lmis_query_result,
        gcc_query_result,
    ):
        """Test citations from multiple sources."""
        narrative = (
            "## Employment Analysis\n\n"
            "Per LMIS: The retention rate is 87.5% (QID: lmis_ret_2024q3). "
            "According to GCC-STAT: Regional employment grew by 12,500 positions "
            "(QID: gcc_emp_2024q3)."
        )

        engine = VerificationEngine(
            verification_config,
            user_roles=[],
            citation_rules=citation_rules,
        )

        summary = engine.run_with_agent_report(
            narrative, [lmis_query_result, gcc_query_result]
        )

        assert summary.ok is True
        assert summary.citation_report is not None
        assert summary.citation_report.total_numbers == 2
        assert summary.citation_report.cited_numbers == 2
        assert len(summary.citation_report.sources_used) == 2

    def test_unknown_source_fails(
        self,
        citation_rules,
        verification_config,
    ):
        """Test that unknown sources fail verification."""
        # Create query result with non-matching source
        other_qr = QueryResult(
            query_id="other_001",
            rows=[Row(data={"value": 100})],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="OTHER_database",
                locator="/data/other.csv",
                fields=["value"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        narrative = "Per LMIS: The count is 100 (QID: other_001)."

        engine = VerificationEngine(
            verification_config,
            user_roles=[],
            citation_rules=citation_rules,
        )

        summary = engine.run_with_agent_report(narrative, [other_qr])

        assert summary.ok is False
        assert len(summary.citation_report.malformed) == 1

    def test_citation_issues_convert_to_verification_issues(
        self,
        citation_rules,
        verification_config,
        lmis_query_result,
    ):
        """Test that citation issues appear in verification issues."""
        narrative = "The rate is 87.5% without citation."

        engine = VerificationEngine(
            verification_config,
            user_roles=[],
            citation_rules=citation_rules,
        )

        summary = engine.run_with_agent_report(narrative, [lmis_query_result])

        # Check that citation issues are in main issues list
        assert len(summary.issues) > 0
        citation_issues = [i for i in summary.issues if "UNCITED" in i.code]
        assert len(citation_issues) == 1
        assert citation_issues[0].layer == "L2"

    def test_no_citation_rules_skips_enforcement(
        self,
        verification_config,
        lmis_query_result,
    ):
        """Test that missing citation rules skips enforcement."""
        narrative = "The rate is 87.5% without citation."

        # Engine without citation rules
        engine = VerificationEngine(
            verification_config,
            user_roles=[],
            citation_rules=None,
        )

        summary = engine.run_with_agent_report(narrative, [lmis_query_result])

        # Should pass since citation enforcement is skipped
        assert summary.ok is True
        assert summary.citation_report is None

    def test_years_ignored(
        self,
        citation_rules,
        verification_config,
        lmis_query_result,
    ):
        """Test that years are not treated as numeric claims."""
        narrative = (
            "Per LMIS: In 2023, the rate was 85% (QID: lmis_ret_2023). "
            "Per LMIS: In 2024, it increased to 87.5% (QID: lmis_ret_2024)."
        )

        engine = VerificationEngine(
            verification_config,
            user_roles=[],
            citation_rules=citation_rules,
        )

        summary = engine.run_with_agent_report(narrative, [lmis_query_result])

        # Should only detect 85% and 87.5%, not years
        assert summary.citation_report.total_numbers == 2
        assert summary.ok is True

    def test_citation_with_layers_2_4(
        self,
        citation_rules,
        lmis_query_result,
    ):
        """Test citation enforcement works with other verification layers."""
        # Config with actual verification rules
        config = VerificationConfig(
            crosschecks=[],
            sanity=[
                {"metric": "retention_rate", "rate_0_1": True}
            ],
            freshness_max_hours=72,
        )

        narrative = (
            "Per LMIS: The retention rate is 87.5% in Q3 (QID: lmis_ret_2024q3)."
        )

        engine = VerificationEngine(
            config,
            user_roles=[],
            citation_rules=citation_rules,
        )

        summary = engine.run_with_agent_report(narrative, [lmis_query_result])

        # Both citation and sanity checks should pass
        assert summary.ok is True
        assert summary.citation_report.ok is True

    def test_empty_narrative(
        self,
        citation_rules,
        verification_config,
        lmis_query_result,
    ):
        """Test empty narrative doesn't cause errors."""
        narrative = ""

        engine = VerificationEngine(
            verification_config,
            user_roles=[],
            citation_rules=citation_rules,
        )

        summary = engine.run_with_agent_report(narrative, [lmis_query_result])

        assert summary.ok is True
        assert summary.citation_report.total_numbers == 0

    def test_no_query_results(
        self,
        citation_rules,
        verification_config,
    ):
        """Test handling of no query results."""
        narrative = "Per LMIS: The rate is 87.5% (QID: test_001)."

        engine = VerificationEngine(
            verification_config,
            user_roles=[],
            citation_rules=citation_rules,
        )

        summary = engine.run_with_agent_report(narrative, [])

        # Should return empty summary
        assert summary.ok is True
        assert len(summary.issues) == 0
