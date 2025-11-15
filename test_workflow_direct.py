"""Test workflow directly without API."""
import asyncio
import sys
import os
from pathlib import Path

# Set environment variables
os.environ["DATABASE_URL"] = "postgresql://postgres:1234@localhost:5432/qnwis"
os.environ["QNWIS_JWT_SECRET"] = "dev-secret-key-for-testing"
os.environ["ENVIRONMENT"] = "development"

sys.path.insert(0, str(Path(__file__).parent / "src"))

async def main():
    from qnwis.orchestration.streaming import run_workflow_stream
    from qnwis.agents.base import DataClient
    from qnwis.data.deterministic.registry import QueryRegistry
    from qnwis.llm.client import LLMClient
    
    print("Initializing components...")
    
    # Initialize
    registry = QueryRegistry()
    registry.load_all()
    print(f"Loaded {len(registry._items)} queries")
    
    data_client = DataClient()
    llm_client = LLMClient(provider="anthropic")
    
    question = "What are the current unemployment trends in the GCC region?"
    print(f"\nTesting: {question}\n")
    
    event_count = 0
    try:
        async for event in run_workflow_stream(
            question=question,
            data_client=data_client,
            llm_client=llm_client,
            query_registry=registry,
            provider="anthropic",
            request_id="test-direct"
        ):
            event_count += 1
            print(f"Event {event_count}: {event.stage} | {event.status}")
            
            if event.stage == "error":
                print(f"\nERROR EVENT:")
                print(f"  Payload: {event.payload}")
                
        print(f"\nWorkflow completed: {event_count} events")
        
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        print(f"Type: {type(e).__name__}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
