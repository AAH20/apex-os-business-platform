"""Comprehensive integration tests for all 8 pages of APEX-OS Business Platform."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web" / "backend"))

from main import app

PAGES = ["/", "/users", "/products", "/orders", "/reports", "/analytics", "/settings", "/profile"]
RESOURCES = ["dashboard", "accounting", "crm", "analytics", "agent-reach", "bigdata", "datascience", "continuous-bi"]


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── 1. Page Load Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_page_loads_without_errors(client, path):
    """Each of the 8 pages returns HTTP 200."""
    resp = await client.get(path)
    assert resp.status_code == 200, f"Page {path} returned {resp.status_code}"


@pytest.mark.asyncio
async def test_all_pages_return_html(client):
    """All pages return HTML content."""
    for path in PAGES:
        resp = await client.get(path)
        assert "text/html" in resp.headers.get("content-type", ""), f"{path} not HTML"


# ── 2. API Endpoint Data Tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.asyncio
@pytest.mark.parametrize("resource", RESOURCES)
async def test_api_list_returns_data(client, resource):
    """Each resource endpoint returns a non-empty list."""
    resp = await client.get(f"/api/{resource}")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) > 0, f"/api/{resource} returned empty"


@pytest.mark.asyncio
async def test_api_all_endpoint(client):
    resp = await client.get("/api/all")
    assert resp.status_code == 200
    data = resp.json()
    for key in ["dashboard", "accounting", "crm", "analytics", "agent_reach", "bigdata", "datascience", "continuous_bi"]:
        assert key in data, f"Missing key: {key}"


# ── 3. CRUD Operation Tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("resource", RESOURCES)
async def test_crud_create_read_update_delete(client, resource):
    """Full CRUD cycle on every resource."""
    # CREATE
    payload = {"data": {"name": "test-item", "value": 42}}
    resp = await client.post(f"/api/{resource}", json=payload)
    assert resp.status_code == 201, f"CREATE failed for {resource}: {resp.text}"
    item = resp.json()
    item_id = item["id"]

    # READ
    resp = await client.get(f"/api/{resource}/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == item_id

    # UPDATE
    resp = await client.put(f"/api/{resource}/{item_id}", json={"data": {"name": "updated"}})
    assert resp.status_code == 200
    assert resp.json()["name"] == "updated"

    # DELETE
    resp = await client.delete(f"/api/{resource}/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


@pytest.mark.asyncio
async def test_users_crud(client):
    """Users route module CRUD."""
    resp = await client.post("/api/users/", json={"name": "Test", "email": "t@e.com"})
    assert resp.status_code == 201
    uid = resp.json()["id"]
    resp = await client.get(f"/api/users/{uid}")
    assert resp.status_code == 200
    resp = await client.put(f"/api/users/{uid}", json={"name": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"
    resp = await client.delete(f"/api/users/{uid}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_products_crud(client):
    resp = await client.post("/api/products", json={"name": "P", "price": 10.0, "stock": 5})
    assert resp.status_code == 201
    pid = resp.json()["id"]
    resp = await client.get(f"/api/products/{pid}")
    assert resp.status_code == 200
    resp = await client.put(f"/api/products/{pid}", json={"price": 20.0})
    assert resp.status_code == 200
    assert resp.json()["price"] == 20.0
    resp = await client.delete(f"/api/products/{pid}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_orders_crud(client):
    resp = await client.post("/api/orders/", json={"customer_id": 1, "items": [{"product_id": 1, "quantity": 2, "unit_price": 10.0}]})
    assert resp.status_code == 201
    oid = resp.json()["id"]
    resp = await client.get(f"/api/orders/{oid}")
    assert resp.status_code == 200
    resp = await client.put(f"/api/orders/{oid}", json={"status": "shipped"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "shipped"
    resp = await client.delete(f"/api/orders/{oid}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_accounts_crud(client):
    resp = await client.post("/api/accounts/", json={"name": "Test", "type": "asset", "code": "9999"})
    assert resp.status_code == 201
    aid = resp.json()["id"]
    resp = await client.get(f"/api/accounts/{aid}")
    assert resp.status_code == 200
    resp = await client.put(f"/api/accounts/{aid}", json={"balance": 999.0})
    assert resp.status_code == 200
    assert resp.json()["balance"] == 999.0
    resp = await client.delete(f"/api/accounts/{aid}")
    assert resp.status_code == 204


# ── 4. Error Handling Tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("resource", RESOURCES)
async def test_404_for_missing_item(client, resource):
    resp = await client.get(f"/api/{resource}/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("resource", RESOURCES)
async def test_404_on_delete_missing(client, resource):
    resp = await client.delete(f"/api/{resource}/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_users_404(client):
    resp = await client.get("/api/users/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_products_404(client):
    resp = await client.get("/api/products/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_orders_404(client):
    resp = await client.get("/api/orders/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_accounts_404(client):
    resp = await client.get("/api/accounts/99999")
    assert resp.status_code == 404


# ── 5. Data Validation Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_product_validation_rejects_negative_price(client):
    resp = await client.post("/api/products", json={"name": "X", "price": -1, "stock": 1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_product_validation_rejects_zero_stock(client):
    resp = await client.post("/api/products", json={"name": "X", "price": 10, "stock": -1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_order_validation_rejects_invalid_status(client):
    resp = await client.post("/api/orders/", json={"customer_id": 1, "items": [{"product_id": 1, "quantity": 1, "unit_price": 10}], "status": "invalid"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_account_validation_rejects_bad_type(client):
    resp = await client.post("/api/accounts/", json={"name": "X", "type": "bad", "code": "1"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_user_duplicate_email_rejected(client):
    resp = await client.post("/api/users/", json={"name": "A", "email": "dup@test.com"})
    assert resp.status_code == 201
    resp = await client.post("/api/users/", json={"name": "B", "email": "dup@test.com"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_requires_data_field(client):
    resp = await client.post("/api/dashboard", json={"not_data": {}})
    assert resp.status_code == 422
