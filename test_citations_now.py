"""Quick test to verify citations are working in agent narratives.

Path A: Uses existing LLMWorkflow orchestration and CitationInjector.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging to see citation messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from qnwis.orchestration.graph_llm import LLMWorkflow
from qnwis.agents.base import DataClient
from qnwis.llm.client import LLMClient
from qnwis.config.model_select import get_llm_config
from qnwis.data.deterministic.models import QueryResult, Row, Provenance, Freshness


class StubDataClient(DataClient):
    """Stub deterministic client that returns synthetic results for testing.

    This avoids hitting the real database while still exercising citation logic.
    """

    def run(self, query_id: str) -> QueryResult:  # type: ignore[override]
        # Simple synthetic unemployment-style result
        rows = [Row(data={"unemployment_rate": 0.10, "country": "Qatar"})]
        provenance = Provenance(
            source="sql",
            dataset_id="synthetic_unemployment",
            locator=f"stub://{query_id}",
            fields=["unemployment_rate", "country"],
        )
        freshness = Freshness(asof_date="2024-03-31", updated_at=None)
        return QueryResult(
            query_id=query_id,
            rows=rows,
            unit="percent",
            provenance=provenance,
            freshness=freshness,
        )


async def test_now() -> bool:
    """Run a single query and check for citations in narratives."""
    print("\n" + "=" * 80)
    print("CITATION TEST - PATH A")
    print("=" * 80)

    # Initialize
    print("\n1. Initializing (stub data client)...")
    data_client = StubDataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)

    # Build workflow
    print("2. Building workflow...")
    workflow = LLMWorkflow(data_client, llm_client)

    # Run query
    question = "Compare Qatar's unemployment to other GCC countries"
    print(f"3. Running query: {question}\n")

    result = await workflow.run(question)

    # Check results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    reports = result.get("agent_reports", [])
    print(f"\nAgent reports: {len(reports)}")

    citations_found = False

    for i, report in enumerate(reports):
        agent = getattr(report, "agent", f"Agent{i}")
        print(f"\n--- {agent} ---")

        if hasattr(report, "narrative") and report.narrative:
            narrative = report.narrative
            has_cites = "[Per extraction:" in narrative

            if has_cites:
                citations_found = True
                print("✅ CITATIONS FOUND!")
                print("First 300 chars:\n" + narrative[:300] + "...")
            else:
                print("❌ NO CITATIONS")
                print("First 300 chars:\n" + narrative[:300] + "...")
        else:
            print("⚠ No narrative field on report")

    print("\n" + "=" * 80)
    if citations_found:
        print("SUCCESS - CITATIONS WORKING")
    else:
        print("FAILED - NO CITATIONS FOUND")
    print("=" * 80)

    return citations_found


if __name__ == "__main__":
    try:
        ok = asyncio.run(test_now())
        sys.exit(0 if ok else 1)
    except Exception as exc:  # pragma: no cover
        print(f"\nError during test: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
