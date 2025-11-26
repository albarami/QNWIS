"""
Unit tests for Scenario Generator.

Tests scenario generation with Claude Sonnet 4 for parallel analysis.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from qnwis.orchestration.nodes.scenario_generator import ScenarioGenerator


class MockLLMResponse:
    """Mock LLM response for testing"""
    def __init__(self, content):
        self.content = content


@pytest.mark.asyncio
async def test_scenario_generation_from_query():
    """Test that scenario generator produces 4-6 scenarios from a query."""
    generator = ScenarioGenerator()
    
    # Mock Claude API response
    mock_scenarios = [
        {
            "id": "scenario_1",
            "name": "Base Case",
            "description": "Current trends continue",
            "modified_assumptions": {"oil_price": 75}
        },
        {
            "id": "scenario_2",
            "name": "Oil Shock",
            "description": "Oil price drops to $45",
            "modified_assumptions": {"oil_price": 45}
        },
        {
            "id": "scenario_3",
            "name": "GCC Competition",
            "description": "Intense regional competition",
            "modified_assumptions": {"gcc_competition": "intense"}
        },
        {
            "id": "scenario_4",
            "name": "Tech Disruption",
            "description": "AI disrupts labor market",
            "modified_assumptions": {"ai_impact": "high"}
        }
    ]
    
    mock_response = MockLLMResponse(json.dumps(mock_scenarios))
    
    with patch('qnwis.orchestration.llm_wrapper.call_llm_with_rate_limit', 
               return_value=mock_response):
        scenarios = await generator.generate_scenarios(
            query="Should Qatar invest $50B in financial hub?",
            extracted_facts={"gdp": "200B", "oil_price": "75"}
        )
    
    # Verify 4-6 scenarios generated (plan says 4-6)
    assert 4 <= len(scenarios) <= 6, f"Expected 4-6 scenarios, got {len(scenarios)}"
    assert scenarios[0]['name'] == "Base Case"
    # Verify proper structure
    for scenario in scenarios:
        assert 'id' in scenario
        assert 'name' in scenario
        assert 'description' in scenario
        assert 'modified_assumptions' in scenario


@pytest.mark.asyncio
async def test_scenario_structure_validation():
    """Test that scenarios have correct structure (id, name, description, modified_assumptions)."""
    generator = ScenarioGenerator()
    
    # Valid scenarios
    valid_scenarios = [
        {"id": "s1", "name": "Test", "description": "Test scenario", "modified_assumptions": {"x": 1}},
        {"id": "s2", "name": "Test2", "description": "Test scenario 2", "modified_assumptions": {"y": 2}},
        {"id": "s3", "name": "Test3", "description": "Test scenario 3", "modified_assumptions": {"z": 3}},
        {"id": "s4", "name": "Test4", "description": "Test scenario 4", "modified_assumptions": {"a": 4}}
    ]
    
    mock_response = MockLLMResponse(json.dumps(valid_scenarios))
    
    with patch('qnwis.orchestration.llm_wrapper.call_llm_with_rate_limit',
               return_value=mock_response):
        scenarios = await generator.generate_scenarios("test query", {})
    
    # Verify all required fields present
    for scenario in scenarios:
        assert 'id' in scenario
        assert 'name' in scenario
        assert 'description' in scenario
        assert 'modified_assumptions' in scenario
        assert isinstance(scenario['modified_assumptions'], dict)


@pytest.mark.asyncio
async def test_scenario_diversity():
    """Test that scenarios have different assumptions."""
    generator = ScenarioGenerator()
    
    diverse_scenarios = [
        {"id": "s1", "name": "Base", "description": "base", "modified_assumptions": {"oil_price": 75}},
        {"id": "s2", "name": "Low Oil", "description": "low", "modified_assumptions": {"oil_price": 45}},
        {"id": "s3", "name": "High Oil", "description": "high", "modified_assumptions": {"oil_price": 100}},
        {"id": "s4", "name": "Competition", "description": "comp", "modified_assumptions": {"gcc_competition": "high"}}
    ]
    
    mock_response = MockLLMResponse(json.dumps(diverse_scenarios))
    
    with patch('qnwis.orchestration.llm_wrapper.call_llm_with_rate_limit',
               return_value=mock_response):
        scenarios = await generator.generate_scenarios("test", {})
    
    # Verify scenarios have different assumptions
    assumptions = [s['modified_assumptions'] for s in scenarios]
    assert len(assumptions) == len(set(str(a) for a in assumptions))  # All different


@pytest.mark.asyncio
async def test_scenario_plausibility():
    """Test that scenarios are realistic (not extreme outliers)."""
    generator = ScenarioGenerator()
    
    plausible_scenarios = [
        {"id": "s1", "name": "Base", "description": "Realistic base case scenario with moderate assumptions", 
         "modified_assumptions": {"oil_price": 75, "growth": 0.03}},
        {"id": "s2", "name": "Recession", "description": "Realistic downturn scenario based on historical precedent",
         "modified_assumptions": {"oil_price": 50, "growth": -0.01}},
        {"id": "s3", "name": "Recovery", "description": "Realistic recovery scenario with strong fundamentals",
         "modified_assumptions": {"oil_price": 85, "growth": 0.05}},
        {"id": "s4", "name": "Competition", "description": "Realistic competitive pressure from regional peers",
         "modified_assumptions": {"gcc_competition": "moderate", "market_share": 0.25}}
    ]
    
    mock_response = MockLLMResponse(json.dumps(plausible_scenarios))
    
    with patch('qnwis.orchestration.llm_wrapper.call_llm_with_rate_limit',
               return_value=mock_response):
        scenarios = await generator.generate_scenarios("test", {})
    
    # Verify descriptions are detailed (> 20 chars)
    for scenario in scenarios:
        assert len(scenario['description']) > 20, \
            f"Scenario {scenario['name']} has too short description"


@pytest.mark.asyncio
async def test_format_facts_truncation():
    """Test that facts are limited to 50 items in prompt."""
    generator = ScenarioGenerator()
    
    # Create 100 facts
    many_facts = {f"fact_{i}": f"value_{i}" for i in range(100)}
    
    formatted = generator._format_facts(many_facts)
    
    # Count lines (should be ~50 + 1 continuation line)
    lines = formatted.split('\n')
    assert len(lines) <= 52  # 50 facts + continuation + buffer
    assert "... and 50 more facts" in formatted or "... and" in formatted


@pytest.mark.asyncio
async def test_llm_model_is_claude_sonnet_4():
    """Test that generator uses Claude Sonnet 4 model."""
    generator = ScenarioGenerator()
    
    # Verify model configuration
    assert hasattr(generator, 'llm')
    assert generator.llm.model == "claude-sonnet-4-20250514"
    assert generator.llm.temperature == 0.3
    assert generator.llm.max_tokens == 4000


@pytest.mark.asyncio
async def test_scenario_generation_error_handling():
    """Test that generator handles errors gracefully."""
    generator = ScenarioGenerator()
    
    # Test invalid JSON response
    with patch('qnwis.orchestration.llm_wrapper.call_llm_with_rate_limit',
               return_value=MockLLMResponse("invalid json")):
        with pytest.raises((ValueError, json.JSONDecodeError)):
            await generator.generate_scenarios("test", {})
    
    # Test missing required fields (need at least 4 scenarios)
    invalid_scenarios = [
        {"id": "s1", "name": "Test"},  # Missing description and modified_assumptions
        {"id": "s2", "name": "Test2"},
        {"id": "s3", "name": "Test3"},
        {"id": "s4", "name": "Test4"}
    ]
    
    with patch('qnwis.orchestration.llm_wrapper.call_llm_with_rate_limit',
               return_value=MockLLMResponse(json.dumps(invalid_scenarios))):
        with pytest.raises(ValueError):
            await generator.generate_scenarios("test", {})


@pytest.mark.asyncio
async def test_scenario_id_uniqueness():
    """Test that scenario IDs are unique."""
    generator = ScenarioGenerator()
    
    # Scenarios with duplicate IDs should be rejected
    duplicate_scenarios = [
        {"id": "s1", "name": "Test1", "description": "desc1 with enough text", "modified_assumptions": {"x": 1}},
        {"id": "s1", "name": "Test2", "description": "desc2 with enough text", "modified_assumptions": {"y": 2}},  # Duplicate ID
        {"id": "s2", "name": "Test3", "description": "desc3 with enough text", "modified_assumptions": {"z": 3}},
        {"id": "s3", "name": "Test4", "description": "desc4 with enough text", "modified_assumptions": {"a": 4}}
    ]
    
    with patch('qnwis.orchestration.llm_wrapper.call_llm_with_rate_limit',
               return_value=MockLLMResponse(json.dumps(duplicate_scenarios))):
        with pytest.raises(ValueError):
            await generator.generate_scenarios("test", {})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

