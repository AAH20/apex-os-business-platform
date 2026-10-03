"""Tests for deepened API modules: GraphQL, WebSockets, versioning, rate limiting, OpenAPI."""
import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock


class TestGraphQL:
    """Test GraphQL API."""

    def test_graphql_query_parsing(self):
        from apex_os_bp.api.deepened import GraphQLHandler
        handler = GraphQLHandler()
        result = handler.parse("{ users { id name } }")
        assert result is not None
        assert "users" in str(result)

    def test_graphql_mutation_parsing(self):
        from apex_os_bp.api.deepened import GraphQLHandler
        handler = GraphQLHandler()
        result = handler.parse("mutation { createUser(name: \"Alice\") { id } }")
        assert "createUser" in str(result)

    def test_graphql_execution(self):
        from apex_os_bp.api.deepened import GraphQLHandler
        handler = GraphQLHandler()
        schema = handler.build_schema({"users": [{"id": 1, "name": "Alice"}]})
        result = handler.execute("{ users { id name } }", schema)
        assert result["data"]["users"][0]["name"] == "Alice"

    def test_graphql_validation_error(self):
        from apex_os_bp.api.deepened import GraphQLHandler
        handler = GraphQLHandler()
        with pytest.raises(Exception):
            handler.parse("{ invalid syntax here")


class TestWebSockets:
    """Test WebSocket handling."""

    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        from apex_os_bp.api.deepened import WebSocketManager
        manager = WebSocketManager()
        mock_ws = MagicMock()
        await manager.connect(mock_ws, client_id="c1")
        assert "c1" in manager.connections

    @pytest.mark.asyncio
    async def test_websocket_broadcast(self):
        from apex_os_bp.api.deepened import WebSocketManager
        manager = WebSocketManager()
        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()
        await manager.connect(mock_ws, client_id="c1")
        await manager.broadcast({"type": "update"})
        mock_ws.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_disconnect(self):
        from apex_os_bp.api.deepened import WebSocketManager
        manager = WebSocketManager()
        mock_ws = MagicMock()
        await manager.connect(mock_ws, client_id="c1")
        await manager.disconnect("c1")
        assert "c1" not in manager.connections


class TestAPIVersioning:
    """Test API versioning."""

    def test_version_header_parsing(self):
        from apex_os_bp.api.deepened import VersionManager
        vm = VersionManager(default="v1")
        version = vm.parse_header("application/vnd.api.v2+json")
        assert version == "v2"

    def test_version_default(self):
        from apex_os_bp.api.deepened import VersionManager
        vm = VersionManager(default="v1")
        assert vm.parse_header(None) == "v1"

    def test_version_routing(self):
        from apex_os_bp.api.deepened import VersionManager
        vm = VersionManager()
        assert vm.get_handler("v1") is not None
        assert vm.get_handler("v2") is not None


class TestRateLimiting:
    """Test rate limiting."""

    def test_rate_limit_allows_under_limit(self):
        from apex_os_bp.api.deepened import RateLimiter
        limiter = RateLimiter(max_requests=5, window=60)
        for i in range(5):
            assert limiter.allow("client_1") is True

    def test_rate_limit_blocks_over_limit(self):
        from apex_os_bp.api.deepened import RateLimiter
        limiter = RateLimiter(max_requests=2, window=60)
        limiter.allow("client_1")
        limiter.allow("client_1")
        assert limiter.allow("client_1") is False

    def test_rate_limit_window_reset(self):
        from apex_os_bp.api.deepened import RateLimiter
        limiter = RateLimiter(max_requests=1, window=0)
        assert limiter.allow("client_1") is True
        assert limiter.allow("client_1") is True  # window expired

    def test_rate_limit_per_client(self):
        from apex_os_bp.api.deepened import RateLimiter
        limiter = RateLimiter(max_requests=1, window=60)
        assert limiter.allow("client_a") is True
        assert limiter.allow("client_b") is True


class TestOpenAPIDocs:
    """Test OpenAPI documentation generation."""

    def test_openapi_schema_generation(self):
        from apex_os_bp.api.deepened import OpenAPIGenerator
        gen = OpenAPIGenerator(title="Test API", version="1.0")
        spec = gen.generate()
        assert spec["info"]["title"] == "Test API"
        assert spec["info"]["version"] == "1.0"

    def test_openapi_add_path(self):
        from apex_os_bp.api.deepened import OpenAPIGenerator
        gen = OpenAPIGenerator(title="Test", version="1.0")
        gen.add_path("/users", "GET", {"summary": "List users"})
        spec = gen.generate()
        assert "/users" in spec["paths"]

    def test_openapi_add_model(self):
        from apex_os_bp.api.deepened import OpenAPIGenerator
        gen = OpenAPIGenerator(title="Test", version="1.0")
        gen.add_model("User", {"id": "integer", "name": "string"})
        spec = gen.generate()
        assert "User" in spec["components"]["schemas"]
