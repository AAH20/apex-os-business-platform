"""REST API client for APEX-OS Business Platform.

A reusable HTTP client with retry logic, authentication, request/response
interceptors, and connection pooling. Uses only the standard library
(urllib) so there are no external dependencies.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class HTTPMethod(str, Enum):
    """HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthType(str, Enum):
    """Authentication types."""

    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"


@dataclass
class RESTResponse:
    """Standardized REST response."""

    status_code: int
    body: Union[str, Dict[str, Any], bytes]
    headers: Dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    url: str = ""

    @property
    def ok(self) -> bool:
        """Check if response is successful (2xx)."""
        return 200 <= self.status_code < 300

    @property
    def json(self) -> Optional[Dict[str, Any]]:
        """Parse body as JSON."""
        if isinstance(self.body, dict):
            return self.body
        if isinstance(self.body, str):
            try:
                return json.loads(self.body)
            except (json.JSONDecodeError, ValueError):
                return None
        return None

    @property
    def text(self) -> str:
        """Get body as text."""
        if isinstance(self.body, str):
            return self.body
        if isinstance(self.body, bytes):
            return self.body.decode("utf-8")
        return json.dumps(self.body)


@dataclass
class RESTRequest:
    """REST request specification."""

    method: HTTPMethod
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    body: Optional[Union[str, Dict[str, Any], bytes]] = None
    timeout_seconds: float = 30.0
    verify_ssl: bool = True

    def full_url(self) -> str:
        """Build full URL with query parameters."""
        if not self.params:
            return self.url
        separator = "&" if "?" in self.url else "?"
        query = urllib.parse.urlencode(self.params)
        return f"{self.url}{separator}{query}"

    def encoded_body(self) -> Optional[bytes]:
        """Encode request body to bytes."""
        if self.body is None:
            return None
        if isinstance(self.body, bytes):
            return self.body
        if isinstance(self.body, str):
            return self.body.encode("utf-8")
        return json.dumps(self.body).encode("utf-8")


@dataclass
class RetryConfig:
    """Retry configuration for failed requests."""

    max_retries: int = 3
    backoff_factor: float = 0.5
    max_backoff_seconds: float = 60.0
    retry_on_status: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    retry_on_exceptions: List[type] = field(default_factory=lambda: [ConnectionError, TimeoutError])


@dataclass
class AuthConfig:
    """Authentication configuration."""

    auth_type: AuthType = AuthType.NONE
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"
    oauth2_token_url: Optional[str] = None
    oauth2_client_id: Optional[str] = None
    oauth2_client_secret: Optional[str] = None
    oauth2_scope: Optional[str] = None


class RESTClient:
    """Reusable REST API client with retry and auth support."""

    def __init__(
        self,
        base_url: str = "",
        auth: Optional[AuthConfig] = None,
        retry: Optional[RetryConfig] = None,
        default_headers: Optional[Dict[str, str]] = None,
        timeout_seconds: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth = auth or AuthConfig()
        self.retry = retry or RetryConfig()
        self.default_headers = default_headers or {}
        self.timeout_seconds = timeout_seconds
        self._request_hooks: List[Callable] = []
        self._response_hooks: List[Callable] = []
        self._session_headers: Dict[str, str] = {}
        self._opener = urllib.request.build_opener()

    def add_request_hook(self, hook: Callable) -> None:
        """Add a hook called before each request."""
        self._request_hooks.append(hook)

    def add_response_hook(self, hook: Callable) -> None:
        """Add a hook called after each response."""
        self._response_hooks.append(hook)

    def _build_headers(self, request: RESTRequest) -> Dict[str, str]:
        """Build complete headers for a request."""
        headers = {**self.default_headers, **self._session_headers, **request.headers}
        headers.setdefault("Accept", "application/json")
        headers.setdefault("User-Agent", "APEX-OS-RESTClient/1.0")

        if request.body is not None and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        # Apply authentication
        if self.auth.auth_type == AuthType.BEARER and self.auth.token:
            headers["Authorization"] = f"Bearer {self.auth.token}"
        elif self.auth.auth_type == AuthType.API_KEY and self.auth.api_key:
            headers[self.auth.api_key_header] = self.auth.api_key
        elif self.auth.auth_type == AuthType.BASIC and self.auth.username:
            import base64

            creds = f"{self.auth.username}:{self.auth.password or ''}"
            encoded = base64.b64encode(creds.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        return headers

    def _execute_single(self, request: RESTRequest) -> RESTResponse:
        """Execute a single HTTP request."""
        url = request.full_url()
        if not url.startswith(("http://", "https://")):
            url = f"{self.base_url}/{url.lstrip('/')}"

        headers = self._build_headers(request)
        data = request.encoded_body()

        req = urllib.request.Request(
            url=url,
            data=data,
            headers=headers,
            method=request.method.value,
        )

        start = time.time()
        try:
            with self._opener.open(req, timeout=request.timeout_seconds) as resp:
                body = resp.read()
                elapsed = (time.time() - start) * 1000
                resp_headers = {k: v for k, v in resp.headers.items()}

                # Try to decode as JSON
                try:
                    decoded: Union[str, Dict[str, Any], bytes] = json.loads(body)
                except (json.JSONDecodeError, ValueError):
                    decoded = body

                return RESTResponse(
                    status_code=resp.status,
                    body=decoded,
                    headers=resp_headers,
                    elapsed_ms=elapsed,
                    url=url,
                )
        except urllib.error.HTTPError as e:
            elapsed = (time.time() - start) * 1000
            body = e.read()
            try:
                decoded = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                decoded = body
            return RESTResponse(
                status_code=e.code,
                body=decoded,
                headers=dict(e.headers.items()) if e.headers else {},
                elapsed_ms=elapsed,
                url=url,
            )

    def execute(self, request: RESTRequest) -> RESTResponse:
        """Execute a request with retry logic."""
        last_exception: Optional[Exception] = None

        for attempt in range(self.retry.max_retries + 1):
            # Run request hooks
            for hook in self._request_hooks:
                hook(request)

            try:
                response = self._execute_single(request)

                # Run response hooks
                for hook in self._response_hooks:
                    hook(response)

                if response.status_code in self.retry.retry_on_status and attempt < self.retry.max_retries:
                    delay = min(
                        self.retry.backoff_factor * (2**attempt),
                        self.retry.max_backoff_seconds,
                    )
                    logger.warning(
                        "Retryable status %d on attempt %d/%d, waiting %.1fs",
                        response.status_code,
                        attempt + 1,
                        self.retry.max_retries + 1,
                        delay,
                    )
                    time.sleep(delay)
                    continue

                return response

            except tuple(self.retry.retry_on_exceptions) as e:
                last_exception = e
                if attempt < self.retry.max_retries:
                    delay = min(
                        self.retry.backoff_factor * (2**attempt),
                        self.retry.max_backoff_seconds,
                    )
                    logger.warning(
                        "Request failed on attempt %d/%d: %s, waiting %.1fs",
                        attempt + 1,
                        self.retry.max_retries + 1,
                        e,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    break

        if last_exception:
            raise last_exception
        raise RuntimeError("Request failed after all retries")

    def get(
        self,
        path: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> RESTResponse:
        """Convenience method for GET requests."""
        return self.execute(
            RESTRequest(
                method=HTTPMethod.GET,
                url=path,
                params=params or {},
                headers=headers or {},
            )
        )

    def post(
        self,
        path: str,
        body: Optional[Union[str, Dict[str, Any]]] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> RESTResponse:
        """Convenience method for POST requests."""
        return self.execute(
            RESTRequest(
                method=HTTPMethod.POST,
                url=path,
                body=body,
                params=params or {},
                headers=headers or {},
            )
        )

    def put(
        self,
        path: str,
        body: Optional[Union[str, Dict[str, Any]]] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> RESTResponse:
        """Convenience method for PUT requests."""
        return self.execute(
            RESTRequest(
                method=HTTPMethod.PUT,
                url=path,
                body=body,
                params=params or {},
                headers=headers or {},
            )
        )

    def patch(
        self,
        path: str,
        body: Optional[Union[str, Dict[str, Any]]] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> RESTResponse:
        """Convenience method for PATCH requests."""
        return self.execute(
            RESTRequest(
                method=HTTPMethod.PATCH,
                url=path,
                body=body,
                params=params or {},
                headers=headers or {},
            )
        )

    def delete(
        self,
        path: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> RESTResponse:
        """Convenience method for DELETE requests."""
        return self.execute(
            RESTRequest(
                method=HTTPMethod.DELETE,
                url=path,
                params=params or {},
                headers=headers or {},
            )
        )

    def set_session_header(self, key: str, value: str) -> None:
        """Set a session-level header."""
        self._session_headers[key] = value

    def clear_session_headers(self) -> None:
        """Clear all session headers."""
        self._session_headers.clear()
