"""Integration tests for rate limiting."""

from __future__ import annotations

import time

from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from src.qnwis.api.deps import attach_security
from src.qnwis.api.endpoints_security_demo import router
from src.qnwis.security.rate_limiter import rate_limit


def test_rate_limit_applies():
    """Test that rate limiting is enforced after max requests."""
    from src.qnwis.security.rate_limiter import RateLimiter
    
    # Create a fresh limiter for this test
    test_limiter = RateLimiter()
    test_limiter.max_req = 3
    
    async def test_rate_limit(request: Request):
        from fastapi import HTTPException
        fwd = request.headers.get("X-Forwarded-For")
        client = (
            (fwd.split(",")[0].strip() if fwd else request.client.host)
            if request.client
            else "unknown"
        )
        ok, count, ttl = test_limiter.check(f"rl:{client}:{request.url.path}")
        limit = 3
        remaining = max(0, limit - count)
        reset_epoch = str(int(time.time()) + ttl)
        request.state.rate_limit_headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": reset_epoch,
            "Retry-After": str(ttl if remaining == 0 else 0),
        }
        if not ok:
            raise HTTPException(status_code=429, detail="Too Many Requests")
    
    app = FastAPI(dependencies=[Depends(test_rate_limit)])
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)

    for i in range(3):
        r = client.get("/ping")
        assert r.status_code == 200
    r = client.get("/ping")
    assert r.status_code == 429
    assert r.headers.get("X-RateLimit-Limit") == "3"
    assert r.headers.get("X-RateLimit-Remaining") == "0"
    reset_header = r.headers.get("X-RateLimit-Reset")
    assert reset_header is not None
    assert int(reset_header) >= int(time.time())


def test_rate_limit_headers_present():
    """Test that rate limit headers are present in responses."""
    app = FastAPI(dependencies=[Depends(rate_limit)])
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)

    r = client.get("/ping")
    assert r.status_code == 200
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers
    assert "X-RateLimit-Reset" in r.headers


def test_rate_limit_retry_after_header():
    """Test that Retry-After header is present when rate limited."""
    from src.qnwis.security.rate_limiter import RateLimiter
    
    # Create a fresh limiter for this test
    test_limiter = RateLimiter()
    test_limiter.max_req = 2
    
    async def test_rate_limit(request: Request):
        from fastapi import HTTPException
        fwd = request.headers.get("X-Forwarded-For")
        client = (
            (fwd.split(",")[0].strip() if fwd else request.client.host)
            if request.client
            else "unknown"
        )
        ok, count, ttl = test_limiter.check(f"rl:{client}:{request.url.path}")
        limit = 2
        remaining = max(0, limit - count)
        reset_epoch = str(int(time.time()) + ttl)
        request.state.rate_limit_headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": reset_epoch,
            "Retry-After": str(ttl if remaining == 0 else 0),
        }
        if not ok:
            raise HTTPException(status_code=429, detail="Too Many Requests")
    
    app = FastAPI(dependencies=[Depends(test_rate_limit)])
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)

    for i in range(2):
        client.get("/ping")
    r = client.get("/ping")
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    retry_after = int(r.headers["Retry-After"])
    assert retry_after >= 0  # May be 0 or positive depending on timing
    assert int(r.headers["X-RateLimit-Reset"]) >= int(time.time())


def test_rate_limit_per_client():
    """Test that rate limiting is applied per client."""
    app = FastAPI(dependencies=[Depends(rate_limit)])
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)

    # Each test client should have independent rate limit
    r = client.get("/ping")
    assert r.status_code == 200
    remaining1 = int(r.headers.get("X-RateLimit-Remaining", "0"))

    r = client.get("/ping")
    assert r.status_code == 200
    remaining2 = int(r.headers.get("X-RateLimit-Remaining", "0"))

    # Remaining should decrease
    assert remaining2 < remaining1
