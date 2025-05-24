import time

import pytest

from swagcli.plugins.rate_limiter import RateLimiter


def test_rate_limiter_creation():
    limiter = RateLimiter(requests_per_second=2)
    assert limiter.requests_per_second == 2
    assert len(limiter.requests) == 0


def test_rate_limiter_on_request_waits(monkeypatch):
    limiter = RateLimiter(requests_per_second=1)
    # Add a request to simulate a recent call
    limiter.requests.append(time.time())
    # Patch time.sleep to track if it is called
    called = {}

    def fake_sleep(secs):
        called["slept"] = secs

    monkeypatch.setattr(time, "sleep", fake_sleep)
    # Should sleep since a request was just made
    limiter.on_request("GET", "http://test", None, None)
    assert "slept" in called
    assert called["slept"] >= 0


def test_rate_limiter_on_request_no_wait(monkeypatch):
    limiter = RateLimiter(requests_per_second=1)
    # Patch time.sleep to fail if called
    monkeypatch.setattr(time, "sleep", lambda secs: pytest.fail("Should not sleep"))
    # Should not sleep since no requests yet
    limiter.on_request("GET", "http://test", None, None)
    assert len(limiter.requests) == 1


def test_plugin_metadata():
    limiter = RateLimiter()
    assert limiter.name == "rate_limiter"
    assert limiter.description == "Rate limits API requests"
    assert limiter.version == "1.0.0"
    assert limiter.author == "SwagCli Team"
