#!/usr/bin/env python3
"""Simple test to trigger workflow and check logs."""
import requests
import sys

print("🧪 Sending request...", flush=True)
try:
    response = requests.post(
        "http://localhost:8000/api/v1/council/stream",
        json={"question": "test", "provider": "anthropic"},
        stream=True,
        timeout=10
    )
    print(f"Status: {response.status_code}", flush=True)
    
    count = 0
    for line in response.iter_lines():
        if line:
            print(f"Event {count}: {line.decode()[:100]}", flush=True)
            count += 1
            if count >= 5:
                break
                
except Exception as e:
    print(f"Error: {e}", flush=True)
    sys.exit(1)
