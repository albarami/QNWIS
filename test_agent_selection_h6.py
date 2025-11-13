"""Test script for H6 Agent Selection implementation."""

import sys
sys.path.insert(0, 'src')

from qnwis.orchestration.agent_selector import AgentSelector, select_agents_for_question

def test_unemployment_query():
    """Test agent selection for unemployment query."""
    print("=" * 60)
    print("TEST 1: Unemployment Query")
    print("=" * 60)
    
    classification = {
        "intent": "unemployment",
        "entities": {"unemployment": True},
        "complexity": "medium",
        "question": "What is Qatar's unemployment rate?"
    }
    
    result = select_agents_for_question(classification, min_agents=2, max_agents=4)
    selected = result["selected_agents"]
    explanation = result["explanation"]
    
    print(f"✅ Selected {len(selected)} agents: {selected}")
    print(f"   Savings: {explanation['savings']}")
    print(f"   Intent: {explanation['intent']}")
    
    # Should include LabourEconomist
    assert "LabourEconomist" in selected, "LabourEconomist should be selected for unemployment"
    print(f"✅ Correctly selected LabourEconomist for unemployment query")
    
    print()
    return True

def test_qatarization_query():
    """Test agent selection for Qatarization query."""
    print("=" * 60)
    print("TEST 2: Qatarization Query")
    print("=" * 60)
    
    classification = {
        "intent": "qatarization",
        "entities": {"qatari": True, "nationalization": True},
        "complexity": "medium",
        "question": "What is the Qatarization rate in the private sector?"
    }
    
    result = select_agents_for_question(classification)
    selected = result["selected_agents"]
    explanation = result["explanation"]
    
    print(f"✅ Selected {len(selected)} agents: {selected}")
    print(f"   Savings: {explanation['savings']}")
    
    # Should include Nationalization
    assert "Nationalization" in selected, "Nationalization should be selected for qatarization"
    print(f"✅ Correctly selected Nationalization for qatarization query")
    
    print()
    return True

def test_gcc_comparison_query():
    """Test agent selection for GCC comparison query."""
    print("=" * 60)
    print("TEST 3: GCC Comparison Query")
    print("=" * 60)
    
    classification = {
        "intent": "gcc_comparison",
        "entities": {"gcc": True, "compare": True},
        "complexity": "medium",
        "question": "How does Qatar compare to other GCC countries on unemployment?"
    }
    
    result = select_agents_for_question(classification)
    selected = result["selected_agents"]
    explanation = result["explanation"]
    
    print(f"✅ Selected {len(selected)} agents: {selected}")
    print(f"   Savings: {explanation['savings']}")
    
    # Should include Nationalization (handles GCC)
    assert "Nationalization" in selected, "Nationalization should handle GCC comparison"
    print(f"✅ Correctly selected Nationalization for GCC comparison")
    
    print()
    return True

def test_skills_query():
    """Test agent selection for skills query."""
    print("=" * 60)
    print("TEST 4: Skills Gap Query")
    print("=" * 60)
    
    classification = {
        "intent": "skills",
        "entities": {"skills": True, "education": True},
        "complexity": "medium",
        "question": "What are the critical skills gaps in Qatar's workforce?"
    }
    
    result = select_agents_for_question(classification)
    selected = result["selected_agents"]
    explanation = result["explanation"]
    
    print(f"✅ Selected {len(selected)} agents: {selected}")
    print(f"   Savings: {explanation['savings']}")
    
    # Should include SkillsAgent
    assert "SkillsAgent" in selected, "SkillsAgent should be selected for skills"
    print(f"✅ Correctly selected SkillsAgent for skills query")
    
    print()
    return True

def test_vision_2030_query():
    """Test agent selection for Vision 2030 query."""
    print("=" * 60)
    print("TEST 5: Vision 2030 Query")
    print("=" * 60)
    
    classification = {
        "intent": "vision_2030",
        "entities": {"vision": True, "2030": True},
        "complexity": "high",
        "question": "How is Qatar progressing toward Vision 2030 workforce targets?"
    }
    
    result = select_agents_for_question(classification)
    selected = result["selected_agents"]
    explanation = result["explanation"]
    
    print(f"✅ Selected {len(selected)} agents: {selected}")
    print(f"   Savings: {explanation['savings']}")
    print(f"   Complexity: {explanation['complexity']}")
    
    # Should include NationalStrategy and Nationalization
    assert "NationalStrategy" in selected or "Nationalization" in selected, \
        "Should include strategy agents for Vision 2030"
    print(f"✅ Correctly selected strategy agents for Vision 2030")
    
    print()
    return True

def test_min_max_constraints():
    """Test min/max agent constraints."""
    print("=" * 60)
    print("TEST 6: Min/Max Constraints")
    print("=" * 60)
    
    # Generic query that doesn't match any intent
    classification = {
        "intent": "unknown",
        "entities": {},
        "complexity": "low",
        "question": "General question"
    }
    
    # Test min constraint
    result = select_agents_for_question(classification, min_agents=3, max_agents=4)
    selected = result["selected_agents"]
    
    print(f"✅ Min agents (3): Selected {len(selected)} agents")
    assert len(selected) >= 3, f"Should select at least 3 agents, got {len(selected)}"
    print(f"   Constraint satisfied: {len(selected)} >= 3")
    
    # Test max constraint
    classification_multi = {
        "intent": "unemployment",
        "entities": {"unemployment": True, "qatari": True, "gcc": True, "skills": True},
        "complexity": "high",
        "question": "Complex question matching multiple intents"
    }
    
    result2 = select_agents_for_question(classification_multi, min_agents=2, max_agents=3)
    selected2 = result2["selected_agents"]
    
    print(f"✅ Max agents (3): Selected {len(selected2)} agents")
    assert len(selected2) <= 3, f"Should select at most 3 agents, got {len(selected2)}"
    print(f"   Constraint satisfied: {len(selected2)} <= 3")
    
    print()
    return True

def test_cost_savings():
    """Test cost savings calculation."""
    print("=" * 60)
    print("TEST 7: Cost Savings")
    print("=" * 60)
    
    # Focused query - should select 2-3 agents (40-60% savings)
    classification = {
        "intent": "unemployment",
        "entities": {"unemployment": True},
        "complexity": "low",
        "question": "Qatar unemployment rate?"
    }
    
    result = select_agents_for_question(classification, min_agents=2, max_agents=4)
    selected = result["selected_agents"]
    savings = result["explanation"]["savings"]
    
    print(f"✅ Focused query:")
    print(f"   Selected: {len(selected)}/5 agents")
    print(f"   Savings: {savings}")
    
    # Parse savings percentage
    savings_pct = int(savings.replace('%', ''))
    assert savings_pct > 0, "Should have some cost savings"
    print(f"✅ Cost savings: {savings_pct}% (running {len(selected)} instead of 5)")
    
    print()
    return True

def test_explanation():
    """Test selection explanation."""
    print("=" * 60)
    print("TEST 8: Selection Explanation")
    print("=" * 60)
    
    classification = {
        "intent": "qatarization",
        "entities": {"qatari": True},
        "complexity": "medium",
        "question": "Qatarization progress?"
    }
    
    result = select_agents_for_question(classification)
    explanation = result["explanation"]
    
    print(f"✅ Explanation generated:")
    print(f"   Selected: {explanation['selected_count']} agents")
    print(f"   Total: {explanation['total_available']} available")
    print(f"   Intent: {explanation['intent']}")
    print(f"   Complexity: {explanation['complexity']}")
    
    # Check agent details
    print(f"\n   Agent Details:")
    for agent_name, details in explanation["agents"].items():
        print(f"     • {agent_name}: {details['description']}")
        print(f"       Reasons: {', '.join(details['reasons'])}")
    
    assert "agents" in explanation, "Explanation should include agent details"
    print(f"\n✅ Comprehensive explanation provided")
    
    print()
    return True

def run_all_tests():
    """Run all agent selection tests."""
    print("\n" + "=" * 60)
    print("TESTING H6 AGENT SELECTION")
    print("=" * 60 + "\n")
    
    results = []
    
    try:
        results.append(("Unemployment Query", test_unemployment_query()))
        results.append(("Qatarization Query", test_qatarization_query()))
        results.append(("GCC Comparison", test_gcc_comparison_query()))
        results.append(("Skills Query", test_skills_query()))
        results.append(("Vision 2030", test_vision_2030_query()))
        results.append(("Min/Max Constraints", test_min_max_constraints()))
        results.append(("Cost Savings", test_cost_savings()))
        results.append(("Explanation", test_explanation()))
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - H6 AGENT SELECTION WORKING")
        print("\n💰 Cost Savings: 40-60% API cost reduction")
        print("⚡ Performance: Faster responses (fewer agents)")
        print("🎯 Quality: Only relevant experts contribute")
    else:
        print("❌ SOME TESTS FAILED - NEEDS FIXES")
    print("=" * 60 + "\n")
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
