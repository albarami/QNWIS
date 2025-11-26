#!/usr/bin/env python3
"""
Extract FULL debate content from the partial Phase 8 run.
We need to see the ACTUAL agent arguments, not just metadata.
"""
import json
import re

print("="*80)
print("EXTRACTING FULL DEBATE CONTENT - PHASE 8 TEST 1")
print("="*80)

# Load partial test results
with open('phase8_test1_results.json', 'r') as f:
    results = json.load(f)

print(f"\n📊 METADATA:")
print(f"Agents invoked: {len(results['agents_invoked'])}")
print(f"Debate turns: {results['debate_turns_count']}")
print(f"Errors: {len(results['errors'])}")

print(f"\n{'='*80}")
print("AGENT OPENING STATEMENTS (First 500 chars each)")
print(f"{'='*80}")

# Extract opening statements for Micro and Macro
for turn in results['debate_turns_sample']:
    agent = turn['agent']
    turn_type = turn['type']
    preview = turn['preview']
    
    if agent in ['MicroEconomist', 'MacroEconomist'] and turn_type == 'opening_statement':
        print(f"\n{'─'*80}")
        print(f"🎯 {agent.upper()} - OPENING STATEMENT")
        print(f"{'─'*80}")
        print(preview)
        print("...")

print(f"\n{'='*80}")
print("DEBATE QUALITY ASSESSMENT")
print(f"{'='*80}")

# Check for debate quality indicators
micro_preview = ""
macro_preview = ""

for turn in results['debate_turns_sample']:
    if turn['agent'] == 'MicroEconomist' and turn['type'] == 'opening_statement':
        micro_preview = turn['preview'].lower()
    elif turn['agent'] == 'MacroEconomist' and turn['type'] == 'opening_statement':
        macro_preview = turn['preview'].lower()

# Micro indicators (cost/efficiency focus)
micro_indicators = {
    "cost": "cost" in micro_preview,
    "benefit": "benefit" in micro_preview or "roi" in micro_preview,
    "efficiency": "efficiency" in micro_preview or "efficient" in micro_preview,
    "npv": "npv" in micro_preview,
    "resource": "resource" in micro_preview or "allocation" in micro_preview
}

# Macro indicators (strategy/security focus)
macro_indicators = {
    "strategic": "strategic" in macro_preview,
    "security": "security" in macro_preview,
    "national": "national" in macro_preview,
    "resilience": "resilience" in macro_preview or "resilient" in macro_preview,
    "viability": "viability" in macro_preview or "viable" in macro_preview
}

print("\n✅ MICROECONOMIST ANALYSIS:")
for indicator, present in micro_indicators.items():
    status = "✓" if present else "✗"
    print(f"  {status} Mentions {indicator}")

print("\n✅ MACROECONOMIST ANALYSIS:")
for indicator, present in macro_indicators.items():
    status = "✓" if present else "✗"
    print(f"  {status} Mentions {indicator}")

# Overall assessment
micro_score = sum(micro_indicators.values())
macro_score = sum(macro_indicators.values())

print(f"\n{'='*80}")
print("VERDICT")
print(f"{'='*80}")
print(f"MicroEconomist focus score: {micro_score}/5 indicators")
print(f"MacroEconomist focus score: {macro_score}/5 indicators")

if micro_score >= 3 and macro_score >= 3:
    print("\n✅ DEBATE QUALITY: PASS")
    print("   Both agents demonstrate their distinct analytical perspectives.")
elif micro_score >= 2 or macro_score >= 2:
    print("\n⚠️  DEBATE QUALITY: PARTIAL")
    print("   Some perspective distinction visible, but could be stronger.")
else:
    print("\n❌ DEBATE QUALITY: FAIL")
    print("   Agents not showing distinct micro/macro perspectives.")

print(f"\n{'='*80}")
print("ISSUES DETECTED")
print(f"{'='*80}")
for i, error in enumerate(results['errors'], 1):
    if 'workflow_timeout' in error.lower():
        print(f"{i}. ⚠️  WORKFLOW TIMEOUT - Synthesis incomplete")
        print("   → FIX: Add emergency synthesis for timeout scenarios")
    elif 'sentencetransformer' in error.lower() or 'meta tensor' in error.lower():
        print(f"{i}. ⚠️  CONVERGENCE DETECTION ERROR - Using fallback")
        print("   → FIX: Already handled with fallback logic")
    else:
        print(f"{i}. {error}")
