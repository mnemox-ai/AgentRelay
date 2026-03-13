"""In-memory sliding-window rate limiter."""

from __future__ import annotations

import time
from collections import deque


class RateLimiter:
    """Per-client sliding-window rate limiter backed by a plain dict.

    Each client_id maps to a deque of request timestamps. On each
    ``check()`` call, expired entries are pruned and the request is
    allowed only if the remaining count is below ``max_requests``.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = {}

    def check(self, client_id: str) -> bool:
        """Return ``True`` if the request is allowed, ``False`` if rate-limited."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        bucket = self._buckets.get(client_id)
        if bucket is None:
            bucket = deque()
            self._buckets[client_id] = bucket

        # Prune expired timestamps
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            return False

        bucket.append(now)
        return True

    def retry_after(self, client_id: str) -> int:
        """Seconds until the oldest entry in the window expires."""
        bucket = self._buckets.get(client_id)
        if not bucket:
            return 0
        elapsed = time.monotonic() - bucket[0]
        remaining = self.window_seconds - elapsed
        return max(1, int(remaining) + 1)
