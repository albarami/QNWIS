import httpx

url = "http://localhost:8000/api/v1/council/stream"
payload = {"question": "test", "provider": "stub"}

try:
    with httpx.Client(timeout=10.0) as client:
        response = client.post(url, json=payload, headers={"Accept": "text/event-stream"})
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"\nFirst 500 chars of response:")
        print(response.text[:500])
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
