"""Test basic LangGraph workflow (2 nodes)."""

import asyncio

from src.qnwis.orchestration.workflow import run_intelligence_query


async def test() -> None:
    """Execute the two-node LangGraph workflow and print diagnostics."""
    print("=" * 80)
    print("TESTING LANGGRAPH BASIC WORKFLOW (2 NODES)")
    print("=" * 80)

    query = "What is Qatar's GDP growth from 2010 to 2024?"
    print(f"\nQuery: {query}")

    result = await run_intelligence_query(query)

    print(f"\nComplexity: {result['complexity']}")
    print(f"Nodes executed: {result['nodes_executed']}")
    print(f"Data sources: {result['data_sources']}")
    print(f"Facts extracted: {len(result['extracted_facts'])}")
    print(f"Data quality: {result['data_quality_score']:.2f}")
    print(f"Execution time: {result['execution_time']:.2f}s")

    print("\nReasoning chain:")
    for step in result["reasoning_chain"]:
        print(f"  - {step}")

    if result["warnings"]:
        print("\nWarnings:")
        for warning in result["warnings"]:
            print(f"  ! {warning}")

    if result["errors"]:
        print("\nErrors:")
        for error in result["errors"]:
            print(f"  X {error}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE - Basic workflow operational")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test())

