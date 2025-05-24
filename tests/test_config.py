import json
from pathlib import Path
import pytest
from swagcli.config import Config, AuthConfig, CacheConfig


def test_config_creation():
    config = Config(base_url="https://api.example.com")
    assert config.base_url == "https://api.example.com"
    assert config.timeout == 30
    assert config.max_retries == 3
    assert config.verify_ssl is True


def test_auth_config():
    auth = AuthConfig(type="api_key", api_key="secret123", api_key_header="X-API-Key")
    assert auth.type == "api_key"
    assert auth.api_key.get_secret_value() == "secret123"
    assert auth.api_key_header == "X-API-Key"


def test_cache_config():
    cache = CacheConfig(
        enabled=True, ttl=600, max_size=2000, storage_path=Path("/tmp/cache")
    )
    assert cache.enabled is True
    assert cache.ttl == 600
    assert cache.max_size == 2000
    assert cache.storage_path == Path("/tmp/cache")


def test_config_save_load(tmp_path):
    config_path = tmp_path / "config.json"
    config = Config(
        base_url="https://api.example.com",
        auth=AuthConfig(type="api_key", api_key="secret123"),
        cache=CacheConfig(storage_path=tmp_path / "cache"),
    )

    config.save(config_path)
    loaded_config = Config.load(config_path)

    assert loaded_config.base_url == config.base_url
    assert loaded_config.auth.type == config.auth.type
    assert (
        loaded_config.auth.api_key.get_secret_value()
        == config.auth.api_key.get_secret_value()
    )
    assert loaded_config.cache.storage_path == config.cache.storage_path
