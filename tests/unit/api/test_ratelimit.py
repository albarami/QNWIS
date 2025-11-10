from qnwis.security import Principal
from qnwis.security.ratelimit import RateLimiter
from qnwis.utils.clock import Clock


class DummyClock(Clock):
    def __init__(self):
        self.perf = 0.0
        super().__init__(now=lambda: None, perf_counter=lambda: self.perf)

    def advance(self, seconds: float) -> None:
        self.perf += seconds


def test_rate_limiter_allows_until_burst():
    limiter = RateLimiter(rps=2, burst=2, daily=5, redis_url=None)
    principal = Principal(subject="svc", roles=("analyst",), ratelimit_id="svc")
    assert limiter.consume(principal).allowed
    assert limiter.consume(principal).allowed
    result = limiter.consume(principal)
    assert not result.allowed
    assert result.reason == "rps_limit_exceeded"


def test_rate_limiter_daily_limit():
    limiter = RateLimiter(rps=100, burst=100, daily=2, redis_url=None)
    principal = Principal(subject="svc", roles=("analyst",), ratelimit_id="svc")
    assert limiter.consume(principal).allowed
    assert limiter.consume(principal).allowed
    result = limiter.consume(principal)
    assert not result.allowed
    assert result.reason == "daily_limit_exceeded"


def test_rate_limiter_refills_tokens():
    clock = DummyClock()
    limiter = RateLimiter(rps=1, burst=1, daily=5, redis_url=None, clock=clock)
    principal = Principal(subject="svc", roles=("analyst",), ratelimit_id="svc")
    assert limiter.consume(principal).allowed
    denied = limiter.consume(principal)
    assert not denied.allowed
    clock.advance(1.5)
    refreshed = limiter.consume(principal)
    assert refreshed.allowed
