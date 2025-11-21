from src.qnwis.orchestration.data_quality import calculate_data_quality, identify_missing_data
from src.qnwis.orchestration.prefetch_apis import classify_query_for_extraction


def test_classify_query_for_extraction_identifies_domains():
    query = "Evaluate food import costs and agriculture energy subsidies"
    query_types = classify_query_for_extraction(query)
    assert "food_security" in query_types


def test_data_quality_and_gap_detection():
    facts = [
        {"metric": "current_food_import_costs", "data_type": "current_food_import_costs"},
        {"metric": "food_self_sufficiency_percentage", "data_type": "food_self_sufficiency_percentage"},
    ]
    required = [
        "current_food_import_costs",
        "food_self_sufficiency_percentage",
        "energy_costs_for_agriculture",
    ]

    score = calculate_data_quality(facts, required)
    missing = identify_missing_data(facts, required)

    assert 0 < score < 1
    assert "energy_costs_for_agriculture" in missing
