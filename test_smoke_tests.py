"""Production Smoke Tests - 3 test queries."""

import requests
import json
import time

API_URL = "http://localhost:8000/api/v1/council/stream"

# 3 test queries covering different complexities
test_queries = [
    {
        "name": "Simple Query",
        "question": "What is Qatar's GDP?",
        "expected_time": 30,
        "expected_complexity": "simple"
    },
    {
        "name": "Medium Query",
        "question": "Analyze Qatar's labor market trends",
        "expected_time": 1200,  # 20 minutes
        "expected_complexity": "medium"
    },
    {
        "name": "Complex Query",
        "question": "Should Qatar invest in tech hub vs logistics hub?",
        "expected_time": 1800,  # 30 minutes
        "expected_complexity": "complex"
    }
]

print("="*80)
print("PRODUCTION SMOKE TESTS")
print("="*80)
print(f"Testing {len(test_queries)} queries")
print("="*80)

results = []

for i, test in enumerate(test_queries, 1):
    print(f"\n[Test {i}/{len(test_queries)}] {test['name']}")
    print(f"  Query: {test['question']}")
    print(f"  Expected: {test['expected_complexity']}, ~{test['expected_time']}s")
    print("-"*80)
    
    start_time = time.time()
    
    try:
        response = requests.post(
            API_URL,
            json={"question": test['question']},
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=test['expected_time'] + 300  # Extra buffer
        )
        
        if response.status_code != 200:
            print(f"  [FAIL] HTTP {response.status_code}")
            results.append({
                **test,
                "status": "FAILED",
                "error": f"HTTP {response.status_code}"
            })
            continue
        
        # Process stream
        events = []
        stages = []
        
        for line in response.iter_lines():
            if line and line.decode('utf-8').startswith('data: '):
                data = line[6:]
                try:
                    event = json.loads(data)
                    events.append(event)
                    stage = event.get('stage', '')
                    if stage and stage not in stages:
                        stages.append(stage)
                except:
                    pass
        
        elapsed = time.time() - start_time
        
        # Analyze results
        has_synthesis = any(e.get('stage') in ['synthesize', 'complete'] for e in events)
        has_verification = 'verify' in stages
        
        print(f"  [PASS] Completed in {elapsed:.1f}s")
        print(f"  Stages: {len(stages)} stages executed")
        print(f"  Events: {len(events)} total events")
        print(f"  Synthesis: {'YES' if has_synthesis else 'NO'}")
        print(f"  Verification: {'YES' if has_verification else 'NO'}")
        
        # Check for final synthesis
        final_events = [e for e in events if e.get('stage') == 'complete']
        if final_events:
            final_payload = final_events[-1].get('payload', {})
            synthesis = final_payload.get('final_synthesis', '')
            confidence = final_payload.get('confidence_score', 0)
            
            print(f"  Synthesis length: {len(synthesis)} chars")
            print(f"  Confidence: {confidence:.0%}")
        
        results.append({
            **test,
            "status": "SUCCESS",
            "time": elapsed,
            "stages": len(stages),
            "events": len(events)
        })
        
    except requests.exceptions.Timeout:
        print(f"  [FAIL] Timeout (>{test['expected_time']}s)")
        results.append({
            **test,
            "status": "TIMEOUT"
        })
    except Exception as e:
        print(f"  [FAIL] Error: {str(e)[:100]}")
        results.append({
            **test,
            "status": "ERROR",
            "error": str(e)[:200]
        })

# Summary
print("\n" + "="*80)
print("SMOKE TEST RESULTS")
print("="*80)

successful = sum(1 for r in results if r.get('status') == 'SUCCESS')
total = len(results)

print(f"\nSuccess: {successful}/{total}")

for i, result in enumerate(results, 1):
    status_icon = "[PASS]" if result.get('status') == 'SUCCESS' else "[FAIL]"
    print(f"{status_icon} Test {i}: {result['name']} - {result.get('status')}")
    if result.get('status') == 'SUCCESS':
        print(f"         Time: {result.get('time', 0):.1f}s, Stages: {result.get('stages', 0)}")

print("\n" + "="*80)
if successful == total:
    print(f"[SUCCESS] ALL SMOKE TESTS PASSED ({successful}/{total})")
    print("System ready for production!")
else:
    print(f"[REVIEW] {total - successful} tests failed")
print("="*80)

