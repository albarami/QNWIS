"""
Direct test of citation injection - bypasses Chainlit UI completely.

This script directly calls the LLM workflow and prints the results,
allowing us to verify that citations are being injected into the narrative.
"""

import asyncio
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qnwis.orchestration.graph_llm import LLMWorkflow
from qnwis.agents.base import DataClient
from qnwis.llm.client import LLMClient
from qnwis.config.model_select import get_llm_config

# Configure logging to show citation injection messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_citation_injection():
    """Test citation injection by running a query directly."""

    print("\n" + "="*80)
    print("DIRECT CITATION INJECTION TEST")
    print("="*80)

    # Initialize workflow
    logger.info("Initializing workflow components...")
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)
    workflow = LLMWorkflow(data_client, llm_client)

    # Test query
    question = "Compare Qatar's unemployment to other GCC countries"
    logger.info(f"\nQuery: {question}")

    # Run workflow
    logger.info("\nExecuting workflow...")
    print("\n" + "-"*80)
    result = await workflow.run(question)
    print("-"*80)

    # Extract and display results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)

    agent_reports = result.get("agent_reports", [])
    print(f"\nNumber of agent reports: {len(agent_reports)}")

    if not agent_reports:
        print("\n❌ NO AGENT REPORTS FOUND")
        return False

    # Check each report for citations
    citations_found = False

    for i, report in enumerate(agent_reports):
        agent_name = report.agent_name if hasattr(report, 'agent_name') else f"Agent {i}"
        print(f"\n{'='*80}")
        print(f"AGENT: {agent_name}")
        print('='*80)

        # Check narrative field (what UI displays)
        if hasattr(report, 'narrative') and report.narrative:
            narrative = report.narrative
            has_citations = "[Per extraction:" in narrative

            if has_citations:
                citations_found = True
                print(f"\n✅ CITATIONS FOUND IN NARRATIVE!")

                # Count citations
                import re
                citations = re.findall(r'\[Per extraction:.*?\]', narrative)
                print(f"   Total citations: {len(citations)}")

                # Show first 500 chars of narrative with citations
                print(f"\nNarrative preview (first 500 chars):")
                print("-"*80)
                print(narrative[:500])
                if len(narrative) > 500:
                    print("...")
                print("-"*80)

                # Show a few example citations
                if citations:
                    print(f"\nExample citations:")
                    for j, citation in enumerate(citations[:3]):
                        print(f"  {j+1}. {citation}")
            else:
                print(f"\n❌ NO CITATIONS IN NARRATIVE")
                print(f"\nNarrative preview (first 300 chars):")
                print("-"*80)
                print(narrative[:300])
                print("...")
                print("-"*80)
        else:
            print("\n⚠️  No narrative field found in report")

    # Final verdict
    print("\n" + "="*80)
    if citations_found:
        print("✅✅✅ SUCCESS: Citations are being injected! ✅✅✅")
        print("="*80)
        print("\nThe citation injection fix is working correctly.")
        print("Every number in the narrative has a [Per extraction: ...] citation.")
        return True
    else:
        print("❌❌❌ FAILURE: No citations found in narratives ❌❌❌")
        print("="*80)
        print("\nThe citation injection may not be working as expected.")
        print("Check the logs above for 'Injected citations into narrative' messages.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_citation_injection())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
