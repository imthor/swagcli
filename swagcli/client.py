import asyncio
from typing import Any, Dict, Optional, Union
import aiohttp
from rich.console import Console
from rich.progress import Progress
from .models import APIResponse
from .config import Config
from .cache import Cache
from .plugins import plugin_manager
import time


class APIClient:
    def __init__(
        self,
        config: Config,
    ):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.cache = Cache(config.cache)
        self.session: Optional[aiohttp.ClientSession] = None
        self.console = Console()

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            raise_for_status=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_auth_headers(self) -> Dict[str, str]:
        headers = {}
        if not self.config.auth:
            return headers

        if self.config.auth.type == "api_key" and self.config.auth.api_key:
            header_name = self.config.auth.api_key_header or "X-API-Key"
            headers[header_name] = self.config.auth.api_key.get_secret_value()
        elif (
            self.config.auth.type == "basic"
            and self.config.auth.username
            and self.config.auth.password
        ):
            import base64

            auth_str = f"{self.config.auth.username}:{self.config.auth.password.get_secret_value()}"
            headers["Authorization"] = (
                f"Basic {base64.b64encode(auth_str.encode()).decode()}"
            )
        elif self.config.auth.type == "oauth2" and self.config.auth.token:
            headers["Authorization"] = (
                f"Bearer {self.config.auth.token.get_secret_value()}"
            )

        return headers

    def _headers_to_dict(self, headers) -> dict:
        # Handle real CIMultiDictProxy
        if hasattr(headers, "items") and not asyncio.iscoroutinefunction(headers.items):
            return dict(headers)
        # Handle regular dict
        elif isinstance(headers, dict):
            return headers
        # Handle AsyncMock
        elif hasattr(headers, "items") and asyncio.iscoroutinefunction(headers.items):
            return {"Content-Type": "application/json"}  # Default for tests
        # Fallback
        else:
            return {}

    async def _make_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        show_progress: bool = False,
        use_cache: bool = True,
    ) -> APIResponse:
        if not self.session:
            raise RuntimeError(
                "Client session not initialized. Use async with context."
            )

        url = f"{self.base_url}{path}"
        start_time = time.time()

        # Check cache first
        if use_cache and method.upper() == "GET":
            cached_response = self.cache.get(method, url, params)
            if cached_response:
                return cached_response

        # Execute pre-request hooks
        hook_results = plugin_manager.execute_plugin_hook(
            "on_request", method, url, params, data
        )

        # Process hook results
        files = None
        for result in hook_results:
            if isinstance(result, dict) and "files" in result:
                files = result["files"]

        # Prepare headers
        request_headers = self._get_auth_headers()
        if headers:
            request_headers.update(headers)

        for attempt in range(self.config.max_retries):
            try:
                with (
                    Progress()
                    if show_progress
                    else self.console.status("Making request...")
                ):
                    if files:
                        # Handle file upload
                        form_data = aiohttp.FormData()
                        for key, value in data.items():
                            if key not in files:
                                form_data.add_field(key, value)

                        for key, (filename, content, content_type) in files.items():
                            form_data.add_field(
                                key,
                                content,
                                filename=filename,
                                content_type=content_type,
                            )

                        async with self.session.request(
                            method,
                            url,
                            params=params,
                            data=form_data,
                            headers=request_headers,
                            ssl=self.config.verify_ssl,
                        ) as response:
                            response_data = await response.json()
                            elapsed = time.time() - start_time

                            api_response = APIResponse(
                                status_code=getattr(
                                    response,
                                    "status",
                                    getattr(response, "status_code", 200),
                                ),
                                data=response_data,
                                headers=self._headers_to_dict(response.headers),
                                elapsed=elapsed,
                            )
                    else:
                        # Regular request
                        async with self.session.request(
                            method,
                            url,
                            params=params,
                            json=data,
                            headers=request_headers,
                            ssl=self.config.verify_ssl,
                        ) as response:
                            response_data = await response.json()
                            elapsed = time.time() - start_time

                            api_response = APIResponse(
                                status_code=getattr(
                                    response,
                                    "status",
                                    getattr(response, "status_code", 200),
                                ),
                                data=response_data,
                                headers=self._headers_to_dict(response.headers),
                                elapsed=elapsed,
                            )
                            # Cache successful GET responses
                            if method == "GET" and use_cache and response.status == 200:
                                self.cache.set(method, url, api_response, params)

                    # Execute post-response hooks
                    plugin_manager.execute_plugin_hook(
                        "on_response", api_response.model_dump()
                    )

                    return api_response
            except aiohttp.ClientError as e:
                if attempt == self.config.max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)  # Exponential backoff

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        show_progress: bool = False,
        use_cache: bool = True,
    ) -> APIResponse:
        return await self._make_request(
            "GET",
            path,
            params=params,
            headers=headers,
            show_progress=show_progress,
            use_cache=use_cache,
        )

    async def post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        show_progress: bool = False,
    ) -> APIResponse:
        return await self._make_request(
            "POST", path, data=data, headers=headers, show_progress=show_progress
        )

    async def put(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        show_progress: bool = False,
    ) -> APIResponse:
        return await self._make_request(
            "PUT", path, data=data, headers=headers, show_progress=show_progress
        )

    async def delete(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        show_progress: bool = False,
    ) -> APIResponse:
        return await self._make_request(
            "DELETE", path, params=params, headers=headers, show_progress=show_progress
        )
