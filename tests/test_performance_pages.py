"""Performance tests for all APEX-OS Business Platform pages."""
import asyncio
import os
import time
import psutil
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("ADMIN_PASSWORD", "test-password")
os.environ.setdefault("JWT_SECRET", "test-secret")

from apex_os_bp.api.app import create_api_app
app = create_api_app()

PAGES = ["/", "/dashboard", "/projects", "/tasks", "/reports", "/settings", "/users", "/analytics"]
API_ENDPOINTS = ["/api/v1/health", "/api/v1/projects", "/api/v1/tasks", "/api/v1/users"]
MAX_PAGE_LOAD = 2.0
MAX_API_RESPONSE = 1.0
MAX_RENDER_TIME = 0.5
MAX_MEMORY_MB = 512
MAX_CONCURRENT_USERS = 50


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestPageLoadTimes:
    """Test that all pages load within acceptable time limits."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_page_load_time(self, client, path):
        start = time.perf_counter()
        resp = await client.get(path)
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        assert elapsed < MAX_PAGE_LOAD, f"{path} took {elapsed:.2f}s (max {MAX_PAGE_LOAD}s)"

    @pytest.mark.asyncio
    async def test_all_pages_load_under_threshold(self, client):
        times = {}
        for path in PAGES:
            start = time.perf_counter()
            resp = await client.get(path)
            times[path] = time.perf_counter() - start
            assert resp.status_code == 200
        avg = sum(times.values()) / len(times)
        assert avg < MAX_PAGE_LOAD, f"Average load {avg:.2f}s exceeds {MAX_PAGE_LOAD}s"


class TestAPIResponseTimes:
    """Test that API endpoints respond within acceptable time limits."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", API_ENDPOINTS)
    async def test_api_response_time(self, client, endpoint):
        start = time.perf_counter()
        resp = await client.get(endpoint)
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        assert elapsed < MAX_API_RESPONSE, f"{endpoint} took {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_api_sequential_burst(self, client):
        start = time.perf_counter()
        for endpoint in API_ENDPOINTS:
            resp = await client.get(endpoint)
            assert resp.status_code == 200
        elapsed = time.perf_counter() - start
        assert elapsed < MAX_API_RESPONSE * len(API_ENDPOINTS)


class TestRenderingPerformance:
    """Test page rendering performance with repeated requests."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES[:4])
    async def test_repeated_render_consistency(self, client, path):
        times = []
        for _ in range(5):
            start = time.perf_counter()
            resp = await client.get(path)
            times.append(time.perf_counter() - start)
            assert resp.status_code == 200
        assert max(times) < MAX_RENDER_TIME, f"{path} max render {max(times):.3f}s"
        assert (max(times) - min(times)) < 0.2, f"{path} inconsistent render times"

    @pytest.mark.asyncio
    async def test_concurrent_page_renders(self, client):
        async def fetch(path):
            start = time.perf_counter()
            resp = await client.get(path)
            return time.perf_counter() - start, resp.status_code

        results = await asyncio.gather(*[fetch(p) for p in PAGES])
        for (elapsed, status), path in zip(results, PAGES):
            assert status == 200
            assert elapsed < MAX_RENDER_TIME * 2


class TestMemoryUsage:
    """Test that the application stays within memory bounds."""

    @pytest.mark.asyncio
    async def test_memory_under_threshold(self, client):
        process = psutil.Process()
        baseline = process.memory_info().rss / 1024 / 1024
        for path in PAGES:
            await client.get(path)
        for endpoint in API_ENDPOINTS:
            await client.get(endpoint)
        current = process.memory_info().rss / 1024 / 1024
        assert current < MAX_MEMORY_MB, f"Memory {current:.0f}MB exceeds {MAX_MEMORY_MB}MB"
        assert current - baseline < 100, f"Memory grew {current - baseline:.0f}MB"

    @pytest.mark.asyncio
    async def test_memory_stable_under_repeated_load(self, client):
        process = psutil.Process()
        for _ in range(3):
            for path in PAGES:
                await client.get(path)
        mem = process.memory_info().rss / 1024 / 1024
        assert mem < MAX_MEMORY_MB, f"Memory {mem:.0f}MB after repeated load"


class TestConcurrentUsers:
    """Test application behavior under concurrent user load."""

    @pytest.mark.asyncio
    async def test_concurrent_page_access(self, client):
        async def access_page(path):
            resp = await client.get(path)
            return resp.status_code

        tasks = [access_page(p) for p in PAGES * 5]
        results = await asyncio.gather(*tasks)
        assert all(s == 200 for s in results)

    @pytest.mark.asyncio
    async def test_concurrent_api_load(self, client):
        async def call_api(endpoint):
            resp = await client.get(endpoint)
            return resp.status_code

        tasks = [call_api(e) for e in API_ENDPOINTS * 10]
        results = await asyncio.gather(*tasks)
        assert all(s == 200 for s in results)

    @pytest.mark.asyncio
    async def test_mixed_concurrent_load(self, client):
        async def hit(path):
            resp = await client.get(path)
            return resp.status_code

        all_paths = PAGES + API_ENDPOINTS
        tasks = [hit(p) for p in all_paths * 4]
        results = await asyncio.gather(*tasks)
        assert len(results) == len(all_paths) * 4
        assert all(s == 200 for s in results)

    @pytest.mark.asyncio
    async def test_sustained_concurrent_load(self, client):
        async def round_of_requests():
            paths = PAGES + API_ENDPOINTS
            return await asyncio.gather(*[client.get(p) for p in paths])

        for _ in range(5):
            responses = await round_of_requests()
            assert all(r.status_code == 200 for r in responses)
