#!/usr/bin/env python3
"""Test script to capture full debate workflow output."""

import requests
import json

url = "http://localhost:8000/api/v1/council/stream"
data = {
    "question": "Qatar Ministry of Labour",
    "provider": "anthropic"
}

print("🧪 Testing debate workflow...")
print(f"URL: {url}\n")

debate_turns_found = []
all_stages = []

try:
    response = requests.post(url, json=data, stream=True, timeout=180)
    print(f"Status: {response.status_code}\n")
    
    with open("debate_test_output.txt", "w", encoding="utf-8") as f:
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                f.write(decoded + "\n")
                
                # Parse stage names
                if decoded.startswith("data:"):
                    try:
                        json_str = decoded[5:].strip()
                        event_data = json.loads(json_str)
                        stage = event_data.get("stage", "")
                        all_stages.append(stage)
                        
                        if "debate:turn" in stage:
                            debate_turns_found.append(event_data)
                            print(f"✅ DEBATE TURN FOUND: {stage}")
                            print(f"   Payload: {json.dumps(event_data.get('payload', {}), indent=2)}\n")
                    except:
                        pass
    
    print("\n" + "="*60)
    print(f"📊 RESULTS:")
    print(f"   Total stages: {len(all_stages)}")
    print(f"   Unique stages: {set(all_stages)}")
    print(f"   Debate turns found: {len(debate_turns_found)}")
    print(f"\n   Full output saved to: debate_test_output.txt")
    
    if len(debate_turns_found) == 0:
        print("\n❌ NO DEBATE TURNS DETECTED!")
        print("   Expected: debate:turn1, debate:turn2, etc.")
        print("   This is the BUG we need to fix.")
    else:
        print(f"\n✅ SUCCESS! Found {len(debate_turns_found)} debate turns")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
