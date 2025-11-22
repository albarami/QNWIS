"""Test classifier patterns."""

import sys
sys.path.insert(0, "src")

from qnwis.orchestration.nodes.classifier import classify_query_node

test_queries = [
    ("What is Qatar's current GDP?", "simple"),
    ("What is unemployment rate?", "simple"),
    ("Show me latest data", "simple"),
    ("What are Qatar's employment trends?", "medium"),
    ("How is Qatar performing economically?", "medium"),
    ("Should Qatar invest in agriculture?", "complex"),
    ("Urgent: unemployment crisis", "critical"),
]

print("=" * 80)
print("CLASSIFIER PATTERN TESTING")
print("=" * 80)

for query, expected in test_queries:
    state = {
        "query": query,
        "reasoning_chain": [],
        "nodes_executed": [],
    }
    
    result = classify_query_node(state)
    actual = result["complexity"]
    status = "[OK]" if actual == expected else "[FAIL]"
    
    print(f"\n{status} Query: \"{query}\"")
    print(f"     Expected: {expected}, Actual: {actual}")

print("\n" + "=" * 80)
print("CLASSIFIER TEST COMPLETE")
print("=" * 80)

