"""Quick test script to check streaming endpoint."""
import requests
import json

url = "http://localhost:8000/api/v1/council/stream"
payload = {
    "question": "What is the unemployment rate in Qatar?"
}

print("Testing streaming endpoint...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("\n" + "="*50 + "\n")

try:
    response = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        stream=True,
        timeout=300  # 5 minutes for long LLM workflows
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print("\n" + "="*50 + "\n")
    
    if response.status_code == 200:
        print("Stream events:")
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                print(decoded)
                if len(decoded) > 200:
                    print("  (truncated for readability)")
    else:
        print(f"Error response: {response.text}")
        
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
