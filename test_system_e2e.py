"""
End-to-end system test for Step 39 LLM agents.

Tests the complete workflow with stub LLM provider.
"""

import asyncio
import os

# Set stub provider for testing
os.environ["QNWIS_LLM_PROVIDER"] = "stub"
os.environ["QNWIS_STUB_TOKEN_DELAY_MS"] = "0"  # Fast for testing

from src.qnwis.agents.base import DataClient
from src.qnwis.llm.client import LLMClient
from src.qnwis.orchestration.streaming import run_workflow_stream


async def test_workflow():
    """Test complete workflow with streaming."""
    print("🚀 Starting Step 39 End-to-End Test\n")
    
    # Initialize clients
    print("1️⃣  Initializing clients...")
    data_client = DataClient()
    llm_client = LLMClient()
    print(f"   ✅ LLM Provider: {llm_client.provider}")
    print(f"   ✅ LLM Model: {llm_client.model}\n")
    
    # Test question
    question = "What are the unemployment trends in Qatar?"
    print(f"2️⃣  Testing question: '{question}'\n")
    
    # Run workflow
    print("3️⃣  Running workflow with streaming...\n")
    
    stages_seen = []
    agent_count = 0
    synthesis_tokens = 0
    
    async for event in run_workflow_stream(question, data_client, llm_client):
        stage = event.stage
        status = event.status
        
        if status == "complete":
            stages_seen.append(stage)
            latency = event.latency_ms or 0
            print(f"   ✅ {stage}: {latency:.0f}ms")
            
            if stage.startswith("agent:"):
                agent_count += 1
        
        elif status == "streaming" and stage == "synthesize":
            synthesis_tokens += 1
    
    print(f"\n4️⃣  Workflow Complete!")
    print(f"   📊 Stages: {len(stages_seen)}")
    print(f"   🤖 Agents: {agent_count}")
    print(f"   ✨ Synthesis tokens: {synthesis_tokens}")
    
    # Verify expected stages
    print(f"\n5️⃣  Verification:")
    assert "classify" in stages_seen, "Missing classify stage"
    print(f"   ✅ Classification")
    
    assert "prefetch" in stages_seen, "Missing prefetch stage"
    print(f"   ✅ Prefetch")
    
    assert agent_count >= 3, f"Expected >=3 agents, got {agent_count}"
    print(f"   ✅ Agents ({agent_count})")
    
    assert "verify" in stages_seen, "Missing verify stage"
    print(f"   ✅ Verification")
    
    assert "synthesize" in stages_seen, "Missing synthesize stage"
    print(f"   ✅ Synthesis")
    
    assert synthesis_tokens > 0, "No synthesis tokens"
    print(f"   ✅ Streaming ({synthesis_tokens} tokens)")
    
    assert "done" in stages_seen, "Missing done stage"
    print(f"   ✅ Completion")
    
    print(f"\n✅ ALL TESTS PASSED!")
    print(f"\n🎉 Step 39 system is working correctly!")


if __name__ == "__main__":
    asyncio.run(test_workflow())
