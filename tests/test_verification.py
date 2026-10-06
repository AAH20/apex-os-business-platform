"""Comprehensive verification tests for APEX-OS Business Platform.

Converted from live-server httpx tests (http://localhost:8000) to in-process
FastAPI TestClient calls against web/backend/main.py's ``app`` with the
``X-API-Key`` header.

Conversion mapping:
- The backend is a pure JSON API (web/backend/main.py); it serves no HTML.
  The original "page load / navigation / rendered data" tests require the
  rendered React SPA (web/frontend, served by its own dev server), which is
  not available in CI, so those tests skip with a documented reason.
- API paths use the backend's real prefixes (/api/users, /api/tasks, ...) —
  not the /api/v1 prefix this file originally assumed.
- Create/update payloads match the real route models in web/backend/routes/.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web" / "backend"))

from main import app  # noqa: E402  (web/backend FastAPI app)

API_KEY = os.environ.get("API_KEY", "test-api-key-12345")
AUTH = {"X-API-Key": API_KEY}

# SPA routes of the web/frontend React app — not served by the FastAPI backend.
SPA_PAGES = [
    "/",
    "/dashboard",
    "/projects",
    "/tasks",
    "/team",
    "/reports",
    "/settings",
    "/analytics",
]

SKIP_SPA = pytest.mark.skip(
    reason="Requires the rendered React SPA (web/frontend) served by a frontend "
           "server; the FastAPI backend is API-only and CI has no frontend server."
)

# Real backend endpoints corresponding to the original API_ENDPOINTS list.
API_ENDPOINTS = [
    "/api/health",
    "/api/projects",
    "/api/tasks",
    "/api/users",
    "/api/reports",
    "/api/analytics",
    "/api/notifications",
]

client = TestClient(app)


# ── 1. Page Load Tests ──────────────────────────────────────────────────────

@pytest.mark.skip(
    reason="Requires the rendered React SPA (web/frontend) served by a frontend "
           "server; the FastAPI backend is API-only and CI has no frontend server."
)
@pytest.mark.parametrize("path", SPA_PAGES)
async def test_page_loads(path):
    """All 8 SPA pages must return 200 and non-empty HTML."""


@SKIP_SPA
async def test_pages_no_server_errors():
    """No SPA page should return a 5xx error."""


# ── 2. API Endpoint Tests ───────────────────────────────────────────────────

@pytest.mark.parametrize("endpoint", API_ENDPOINTS)
def test_api_endpoint_status(endpoint):
    """All API endpoints must return valid status codes."""
    resp = client.get(endpoint, headers=AUTH)
    assert resp.status_code in (200, 201, 204), (
        f"API {endpoint} returned {resp.status_code}"
    )


def test_api_returns_json():
    """API endpoints must return JSON content."""
    for endpoint in API_ENDPOINTS:
        resp = client.get(endpoint, headers=AUTH)
        if resp.status_code == 200:
            ct = resp.headers.get("content-type", "")
            assert "application/json" in ct, f"{endpoint} not JSON: {ct}"


def test_health_endpoint():
    """Health endpoint must report healthy status."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in ("ok", "healthy", "up")


@pytest.mark.skip(
    reason="The backend has no /api/settings route (settings are SPA-only client "
           "state); no API endpoint exists to verify."
)
def test_settings_endpoint():
    """Original test expected /api/v1/settings to exist."""


# ── 3. CRUD Operation Tests ─────────────────────────────────────────────────

def test_project_crud():
    """Full CRUD cycle for projects (routes/projects.py: name required)."""
    payload = {"name": "Test Project", "description": "Verification test"}
    resp = client.post("/api/projects", headers=AUTH, json=payload)
    assert resp.status_code in (200, 201), resp.text
    created = resp.json()
    project_id = created.get("id")
    assert project_id is not None

    resp = client.get(f"/api/projects/{project_id}", headers=AUTH)
    assert resp.status_code == 200

    resp = client.put(
        f"/api/projects/{project_id}", headers=AUTH, json={"name": "Updated Test Project"}
    )
    assert resp.status_code == 200

    resp = client.delete(f"/api/projects/{project_id}", headers=AUTH)
    assert resp.status_code in (200, 204)


def test_task_crud():
    """Full CRUD cycle for tasks (routes/tasks.py: status in todo|in_progress|done)."""
    payload = {"title": "Test Task", "status": "todo"}
    resp = client.post("/api/tasks", headers=AUTH, json=payload)
    assert resp.status_code in (200, 201), resp.text
    task_id = resp.json().get("id")

    resp = client.get(f"/api/tasks/{task_id}", headers=AUTH)
    assert resp.status_code == 200

    # Real model only accepts todo|in_progress|done; the original "completed"
    # value is not a valid task status.
    resp = client.put(f"/api/tasks/{task_id}", headers=AUTH, json={"status": "done"})
    assert resp.status_code == 200

    resp = client.delete(f"/api/tasks/{task_id}", headers=AUTH)
    assert resp.status_code in (200, 204)


def test_user_crud():
    """Full CRUD cycle for users (routes/users.py: collection lives at /api/users/)."""
    payload = {"name": "Test User", "email": "test@example.com"}
    resp = client.post("/api/users/", headers=AUTH, json=payload)
    assert resp.status_code in (200, 201), resp.text
    user_id = resp.json().get("id")

    resp = client.get(f"/api/users/{user_id}", headers=AUTH)
    assert resp.status_code == 200

    resp = client.put(f"/api/users/{user_id}", headers=AUTH, json={"name": "Updated User"})
    assert resp.status_code == 200

    resp = client.delete(f"/api/users/{user_id}", headers=AUTH)
    assert resp.status_code in (200, 204)


# ── 4. Navigation Tests ─────────────────────────────────────────────────────

@SKIP_SPA
async def test_navigation_links_present():
    """Each SPA page must contain navigation links to other pages."""


@SKIP_SPA
async def test_internal_links_resolvable():
    """Internal links on SPA pages should resolve to valid responses."""


# ── 5. Data Display Tests ───────────────────────────────────────────────────

@SKIP_SPA
async def test_data_display_on_dashboard():
    """Dashboard SPA page must display data elements."""


@SKIP_SPA
async def test_data_display_on_projects():
    """Projects SPA page must display project data or empty state."""


@SKIP_SPA
async def test_data_display_on_tasks():
    """Tasks SPA page must display task data or empty state."""


@SKIP_SPA
async def test_data_display_on_team():
    """Team SPA page must display team member data or empty state."""


@SKIP_SPA
async def test_data_display_on_reports():
    """Reports SPA page must display report data or empty state."""


@SKIP_SPA
async def test_data_display_on_analytics():
    """Analytics SPA page must display analytics data or empty state."""


# ── 6. API Data Consistency ─────────────────────────────────────────────────

def test_api_data_consistency():
    """API list endpoints must return arrays or paginated objects."""
    for endpoint in ["/api/projects", "/api/tasks", "/api/users"]:
        resp = client.get(endpoint, headers=AUTH)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (list, dict)), (
                f"{endpoint} returned unexpected type: {type(data)}"
            )
