"""Deepened API module: GraphQL, WebSockets, versioning, rate limiting, OpenAPI docs."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# 1. GraphQL endpoint with schema stitching
# ---------------------------------------------------------------------------


@dataclass
class GraphQLField:
    name: str
    resolver: Callable[..., Any]
    args: Dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class GraphQLType:
    name: str
    fields: Dict[str, GraphQLField] = field(default_factory=dict)


class SchemaStitcher:
    """Merge multiple GraphQL sub-schemas into one unified schema."""

    def __init__(self) -> None:
        self._types: Dict[str, GraphQLType] = {}
        self._query_fields: Dict[str, GraphQLField] = {}
        self._mutation_fields: Dict[str, GraphQLField] = {}
        self._subscriptions: Dict[str, GraphQLField] = {}

    def register_schema(self, schema: Dict[str, Any]) -> None:
        """Register a sub-schema dict with 'types', 'queries', 'mutations'."""
        for type_def in schema.get("types", []):
            gql_type = GraphQLType(name=type_def["name"])
            for fname, fdef in type_def.get("fields", {}).items():
                gql_type.fields[fname] = GraphQLField(
                    name=fname,
                    resolver=fdef.get("resolver"),
                    args=fdef.get("args", {}),
                    description=fdef.get("description", ""),
                )
            self._types[type_def["name"]] = gql_type
        for fname, fdef in schema.get("queries", {}).items():
            self._query_fields[fname] = GraphQLField(
                name=fname,
                resolver=fdef.get("resolver"),
                args=fdef.get("args", {}),
            )
        for fname, fdef in schema.get("mutations", {}).items():
            self._mutation_fields[fname] = GraphQLField(
                name=fname,
                resolver=fdef.get("resolver"),
                args=fdef.get("args", {}),
            )
        for fname, fdef in schema.get("subscriptions", {}).items():
            self._subscriptions[fname] = GraphQLField(
                name=fname,
                resolver=fdef.get("resolver"),
                args=fdef.get("args", {}),
            )

    def get_schema_sdl(self) -> str:
        """Generate a simplified SDL representation of the merged schema."""
        lines: List[str] = []
        for tname, tdef in self._types.items():
            lines.append(f"type {tname} {{")
            for fname in tdef.fields:
                lines.append(f"  {fname}")
            lines.append("}")
        if self._query_fields:
            lines.append("type Query {")
            for fname in self._query_fields:
                lines.append(f"  {fname}")
            lines.append("}")
        if self._mutation_fields:
            lines.append("type Mutation {")
            for fname in self._mutation_fields:
                lines.append(f"  {fname}")
            lines.append("}")
        return "\n".join(lines)

    async def execute(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against the merged schema."""
        variables = variables or {}
        query = query.strip()
        operation = "query"
        if query.startswith("mutation"):
            operation = "mutation"
        elif query.startswith("subscription"):
            operation = "subscription"
        field_name = self._extract_field_name(query)
        if not field_name:
            return {"errors": [{"message": "Could not parse query"}]}
        pool = (
            self._query_fields
            if operation == "query"
            else self._mutation_fields if operation == "mutation" else self._subscriptions
        )
        gql_field = pool.get(field_name)
        if not gql_field or not gql_field.resolver:
            return {"errors": [{"message": f"Unknown field: {field_name}"}]}
        try:
            result = gql_field.resolver(**variables)
            if asyncio.iscoroutine(result):
                result = await result
            return {"data": {field_name: result}}
        except Exception as exc:
            return {"errors": [{"message": str(exc)}]}

    @staticmethod
    def _extract_field_name(query: str) -> Optional[str]:
        """Naive field extraction — production would use a real parser."""
        depth = 0
        for ch in query:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif depth == 1 and ch.isalpha():
                start = query.index(ch)
                end = start
                while end < len(query) and (query[end].isalnum() or query[end] == "_"):
                    end += 1
                return query[start:end]
        return None


# ---------------------------------------------------------------------------
# 2. WebSocket support for real-time updates
# ---------------------------------------------------------------------------


@dataclass
class WSClient:
    client_id: str
    socket: Any
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: float = field(default_factory=time.time)


class WebSocketManager:
    """Manage WebSocket connections and pub/sub for real-time updates."""

    def __init__(self) -> None:
        self._clients: Dict[str, WSClient] = {}
        self._channels: Dict[str, Set[str]] = defaultdict(set)
        self._message_queue: asyncio.Queue[Tuple[str, Dict[str, Any]]] = asyncio.Queue()

    async def connect(self, socket: Any) -> str:
        client_id = str(uuid.uuid4())
        self._clients[client_id] = WSClient(client_id=client_id, socket=socket)
        return client_id

    async def disconnect(self, client_id: str) -> None:
        client = self._clients.pop(client_id, None)
        if client:
            for channel in client.subscriptions:
                self._channels[channel].discard(client_id)

    async def handle_message(self, client_id: str, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await self.send_to(client_id, {"type": "error", "message": "Invalid JSON"})
            return
        msg_type = msg.get("type", "")
        if msg_type == "subscribe":
            channel = msg.get("channel", "")
            self._channels[channel].add(client_id)
            if client_id in self._clients:
                self._clients[client_id].subscriptions.add(channel)
            await self.send_to(client_id, {"type": "subscribed", "channel": channel})
        elif msg_type == "unsubscribe":
            channel = msg.get("channel", "")
            self._channels[channel].discard(client_id)
            if client_id in self._clients:
                self._clients[client_id].subscriptions.discard(channel)
            await self.send_to(client_id, {"type": "unsubscribed", "channel": channel})
        elif msg_type == "ping":
            await self.send_to(client_id, {"type": "pong"})

    async def publish(self, channel: str, payload: Dict[str, Any]) -> int:
        """Publish to all subscribers of a channel. Returns delivery count."""
        recipients = self._channels.get(channel, set()).copy()
        delivered = 0
        for cid in recipients:
            if await self.send_to(cid, {"type": "message", "channel": channel, "data": payload}):
                delivered += 1
        return delivered

    async def send_to(self, client_id: str, message: Dict[str, Any]) -> bool:
        client = self._clients.get(client_id)
        if not client:
            return False
        try:
            if hasattr(client.socket, "send_json"):
                await client.socket.send_json(message)
            elif hasattr(client.socket, "send"):
                await client.socket.send(json.dumps(message))
            return True
        except Exception:
            await self.disconnect(client_id)
            return False

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def channel_count(self) -> int:
        return len(self._channels)


# ---------------------------------------------------------------------------
# 3. API versioning with content negotiation
# ---------------------------------------------------------------------------


class VersionPolicy(Enum):
    HEADER = "header"
    URL_PATH = "url_path"
    QUERY_PARAM = "query_param"
    CONTENT_TYPE = "content_type"


@dataclass
class APIVersion:
    major: int
    minor: int = 0
    patch: int = 0

    @classmethod
    def from_string(cls, raw: str) -> "APIVersion":
        parts = raw.lstrip("v").split(".")
        nums = [int(p) for p in parts] + [0, 0, 0]
        return cls(major=nums[0], minor=nums[1], patch=nums[2])

    def __str__(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}"


class ContentNegotiator:
    """Resolve API version from request via multiple strategies."""

    def __init__(
        self,
        default_version: APIVersion = APIVersion(1, 0),
        supported_versions: Optional[List[APIVersion]] = None,
        policy: VersionPolicy = VersionPolicy.HEADER,
    ) -> None:
        self.default_version = default_version
        self.supported_versions = supported_versions or [default_version]
        self.policy = policy

    def negotiate(
        self,
        accept_header: str = "",
        url_path: str = "",
        query_params: Optional[Dict[str, str]] = None,
    ) -> Tuple[APIVersion, str]:
        """Return (version, content_type) tuple."""
        query_params = query_params or {}
        version: Optional[APIVersion] = None
        if self.policy == VersionPolicy.HEADER:
            version = self._from_accept_header(accept_header)
        elif self.policy == VersionPolicy.URL_PATH:
            version = self._from_url_path(url_path)
        elif self.policy == VersionPolicy.QUERY_PARAM:
            raw = query_params.get("api_version", "")
            version = APIVersion.from_string(raw) if raw else None
        elif self.policy == VersionPolicy.CONTENT_TYPE:
            version = self._from_content_type(accept_header)
        if version is None:
            version = self.default_version
        if version not in self.supported_versions:
            version = self.default_version
        content_type = self._resolve_content_type(accept_header)
        return version, content_type

    def _from_accept_header(self, header: str) -> Optional[APIVersion]:
        for part in header.split(","):
            part = part.strip()
            if "vnd.apex" in part and "v" in part:
                for token in part.split(";"):
                    token = token.strip()
                    if token.startswith("v") and token[1:2].isdigit():
                        try:
                            return APIVersion.from_string(token.split("+")[0])
                        except (ValueError, IndexError):
                            continue
        return None

    def _from_url_path(self, path: str) -> Optional[APIVersion]:
        for segment in path.split("/"):
            if segment.startswith("v") and len(segment) > 1 and segment[1].isdigit():
                try:
                    return APIVersion.from_string(segment)
                except ValueError:
                    continue
        return None

    def _from_content_type(self, header: str) -> Optional[APIVersion]:
        for part in header.split(","):
            part = part.strip()
            if part.startswith("application/vnd.apex"):
                for token in part.split(";"):
                    token = token.strip()
                    if token.startswith("version="):
                        try:
                            return APIVersion.from_string(token.split("=")[1])
                        except (ValueError, IndexError):
                            continue
        return None

    @staticmethod
    def _resolve_content_type(accept_header: str) -> str:
        if "application/json" in accept_header:
            return "application/json"
        if "application/xml" in accept_header:
            return "application/xml"
        if "text/html" in accept_header:
            return "text/html"
        return "application/json"


# ---------------------------------------------------------------------------
# 4. Rate limiting with token bucket algorithm
# ---------------------------------------------------------------------------


@dataclass
class TokenBucket:
    capacity: float
    refill_rate: float  # tokens per second
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.time)

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def consume(self, tokens: float = 1.0) -> bool:
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def remaining(self) -> float:
        self._refill()
        return self.tokens

    @property
    def retry_after(self) -> float:
        self._refill()
        if self.tokens >= 1.0:
            return 0.0
        return (1.0 - self.tokens) / self.refill_rate


class RateLimiter:
    """Token-bucket rate limiter keyed by client identifier."""

    def __init__(
        self,
        capacity: float = 100.0,
        refill_rate: float = 10.0,
        key_func: Optional[Callable[[Dict[str, Any]], str]] = None,
    ) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._buckets: Dict[str, TokenBucket] = {}
        self._key_func = key_func or (lambda ctx: ctx.get("client_id", "anonymous"))

    def _get_bucket(self, key: str) -> TokenBucket:
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(
                capacity=self.capacity, refill_rate=self.refill_rate
            )
        return self._buckets[key]

    def is_allowed(self, context: Dict[str, Any], cost: float = 1.0) -> Tuple[bool, Dict[str, Any]]:
        key = self._key_func(context)
        bucket = self._get_bucket(key)
        allowed = bucket.consume(cost)
        headers = {
            "X-RateLimit-Limit": str(int(self.capacity)),
            "X-RateLimit-Remaining": str(int(bucket.remaining)),
            "X-RateLimit-Reset": str(int(time.time() + bucket.retry_after)),
        }
        if not allowed:
            headers["Retry-After"] = str(int(bucket.retry_after) + 1)
        return allowed, headers

    def get_bucket_info(self, key: str) -> Dict[str, Any]:
        bucket = self._buckets.get(key)
        if not bucket:
            return {"capacity": self.capacity, "remaining": self.capacity, "refill_rate": self.refill_rate}
        return {
            "capacity": bucket.capacity,
            "remaining": bucket.remaining,
            "refill_rate": bucket.refill_rate,
            "retry_after": bucket.retry_after,
        }


# ---------------------------------------------------------------------------
# 5. API documentation with OpenAPI / Swagger
# ---------------------------------------------------------------------------


class OpenAPIDocumentation:
    """Generate and serve OpenAPI 3.0 specification."""

    def __init__(
        self,
        title: str = "APEX-OS Business Platform API",
        version: str = "1.0.0",
        description: str = "",
    ) -> None:
        self.title = title
        self.version = version
        self.description = description
        self._paths: Dict[str, Dict[str, Any]] = {}
        self._schemas: Dict[str, Any] = {}
        self._tags: List[Dict[str, str]] = []

    def add_path(
        self,
        path: str,
        method: str,
        summary: str = "",
        description: str = "",
        parameters: Optional[List[Dict[str, Any]]] = None,
        request_body: Optional[Dict[str, Any]] = None,
        responses: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        if path not in self._paths:
            self._paths[path] = {}
        self._paths[path][method.lower()] = {
            "summary": summary,
            "description": description,
            "parameters": parameters or [],
            "requestBody": request_body,
            "responses": responses or {"200": {"description": "Success"}},
            "tags": tags or [],
            "operationId": f"{method.lower()}_{path.replace('/', '_').strip('_')}",
        }

    def add_schema(self, name: str, schema: Dict[str, Any]) -> None:
        self._schemas[name] = schema

    def add_tag(self, name: str, description: str = "") -> None:
        self._tags.append({"name": name, "description": description})

    def to_spec(self) -> Dict[str, Any]:
        return {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description,
            },
            "servers": [{"url": "/api/v1"}],
            "tags": self._tags,
            "paths": self._paths,
            "components": {"schemas": self._schemas},
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_spec(), indent=indent)

    def get_swagger_ui(self, spec_url: str = "/api/openapi.json") -> str:
        """Return Swagger UI HTML for interactive documentation."""
        return f"""<!DOCTYPE html>
<html><head><title>{self.title} — Swagger UI</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
</head><body><div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({{ url: "{spec_url}", dom_id: "#swagger-ui" }});
</script></body></html>"""


# ---------------------------------------------------------------------------
# Convenience: unified API facade tying all five features together
# ---------------------------------------------------------------------------


class DeepenedAPI:
    """Unified facade combining all deepened API capabilities."""

    def __init__(self) -> None:
        self.graphql = SchemaStitcher()
        self.websocket = WebSocketManager()
        self.negotiator = ContentNegotiator()
        self.rate_limiter = RateLimiter()
        self.docs = OpenAPIDocumentation()

    def configure_default(self) -> None:
        """Wire up sensible defaults for all subsystems."""
        self.negotiator = ContentNegotiator(
            default_version=APIVersion(1, 0),
            supported_versions=[APIVersion(1, 0), APIVersion(2, 0)],
            policy=VersionPolicy.HEADER,
        )
        self.rate_limiter = RateLimiter(capacity=100, refill_rate=10)
        self.docs.add_tag("Core", "Core API operations")
        self.docs.add_tag("GraphQL", "GraphQL endpoint")
        self.docs.add_tag("WebSocket", "Real-time WebSocket endpoint")
        self.docs.add_path(
            "/graphql", "post",
            summary="GraphQL endpoint",
            description="Execute GraphQL queries against the stitched schema.",
            tags=["GraphQL"],
        )
        self.docs.add_path(
            "/ws", "get",
            summary="WebSocket endpoint",
            description="Connect for real-time pub/sub updates.",
            tags=["WebSocket"],
        )
