"""
Test script for Phase 3: Conditional Routing to Deterministic Agents

Tests:
1. Temporal query → TimeMachine agent
2. Forecast query → Predictor agent
3. Scenario query → Scenario agent
4. General query → LLM agents
"""

import asyncio
import logging
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


async def test_temporal_routing():
    """Test 1: Temporal query should route to TimeMachine"""
    print("\n" + "="*80)
    print("TEST 1: Temporal Query -> TimeMachine")
    print("="*80)

    # Initialize workflow
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)
    workflow = LLMWorkflow(data_client, llm_client)

    # Test question with temporal pattern
    question = "What was Qatar's unemployment rate trend in 2023?"

    print(f"\nQuestion: {question}")
    print("Expected routing: TimeMachine")

    # Run workflow
    result = await workflow.run(question)

    # Check routing
    classification = result.get("classification", {})
    route_to = classification.get("route_to")
    deterministic_result = result.get("deterministic_result")

    print(f"\nActual routing: {route_to}")
    print(f"Deterministic result present: {bool(deterministic_result)}")

    if route_to == "time_machine":
        print("[PASS] TEST PASSED: Correctly routed to TimeMachine")
    else:
        print(f"[FAIL] TEST FAILED: Expected 'time_machine', got '{route_to}'")

    return route_to == "time_machine"


async def test_forecast_routing():
    """Test 2: Forecast query should route to Predictor"""
    print("\n" + "="*80)
    print("TEST 2: Forecast Query -> Predictor")
    print("="*80)

    # Initialize workflow
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)
    workflow = LLMWorkflow(data_client, llm_client)

    # Test question with forecast pattern
    question = "What will unemployment be next year?"

    print(f"\nQuestion: {question}")
    print("Expected routing: Predictor")

    # Run workflow
    result = await workflow.run(question)

    # Check routing
    classification = result.get("classification", {})
    route_to = classification.get("route_to")
    deterministic_result = result.get("deterministic_result")

    print(f"\nActual routing: {route_to}")
    print(f"Deterministic result present: {bool(deterministic_result)}")

    if route_to == "predictor":
        print("[PASS] TEST PASSED: Correctly routed to Predictor")
    else:
        print(f"[FAIL] TEST FAILED: Expected 'predictor', got '{route_to}'")

    return route_to == "predictor"


async def test_scenario_routing():
    """Test 3: Scenario query should route to Scenario agent"""
    print("\n" + "="*80)
    print("TEST 3: Scenario Query -> Scenario")
    print("="*80)

    # Initialize workflow
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)
    workflow = LLMWorkflow(data_client, llm_client)

    # Test question with scenario pattern
    question = "What if Qatarization increases by 10%?"

    print(f"\nQuestion: {question}")
    print("Expected routing: Scenario")

    # Run workflow
    result = await workflow.run(question)

    # Check routing
    classification = result.get("classification", {})
    route_to = classification.get("route_to")
    deterministic_result = result.get("deterministic_result")

    print(f"\nActual routing: {route_to}")
    print(f"Deterministic result present: {bool(deterministic_result)}")

    if route_to == "scenario":
        print("[PASS] TEST PASSED: Correctly routed to Scenario")
    else:
        print(f"[FAIL] TEST FAILED: Expected 'scenario', got '{route_to}'")

    return route_to == "scenario"


async def test_llm_routing():
    """Test 4: General query should route to LLM agents"""
    print("\n" + "="*80)
    print("TEST 4: General Query -> LLM Agents")
    print("="*80)

    # Initialize workflow
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)
    workflow = LLMWorkflow(data_client, llm_client)

    # Test question without deterministic patterns
    question = "Analyze Qatar's labour market dynamics"

    print(f"\nQuestion: {question}")
    print("Expected routing: LLM agents (route_to=None)")

    # Run workflow
    result = await workflow.run(question)

    # Check routing
    classification = result.get("classification", {})
    route_to = classification.get("route_to")
    agent_reports = result.get("agent_reports", [])
    deterministic_result = result.get("deterministic_result")

    print(f"\nActual routing: {route_to}")
    print(f"Agent reports count: {len(agent_reports)}")
    print(f"Deterministic result present: {bool(deterministic_result)}")

    if route_to is None and len(agent_reports) > 0:
        print("[PASS] TEST PASSED: Correctly routed to LLM agents")
    else:
        print(f"[FAIL] TEST FAILED: Expected route_to=None with agents, got '{route_to}'")

    return route_to is None


async def main():
    """Run all routing tests"""
    print("\n" + "="*80)
    print("PHASE 3: CONDITIONAL ROUTING TESTS")
    print("="*80)

    results = []

    try:
        results.append(await test_temporal_routing())
        results.append(await test_forecast_routing())
        results.append(await test_scenario_routing())
        results.append(await test_llm_routing())

        print("\n" + "="*80)
        passed = sum(results)
        total = len(results)

        if passed == total:
            print(f"ALL TESTS PASSED ({passed}/{total}) [PASS]")
        else:
            print(f"SOME TESTS FAILED ({passed}/{total} passed) [FAIL]")
        print("="*80)

        if passed == total:
            print("\nPhase 3 conditional routing is working correctly!")
        else:
            print("\nPhase 3 conditional routing has issues that need attention.")

    except Exception as e:
        print(f"\n[FAIL] TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
