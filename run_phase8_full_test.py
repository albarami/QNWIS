#!/usr/bin/env python3
"""
Phase 8 Full Test - Capture COMPLETE debate content
Let it run for 20-30 minutes (appropriate for complex strategic query)
"""
import requests
import json
import time
from datetime import datetime

def run_food_security_test():
    """Run Food Security test with FULL content capture"""
    
    print("="*80)
    print("PHASE 8.1: FOOD SECURITY TEST - FULL RUN")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    print("Expected duration: 20-30 minutes for complex strategic query")
    print("This is APPROPRIATE for $15B investment decision")
    print("="*80)
    
    url = "http://127.0.0.1:8000/api/v1/council/stream"
    payload = {
        "question": "Should Qatar invest $15B in Food Valley project targeting 40% food self-sufficiency by 2030?",
        "provider": "anthropic"
    }
    
    # Collectors for full content
    all_events = []
    micro_content = []
    macro_content = []
    debate_turns = []
    synthesis_content = []
    errors = []
    
    try:
        print("\nSending request to backend...")
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=2400,  # 40 minute timeout (generous)
            stream=True
        )
        
        print("Receiving streaming response...")
        line_count = 0
        
        for line in response.iter_lines():
            if not line:
                continue
                
            line_count += 1
            if line_count % 10 == 0:
                print(f"  Received {line_count} events... (elapsed: {(datetime.now().timestamp() - start_time):.0f}s)")
            
            try:
                decoded = line.decode('utf-8')
                
                # Parse SSE format
                if decoded.startswith('data: '):
                    data_str = decoded[6:]  # Skip "data: "
                    data = json.loads(data_str)
                    all_events.append(data)
                    
                    stage = data.get('stage', '')
                    payload_data = data.get('payload', {})
                    
                    # Capture debate turns with FULL content
                    if stage == 'debate:turn':
                        agent = payload_data.get('agent', '')
                        turn_type = payload_data.get('type', '')
                        message = payload_data.get('message', '')  # FULL MESSAGE, not preview
                        
                        turn_data = {
                            'agent': agent,
                            'type': turn_type,
                            'message': message,
                            'timestamp': data.get('timestamp', '')
                        }
                        debate_turns.append(turn_data)
                        
                        # Separate Micro and Macro content
                        if agent == 'MicroEconomist':
                            micro_content.append(turn_data)
                        elif agent == 'MacroEconomist':
                            macro_content.append(turn_data)
                        
                        print(f"    → Debate turn {len(debate_turns)}: {agent} ({turn_type})")
                    
                    # Capture synthesis
                    elif 'synthesis' in stage.lower() or 'final' in stage.lower():
                        synthesis_content.append({
                            'stage': stage,
                            'content': payload_data,
                            'timestamp': data.get('timestamp', '')
                        })
                        print(f"    → Synthesis stage: {stage}")
                    
                    # Capture errors
                    elif 'error' in stage or data.get('status') == 'error':
                        error_msg = payload_data.get('error', data.get('message', 'Unknown error'))
                        errors.append(error_msg)
                        print(f"    ⚠️  Error: {error_msg[:100]}")
                        
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"    Warning: Failed to parse event: {e}")
                continue
        
        end_time = time.time()
        duration_min = (end_time - start_time) / 60
        
        print(f"\n{'='*80}")
        print(f"TEST COMPLETED")
        print(f"{'='*80}")
        print(f"Duration: {duration_min:.1f} minutes")
        print(f"Total events: {len(all_events)}")
        print(f"Debate turns: {len(debate_turns)}")
        print(f"MicroEconomist turns: {len(micro_content)}")
        print(f"MacroEconomist turns: {len(macro_content)}")
        print(f"Synthesis stages: {len(synthesis_content)}")
        print(f"Errors: {len(errors)}")
        
        # Save FULL results
        results = {
            'test_name': 'Food Security - Full Run',
            'start_time': datetime.fromtimestamp(start_time).isoformat(),
            'end_time': datetime.fromtimestamp(end_time).isoformat(),
            'duration_minutes': duration_min,
            'total_events': len(all_events),
            'debate_turns_count': len(debate_turns),
            'debate_turns': debate_turns,  # FULL content
            'micro_content': micro_content,
            'macro_content': macro_content,
            'synthesis_content': synthesis_content,
            'errors': errors
        }
        
        # Save to file
        with open('phase8_full_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Full results saved to: phase8_full_test_results.json")
        
        return results
        
    except requests.exceptions.Timeout:
        print(f"\n❌ Request timed out after 40 minutes")
        return {'error': 'timeout', 'partial_data': {'debate_turns': debate_turns}}
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

if __name__ == "__main__":
    start_time = time.time()
    results = run_food_security_test()
    
    if 'error' not in results:
        print(f"\n{'='*80}")
        print("ANALYZING DEBATE QUALITY")
        print(f"{'='*80}")
        
        # Check for Micro/Macro participation
        micro_turns = len(results.get('micro_content', []))
        macro_turns = len(results.get('macro_content', []))
        
        print(f"\n✓ MicroEconomist: {micro_turns} turns")
        print(f"✓ MacroEconomist: {macro_turns} turns")
        
        if micro_turns > 0 and macro_turns > 0:
            print(f"\n✅ BOTH AGENTS PARTICIPATED")
            
            # Show first statements
            if results.get('micro_content'):
                print(f"\n{'─'*80}")
                print("MICROECONOMIST OPENING (first 500 chars):")
                print(f"{'─'*80}")
                first_micro = results['micro_content'][0]['message'][:500]
                print(first_micro)
                print("...\n")
            
            if results.get('macro_content'):
                print(f"{'─'*80}")
                print("MACROECONOMIST OPENING (first 500 chars):")
                print(f"{'─'*80}")
                first_macro = results['macro_content'][0]['message'][:500]
                print(first_macro)
                print("...\n")
        else:
            print(f"\n❌ MISSING AGENT PARTICIPATION")
        
        # Check synthesis
        if results.get('synthesis_content'):
            print(f"\n✅ SYNTHESIS COMPLETED ({len(results['synthesis_content'])} stages)")
        else:
            print(f"\n⚠️  NO SYNTHESIS CAPTURED")
        
        print(f"\n{'='*80}")
        print(f"Phase 8.1 Status: {'✅ COMPLETE' if micro_turns > 0 and macro_turns > 0 else '❌ INCOMPLETE'}")
        print(f"{'='*80}")
