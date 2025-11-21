from src.qnwis.orchestration.agent_selector import AgentSelector, classify_data_availability


def test_classify_data_availability_uses_facts():
    query = "Should we invest in food security megaprojects?"
    facts = [
        {"type": "time_series_employment"},
        {"metric": "current_food_import_costs", "category": "sector"},
    ]

    available = classify_data_availability(query, facts)
    assert "time_series_employment" in available
    assert "sector_metrics" in available


def test_agent_selector_filters_deterministic_agents():
    selector = AgentSelector()
    classification = {
        "intent": "strategy",
        "entities": {},
        "complexity": "medium",
        "question": "Should Qatar invest in a food security hub?",
    }

    # Facts without labour-market coverage ensure deterministic agents skip
    selected = selector.select_agents(
        classification,
        min_agents=2,
        max_agents=4,
        extracted_facts=[{"type": "investment"}],
    )

    # Deterministic agents such as TimeMachine should not be present
    assert "TimeMachine" not in selected
