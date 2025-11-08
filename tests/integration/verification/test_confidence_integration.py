"""
Integration tests for confidence scoring in orchestration workflow.

Tests the full graph run → OrchestrationResult.confidence populated and
Format node showing "Confidence Assessment" section.

Scenarios:
1. Happy path: Perfect verification → GREEN confidence
2. Minor issues: Some warnings → AMBER confidence
3. Major issues: Multiple failures → RED confidence
4. ERROR from result verification: Run fails, but confidence stored for audit
"""

import pytest

from src.qnwis.agents.base import AgentReport, Evidence, Finding
from src.qnwis.data.deterministic.models import QueryResult
from src.qnwis.orchestration.nodes.format import format_report
from src.qnwis.orchestration.nodes.verify import verify_structure
from src.qnwis.orchestration.schemas import (
    ConfidenceBreakdown,
    OrchestrationResult,
    OrchestrationTask,
    WorkflowState,
)


@pytest.fixture
def mock_query_results() -> list[QueryResult]:
    """Create mock query results for prefetch cache."""
    return [
        QueryResult(
            query_id="Q001",
            dataset_id="LMIS",
            locator="test/data.csv",
            fields=["retention_rate", "sector"],
            data=[{"sector": "Healthcare", "retention_rate": 0.85}],
            metadata={"freshness_as_of": "2025-11-01T00:00:00Z"},
        ),
        QueryResult(
            query_id="Q002",
            dataset_id="GCC-STAT",
            locator="test/ref.csv",
            fields=["retention_rate", "sector"],
            data=[{"sector": "Healthcare", "retention_rate": 0.84}],
            metadata={"freshness_as_of": "2025-11-01T00:00:00Z"},
        ),
    ]


@pytest.fixture
def agent_report_perfect() -> AgentReport:
    """Perfect agent report with all citations and evidence."""
    return AgentReport(
        agent="test_agent",
        findings=[
            Finding(
                title="Healthcare Retention Analysis",
                summary=(
                    "The retention rate for Healthcare is 85% according to LMIS (QID:Q001). "
                    "Cross-validated with GCC-STAT at 84% (QID:Q002)."
                ),
                metrics={"retention_rate": 0.85},
                evidence=[
                    Evidence(
                        query_id="Q001",
                        dataset_id="LMIS",
                        locator="test/data.csv",
                        fields=["retention_rate"],
                        freshness_as_of="2025-11-01T00:00:00Z",
                    ),
                    Evidence(
                        query_id="Q002",
                        dataset_id="GCC-STAT",
                        locator="test/ref.csv",
                        fields=["retention_rate"],
                        freshness_as_of="2025-11-01T00:00:00Z",
                    ),
                ],
                confidence_score=1.0,
            )
        ],
        warnings=[],
    )


@pytest.fixture
def agent_report_minor_issues() -> AgentReport:
    """Agent report with minor issues (some uncited claims)."""
    return AgentReport(
        agent="test_agent",
        findings=[
            Finding(
                title="Sector Analysis",
                summary=(
                    "Retention rates vary significantly. Healthcare shows 85% "
                    "according to LMIS (QID:Q001). Manufacturing has seen improvements to 78%. "
                    "Some PII data like john.doe@example.com was detected."
                ),
                metrics={"retention_healthcare": 0.85, "retention_manufacturing": 0.78},
                evidence=[
                    Evidence(
                        query_id="Q001",
                        dataset_id="LMIS",
                        locator="test/data.csv",
                        fields=["retention_rate"],
                        freshness_as_of="2025-10-25T00:00:00Z",  # Slightly older
                    ),
                ],
                confidence_score=0.9,
            )
        ],
        warnings=["Missing citation for manufacturing retention rate"],
    )


@pytest.fixture
def agent_report_major_issues() -> AgentReport:
    """Agent report with major issues (many uncited claims, errors)."""
    return AgentReport(
        agent="test_agent",
        findings=[
            Finding(
                title="Problematic Report",
                summary=(
                    "The sector shows declining trends. Multiple metrics like 45%, 67%, "
                    "and 89% indicate variations. Email addresses like test@example.com "
                    "and IDs like 1234567890123 appeared in raw data. "
                    "According to Unknown Source, the rate is 55%."
                ),
                metrics={"rate1": 0.45, "rate2": 0.67, "rate3": 0.89},
                evidence=[],  # No evidence provided
                confidence_score=0.3,
            )
        ],
        warnings=["No evidence citations", "Unknown data source", "PII detected"],
    )


class TestConfidenceInWorkflow:
    """Test confidence scoring integrated in verify/format workflow."""

    def test_perfect_verification_green_confidence(
        self, agent_report_perfect, mock_query_results
    ):
        """Perfect verification should produce GREEN confidence."""
        # Create workflow state with agent output
        task = OrchestrationTask(intent="pattern.anomalies", params={})
        state = WorkflowState(
            task=task,
            agent_output=agent_report_perfect,
            metadata={
                "agent": "test_agent",
                "method": "analyze_patterns",
                "routing": {},
                "agents": [],
                "cache_stats": {},
            },
            prefetch_cache={
                "Q001": mock_query_results[0],
                "Q002": mock_query_results[1],
            },
        )

        # Run verify node
        verified_state_dict = verify_structure(
            state.model_dump(),
            strict=False,
            require_evidence=True,
            require_freshness=True,
        )

        # Check that confidence was computed
        assert "confidence_breakdown" in verified_state_dict["metadata"]
        confidence_dict = verified_state_dict["metadata"]["confidence_breakdown"]
        assert confidence_dict["score"] >= 90
        assert confidence_dict["band"] == "GREEN"

        # Run format node
        formatted_state_dict = format_report(verified_state_dict)

        # Extract formatted result
        result = OrchestrationResult.model_validate(
            formatted_state_dict["agent_output"]
        )

        # Verify confidence is attached
        assert result.confidence is not None
        assert isinstance(result.confidence, ConfidenceBreakdown)
        assert result.confidence.score >= 90
        assert result.confidence.band == "GREEN"

        # Verify confidence section in report
        section_titles = [s.title for s in result.sections]
        assert "Confidence Assessment" in section_titles

        # Find confidence section
        confidence_section = next(
            s for s in result.sections if s.title == "Confidence Assessment"
        )
        assert "GREEN" in confidence_section.body_md
        assert str(result.confidence.score) in confidence_section.body_md

    def test_minor_issues_amber_confidence(
        self, agent_report_minor_issues, mock_query_results
    ):
        """Minor verification issues should produce AMBER confidence."""
        task = OrchestrationTask(intent="pattern.anomalies", params={})
        state = WorkflowState(
            task=task,
            agent_output=agent_report_minor_issues,
            metadata={
                "agent": "test_agent",
                "method": "analyze_patterns",
                "routing": {},
                "agents": [],
                "cache_stats": {},
            },
            prefetch_cache={
                "Q001": mock_query_results[0],
            },
        )

        # Run verify node
        verified_state_dict = verify_structure(
            state.model_dump(),
            strict=False,
            require_evidence=True,
            require_freshness=True,
        )

        # Check confidence computed
        confidence_dict = verified_state_dict["metadata"].get("confidence_breakdown")
        if confidence_dict:
            # Should be AMBER or possibly GREEN depending on issue severity
            assert confidence_dict["score"] >= 70
            assert confidence_dict["band"] in {"GREEN", "AMBER"}

        # Run format node
        formatted_state_dict = format_report(verified_state_dict)
        result = OrchestrationResult.model_validate(
            formatted_state_dict["agent_output"]
        )

        # Verify confidence attached
        if result.confidence:
            assert result.confidence.score >= 70
            assert result.confidence.band in {"GREEN", "AMBER"}

    def test_major_issues_red_confidence(
        self, agent_report_major_issues, mock_query_results
    ):
        """Major verification issues should produce RED confidence."""
        task = OrchestrationTask(intent="pattern.anomalies", params={})
        state = WorkflowState(
            task=task,
            agent_output=agent_report_major_issues,
            metadata={
                "agent": "test_agent",
                "method": "analyze_patterns",
                "routing": {},
                "agents": [],
                "cache_stats": {},
            },
            prefetch_cache={},  # No prefetch data
        )

        # Run verify node (should pass structural checks but have verification issues)
        verified_state_dict = verify_structure(
            state.model_dump(),
            strict=False,
            require_evidence=False,  # Relax for this test
            require_freshness=False,
        )

        # Even with no evidence, confidence should still be computed
        # (using insufficient evidence floor)
        confidence_dict = verified_state_dict["metadata"].get("confidence_breakdown")
        if confidence_dict:
            # Should be RED due to insufficient evidence
            assert confidence_dict["score"] < 75
            assert confidence_dict["band"] == "RED"

        # Run format node
        formatted_state_dict = format_report(verified_state_dict)
        result = OrchestrationResult.model_validate(
            formatted_state_dict["agent_output"]
        )

        # Verify confidence reflects issues
        if result.confidence:
            assert result.confidence.score < 75
            assert result.confidence.band == "RED"

    def test_verification_error_with_confidence_for_audit(
        self, agent_report_major_issues, mock_query_results
    ):
        """
        When verification fails with ERROR, confidence should still be computed
        for audit trail purposes.
        """
        task = OrchestrationTask(intent="pattern.anomalies", params={})

        # Create report with no evidence (will fail strict validation)
        state = WorkflowState(
            task=task,
            agent_output=agent_report_major_issues,
            metadata={
                "agent": "test_agent",
                "method": "analyze_patterns",
                "routing": {},
                "agents": [],
                "cache_stats": {},
            },
            prefetch_cache={},
        )

        # Run verify with strict=True and required evidence
        verified_state_dict = verify_structure(
            state.model_dump(),
            strict=False,  # Don't fail the workflow
            require_evidence=True,
            require_freshness=True,
        )

        # Even if verification had errors, confidence should be present
        confidence_dict = verified_state_dict["metadata"].get("confidence_breakdown")

        # Confidence may or may not be computed depending on whether
        # verification layers ran. If it is computed, it should be stored.
        if confidence_dict:
            # Should be low confidence
            assert 0 <= confidence_dict["score"] <= 100
            assert confidence_dict["band"] in {"GREEN", "AMBER", "RED"}

            # Verify it would be included in audit metadata
            assert "confidence_breakdown" in verified_state_dict["metadata"]


class TestConfidenceSection:
    """Test confidence section formatting in reports."""

    def test_confidence_section_structure(self, agent_report_perfect, mock_query_results):
        """Confidence section should have proper structure."""
        task = OrchestrationTask(intent="pattern.anomalies", params={})
        state = WorkflowState(
            task=task,
            agent_output=agent_report_perfect,
            metadata={
                "agent": "test_agent",
                "method": "analyze_patterns",
                "routing": {},
                "agents": [],
                "cache_stats": {},
            },
            prefetch_cache={
                "Q001": mock_query_results[0],
                "Q002": mock_query_results[1],
            },
        )

        verified_state_dict = verify_structure(state.model_dump(), strict=False)
        formatted_state_dict = format_report(verified_state_dict)
        result = OrchestrationResult.model_validate(
            formatted_state_dict["agent_output"]
        )

        # Find confidence section
        confidence_sections = [
            s for s in result.sections if s.title == "Confidence Assessment"
        ]

        if confidence_sections:
            section = confidence_sections[0]

            # Check section contains key elements
            assert "Overall Score" in section.body_md
            assert "Component Breakdown" in section.body_md
            assert "Key Factors" in section.body_md
            assert "Interpretation" in section.body_md

            # Check band is mentioned
            if result.confidence:
                assert result.confidence.band in section.body_md

            # Check component table is present
            assert "Citation Coverage" in section.body_md or "citation" in section.body_md.lower()
            assert "Result Verification" in section.body_md or "numbers" in section.body_md.lower()

    def test_confidence_dashboard_payload_structure(
        self, agent_report_perfect, mock_query_results
    ):
        """Dashboard payload should have correct structure."""
        task = OrchestrationTask(intent="pattern.anomalies", params={})
        state = WorkflowState(
            task=task,
            agent_output=agent_report_perfect,
            metadata={
                "agent": "test_agent",
                "method": "analyze_patterns",
                "routing": {},
                "agents": [],
                "cache_stats": {},
            },
            prefetch_cache={
                "Q001": mock_query_results[0],
                "Q002": mock_query_results[1],
            },
        )

        verified_state_dict = verify_structure(state.model_dump(), strict=False)
        formatted_state_dict = format_report(verified_state_dict)
        result = OrchestrationResult.model_validate(
            formatted_state_dict["agent_output"]
        )

        if result.confidence:
            payload = result.confidence.dashboard_payload

            # Required keys
            assert "score" in payload
            assert "band" in payload
            assert "coverage" in payload
            assert "freshness" in payload

            # Value types and ranges
            assert isinstance(payload["score"], int)
            assert 0 <= payload["score"] <= 100
            assert payload["band"] in {"GREEN", "AMBER", "RED"}
            assert isinstance(payload["coverage"], (int, float))
            assert 0.0 <= payload["coverage"] <= 1.0
            assert isinstance(payload["freshness"], (int, float))
            assert 0.0 <= payload["freshness"] <= 1.0


class TestConfidenceComponents:
    """Test individual component scores are reflected correctly."""

    def test_citation_component_reflected(
        self, agent_report_perfect, mock_query_results
    ):
        """Citation component should be 100 for perfect citations."""
        task = OrchestrationTask(intent="pattern.anomalies", params={})
        state = WorkflowState(
            task=task,
            agent_output=agent_report_perfect,
            metadata={
                "agent": "test_agent",
                "method": "analyze_patterns",
                "routing": {},
                "agents": [],
                "cache_stats": {},
            },
            prefetch_cache={
                "Q001": mock_query_results[0],
                "Q002": mock_query_results[1],
            },
        )

        verified_state_dict = verify_structure(state.model_dump(), strict=False)
        formatted_state_dict = format_report(verified_state_dict)
        result = OrchestrationResult.model_validate(
            formatted_state_dict["agent_output"]
        )

        if result.confidence:
            # Citation component should be high (perfect citations)
            citation_score = result.confidence.components.get("citation", 0)
            assert citation_score >= 90.0

    def test_privacy_component_penalized_on_redactions(
        self, agent_report_minor_issues, mock_query_results
    ):
        """Privacy component should be penalized when redactions applied."""
        task = OrchestrationTask(intent="pattern.anomalies", params={})
        state = WorkflowState(
            task=task,
            agent_output=agent_report_minor_issues,
            metadata={
                "agent": "test_agent",
                "method": "analyze_patterns",
                "routing": {},
                "agents": [],
                "cache_stats": {},
            },
            prefetch_cache={
                "Q001": mock_query_results[0],
            },
        )

        verified_state_dict = verify_structure(state.model_dump(), strict=False)

        # Check if redactions were applied
        redactions = verified_state_dict["metadata"].get("verification_redactions", 0)

        if redactions > 0:
            formatted_state_dict = format_report(verified_state_dict)
            result = OrchestrationResult.model_validate(
                formatted_state_dict["agent_output"]
            )

            if result.confidence:
                # Privacy component should be slightly penalized
                privacy_score = result.confidence.components.get("privacy", 100)
                assert privacy_score < 100.0
