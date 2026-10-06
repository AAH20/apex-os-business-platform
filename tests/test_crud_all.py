"""Comprehensive CRUD tests for all APEX-OS Business Platform modules.

Converted from live-server httpx tests (http://localhost:8000/api/v1/...) to
in-process FastAPI TestClient calls against web/backend/main.py's ``app``.

Conversion mapping (verified against web/backend/routes/*.py):
- The /api/v1 prefix does not exist on this backend; real prefixes are
  /api/users, /api/products, /api/orders, /api/customers, /api/invoices,
  /api/payments.
- Collection routes are slash-sensitive (registered as "/" or ""):
  GET /api/users/ vs GET /api/products — exact effective paths are encoded in
  MODULE_CFG below. A GET sent to a POST-only path returns 405 on this
  FastAPI version (main.py's slash-less alias pass cannot see routers that
  are included via _IncludedRouter wrappers).
- ids are ints everywhere except invoices (string ids like "INV-1001").
- Update payloads: modules whose models have no "name" field (orders,
  invoices, payments) ignore the extra key and return 200 unchanged.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web" / "backend"))

from main import app  # noqa: E402  (web/backend FastAPI app)

API_KEY = os.environ.get("API_KEY", "test-api-key-12345")
AUTH = {"X-API-Key": API_KEY}

MODULES = ["users", "products", "orders", "customers", "invoices", "payments"]

# Per-module real API surface (verified against the route declarations).
# "collection": exact GET path of the list endpoint.
# "create": exact POST path of the create endpoint.
# "missing_id": a well-typed id that does not exist (int-like for int-id
#               modules so the request reaches the handler and 404s instead
#               of failing path-type validation with 422).
MODULE_CFG: Dict[str, Dict[str, Any]] = {
    "users": {
        "collection": "/api/users/",
        "create": "/api/users/",
        "missing_id": "99999",
    },
    "products": {
        "collection": "/api/products",
        "create": "/api/products",
        "missing_id": "99999",
    },
    "orders": {
        "collection": "/api/orders/",
        "create": "/api/orders",
        "missing_id": "99999",
    },
    "customers": {
        "collection": "/api/customers/",
        "create": "/api/customers/",
        "missing_id": "99999",
    },
    "invoices": {
        "collection": "/api/invoices",
        "create": "/api/invoices",
        "missing_id": "nonexistent-id-99999",
    },
    "payments": {
        "collection": "/api/payments/",
        "create": "/api/payments",
        "missing_id": "99999",
    },
}

# Valid create payloads matching the real Pydantic models (extra keys such as
# "sku" are ignored by the models, so they are kept from the original tests).
def _payload_for(module: str) -> Dict[str, Any]:
    payloads = {
        # users: the email must be unique per call (routes/users.py rejects
        # duplicates with 409, and the in-memory store persists across tests
        # in one process).
        "users": {
            "name": "Test User",
            "email": f"test{os.urandom(6).hex()}@example.com",
            "role": "member",
        },
        "products": {"name": "Test Product", "price": 29.99, "stock": 10, "sku": "TEST-001"},
        # orders: customer_id/items must be ints and items need quantity +
        # unit_price per OrderItem (the original {"product_id": "p1", "qty": 2}
        # shape would 422).
        "orders": {
            "customer_id": 1,
            "items": [{"product_id": 1, "quantity": 2, "unit_price": 9.99}],
        },
        "customers": {"name": "Test Customer", "email": "cust@example.com"},
        # invoices: InvoiceCreate requires customer_name, customer_email,
        # amount, issue_date, due_date (the original {"customer_id": ...}
        # shape would 422).
        "invoices": {
            "customer_name": "Test Customer",
            "customer_email": "cust@example.com",
            "amount": 100.0,
            "status": "draft",
            "issue_date": "2026-01-01",
            "due_date": "2026-02-01",
        },
        # payments: PaymentCreate requires amount and method (invoice_id is
        # not a model field; the optional order_id/customer_id are).
        "payments": {"amount": 100.0, "method": "card", "customer_id": "cust-1"},
    }
    return payloads[module]


client = TestClient(app)


@pytest.fixture
def sample_data():
    """Create a sample record per module for read/update/delete tests."""
    records = {}
    for module in MODULES:
        cfg = MODULE_CFG[module]
        r = client.post(cfg["create"], headers=AUTH, json=_payload_for(module))
        if r.status_code in (200, 201):
            records[module] = r.json()
    yield records
    # Cleanup
    for module, rec in records.items():
        rid = rec.get("id") or rec.get("_id")
        if rid:
            client.delete(f"/api/{module}/{rid}", headers=AUTH)


# ─── CREATE ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("module", MODULES)
def test_create(module):
    r = client.post(MODULE_CFG[module]["create"], headers=AUTH, json=_payload_for(module))
    assert r.status_code in (200, 201), f"Create {module} failed: {r.text}"
    data = r.json()
    assert "id" in data or "_id" in data


@pytest.mark.parametrize("module", MODULES)
def test_create_validation_error(module):
    r = client.post(MODULE_CFG[module]["create"], headers=AUTH, json={})
    assert r.status_code == 422


# ─── READ ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("module", MODULES)
def test_list(module):
    r = client.get(MODULE_CFG[module]["collection"], headers=AUTH)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) or "items" in data or "data" in data


@pytest.mark.parametrize("module", MODULES)
def test_get_by_id(sample_data, module):
    rec = sample_data.get(module)
    if not rec:
        pytest.skip(f"No record created for {module}")
    rid = rec.get("id") or rec.get("_id")
    r = client.get(f"/api/{module}/{rid}", headers=AUTH)
    assert r.status_code == 200


@pytest.mark.parametrize("module", MODULES)
def test_get_not_found(module):
    r = client.get(f"/api/{module}/{MODULE_CFG[module]['missing_id']}", headers=AUTH)
    assert r.status_code == 404


# ─── UPDATE ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("module", MODULES)
def test_update(sample_data, module):
    rec = sample_data.get(module)
    if not rec:
        pytest.skip(f"No record created for {module}")
    rid = rec.get("id") or rec.get("_id")
    # "name" is accepted by users/products/customers models; orders/invoices/
    # payments models have no name field and simply ignore it (200 unchanged).
    r = client.put(f"/api/{module}/{rid}", headers=AUTH, json={"name": "Updated"})
    assert r.status_code in (200, 204)


@pytest.mark.parametrize("module", MODULES)
def test_update_not_found(module):
    r = client.put(
        f"/api/{module}/{MODULE_CFG[module]['missing_id']}",
        headers=AUTH,
        json={"name": "X"},
    )
    assert r.status_code == 404


# ─── DELETE ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("module", MODULES)
def test_delete(sample_data, module):
    rec = sample_data.get(module)
    if not rec:
        pytest.skip(f"No record created for {module}")
    rid = rec.get("id") or rec.get("_id")
    r = client.delete(f"/api/{module}/{rid}", headers=AUTH)
    assert r.status_code in (200, 204)
    r2 = client.get(f"/api/{module}/{rid}", headers=AUTH)
    assert r2.status_code == 404


@pytest.mark.parametrize("module", MODULES)
def test_delete_not_found(module):
    r = client.delete(f"/api/{module}/{MODULE_CFG[module]['missing_id']}", headers=AUTH)
    assert r.status_code == 404


# ─── PAGINATION ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("module", MODULES)
def test_pagination(module):
    # page/limit are valid query names on users/products/customers; the other
    # modules use page/page_size and ignore the unknown "limit" key, so the
    # request still returns 200.
    r = client.get(f"{MODULE_CFG[module]['collection']}?page=1&limit=1", headers=AUTH)
    assert r.status_code == 200


@pytest.mark.parametrize("module", MODULES)
def test_pagination_invalid_page(module):
    # page=-1 and/or limit=0 violate ge=1/ge=1 query constraints on every
    # module's list endpoint -> 422.
    r = client.get(f"{MODULE_CFG[module]['collection']}?page=-1&limit=0", headers=AUTH)
    assert r.status_code in (400, 422)


# ─── ERROR HANDLING ─────────────────────────────────────────────────────────

def test_method_not_allowed():
    r = client.patch("/api/users/nonexistent", headers=AUTH)
    assert r.status_code == 405


def test_malformed_json():
    r = client.post(
        "/api/users/",
        headers={**AUTH, "Content-Type": "application/json"},
        content=b"{invalid",
    )
    assert r.status_code == 422
