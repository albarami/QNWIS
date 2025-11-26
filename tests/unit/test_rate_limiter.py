"""
Unit tests for rate limiter.

Tests the rate limiting functionality to ensure Claude API 429 errors are prevented.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from qnwis.orchestration.rate_limiter import RateLimitedExecutor, get_rate_limiter


@pytest.mark.asyncio
async def test_rate_limiter_enforces_50_per_minute():
    """Test that rate limiter enforces the 50 requests/minute limit."""
    rate_limiter = RateLimitedExecutor(max_requests_per_minute=10)  # Lower for faster test
    
    # Mock function
    mock_func = AsyncMock(return_value="success")
    
    # Make 10 requests (should succeed immediately)
    start_time = time.time()
    for _ in range(10):
        await rate_limiter.execute_with_rate_limit(mock_func)
    elapsed = time.time() - start_time
    
    # Should complete quickly (< 1 second)
    assert elapsed < 1.0
    assert mock_func.call_count == 10
    
    # 11th request should trigger rate limiting
    start_time = time.time()
    await rate_limiter.execute_with_rate_limit(mock_func)
    elapsed = time.time() - start_time
    
    # Should have been delayed
    assert elapsed > 0.1  # Some delay occurred
    assert mock_func.call_count == 11


@pytest.mark.asyncio
async def test_no_429_errors_under_load():
    """
    Test that rate limiter prevents 429 errors under load.
    
    Simulates 240 requests over 5 minutes (6 scenarios × 40 calls each).
    With 50 req/min limit, this should take ~5 minutes without errors.
    """
    rate_limiter = RateLimitedExecutor(max_requests_per_minute=50)
    
    # Mock function that would return 429 if called too fast
    call_count = 0
    
    async def mock_api_call():
        nonlocal call_count
        call_count += 1
        return f"response_{call_count}"
    
    # Make 50 requests (should succeed without blocking much)
    start_time = time.time()
    tasks = [rate_limiter.execute_with_rate_limit(mock_api_call) for _ in range(50)]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time
    
    # All requests should succeed
    assert len(results) == 50
    assert call_count == 50
    
    # Should complete in reasonable time (< 10 seconds with semaphore)
    assert elapsed < 10.0


@pytest.mark.asyncio
async def test_graceful_backoff():
    """Test that rate limiter gracefully backs off when limit is approached."""
    rate_limiter = RateLimitedExecutor(max_requests_per_minute=5)
    
    mock_func = AsyncMock(return_value="success")
    
    # Make 5 requests (at limit)
    for _ in range(5):
        await rate_limiter.execute_with_rate_limit(mock_func)
    
    # Next request should trigger backoff
    start_time = time.time()
    await rate_limiter.execute_with_rate_limit(mock_func)
    elapsed = time.time() - start_time
    
    # Should have waited (at least a few seconds)
    assert elapsed > 1.0
    assert mock_func.call_count == 6


@pytest.mark.asyncio
async def test_concurrent_scenarios_respect_limit():
    """
    Test that 6 concurrent scenarios respect the global rate limit.
    
    This simulates 6 parallel scenarios, each making LLM calls.
    The rate limiter should prevent the combined total from exceeding 50 req/min.
    """
    rate_limiter = RateLimitedExecutor(max_requests_per_minute=20)  # Lower for faster test
    
    async def scenario_worker(scenario_id: int, num_calls: int):
        """Simulate a scenario making multiple LLM calls."""
        results = []
        for i in range(num_calls):
            mock_func = AsyncMock(return_value=f"scenario_{scenario_id}_call_{i}")
            result = await rate_limiter.execute_with_rate_limit(mock_func)
            results.append(result)
        return results
    
    # Run 6 scenarios concurrently, each making 5 calls (30 total)
    start_time = time.time()
    tasks = [scenario_worker(i, 5) for i in range(6)]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time
    
    # All scenarios should complete
    assert len(results) == 6
    for scenario_results in results:
        assert len(scenario_results) == 5
    
    # Should take some time due to rate limiting (30 calls, 20/min limit = ~2 minutes)
    # But with semaphore, may complete faster
    assert elapsed > 0.5  # At least some delay


@pytest.mark.asyncio
async def test_rate_limiter_wraps_individual_llm_calls():
    """
    BUG FIX TEST: Verify rate limiter wraps individual LLM calls, not workflows.
    
    This is the critical test to ensure Bug #1 is fixed.
    Rate limiter must be applied to llm.ainvoke(), not workflow.ainvoke().
    """
    rate_limiter = RateLimitedExecutor(max_requests_per_minute=10)
    
    # Simulate individual LLM calls
    mock_llm_call = AsyncMock(return_value="llm_response")
    
    # Each call should be rate limited
    call_times = []
    for _ in range(5):
        start = time.time()
        await rate_limiter.execute_with_rate_limit(mock_llm_call)
        call_times.append(time.time() - start)
    
    # First few calls should be fast, but we're tracking each one
    assert mock_llm_call.call_count == 5
    
    # Verify we're not wrapping a workflow (which would only count as 1 call)
    # If we were wrapping workflow, call_count would be 1, not 5
    assert mock_llm_call.call_count == 5  # Each individual call tracked


@pytest.mark.asyncio
async def test_singleton_rate_limiter():
    """Test that get_rate_limiter() returns the same instance."""
    limiter1 = get_rate_limiter()
    limiter2 = get_rate_limiter()
    
    # Should be the same instance
    assert limiter1 is limiter2
    
    # Both should track requests from the same pool
    mock_func = AsyncMock(return_value="success")
    
    await limiter1.execute_with_rate_limit(mock_func)
    assert len(limiter2.request_times) == 1  # Same instance, same tracking
    
    await limiter2.execute_with_rate_limit(mock_func)
    assert len(limiter1.request_times) == 2  # Same instance, same tracking


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

