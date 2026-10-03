"""
Comprehensive verification tests for APEX-OS Business Platform.
Tests: page loads, API endpoints, CRUD operations, navigation, data display.
"""
import pytest
import pytest_asyncio
import httpx
import asyncio
from typing import AsyncGenerator

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

# Expected pages in the platform
PAGES = [
    "/",
    "/dashboard",
    "/projects",
    "/tasks",
    "/team",
    "/reports",
    "/settings",
    "/analytics",
]

# Expected API endpoints
API_ENDPOINTS = [
    "/health",
    "/projects",
    "/tasks",
    "/users",
    "/reports",
    "/analytics",
    "/notifications",
    "/settings",
]


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as c:
        yield c


# ── 1. Page Load Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_page_loads(client: httpx.AsyncClient, path: str):
    """All 8 pages must return 200 and non-empty HTML."""
    resp = await client.get(path)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    assert len(resp.text) > 0, f"{path} returned empty body"
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_pages_no_server_errors(client: httpx.AsyncClient):
    """No page should return a 5xx error."""
    for path in PAGES:
        resp = await client.get(path)
        assert resp.status_code < 500, f"{path} server error: {resp.status_code}"


# ── 2. API Endpoint Tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", API_ENDPOINTS)
async def test_api_endpoint_status(client: httpx.AsyncClient, endpoint: str):
    """All API endpoints must return valid status codes."""
    resp = await client.get(f"{API_BASE}{endpoint}")
    assert resp.status_code in (200, 201, 204), (
        f"API {endpoint} returned {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_api_returns_json(client: httpx.AsyncClient):
    """API endpoints must return JSON content."""
    for endpoint in API_ENDPOINTS:
        resp = await client.get(f"{API_BASE}{endpoint}")
        if resp.status_code == 200:
            ct = resp.headers.get("content-type", "")
            assert "application/json" in ct, f"{endpoint} not JSON: {ct}"


@pytest.mark.asyncio
async def test_health_endpoint(client: httpx.AsyncClient):
    """Health endpoint must report healthy status."""
    resp = await client.get(f"{API_BASE}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in ("ok", "healthy", "up")


# ── 3. CRUD Operation Tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_project_crud(client: httpx.AsyncClient):
    """Full CRUD cycle for projects."""
    # Create
    payload = {"name": "Test Project", "description": "Verification test"}
    resp = await client.post(f"{API_BASE}/projects", json=payload)
    assert resp.status_code in (200, 201)
    created = resp.json()
    project_id = created.get("id") or created.get("project", {}).get("id")
    assert project_id is not None

    # Read
    resp = await client.get(f"{API_BASE}/projects/{project_id}")
    assert resp.status_code == 200

    # Update
    resp = await client.put(
        f"{API_BASE}/projects/{project_id}",
        json={"name": "Updated Test Project"},
    )
    assert resp.status_code == 200

    # Delete
    resp = await client.delete(f"{API_BASE}/projects/{project_id}")
    assert resp.status_code in (200, 204)


@pytest.mark.asyncio
async def test_task_crud(client: httpx.AsyncClient):
    """Full CRUD cycle for tasks."""
    payload = {"title": "Test Task", "status": "pending"}
    resp = await client.post(f"{API_BASE}/tasks", json=payload)
    assert resp.status_code in (200, 201)
    task_id = resp.json().get("id")

    resp = await client.get(f"{API_BASE}/tasks/{task_id}")
    assert resp.status_code == 200

    resp = await client.put(
        f"{API_BASE}/tasks/{task_id}", json={"status": "completed"}
    )
    assert resp.status_code == 200

    resp = await client.delete(f"{API_BASE}/tasks/{task_id}")
    assert resp.status_code in (200, 204)


@pytest.mark.asyncio
async def test_user_crud(client: httpx.AsyncClient):
    """Full CRUD cycle for users."""
    payload = {"name": "Test User", "email": "test@example.com"}
    resp = await client.post(f"{API_BASE}/users", json=payload)
    assert resp.status_code in (200, 201)
    user_id = resp.json().get("id")

    resp = await client.get(f"{API_BASE}/users/{user_id}")
    assert resp.status_code == 200

    resp = await client.put(
        f"{API_BASE}/users/{user_id}", json={"name": "Updated User"}
    )
    assert resp.status_code == 200

    resp = await client.delete(f"{API_BASE}/users/{user_id}")
    assert resp.status_code in (200, 204)


# ── 4. Navigation Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigation_links_present(client: httpx.AsyncClient):
    """Each page must contain navigation links to other pages."""
    resp = await client.get("/")
    html = resp.text.lower()
    for page in PAGES:
        if page == "/":
            continue
        assert page.strip("/") in html or f'href="{page}"' in html, (
            f"Navigation to {page} not found on /"
        )


@pytest.mark.asyncio
async def test_internal_links_resolvable(client: httpx.AsyncClient):
    """Internal links on pages should resolve to valid responses."""
    import re
    for page in PAGES:
        resp = await client.get(page)
        links = re.findall(r'href="(/[^"]*)"', resp.text)
        for link in set(links):
            if link.startswith("/api") or link.startswith("http"):
                continue
            link_resp = await client.get(link)
            assert link_resp.status_code < 500, (
                f"Broken link {link} on {page}: {link_resp.status_code}"
            )


# ── 5. Data Display Tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_data_display_on_dashboard(client: httpx.AsyncClient):
    """Dashboard must display data elements."""
    resp = await client.get("/dashboard")
    html = resp.text.lower()
    has_data = any(kw in html for kw in [
        "project", "task", "user", "report", "metric", "stat", "chart", "table"
    ])
    assert has_data, "Dashboard contains no recognizable data elements"


@pytest.mark.asyncio
async def test_data_display_on_projects(client: httpx.AsyncClient):
    """Projects page must display project data or empty state."""
    resp = await client.get("/projects")
    html = resp.text.lower()
    has_content = any(kw in html for kw in [
        "project", "name", "description", "status", "no data", "empty"
    ])
    assert has_content, "Projects page has no data display"


@pytest.mark.asyncio
async def test_data_display_on_tasks(client: httpx.AsyncClient):
    """Tasks page must display task data or empty state."""
    resp = await client.get("/tasks")
    html = resp.text.lower()
    has_content = any(kw in html for kw in [
        "task", "title", "status", "assignee", "no data", "empty"
    ])
    assert has_content, "Tasks page has no data display"


@pytest.mark.asyncio
async def test_data_display_on_team(client: httpx.AsyncClient):
    """Team page must display team member data or empty state."""
    resp = await client.get("/team")
    html = resp.text.lower()
    has_content = any(kw in html for kw in [
        "user", "member", "name", "email", "role", "no data", "empty"
    ])
    assert has_content, "Team page has no data display"


@pytest.mark.asyncio
async def test_data_display_on_reports(client: httpx.AsyncClient):
    """Reports page must display report data or empty state."""
    resp = await client.get("/reports")
    html = resp.text.lower()
    has_content = any(kw in html for kw in [
        "report", "summary", "total", "count", "no data", "empty"
    ])
    assert has_content, "Reports page has no data display"


@pytest.mark.asyncio
async def test_data_display_on_analytics(client: httpx.AsyncClient):
    """Analytics page must display analytics data or empty state."""
    resp = await client.get("/analytics")
    html = resp.text.lower()
    has_content = any(kw in html for kw in [
        "chart", "graph", "metric", "analytics", "data", "no data", "empty"
    ])
    assert has_content, "Analytics page has no data display"


@pytest.mark.asyncio
async def test_api_data_consistency(client: httpx.AsyncClient):
    """API list endpoints must return arrays or paginated objects."""
    for endpoint in ["/projects", "/tasks", "/users"]:
        resp = await client.get(f"{API_BASE}{endpoint}")
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (list, dict)), (
                f"{endpoint} returned unexpected type: {type(data)}"
            )
