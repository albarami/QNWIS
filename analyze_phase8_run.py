#!/usr/bin/env python3
"""Analyze Phase 8 Test 1 results to diagnose timeout"""
import json
from datetime import datetime

# Load test results
with open('phase8_test1_results.json', 'r') as f:
    results = json.load(f)

print("="*60)
print("PHASE 8 TEST 1 TIMEOUT DIAGNOSIS")
print("="*60)

print("\n📊 BASIC METRICS:")
print(f"Total agents invoked: {len(results['agents_invoked'])}")
print(f"Agent list: {', '.join(results['agents_invoked'])}")
print(f"Total debate turns: {results['debate_turns_count']}")
print(f"Errors: {len(results['errors'])}")

print("\n🔍 DEBATE TURN BREAKDOWN:")
for i, turn in enumerate(results['debate_turns_sample'], 1):
    print(f"\nTurn {i}:")
    print(f"  Agent: {turn['agent']}")
    print(f"  Type: {turn['type']}")
    print(f"  Preview: {turn['preview'][:150]}...")

print("\n❌ ERRORS:")
for i, error in enumerate(results['errors'], 1):
    print(f"{i}. {error}")

print("\n🎯 DIAGNOSIS:")
print(f"✓ MicroEconomist invoked: {'MicroEconomist' in results['agents_invoked']}")
print(f"✓ MacroEconomist invoked: {'MacroEconomist' in results['agents_invoked']}")
print(f"✓ Debate occurred: {results['debate_turns_count'] > 0}")

# Test duration estimate
print("\n⏱️  TIMING ANALYSIS:")
print("Test started: 08:49:18")
print("Test completed: 09:19:20")
print("Total duration: ~30 minutes")
print(f"Debate turns captured: {results['debate_turns_count']}")
print(f"Average time per turn: ~{30*60 / max(results['debate_turns_count'], 1):.1f} seconds")

print("\n🚨 ROOT CAUSE:")
if results['debate_turns_count'] > 30:
    print("❌ TOO MANY DEBATE TURNS")
    print(f"   Expected: 10-20 turns for simple query")
    print(f"   Actual: {results['debate_turns_count']} turns")
    print(f"   System configured for MAX_TURNS_TOTAL = 125")
    print("   → This caused 30-minute runtime")

print("\n💡 REQUIRED FIXES:")
print("1. Reduce MAX_TURNS_TOTAL from 125 to 25")
print("2. Reduce MAX_TURNS_PER_PHASE proportionally")
print("3. Add circuit breaker for early termination")
print("4. Optimize convergence detection")

print("\n" + "="*60)
