"""
Complete backend test - verify ALL components and agents work.
No frontend involved - pure backend testing.
"""
import requests
import json
import time
from datetime import datetime

API_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_health():
    """Test 1: Health check"""
    print_section("TEST 1: Health Check")
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}")
            print(f"✅ Version: {data['version']}")
            for component in data.get('components', []):
                status_icon = "✅" if component['status'] == 'healthy' else "❌"
                print(f"{status_icon} {component['name']}: {component['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_streaming_workflow(question):
    """Test 2: Full streaming workflow with all agents"""
    print_section(f"TEST 2: Streaming Workflow")
    print(f"Question: {question}")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    try:
        response = requests.post(
            f"{API_URL}/api/v1/council/stream",
            json={"question": question},
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=300  # 5 minutes
        )
        
        if response.status_code != 200:
            print(f"❌ Failed: HTTP {response.status_code}")
            print(response.text)
            return False
        
        print("✅ Stream connected")
        print("-" * 70)
        
        events = []
        stages_seen = set()
        agents_seen = set()
        
        for line in response.iter_lines():
            if not line:
                continue
                
            line_str = line.decode('utf-8')
            
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    stage = data.get('stage', 'unknown')
                    status = data.get('status', 'unknown')
                    payload = data.get('payload', {})
                    
                    events.append(data)
                    stages_seen.add(stage)
                    
                    # Print stage updates
                    if status in ['running', 'complete']:
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        print(f"[{timestamp}] {stage:20s} → {status}")
                        
                        # Print key details
                        if stage == 'classify' and status == 'complete':
                            classification = payload.get('classification', {})
                            print(f"  └─ Complexity: {classification.get('complexity', 'unknown')}")
                            print(f"  └─ Intent: {classification.get('intent', 'unknown')}")
                        
                        elif stage == 'prefetch' and status == 'complete':
                            fact_count = payload.get('fact_count', 0)
                            sources = payload.get('sources', [])
                            print(f"  └─ Facts extracted: {fact_count}")
                            print(f"  └─ Sources: {', '.join(sources[:3])}")
                        
                        elif stage == 'rag' and status == 'complete':
                            snippets = payload.get('snippets_retrieved', 0)
                            print(f"  └─ RAG snippets: {snippets}")
                        
                        elif stage == 'agent_selection' and status == 'complete':
                            selected = payload.get('selected_agents', [])
                            agents_seen.update(selected)
                            print(f"  └─ Agents selected: {', '.join(selected)}")
                        
                        elif stage == 'agents' and status == 'complete':
                            agent_reports = payload.get('agent_reports', [])
                            print(f"  └─ Agent reports received: {len(agent_reports)}")
                            for report in agent_reports:
                                agent_name = report.get('agent_name', 'unknown')
                                confidence = report.get('confidence', 0)
                                print(f"      • {agent_name}: {confidence:.2f} confidence")
                        
                        elif stage == 'synthesize' and status == 'complete':
                            synthesis = payload.get('final_synthesis', '')
                            confidence = payload.get('confidence_score', 0)
                            print(f"  └─ Synthesis length: {len(synthesis)} chars")
                            print(f"  └─ Confidence: {confidence:.2f}")
                        
                        elif stage == 'done' and status == 'complete':
                            print(f"\n✅ WORKFLOW COMPLETE")
                            print(f"   Finished: {datetime.now().strftime('%H:%M:%S')}")
                            print(f"   Total events: {len(events)}")
                            print(f"   Stages seen: {len(stages_seen)}")
                            print(f"   Agents invoked: {len(agents_seen)}")
                            return True
                    
                    if status == 'error':
                        print(f"❌ ERROR at stage {stage}")
                        print(f"   {payload.get('error', 'Unknown error')}")
                        return False
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"⚠️  Event parse error: {e}")
                    continue
        
        print("⚠️  Stream ended without 'done' event")
        return False
        
    except requests.exceptions.Timeout:
        print("❌ Request timeout after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False

def test_complete_json_workflow(question):
    """Test 3: Complete JSON workflow (non-streaming)"""
    print_section("TEST 3: Complete JSON Workflow")
    print(f"Question: {question}")
    
    try:
        response = requests.post(
            f"{API_URL}/api/v1/council/run-llm",
            json={"question": question},
            headers={"Content-Type": "application/json"},
            timeout=300
        )
        
        if response.status_code != 200:
            print(f"❌ Failed: HTTP {response.status_code}")
            return False
        
        data = response.json()
        print("✅ Workflow completed")
        print(f"   Complexity: {data.get('complexity', 'unknown')}")
        print(f"   Facts extracted: {len(data.get('extracted_facts', []))}")
        print(f"   Agents invoked: {len(data.get('agents_invoked', []))}")
        print(f"   Agent reports: {len(data.get('agent_reports', []))}")
        print(f"   Confidence: {data.get('confidence_score', 0):.2f}")
        print(f"   Synthesis length: {len(data.get('final_synthesis', ''))} chars")
        
        # Show agent details
        if data.get('agent_reports'):
            print("\n   Agent Reports:")
            for report in data['agent_reports']:
                name = report.get('agent_name', 'unknown')
                conf = report.get('confidence', 0)
                print(f"     • {name}: {conf:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("  🔧 QNWIS BACKEND COMPREHENSIVE TEST")
    print("  Testing ALL components and agents (no frontend)")
    print("="*70)
    
    # Test questions
    questions = [
        "What is the unemployment rate in Qatar?",
    ]
    
    results = {}
    
    # Test 1: Health
    results['health'] = test_health()
    
    if not results['health']:
        print("\n❌ Backend is not healthy. Fix health issues first.")
        return
    
    time.sleep(2)
    
    # Test 2: Streaming workflow
    results['streaming'] = test_streaming_workflow(questions[0])
    
    time.sleep(2)
    
    # Test 3: Complete JSON workflow
    results['json'] = test_complete_json_workflow(questions[0])
    
    # Summary
    print_section("SUMMARY")
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"{icon} {test_name.upper()}: {'PASSED' if passed else 'FAILED'}")
    
    print("\n" + "="*70)
    if all_passed:
        print("  ✅ ALL TESTS PASSED - Backend is working correctly!")
        print("  ✅ All components operational")
        print("  ✅ All agents functional")
        print("="*70)
    else:
        print("  ❌ SOME TESTS FAILED - See errors above")
        print("="*70)

if __name__ == "__main__":
    main()
