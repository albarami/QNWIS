"""Direct test of the streaming workflow to see the error"""
import asyncio
import sys
import traceback

async def test_streaming():
    try:
        from src.qnwis.orchestration.streaming import run_workflow_stream
        from src.qnwis.agents.base import DataClient
        from src.qnwis.llm.client import LLMClient
        from src.qnwis.classification.classifier import Classifier
        
        print("✅ Imports successful")
        
        data_client = DataClient()
        print("✅ DataClient created")
        
        llm_client = LLMClient(provider='stub', model=None)
        print("✅ LLMClient created")
        
        classifier = Classifier()
        print("✅ Classifier created")
        
        print("\n🚀 Starting workflow stream...")
        
        async for event in run_workflow_stream(
            question="What is Qatar unemployment?",
            data_client=data_client,
            llm_client=llm_client,
            classifier=classifier,
        ):
            print(f"📦 Event: {event.get('stage', 'unknown')}")
            
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False
    
    print("\n✅ Streaming test complete!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_streaming())
    sys.exit(0 if success else 1)
