"""Rate limiting middleware for the API."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiting middleware.

    Tracks requests per client (by IP or API key) and enforces
    a maximum number of requests within a sliding time window.
    """

    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        exclude_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = set(exclude_paths or [])
        # client_id -> list of timestamps
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def _get_client_id(self, request: Request) -> str:
        """Get a unique identifier for the client."""
        # Prefer API key header, fall back to IP
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{api_key}"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    def _is_excluded(self, path: str) -> bool:
        """Check if the path is excluded from rate limiting."""
        for excluded in self.exclude_paths:
            if path.startswith(excluded):
                return True
        return False

    def _clean_old_requests(self, client_id: str, now: float) -> None:
        """Remove requests outside the current window."""
        self._requests[client_id] = [
            t for t in self._requests[client_id]
            if now - t < self.window_seconds
        ]

    def _is_rate_limited(self, client_id: str) -> Tuple[bool, Dict[str, int]]:
        """Check if the client is rate limited. Returns (is_limited, headers)."""
        now = time.time()
        self._clean_old_requests(client_id, now)
        count = len(self._requests[client_id])
        remaining = max(0, self.max_requests - count - 1)
        reset_at = int(now + self.window_seconds)

        headers = {
            "X-RateLimit-Limit": str(self.max_requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_at),
        }

        if count >= self.max_requests:
            return True, headers
        return False, headers

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request through the middleware."""
        if self._is_excluded(request.url.path):
            return await call_next(request)

        client_id = self._get_client_id(request)
        is_limited, headers = self._is_rate_limited(client_id)

        if is_limited:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Try again later.",
                    "status_code": 429,
                },
                headers={**headers, "Retry-After": str(self.window_seconds)},
            )

        # Record this request
        self._requests[client_id].append(time.time())

        response = await call_next(request)
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
        return response
