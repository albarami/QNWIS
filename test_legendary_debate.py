#!/usr/bin/env python3
"""Test script for legendary debate feature."""

import requests
import json
import time

url = "http://localhost:8000/api/v1/council/stream"
data = {
    "question": "Qatar Ministry of Labour workforce nationalization",
    "provider": "anthropic"
}

print("🎭 Testing LEGENDARY DEBATE Feature!")
print(f"URL: {url}")
print(f"Question: {data['question']}\n")
print("="*70)

debate_turns = []
all_events = []
start_time = time.time()

try:
    response = requests.post(url, json=data, stream=True, timeout=300)
    print(f"✅ Connection established (Status: {response.status_code})\n")
    
    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            
            if decoded.startswith("data:"):
                try:
                    json_str = decoded[5:].strip()
                    event = json.loads(json_str)
                    stage = event.get("stage", "")
                    status = event.get("status", "")
                    
                    all_events.append(stage)
                    
                    # Track debate turns
                    if "debate:turn" in stage:
                        payload = event.get("payload", {})
                        turn_num = payload.get("turn", "?")
                        agent = payload.get("agent", "?")
                        turn_type = payload.get("type", "?")
                        message = payload.get("message", "")[:80]
                        
                        debate_turns.append(event)
                        
                        elapsed = time.time() - start_time
                        print(f"🎯 TURN {turn_num} [{elapsed:.1f}s] {agent.upper()} ({turn_type})")
                        print(f"   {message}...")
                        print()
                    
                    # Track key stages
                    elif stage in ["classify", "prefetch", "rag", "agent_selection", "debate", "critique", "verify", "synthesize", "done"]:
                        elapsed = time.time() - start_time
                        print(f"📍 Stage: {stage} ({status}) [{elapsed:.1f}s]")
                        
                    # Exit on done
                    if stage == "done":
                        break
                        
                except Exception as e:
                    pass
    
    print("\n" + "="*70)
    print("📊 TEST RESULTS:")
    print(f"   Total events: {len(all_events)}")
    print(f"   Debate turns captured: {len(debate_turns)}")
    print(f"   Total duration: {time.time() - start_time:.1f}s")
    print(f"   Unique stages: {set(all_events)}")
    
    if len(debate_turns) > 0:
        print(f"\n✅ SUCCESS! LEGENDARY DEBATE IS STREAMING!")
        print(f"   Captured {len(debate_turns)} debate turns in real-time")
    else:
        print(f"\n❌ NO DEBATE TURNS DETECTED")
        print(f"   Expected: debate:turn events")
        print(f"   Frontend will show 'Waiting for debate to start...'")
        
except KeyboardInterrupt:
    print("\n\n⚠️  Test interrupted by user")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
