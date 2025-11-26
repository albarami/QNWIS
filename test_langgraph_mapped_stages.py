"""Test LangGraph workflow with mapped stage names."""

import requests
import json
import time

API_URL = "http://localhost:8000/api/v1/council/stream"
query = "What is Qatar's labor force participation rate?"

print("Testing LangGraph Workflow (Mapped Stage Names)")
print("="*80)
print(f"Query: {query}")
print("="*80)

start_time = time.time()

try:
    response = requests.post(
        API_URL,
        json={"question": query},
        headers={"Content-Type": "application/json"},
        stream=True,
        timeout=180
    )
    
    if response.status_code != 200:
        print(f"ERROR: HTTP {response.status_code}")
        print(response.text)
        exit(1)
    
    stages_seen = []
    events = []
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                try:
                    event = json.loads(data)
                    events.append(event)
                    
                    stage = event.get('stage', '')
                    status = event.get('status', '')
                    
                    if stage and stage not in stages_seen:
                        stages_seen.append(stage)
                        print(f"[{len(stages_seen)}] {stage}: {status}")
                    
                except json.JSONDecodeError:
                    pass
    
    elapsed = time.time() - start_time
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Execution time: {elapsed:.1f}s")
    print(f"Total stages: {len(stages_seen)}")
    print(f"Stages: {stages_seen}")
    
    # Check for LangGraph stages (mapped names)
    # classifier->classify, extraction->prefetch, rag is synthetic, verification->verify, synthesis->synthesize
    expected_mapped_stages = [
        'classify',  # classifier mapped
        'prefetch',  # extraction mapped
        'rag',  # synthetic stage
        'verify',  # verification mapped
        'synthesize'  # synthesis mapped
    ]
    
    found_stages = [s for s in expected_mapped_stages if s in stages_seen]
    
    print(f"\nLangGraph mapped stages found: {len(found_stages)}/{len(expected_mapped_stages)}")
    print(f"Found: {found_stages}")
    
    if 'classify' in stages_seen and 'prefetch' in stages_seen:
        print("\n[PASS] LangGraph workflow active (mapped stage names)")
        
        # Check for verification (mapped as 'verify')
        if 'verify' in stages_seen:
            print("[PASS] Verification node executed!")
            
            # Get verification results
            final_events = [e for e in events if e.get('stage') == 'complete']
            if final_events:
                payload = final_events[-1].get('payload', {})
                fact_check = payload.get('fact_check_results', {})
                gpu_verification = fact_check.get('gpu_verification')
                
                if gpu_verification:
                    print(f"\nGPU Fact Verification Results:")
                    print(f"  Total claims: {gpu_verification.get('total_claims', 0)}")
                    print(f"  Verified claims: {gpu_verification.get('verified_claims', 0)}")
                    print(f"  Verification rate: {gpu_verification.get('verification_rate', 0):.0%}")
                    print(f"  Avg confidence: {gpu_verification.get('avg_confidence', 0):.2f}")
                    print("\n[PASS] GPU fact verification operational!")
                else:
                    print("\n[INFO] Verification ran but checking payload...")
                    # Check verify stage payload directly
                    verify_events = [e for e in events if e.get('stage') == 'verify']
                    if verify_events:
                        verify_payload = verify_events[-1].get('payload', {})
                        fact_check = verify_payload.get('fact_check_results', {})
                        if fact_check:
                            print(f"[INFO] Verification results found in verify stage:")
                            print(f"  Status: {fact_check.get('status')}")
                            gpu_ver = fact_check.get('gpu_verification')
                            if gpu_ver:
                                print(f"  GPU verification active!")
                            else:
                                print(f"  GPU verification not in payload")
        else:
            print("[WARN] Verification stage not found (expected 'verify')")
    else:
        print(f"\n[FAIL] LangGraph stages not found")
        exit(1)
    
    print("\n" + "="*80)
    print("[SUCCESS] System working with LangGraph workflow!")
    print("="*80)
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

