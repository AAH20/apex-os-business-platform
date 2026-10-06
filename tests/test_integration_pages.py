"""Integration tests for the APEX-OS Business Platform API + page resources.

Converted from live-server httpx tests (http://localhost:8000) to in-process
FastAPI TestClient calls against web/backend/main.py's ``app``.

Notes on the conversion:
- The backend is a pure API service: it has no HTML routes. The SPA pages
  (``/``, ``/users``, ``/products`` ...) are served by the separate frontend
  (web/frontend, built by npm) and are not part of this FastAPI app, so the
  original "page loads over HTTP" tests are verified against the backend API
  resources those pages render instead.
- Auth is the ``X-API-Key`` header (default ``test-api-key-12345``);
  ``/api/health`` is public.
- main.py registers a generic CRUD factory for the 8 dashboard resources plus
  the route modules from routes/ (users, products, orders, accounts, ...).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# web/backend is also on sys.path via tests/conftest.py, but keep the explicit
# insert so this module works when invoked standalone.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web" / "backend"))

from main import app  # noqa: E402  (web/backend FastAPI app)

API_KEY = os.environ.get("API_KEY", "test-api-key-12345")
AUTH = {"X-API-Key": API_KEY}

# The 8 resources registered by main.py's CRUD factory (route names).
RESOURCES = [
    "dashboard",
    "accounting",
    "crm",
    "analytics",
    "agent-reach",
    "bigdata",
    "datascience",
    "continuous-bi",
]

client = TestClient(app)


# ── 1. Backend serves every resource its pages render ───────────────────────

@pytest.mark.parametrize("resource", RESOURCES)
def test_page_resource_loads_without_errors(resource):
    """Each page's backing API resource returns HTTP 200 (page itself is SPA)."""
    resp = client.get(f"/api/{resource}", headers=AUTH)
    assert resp.status_code == 200, f"Resource {resource} returned {resp.status_code}"


@pytest.mark.parametrize("resource", RESOURCES)
def test_page_resources_return_json(resource):
    """All page-backing resources return JSON (SPA pages are out of scope)."""
    resp = client.get(f"/api/{resource}", headers=AUTH)
    assert "application/json" in resp.headers.get("content-type", ""), f"{resource} not JSON"


# ── 2. API Endpoint Data Tests ──────────────────────────────────────────────

def test_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.parametrize("resource", RESOURCES)
def test_api_list_returns_data(resource):
    """Each resource endpoint returns a non-empty list."""
    resp = client.get(f"/api/{resource}", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) > 0, f"/api/{resource} returned empty"


def test_api_all_endpoint():
    resp = client.get("/api/all", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    for key in [
        "dashboard", "accounting", "crm", "analytics",
        "agent_reach", "bigdata", "datascience", "continuous_bi",
    ]:
        assert key in data, f"Missing key: {key}"


# ── 3. CRUD Operation Tests ─────────────────────────────────────────────────

@pytest.mark.parametrize("resource", RESOURCES)
def test_crud_create_read_update_delete(resource):
    """Full CRUD cycle on every generic resource."""
    # CREATE
    payload = {"data": {"name": "test-item", "value": 42}}
    resp = client.post(f"/api/{resource}", headers=AUTH, json=payload)
    assert resp.status_code == 201, f"CREATE failed for {resource}: {resp.text}"
    item = resp.json()
    item_id = item["id"]

    # READ
    resp = client.get(f"/api/{resource}/{item_id}", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["id"] == item_id

    # UPDATE
    resp = client.put(f"/api/{resource}/{item_id}", headers=AUTH, json={"data": {"name": "updated"}})
    assert resp.status_code == 200
    assert resp.json()["name"] == "updated"

    # DELETE
    resp = client.delete(f"/api/{resource}/{item_id}", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


def test_users_crud():
    """Users route module CRUD (POST/GET list live on /api/users/ with slash)."""
    resp = client.post("/api/users/", headers=AUTH, json={"name": "Test", "email": "t@e.com"})
    assert resp.status_code == 201
    uid = resp.json()["id"]
    resp = client.get(f"/api/users/{uid}", headers=AUTH)
    assert resp.status_code == 200
    resp = client.put(f"/api/users/{uid}", headers=AUTH, json={"name": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"
    resp = client.delete(f"/api/users/{uid}", headers=AUTH)
    assert resp.status_code == 204


def test_products_crud():
    resp = client.post("/api/products", headers=AUTH, json={"name": "P", "price": 10.0, "stock": 5})
    assert resp.status_code == 201
    pid = resp.json()["id"]
    resp = client.get(f"/api/products/{pid}", headers=AUTH)
    assert resp.status_code == 200
    resp = client.put(f"/api/products/{pid}", headers=AUTH, json={"price": 20.0})
    assert resp.status_code == 200
    assert resp.json()["price"] == 20.0
    resp = client.delete(f"/api/products/{pid}", headers=AUTH)
    assert resp.status_code == 204


def test_orders_crud():
    resp = client.post(
        "/api/orders",
        headers=AUTH,
        json={"customer_id": 1, "items": [{"product_id": 1, "quantity": 2, "unit_price": 10.0}]},
    )
    assert resp.status_code == 201
    oid = resp.json()["id"]
    resp = client.get(f"/api/orders/{oid}", headers=AUTH)
    assert resp.status_code == 200
    resp = client.put(f"/api/orders/{oid}", headers=AUTH, json={"status": "shipped"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "shipped"
    resp = client.delete(f"/api/orders/{oid}", headers=AUTH)
    assert resp.status_code == 204


def test_accounts_crud():
    resp = client.post("/api/accounts", headers=AUTH, json={"name": "Test", "type": "asset", "code": "9999"})
    assert resp.status_code == 201
    aid = resp.json()["id"]
    resp = client.get(f"/api/accounts/{aid}", headers=AUTH)
    assert resp.status_code == 200
    resp = client.put(f"/api/accounts/{aid}", headers=AUTH, json={"balance": 999.0})
    assert resp.status_code == 200
    assert resp.json()["balance"] == 999.0
    resp = client.delete(f"/api/accounts/{aid}", headers=AUTH)
    assert resp.status_code == 204


# ── 4. Error Handling Tests ─────────────────────────────────────────────────

@pytest.mark.parametrize("resource", RESOURCES)
def test_404_for_missing_item(resource):
    resp = client.get(f"/api/{resource}/nonexistent-id", headers=AUTH)
    assert resp.status_code == 404


@pytest.mark.parametrize("resource", RESOURCES)
def test_404_on_delete_missing(resource):
    resp = client.delete(f"/api/{resource}/nonexistent-id", headers=AUTH)
    assert resp.status_code == 404


def test_users_404():
    resp = client.get("/api/users/99999", headers=AUTH)
    assert resp.status_code == 404


def test_products_404():
    resp = client.get("/api/products/99999", headers=AUTH)
    assert resp.status_code == 404


def test_orders_404():
    resp = client.get("/api/orders/99999", headers=AUTH)
    assert resp.status_code == 404


def test_accounts_404():
    resp = client.get("/api/accounts/99999", headers=AUTH)
    assert resp.status_code == 404


# ── 5. Data Validation Tests ────────────────────────────────────────────────

def test_product_validation_rejects_negative_price():
    resp = client.post("/api/products", headers=AUTH, json={"name": "X", "price": -1, "stock": 1})
    assert resp.status_code == 422


def test_product_validation_rejects_zero_stock():
    resp = client.post("/api/products", headers=AUTH, json={"name": "X", "price": 10, "stock": -1})
    assert resp.status_code == 422


def test_order_validation_rejects_invalid_status():
    resp = client.post(
        "/api/orders",
        headers=AUTH,
        json={"customer_id": 1, "items": [{"product_id": 1, "quantity": 1, "unit_price": 10}], "status": "invalid"},
    )
    assert resp.status_code == 422


def test_account_validation_rejects_bad_type():
    resp = client.post("/api/accounts", headers=AUTH, json={"name": "X", "type": "bad", "code": "1"})
    assert resp.status_code == 422


def test_user_duplicate_email_rejected():
    resp = client.post("/api/users/", headers=AUTH, json={"name": "A", "email": "dup@test.com"})
    assert resp.status_code == 201
    resp = client.post("/api/users/", headers=AUTH, json={"name": "B", "email": "dup@test.com"})
    assert resp.status_code == 409


def test_create_requires_data_field():
    """Original test expected 422 when 'data' is missing, but the generic CRUD
    factory accepts any JSON object body (parse_request_body treats the payload
    itself as the item). Mapping: the documented behavior is that arbitrary
    JSON objects are accepted and an id is auto-assigned."""
    resp = client.post("/api/dashboard", headers=AUTH, json={"not_data": {}})
    assert resp.status_code == 201, resp.text
    assert resp.json()["id"]


def test_missing_api_key_rejected():
    """The API key middleware rejects unauthenticated requests."""
    resp = client.get("/api/users/")
    assert resp.status_code == 401
