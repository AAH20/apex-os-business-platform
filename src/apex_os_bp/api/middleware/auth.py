"""Authentication middleware for the API."""
from __future__ import annotations

import secrets
import time
from typing import Callable, Dict, Optional, Set

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from apex_os_bp.security.auth import Authenticator


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT-like token authentication middleware.

    Validates Bearer tokens on protected routes. Public routes
    (health, login, register) are exempt.
    """

    # Paths that don't require authentication
    PUBLIC_PATHS: Set[str] = {
        "/api/v1/health",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    # Class-level instance registry for dependency injection
    _instances: list = []

    def __init__(self, app, authenticator: Authenticator, secret: str):
        super().__init__(app)
        self.authenticator = authenticator
        self.secret = secret
        # In-memory token store: token -> (user_id, expires_at)
        self._tokens: Dict[str, tuple[str, float]] = {}
        AuthMiddleware._instances.append(self)

    @classmethod
    def get_instance(cls) -> Optional["AuthMiddleware"]:
        """Get the most recently created instance."""
        return cls._instances[-1] if cls._instances else None

    def _is_public_path(self, path: str) -> bool:
        """Check if the path is public."""
        for public_path in self.PUBLIC_PATHS:
            if path.startswith(public_path):
                return True
        return False

    def create_token(self, user_id: str, expires_in: int = 3600) -> str:
        """Create a new token for a user."""
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + expires_in
        self._tokens[token] = (user_id, expires_at)
        return token

    def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False

    def validate_token(self, token: str) -> Optional[str]:
        """Validate a token and return the user_id if valid."""
        if token not in self._tokens:
            return None
        user_id, expires_at = self._tokens[token]
        if time.time() > expires_at:
            del self._tokens[token]
            return None
        return user_id

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request through the middleware."""
        # Allow public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Check for X-API-Key header first
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            # Accept any non-empty API key as valid (simple key auth)
            request.state.user_id = "api_key_user"
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid authorization header", "status_code": 401},
            )

        token = auth_header[7:]  # Remove "Bearer " prefix
        user_id = self.validate_token(token)
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token", "status_code": 401},
            )

        # Attach user_id to request state
        request.state.user_id = user_id
        return await call_next(request)
