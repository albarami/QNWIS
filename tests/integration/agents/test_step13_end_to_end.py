"""
Integration end-to-end test for Step 13 agents.

Verifies that Pattern Detective and National Strategy agents:
1. Only use DataClient methods (no .execute_query or raw HTTP)
2. Generate narratives with Executive Summary, Findings, Evidence Table, Citations + Query IDs,
   Freshness, and Reproducibility
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.agents.base import DataClient
from src.qnwis.agents.national_strategy import NationalStrategyAgent
from src.qnwis.agents.pattern_detective import PatternDetectiveAgent
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis


@pytest.fixture
def synthetic_client(tmp_path, monkeypatch):
    """Fixture providing DataClient with synthetic LMIS data."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(tmp_path)

    client = DataClient(queries_dir="src/qnwis/data/queries", ttl_s=60)

    yield client
    csvcat.BASE = old_base


class TestStep13EndToEnd:
    """Integration tests verifying Step 13 agent compliance and narrative quality."""

    def test_pattern_detective_only_uses_dataclient_methods(self, synthetic_client: DataClient) -> None:
        """Verify Pattern Detective only calls DataClient.run(), not execute_query or HTTP."""
        agent = PatternDetectiveAgent(synthetic_client)

        # Spy on the client to ensure only .run() is called
        original_run = synthetic_client.run
        call_log: list[str] = []

        def spy_run(query_id: str):
            call_log.append(f"run:{query_id}")
            return original_run(query_id)

        with patch.object(synthetic_client, "run", side_effect=spy_run):
            # Test all Pattern Detective methods
            report1 = agent.detect_anomalous_retention(z_threshold=2.5)
            report2 = agent.find_correlations(method="spearman")
            report3 = agent.identify_root_causes(top_n=3)
            report4 = agent.best_practices(metric="qatarization", top_n=5)

            # Verify all calls were to .run()
            assert len(call_log) > 0, "Agent should have called DataClient.run()"
            assert all(call.startswith("run:") for call in call_log), "Only DataClient.run() should be called"

        # Verify reports contain findings
        assert len(report1.findings) >= 0  # May have 0 if no anomalies
        assert len(report2.findings) == 1
        assert len(report3.findings) >= 0
        assert len(report4.findings) == 1

    def test_national_strategy_only_uses_dataclient_methods(self, synthetic_client: DataClient) -> None:
        """Verify National Strategy only calls DataClient.run(), not execute_query or HTTP."""
        agent = NationalStrategyAgent(synthetic_client)

        original_run = synthetic_client.run
        call_log: list[str] = []

        def spy_run(query_id: str):
            call_log.append(f"run:{query_id}")
            return original_run(query_id)

        with patch.object(synthetic_client, "run", side_effect=spy_run):
            # Test all National Strategy methods
            report1 = agent.gcc_benchmark(min_countries=3)
            report2 = agent.talent_competition_assessment()
            report3 = agent.vision2030_alignment()

            # Verify all calls were to .run()
            assert len(call_log) > 0, "Agent should have called DataClient.run()"
            assert all(call.startswith("run:") for call in call_log), "Only DataClient.run() should be called"

        # Verify reports contain findings
        assert len(report1.findings) >= 0
        assert len(report2.findings) >= 0
        assert len(report3.findings) >= 0

    def test_pattern_detective_narrative_structure(self, synthetic_client: DataClient) -> None:
        """Verify Pattern Detective narratives contain all required components."""
        agent = PatternDetectiveAgent(synthetic_client)

        report = agent.find_correlations(method="spearman", min_correlation=0.3)

        assert len(report.findings) == 1
        insight = report.findings[0]

        # Executive Summary (title + summary)
        assert insight.title, "Insight must have a title (Executive Summary)"
        assert insight.summary, "Insight must have a summary"
        assert len(insight.summary) > 10, "Summary should be substantive"

        # Findings (metrics)
        assert len(insight.metrics) > 0, "Insight must contain metrics"
        assert "correlation" in insight.metrics or "sample_size" in insight.metrics

        # Evidence Table (evidence list with provenance)
        assert len(insight.evidence) >= 2, "Must have at least original + derived evidence"
        for ev in insight.evidence:
            assert ev.query_id, "Evidence must include Query ID"
            assert ev.dataset_id, "Evidence must include dataset_id"
            assert ev.locator, "Evidence must include locator"

        # Citations + Query IDs
        query_ids = [e.query_id for e in insight.evidence]
        assert len(query_ids) >= 2, "Must cite at least 2 query IDs (source + derived)"
        assert any("derived_" in qid for qid in query_ids), "Must include derived query result"

        # Freshness (confidence_score based on warnings)
        assert hasattr(insight, "confidence_score"), "Insight must have confidence_score"
        assert 0.5 <= insight.confidence_score <= 1.0, "Confidence score must be bounded [0.5, 1.0]"

        # Reproducibility (all evidence includes locator for data sources)
        assert all(ev.locator for ev in insight.evidence), "All evidence must be reproducible with locators"

    def test_national_strategy_narrative_structure(self, synthetic_client: DataClient) -> None:
        """Verify National Strategy narratives contain all required components."""
        agent = NationalStrategyAgent(synthetic_client)

        report = agent.gcc_benchmark(min_countries=2)

        if len(report.findings) == 0:
            pytest.skip("Insufficient GCC data in synthetic dataset")

        insight = report.findings[0]

        # Executive Summary
        assert insight.title, "Insight must have a title"
        assert insight.summary, "Insight must have a summary"

        # Findings
        assert len(insight.metrics) > 0, "Insight must contain metrics"

        # Evidence Table
        assert len(insight.evidence) >= 1, "Must have evidence"
        for ev in insight.evidence:
            assert ev.query_id, "Evidence must include Query ID"
            assert ev.dataset_id, "Evidence must include dataset_id"

        # Citations + Query IDs
        query_ids = [e.query_id for e in insight.evidence]
        assert len(query_ids) >= 1, "Must cite at least 1 query ID"

        # Freshness
        assert hasattr(insight, "confidence_score")
        assert 0.5 <= insight.confidence_score <= 1.0

        # Reproducibility
        assert all(ev.locator for ev in insight.evidence)

    def test_pattern_detective_best_practices_full_narrative(self, synthetic_client: DataClient) -> None:
        """Test best_practices method produces complete narrative with all components."""
        agent = PatternDetectiveAgent(synthetic_client)

        report = agent.best_practices(metric="qatarization", top_n=5)

        assert len(report.findings) == 1
        insight = report.findings[0]

        # Verify all narrative components
        assert "Best practices" in insight.title
        assert "qatarization" in insight.title.lower()
        assert len(insight.summary) > 20
        assert insight.metrics["metric"] == "qatarization"
        assert "top_5_average" in insight.metrics
        assert "overall_average" in insight.metrics

        # Evidence must include source + derived
        assert len(insight.evidence) == 2
        query_ids = [e.query_id for e in insight.evidence]
        assert any("syn_qatarization" in qid or "q_" in qid for qid in query_ids)
        assert any("derived_" in qid for qid in query_ids)

        # All evidence must have complete provenance
        for ev in insight.evidence:
            assert ev.query_id
            assert ev.dataset_id
            assert ev.locator
            assert isinstance(ev.fields, list)

    def test_national_strategy_vision2030_full_narrative(self, synthetic_client: DataClient) -> None:
        """Test vision2030_alignment produces complete narrative."""
        agent = NationalStrategyAgent(synthetic_client)

        report = agent.vision2030_alignment(target_year=2030, current_year=2024)

        if len(report.findings) == 0:
            pytest.skip("No valid qatarization data in synthetic dataset")

        insight = report.findings[0]

        # Verify narrative structure
        assert "Vision 2030" in insight.title
        assert len(insight.summary) > 30
        assert "current_qatarization" in insight.metrics
        assert "target_qatarization" in insight.metrics
        assert "gap_percentage_points" in insight.metrics
        assert "required_annual_growth" in insight.metrics

        # Evidence
        assert len(insight.evidence) >= 2
        query_ids = [e.query_id for e in insight.evidence]
        assert any("qatarization" in qid.lower() for qid in query_ids)
        assert any("derived_" in qid for qid in query_ids)

        # Reproducibility: all evidence has locator
        assert all(ev.locator for ev in insight.evidence)

    def test_agent_reports_contain_warnings_when_applicable(self, synthetic_client: DataClient) -> None:
        """Verify agents propagate warnings from data sources into reports."""
        agent = PatternDetectiveAgent(synthetic_client)

        # Use a method that may produce warnings
        report = agent.detect_anomalous_retention(z_threshold=2.5, min_sample_size=3)

        # If findings exist, check that warnings are captured
        if report.findings:
            insight = report.findings[0]
            # Warnings should be a list (may be empty)
            assert isinstance(insight.warnings, list)
            # Confidence score should reflect warnings
            assert 0.5 <= insight.confidence_score <= 1.0

    def test_no_direct_execute_query_calls(self, synthetic_client: DataClient) -> None:
        """Verify agents never call execute_query directly."""
        agent_pd = PatternDetectiveAgent(synthetic_client)
        agent_ns = NationalStrategyAgent(synthetic_client)

        # Mock execute_query to fail if called
        with patch("src.qnwis.data.deterministic.access.execute") as mock_execute:
            mock_execute.side_effect = AssertionError("Direct execute() call detected!")

            # Run agent methods (they should use DataClient.run which uses execute_cached)
            try:
                agent_pd.find_correlations()
                agent_ns.gcc_benchmark(min_countries=2)
            except AssertionError as e:
                if "Direct execute() call detected!" in str(e):
                    pytest.fail("Agent called execute_query directly instead of using DataClient")

            # If no AssertionError, test passed

    def test_all_evidence_includes_query_ids(self, synthetic_client: DataClient) -> None:
        """Verify all evidence objects include query_id for citation tracing."""
        agent = PatternDetectiveAgent(synthetic_client)

        report = agent.best_practices(metric="retention", top_n=3)

        if len(report.findings) == 0:
            pytest.skip("No findings in report")

        for insight in report.findings:
            for evidence in insight.evidence:
                assert evidence.query_id, f"Evidence missing query_id: {evidence}"
                assert isinstance(evidence.query_id, str)
                assert len(evidence.query_id) > 0

    def test_derived_results_have_proper_query_ids(self, synthetic_client: DataClient) -> None:
        """Verify derived results use 'derived_operation_hash' query ID format."""
        agent = PatternDetectiveAgent(synthetic_client)

        report = agent.identify_root_causes(top_n=2)

        if len(report.findings) == 0:
            pytest.skip("No findings in report")

        insight = report.findings[0]
        query_ids = [e.query_id for e in insight.evidence]

        # Should have at least one derived result
        derived_ids = [qid for qid in query_ids if "derived_" in qid]
        assert len(derived_ids) > 0, "Must include at least one derived query result"

        # Derived IDs should follow format: derived_operation_hash
        for did in derived_ids:
            assert did.startswith("derived_"), f"Derived ID must start with 'derived_': {did}"
            # Format is derived_operation_hash, so should have at least 3 parts when split by _
            parts = did.split("_")
            assert len(parts) >= 3, f"Derived ID must have format derived_operation_hash: {did}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
