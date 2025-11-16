"""Test the other council endpoint"""
import requests
import json

url = "http://localhost:8000/api/v1/council/run-llm"
payload = {
    "question": "Test query",
    "provider": "stub",
    "model": None
}

print(f"Testing {url}")
print(f"Payload: {json.dumps(payload, indent=2)}\n")

response = requests.post(url, json=payload)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✅ SUCCESS!")
    print(json.dumps(response.json(), indent=2))
else:
    print(f"❌ ERROR: {response.text}")
