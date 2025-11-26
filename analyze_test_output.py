import json

with open('phase8_full_test_results.json', 'r') as f:
    data = json.load(f)

# Summary
print("="*80)
print("PHASE 8 TEST ANALYSIS")
print("="*80)
print(f"Duration: {data.get('duration_minutes', 0):.1f} minutes")
print(f"Total events captured: {data.get('total_events', 0)}")
print(f"Debate turns: {data.get('debate_turns_count', 0)}")
print()

# Debate participation
debate_turns = data.get('debate_turns', [])
micro_turns = [t for t in debate_turns if t.get('agent') == 'MicroEconomist']
macro_turns = [t for t in debate_turns if t.get('agent') == 'MacroEconomist']
print(f"MicroEconomist turns: {len(micro_turns)}")
print(f"MacroEconomist turns: {len(macro_turns)}")
print()

# Synthesis
synth = data.get('synthesis_content', [])
print(f"Synthesis stages captured: {len(synth)}")
if synth:
    for s in synth:
        print(f"  - Stage: {s.get('stage')}")
        content = s.get('content', {})
        if isinstance(content, dict):
            msg = content.get('message', '')
            print(f"    Message: {msg}")
print()

# Errors
errors = data.get('errors', [])
print(f"Errors: {len(errors)}")
has_timeout = any('workflow_timeout' in str(e) for e in errors)
print(f"Has workflow_timeout error: {has_timeout}")
if errors:
    print("Error types:")
    for e in errors:
        print(f"  - {str(e)[:80]}...")
print()

# Success criteria
print("="*80)
print("SUCCESS CRITERIA CHECK")
print("="*80)
criteria = {
    "Duration 30-35 min": 30 <= data.get('duration_minutes', 0) <= 35,
    "Debate turns 42-48": 42 <= data.get('debate_turns_count', 0) <= 48,
    "Synthesis stages >= 1": len(synth) >= 1,
    "No workflow_timeout": not has_timeout,
    "MicroEconomist participated": len(micro_turns) > 0,
    "MacroEconomist participated": len(macro_turns) > 0,
}

for criterion, passed in criteria.items():
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {criterion}")

print()
if all(criteria.values()):
    print("🎉 ALL SUCCESS CRITERIA MET!")
else:
    print("⚠️ SOME CRITERIA NOT MET")
