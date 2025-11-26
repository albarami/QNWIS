#!/usr/bin/env python3
"""Test adaptive debate complexity detection"""

# Simulate the detection logic
def detect_question_complexity(question: str) -> str:
    """Detect question complexity."""
    question_lower = question.lower()
    
    # SIMPLE: Factual queries
    simple_indicators = [
        "what is", "what are", "how many", "when did", "who is",
        "unemployment rate", "latest data", "current status"
    ]
    if any(indicator in question_lower for indicator in simple_indicators):
        if len(question.split()) < 15:
            return "simple"
    
    # COMPLEX: Strategic decisions
    complex_indicators = [
        "$", "billion", "investment", "should qatar", "strategic",
        "policy", "food security", "self-sufficiency", "by 20",
        "long-term", "national", "economic development"
    ]
    complex_count = sum(1 for indicator in complex_indicators if indicator in question_lower)
    if complex_count >= 3:
        return "complex"
    
    return "standard"

# Test cases
test_cases = [
    {
        "question": "Should Qatar invest $15B in Food Valley project targeting 40% food self-sufficiency by 2030?",
        "expected": "complex",
        "reasoning": "Investment decision with dollar amount, strategic indicators"
    },
    {
        "question": "What are Qatar's hospitality sector labor market trends and workforce challenges?",
        "expected": "standard",
        "reasoning": "Analytical query, no strategic decision"
    },
    {
        "question": "What is Qatar's unemployment rate?",
        "expected": "simple",
        "reasoning": "Simple factual query, short question"
    },
    {
        "question": "Should Qatar develop long-term national economic development policy for food security?",
        "expected": "complex",
        "reasoning": "Strategic policy with multiple complex indicators"
    }
]

print("="*80)
print("ADAPTIVE DEBATE COMPLEXITY DETECTION TEST")
print("="*80)

configs = {
    "simple": {"turns": 15, "duration": "2-3 min"},
    "standard": {"turns": 40, "duration": "8-12 min"},
    "complex": {"turns": 125, "duration": "20-30 min"}
}

for i, test in enumerate(test_cases, 1):
    question = test["question"]
    expected = test["expected"]
    reasoning = test["reasoning"]
    
    detected = detect_question_complexity(question)
    status = "✅ PASS" if detected == expected else "❌ FAIL"
    
    config = configs[detected]
    
    print(f"\n{'='*80}")
    print(f"TEST {i}: {status}")
    print(f"{'='*80}")
    print(f"Question: {question}")
    print(f"\nExpected: {expected.upper()}")
    print(f"Detected: {detected.upper()}")
    print(f"Reasoning: {reasoning}")
    print(f"\nDebate Config:")
    print(f"  - Max turns: {config['turns']}")
    print(f"  - Duration: {config['duration']}")
    
    # Count indicators
    question_lower = question.lower()
    complex_indicators = [
        "$", "billion", "investment", "should qatar", "strategic",
        "policy", "food security", "self-sufficiency", "by 20",
        "long-term", "national", "economic development"
    ]
    found_indicators = [ind for ind in complex_indicators if ind in question_lower]
    if found_indicators:
        print(f"  - Complex indicators found: {', '.join(found_indicators)} (count: {len(found_indicators)})")

print(f"\n{'='*80}")
print("TEST SUMMARY")
print(f"{'='*80}")
passed = sum(1 for test in test_cases if detect_question_complexity(test["question"]) == test["expected"])
print(f"Passed: {passed}/{len(test_cases)}")
print(f"Status: {'✅ ALL TESTS PASSED' if passed == len(test_cases) else '❌ SOME TESTS FAILED'}")
