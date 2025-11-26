"""Test debate orchestrator directly"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from qnwis.orchestration.legendary_debate_orchestrator import LegendaryDebateOrchestrator
from qnwis.llm.client import LLMClient

async def test_debate():
    print("Creating LLM client...")
    llm_client = LLMClient(provider="anthropic")
    
    print("Creating orchestrator...")
    orchestrator = LegendaryDebateOrchestrator(
        emit_event_fn=lambda *args: None,
        llm_client=llm_client
    )
    
    print("Running debate...")
    try:
        result = await orchestrator.conduct_legendary_debate(
            question="Test question",
            contradictions=[],
            agents_map={},
            agent_reports_map={},
            llm_client=llm_client
        )
        print(f"Success! Result: {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_debate())
