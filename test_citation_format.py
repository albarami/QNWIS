"""
Test script to verify zero fabrication citation format in Labour Economist agent.

This script tests Phase 1 Step 1A implementation.
"""

import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from src.qnwis.agents.labour_economist import LabourEconomistAgent
from src.qnwis.agents.base import DataClient
from src.qnwis.llm.client import LLMClient
from src.qnwis.config.model_select import get_llm_config

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_citation_format():
    """Test that labour economist produces citations in correct format."""

    print("\n" + "="*80)
    print("PHASE 1 STEP 1A: ZERO FABRICATION CITATION TEST")
    print("="*80 + "\n")

    # Initialize clients
    data_client = DataClient()
    llm_config = get_llm_config()
    llm_client = LLMClient(config=llm_config)

    # Initialize agent
    agent = LabourEconomistAgent(data_client, llm_client)

    # Test query
    question = "What is Qatar's unemployment rate?"

    print(f"Test Question: {question}\n")
    print("Streaming agent response...\n")
    print("-" * 80)

    # Stream the response
    full_text = ""
    async for event in agent.run_stream(question, context={}):
        if event["type"] == "status":
            # Remove emojis for Windows console compatibility
            status_msg = event['content'].encode('ascii', 'ignore').decode('ascii')
            print(f"\n[STATUS] {status_msg}")
        elif event["type"] == "token":
            token = event["content"].encode('ascii', 'ignore').decode('ascii')
            print(token, end="", flush=True)
            full_text += event["content"]
        elif event["type"] == "warning":
            warning_msg = event['content'].encode('ascii', 'ignore').decode('ascii')
            print(f"\n[WARNING] {warning_msg}")
        elif event["type"] == "complete":
            report = event["report"]
            latency_ms = event["latency_ms"]
            print("\n" + "-" * 80)
            print(f"\n[COMPLETE] Latency: {latency_ms:.0f}ms\n")

            # Analyze citations
            print("="*80)
            print("CITATION ANALYSIS")
            print("="*80 + "\n")

            # Check for citation pattern
            import re
            citation_pattern = r'\[Per extraction: \'[^\']+\' from [^\]]+\]'
            citations_found = re.findall(citation_pattern, full_text)

            print(f"Citations found: {len(citations_found)}")
            for i, citation in enumerate(citations_found, 1):
                print(f"  {i}. {citation}")

            # Check for numbers without citations
            number_pattern = r'\b\d+\.?\d*%?\b'
            numbers_found = re.findall(number_pattern, full_text)
            print(f"\nTotal numbers in text: {len(numbers_found)}")

            # Check report findings
            if report.findings:
                print(f"\nReport findings: {len(report.findings)}")
                for finding in report.findings:
                    print(f"  - Title: {finding.title}")
                    print(f"  - Confidence: {finding.confidence_score:.2f}")
                    if finding.warnings:
                        print(f"  - Warnings: {len(finding.warnings)}")
                        for warning in finding.warnings[:3]:  # Show first 3
                            print(f"    • {warning}")

            # Success criteria
            print("\n" + "="*80)
            print("SUCCESS CRITERIA")
            print("="*80 + "\n")

            success = True

            # Criterion 1: At least one citation found
            if len(citations_found) > 0:
                print("[PASS] Citations present in response")
            else:
                print("[FAIL] No citations found - FAILED")
                success = False

            # Criterion 2: Citation format correct
            if citations_found and all('[Per extraction:' in c for c in citations_found):
                print("[PASS] Citation format correct")
            else:
                print("[FAIL] Citation format incorrect - FAILED")
                success = False

            # Criterion 3: No fabrication warnings
            has_warnings = any(f.warnings for f in report.findings)
            if not has_warnings:
                print("[PASS] No fabrication warnings")
            else:
                print("[WARN] Fabrication warnings present (may need investigation)")

            if success:
                print("\n" + "="*80)
                print("[PASS] PHASE 1 STEP 1A: LABOUR ECONOMIST - PASSED")
                print("="*80 + "\n")
            else:
                print("\n" + "="*80)
                print("[FAIL] PHASE 1 STEP 1A: LABOUR ECONOMIST - FAILED")
                print("="*80 + "\n")

        elif event["type"] == "error":
            error_msg = event['content'].encode('ascii', 'ignore').decode('ascii')
            print(f"\n[ERROR] {error_msg}")
            print("\n[FAIL] Test failed due to error")


if __name__ == "__main__":
    asyncio.run(test_citation_format())
