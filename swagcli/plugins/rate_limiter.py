import time
from collections import deque
from typing import Any, Dict, Optional
from ..plugins import Plugin

plugin = Plugin(
    name="rate_limiter",
    description="Rate limits API requests",
    version="1.0.0",
    author="SwagCli Team",
)


class RateLimiter:
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()

    def can_make_request(self) -> bool:
        now = time.time()

        # Remove old requests
        while self.requests and now - self.requests[0] > self.time_window:
            self.requests.popleft()

        return len(self.requests) < self.max_requests

    def add_request(self) -> None:
        self.requests.append(time.time())

    def get_wait_time(self) -> float:
        if not self.requests:
            return 0

        now = time.time()
        oldest_request = self.requests[0]
        return max(0, self.time_window - (now - oldest_request))


# Create a global rate limiter instance
rate_limiter = RateLimiter()


def on_request(
    method: str, url: str, params: Dict[str, Any] = None, data: Dict[str, Any] = None
) -> Optional[Dict[str, Any]]:
    """Hook called before making a request to enforce rate limits."""
    if not rate_limiter.can_make_request():
        wait_time = rate_limiter.get_wait_time()
        time.sleep(wait_time)

    rate_limiter.add_request()
    return None
