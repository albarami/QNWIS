"""Simple backend test - direct testing without streaming delays."""
import requests
import json
import sys

API_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n1. Testing Health Endpoint...")
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5)
        print(f"   Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ System Status: {data['status']}")
            for comp in data.get('components', []):
                print(f"   ✅ {comp['name']}: {comp['status']}")
            return True
        else:
            print(f"   ❌ Health check failed")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_json_endpoint():
    """Test non-streaming JSON endpoint"""
    print("\n2. Testing JSON Workflow Endpoint...")
    print("   Question: 'Quick test question'")
    
    try:
        resp = requests.post(
            f"{API_URL}/api/v1/council/run-llm",
            json={"question": "Quick test question", "provider": "stub"},
            timeout=60
        )
        print(f"   Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ Workflow completed")
            print(f"   ✅ Complexity: {data.get('complexity', 'N/A')}")
            print(f"   ✅ Facts: {len(data.get('extracted_facts', []))}")
            print(f"   ✅ Agents: {len(data.get('agents_invoked', []))}")
            print(f"   ✅ Confidence: {data.get('confidence_score', 0)}")
            
            if data.get('agents_invoked'):
                print(f"   ✅ Agents invoked: {', '.join(data['agents_invoked'])}")
            
            return True
        else:
            print(f"   ❌ Request failed")
            print(f"   Response: {resp.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timeout (60s)")
        return False
    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}: {e}")
        return False

def test_streaming_quick():
    """Test streaming endpoint (first few events only)"""
    print("\n3. Testing Streaming Endpoint (quick check)...")
    
    try:
        resp = requests.post(
            f"{API_URL}/api/v1/council/stream",
            json={"question": "Test", "provider": "stub"},
            stream=True,
            timeout=30
        )
        
        print(f"   Status Code: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"   ❌ Stream failed to connect")
            return False
        
        print(f"   ✅ Stream connected")
        
        # Read first 5 events only
        event_count = 0
        for line in resp.iter_lines():
            if not line:
                continue
            
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    stage = data.get('stage', 'unknown')
                    status = data.get('status', 'unknown')
                    print(f"   ✅ Event {event_count + 1}: {stage} → {status}")
                    
                    event_count += 1
                    if event_count >= 5:
                        print(f"   ✅ First 5 events received successfully")
                        return True
                except:
                    pass
        
        return event_count > 0
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("  QNWIS BACKEND QUICK TEST")
    print("  (Direct backend testing, no frontend)")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Health
    results['health'] = test_health()
    if not results['health']:
        print("\n❌ Backend health check failed. Is the server running?")
        print("   Start with: python -m uvicorn src.qnwis.api.server:app --host 127.0.0.1 --port 8000")
        sys.exit(1)
    
    # Test 2: JSON endpoint
    results['json'] = test_json_endpoint()
    
    # Test 3: Streaming (just first few events)
    results['streaming'] = test_streaming_quick()
    
    # Summary
    print("\n" + "=" * 60)
    print("  TEST RESULTS:")
    print("=" * 60)
    
    for name, passed in results.items():
        icon = "✅" if passed else "❌"
        status = "PASSED" if passed else "FAILED"
        print(f"  {icon} {name.upper():15s}: {status}")
    
    all_passed = all(results.values())
    
    print("=" * 60)
    if all_passed:
        print("  ✅ ALL BACKEND TESTS PASSED!")
        print("  Backend is working correctly.")
    else:
        print("  ❌ SOME TESTS FAILED")
        print("  Check errors above.")
    print("=" * 60)

if __name__ == "__main__":
    main()
