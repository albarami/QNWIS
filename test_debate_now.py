#!/usr/bin/env python3
"""
Direct backend test - proves legendary debate system works.
Connects to backend SSE stream and prints all events.
"""

import requests
import json
import time
from datetime import datetime

BACKEND_URL = "http://localhost:8000"
STREAM_ENDPOINT = f"{BACKEND_URL}/api/v1/council/stream"

TEST_QUESTION = "What are the risks of increasing Qatar's Qatarization target to 80% by 2028 while maintaining 5% GDP growth?"

def test_backend():
    print("=" * 80)
    print("🚀 LEGENDARY DEBATE SYSTEM - BACKEND TEST")
    print("=" * 80)
    print()
    print(f"⏰ Start Time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"❓ Question: {TEST_QUESTION}")
    print(f"🔗 Backend: {BACKEND_URL}")
    print()
    print("=" * 80)
    print("📡 STREAMING EVENTS...")
    print("=" * 80)
    print()
    
    start_time = time.time()
    event_count = 0
    debate_turns = 0
    stages_seen = set()
    agents_seen = set()
    
    try:
        # Stream SSE events from backend
        response = requests.post(
            STREAM_ENDPOINT,
            json={
                "question": TEST_QUESTION,
                "provider": "anthropic"
            },
            stream=True,
            headers={"Accept": "text/event-stream"},
            timeout=1800  # 30 minutes
        )
        
        print(f"✅ Connection established (HTTP {response.status_code})")
        print()
        
        for line in response.iter_lines():
            if not line:
                continue
                
            line = line.decode('utf-8')
            
            # Parse SSE format
            if line.startswith('data: '):
                data_json = line[6:]  # Remove 'data: ' prefix
                
                try:
                    event = json.loads(data_json)
                    event_count += 1
                    
                    stage = event.get('stage', 'unknown')
                    status = event.get('status', 'unknown')
                    
                    stages_seen.add(stage)
                    
                    # Track debate turns
                    if stage == 'debate:turn':
                        debate_turns += 1
                        turn_data = event.get('payload', {})
                        agent = turn_data.get('agent', 'Unknown')
                        turn_type = turn_data.get('type', 'unknown')
                        message = turn_data.get('message', '')
                        
                        print(f"💬 DEBATE TURN {debate_turns}: {agent} - {turn_type}")
                        print(f"   {message[:150]}...")
                        print()
                    
                    # Track agents
                    elif stage.startswith('agent:'):
                        agent_name = stage.split(':', 1)[1]
                        agents_seen.add(agent_name)
                        if status == 'complete':
                            print(f"✅ Agent: {agent_name} - COMPLETE")
                    
                    # Major stage transitions
                    elif status == 'running':
                        elapsed = time.time() - start_time
                        print(f"🔄 [{elapsed:.0f}s] Stage: {stage.upper()} - STARTING")
                        
                    elif status == 'complete':
                        elapsed = time.time() - start_time
                        latency = event.get('latency_ms', 0)
                        payload = event.get('payload', {})
                        
                        print(f"✅ [{elapsed:.0f}s] Stage: {stage.upper()} - COMPLETE ({latency:.0f}ms)")
                        
                        # Show important details
                        if stage == 'debate':
                            print(f"   💬 Conversation turns: {debate_turns}")
                            print(f"   📊 Total turns: {payload.get('total_turns', 0)}")
                            print(f"   ✔️  Consensus: {payload.get('consensus', {}).get('status', 'N/A')}")
                        
                        elif stage == 'agents':
                            print(f"   🤖 Agents completed: {len(agents_seen)}")
                        
                        print()
                    
                    elif stage == 'error':
                        elapsed = time.time() - start_time
                        print(f"❌ [{elapsed:.0f}s] ERROR: stage={stage} payload={event.get('payload')} message={event.get('message')}")
                        
                    # Done!
                    elif stage == 'done':
                        elapsed = time.time() - start_time
                        print()
                        print("=" * 80)
                        print("🎉 WORKFLOW COMPLETE!")
                        print("=" * 80)
                        print(f"⏱️  Total Time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
                        print(f"📊 Total Events: {event_count}")
                        print(f"💬 Debate Turns: {debate_turns}")
                        print(f"🤖 Agents: {len(agents_seen)}")
                        print(f"🎯 Stages: {', '.join(sorted(stages_seen))}")
                        print("=" * 80)
                        break
                        
                except json.JSONDecodeError:
                    pass
                    
    except KeyboardInterrupt:
        print()
        print("❌ Interrupted by user")
    except requests.exceptions.Timeout:
        print()
        print("⏰ Timeout after 30 minutes")
    except Exception as e:
        print()
        print(f"❌ Error: {e}")
    
    elapsed = time.time() - start_time
    print()
    print("=" * 80)
    print("📈 FINAL STATS")
    print("=" * 80)
    print(f"⏱️  Duration: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
    print(f"📊 Events: {event_count}")
    print(f"💬 Debate Turns: {debate_turns}")
    print(f"🤖 Unique Agents: {len(agents_seen)}")
    print(f"🎯 Stages Seen: {len(stages_seen)}")
    if stages_seen:
        print(f"   {', '.join(sorted(stages_seen))}")
    print("=" * 80)

if __name__ == "__main__":
    test_backend()
