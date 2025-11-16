"""Detailed test to see where workflow hangs"""
import asyncio
import sys
from datetime import datetime

async def test():
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting imports...")
        from src.qnwis.orchestration.graph_llm import LLMWorkflow
        from src.qnwis.agents.base import DataClient
        from src.qnwis.llm.client import LLMClient
        from src.qnwis.classification.classifier import Classifier
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Creating components...")
        data_client = DataClient()
        llm_client = LLMClient(provider='stub', model=None)
        classifier = Classifier()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Creating workflow...")
        workflow = LLMWorkflow(data_client, llm_client, classifier)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Creating callback...")
        
        events_received = []
        
        async def callback(stage, status, payload, latency):
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            print(f"[{timestamp}] EVENT: {stage} - {status}")
            events_received.append((stage, status))
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting run_stream...")
        print("=" * 60)
        
        # Add timeout to prevent infinite hang
        try:
            result = await asyncio.wait_for(
                workflow.run_stream("test query", callback),
                timeout=30.0  # 30 second timeout
            )
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] SUCCESS!")
            print(f"Events received: {len(events_received)}")
            for i, (stage, status) in enumerate(events_received, 1):
                print(f"  {i}. {stage} - {status}")
            return True
        except asyncio.TimeoutError:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] TIMEOUT after 30s!")
            print(f"Events received before timeout: {len(events_received)}")
            for i, (stage, status) in enumerate(events_received, 1):
                print(f"  {i}. {stage} - {status}")
            print("\nLast event suggests hang at this stage")
            return False
        
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
