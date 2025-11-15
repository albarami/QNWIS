"""Test real workflow with citation injection verification."""
import asyncio
import sys
import re

async def test_real_workflow():
    try:
        from src.qnwis.agents.base import DataClient
        from src.qnwis.llm.client import LLMClient
        from src.qnwis.classification.classifier import Classifier
        from src.qnwis.orchestration.streaming import run_workflow_stream

        print("="*80)
        print("REAL WORKFLOW TEST - Citation Injection Verification")
        print("="*80)

        print("\nInitializing components...")
        data_client = DataClient()
        llm_client = LLMClient(provider="anthropic")  # Use REAL LLM
        classifier = Classifier()

        print("Starting workflow stream...")
        question = "Compare Qatar unemployment to GCC"
        print(f"Question: {question}\n")

        # Collect all events
        events = []
        agent_reports = []
        final_synthesis = None

        async for event in run_workflow_stream(
            question=question,
            data_client=data_client,
            llm_client=llm_client,
            classifier=classifier
        ):
            events.append(event)

            # Show progress
            if event.status == "complete":
                print(f"[COMPLETE] {event.stage}")
            elif event.status == "error":
                print(f"[ERROR] {event.stage}: {event.payload}")

            # Capture agent reports
            if event.stage.startswith("agent:") and event.status == "complete":
                if hasattr(event, 'payload') and isinstance(event.payload, dict):
                    if 'report' in event.payload:
                        agent_reports.append(event.payload['report'])

            # Capture final synthesis
            if event.stage == "synthesize" and event.status == "complete":
                if hasattr(event, 'payload'):
                    final_synthesis = event.payload

        print(f"\n{'='*80}")
        print(f"WORKFLOW COMPLETED - {len(events)} events")
        print('='*80)

        # Check for citations in agent reports
        print(f"\n{'='*80}")
        print("CHECKING AGENT REPORTS FOR CITATIONS")
        print('='*80)

        citations_found = False

        if not agent_reports:
            print("\nWARNING: No agent reports captured from events")
            print("Checking event payloads directly...")

            # Look through all events for reports
            for event in events:
                if hasattr(event, 'payload') and isinstance(event.payload, dict):
                    # Check if payload has text fields
                    for key, value in event.payload.items():
                        if isinstance(value, str) and "[Per extraction:" in value:
                            citations_found = True
                            print(f"\n[FOUND] Citations in event.payload['{key}']")
                            print(f"Preview: {value[:200]}...")
                            break

        for i, report in enumerate(agent_reports):
            agent_name = getattr(report, 'agent_name', f'Agent {i}')
            print(f"\n--- {agent_name} ---")

            # Check narrative
            if hasattr(report, 'narrative') and report.narrative:
                narrative = report.narrative
                has_citations = "[Per extraction:" in narrative

                if has_citations:
                    citations_found = True
                    citations = re.findall(r'\[Per extraction:.*?\]', narrative)
                    print(f"[SUCCESS] Found {len(citations)} citations in narrative!")
                    print(f"\nNarrative preview (first 500 chars):")
                    print("-"*80)
                    print(narrative[:500])
                    if len(narrative) > 500:
                        print("...")
                    print("-"*80)
                else:
                    print("[FAIL] NO citations in narrative")
                    print(f"Narrative preview: {narrative[:300]}...")
            else:
                print("[WARN] No narrative field")

        # Check synthesis
        if final_synthesis:
            print(f"\n{'='*80}")
            print("CHECKING FINAL SYNTHESIS")
            print('='*80)

            if isinstance(final_synthesis, dict):
                for key, value in final_synthesis.items():
                    if isinstance(value, str) and "[Per extraction:" in value:
                        citations_found = True
                        print(f"\n[FOUND] Citations in synthesis['{key}']")
                        print(f"Preview: {value[:300]}...")
            elif isinstance(final_synthesis, str):
                if "[Per extraction:" in final_synthesis:
                    citations_found = True
                    print(f"\n[FOUND] Citations in synthesis")
                    print(f"Preview: {final_synthesis[:300]}...")

        # Final verdict
        print(f"\n{'='*80}")
        if citations_found:
            print("RESULT: SUCCESS - Citations are being injected!")
        else:
            print("RESULT: FAIL - No citations found in output")
        print('='*80)

        return citations_found

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    success = asyncio.run(test_real_workflow())
    sys.exit(0 if success else 1)
