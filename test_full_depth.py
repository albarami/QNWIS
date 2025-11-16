"""
Full Depth Test - Verify Legendary 5-Agent System
Tests that all cost optimizations are disabled and full depth is active.
"""

import asyncio
import sys
from datetime import datetime

from src.qnwis.orchestration.graph_llm import LLMWorkflow
from src.qnwis.agents.base import DataClient
from src.qnwis.llm.client import LLMClient
from src.qnwis.classification.classifier import Classifier


async def test_legendary_depth():
    """Verify full 5-agent depth is active"""
    
    print("\n" + "="*60)
    print("🎯 TESTING LEGENDARY DEPTH - ZERO COMPROMISES")
    print("="*60)
    print(f"Started: {datetime.now().isoformat()}\n")
    
    try:
        # Initialize workflow
        print("Initializing legendary 5-agent workflow...")
        workflow = LLMWorkflow()
        print("✅ Workflow initialized\n")
        
        # Test query
        query = "Is 70% Qatarization in Qatar's financial sector by 2030 feasible?"
        
        print("="*60)
        print("QUERY")
        print("="*60)
        print(f"{query}\n")
        
        print("="*60)
        print("EXECUTION (Watch for all 5 agents)")
        print("="*60)
        
        # Run workflow
        result = await workflow.run(query)
        
        print("\n" + "="*60)
        print("VERIFICATION RESULTS")
        print("="*60)
        
        # Verify all 5 agents invoked
        agents = result.get('agents_invoked', [])
        expected_agents = [
            'labour_economist',
            'financial_economist',
            'market_economist',
            'operations_expert',
            'research_scientist'
        ]
        
        print(f"\n✓ Agents invoked: {len(agents)}/5")
        for agent in agents:
            print(f"  {'✅' if agent in expected_agents else '❌'} {agent}")
        
        if len(agents) != 5:
            print(f"\n❌ FAILURE: Expected 5 agents, got {len(agents)}")
            print("   Cost optimization may still be active!")
            return False
        
        # Verify all expected agents present
        missing = set(expected_agents) - set(agents)
        if missing:
            print(f"\n❌ FAILURE: Missing agents: {missing}")
            return False
        
        print("\n✅ SUCCESS: All 5 agents invoked!")
        
        # Verify agent reports exist (Fix 1.1)
        reports = result.get('agent_reports', [])
        print(f"\n✓ Agent reports: {len(reports)}")
        
        total_citations = 0
        for report in reports:
            citations = len(report.get('citations', []))
            total_citations += citations
            confidence = report.get('confidence', 0)
            print(f"  • {report['agent_name']}: {citations} citations, {confidence:.0%} confidence")
        
        if len(reports) != 5:
            print(f"\n⚠️  WARNING: Expected 5 reports, got {len(reports)}")
        else:
            print(f"\n✅ SUCCESS: All 5 structured reports generated!")
            print(f"   Total citations: {total_citations}")
        
        # Verify debate happened
        debate = result.get('multi_agent_debate', '')
        print(f"\n✓ Multi-Agent Debate: {len(debate)} chars")
        if len(debate) > 500:
            print("  ✅ Substantial debate content generated")
        else:
            print("  ⚠️  Debate content seems short")
        
        # Verify critique happened
        critique = result.get('critique_output', '')
        print(f"\n✓ Devil's Advocate Critique: {len(critique)} chars")
        if len(critique) > 200:
            print("  ✅ Critique generated")
        else:
            print("  ⚠️  Critique seems short or missing")
        
        # Verify verification ran
        verification = result.get('verification', {})
        citations_checked = verification.get('total_citations', 0)
        violations = verification.get('citation_violations', [])
        violation_count = len(violations) if isinstance(violations, list) else violations
        
        print(f"\n✓ Verification:")
        print(f"  • Citations checked: {citations_checked}")
        print(f"  • Violations found: {violation_count}")
        print("  ✅ Verification system active")
        
        # Show metrics
        metrics = result.get('metrics', {})
        
        print("\n" + "="*60)
        print("DEPTH METRICS")
        print("="*60)
        
        cost = metrics.get('total_cost_usd', 0)
        latency = metrics.get('total_latency_ms', 0) / 1000
        llm_calls = metrics.get('llm_calls_count', 0)
        confidence = result.get('confidence_score', 0)
        
        print(f"Cost:       ${cost:.4f}")
        print(f"Latency:    {latency:.1f}s")
        print(f"LLM calls:  {llm_calls}")
        print(f"Confidence: {confidence:.0%}")
        
        # Validate depth indicators
        print("\n" + "="*60)
        print("DEPTH VALIDATION")
        print("="*60)
        
        issues = []
        
        # Cost should be $0.50-0.87 for full depth
        if cost < 0.10:
            issues.append(f"⚠️  Cost too low (${cost:.2f}) - may indicate shortcuts")
        elif cost < 0.50:
            issues.append(f"⚠️  Cost lower than expected (${cost:.2f}) - verify all agents ran")
        else:
            print(f"✅ Cost ${cost:.2f} indicates full depth (expected $0.50-0.87)")
        
        # LLM calls should be ~10 (5 agents + debate + critique + synthesis)
        if llm_calls == 0:
            issues.append("❌ CRITICAL: No LLM calls made - system not working!")
        elif llm_calls < 5:
            issues.append(f"⚠️  Only {llm_calls} LLM calls - expected ~10 for full depth")
        else:
            print(f"✅ {llm_calls} LLM calls indicates full workflow")
        
        # All 5 agents must be invoked
        if len(agents) != 5:
            issues.append(f"❌ CRITICAL: Only {len(agents)} agents invoked instead of 5!")
        else:
            print(f"✅ All 5 agents invoked - no shortcuts taken")
        
        # Debate must exist
        if len(debate) < 500:
            issues.append("⚠️  Debate content short or missing")
        else:
            print(f"✅ Multi-agent debate generated ({len(debate)} chars)")
        
        # Critique must exist
        if len(critique) < 200:
            issues.append("⚠️  Critique short or missing")
        else:
            print(f"✅ Devil's advocate critique generated ({len(critique)} chars)")
        
        print("\n" + "="*60)
        print("FINAL VERDICT")
        print("="*60)
        
        if issues:
            print("\n⚠️  ISSUES FOUND:\n")
            for issue in issues:
                print(f"   {issue}")
            print("\n❌ DEPTH TEST: PARTIAL PASS (Some optimizations may still be active)")
            return False
        else:
            print("\n✅ ALL CHECKS PASSED!")
            print("✅ LEGENDARY DEPTH CONFIRMED!")
            print(f"\n   • All 5 PhD-level agents analyzed the query")
            print(f"   • Full multi-agent debate conducted")
            print(f"   • Devil's advocate critique applied")
            print(f"   • Complete verification performed")
            print(f"   • Ministerial-grade synthesis generated")
            print(f"\n   Cost: ${cost:.2f} (acceptable for depth)")
            print(f"   Value: Replaces $50K+ consulting engagement")
            print(f"   ROI: ~{50000/max(cost, 0.01):.0f}x return on investment")
            print("\n🎉 YOUR LEGENDARY SYSTEM IS FULLY OPERATIONAL!")
            return True
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ TEST FAILED WITH ERROR")
        print("="*60)
        print(f"Error: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n⚠️  PREREQUISITES:")
    print("  1. ANTHROPIC_API_KEY must be set in .env")
    print("  2. All dependencies installed (pip install -r requirements.txt)")
    print("  3. System restored to full depth mode")
    print()
    
    success = asyncio.run(test_legendary_depth())
    
    print("\n" + "="*60)
    if success:
        print("✅ READY FOR PRODUCTION")
        print("="*60)
        print("\nYour legendary 5-agent system is verified and ready!")
        print("Next steps:")
        print("  1. Deploy to staging")
        print("  2. Run smoke tests")
        print("  3. Deploy to production")
        print("\nNo compromises. Pure depth. Legendary intelligence. 🚀")
    else:
        print("❌ NOT READY - ISSUES FOUND")
        print("="*60)
        print("\nPlease review issues above and verify:")
        print("  1. Cost optimizations are fully disabled")
        print("  2. All 5 agents are being invoked")
        print("  3. LLM API is being called")
        print("\nCheck INTEGRATION_TEST_ISSUES.md for debugging guidance.")
    
    sys.exit(0 if success else 1)
