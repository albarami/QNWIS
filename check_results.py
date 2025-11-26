import json

with open('phase8_full_test_results.json', 'r') as f:
    data = json.load(f)

print(f"Total events: {len(data.get('events', []))}")
print(f"Debate turns: {len(data.get('debate_turns', []))}")
print(f"Synthesis content entries: {len(data.get('synthesis_content', []))}")
print(f"Errors: {len(data.get('errors', []))}")
print()

# Check for workflow_timeout error
errors = data.get('errors', [])
has_timeout = any('workflow_timeout' in str(e) for e in errors)
print(f"Has workflow_timeout error: {has_timeout}")
print()

# Show synthesis content
synth = data.get('synthesis_content', [])
if synth:
    print("Synthesis content:")
    for s in synth:
        print(f"  Stage: {s.get('stage')}")
        print(f"  Content: {str(s.get('content'))[:200]}...")
print()

# Check last few events
events = data.get('events', [])
if events:
    print(f"Last 5 event stages:")
    for e in events[-5:]:
        print(f"  - {e.get('stage', 'unknown')}: {e.get('status', 'unknown')}")
