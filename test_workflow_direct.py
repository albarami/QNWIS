#!/usr/bin/env python3
"""
Direct test of workflow execution - bypasses SSE/API layer
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.qnwis.data.client import DataClient
from src.qnwis.llm.client import LLMClient
from src.qnwis.classification.classifier import Classifier
from src.qnwis.orchestration.streaming import run_workflow_stream

async def main():
    print("\n" + "="*80)
    print("🧪 DIRECT WORKFLOW TEST")
    print("="*80)
    
    question = "Qatar is considering mandating 40% Qatari nationals in the private sector technology industry by 2027, up from current 8%. Provide comprehensive analysis."
    
    print(f"\n📝 Question: {question[:100]}...")
    print(f"\n🔧 Initializing clients...")
    
    data_client = DataClient()
    llm_client = LLMClient(provider="anthropic")
    classifier = Classifier()
    
    print(f"✅ Clients initialized")
    print(f"\n🚀 Starting workflow stream...\n")
    
    event_count = 0
    try:
        async for event in run_workflow_stream(
            question=question,
            data_client=data_client,
            llm_client=llm_client,
            classifier=classifier,
        ):
            event_count += 1
            print(f"\n📨 Event #{event_count}:")
            print(f"   Stage: {event.stage}")
            print(f"   Status: {event.status}")
            
            if event.payload:
                if "classification" in event.payload:
                    print(f"   Classification: {event.payload['classification'].get('complexity', 'N/A')}")
                if "fact_count" in event.payload:
                    print(f"   Facts: {event.payload['fact_count']}")
                if "extracted_facts" in event.payload:
                    print(f"   Extracted facts: {len(event.payload['extracted_facts'])}")
                if "agents_invoked" in event.payload:
                    print(f"   Agents: {event.payload['agents_invoked']}")
                if "error" in event.payload:
                    print(f"   ❌ ERROR: {event.payload['error']}")
                    
            if event.latency_ms:
                print(f"   Latency: {event.latency_ms:.0f}ms")
                
        print(f"\n{'='*80}")
        print(f"✅ Workflow completed successfully!")
        print(f"📊 Total events received: {event_count}")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ Workflow FAILED!")
        print(f"Error: {e}")
        print(f"{'='*80}\n")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
