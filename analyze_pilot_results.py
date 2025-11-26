"""
Re-analyze pilot results with NEW quality gates (no time evaluation)
User priority: accuracy and depth, not speed
"""
import json

# Load results
with open('pilot_evidence/PILOT_SUMMARY.json', 'r') as f:
    data = json.load(f)

# Expected facts per query (from WEEK_3_PILOT_TEST.md)
expected_facts = {
    1: 80,   # Economic
    2: 100,  # Energy
    3: 60,   # Tourism
    4: 80,   # Food
    5: 60,   # Healthcare
    6: 80,   # Digital
    7: 80,   # Manufacturing
    8: 120,  # Workforce
    9: 80,   # Infrastructure
    10: 120  # Strategic
}

print("="*80)
print("PILOT RESULTS RE-ANALYSIS - NEW QUALITY GATES")
print("Quality Gates: FACTS + CONFIDENCE only (time not evaluated)")
print("User priority: Accuracy and depth > speed")
print("="*80)

successful = []
failed = []

for result in data["results"]:
    qid = result["id"]
    domain = result["domain"]
    facts = result["facts"]
    confidence = result["confidence"]
    time = result["time"]
    
    # NEW quality gate criteria
    meets_facts = facts >= expected_facts[qid]
    meets_confidence = confidence >= 0.5
    
    # Quality gate result
    passed = meets_facts and meets_confidence
    
    status = "✅ PASS" if passed else "❌ FAIL"
    
    print(f"\nQuery {qid}: {domain}")
    print(f"  Facts: {facts} (expected: >={expected_facts[qid]}) {'✅' if meets_facts else '❌'}")
    print(f"  Confidence: {confidence:.2f} (target: >=0.5) {'✅' if meets_confidence else '❌'}")
    print(f"  Time: {time:.1f}s (not evaluated)")
    print(f"  Sources: {result['sources']}")
    print(f"  {status}")
    
    if passed:
        successful.append(result)
    else:
        failed.append(result)

# Summary
print("\n" + "="*80)
print("SUMMARY WITH NEW QUALITY GATES")
print("="*80)

if successful:
    avg_facts = sum(r["facts"] for r in successful) / len(successful)
    avg_confidence = sum(r["confidence"] for r in successful) / len(successful)
    avg_time = sum(r["time"] for r in successful) / len(successful)
else:
    avg_facts = avg_confidence = avg_time = 0

print(f"\nQueries PASSED: {len(successful)}/10")
print(f"Average facts (passed queries): {avg_facts:.0f}")
print(f"Average confidence (passed queries): {avg_confidence:.2f}")
print(f"Average time: {avg_time:.1f}s (not evaluated)")

print(f"\n{'='*80}")
print("QUALITY GATE EVALUATION")
print(f"{'='*80}")
all_passed = len(successful) == 10
facts_ok = avg_facts >= 80 if successful else False
confidence_ok = avg_confidence >= 0.5 if successful else False

print(f"All 10 queries passed: {'✅ PASS' if all_passed else '❌ FAIL'} ({len(successful)}/10)")
print(f"Average facts >=80: {'✅ PASS' if facts_ok else '❌ FAIL'} ({avg_facts:.0f})")
print(f"Average confidence >=0.5: {'✅ PASS' if confidence_ok else '❌ FAIL'} ({avg_confidence:.2f})")

print(f"\n{'='*80}")
if all_passed and facts_ok and confidence_ok:
    print("✅ GO DECISION: Proceed to full 50-query suite")
else:
    print("⚠️  CONDITIONAL GO: Strong results but some queries need improvement")
    print(f"\nStrong queries ({len(successful)} PASSED):")
    for r in successful:
        print(f"  - Query {r['id']}: {r['domain']} (facts={r['facts']}, conf={r['confidence']:.2f})")
    
    print(f"\nWeak queries ({len(failed)} FAILED):")
    for r in failed:
        print(f"  - Query {r['id']}: {r['domain']} (facts={r['facts']}, conf={r['confidence']:.2f})")
        
print("="*80)
