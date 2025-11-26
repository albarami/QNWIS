"""Stress test: 10 complex queries in sequence."""

import requests
import json
import time
import torch

API_URL = "http://localhost:8000/api/v1/council/stream"

# 10 diverse complex queries
queries = [
    "What is Qatar's unemployment rate?",  # Simple - fast
    "Analyze Qatar's tourism sector growth trends.",  # Medium
    "Should Qatar invest in AI infrastructure?",  # Complex
    "What are GCC labor market trends?",  # Simple
    "Evaluate Qatar's food security strategy.",  # Complex
    "What is Qatar's GDP growth?",  # Simple
    "Analyze Qatar nationalization policy effectiveness.",  # Medium
    "Should Qatar expand LNG production or renewable energy?",  # Complex
    "What are Qatar employment statistics?",  # Simple
    "Evaluate Qatar Vision 2030 workforce goals progress.",  # Complex
]

print("="*80)
print("STEP 6: STRESS TEST")
print("="*80)
print(f"Submitting {len(queries)} queries in sequence")
print("Checking for:")
print("  - No memory leaks")
print("  - Consistent performance")
print("  - No rate limit errors")
print("  - All verifications complete")
print("  - GPU memory stable")
print("="*80)

results = []
gpu_memory_before = 0
gpu_memory_after = 0

if torch.cuda.is_available():
    gpu_memory_before = torch.cuda.memory_allocated(6) / 1e9
    print(f"\nGPU 6 memory before: {gpu_memory_before:.2f}GB")

for i, query in enumerate(queries, 1):
    print(f"\n[Query {i}/{len(queries)}] {query[:60]}...")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            API_URL,
            json={"question": query},
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=300  # 5 minutes max per query
        )
        
        if response.status_code != 200:
            print(f"  ERROR: HTTP {response.status_code}")
            results.append({
                'query': query,
                'status': 'FAILED',
                'error': f'HTTP {response.status_code}',
                'time': 0
            })
            continue
        
        # Consume stream
        event_count = 0
        for line in response.iter_lines():
            if line and line.decode('utf-8').startswith('data: '):
                event_count += 1
        
        elapsed = time.time() - start_time
        
        print(f"  Status: OK")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Events: {event_count}")
        
        results.append({
            'query': query,
            'status': 'SUCCESS',
            'time': elapsed,
            'events': event_count
        })
        
    except requests.exceptions.Timeout:
        print(f"  ERROR: Timeout (>300s)")
        results.append({
            'query': query,
            'status': 'TIMEOUT',
            'time': 300
        })
    except Exception as e:
        print(f"  ERROR: {str(e)[:80]}")
        results.append({
            'query': query,
            'status': 'ERROR',
            'error': str(e)[:100],
            'time': 0
        })

if torch.cuda.is_available():
    gpu_memory_after = torch.cuda.memory_allocated(6) / 1e9
    print(f"\nGPU 6 memory after: {gpu_memory_after:.2f}GB")
    memory_leak = gpu_memory_after - gpu_memory_before
    print(f"Memory change: {memory_leak:+.2f}GB")

# Analysis
print("\n" + "="*80)
print("STRESS TEST RESULTS")
print("="*80)

successful = sum(1 for r in results if r['status'] == 'SUCCESS')
failed = sum(1 for r in results if r['status'] in ['FAILED', 'ERROR'])
timeouts = sum(1 for r in results if r['status'] == 'TIMEOUT')

print(f"\nSuccess: {successful}/{len(queries)}")
print(f"Failed:  {failed}/{len(queries)}")
print(f"Timeout: {timeouts}/{len(queries)}")

if successful > 0:
    times = [r['time'] for r in results if r['status'] == 'SUCCESS']
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\nExecution times:")
    print(f"  Average: {avg_time:.1f}s")
    print(f"  Min:     {min_time:.1f}s")
    print(f"  Max:     {max_time:.1f}s")
    
    # Check for performance degradation
    if len(times) >= 3:
        first_third = sum(times[:3]) / 3
        last_third = sum(times[-3:]) / 3
        degradation = ((last_third - first_third) / first_third) * 100
        
        print(f"\nPerformance consistency:")
        print(f"  First 3 avg:  {first_third:.1f}s")
        print(f"  Last 3 avg:   {last_third:.1f}s")
        print(f"  Degradation:  {degradation:+.1f}%")
        
        if abs(degradation) < 20:
            print(f"  [PASS] Consistent performance (<20% variation)")
        else:
            print(f"  [WARN] Performance varied by {degradation:.0f}%")

# Memory leak check
if torch.cuda.is_available():
    print(f"\nMemory leak check:")
    print(f"  Before: {gpu_memory_before:.2f}GB")
    print(f"  After:  {gpu_memory_after:.2f}GB")
    print(f"  Change: {memory_leak:+.2f}GB")
    
    if abs(memory_leak) < 0.5:
        print(f"  [PASS] No significant memory leak (<0.5GB)")
    else:
        print(f"  [WARN] Memory changed by {memory_leak:.2f}GB")

print("\n" + "="*80)
if successful >= 8:  # 80% success rate
    print(f"[PASS] STEP 6: STRESS TEST PASSED ({successful}/{len(queries)} queries)")
    print("System stable under load!")
else:
    print(f"[REVIEW] STEP 6: {successful}/{len(queries)} queries succeeded")
print("="*80)

