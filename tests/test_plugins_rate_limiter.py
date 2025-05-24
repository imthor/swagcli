import time
import pytest
from swagcli.plugins.rate_limiter import plugin, RateLimiter, on_request


def test_rate_limiter_creation():
    limiter = RateLimiter(max_requests=2, time_window=1)
    assert limiter.max_requests == 2
    assert limiter.time_window == 1
    assert len(limiter.requests) == 0


def test_rate_limiter_requests():
    limiter = RateLimiter(max_requests=2, time_window=1)

    # First request should be allowed
    assert limiter.can_make_request() is True
    limiter.add_request()

    # Second request should be allowed
    assert limiter.can_make_request() is True
    limiter.add_request()

    # Third request should be blocked
    assert limiter.can_make_request() is False


def test_rate_limiter_time_window():
    limiter = RateLimiter(max_requests=1, time_window=1)

    # First request
    assert limiter.can_make_request() is True
    limiter.add_request()

    # Should be blocked
    assert limiter.can_make_request() is False

    # Wait for time window to expire
    time.sleep(1.1)

    # Should be allowed again
    assert limiter.can_make_request() is True


def test_rate_limiter_wait_time():
    limiter = RateLimiter(max_requests=1, time_window=1)

    # Add a request
    limiter.add_request()

    # Check wait time
    wait_time = limiter.get_wait_time()
    assert 0 < wait_time <= 1


def test_plugin_metadata():
    assert plugin.name == "rate_limiter"
    assert plugin.description == "Rate limits API requests"
    assert plugin.version == "1.0.0"
    assert plugin.author == "SwagCli Team"
