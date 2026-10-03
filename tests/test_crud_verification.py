"""Comprehensive CRUD verification tests for APEX-OS Business Platform."""
import pytest
import pytest_asyncio
import httpx
import asyncio
from typing import Any

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"
TIMEOUT = 10.0

# ── Fixtures ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient(base_url=API_URL, timeout=TIMEOUT) as c:
        yield c

@pytest_asyncio.fixture
async def sample_user():
    return {"name": "Test User", "email": "test@example.com", "role": "member"}

@pytest_asyncio.fixture
async def sample_product():
    return {"name": "Test Product", "price": 29.99, "stock": 100, "sku": "TEST-001"}

@pytest_asyncio.fixture
async def sample_order():
    return {"customer_id": 1, "items": [{"product_id": 1, "qty": 2}]}

@pytest_asyncio.fixture
async def created_user(client, sample_user):
    r = await client.post("/users", json=sample_user)
    data = r.json()
    yield data
    await client.delete(f"/users/{data['id']}")

@pytest_asyncio.fixture
async def created_product(client, sample_product):
    r = await client.post("/products", json=sample_product)
    data = r.json()
    yield data
    await client.delete(f"/products/{data['id']}")

@pytest_asyncio.fixture
async def created_order(client, sample_order):
    r = await client.post("/orders", json=sample_order)
    data = r.json()
    yield data
    await client.delete(f"/orders/{data['id']}")

# ── 1. Page Load Tests ────────────────────────────────────────────────

class TestPageLoads:
    """Verify all CRUD pages load without errors."""

    @pytest.mark.parametrize("path", [
        "/", "/dashboard", "/users", "/products", "/orders",
        "/customers", "/invoices", "/reports", "/settings",
    ])
    async def test_page_loads(self, path):
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as c:
            r = await c.get(path)
            assert r.status_code == 200, f"{path} returned {r.status_code}"

    @pytest.mark.parametrize("path", [
        "/users/new", "/products/new", "/orders/new",
        "/users/1/edit", "/products/1/edit", "/orders/1/edit",
    ])
    async def test_form_pages_load(self, path):
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as c:
            r = await c.get(path)
            assert r.status_code in (200, 302), f"{path} returned {r.status_code}"

# ── 2. API Endpoint Status Tests ──────────────────────────────────────

class TestAPIEndpoints:
    """Verify all API endpoints return correct status codes."""

    @pytest.mark.parametrize("method,path,expected", [
        ("GET", "/users", 200),
        ("GET", "/products", 200),
        ("GET", "/orders", 200),
        ("GET", "/customers", 200),
        ("GET", "/invoices", 200),
        ("GET", "/reports", 200),
        ("GET", "/settings", 200),
        ("GET", "/users/1", 200),
        ("GET", "/products/1", 200),
        ("GET", "/orders/1", 200),
        ("GET", "/nonexistent", 404),
    ])
    async def test_endpoint_status(self, method, path, expected):
        async with httpx.AsyncClient(base_url=API_URL, timeout=TIMEOUT) as c:
            r = await c.request(method, path)
            assert r.status_code == expected, \
                f"{method} {path} → {r.status_code} (expected {expected})"

    @pytest.mark.parametrize("path", ["/users", "/products", "/orders", "/customers"])
    async def test_list_returns_array(self, client, path):
        r = await client.get(path)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) or isinstance(data, dict)

# ── 3. CRUD Operation Tests ───────────────────────────────────────────

class TestUserCRUD:
    async def test_create_user(self, client, sample_user):
        r = await client.post("/users", json=sample_user)
        assert r.status_code in (200, 201)
        data = r.json()
        assert "id" in data
        assert data["name"] == sample_user["name"]
        await client.delete(f"/users/{data['id']}")

    async def test_read_user(self, client, created_user):
        r = await client.get(f"/users/{created_user['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == created_user["id"]

    async def test_update_user(self, client, created_user):
        r = await client.put(f"/users/{created_user['id']}", json={"name": "Updated"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"

    async def test_delete_user(self, client, sample_user):
        r = await client.post("/users", json=sample_user)
        uid = r.json()["id"]
        r2 = await client.delete(f"/users/{uid}")
        assert r2.status_code in (200, 204)
        r3 = await client.get(f"/users/{uid}")
        assert r3.status_code == 404

    async def test_list_users(self, client):
        r = await client.get("/users")
        assert r.status_code == 200
        assert isinstance(r.json(), (list, dict))

class TestProductCRUD:
    async def test_create_product(self, client, sample_product):
        r = await client.post("/products", json=sample_product)
        assert r.status_code in (200, 201)
        data = r.json()
        assert "id" in data
        assert data["name"] == sample_product["name"]
        await client.delete(f"/products/{data['id']}")

    async def test_read_product(self, client, created_product):
        r = await client.get(f"/products/{created_product['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == created_product["id"]

    async def test_update_product(self, client, created_product):
        r = await client.put(f"/products/{created_product['id']}", json={"price": 39.99})
        assert r.status_code == 200
        assert r.json()["price"] == 39.99

    async def test_delete_product(self, client, sample_product):
        r = await client.post("/products", json=sample_product)
        pid = r.json()["id"]
        r2 = await client.delete(f"/products/{pid}")
        assert r2.status_code in (200, 204)
        r3 = await client.get(f"/products/{pid}")
        assert r3.status_code == 404

class TestOrderCRUD:
    async def test_create_order(self, client, sample_order):
        r = await client.post("/orders", json=sample_order)
        assert r.status_code in (200, 201)
        data = r.json()
        assert "id" in data
        await client.delete(f"/orders/{data['id']}")

    async def test_read_order(self, client, created_order):
        r = await client.get(f"/orders/{created_order['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == created_order["id"]

    async def test_update_order(self, client, created_order):
        r = await client.put(f"/orders/{created_order['id']}", json={"status": "shipped"})
        assert r.status_code == 200

    async def test_delete_order(self, client, sample_order):
        r = await client.post("/orders", json=sample_order)
        oid = r.json()["id"]
        r2 = await client.delete(f"/orders/{oid}")
        assert r2.status_code in (200, 204)

# ── 4. Navigation Tests ───────────────────────────────────────────────

class TestNavigation:
    @pytest.mark.parametrize("from_page,to_page,link_text", [
        ("/", "/dashboard", "Dashboard"),
        ("/", "/users", "Users"),
        ("/", "/products", "Products"),
        ("/", "/orders", "Orders"),
        ("/users", "/users/new", "New User"),
        ("/products", "/products/new", "New Product"),
        ("/orders", "/orders/new", "New Order"),
    ])
    async def test_navigation_links(self, from_page, to_page, link_text):
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as c:
            r = await c.get(from_page)
            assert r.status_code == 200
            assert to_page in r.text or link_text in r.text, \
                f"Link to {to_page} not found on {from_page}"

    async def test_breadcrumb_navigation(self):
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as c:
            r = await c.get("/users/1")
            assert r.status_code in (200, 302)

    async def test_redirect_after_create(self, client, sample_user):
        r = await client.post("/users", json=sample_user, follow_redirects=False)
        assert r.status_code in (200, 201, 302)
        if r.status_code == 302:
            assert "/users" in r.headers.get("location", "")

# ── 5. Data Display Tests ─────────────────────────────────────────────

class TestDataDisplay:
    @pytest.mark.parametrize("path,expected_keys", [
        ("/users", ["id", "name", "email"]),
        ("/products", ["id", "name", "price"]),
        ("/orders", ["id", "status"]),
    ])
    async def test_list_data_structure(self, client, path, expected_keys):
        r = await client.get(path)
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", data.get("data", []))
        if items:
            for key in expected_keys:
                assert key in items[0], f"Key '{key}' missing in {path} response"

    @pytest.mark.parametrize("path", ["/users/1", "/products/1", "/orders/1"])
    async def test_detail_data_structure(self, client, path):
        r = await client.get(path)
        assert r.status_code == 200
        data = r.json()
        assert "id" in data

    async def test_pagination_params(self, client):
        r = await client.get("/users?page=1&limit=10")
        assert r.status_code == 200

    async def test_search_filter(self, client):
        r = await client.get("/users?search=test")
        assert r.status_code == 200

    async def test_empty_state(self, client):
        r = await client.get("/users?search=nonexistent_xyz_12345")
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", [])
        assert len(items) == 0

    async def test_error_response_format(self, client):
        r = await client.get("/users/999999999")
        assert r.status_code == 404
        data = r.json()
        assert "error" in data or "detail" in data or "message" in data

# ── 6. Validation Tests ───────────────────────────────────────────────

class TestValidation:
    async def test_create_user_invalid_email(self, client):
        r = await client.post("/users", json={"name": "X", "email": "not-an-email"})
        assert r.status_code == 422

    async def test_create_product_negative_price(self, client):
        r = await client.post("/products", json={"name": "X", "price": -10})
        assert r.status_code == 422

    async def test_create_missing_required_fields(self, client):
        r = await client.post("/users", json={})
        assert r.status_code == 422

    async def test_method_not_allowed(self, client):
        r = await client.patch("/users/1")
        assert r.status_code == 405
