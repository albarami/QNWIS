"""Test API endpoint to capture full error."""
import httpx
import json

url = "http://127.0.0.1:8000/api/v1/council/stream"
payload = {
    "question": "Compare Qatar unemployment to GCC",
    "provider": "stub"
}

try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"\nResponse body:")
        print(response.text[:2000])
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
