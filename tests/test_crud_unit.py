"""Comprehensive CRUD unit tests for APEX-OS Business Platform."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Any

# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_entity():
    return {
        "id": "ent_001",
        "name": "Test Entity",
        "status": "active",
        "created_at": "2026-10-01T00:00:00Z",
        "updated_at": "2026-10-01T00:00:00Z",
        "metadata": {"key": "value"},
    }


@pytest.fixture
def sample_list():
    return [
        {"id": f"ent_{i:03d}", "name": f"Entity {i}", "status": "active"}
        for i in range(5)
    ]


@pytest_asyncio.fixture
async def mock_client():
    client = AsyncMock()
    client.base_url = "http://localhost:8000"
    client.timeout = 30
    return client


# ── 1. CRUD Utility Functions ─────────────────────────────────────────────

class TestCrudUtilities:
    """Test CRUD utility/helper functions."""

    def test_generate_id_format(self):
        from src.crud.utils import generate_id
        eid = generate_id()
        assert isinstance(eid, str)
        assert len(eid) >= 8

    def test_generate_id_prefix(self):
        from src.crud.utils import generate_id
        eid = generate_id(prefix="usr")
        assert eid.startswith("usr_")

    def test_sanitize_string(self):
        from src.crud.utils import sanitize_string
        assert sanitize_string("  hello  ") == "hello"
        assert sanitize_string("") == ""
        assert sanitize_string(None) == ""

    def test_deep_merge(self):
        from src.crud.utils import deep_merge
        a = {"x": 1, "nested": {"a": 1}}
        b = {"y": 2, "nested": {"b": 2}}
        result = deep_merge(a, b)
        assert result == {"x": 1, "y": 2, "nested": {"a": 1, "b": 2}}

    def test_paginate_list(self):
        from src.crud.utils import paginate
        items = list(range(25))
        page = paginate(items, page=1, per_page=10)
        assert len(page["items"]) == 10
        assert page["total"] == 25
        assert page["page"] == 1

    def test_paginate_empty(self):
        from src.crud.utils import paginate
        result = paginate([], page=1, per_page=10)
        assert result["items"] == []
        assert result["total"] == 0

    def test_parse_datetime_valid(self):
        from src.crud.utils import parse_datetime
        dt = parse_datetime("2026-10-01T00:00:00Z")
        assert isinstance(dt, datetime)

    def test_parse_datetime_invalid(self):
        from src.crud.utils import parse_datetime
        with pytest.raises(ValueError):
            parse_datetime("not-a-date")

    def test_build_query_params(self):
        from src.crud.utils import build_query_params
        params = build_query_params(status="active", limit=10, offset=0)
        assert params == {"status": "active", "limit": 10, "offset": 0}

    def test_build_query_params_skips_none(self):
        from src.crud.utils import build_query_params
        params = build_query_params(status="active", name=None)
        assert params == {"status": "active"}


# ── 2. CRUD Data Models ───────────────────────────────────────────────────

class TestCrudModels:
    """Test CRUD data model definitions and behaviour."""

    def test_entity_model_creation(self):
        from src.crud.models import Entity
        e = Entity(id="e1", name="Test", status="active")
        assert e.id == "e1"
        assert e.name == "Test"
        assert e.status == "active"

    def test_entity_model_defaults(self):
        from src.crud.models import Entity
        e = Entity(id="e2", name="NoStatus")
        assert e.status == "active"
        assert e.created_at is not None

    def test_entity_model_to_dict(self):
        from src.crud.models import Entity
        e = Entity(id="e3", name="DictTest", status="inactive")
        d = e.to_dict()
        assert isinstance(d, dict)
        assert d["id"] == "e3"
        assert d["name"] == "DictTest"

    def test_entity_model_from_dict(self):
        from src.crud.models import Entity
        data = {"id": "e4", "name": "FromDict", "status": "pending"}
        e = Entity.from_dict(data)
        assert e.id == "e4"
        assert e.status == "pending"

    def test_entity_model_validation_error(self):
        from src.crud.models import Entity
        with pytest.raises(ValueError):
            Entity(id="", name="")

    def test_entity_list_model(self):
        from src.crud.models import EntityList
        items = [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}]
        el = EntityList(items=items, total=2)
        assert el.total == 2
        assert len(el.items) == 2

    def test_audit_log_model(self):
        from src.crud.models import AuditLog
        log = AuditLog(action="create", entity_id="e1", user_id="u1")
        assert log.action == "create"
        assert log.entity_id == "e1"

    def test_entity_status_enum(self):
        from src.crud.models import EntityStatus
        assert EntityStatus.ACTIVE == "active"
        assert EntityStatus.INACTIVE == "inactive"
        assert EntityStatus.PENDING == "pending"


# ── 3. CRUD API Client Methods ────────────────────────────────────────────

class TestCrudApiClient:
    """Test CRUD API client HTTP methods."""

    @pytest.mark.asyncio
    async def test_create_entity(self, mock_client, sample_entity):
        from src.crud.client import CrudClient
        mock_client.post.return_value = sample_entity
        client = CrudClient(base_url="http://test", _session=mock_client)
        result = await client.create({"name": "Test Entity"})
        assert result["id"] == "ent_001"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_entity(self, mock_client, sample_entity):
        from src.crud.client import CrudClient
        mock_client.get.return_value = sample_entity
        client = CrudClient(base_url="http://test", _session=mock_client)
        result = await client.get("ent_001")
        assert result["name"] == "Test Entity"
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_entities(self, mock_client, sample_list):
        from src.crud.client import CrudClient
        mock_client.get.return_value = {"items": sample_list, "total": 5}
        client = CrudClient(base_url="http://test", _session=mock_client)
        result = await client.list()
        assert result["total"] == 5
        assert len(result["items"]) == 5

    @pytest.mark.asyncio
    async def test_update_entity(self, mock_client, sample_entity):
        from src.crud.client import CrudClient
        mock_client.put.return_value = {**sample_entity, "name": "Updated"}
        client = CrudClient(base_url="http://test", _session=mock_client)
        result = await client.update("ent_001", {"name": "Updated"})
        assert result["name"] == "Updated"
        mock_client.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_entity(self, mock_client):
        from src.crud.client import CrudClient
        mock_client.delete.return_value = {"deleted": True}
        client = CrudClient(base_url="http://test", _session=mock_client)
        result = await client.delete("ent_001")
        assert result["deleted"] is True
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_entities(self, mock_client, sample_list):
        from src.crud.client import CrudClient
        mock_client.get.return_value = {"items": sample_list[:2], "total": 2}
        client = CrudClient(base_url="http://test", _session=mock_client)
        result = await client.search(query="Entity")
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_bulk_create(self, mock_client, sample_list):
        from src.crud.client import CrudClient
        mock_client.post.return_value = {"created": 5, "items": sample_list}
        client = CrudClient(base_url="http://test", _session=mock_client)
        result = await client.bulk_create([{"name": f"E{i}"} for i in range(5)])
        assert result["created"] == 5

    @pytest.mark.asyncio
    async def test_client_base_url(self):
        from src.crud.client import CrudClient
        client = CrudClient(base_url="http://api.test")
        assert client.base_url == "http://api.test"


# ── 4. CRUD Validation Logic ─────────────────────────────────────────────

class TestCrudValidation:
    """Test CRUD input validation."""

    def test_validate_name_too_short(self):
        from src.crud.validation import validate_entity
        with pytest.raises(ValueError, match="name"):
            validate_entity({"name": ""})

    def test_validate_name_valid(self):
        from src.crud.validation import validate_entity
        result = validate_entity({"name": "Valid Name", "status": "active"})
        assert result["name"] == "Valid Name"

    def test_validate_status_invalid(self):
        from src.crud.validation import validate_entity
        with pytest.raises(ValueError, match="status"):
            validate_entity({"name": "Test", "status": "bogus"})

    def test_validate_id_format(self):
        from src.crud.validation import validate_id
        assert validate_id("ent_001") is True

    def test_validate_id_invalid(self):
        from src.crud.validation import validate_id
        with pytest.raises(ValueError):
            validate_id("")

    def test_validate_pagination_params(self):
        from src.crud.validation import validate_pagination
        result = validate_pagination(page=1, per_page=20)
        assert result == {"page": 1, "per_page": 20}

    def test_validate_pagination_invalid_page(self):
        from src.crud.validation import validate_pagination
        with pytest.raises(ValueError):
            validate_pagination(page=0, per_page=10)

    def test_validate_pagination_max_per_page(self):
        from src.crud.validation import validate_pagination
        with pytest.raises(ValueError):
            validate_pagination(page=1, per_page=10000)

    def test_validate_metadata_dict(self):
        from src.crud.validation import validate_metadata
        result = validate_metadata({"key": "value"})
        assert result == {"key": "value"}

    def test_validate_metadata_invalid(self):
        from src.crud.validation import validate_metadata
        with pytest.raises(ValueError):
            validate_metadata("not-a-dict")


# ── 5. CRUD Error Handling ───────────────────────────────────────────────

class TestCrudErrorHandling:
    """Test CRUD error handling and exceptions."""

    def test_not_found_error(self):
        from src.crud.exceptions import NotFoundError
        err = NotFoundError("Entity not found")
        assert err.status_code == 404
        assert "not found" in str(err).lower()

    def test_validation_error(self):
        from src.crud.exceptions import ValidationError
        err = ValidationError("Invalid input", fields={"name": "required"})
        assert err.status_code == 422
        assert err.fields == {"name": "required"}

    def test_conflict_error(self):
        from src.crud.exceptions import ConflictError
        err = ConflictError("Duplicate entry")
        assert err.status_code == 409

    def test_unauthorized_error(self):
        from src.crud.exceptions import UnauthorizedError
        err = UnauthorizedError("Auth required")
        assert err.status_code == 401

    def test_server_error(self):
        from src.crud.exceptions import ServerError
        err = ServerError("Internal error")
        assert err.status_code == 500

    @pytest.mark.asyncio
    async def test_client_handles_404(self, mock_client):
        from src.crud.client import CrudClient
        from src.crud.exceptions import NotFoundError
        mock_client.get.side_effect = NotFoundError("Missing")
        client = CrudClient(base_url="http://test", _session=mock_client)
        with pytest.raises(NotFoundError):
            await client.get("nonexistent")

    @pytest.mark.asyncio
    async def test_client_handles_timeout(self, mock_client):
        from src.crud.client import CrudClient
        import asyncio
        mock_client.get.side_effect = asyncio.TimeoutError()
        client = CrudClient(base_url="http://test", _session=mock_client)
        with pytest.raises(asyncio.TimeoutError):
            await client.get("ent_001")

    @pytest.mark.asyncio
    async def test_client_handles_connection_error(self, mock_client):
        from src.crud.client import CrudClient
        mock_client.get.side_effect = ConnectionError("refused")
        client = CrudClient(base_url="http://test", _session=mock_client)
        with pytest.raises(ConnectionError):
            await client.get("ent_001")

    def test_error_response_format(self):
        from src.crud.exceptions import CrudError
        err =CrudError("test error", status_code=400)
        d = err.to_dict()
        assert d["error"] == "test error"
        assert d["status_code"] == 400
