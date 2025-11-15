"""Test API directly to see error."""
import asyncio
import traceback

async def test():
    try:
        from src.qnwis.agents.base import DataClient
        from src.qnwis.llm.client import LLMClient
        from src.qnwis.classification.classifier import Classifier
        from src.qnwis.orchestration.streaming import run_workflow_stream
        
        print("Initializing...")
        data_client = DataClient()
        llm_client = LLMClient(provider="stub")
        classifier = Classifier()
        
        print("Running workflow...")
        async for event in run_workflow_stream(
            question="Compare Qatar unemployment to GCC",
            data_client=data_client,
            llm_client=llm_client,
            classifier=classifier
        ):
            print(f"Event: {event.stage} - {event.status}")
            if event.status == "error":
                print(f"ERROR: {event.payload}")
                
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()

asyncio.run(test())
