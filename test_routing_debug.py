"""Debug conditional routing."""

import asyncio
import sys
sys.path.insert(0, "src")

from qnwis.orchestration.workflow import route_by_complexity
from qnwis.orchestration.state import IntelligenceState


def test_router():
    """Test the routing function directly."""
    print("=" * 80)
    print("ROUTING FUNCTION DEBUG")
    print("=" * 80)
    
    test_states = [
        {"complexity": "simple"},
        {"complexity": "medium"},
        {"complexity": "complex"},
        {"complexity": "critical"},
        {"complexity": "unknown"},
    ]
    
    for state in test_states:
        route = route_by_complexity(state)  # type: ignore
        print(f"\nComplexity: {state['complexity']:10s} -> Route: {route}")
    
    print("\n" + "=" * 80)


async def test_full_workflow_routing():
    """Test routing in actual workflow execution."""
    print("\n" + "=" * 80)
    print("FULL WORKFLOW ROUTING TEST")
    print("=" * 80)
    
    from qnwis.orchestration.workflow import run_intelligence_query
    
    # Test with explicitly simple query
    query = "What is Qatar?"  # Very simple
    print(f"\nQuery: \"{query}\"")
    
    result = await run_intelligence_query(query)
    
    print(f"Classified as: {result['complexity']}")
    print(f"Nodes executed: {result['nodes_executed']}")
    print(f"Expected: ['classifier', 'extraction', 'synthesis']")
    print(f"Agent nodes present: {any(n in result['nodes_executed'] for n in ['financial', 'market', 'operations', 'research'])}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_router()
    asyncio.run(test_full_workflow_routing())

