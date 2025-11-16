import requests
import json

url = "http://localhost:8000/api/v1/council/stream"
payload = {
    "question": "What are the implications of raising the minimum wage?",
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514"
}

print("Sending request to:", url)
print("Payload:", json.dumps(payload, indent=2))

response = requests.post(url, json=payload, stream=True)

print(f"\nStatus code: {response.status_code}")
print(f"Headers: {dict(response.headers)}")

if response.status_code != 200:
    print(f"\nError response: {response.text}")
else:
    print("\nStreaming response:")
    for line in response.iter_lines():
        if line:
            print(line.decode('utf-8'))
