"""Test Qatar Open Data API integration."""

import pytest
from qnwis.data.deterministic.registry import QueryRegistry
from qnwis.data.deterministic.cache_access import execute_cached


def test_qatar_api_employees_query():
    """Test that we can execute a Qatar API query for employee data."""
    reg = QueryRegistry()
    reg.load_all()
    
    # Verify query is registered
    assert "q_employees_by_sector_nationality" in reg.all_ids()
    
    # Execute query with short TTL for testing
    result = execute_cached(
        "q_employees_by_sector_nationality",
        reg,
        ttl_s=60,
        invalidate=True,  # Force fresh fetch
    )
    
    # Verify result structure
    assert result.query_id == "q_employees_by_sector_nationality"
    assert result.provenance.source == "qatar_api"
    assert result.provenance.license == "Qatar Open Data Portal License (CC BY 4.0)"
    assert "number-of-employees-and-compensation" in result.provenance.dataset_id
    
    # Verify we got some data (API should return results)
    assert len(result.rows) > 0, "Expected at least one row from Qatar API"
    
    # Verify expected fields in first row
    if result.rows:
        first_row = result.rows[0].data
        # Check for typical fields in this dataset
        expected_fields = {"year", "main_economic_activity", "nationality", "value"}
        actual_fields = set(first_row.keys())
        assert expected_fields.issubset(actual_fields), (
            f"Missing expected fields. Expected: {expected_fields}, Got: {actual_fields}"
        )
    
    print(f"✓ Fetched {len(result.rows)} employee records from Qatar API")
    print(f"✓ Provenance: {result.provenance.dataset_id}")
    print(f"✓ License: {result.provenance.license}")


def test_qatar_api_training_query():
    """Test that we can execute a Qatar API query for training center data."""
    reg = QueryRegistry()
    reg.load_all()
    
    # Verify query is registered
    assert "q_training_center_trainees" in reg.all_ids()
    
    # Execute query
    result = execute_cached(
        "q_training_center_trainees",
        reg,
        ttl_s=60,
        invalidate=True,
    )
    
    # Verify result structure
    assert result.query_id == "q_training_center_trainees"
    assert result.provenance.source == "qatar_api"
    assert len(result.rows) > 0, "Expected training center data from Qatar API"
    
    print(f"✓ Fetched {len(result.rows)} training center records from Qatar API")


def test_qatar_api_caching():
    """Test that Qatar API responses are properly cached."""
    reg = QueryRegistry()
    reg.load_all()
    
    import time
    
    # First call - should hit API
    start = time.perf_counter()
    result1 = execute_cached(
        "q_employees_by_sector_nationality",
        reg,
        ttl_s=300,
        invalidate=True,
    )
    first_call_time = time.perf_counter() - start
    
    # Second call - should hit cache
    start = time.perf_counter()
    result2 = execute_cached(
        "q_employees_by_sector_nationality",
        reg,
        ttl_s=300,
        invalidate=False,
    )
    second_call_time = time.perf_counter() - start
    
    # Cache hit should be significantly faster
    assert second_call_time < first_call_time / 2, "Cache hit should be faster than API call"
    assert result1.rows == result2.rows, "Cached result should match original"
    
    print(f"✓ API call: {first_call_time*1000:.1f}ms, Cache hit: {second_call_time*1000:.1f}ms")


if __name__ == "__main__":
    print("Testing Qatar Open Data API Integration...\n")
    
    try:
        test_qatar_api_employees_query()
        print()
        test_qatar_api_training_query()
        print()
        test_qatar_api_caching()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
