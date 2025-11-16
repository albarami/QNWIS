"""Direct test to find the exact error"""
import asyncio
import sys

async def test():
    try:
        from src.qnwis.orchestration.graph_llm import LLMWorkflow
        from src.qnwis.agents.base import DataClient
        from src.qnwis.llm.client import LLMClient
        from src.qnwis.classification.classifier import Classifier
        
        print("Creating components...")
        data_client = DataClient()
        llm_client = LLMClient(provider='stub', model=None)
        classifier = Classifier()
        
        print("Creating workflow...")
        workflow = LLMWorkflow(data_client, llm_client, classifier)
        
        print("Testing run_stream method...")
        
        async def callback(stage, status, payload, latency):
            print(f"Event: {stage} - {status}")
        
        result = await workflow.run_stream("test query", callback)
        print(f"✅ SUCCESS! Result type: {type(result)}")
        print(f"Result keys: {list(result.keys())[:5] if isinstance(result, dict) else 'not a dict'}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
