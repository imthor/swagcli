import time
from collections import deque
from typing import Any, Dict, List, Optional

from .base import Plugin


class RateLimiter(Plugin):
    def __init__(self, requests_per_second: float = 1.0) -> None:
        super().__init__(
            name="rate_limiter",
            description="Rate limits API requests",
            version="1.0.0",
            author="SwagCli Team",
        )
        self.requests_per_second = requests_per_second
        self.requests: deque[float] = deque()
        self.min_interval = 1.0 / requests_per_second

    def _clean_old_requests(self) -> None:
        """Remove requests older than 1 second."""
        now = time.time()
        while self.requests and now - self.requests[0] >= 1.0:
            self.requests.popleft()

    def _get_wait_time(self) -> float:
        """Calculate how long to wait before making the next request."""
        self._clean_old_requests()
        if len(self.requests) < self.requests_per_second:
            return 0.0

        return max(0.0, self.requests[0] + 1.0 - time.time())

    def on_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        data: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Rate limit requests."""
        wait_time = self._get_wait_time()
        if wait_time > 0:
            time.sleep(wait_time)

        self.requests.append(time.time())
        return None

    def on_response(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """No action needed on response."""
        return None
