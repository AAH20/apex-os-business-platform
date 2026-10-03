"""Comprehensive CRUD tests for all APEX-OS Business Platform modules."""
import pytest
import pytest_asyncio
import httpx
import asyncio
from typing import Any, Dict, List

BASE_URL = "http://localhost:8000/api/v1"
MODULES = ["users", "products", "orders", "customers", "invoices", "payments"]


@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as c:
        yield c


@pytest_asyncio.fixture
async def sample_data(client):
    """Create a sample record per module for read/update/delete tests."""
    records = {}
    for module in MODULES:
        payload = _payload_for(module)
        r = await client.post(f"/{module}/", json=payload)
        if r.status_code in (200, 201):
            records[module] = r.json()
    yield records
    # Cleanup
    for module, rec in records.items():
        rid = rec.get("id") or rec.get("_id")
        if rid:
            await client.delete(f"/{module}/{rid}")


def _payload_for(module: str) -> Dict[str, Any]:
    payloads = {
        "users": {"name": "Test User", "email": "test@example.com", "role": "member"},
        "products": {"name": "Test Product", "price": 29.99, "sku": "TEST-001"},
        "orders": {"customer_id": "cust-1", "items": [{"product_id": "p1", "qty": 2}]},
        "customers": {"name": "Test Customer", "email": "cust@example.com"},
        "invoices": {"customer_id": "cust-1", "amount": 100.0, "status": "draft"},
        "payments": {"invoice_id": "inv-1", "amount": 100.0, "method": "card"},
    }
    return payloads.get(module, {"name": "Test"})


# ─── CREATE ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_create(client, module):
    r = await client.post(f"/{module}/", json=_payload_for(module))
    assert r.status_code in (200, 201), f"Create {module} failed: {r.text}"
    data = r.json()
    assert "id" in data or "_id" in data


@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_create_validation_error(client, module):
    r = await client.post(f"/{module}/", json={})
    assert r.status_code == 422


# ─── READ ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_list(client, module):
    r = await client.get(f"/{module}/")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) or "items" in data or "data" in data


@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_get_by_id(client, sample_data, module):
    rec = sample_data.get(module)
    if not rec:
        pytest.skip(f"No record created for {module}")
    rid = rec.get("id") or rec.get("_id")
    r = await client.get(f"/{module}/{rid}")
    assert r.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_get_not_found(client, module):
    r = await client.get(f"/{module}/nonexistent-id-99999")
    assert r.status_code == 404


# ─── UPDATE ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_update(client, sample_data, module):
    rec = sample_data.get(module)
    if not rec:
        pytest.skip(f"No record created for {module}")
    rid = rec.get("id") or rec.get("_id")
    r = await client.put(f"/{module}/{rid}", json={"name": "Updated"})
    assert r.status_code in (200, 204)


@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_update_not_found(client, module):
    r = await client.put(f"/{module}/nonexistent-id-99999", json={"name": "X"})
    assert r.status_code == 404


# ─── DELETE ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_delete(client, sample_data, module):
    rec = sample_data.get(module)
    if not rec:
        pytest.skip(f"No record created for {module}")
    rid = rec.get("id") or rec.get("_id")
    r = await client.delete(f"/{module}/{rid}")
    assert r.status_code in (200, 204)
    r2 = await client.get(f"/{module}/{rid}")
    assert r2.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_delete_not_found(client, module):
    r = await client.delete(f"/{module}/nonexistent-id-99999")
    assert r.status_code == 404


# ─── PAGINATION ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_pagination(client, module):
    r = await client.get(f"/{module}/?page=1&limit=1")
    assert r.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_pagination_invalid_page(client, module):
    r = await client.get(f"/{module}/?page=-1&limit=0")
    assert r.status_code in (400, 422)


# ─── ERROR HANDLING ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_method_not_allowed(client):
    r = await client.patch("/users/nonexistent")
    assert r.status_code == 405


@pytest.mark.asyncio
async def test_malformed_json(client):
    r = await client.post("/users/", content=b"{invalid", headers={"Content-Type": "application/json"})
    assert r.status_code == 422
