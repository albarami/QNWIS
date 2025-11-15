"""
End-to-end test of the complete workflow with real database and Claude Sonnet.
"""
import asyncio
import os
import sys

# Set environment variables BEFORE importing anything
os.environ['DATABASE_URL'] = 'postgresql://postgres:1234@localhost:5432/qnwis'
os.environ['QNWIS_LLM_PROVIDER'] = 'anthropic'
os.environ['QNWIS_ANTHROPIC_MODEL'] = 'claude-sonnet-4-20250514'

sys.path.insert(0, 'src')

from qnwis.agents.base import DataClient
from qnwis.llm.client import LLMClient
from qnwis.classification.classifier import Classifier
from qnwis.orchestration.streaming import run_workflow_stream


async def test_workflow():
    """Test the complete workflow end-to-end."""
    print("=" * 80)
    print("END-TO-END WORKFLOW TEST")
    print("=" * 80)

    # Initialize components
    print("\n1. Initializing components...")
    data_client = DataClient()
    print(f"   [OK] DataClient initialized ({len(data_client._registry.all_ids())} queries loaded)")

    llm_client = LLMClient(provider='anthropic')
    print(f"   [OK] LLMClient initialized (provider={llm_client.provider}, model={llm_client.model})")

    classifier = Classifier()
    print("   [OK] Classifier initialized")

    # Run workflow
    print("\n2. Running workflow...")
    question = "Compare Qatar's unemployment rate to other GCC countries"
    print(f"   Question: {question}")

    event_count = 0
    agent_reports = []
    synthesis_text = ""
    errors = []

    try:
        async for event in run_workflow_stream(
            question=question,
            data_client=data_client,
            llm_client=llm_client,
            classifier=classifier,
        ):
            event_count += 1

            # Show progress
            if event.status == "running":
                print(f"   [{event_count:3d}] >> {event.stage}")
            elif event.status == "complete":
                latency = f"{event.latency_ms:.0f}ms" if event.latency_ms else "N/A"
                print(f"   [{event_count:3d}] [OK] {event.stage} ({latency})")
            elif event.status == "error":
                error_msg = event.payload.get("error", "Unknown error")
                print(f"   [{event_count:3d}] [ERROR] {event.stage}: {error_msg}")
                errors.append(f"{event.stage}: {error_msg}")
            elif event.status == "streaming" and event.stage == "synthesize":
                token = event.payload.get("token", "")
                synthesis_text += token

            # Collect agent reports
            if event.stage == "done" and event.status == "complete":
                agent_reports = event.payload.get("agent_reports", [])
                if not synthesis_text:
                    synthesis_text = event.payload.get("synthesis", "")
                print(f"\n   Workflow completed!")
                break

            # Stop after 200 events to avoid infinite loops
            if event_count > 200:
                print(f"\n   WARNING: Stopped after {event_count} events")
                break

    except Exception as e:
        print(f"\n   [ERROR] Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        errors.append(f"Workflow exception: {e}")

    # Print results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(f"\n3. Events processed: {event_count}")
    print(f"4. Agent reports: {len(agent_reports)}")

    if agent_reports:
        for i, report in enumerate(agent_reports, 1):
            agent_name = report.get('agent', 'Unknown')
            findings = report.get('findings', [])
            print(f"   [{i}] {agent_name}: {len(findings)} findings")

    print(f"\n5. Synthesis length: {len(synthesis_text)} characters")
    if synthesis_text:
        # Show first 500 chars
        preview = synthesis_text[:500]
        if len(synthesis_text) > 500:
            preview += "..."
        print(f"\n   Preview:")
        for line in preview.split('\n')[:10]:
            print(f"   {line}")

    if errors:
        print(f"\n6. Errors encountered: {len(errors)}")
        for error in errors:
            print(f"   [ERROR] {error}")
    else:
        print(f"\n6. No errors [OK]")

    # Success criteria
    print("\n" + "=" * 80)
    print("SUCCESS CRITERIA")
    print("=" * 80)

    success = True

    if len(agent_reports) == 0:
        print("[FAIL] No agent reports generated")
        success = False
    else:
        print(f"[PASS] {len(agent_reports)} agent reports generated")

    if len(synthesis_text) < 50:
        print("[FAIL] Synthesis too short or missing")
        success = False
    else:
        print(f"[PASS] Synthesis generated ({len(synthesis_text)} chars)")

    if "test finding" in synthesis_text.lower() or "test_metric" in synthesis_text.lower():
        print("[FAIL] Synthesis contains stub test data")
        success = False
    else:
        print("[PASS] Synthesis contains real analysis (not stub data)")

    if len(errors) > 0:
        print(f"[FAIL] {len(errors)} errors occurred")
        success = False
    else:
        print("[PASS] No errors")

    print("\n" + "=" * 80)
    if success:
        print(">>> ALL TESTS PASSED <<<")
    else:
        print(">>> SOME TESTS FAILED <<<")
    print("=" * 80)

    return success


if __name__ == "__main__":
    success = asyncio.run(test_workflow())
    sys.exit(0 if success else 1)
