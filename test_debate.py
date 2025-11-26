#!/usr/bin/env python3
"""Quick test script to trigger debate workflow and check logs."""

import requests
import json

url = "http://localhost:8000/api/v1/council/stream"
data = {
    "question": "Qatar Ministry of Labour",
    "provider": "anthropic"
}

print("🧪 Sending test request to backend...")
print(f"URL: {url}")
print(f"Data: {json.dumps(data, indent=2)}")
print("\n" + "="*60 + "\n")

try:
    response = requests.post(url, json=data, stream=True, timeout=120)
    print(f"Status: {response.status_code}")
    print("\nStreaming events:\n")
    
    for line in response.iter_lines():
        if line:
            print(line.decode('utf-8'))
            
except Exception as e:
    print(f"❌ Error: {e}")
