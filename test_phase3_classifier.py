"""
Quick test for Phase 3: Classifier routing logic only

Tests routing decision without running full workflow.
"""

from src.qnwis.classification.classifier import Classifier

def test_routing():
    """Test classifier routing decisions"""
    classifier = Classifier()

    test_cases = [
        # (question, expected_route)
        ("What was Qatar's unemployment rate in 2023?", "time_machine"),
        ("What were the historical trends?", "time_machine"),
        ("Show me past YoY changes", "time_machine"),

        ("What will unemployment be next year?", "predictor"),
        ("Forecast the retention rate", "predictor"),
        ("Predict future Qatarization levels", "predictor"),

        ("What if Qatarization increases by 10%?", "scenario"),
        ("Simulate a scenario where retention improves", "scenario"),
        ("How would the economy change if wages doubled?", "scenario"),

        ("Analyze Qatar's labour market", None),
        ("What is the current employment rate?", None),
        ("Compare Qatar to GCC countries", None),
    ]

    print("="*80)
    print("PHASE 3: CLASSIFIER ROUTING TESTS")
    print("="*80)

    passed = 0
    total = len(test_cases)

    for question, expected in test_cases:
        classification = classifier.classify_text(question)
        actual = classification.get("route_to")

        status = "PASS" if actual == expected else "FAIL"
        symbol = "[PASS]" if actual == expected else "[FAIL]"

        print(f"\n{symbol} {status}")
        print(f"  Question: {question}")
        print(f"  Expected: {expected}")
        print(f"  Actual:   {actual}")

        if actual == expected:
            passed += 1

    print("\n" + "="*80)
    print(f"RESULTS: {passed}/{total} passed ({passed/total*100:.0f}%)")
    print("="*80)

    if passed == total:
        print("\nAll routing tests PASSED! ✓")
        return True
    else:
        print(f"\n{total - passed} tests FAILED")
        return False


if __name__ == "__main__":
    success = test_routing()
    exit(0 if success else 1)
