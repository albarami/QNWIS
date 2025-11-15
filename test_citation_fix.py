"""
Test script to verify citation injection fix.

This will run a query through the workflow and check if citations
are being injected into the narrative field.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qnwis.orchestration.graph_llm import LLMWorkflow
from qnwis.agents.base import DataClient
from qnwis.llm.client import LLMClient
from qnwis.config.model_select import get_llm_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_citation_injection():
    """Test the citation injection fix."""

    logger.info("\n" + "="*80)
    logger.info("TESTING CITATION INJECTION FIX (Commit 7a9a191)")
    logger.info("="*80)

    # Initialize workflow
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)
    workflow = LLMWorkflow(data_client, llm_client)

    # Test query
    question = "Compare Qatar's unemployment to other GCC countries"
    logger.info(f"\nQuery: {question}")

    # Run workflow
    logger.info("\nRunning workflow...")
    result = await workflow.run(question)

    # Check results
    logger.info("\n" + "="*80)
    logger.info("CHECKING RESULTS")
    logger.info("="*80)

    # Check if we have agent reports
    agent_reports = result.get("agent_reports", [])
    logger.info(f"\nAgent reports found: {len(agent_reports)}")

    if not agent_reports:
        logger.error("❌ NO AGENT REPORTS - Test failed")
        return False

    # Check each report for citations in narrative
    citation_found = False
    for i, report in enumerate(agent_reports):
        agent_name = report.agent_name if hasattr(report, 'agent_name') else f"Agent {i}"
        logger.info(f"\n--- {agent_name} ---")

        # Check narrative field
        if hasattr(report, 'narrative') and report.narrative:
            narrative = report.narrative
            logger.info(f"Narrative length: {len(narrative)} chars")

            # Check for citations
            if "[Per extraction:" in narrative:
                logger.info("✅ CITATIONS FOUND IN NARRATIVE!")
                citation_found = True

                # Show first citation
                import re
                citations = re.findall(r'\[Per extraction:.*?\]', narrative)
                logger.info(f"Total citations: {len(citations)}")
                if citations:
                    logger.info(f"First citation: {citations[0]}")
            else:
                logger.warning("❌ NO CITATIONS IN NARRATIVE")
                logger.info(f"Narrative preview: {narrative[:200]}...")
        else:
            logger.warning("❌ No narrative field found")

        # Also check findings for completeness
        if hasattr(report, 'findings') and report.findings:
            logger.info(f"Findings count: {len(report.findings)}")
            for j, finding in enumerate(report.findings):
                if isinstance(finding, dict) and 'analysis' in finding:
                    if "[Per extraction:" in finding['analysis']:
                        logger.info(f"  ✅ Finding {j} has citations in analysis")

    # Final verdict
    logger.info("\n" + "="*80)
    if citation_found:
        logger.info("✅✅✅ TEST PASSED: Citations found in narrative field! ✅✅✅")
        logger.info("="*80)
        return True
    else:
        logger.error("❌❌❌ TEST FAILED: No citations in narrative field ❌❌❌")
        logger.info("="*80)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_citation_injection())
    sys.exit(0 if success else 1)
