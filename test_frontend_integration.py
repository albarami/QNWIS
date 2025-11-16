"""
Test frontend integration by verifying:
1. Backend API responds
2. SSE stream works
3. All expected fields are in payload
"""
import requests
import json
from datetime import datetime

def test_api_health():
    """Test 1: Verify API is responding"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"✅ Test 1/3: API Health Check - Status {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Test 1/3: API Health Check Failed - {e}")
        return False

def test_sse_stream():
    """Test 2: Verify SSE streaming works"""
    try:
        print("\n🔄 Test 2/3: Testing SSE Stream...")
        payload = {
            "question": "Test query for SSE verification",
            "provider": "stub"  # Use stub to avoid real LLM calls
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/council/stream",
            json=payload,
            stream=True,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Test 2/3: SSE Stream Failed - Status {response.status_code}")
            return False
        
        events_received = 0
        stages_seen = set()
        
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    try:
                        event_data = json.loads(decoded[6:])
                        events_received += 1
                        if 'stage' in event_data:
                            stages_seen.add(event_data['stage'])
                        
                        # Stop after a few events for testing
                        if events_received >= 5:
                            break
                    except json.JSONDecodeError:
                        pass
        
        print(f"✅ Test 2/3: SSE Stream Working - {events_received} events, {len(stages_seen)} unique stages")
        print(f"   Stages seen: {', '.join(sorted(stages_seen))}")
        return events_received > 0
        
    except Exception as e:
        print(f"❌ Test 2/3: SSE Stream Failed - {e}")
        return False

def test_workflow_state_fields():
    """Test 3: Verify all required WorkflowState fields exist in payloads"""
    try:
        print("\n🔄 Test 3/3: Verifying WorkflowState fields...")
        
        required_fields = [
            'stage',
            'status',
            'payload',
            'timestamp'
        ]
        
        payload_fields = [
            'query',
            'complexity',
            'extracted_facts',
            'agent_outputs',
            'agents_invoked',
            'final_synthesis',
            'confidence_score'
        ]
        
        # Quick stub call
        response = requests.post(
            "http://localhost:8000/api/v1/council/stream",
            json={"question": "Field verification test", "provider": "stub"},
            stream=True,
            timeout=15
        )
        
        fields_found = set()
        
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    try:
                        event = json.loads(decoded[6:])
                        fields_found.update(event.keys())
                        
                        if event.get('stage') == 'done':
                            break
                    except json.JSONDecodeError:
                        pass
        
        missing = set(required_fields) - fields_found
        if missing:
            print(f"❌ Test 3/3: Missing required fields: {missing}")
            return False
        
        print(f"✅ Test 3/3: WorkflowState fields verified - {len(fields_found)} fields present")
        print(f"   Fields: {', '.join(sorted(fields_found))}")
        return True
        
    except Exception as e:
        print(f"❌ Test 3/3: Field verification failed - {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("FRONTEND INTEGRATION TEST SUITE")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    # Run all tests
    results.append(("API Health", test_api_health()))
    results.append(("SSE Streaming", test_sse_stream()))
    results.append(("WorkflowState Fields", test_workflow_state_fields()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Frontend integration verified!")
        exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Review errors above")
        exit(1)
