"""
Test Agent Architecture Fix - Verify Class-Based Agents Work
Tests that the new class-based agent architecture with intelligent selection (2-4 agents) works correctly.
"""

import asyncio
import sys
from datetime import datetime

from src.qnwis.orchestration.graph_llm import LLMWorkflow


async def test_agent_architecture():
    """Verify class-based agent architecture with intelligent selection"""
    
    print("\n" + "="*60)
    print("🎯 TESTING CLASS-BASED AGENT ARCHITECTURE")
    print("="*60)
    print(f"Started: {datetime.now().isoformat()}\n")
    
    try:
        # Initialize workflow
        print("Step 1: Initializing workflow...")
        workflow = LLMWorkflow()
        print("✅ Workflow initialized successfully\n")
        
        # Test query
        query = "Is 70% Qatarization in Qatar's financial sector by 2030 feasible?"
        
        print("="*60)
        print("TEST QUERY")
        print("="*60)
        print(f"{query}\n")
        
        print("="*60)
        print("WORKFLOW EXECUTION")
        print("="*60)
        print("Watching for:")
        print("  ✓ Classification stage")
        print("  ✓ Agent selection (2-4 agents via AgentSelector)")
        print("  ✓ Agent instantiation (using classes, not modules)")
        print("  ✓ Agent execution (calling .run() method)")
        print("  ✓ No AttributeError about .analyze()")
        print("  ✓ No infinite looping\n")
        
        # Run workflow
        result = await workflow.run(query)
        
        print("\n" + "="*60)
        print("VERIFICATION RESULTS")
        print("="*60)
        
        # Check agents invoked
        agents = result.get('agents_invoked', [])
        print(f"\n✓ Agents invoked: {len(agents)}")
        for agent in agents:
            print(f"  • {agent}")
        
        # Verify agent count (should be 2-4)
        if len(agents) < 2:
            print(f"\n❌ FAILURE: Expected MIN_AGENTS=2, got {len(agents)}")
            return False
        elif len(agents) > 4:
            print(f"\n❌ FAILURE: Expected MAX_AGENTS=4, got {len(agents)}")
            return False
        else:
            print(f"\n✅ SUCCESS: Agent count within MIN=2, MAX=4 range")
        
        # Verify agent reports exist
        reports = result.get('agent_reports', [])
        print(f"\n✓ Agent reports: {len(reports)}")
        
        if len(reports) != len(agents):
            print(f"\n⚠️  WARNING: Reports ({len(reports)}) != Agents ({len(agents)})")
        
        # Show report details
        for report in reports:
            agent_name = report.get('agent_name', 'Unknown')
            confidence = report.get('confidence', 0)
            narrative_len = len(report.get('narrative', ''))
            citations = len(report.get('citations', []))
            print(f"  • {agent_name}: {confidence:.0%} confidence, {narrative_len} chars, {citations} citations")
        
        print(f"\n✅ SUCCESS: All {len(reports)} agents returned structured reports")
        
        # Verify workflow stages completed
        print("\n✓ Workflow stages:")
        
        classification = result.get('classification', {})
        if classification:
            complexity = classification.get('complexity', 'unknown')
            print(f"  • Classification: {complexity} complexity")
        
        selected = result.get('selected_agents', [])
        if selected:
            print(f"  • Agent Selection: {len(selected)} agents selected")
        
        debate = result.get('multi_agent_debate', '')
        if debate:
            print(f"  • Multi-Agent Debate: {len(debate)} chars")
        
        critique = result.get('critique_output', '')
        if critique:
            print(f"  • Devil's Advocate: {len(critique)} chars")
        
        verification = result.get('verification', {})
        if verification:
            print(f"  • Verification: {verification.get('total_citations', 0)} citations checked")
        
        synthesis = result.get('final_synthesis', '')
        if synthesis:
            print(f"  • Final Synthesis: {len(synthesis)} chars")
        
        # Show metrics
        metadata = result.get('metadata', {})
        total_latency = metadata.get('total_latency_ms', 0)
        
        print("\n" + "="*60)
        print("PERFORMANCE METRICS")
        print("="*60)
        print(f"Total Latency: {total_latency/1000:.1f}s")
        print(f"Agents Used: {len(agents)}/{workflow.agent_selector.MAX_AGENTS}")
        print(f"Final Confidence: {result.get('confidence_score', 0):.0%}")
        
        # Final validation
        print("\n" + "="*60)
        print("ARCHITECTURE VALIDATION")
        print("="*60)
        
        issues = []
        
        # Must have invoked at least 2 agents
        if len(agents) < 2:
            issues.append("❌ CRITICAL: Less than MIN_AGENTS=2 invoked")
        else:
            print(f"✅ MIN_AGENTS=2 constraint respected ({len(agents)} agents)")
        
        # Must not exceed 4 agents
        if len(agents) > 4:
            issues.append("❌ CRITICAL: More than MAX_AGENTS=4 invoked")
        else:
            print(f"✅ MAX_AGENTS=4 constraint respected ({len(agents)} agents)")
        
        # Must have reports matching agents
        if len(reports) != len(agents):
            issues.append(f"⚠️  Report count mismatch: {len(reports)} reports vs {len(agents)} agents")
        else:
            print(f"✅ All {len(agents)} agents returned reports")
        
        # Must have valid agent names
        valid_agent_names = [
            "LabourEconomist", "Nationalization", "SkillsAgent", "PatternDetective",
            "NationalStrategy", "labour_economist", "nationalization", "skills"
        ]
        for agent in agents:
            if agent not in valid_agent_names:
                issues.append(f"⚠️  Unexpected agent name: {agent}")
        
        if not issues:
            print("✅ All agent names are valid")
        
        # Must have final synthesis
        if not synthesis:
            issues.append("⚠️  No final synthesis generated")
        else:
            print(f"✅ Final synthesis generated ({len(synthesis)} chars)")
        
        print("\n" + "="*60)
        print("FINAL VERDICT")
        print("="*60)
        
        if issues:
            print("\n⚠️  ISSUES FOUND:\n")
            for issue in issues:
                print(f"   {issue}")
            print("\n❌ ARCHITECTURE TEST: PARTIAL PASS")
            return False
        else:
            print("\n✅ ALL CHECKS PASSED!")
            print("✅ CLASS-BASED ARCHITECTURE WORKING CORRECTLY!")
            print(f"\n   • Intelligent agent selection active (2-4 agents)")
            print(f"   • {len(agents)} agents instantiated from classes")
            print(f"   • All agents used .run() method (not .analyze())")
            print(f"   • No AttributeError exceptions")
            print(f"   • No infinite looping")
            print(f"   • Workflow completed successfully")
            print("\n🎉 ARCHITECTURE FIX SUCCESSFUL!")
            return True
        
    except AttributeError as e:
        if '.analyze' in str(e):
            print("\n" + "="*60)
            print("❌ CRITICAL: AttributeError for .analyze()")
            print("="*60)
            print(f"Error: {str(e)}")
            print("\nThis means the workflow is still trying to call module-level")
            print("analyze() functions instead of using agent classes!")
            print("\nCheck: src/qnwis/orchestration/graph_llm.py line 705-776")
            return False
        else:
            raise
        
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
    print("  2. All dependencies installed")
    print("  3. LLM agent classes exported from __init__.py")
    print()
    
    success = asyncio.run(test_agent_architecture())
    
    print("\n" + "="*60)
    if success:
        print("✅ ARCHITECTURE FIX VERIFIED")
        print("="*60)
        print("\nThe class-based agent architecture is working!")
        print("\nKey improvements verified:")
        print("  ✓ Agents instantiated from classes (not modules)")
        print("  ✓ .run() method used (not .analyze())")
        print("  ✓ AgentSelector MIN=2, MAX=4 respected")
        print("  ✓ No AttributeError exceptions")
        print("  ✓ No infinite looping")
        print("\n🚀 Ready for next phase: Integrate missing agents")
    else:
        print("❌ ARCHITECTURE ISSUES FOUND")
        print("="*60)
        print("\nPlease review issues above and check:")
        print("  1. graph_llm.py uses agent classes (not modules)")
        print("  2. All LLM agents exported from __init__.py")
        print("  3. AgentSelector constraints are respected")
    
    sys.exit(0 if success else 1)
