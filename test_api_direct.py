"""Direct API test to see actual error."""
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test():
    try:
        from qnwis.orchestration.streaming import workflow
        from qnwis.agents.base import DataClient
        from qnwis.data.deterministic.query_registry import QueryRegistry
        from qnwis.llm.anthropic_client import AnthropicClient
        
        # Initialize
        llm = AnthropicClient()
        registry = QueryRegistry()
        registry.load_all()
        client = DataClient(registry)
        
        # Run workflow
        print("\n🧪 Testing workflow with: 'What are the current unemployment trends in the GCC region?'\n")
        
        async for event in workflow(
            question="What are the current unemployment trends in the GCC region?",
            llm_client=llm,
            data_client=client,
            query_registry=registry,
            provider="anthropic",
            request_id="test-123"
        ):
            print(f"📡 {event.stage:20} | {event.status:10} | {event.payload if event.payload else ''}")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n🔍 FULL TRACEBACK:")
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test())
