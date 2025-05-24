import time
from pathlib import Path
import pytest
from swagcli.cache import Cache
from swagcli.config import CacheConfig
from swagcli.models import APIResponse


@pytest.fixture
def cache_config():
    return CacheConfig(
        enabled=True,
        ttl=1,  # 1 second TTL for testing
        max_size=1000,
        storage_path=Path("/tmp/swagcli_test_cache"),
    )


@pytest.fixture
def cache(cache_config):
    return Cache(cache_config)


def test_cache_set_get(cache):
    method = "GET"
    url = "https://api.example.com/test"
    api_response = APIResponse(
        status_code=200,
        data={"key": "value"},
        headers={"Content-Type": "application/json"},
        elapsed=0.1,
    )

    # Test setting and getting data
    cache.set(method, url, api_response)
    cached_data = cache.get(method, url)
    assert cached_data is not None
    assert cached_data.status_code == api_response.status_code
    assert cached_data.data == api_response.data
    assert cached_data.headers == api_response.headers
    assert cached_data.elapsed == api_response.elapsed


def test_cache_expiration(cache):
    method = "GET"
    url = "https://api.example.com/test"
    api_response = APIResponse(
        status_code=200,
        data={"key": "value"},
        headers={"Content-Type": "application/json"},
        elapsed=0.1,
    )

    # Set data and wait for expiration
    cache.set(method, url, api_response)
    time.sleep(1.1)  # Wait for TTL to expire

    # Data should be expired
    cached_data = cache.get(method, url)
    assert cached_data is None


def test_cache_different_keys(cache):
    method = "GET"
    url = "https://api.example.com/test"
    api_response1 = APIResponse(
        status_code=200,
        data={"key": "value1"},
        headers={"Content-Type": "application/json"},
        elapsed=0.1,
    )
    api_response2 = APIResponse(
        status_code=200,
        data={"key": "value2"},
        headers={"Content-Type": "application/json"},
        elapsed=0.1,
    )

    # Test different parameters
    cache.set(method, url, api_response1, params={"param1": "value1"})
    cache.set(method, url, api_response2, params={"param2": "value2"})

    cached1 = cache.get(method, url, params={"param1": "value1"})
    cached2 = cache.get(method, url, params={"param2": "value2"})

    assert cached1 is not None
    assert cached1.data == api_response1.data
    assert cached2 is not None
    assert cached2.data == api_response2.data


def test_cache_clear(cache):
    method = "GET"
    url = "https://api.example.com/test"
    api_response = APIResponse(
        status_code=200,
        data={"key": "value"},
        headers={"Content-Type": "application/json"},
        elapsed=0.1,
    )

    cache.set(method, url, api_response)
    cache.clear()

    assert cache.get(method, url) is None


def test_cache_disabled(cache_config):
    cache_config.enabled = False
    cache = Cache(cache_config)

    method = "GET"
    url = "https://api.example.com/test"
    api_response = APIResponse(
        status_code=200,
        data={"key": "value"},
        headers={"Content-Type": "application/json"},
        elapsed=0.1,
    )

    cache.set(method, url, api_response)
    assert cache.get(method, url) is None
