import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
import diskcache
from .config import CacheConfig
from .models import APIResponse


class Cache:
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache = diskcache.Cache(config.storage_path)
        self.config.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> str:
        key_parts = [method, url]
        if params:
            key_parts.append(json.dumps(params, sort_keys=True))
        if data:
            key_parts.append(json.dumps(data, sort_keys=True))
        return hashlib.sha256("|".join(key_parts).encode()).hexdigest()

    def get(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> Optional[APIResponse]:
        if not self.config.enabled:
            return None

        cache_key = self._get_cache_key(method, url, params, data)
        cached_data = self.cache.get(cache_key)

        if cached_data is None:
            return None

        timestamp, data = cached_data
        if time.time() - timestamp > self.config.ttl:
            self.cache.delete(cache_key)
            return None

        # Reconstruct APIResponse from dict
        if isinstance(data, dict) and all(
            k in data for k in ("status_code", "data", "headers", "elapsed")
        ):
            return APIResponse(**data)
        return None

    def set(
        self,
        method: str,
        url: str,
        api_response: APIResponse,
        params: Optional[Dict] = None,
        request_data: Optional[Dict] = None,
    ) -> None:
        if not self.config.enabled:
            return

        cache_key = self._get_cache_key(method, url, params, request_data)
        # Store as dict using model_dump() for Pydantic v2 compatibility
        self.cache.set(
            cache_key, (time.time(), api_response.model_dump()), expire=self.config.ttl
        )

    def clear(self) -> None:
        self.cache.clear()

    def __del__(self):
        self.cache.close()
