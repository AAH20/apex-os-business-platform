"""API Gateway for APEX-OS Business Platform."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Route:
    """API route."""
    path: str
    method: str
    handler: str
    metadata: Dict = field(default_factory=dict)


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: Dict[str, List[float]] = {}

    def allow(self, client_id: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        if client_id not in self._clients:
            self._clients[client_id] = []

        self._clients[client_id] = [
            t for t in self._clients[client_id]
            if now - t < self.window_seconds
        ]

        if len(self._clients[client_id]) >= self.max_requests:
            return False

        self._clients[client_id].append(now)
        return True


class APIGateway:
    """API Gateway with routing and rate limiting."""

    def __init__(self):
        self._routes: Dict[str, Route] = {}
        self._rate_limiter: Optional[RateLimiter] = None

    def add_route(self, route: Route) -> None:
        """Add route to gateway."""
        key = f"{route.method}:{route.path}"
        self._routes[key] = route

    def get_route(self, path: str, method: str) -> Optional[Route]:
        """Get route by path and method."""
        key = f"{method}:{path}"
        return self._routes.get(key)

    def set_rate_limiter(self, limiter: RateLimiter) -> None:
        """Set rate limiter."""
        self._rate_limiter = limiter

    @property
    def routes(self) -> List[Route]:
        """Get all routes."""
        return list(self._routes.values())
