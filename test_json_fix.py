"""Test the JSON parsing fix for Nationalization and Skills agents."""
import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qnwis.agents import NationalizationAgent, SkillsAgent
from qnwis.agents.base import DataClient
from qnwis.llm.client import LLMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_nationalization():
    """Test Nationalization agent with JSON fix."""
    logger.info("Testing Nationalization agent...")

    try:
        client = DataClient()
        llm = LLMClient()
        agent = NationalizationAgent(client, llm)

        question = "What are the unemployment rates in GCC countries?"
        context = {}

        logger.info(f"Running agent with question: {question}")
        report = await agent.run(question, context)

        logger.info(f"✓ Nationalization agent succeeded!")
        logger.info(f"  Findings: {len(report.findings)}")
        logger.info(f"  Narrative length: {len(report.narrative)} chars")

        return True
    except Exception as e:
        logger.error(f"✗ Nationalization agent failed: {e}")
        return False


async def test_skills():
    """Test Skills agent with JSON fix."""
    logger.info("Testing Skills agent...")

    try:
        client = DataClient()
        llm = LLMClient()
        agent = SkillsAgent(client, llm)

        question = "What is the gender distribution in employment?"
        context = {}

        logger.info(f"Running agent with question: {question}")
        report = await agent.run(question, context)

        logger.info(f"✓ Skills agent succeeded!")
        logger.info(f"  Findings: {len(report.findings)}")
        logger.info(f"  Narrative length: {len(report.narrative)} chars")

        return True
    except Exception as e:
        logger.error(f"✗ Skills agent failed: {e}")
        return False


async def main():
    """Run both tests."""
    logger.info("=" * 80)
    logger.info("Testing JSON Parsing Fix for LLM Agents")
    logger.info("=" * 80)

    results = []

    # Test Nationalization
    results.append(await test_nationalization())
    logger.info("")

    # Test Skills
    results.append(await test_skills())
    logger.info("")

    # Summary
    logger.info("=" * 80)
    logger.info("Test Results:")
    logger.info(f"  Nationalization: {'PASS' if results[0] else 'FAIL'}")
    logger.info(f"  Skills: {'PASS' if results[1] else 'FAIL'}")
    logger.info(f"  Overall: {'ALL TESTS PASSED' if all(results) else 'SOME TESTS FAILED'}")
    logger.info("=" * 80)

    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
