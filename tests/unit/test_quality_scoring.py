from src.qnwis.orchestration.quality_metrics import (
    calculate_analysis_confidence,
    calculate_data_completeness,
    calculate_agent_consensus,
    format_confidence_report,
)


def test_confidence_scoring_components():
    facts = [
        {"metric": "current_food_import_costs", "value": 5_000_000_000, "data_type": "current_food_import_costs"},
        {"metric": "food_self_sufficiency_percentage", "value": 30, "data_type": "food_self_sufficiency_percentage"},
    ]
    required = ["current_food_import_costs", "food_self_sufficiency_percentage", "energy_costs_for_agriculture"]
    agent_outputs = {"primary": "analysis text"}

    confidence = calculate_analysis_confidence(
        facts=facts,
        required_data=required,
        agent_outputs=agent_outputs,
        citation_violations=1,
    )

    assert 0 <= confidence["overall_confidence"] <= 1
    assert confidence["components"]["data_quality"] > 0
    assert confidence["citation_violations"] == 1

    report = format_confidence_report(confidence)
    assert "Analysis Confidence Report" in report


def test_consensus_and_completeness_helpers():
    consensus = calculate_agent_consensus({"a": "one", "b": "two"})
    assert consensus >= 0.7

    completeness = calculate_data_completeness(
        [{"metric": "unemployment", "value": 3.0}],
        ["unemployment", "labor_force_participation"],
    )
    assert completeness["completeness_score"] <= 1
    assert "labor_force_participation" in completeness["missing_categories"]
