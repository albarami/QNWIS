#!/usr/bin/env python3
"""Capture full error details."""

import requests
import json

url = "http://localhost:8000/api/v1/council/stream"
data = {
    "question": "Test query",
    "provider": "anthropic"
}

response = requests.post(url, json=data, stream=True, timeout=60)

for line in response.iter_lines():
    if line:
        decoded = line.decode('utf-8')
        print(decoded)
        
        if "error" in decoded.lower():
            print("\n❌ ERROR DETECTED:")
            try:
                if decoded.startswith("data:"):
                    error_event = json.loads(decoded[5:].strip())
                    print(json.dumps(error_event, indent=2))
            except:
                pass
