"""Final end-to-end test"""
import requests
import time

url = "http://localhost:8000/api/v1/council/stream"
question = "What are Qatar's current unemployment statistics?"

print("Starting test...")
print(f"URL: {url}")
print(f"Question: {question}")
print()

response = requests.post(
    url,
    json={
        "question": question,
        "provider": "anthropic"
    },
    stream=True,
    timeout=1800
)

print(f"Response status: {response.status_code}")
if response.status_code != 200:
    print(f"Error: {response.text}")
    exit(1)

print("Stream started. Watching events...")
print()

debate_started = False
debate_turns = 0
for line in response.iter_lines():
    if not line:
        continue
    line = line.decode('utf-8')
    if line.startswith('data: '):
        import json
        try:
            event = json.loads(line[6:])
            stage = event.get('stage', '')
            status = event.get('status', '')
            
            if stage == 'debate' and status == 'running':
                print("DEBATE STAGE STARTED!")
                debate_started = True
            
            if stage == 'debate:turn':
                debate_turns += 1
                turn = event.get('payload', {})
                print(f"Turn {debate_turns}: {turn.get('agent')} - {turn.get('type')}")
                
            if stage == 'done':
                print()
                print(f"WORKFLOW COMPLETE!")
                print(f"Debate started: {debate_started}")
                print(f"Debate turns: {debate_turns}")
                break
        except:
            pass

print("Test complete.")
