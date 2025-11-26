#!/usr/bin/env python3
"""
Test emergency synthesis functionality
"""

import asyncio
import json
import sys
import os

# Add project to path
sys.path.insert(0, os.path.abspath('.'))

from src.qnwis.orchestration.legendary_debate_orchestrator import LegendaryDebateOrchestrator
from src.qnwis.llm.client import LLMClient
from src.qnwis.llm.config import get_llm_config

async def test_emergency_synthesis():
    """Test emergency synthesis with mock debate history"""
    
    print("="*80)
    print("EMERGENCY SYNTHESIS TEST")
    print("="*80)
    
    # Get LLM config
    llm_config = get_llm_config()
    
    # Mock LLM client with stub provider
    llm_client = LLMClient(provider="stub", config=llm_config)
    
    # Mock event callback
    async def mock_callback(stage, status, payload=None, latency=0):
        pass
    
    # Create orchestrator
    orchestrator = LegendaryDebateOrchestrator(
        emit_event_fn=mock_callback,
        llm_client=llm_client
    )
    
    # Mock debate history with actual agent contributions
    debate_history = [
        {
            "agent": "MicroEconomist",
            "message": "## Cost Analysis: $15B Investment\n\nFrom a microeconomic perspective, this investment shows concerning inefficiencies. Production costs are 3-5x higher than imports due to Qatar's harsh climate and water scarcity (7 cubic meters per capita annually). The opportunity cost is significant - this capital could yield higher returns in other sectors aligned with Qatar's comparative advantages.",
            "type": "opening_statement",
            "turn": 1
        },
        {
            "agent": "MacroEconomist",
            "message": "## Strategic Security Assessment\n\nWhile microeconomic concerns about cost efficiency are valid, they miss the strategic dimension. Qatar's 90% food import dependency creates systemic vulnerability during geopolitical crises (as seen in 2017 blockade). The $15B investment (6.4% of GDP) must be evaluated against the cost of food security failure, which is effectively infinite. National resilience is not captured in NPV calculations.",
            "type": "opening_statement",
            "turn": 2
        },
        {
            "agent": "MicroEconomist",
            "message": "## Challenge to Strategic Premium Argument\n\nThe strategic security argument assumes this investment is the only path to resilience. However, diversified import partnerships, strategic reserves, and regional trade agreements offer more cost-effective risk mitigation. The blockade was resolved through diplomacy, not agriculture. Investing $15B in low-efficiency domestic production locks in high costs permanently rather than building flexible alternatives.",
            "type": "challenge",
            "turn": 5
        },
        {
            "agent": "MacroEconomist",
            "message": "## Defense: Strategic Options Value\n\nImport diversification still leaves Qatar dependent on external suppliers - the risk type changes but doesn't disappear. Domestic capacity provides optionality: it can be scaled up during crises and scaled down during stability. The economic value of this insurance policy isn't captured in static ROI calculations. Climate change and supply chain disruptions are increasing, making self-sufficiency more valuable over time.",
            "type": "defense",
            "turn": 6
        },
        {
            "agent": "SkillsAgent",
            "message": "Workforce analysis shows significant training gaps. Agricultural technology requires specialized skills Qatar currently lacks. Estimated 2,500+ new positions needing 18-24 months training. Brain drain risk if salaries don't compete with oil/gas sector.",
            "type": "supporting_analysis",
            "turn": 10
        }
    ]
    
    agents_invoked = ["MicroEconomist", "MacroEconomist", "SkillsAgent", "Nationalization", "PatternDetective"]
    
    print(f"\nTest Setup:")
    print(f"  - Debate turns: {len(debate_history)}")
    print(f"  - Agents: {len(agents_invoked)}")
    print(f"  - MicroEconomist turns: {sum(1 for t in debate_history if t['agent'] == 'MicroEconomist')}")
    print(f"  - MacroEconomist turns: {sum(1 for t in debate_history if t['agent'] == 'MacroEconomist')}")
    
    # Generate emergency synthesis
    print(f"\n{'='*80}")
    print("GENERATING EMERGENCY SYNTHESIS...")
    print(f"{'='*80}\n")
    
    synthesis = await orchestrator.generate_emergency_synthesis(
        debate_history,
        agents_invoked
    )
    
    print(synthesis)
    print(f"\n{'='*80}")
    
    # Verify structure
    print("\nVERIFYING SYNTHESIS STRUCTURE...")
    print(f"{'='*80}")
    
    checks = {
        "Contains MicroEconomist section": "MicroEconomist" in synthesis,
        "Contains MacroEconomist section": "MacroEconomist" in synthesis,
        "Contains Recommendation section": "Recommendation" in synthesis,
        "Contains Confidence level": "Confidence" in synthesis or "confidence" in synthesis,
        "Contains emergency warning": "Emergency" in synthesis or "Timeout" in synthesis,
        "Length > 200 chars": len(synthesis) > 200
    }
    
    all_passed = True
    for check, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check}")
        if not result:
            all_passed = False
    
    print(f"\n{'='*80}")
    if all_passed:
        print("✅ EMERGENCY SYNTHESIS TEST PASSED")
        print(f"{'='*80}")
        return 0
    else:
        print("❌ EMERGENCY SYNTHESIS TEST FAILED")
        print(f"{'='*80}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(test_emergency_synthesis())
    sys.exit(exit_code)
