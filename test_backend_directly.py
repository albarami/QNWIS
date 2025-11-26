"""
Test backend SSE stream directly to verify all stages execute properly.
Shows real-time events from the backend.
"""

import requests
import json
from datetime import datetime

def test_backend_stream():
    """Test the backend /api/v1/council/stream endpoint directly."""
    
    url = "http://localhost:8000/api/v1/council/stream"
    
    payload = {
        "question": "What are the unemployment trends in Qatar?",
        "provider": "anthropic"
    }
    
    print("=" * 80)
    print(f"Testing Backend SSE Stream at {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 80)
    print(f"\nURL: {url}")
    print(f"Question: {payload['question']}")
    print(f"Provider: {payload['provider']}")
    print("\n" + "=" * 80)
    print("STREAMING EVENTS (Real-time from backend):")
    print("=" * 80 + "\n")
    
    stage_count = {}
    agent_events = []
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            },
            stream=True,
            timeout=300  # 5 minutes
        )
        
        if response.status_code != 200:
            print(f"❌ ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        print(f"✅ Connected to backend (HTTP {response.status_code})\n")
        
        event_count = 0
        current_event_type = None
        
        for line in response.iter_lines():
            if not line:
                continue
                
            line = line.decode('utf-8')
            
            # Parse SSE format
            if line.startswith('event:'):
                current_event_type = line.replace('event:', '').strip()
            elif line.startswith('data:'):
                event_count += 1
                data_str = line.replace('data:', '').strip()
                
                try:
                    data = json.loads(data_str)
                    stage = data.get('stage', '?')
                    status = data.get('status', '?')
                    latency = data.get('latency_ms')
                    
                    # Track stages
                    if stage not in stage_count:
                        stage_count[stage] = 0
                    stage_count[stage] += 1
                    
                    # Track agent events
                    if stage.startswith('agent:'):
                        agent_name = stage.replace('agent:', '')
                        agent_events.append({
                            'name': agent_name,
                            'status': status,
                            'latency': latency
                        })
                    
                    # Print event details
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    
                    if stage == 'heartbeat':
                        print(f"[{timestamp}] 💓 Heartbeat")
                    elif stage.startswith('agent:'):
                        agent_name = stage.replace('agent:', '')
                        if status == 'running':
                            print(f"[{timestamp}] 🔄 Agent: {agent_name} - RUNNING")
                        elif status == 'complete':
                            print(f"[{timestamp}] ✅ Agent: {agent_name} - COMPLETE (latency: {latency}ms)")
                        elif status == 'error':
                            error = data.get('payload', {}).get('error', 'Unknown error')
                            print(f"[{timestamp}] ❌ Agent: {agent_name} - ERROR: {error}")
                    elif status == 'running':
                        print(f"[{timestamp}] 🚀 Stage: {stage.upper()} - STARTING")
                    elif status == 'complete':
                        lat_str = f" ({latency}ms)" if latency else ""
                        print(f"[{timestamp}] ✅ Stage: {stage.upper()} - COMPLETE{lat_str}")
                        
                        # Show payload summary for key stages
                        payload_data = data.get('payload', {})
                        if stage == 'classify' and payload_data:
                            complexity = payload_data.get('complexity', '?')
                            print(f"             └─ Complexity: {complexity}")
                        elif stage == 'prefetch' and payload_data:
                            facts = payload_data.get('extracted_facts', [])
                            print(f"             └─ Extracted facts: {len(facts)}")
                        elif stage == 'rag' and payload_data:
                            docs = payload_data.get('documents', [])
                            print(f"             └─ RAG documents: {len(docs)}")
                        elif stage == 'agent_selection' and payload_data:
                            agents = payload_data.get('selected_agents', [])
                            print(f"             └─ Selected agents: {agents}")
                        elif stage == 'agents' and payload_data:
                            agent_list = payload_data.get('agents', [])
                            print(f"             └─ Agents to execute: {len(agent_list)} → {agent_list}")
                    elif status == 'error':
                        error = data.get('payload', {}).get('error', 'Unknown error')
                        print(f"[{timestamp}] ❌ Stage: {stage.upper()} - ERROR: {error}")
                    
                    # Check for done
                    if stage == 'done':
                        print(f"\n[{timestamp}] 🎉 WORKFLOW COMPLETE!")
                        break
                        
                except json.JSONDecodeError:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Could not parse: {data_str[:100]}")
        
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"\nTotal events received: {event_count}")
        print(f"\nStages executed:")
        for stage, count in sorted(stage_count.items()):
            if not stage.startswith('agent:'):
                print(f"  {stage}: {count} events")
        
        # Agent summary
        unique_agents = set()
        completed_agents = []
        failed_agents = []
        
        for agent in agent_events:
            unique_agents.add(agent['name'])
            if agent['status'] == 'complete':
                completed_agents.append(agent['name'])
            elif agent['status'] == 'error':
                failed_agents.append(agent['name'])
        
        print(f"\nAgent execution:")
        print(f"  Unique agents: {len(unique_agents)}")
        print(f"  Completed: {len(completed_agents)}")
        print(f"  Failed: {len(failed_agents)}")
        
        if len(unique_agents) > 0:
            print(f"\n  Agent list: {sorted(unique_agents)}")
        
        if failed_agents:
            print(f"\n  ⚠️  Failed agents: {failed_agents}")
        
        print("\n" + "=" * 80)
        
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timed out after 5 minutes")
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ ERROR: Could not connect to backend")
        print(f"   Is the backend running on http://localhost:8000?")
        print(f"   Error: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_backend_stream()
