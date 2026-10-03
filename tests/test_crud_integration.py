"""Comprehensive CRUD integration tests for APEX-OS Business Platform."""
import pytest
import pytest_asyncio
import httpx
import asyncio
from typing import Any, Dict, List

BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 10.0


@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as c:
        yield c


@pytest_asyncio.fixture
async def sample_entity(client):
    """Create a test entity and clean up after."""
    payload = {"name": "Test Entity", "type": "test", "status": "active"}
    resp = await client.post("/entities", json=payload)
    assert resp.status_code == 201
    entity = resp.json()
    yield entity
    await client.delete(f"/entities/{entity['id']}")


# ── CRUD Operations ──────────────────────────────────────────────────────────

class TestCRUDOperations:
    @pytest.mark.asyncio
    async def test_create_entity(self, client):
        payload = {"name": "New Entity", "type": "integration", "status": "active"}
        resp = await client.post("/entities", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == payload["name"]
        assert data["id"] is not None
        await client.delete(f"/entities/{data['id']}")

    @pytest.mark.asyncio
    async def test_read_entity(self, client, sample_entity):
        resp = await client.get(f"/entities/{sample_entity['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sample_entity["id"]

    @pytest.mark.asyncio
    async def test_update_entity(self, client, sample_entity):
        resp = await client.put(
            f"/entities/{sample_entity['id']}",
            json={"name": "Updated Entity", "status": "inactive"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Entity"

    @pytest.mark.asyncio
    async def test_patch_entity(self, client, sample_entity):
        resp = await client.patch(
            f"/entities/{sample_entity['id']}", json={"status": "archived"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    @pytest.mark.asyncio
    async def test_delete_entity(self, client):
        resp = await client.post("/entities", json={"name": "To Delete"})
        eid = resp.json()["id"]
        resp = await client.delete(f"/entities/{eid}")
        assert resp.status_code in (200, 204)
        resp = await client.get(f"/entities/{eid}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_entities(self, client):
        resp = await client.get("/entities")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Form Submissions ─────────────────────────────────────────────────────────

class TestFormSubmissions:
    @pytest.mark.asyncio
    async def test_form_submission_creates_record(self, client):
        form_data = {"field_name": "value", "field_email": "test@example.com"}
        resp = await client.post("/forms/submit", data=form_data)
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_form_submission_with_files(self, client):
        files = {"file": ("test.txt", b"content", "text/plain")}
        resp = await client.post("/forms/upload", files=files)
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_form_submission_json(self, client):
        payload = {"title": "Form Test", "description": "Testing JSON form"}
        resp = await client.post("/forms/submit", json=payload)
        assert resp.status_code in (200, 201)


# ── Data Validation ──────────────────────────────────────────────────────────

class TestDataValidation:
    @pytest.mark.asyncio
    async def test_missing_required_field(self, client):
        resp = await client.post("/entities", json={"type": "test"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_field_type(self, client):
        resp = await client.post("/entities", json={"name": 12345})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_payload(self, client):
        resp = await client.post("/entities", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_email_format(self, client):
        resp = await client.post("/entities", json={"name": "Test", "email": "not-an-email"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_field_length_validation(self, client):
        resp = await client.post("/entities", json={"name": "x" * 500})
        assert resp.status_code == 422


# ── Error Handling ───────────────────────────────────────────────────────────

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_not_found(self, client):
        resp = await client.get("/entities/999999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client):
        resp = await client.patch("/entities")
        assert resp.status_code == 405

    @pytest.mark.asyncio
    async def test_unprocessable_entity(self, client):
        resp = await client.post("/entities", content="not json", headers={"Content-Type": "application/json"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_conflict_on_duplicate(self, client):
        payload = {"name": "Duplicate", "unique_key": "dup-001"}
        await client.post("/entities", json=payload)
        resp = await client.post("/entities", json=payload)
        assert resp.status_code == 409


# ── Pagination ───────────────────────────────────────────────────────────────

class TestPagination:
    @pytest.mark.asyncio
    async def test_pagination_default(self, client):
        resp = await client.get("/entities")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_pagination_with_limit(self, client):
        resp = await client.get("/entities?limit=5")
        assert resp.status_code == 200
        assert len(resp.json()) <= 5

    @pytest.mark.asyncio
    async def test_pagination_with_offset(self, client):
        resp = await client.get("/entities?offset=10&limit=5")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_pagination_page_param(self, client):
        resp = await client.get("/entities?page=2&per_page=3")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_pagination_invalid_params(self, client):
        resp = await client.get("/entities?limit=-1")
        assert resp.status_code == 422
