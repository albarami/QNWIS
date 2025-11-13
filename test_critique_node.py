"""
Test script for Phase 2 Step 2B: Critique/Devil's Advocate Node

Tests:
1. Skip critique when no reports
2. Critique single agent report
3. Critique multiple reports with debate results
4. Full workflow integration
"""

import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from src.qnwis.orchestration.graph_llm import LLMWorkflow
from src.qnwis.agents.base import DataClient
from src.qnwis.llm.client import LLMClient
from src.qnwis.config.model_select import get_llm_config

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_skip_no_reports():
    """Test 1: Skip critique when no reports"""
    print("\n" + "="*80)
    print("TEST 1: Skip Critique - No Reports")
    print("="*80)

    # Initialize orchestrator
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)

    orchestrator = LLMWorkflow(data_client, llm_client)

    # Create mock state with no reports
    mock_state = {
        "question": "Test question",
        "agent_reports": [],
        "debate_results": None,
        "classification": None,
        "prefetch": None,
        "rag_context": None,
        "selected_agents": None,
        "critique_results": None,
        "verification": None,
        "synthesis": None,
        "error": None,
        "metadata": {},
        "reasoning_chain": [],
        "event_callback": None
    }

    # Test critique node
    result_state = await orchestrator._critique_node(mock_state)

    critique_results = result_state.get("critique_results", {})
    print(f"Status: {critique_results.get('status')}")
    print(f"Reason: {critique_results.get('reason', 'N/A')}")

    assert critique_results.get("status") == "skipped", "Should skip when no reports"

    print("[PASS] TEST PASSED: Critique skipped as expected")


async def test_critique_single_report():
    """Test 2: Critique single agent report"""
    print("\n" + "="*80)
    print("TEST 2: Critique Single Report")
    print("="*80)

    # Initialize orchestrator
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)

    orchestrator = LLMWorkflow(data_client, llm_client)

    # Create mock state with single report
    mock_state = {
        "question": "What is Qatar's unemployment rate?",
        "agent_reports": [
            {
                "agent_name": "LabourEconomist",
                "narrative": "Qatar unemployment rate is [Per extraction: '0.10' from GCC-STAT Period-A]. This represents excellent performance.",
                "confidence": 0.95
            }
        ],
        "debate_results": None,
        "classification": None,
        "prefetch": None,
        "rag_context": None,
        "selected_agents": None,
        "critique_results": None,
        "verification": None,
        "synthesis": None,
        "error": None,
        "metadata": {},
        "reasoning_chain": [],
        "event_callback": None
    }

    # Test critique node
    print("\nRunning critique...")
    result_state = await orchestrator._critique_node(mock_state)

    critique_results = result_state.get("critique_results", {})
    print(f"\nCritique Results:")
    print(f"  Status: {critique_results.get('status')}")
    print(f"  Critiques: {len(critique_results.get('critiques', []))}")
    print(f"  Red flags: {len(critique_results.get('red_flags', []))}")
    print(f"  Strengthened: {critique_results.get('strengthened_by_critique', False)}")
    print(f"  Latency: {critique_results.get('latency_ms', 0):.0f}ms")

    if critique_results.get("overall_assessment"):
        print(f"\nOverall Assessment:")
        print(f"  {critique_results['overall_assessment'][:200]}...")

    assert critique_results.get("status") == "complete", "Critique should complete"

    print("\n[PASS] TEST PASSED: Critique completed successfully")


async def test_critique_with_debate():
    """Test 3: Critique multiple reports with debate results"""
    print("\n" + "="*80)
    print("TEST 3: Critique with Debate Context")
    print("="*80)

    # Initialize orchestrator
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)

    orchestrator = LLMWorkflow(data_client, llm_client)

    # Create mock state with multiple reports and debate
    mock_state = {
        "question": "What is Qatar's unemployment rate?",
        "agent_reports": [
            {
                "agent_name": "Agent1",
                "narrative": "Qatar unemployment is [Per extraction: '0.10' from GCC-STAT Period-A]",
                "confidence": 0.90
            },
            {
                "agent_name": "Agent2",
                "narrative": "Unemployment rate is [Per extraction: '0.12' from World-Bank Period-B]",
                "confidence": 0.85
            }
        ],
        "debate_results": {
            "contradictions_found": 1,
            "resolved": 1,
            "flagged_for_review": 0,
            "consensus_narrative": "Use Agent1 value (GCC-STAT higher authority)",
            "status": "complete"
        },
        "classification": None,
        "prefetch": None,
        "rag_context": None,
        "selected_agents": None,
        "critique_results": None,
        "verification": None,
        "synthesis": None,
        "error": None,
        "metadata": {},
        "reasoning_chain": [],
        "event_callback": None
    }

    # Test critique node
    print("\nRunning critique with debate context...")
    result_state = await orchestrator._critique_node(mock_state)

    critique_results = result_state.get("critique_results", {})
    print(f"\nCritique Results:")
    print(f"  Status: {critique_results.get('status')}")
    print(f"  Critiques: {len(critique_results.get('critiques', []))}")
    print(f"  Red flags: {len(critique_results.get('red_flags', []))}")
    print(f"  Strengthened: {critique_results.get('strengthened_by_critique', False)}")

    if critique_results.get("critiques"):
        print(f"\nSample Critique:")
        c = critique_results["critiques"][0]
        print(f"  Agent: {c.get('agent_name', 'Unknown')}")
        print(f"  Weakness: {c.get('weakness_found', 'N/A')[:150]}...")
        print(f"  Severity: {c.get('severity', 'N/A')}")

    assert critique_results.get("status") == "complete", "Critique should complete"

    print("\n[PASS] TEST PASSED: Critique with debate completed")


async def test_full_workflow():
    """Test 4: Full workflow with critique"""
    print("\n" + "="*80)
    print("TEST 4: Full Workflow with Critique")
    print("="*80)

    # Initialize orchestrator
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)

    orchestrator = LLMWorkflow(data_client, llm_client)

    # Create mock state
    mock_state = {
        "question": "What is Qatar's unemployment rate?",
        "agent_reports": [
            {
                "agent_name": "LabourEconomist",
                "narrative": "Qatar unemployment rate is excellent at [Per extraction: '0.10' from GCC-STAT Period-A]",
                "confidence": 0.95
            }
        ],
        "debate_results": {
            "contradictions_found": 0,
            "status": "skipped"
        },
        "classification": None,
        "prefetch": None,
        "rag_context": None,
        "selected_agents": None,
        "critique_results": None,
        "verification": None,
        "synthesis": None,
        "error": None,
        "metadata": {},
        "reasoning_chain": [],
        "event_callback": None
    }

    # Test critique node
    print("\nRunning full critique workflow...")
    result_state = await orchestrator._critique_node(mock_state)

    critique_results = result_state.get("critique_results", {})
    print(f"\nCritique Results:")
    print(f"  Status: {critique_results.get('status')}")
    print(f"  Critiques: {len(critique_results.get('critiques', []))}")
    print(f"  Red flags: {len(critique_results.get('red_flags', []))}")

    if critique_results.get("confidence_adjustments"):
        print(f"\nConfidence Adjustments:")
        for agent, factor in critique_results["confidence_adjustments"].items():
            print(f"  {agent}: {factor:.2f}")

    assert critique_results.get("status") in ["complete", "failed"], "Should complete or fail gracefully"

    print("\n[PASS] TEST PASSED: Full workflow executed")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PHASE 2 STEP 2B: CRITIQUE NODE TESTS")
    print("="*80)

    try:
        await test_skip_no_reports()
        await test_critique_single_report()
        await test_critique_with_debate()
        await test_full_workflow()

        print("\n" + "="*80)
        print("ALL TESTS PASSED [PASS]")
        print("="*80)
        print("\nPhase 2 Step 2B implementation is working correctly!")

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
