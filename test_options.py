import requests

print("Testing OPTIONS request...")
try:
    response = requests.options(
        "http://localhost:8000/api/v1/council/stream",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("\n✅ OPTIONS working - CORS should work")
    else:
        print(f"\n❌ OPTIONS returned {response.status_code} - This is why frontend can't connect")
except Exception as e:
    print(f"ERROR: {e}")

