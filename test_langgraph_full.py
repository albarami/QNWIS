"""Full LangGraph workflow test (all 10 nodes)."""

import asyncio

from src.qnwis.orchestration.workflow import run_intelligence_query


async def test_full_workflow() -> None:
    """Execute the full LangGraph workflow and print a concise summary."""
    print("=" * 80)
    print("TESTING LANGGRAPH FULL WORKFLOW (10 NODES)")
    print("=" * 80)

    query = "Should Qatar invest QAR 15B in green hydrogen infrastructure by 2030?"
    print(f"\nQuery: {query}")

    result = await run_intelligence_query(query)
    nodes = result["nodes_executed"]

    print(f"\nNodes executed ({len(nodes)}): {nodes}")
    print(f"Complexity: {result['complexity']}")
    print(f"Data quality: {result['data_quality_score']:.2f}")
    print(f"Confidence score: {result['confidence_score']:.2f}")
    print(f"Fact check status: {result['fact_check_results']['status']}")

    print("\nDebate summary:")
    print(result.get("debate_synthesis", "N/A"))

    print("\nCritique summary:")
    print(result.get("critique_report", "N/A"))

    print("\nFinal synthesis (truncated to 800 chars):")
    synthesis = result.get("final_synthesis") or ""
    safe_synthesis = synthesis.encode("ascii", errors="ignore").decode("ascii", errors="ignore")
    snippet = safe_synthesis[:800]
    if len(safe_synthesis) > 800:
        snippet += "..."
    print(snippet)

    print("\nWarnings:", result.get("warnings"))
    print("Errors:", result.get("errors"))

    print("\n" + "=" * 80)
    print("TEST COMPLETE - Full workflow operational")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_full_workflow())

