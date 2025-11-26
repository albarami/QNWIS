"""
Unit tests for Meta-Synthesis Node.

Tests cross-scenario synthesis to identify robust recommendations and uncertainties.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from qnwis.orchestration.nodes.meta_synthesis import (
    meta_synthesis_node,
    _extract_scenario_summaries,
    _build_synthesis_prompt,
    _format_scenarios,
    _validate_synthesis,
    _emergency_synthesis
)


class MockLLMResponse:
    """Mock LLM response"""
    def __init__(self, content):
        self.content = content


@pytest.mark.asyncio
async def test_meta_synthesis_with_consensus():
    """Test meta-synthesis when all scenarios agree."""
    scenario_results = [
        {
            'scenario_id': 's1',
            'scenario_metadata': {
                'id': 's1',
                'name': 'Base Case',
                'description': 'Current trends',
                'modified_assumptions': {'oil_price': 75}
            },
            'final_synthesis': 'Recommendation: Invest in technology hub',
            'confidence_score': 0.85,
            'scenario_execution_time': 45.0,
            'warnings': [],
            'reasoning_chain': ['step1', 'step2', 'step3']
        },
        {
            'scenario_id': 's2',
            'scenario_metadata': {
                'id': 's2',
                'name': 'High Competition',
                'description': 'Intense GCC competition',
                'modified_assumptions': {'gcc_competition': 'high'}
            },
            'final_synthesis': 'Recommendation: Invest in technology hub with differentiation',
            'confidence_score': 0.80,
            'scenario_execution_time': 50.0,
            'warnings': [],
            'reasoning_chain': ['step1', 'step2']
        }
    ]
    
    mock_synthesis = """# META-SYNTHESIS: CROSS-SCENARIO STRATEGIC INTELLIGENCE

## ROBUST RECOMMENDATIONS (High Confidence)
- Invest in technology hub (consensus across all scenarios)

## SCENARIO-DEPENDENT STRATEGIES
- IF competition intensifies, THEN differentiate via specialization

## KEY UNCERTAINTIES & RISK FACTORS
- GCC competition level

## EARLY WARNING INDICATORS
- Monitor UAE and Saudi tech hub announcements

## FINAL STRATEGIC GUIDANCE
- Immediate action: Launch technology hub feasibility study
"""
    
    with patch('qnwis.orchestration.llm_wrapper.call_llm_with_rate_limit',
               return_value=MockLLMResponse(mock_synthesis)):
        synthesis = await meta_synthesis_node(scenario_results)
    
    # Verify synthesis contains expected sections
    assert "ROBUST RECOMMENDATIONS" in synthesis
    assert "SCENARIO-DEPENDENT" in synthesis
    assert "UNCERTAINTIES" in synthesis
    assert "technology hub" in synthesis.lower()


@pytest.mark.asyncio
async def test_meta_synthesis_with_divergence():
    """Test meta-synthesis when scenarios have different recommendations."""
    scenario_results = [
        {
            'scenario_id': 's1',
            'scenario_metadata': {
                'id': 's1',
                'name': 'High Oil',
                'description': 'High oil prices',
                'modified_assumptions': {'oil_price': 100}
            },
            'final_synthesis': 'Recommendation: Financial hub',
            'confidence_score': 0.90,
            'scenario_execution_time': 40.0,
            'warnings': [],
            'reasoning_chain': ['step1']
        },
        {
            'scenario_id': 's2',
            'scenario_metadata': {
                'id': 's2',
                'name': 'Low Oil',
                'description': 'Oil price shock',
                'modified_assumptions': {'oil_price': 45}
            },
            'final_synthesis': 'Recommendation: Technology hub for diversification',
            'confidence_score': 0.75,
            'scenario_execution_time': 42.0,
            'warnings': [],
            'reasoning_chain': ['step1']
        }
    ]
    
    mock_synthesis = """# META-SYNTHESIS

## ROBUST RECOMMENDATIONS
- Diversify economy (consensus)

## SCENARIO-DEPENDENT STRATEGIES
- IF oil prices high: Financial hub
- IF oil prices low: Technology hub
"""
    
    with patch('qnwis.orchestration.llm_wrapper.call_llm_with_rate_limit',
               return_value=MockLLMResponse(mock_synthesis)):
        synthesis = await meta_synthesis_node(scenario_results)
    
    assert "SCENARIO-DEPENDENT" in synthesis
    assert len(synthesis) > 100


@pytest.mark.asyncio
async def test_robust_recommendations_extraction():
    """Test that robust recommendations across scenarios are identified."""
    # Both scenarios recommend diversification
    scenario_results = [
        {
            'scenario_id': 's1',
            'scenario_metadata': {'id': 's1', 'name': 'Scenario 1', 'description': 'desc1', 'modified_assumptions': {}},
            'final_synthesis': 'Diversify economy and build human capital',
            'confidence_score': 0.85,
            'scenario_execution_time': 40.0,
            'warnings': [],
            'reasoning_chain': []
        },
        {
            'scenario_id': 's2',
            'scenario_metadata': {'id': 's2', 'name': 'Scenario 2', 'description': 'desc2', 'modified_assumptions': {}},
            'final_synthesis': 'Diversify economy and strengthen institutions',
            'confidence_score': 0.80,
            'scenario_execution_time': 41.0,
            'warnings': [],
            'reasoning_chain': []
        }
    ]
    
    mock_synthesis = """# META-SYNTHESIS

## ROBUST RECOMMENDATIONS
- Diversify economy (appears in ALL scenarios)

## KEY UNCERTAINTIES & RISK FACTORS
- Implementation approach varies by scenario
"""
    
    with patch('qnwis.orchestration.llm_wrapper.call_llm_with_rate_limit',
               return_value=MockLLMResponse(mock_synthesis)):
        synthesis = await meta_synthesis_node(scenario_results)
    
    # Should identify diversification as robust across scenarios
    assert "ROBUST" in synthesis
    assert "ALL scenarios" in synthesis or "consensus" in synthesis.lower()


def test_extract_scenario_summaries():
    """Test scenario summary extraction."""
    scenario_results = [
        {
            'scenario_id': 's1',
            'scenario_metadata': {
                'id': 's1',
                'name': 'Test Scenario',
                'description': 'Test description',
                'modified_assumptions': {'x': 1}
            },
            'final_synthesis': 'Test synthesis result',
            'confidence_score': 0.85,
            'scenario_execution_time': 45.0,
            'warnings': ['warning1'],
            'reasoning_chain': ['step1', 'step2', 'step3']
        }
    ]
    
    summaries = _extract_scenario_summaries(scenario_results)
    
    assert len(summaries) == 1
    assert summaries[0]['id'] == 's1'
    assert summaries[0]['name'] == 'Test Scenario'
    assert summaries[0]['confidence'] == 0.85
    assert summaries[0]['reasoning_depth'] == 3


def test_format_scenarios():
    """Test scenario formatting for prompt."""
    summaries = [
        {
            'name': 'Base Case',
            'description': 'Current trends continue',
            'assumptions': {'oil_price': 75},
            'confidence': 0.85,
            'execution_time': 45.0,
            'recommendation': 'Invest in tech hub',
            'warnings': []
        },
        {
            'name': 'Oil Shock',
            'description': 'Low oil prices',
            'assumptions': {'oil_price': 45},
            'confidence': 0.75,
            'execution_time': 50.0,
            'recommendation': 'Diversify rapidly',
            'warnings': ['High risk']
        }
    ]
    
    formatted = _format_scenarios(summaries)
    
    # Verify contains key information
    assert "SCENARIO 1: Base Case" in formatted
    assert "SCENARIO 2: Oil Shock" in formatted
    assert "85%" in formatted  # Confidence
    assert "75%" in formatted  # Confidence
    assert "oil_price" in formatted


def test_validate_synthesis():
    """Test synthesis validation."""
    # Valid synthesis
    valid_synthesis = """# META-SYNTHESIS

## ROBUST RECOMMENDATIONS
- Action 1

## SCENARIO-DEPENDENT STRATEGIES  
- If X then Y

## KEY UNCERTAINTIES
- Uncertainty 1

## EARLY WARNING INDICATORS
- Indicator 1

## FINAL STRATEGIC GUIDANCE
- Guidance 1
"""
    
    # Should not raise
    _validate_synthesis(valid_synthesis)
    
    # Too short should warn but not fail
    short_synthesis = "Too short"
    with pytest.raises(ValueError, match="too short"):
        _validate_synthesis(short_synthesis)
    
    # Empty should fail
    with pytest.raises(ValueError, match="empty"):
        _validate_synthesis("")


def test_emergency_synthesis():
    """Test emergency fallback synthesis."""
    scenario_results = [
        {
            'scenario_metadata': {'name': 'Scenario 1'},
            'confidence_score': 0.85,
            'final_synthesis': 'Result 1'
        },
        {
            'scenario_metadata': {'name': 'Scenario 2'},
            'confidence_score': 0.80,
            'final_synthesis': 'Result 2'
        }
    ]
    
    emergency = _emergency_synthesis(scenario_results, "Test error")
    
    # Should contain basic information
    assert "EMERGENCY SYNTHESIS" in emergency
    assert "Test error" in emergency
    assert "Scenario 1" in emergency
    assert "Scenario 2" in emergency
    assert "85%" in emergency or "80%" in emergency


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

