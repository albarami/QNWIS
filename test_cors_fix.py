"""Test CORS OPTIONS request."""
import requests

print("Testing CORS OPTIONS request...")

# Test OPTIONS (preflight)
try:
    response = requests.options(
        "http://localhost:8000/api/v1/council/stream",
        headers={
            "Origin": "http://localhost:3001",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"
        }
    )
    
    print(f"OPTIONS Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("\n[PASS] CORS preflight working!")
    else:
        print(f"\n[FAIL] CORS preflight returned {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"ERROR: {e}")

