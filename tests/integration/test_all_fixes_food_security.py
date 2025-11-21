import pytest

from src.qnwis.orchestration.agent_selector import classify_data_availability
from src.qnwis.orchestration.data_quality import identify_missing_data
from src.qnwis.orchestration.debate import detect_debate_convergence
from src.qnwis.orchestration.prefetch_apis import (
    CompletePrefetchLayer,
    classify_query_for_extraction,
)
from src.qnwis.orchestration.quality_metrics import calculate_analysis_confidence
from src.qnwis.ui.agent_status import display_agent_execution_status
from src.qnwis.verification.citation_enforcer import verify_citations_strict


@pytest.mark.asyncio
async def test_food_security_flow(monkeypatch):
    """End-to-end smoke test touching all six fixes with mocked data."""

    async def fake_fetch_all_sources(self, query: str):
        return [
            {"metric": "current_food_import_costs", "data_type": "current_food_import_costs", "value": "$5B"},
            {
                "metric": "food_self_sufficiency_percentage",
                "data_type": "food_self_sufficiency_percentage",
                "category": "sector_food",
                "value": 30,
            },
            {
                "metric": "project_costs",
                "data_type": "project_costs",
                "value": "$15 billion",
            },
        ]

    async def fake_execute_targeted_search(self, data_gap, strategy):
        return [
            {
                "metric": data_gap,
                "value": 120.5,
                "source": "Targeted Search",
                "data_type": data_gap,
                "confidence": 0.8,
            }
        ]

    monkeypatch.setattr(CompletePrefetchLayer, "fetch_all_sources", fake_fetch_all_sources)
    monkeypatch.setattr(CompletePrefetchLayer, "_execute_targeted_search", fake_execute_targeted_search)

    prefetch = CompletePrefetchLayer()
    result = await prefetch.fetch_all_sources_with_gaps(
        "Should Qatar invest $15B in a food security megaproject?"
    )

    facts = result["extracted_facts"]
    assert len(facts) >= 3
    assert 0 < result["data_quality_score"] <= 1
    assert identify_missing_data(facts, ["energy_costs_for_agriculture"]) == []

    query_types = classify_query_for_extraction("invest in agriculture self-sufficiency")
    assert "food_security" in query_types

    available = classify_data_availability("food costs", facts)
    assert "sector_metrics" in available

    citation_report = verify_citations_strict(
        '[Per extraction: "Food imports $5B" from World Bank] '
        'Qatar plans to invest $15 billion. [Source: Ministry of Finance]',
        facts,
    )
    assert citation_report["passed"]

    debate_history = [{"agent": f"A{i}", "content": "Consensus text"} for i in range(10)]
    convergence = detect_debate_convergence(debate_history)
    assert "converged" in convergence

    status_md = display_agent_execution_status(
        [
            {"name": "LabourEconomist", "status": "invoked", "duration": 1.0},
            {"name": "TimeMachine", "status": "skipped", "reason": "No labour data"},
        ]
    )
    assert "Agent Execution Status" in status_md

    confidence = calculate_analysis_confidence(
        facts=facts,
        required_data=["current_food_import_costs", "food_self_sufficiency_percentage"],
        agent_outputs={"primary": "analysis"},
        citation_violations=citation_report["violation_count"],
    )
    assert 0 < confidence["overall_confidence"] <= 1


@pytest.mark.asyncio
async def test_labor_market_query_invokes_all_data_types():
    facts = [
        {"metric": "unemployment_rate", "type": "time_series"},
        {"metric": "labour_force_participation", "category": "sector"},
    ]
    available = classify_data_availability("What is the unemployment rate?", facts)
    assert {"labor_market", "time_series_employment"} <= set(available)
