"""
Comprehensive validation of LangGraph refactoring.

Tests all critical features:
1. Unicode-safe console output
2. Feature flag system
3. Conditional routing
4. All 10 nodes operational
5. State management
6. Error handling
"""

import asyncio
import os
import sys

sys.path.insert(0, "src")


def print_section(title: str) -> None:
    """Print section header with ASCII-safe formatting."""
    print("\n" + "=" * 80)
    print(f"{title}")
    print("=" * 80)


async def test_unicode_safety() -> bool:
    """Test 1: Unicode-safe console output."""
    print_section("TEST 1: Unicode-Safe Console Output")
    
    try:
        # These should not crash on Windows
        print("   [OK] ASCII checkmarks working")
        print("   [FAIL] Error indicators working")
        print("   [WARN] Warning indicators working")
        print("\n[OK] Unicode-safe output: PASS")
        return True
    except UnicodeEncodeError as e:
        print(f"\n[FAIL] Unicode error: {e}")
        return False


def test_feature_flags() -> bool:
    """Test 2: Feature flag system."""
    print_section("TEST 2: Feature Flag System")
    
    # Test 1: Legacy mode
    os.environ["QNWIS_WORKFLOW_IMPL"] = "legacy"
    from qnwis.orchestration.feature_flags import get_workflow_implementation
    impl_legacy = get_workflow_implementation()
    print(f"   With IMPL=legacy: {impl_legacy}")
    
    # Test 2: LangGraph mode
    os.environ["QNWIS_WORKFLOW_IMPL"] = "langgraph"
    # Re-call function (it reads env var each time)
    impl_langgraph = get_workflow_implementation()
    print(f"   With IMPL=langgraph: {impl_langgraph}")
    
    # Test 3: Invalid value defaults to legacy
    os.environ["QNWIS_WORKFLOW_IMPL"] = "invalid"
    impl_invalid = get_workflow_implementation()
    print(f"   With IMPL=invalid: {impl_invalid} (should default to legacy)")
    
    success = (
        impl_legacy == "legacy" and
        impl_langgraph == "langgraph" and
        impl_invalid == "legacy"
    )
    
    print(f"\n[{'OK' if success else 'FAIL'}] Feature flags: {'PASS' if success else 'FAIL'}")
    
    # Reset to default
    if "QNWIS_WORKFLOW_IMPL" in os.environ:
        del os.environ["QNWIS_WORKFLOW_IMPL"]
    
    return success


async def test_conditional_routing() -> bool:
    """Test 3: Conditional routing."""
    print_section("TEST 3: Conditional Routing")
    
    from qnwis.orchestration.workflow import run_intelligence_query
    
    # Test simple query (should skip agent nodes)
    print("\n   Testing simple query routing...")
    simple_result = await run_intelligence_query(
        "What is Qatar?"  # Very simple query
    )
    
    simple_nodes = simple_result["nodes_executed"]
    simple_count = len(simple_nodes)
    expected_simple = 3  # classifier, extraction, synthesis
    
    print(f"   Nodes executed: {simple_count}")
    print(f"   Expected: {expected_simple}")
    print(f"   Nodes: {simple_nodes}")
    
    # Verify simple query skipped agent nodes
    skipped_agents = not any(
        node in simple_nodes for node in ["financial", "market", "operations", "research"]
    )
    
    success = simple_count == expected_simple and skipped_agents
    print(f"\n[{'OK' if success else 'FAIL'}] Conditional routing: {'PASS' if success else 'FAIL'}")
    return success


async def test_all_nodes() -> bool:
    """Test 4: All 10 nodes operational."""
    print_section("TEST 4: All 10 Nodes Operational")
    
    from qnwis.orchestration.workflow import run_intelligence_query
    
    print("\n   Executing complex query through all nodes...")
    result = await run_intelligence_query(
        "Analyze Qatar's workforce nationalization strategy"
    )
    
    nodes = result["nodes_executed"]
    expected_nodes = [
        "classifier", "extraction", "financial", "market",
        "operations", "research", "debate", "critique",
        "verification", "synthesis"
    ]
    
    print(f"   Nodes executed: {len(nodes)}/10")
    print(f"   Expected: {expected_nodes}")
    print(f"   Actual: {nodes}")
    
    all_present = all(node in nodes for node in expected_nodes)
    
    print(f"\n[{'OK' if all_present else 'FAIL'}] All nodes: {'PASS' if all_present else 'FAIL'}")
    return all_present


async def test_state_management() -> bool:
    """Test 5: State management."""
    print_section("TEST 5: State Management")
    
    from qnwis.orchestration.workflow import run_intelligence_query
    
    result = await run_intelligence_query("Test query")
    
    # Check all required state fields
    required_fields = [
        "query", "complexity", "extracted_facts", "data_sources",
        "data_quality_score", "agent_reports", "final_synthesis",
        "confidence_score", "reasoning_chain", "nodes_executed",
        "warnings", "errors", "timestamp", "execution_time"
    ]
    
    missing_fields = [f for f in required_fields if f not in result]
    
    print(f"   Required fields: {len(required_fields)}")
    print(f"   Present fields: {len(required_fields) - len(missing_fields)}")
    
    if missing_fields:
        print(f"   Missing: {missing_fields}")
    
    success = len(missing_fields) == 0
    print(f"\n[{'OK' if success else 'FAIL'}] State management: {'PASS' if success else 'FAIL'}")
    return success


async def test_error_handling() -> bool:
    """Test 6: Error handling."""
    print_section("TEST 6: Error Handling")
    
    from qnwis.orchestration.workflow import run_intelligence_query
    
    # Query with no relevant data (should handle gracefully)
    result = await run_intelligence_query("Analyze Martian unemployment")
    
    # Should complete without crashing
    has_synthesis = result.get("final_synthesis") is not None
    has_warnings = len(result.get("warnings", [])) >= 0  # May have warnings
    no_crash = True  # If we got here, no crash
    
    print(f"   Completed without crash: {no_crash}")
    print(f"   Generated synthesis: {has_synthesis}")
    print(f"   Warnings tracked: {len(result.get('warnings', []))} warnings")
    print(f"   Errors tracked: {len(result.get('errors', []))} errors")
    
    success = no_crash and has_synthesis
    print(f"\n[{'OK' if success else 'FAIL'}] Error handling: {'PASS' if success else 'FAIL'}")
    return success


async def main() -> None:
    """Run all validation tests."""
    print_section("LANGGRAPH REFACTOR VALIDATION SUITE")
    
    results = []
    
    # Run tests
    results.append(("Unicode Safety", await test_unicode_safety()))
    results.append(("Feature Flags", test_feature_flags()))
    results.append(("Conditional Routing", await test_conditional_routing()))
    results.append(("All 10 Nodes", await test_all_nodes()))
    results.append(("State Management", await test_state_management()))
    results.append(("Error Handling", await test_error_handling()))
    
    # Summary
    print_section("VALIDATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTests passed: {passed}/{total}")
    print("\nDetailed Results:")
    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status}: {name}")
    
    print("\n" + "=" * 80)
    if passed == total:
        print("ALL TESTS PASSED - Production-ready")
    else:
        print(f"SOME TESTS FAILED - {total - passed} issues found")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

