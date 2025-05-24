import pytest
from unittest.mock import AsyncMock, patch
from swagcli.client import APIClient
from swagcli.config import Config, AuthConfig
from swagcli.models import APIResponse
import tempfile
import shutil
import os
import aiohttp


@pytest.fixture
def config(tmp_path):
    # Use a unique cache directory for each test
    cache_dir = tmp_path / "cache"
    return Config(
        base_url="https://api.example.com",
        auth=AuthConfig(
            type="api_key", api_key="secret123", api_key_header="X-API-Key"
        ),
        cache={"enabled": True, "ttl": 60, "max_size": 100, "storage_path": cache_dir},
    )


@pytest.fixture
async def client(config):
    async with APIClient(config) as client:
        yield client


@pytest.mark.asyncio
async def test_auth_headers(config):
    client = APIClient(config)
    headers = client._get_auth_headers()
    assert headers["X-API-Key"] == "secret123"


@pytest.mark.asyncio
async def test_basic_auth():
    config = Config(
        base_url="https://api.example.com",
        auth=AuthConfig(type="basic", username="user", password="pass"),
    )
    client = APIClient(config)
    headers = client._get_auth_headers()
    assert headers["Authorization"].startswith("Basic ")


@pytest.mark.asyncio
async def test_oauth2_auth():
    config = Config(
        base_url="https://api.example.com",
        auth=AuthConfig(type="oauth2", token="token123"),
    )
    client = APIClient(config)
    headers = client._get_auth_headers()
    assert headers["Authorization"] == "Bearer token123"


@pytest.mark.asyncio
async def test_get_request(client):
    mock_response = AsyncMock()
    mock_response.__aenter__.return_value.status = 200
    mock_response.__aenter__.return_value.json = AsyncMock(
        return_value={"data": "test"}
    )
    mock_response.__aenter__.return_value.headers = {"Content-Type": "application/json"}

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        response = await client.get("/test")
        assert response.status_code == 200
        assert response.data == {"data": "test"}


@pytest.mark.asyncio
async def test_cached_request(client):
    # Clear cache before test
    client.cache.clear()
    mock_response = AsyncMock()
    mock_response.__aenter__.return_value.status = 200
    mock_response.__aenter__.return_value.json = AsyncMock(
        return_value={"data": "test"}
    )
    mock_response.__aenter__.return_value.headers = {"Content-Type": "application/json"}

    with patch(
        "aiohttp.ClientSession.request", return_value=mock_response
    ) as mock_request:
        # First request should make an HTTP call
        response = await client.get("/test")
        assert response.status_code == 200
        assert response.data == {"data": "test"}
        assert mock_request.call_count == 1

        # Second request should use cache (no new HTTP call)
        response = await client.get("/test")
        assert response.status_code == 200
        assert response.data == {"data": "test"}
        assert mock_request.call_count == 1  # Still 1, no new request made


@pytest.mark.asyncio
async def test_retry_on_error(client):
    # Clear cache before test
    client.cache.clear()
    # Create a mock response that acts as an async context manager
    mock_response = AsyncMock()
    mock_response.__aenter__.return_value.status = 500
    mock_response.__aenter__.return_value.json = AsyncMock(
        return_value={"error": "Internal Server Error"}
    )
    mock_response.__aenter__.return_value.headers = {"Content-Type": "application/json"}

    # First call raises aiohttp.ClientError, second call returns mock_response
    with patch(
        "aiohttp.ClientSession.request",
        side_effect=[aiohttp.ClientError("Connection error"), mock_response],
    ):
        # The client should retry and not raise, but return the second response
        response = await client.get("/test")
        assert response.status_code == 500
        assert response.data == {"error": "Internal Server Error"}


@pytest.mark.asyncio
async def test_post_request(client):
    mock_response = AsyncMock()
    mock_response.__aenter__.return_value.status = 201
    mock_response.__aenter__.return_value.json = AsyncMock(return_value={"id": 1})
    mock_response.__aenter__.return_value.headers = {"Content-Type": "application/json"}

    with patch("aiohttp.ClientSession.request", return_value=mock_response):
        response = await client.post("/test", data={"name": "test"})
        assert response.status_code == 201
        assert response.data == {"id": 1}
