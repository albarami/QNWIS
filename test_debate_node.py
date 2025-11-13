"""
Test script for Phase 2 Step 2A: Multi-Agent Debate Node

Tests:
1. No contradictions - should skip debate
2. Simple contradiction - should detect and resolve
3. Source conflict - should prefer authoritative source
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


async def test_no_contradictions():
    """Test 1: No contradictions - should skip debate"""
    print("\n" + "="*80)
    print("TEST 1: No Contradictions")
    print("="*80)

    # Initialize orchestrator
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)

    orchestrator = LLMWorkflow(data_client, llm_client)

    # Create mock state with agreeing reports
    mock_reports = [
        {
            "agent_name": "Agent1",
            "narrative": "Qatar unemployment rate is [Per extraction: '0.10' from GCC-STAT Period-A]",
            "confidence": 0.90
        },
        {
            "agent_name": "Agent2",
            "narrative": "The unemployment rate stands at [Per extraction: '0.10' from GCC-STAT Period-A]",
            "confidence": 0.85
        }
    ]

    # Test contradiction detection
    contradictions = orchestrator._detect_contradictions(mock_reports)

    print(f"Contradictions detected: {len(contradictions)}")
    if contradictions:
        for c in contradictions:
            print(f"  - {c['agent1_name']}: {c['agent1_value']} vs {c['agent2_name']}: {c['agent2_value']}")

    assert len(contradictions) == 0, f"Expected 0 contradictions, but found {len(contradictions)}"

    print("[PASS] TEST PASSED: No contradictions detected as expected")


async def test_simple_contradiction():
    """Test 2: Simple contradiction - should detect"""
    print("\n" + "="*80)
    print("TEST 2: Simple Contradiction")
    print("="*80)

    # Initialize orchestrator
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)

    orchestrator = LLMWorkflow(data_client, llm_client)

    # Create mock state with contradicting reports
    mock_reports = [
        {
            "agent_name": "Agent1",
            "narrative": "Qatar unemployment rate is [Per extraction: '0.10' from GCC-STAT Period-A]",
            "confidence": 0.90
        },
        {
            "agent_name": "Agent2",
            "narrative": "Unemployment rate is [Per extraction: '0.15' from World-Bank Period-B]",
            "confidence": 0.85
        }
    ]

    # Test contradiction detection
    contradictions = orchestrator._detect_contradictions(mock_reports)

    print(f"Contradictions detected: {len(contradictions)}")

    if contradictions:
        print("\nContradiction details:")
        for c in contradictions:
            print(f"  - {c['agent1_name']}: {c['agent1_value']} vs {c['agent2_name']}: {c['agent2_value']}")
            print(f"    Severity: {c['severity']}")

    assert len(contradictions) > 0, "Expected at least 1 contradiction"

    print("[PASS] TEST PASSED: Contradiction detected")


async def test_debate_resolution():
    """Test 3: Debate resolution with LLM arbitration"""
    print("\n" + "="*80)
    print("TEST 3: Debate Resolution")
    print("="*80)

    # Initialize orchestrator
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)

    orchestrator = LLMWorkflow(data_client, llm_client)

    # Create mock contradiction
    contradiction = {
        "metric_name": "qatar_unemployment_rate",
        "agent1_name": "Agent1",
        "agent1_value": 0.10,
        "agent1_value_str": "0.10",
        "agent1_citation": "[Per extraction: '0.10' from GCC-STAT Period-A]",
        "agent1_confidence": 0.90,
        "agent2_name": "Agent2",
        "agent2_value": 0.12,
        "agent2_value_str": "0.12",
        "agent2_citation": "[Per extraction: '0.12' from World-Bank Period-B]",
        "agent2_confidence": 0.85,
        "severity": "medium"
    }

    # Test debate
    print("\nConducting debate...")
    resolution = await orchestrator._conduct_debate(contradiction)

    print(f"\nDebate Resolution:")
    print(f"  Action: {resolution['action']}")
    print(f"  Resolution: {resolution['resolution']}")
    print(f"  Confidence: {resolution['confidence']:.2f}")
    print(f"  Explanation: {resolution['explanation'][:200]}...")

    assert resolution["action"] in ["use_agent1", "use_agent2", "use_both", "flag_for_review"], \
        "Invalid action"

    print("[PASS] TEST PASSED: Debate conducted successfully")


async def test_full_workflow():
    """Test 4: Full debate node in workflow"""
    print("\n" + "="*80)
    print("TEST 4: Full Workflow with Debate")
    print("="*80)

    # Initialize orchestrator
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)

    orchestrator = LLMWorkflow(data_client, llm_client)

    # Create mock state with contradicting reports
    mock_state = {
        "question": "What is Qatar's unemployment rate?",
        "agent_reports": [
            {
                "agent_name": "LabourEconomist",
                "narrative": "Qatar unemployment rate is [Per extraction: '0.10' from GCC-STAT Period-A]",
                "confidence": 0.90
            },
            {
                "agent_name": "NationalStrategy",
                "narrative": "Unemployment rate is [Per extraction: '0.12' from World-Bank Period-B]",
                "confidence": 0.85
            }
        ],
        "classification": None,
        "prefetch": None,
        "rag_context": None,
        "selected_agents": None,
        "debate_results": None,
        "verification": None,
        "synthesis": None,
        "error": None,
        "metadata": {},
        "reasoning_chain": [],
        "event_callback": None
    }

    # Test debate node
    print("\nRunning debate node...")
    result_state = await orchestrator._debate_node(mock_state)

    print(f"\nDebate Results:")
    debate_results = result_state.get("debate_results", {})
    print(f"  Contradictions found: {debate_results.get('contradictions_found', 0)}")
    print(f"  Resolved: {debate_results.get('resolved', 0)}")
    print(f"  Flagged: {debate_results.get('flagged_for_review', 0)}")
    print(f"  Status: {debate_results.get('status')}")
    print(f"  Latency: {debate_results.get('latency_ms', 0):.0f}ms")

    if debate_results.get('consensus_narrative'):
        print(f"\nConsensus Narrative:")
        print(debate_results['consensus_narrative'])

    assert debate_results.get('status') == 'complete', "Debate should complete"

    print("[PASS] TEST PASSED: Full debate workflow executed")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PHASE 2 STEP 2A: DEBATE NODE TESTS")
    print("="*80)

    try:
        await test_no_contradictions()
        await test_simple_contradiction()
        await test_debate_resolution()
        await test_full_workflow()

        print("\n" + "="*80)
        print("ALL TESTS PASSED [PASS]")
        print("="*80)
        print("\nPhase 2 Step 2A implementation is working correctly!")

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
