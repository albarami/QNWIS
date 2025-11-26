#!/usr/bin/env python3
"""
Phase 8 Test Runner - Simplified
Captures only agent invocations and key debate signals
"""
import requests
import json
import time
from datetime import datetime

def extract_key_info(sse_response):
    """Extract agent invocations and debate signals from SSE response"""
    agents_invoked = set()
    debate_turns = []
    errors = []
    
    for line in sse_response.split('\n'):
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])  # Skip "data: " prefix
                stage = data.get('stage', '')
                payload = data.get('payload', {})
                
                # Capture agent invocations
                if 'agent:' in stage:
                    agent_name = stage.split(':')[1]
                    agents_invoked.add(agent_name)
                
                # Capture debate turns
                if stage == 'debate:turn':
                    agent = payload.get('agent', '')
                    turn_type = payload.get('type', '')
                    message = payload.get('message', '')[:200]  # First 200 chars
                    debate_turns.append({
                        'agent': agent,
                        'type': turn_type,
                        'preview': message
                    })
                
                # Capture errors
                if 'error' in stage or data.get('status') == 'error':
                    errors.append(payload.get('error', data.get('message', 'Unknown error')))
                    
            except json.JSONDecodeError:
                continue
    
    return agents_invoked, debate_turns, errors

def run_test(test_name, question):
    """Run a single test"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    print(f"Question: {question}")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    
    url = "http://127.0.0.1:8000/api/v1/council/stream"
    payload = {
        "question": question,
        "provider": "anthropic"
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300,  # 5 minute timeout
            stream=True
        )
        
        # Collect response
        sse_data = ""
        print("Receiving response...")
        for line in response.iter_lines():
            if line:
                sse_data += line.decode('utf-8') + "\n"
        
        print(f"Completed: {datetime.now().strftime('%H:%M:%S')}")
        
        # Extract key information
        agents, turns, errors = extract_key_info(sse_data)
        
        return {
            'test_name': test_name,
            'agents_invoked': sorted(list(agents)),
            'debate_turns_count': len(turns),
            'debate_turns_sample': turns[:5],  # First 5 turns
            'errors': errors,
            'success': len(errors) == 0 and 'MicroEconomist' in agents and 'MacroEconomist' in agents
        }
        
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out after 5 minutes")
        return {
            'test_name': test_name,
            'error': 'Timeout after 5 minutes',
            'success': False
        }
    except Exception as e:
        print(f"ERROR: {e}")
        return {
            'test_name': test_name,
            'error': str(e),
            'success': False
        }

def main():
    """Run both Phase 8 tests"""
    print("="*60)
    print("PHASE 8 END-TO-END VALIDATION")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Food Security
    test1_result = run_test(
        "FOOD SECURITY",
        "Should Qatar invest $15B in Food Valley project targeting 40% food self-sufficiency by 2030?"
    )
    
    # Save Test 1 results
    with open('phase8_test1_results.json', 'w') as f:
        json.dump(test1_result, f, indent=2)
    
    print("\n" + "="*60)
    print("TEST 1 RESULTS:")
    print("="*60)
    print(f"Agents invoked: {', '.join(test1_result.get('agents_invoked', []))}")
    print(f"Debate turns: {test1_result.get('debate_turns_count', 0)}")
    print(f"Errors: {len(test1_result.get('errors', []))}")
    print(f"Success: {test1_result.get('success', False)}")
    
    # Only run Test 2 if Test 1 succeeded
    if test1_result.get('success'):
        print("\nProceeding to Test 2...")
        time.sleep(2)
        
        # Test 2: Labor Market
        test2_result = run_test(
            "LABOR MARKET",
            "What are Qatar's hospitality sector labor market trends and workforce challenges?"
        )
        
        # Save Test 2 results
        with open('phase8_test2_results.json', 'w') as f:
            json.dump(test2_result, f, indent=2)
        
        print("\n" + "="*60)
        print("TEST 2 RESULTS:")
        print("="*60)
        print(f"Agents invoked: {', '.join(test2_result.get('agents_invoked', []))}")
        print(f"Debate turns: {test2_result.get('debate_turns_count', 0)}")
        print(f"Errors: {len(test2_result.get('errors', []))}")
        print(f"Success: {test2_result.get('success', False)}")
    else:
        print("\n⚠️  Test 1 failed - skipping Test 2")
        test2_result = {'skipped': True}
    
    # Final summary
    print("\n" + "="*60)
    print("PHASE 8 FINAL SUMMARY")
    print("="*60)
    phase8_pass = test1_result.get('success', False) and test2_result.get('success', False)
    print(f"Overall Status: {'✅ PASS' if phase8_pass else '❌ FAIL'}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return 0 if phase8_pass else 1

if __name__ == "__main__":
    exit(main())
