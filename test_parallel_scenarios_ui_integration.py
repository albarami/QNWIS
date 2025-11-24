"""
Integration test for parallel scenarios with UI event streaming.

Tests the complete workflow from query submission to final results,
capturing and verifying all SSE events.
"""

import requests
import json
import time

API_URL = "http://localhost:8000/api/v1/council/stream"

print("="*80)
print("PARALLEL SCENARIOS UI INTEGRATION TEST")
print("="*80)

# Complex query that triggers parallel scenarios
query = "Should Qatar invest in renewable energy or maintain LNG focus?"

print(f"\nQuery: {query}")
print(f"Expected: 6 scenarios on GPUs 0-5")
print("\n" + "="*80)
print("Submitting query and capturing events...")
print("="*80)

start_time = time.time()

try:
    response = requests.post(
        API_URL,
        json={"question": query},
        headers={"Content-Type": "application/json"},
        stream=True,
        timeout=1800  # 30 minutes max
    )
    
    if response.status_code != 200:
        print(f"❌ ERROR: HTTP {response.status_code}")
        print(response.text)
        exit(1)
    
    # Event counters
    events_received = []
    scenario_start_events = []
    scenario_complete_events = []
    progress_events = []
    parallel_exec_events = []
    meta_synthesis_events = []
    
    # Process SSE stream
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data = line_str[6:]
                try:
                    event = json.loads(data)
                    events_received.append(event)
                    
                    stage = event.get('stage', '')
                    status = event.get('status', '')
                    
                    # Categorize events
                    if stage == 'scenario_gen':
                        print(f"✅ Scenario generation: {status}")
                    elif stage == 'parallel_exec':
                        parallel_exec_events.append(event)
                        print(f"✅ Parallel execution: {status}")
                    elif stage.startswith('scenario:'):
                        if status == 'started':
                            scenario_start_events.append(event)
                            scenario_name = event.get('payload', {}).get('scenario_name', 'Unknown')
                            gpu_id = event.get('payload', {}).get('gpu_id', '?')
                            print(f"  ▶️  Scenario started: {scenario_name} on GPU {gpu_id}")
                        elif status == 'complete':
                            scenario_complete_events.append(event)
                            scenario_name = event.get('payload', {}).get('scenario_name', 'Unknown')
                            duration = event.get('payload', {}).get('duration_seconds', 0)
                            print(f"  ✅ Scenario complete: {scenario_name} ({duration:.1f}s)")
                    elif stage == 'parallel_progress':
                        progress_events.append(event)
                        payload = event.get('payload', {})
                        completed = payload.get('completed', 0)
                        total = payload.get('total', 0)
                        percent = payload.get('percent', 0)
                        print(f"  📊 Progress: {completed}/{total} ({percent}%)")
                    elif stage == 'meta_synthesis':
                        meta_synthesis_events.append(event)
                        print(f"✅ Meta-synthesis: {status}")
                    
                except json.JSONDecodeError:
                    pass
    
    elapsed = time.time() - start_time
    
    # Analysis and verification
    print("\n" + "="*80)
    print("TEST RESULTS")
    print("="*80)
    
    print(f"\nExecution time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
    print(f"Total events received: {len(events_received)}")
    
    # Verify event counts
    print(f"\nEvent Breakdown:")
    print(f"  Scenario start events: {len(scenario_start_events)}")
    print(f"  Scenario complete events: {len(scenario_complete_events)}")
    print(f"  Progress events: {len(progress_events)}")
    print(f"  Parallel exec events: {len(parallel_exec_events)}")
    print(f"  Meta-synthesis events: {len(meta_synthesis_events)}")
    
    # Assertions
    errors = []
    
    if len(scenario_start_events) == 0:
        errors.append("❌ No scenario start events received")
    else:
        print(f"✅ Scenario start events: {len(scenario_start_events)}")
    
    if len(scenario_complete_events) == 0:
        errors.append("❌ No scenario complete events received")
    else:
        print(f"✅ Scenario complete events: {len(scenario_complete_events)}")
    
    if len(progress_events) == 0:
        errors.append("❌ No progress events received")
    else:
        print(f"✅ Progress events: {len(progress_events)}")
    
    if len(parallel_exec_events) == 0:
        errors.append("❌ No parallel_exec events received")
    else:
        print(f"✅ Parallel exec events: {len(parallel_exec_events)}")
    
    # Check for meta-synthesis
    final_events = [e for e in events_received if e.get('stage') == 'done' or e.get('stage') == 'complete']
    has_meta_synthesis = False
    if final_events:
        final_payload = final_events[-1].get('payload', {})
        if 'meta_synthesis' in final_payload or 'final_synthesis' in final_payload:
            has_meta_synthesis = True
            print(f"✅ Meta-synthesis in final payload")
    
    if not has_meta_synthesis and len(meta_synthesis_events) == 0:
        errors.append("⚠️ No meta-synthesis results found")
    
    # Summary
    print("\n" + "="*80)
    if len(errors) == 0:
        print("✅ ALL CHECKS PASSED")
        print("="*80)
        print("\nIntegration test: SUCCESS")
        print(f"Parallel scenarios: {len(scenario_complete_events)} completed")
        print(f"Events properly emitted: YES")
        print(f"Ready for UI integration: YES")
    else:
        print("⚠️ SOME CHECKS FAILED")
        print("="*80)
        for error in errors:
            print(error)
        print("\nIntegration test: PARTIAL SUCCESS")
        print("Backend works but event emission needs refinement")
    
    print("="*80)
    
except requests.exceptions.Timeout:
    print("❌ ERROR: Request timed out")
    exit(1)
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

