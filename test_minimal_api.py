"""Minimal test of the API streaming endpoint."""
import asyncio
import sys

async def test_streaming():
    try:
        from src.qnwis.agents.base import DataClient
        from src.qnwis.llm.client import LLMClient
        from src.qnwis.classification.classifier import Classifier
        from src.qnwis.orchestration.streaming import run_workflow_stream
        
        print("Initializing components...")
        data_client = DataClient()
        llm_client = LLMClient(provider="stub")
        classifier = Classifier()
        
        print("Starting workflow stream...")
        question = "Compare Qatar unemployment to GCC"
        
        event_count = 0
        async for event in run_workflow_stream(
            question=question,
            data_client=data_client,
            llm_client=llm_client,
            classifier=classifier
        ):
            event_count += 1
            print(f"Event {event_count}: stage={event.stage}, status={event.status}")
            if event.status == "error":
                print(f"  ERROR: {event.payload}")
        
        print(f"\n✅ Workflow completed successfully ({event_count} events)")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_streaming())
