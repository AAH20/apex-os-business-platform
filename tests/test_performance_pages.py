"""Performance tests for all APEX-OS Business Platform pages/API.

Converted from live-server httpx.AsyncClient tests to in-process FastAPI
TestClient calls against ``apex_os_bp.api.app.create_api_app()`` (the backend
app this file already targeted).

Conversion mapping (verified against apex_os_bp/api/app.py + routes/):
- All routes require JWT auth (AuthMiddleware); a module-scoped client logs
  in as admin (password = $ADMIN_PASSWORD, set by tests/conftest.py) and all
  requests carry the bearer token.
- The app is API-only: the page routes (/, /dashboard, ...) belong to the
  separate web/frontend React server and return 404 here — those tests skip
  with a documented reason.
- /api/v1/projects|tasks|users do not exist on this app (see
  test_integration_crud.py notes); the API timing tests target the resources
  that DO exist: /api/v1/health, /api/v1/crm/contacts get in the way of a
  read + write so tasks timing uses /api/v1/accounting/trial-balance.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("ADMIN_PASSWORD", "admin")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-testing-only")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from apex_os_bp.api.app import create_api_app  # noqa: E402
from apex_os_bp.core.config import Config  # noqa: E402

# Relax the rate limit the same way tests/conftest.py's app fixture does:
# the default 100 req/60s breaks under a full-suite burst of API calls.
_config = Config()
_config.set("api.rate_limit.max_requests", 1000)
_config.set("api.rate_limit.window_seconds", 60)
app = create_api_app(_config)

# SPA pages of web/frontend — not served by this FastAPI app (404).
SPA_PAGES = ["/", "/dashboard", "/projects", "/tasks", "/reports", "/settings", "/users", "/analytics"]

# Real authenticated API endpoints on create_api_app().
API_ENDPOINTS = [
    "/api/v1/health",
    "/api/v1/crm/contacts",
    "/api/v1/accounting/trial-balance",
    "/api/v1/analytics/metrics",
]

SKIP_SPA = pytest.mark.skip(
    reason="Requires the rendered SPA (web/frontend) served by a frontend "
           "server; create_api_app() is API-only and CI has no frontend server."
)

MAX_PAGE_LOAD = 2.0
MAX_API_RESPONSE = 1.0
MAX_RENDER_TIME = 0.5
MAX_MEMORY_MB = 1024


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Login with the seeded admin credential (user 'admin', password
        # from $ADMIN_PASSWORD - default 'admin', see tests/conftest.py).
        import os as _os
        pw = _os.environ.get("ADMIN_PASSWORD", "admin")
        r = await c.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": pw},
        )
        token = r.json().get("access_token", "")
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


class TestPageLoadTimes:
    """Test that all pages load within acceptable time limits."""

    @pytest.mark.skip(
        reason="Requires the rendered SPA (web/frontend) served by a frontend "
               "server; create_api_app() is API-only and CI has no frontend server."
    )
    @pytest.mark.parametrize("path", SPA_PAGES)
    async def test_page_load_time(self, client, path):
        start = time.perf_counter()
        resp = await client.get(path)
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        assert elapsed < MAX_PAGE_LOAD, f"{path} took {elapsed:.2f}s (max {MAX_PAGE_LOAD}s)"

    @pytest.mark.skip(
        reason="Requires the rendered SPA (web/frontend) served by a frontend "
               "server; create_api_app() is API-only and CI has no frontend server."
    )
    async def test_all_pages_load_under_threshold(self, client):
        pass


class TestAPIResponseTimes:
    """Test that API endpoints respond within acceptable time limits."""

    @pytest.mark.parametrize("endpoint", API_ENDPOINTS)
    async def test_api_response_time(self, client, endpoint):
        start = time.perf_counter()
        resp = await client.get(endpoint)
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200, f"{endpoint}: {resp.status_code}"
        assert elapsed < MAX_API_RESPONSE, f"{endpoint} took {elapsed:.2f}s"

    async def test_api_sequential_burst(self, client):
        start = time.perf_counter()
        for endpoint in API_ENDPOINTS:
            resp = await client.get(endpoint)
            assert resp.status_code == 200
        elapsed = time.perf_counter() - start
        assert elapsed < MAX_API_RESPONSE * len(API_ENDPOINTS)


class TestRenderingPerformance:
    """Test API rendering performance with repeated requests (API-only app)."""

    @pytest.mark.parametrize("path", API_ENDPOINTS[:4])
    async def test_repeated_render_consistency(self, client, path):
        times = []
        for _ in range(5):
            start = time.perf_counter()
            resp = await client.get(path)
            times.append(time.perf_counter() - start)
            assert resp.status_code == 200
        assert max(times) < MAX_RENDER_TIME, f"{path} max render {max(times):.3f}s"
        assert (max(times) - min(times)) < 0.2, f"{path} inconsistent render times"

    async def test_concurrent_page_renders(self, client):
        async def fetch(path):
            start = time.perf_counter()
            resp = await client.get(path)
            return time.perf_counter() - start, resp.status_code

        results = await asyncio.gather(*[fetch(p) for p in API_ENDPOINTS])
        for (elapsed, status), path in zip(results, API_ENDPOINTS):
            assert status == 200, f"{path}: {status}"
            assert elapsed < MAX_RENDER_TIME * 2


class TestMemoryUsage:
    """Test that the application stays within memory bounds."""

    async def test_memory_under_threshold(self, client):
        import psutil

        process = psutil.Process()
        baseline = process.memory_info().rss / 1024 / 1024
        for endpoint in API_ENDPOINTS:
            await client.get(endpoint)
        current = process.memory_info().rss / 1024 / 1024
        assert current < MAX_MEMORY_MB, f"Memory {current:.0f}MB exceeds {MAX_MEMORY_MB}MB"
        assert current - baseline < 100, f"Memory grew {current - baseline:.0f}MB"

    async def test_memory_stable_under_repeated_load(self, client):
        import psutil

        process = psutil.Process()
        for _ in range(3):
            for endpoint in API_ENDPOINTS:
                await client.get(endpoint)
        mem = process.memory_info().rss / 1024 / 1024
        assert mem < MAX_MEMORY_MB, f"Memory {mem:.0f}MB after repeated load"


class TestConcurrentUsers:
    """Test application behavior under concurrent user load."""

    async def test_concurrent_api_access(self, client):
        async def call_api(endpoint):
            resp = await client.get(endpoint)
            return resp.status_code

        tasks = [call_api(e) for e in API_ENDPOINTS * 5]
        results = await asyncio.gather(*tasks)
        assert all(s == 200 for s in results)

    async def test_concurrent_api_load(self, client):
        async def call_api(endpoint):
            resp = await client.get(endpoint)
            return resp.status_code

        tasks = [call_api(e) for e in API_ENDPOINTS * 10]
        results = await asyncio.gather(*tasks)
        assert all(s == 200 for s in results)

    async def test_mixed_concurrent_load(self, client):
        async def hit(path):
            resp = await client.get(path)
            return resp.status_code

        all_paths = API_ENDPOINTS
        tasks = [hit(p) for p in all_paths * 4]
        results = await asyncio.gather(*tasks)
        assert len(results) == len(all_paths) * 4
        assert all(s == 200 for s in results)

    async def test_sustained_concurrent_load(self, client):
        async def round_of_requests():
            paths = API_ENDPOINTS
            return await asyncio.gather(*[client.get(p) for p in paths])

        for _ in range(5):
            responses = await round_of_requests()
            assert all(r.status_code == 200 for r in responses)
