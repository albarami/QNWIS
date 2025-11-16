"""Test the streaming function directly"""
import asyncio

async def test():
    try:
        from src.qnwis.orchestration.streaming import run_workflow_stream
        from src.qnwis.agents.base import DataClient
        from src.qnwis.llm.client import LLMClient
        from src.qnwis.classification.classifier import Classifier
        
        print("Creating components...")
        data_client = DataClient()
        llm_client = LLMClient(provider='stub', model=None)
        classifier = Classifier()
        
        print("Calling run_workflow_stream...")
        event_count = 0
        
        async for event in run_workflow_stream(
            question="test",
            data_client=data_client,
            llm_client=llm_client,
            classifier=classifier
        ):
            event_count += 1
            print(f"Event {event_count}: {event.stage} - {event.status}")
            
            if event.stage == "done":
                break
        
        print(f"\n✅ Success! Received {event_count} events")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
