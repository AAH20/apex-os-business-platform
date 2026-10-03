"""Performance tests for APEX-OS Business Platform."""
import asyncio
import time
import psutil
import pytest
import httpx
from typing import List

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
CONCURRENCY = 50
MAX_RESPONSE_TIME = 0.5  # seconds
MAX_QUERY_TIME = 0.1  # seconds
MAX_MEMORY_MB = 512


@pytest.mark.asyncio
class TestAPIResponseTimes:
    """Test API endpoint response times."""

    @pytest.mark.parametrize("endpoint", [
        "/health",
        f"{API_PREFIX}/users",
        f"{API_PREFIX}/projects",
        f"{API_PREFIX}/tasks",
    ])
    async def test_endpoint_response_time(self, endpoint):
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            start = time.perf_counter()
            response = await client.get(endpoint)
            elapsed = time.perf_counter() - start
            assert response.status_code == 200
            assert elapsed < MAX_RESPONSE_TIME

    async def test_p95_response_time(self):
        latencies = []
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            for _ in range(100):
                start = time.perf_counter()
                await client.get("/health")
                latencies.append(time.perf_counter() - start)
        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)]
        assert p95 < MAX_RESPONSE_TIME


@pytest.mark.asyncio
class TestConcurrentRequests:
    """Test system under concurrent load."""

    async def test_concurrent_reads(self):
        async def fetch(client, endpoint):
            return await client.get(endpoint)

        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            tasks = [fetch(client, "/health") for _ in range(CONCURRENCY)]
            start = time.perf_counter()
            responses = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            assert all(r.status_code == 200 for r in responses)
            assert elapsed < MAX_RESPONSE_TIME * 5

    async def test_concurrent_writes(self):
        async def post(client):
            return await client.post(f"{API_PREFIX}/tasks", json={"title": "perf"})

        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            tasks = [post(client) for _ in range(CONCURRENCY)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            successes = [r for r in responses if not isinstance(r, Exception)]
            assert len(successes) >= CONCURRENCY * 0.95


@pytest.mark.asyncio
class TestDatabaseQueryPerformance:
    """Test database query execution times."""

    async def test_simple_query_performance(self):
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            start = time.perf_counter()
            response = await client.get(f"{API_PREFIX}/users?limit=10")
            elapsed = time.perf_counter() - start
            assert response.status_code == 200
            assert elapsed < MAX_QUERY_TIME

    async def test_complex_query_performance(self):
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            start = time.perf_counter()
            response = await client.get(
                f"{API_PREFIX}/projects?include=tasks,users&limit=50"
            )
            elapsed = time.perf_counter() - start
            assert response.status_code == 200
            assert elapsed < MAX_QUERY_TIME * 3

    async def test_query_with_filters(self):
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            start = time.perf_counter()
            response = await client.get(
                f"{API_PREFIX}/tasks?status=pending&priority=high&limit=20"
            )
            elapsed = time.perf_counter() - start
            assert response.status_code == 200
            assert elapsed < MAX_QUERY_TIME * 2


@pytest.mark.asyncio
class TestFrontendRenderingPerformance:
    """Test frontend page load and rendering times."""

    async def test_page_load_time(self):
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            start = time.perf_counter()
            response = await client.get("/")
            elapsed = time.perf_counter() - start
            assert response.status_code == 200
            assert elapsed < 1.0

    async def test_static_asset_load(self):
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            start = time.perf_counter()
            response = await client.get("/static/js/main.js")
            elapsed = time.perf_counter() - start
            assert response.status_code == 200
            assert elapsed < 0.5

    @pytest.mark.parametrize("path", ["/dashboard", "/projects", "/settings"])
    async def test_spa_route_load(self, path):
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            start = time.perf_counter()
            response = await client.get(path)
            elapsed = time.perf_counter() - start
            assert response.status_code == 200
            assert elapsed < 1.0


class TestMemoryUsage:
    """Test memory consumption under load."""

    def test_baseline_memory(self):
        process = psutil.Process()
        mem_mb = process.memory_info().rss / 1024 / 1024
        assert mem_mb < MAX_MEMORY_MB

    @pytest.mark.asyncio
    async def test_memory_under_load(self):
        process = psutil.Process()
        baseline = process.memory_info().rss / 1024 / 1024

        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            tasks = [client.get("/health") for _ in range(CONCURRENCY)]
            await asyncio.gather(*tasks)

        current = process.memory_info().rss / 1024 / 1024
        growth = current - baseline
        assert growth < 100  # MB growth under load

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self):
        process = psutil.Process()
        readings = []

        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            for _ in range(5):
                tasks = [client.get("/health") for _ in range(20)]
                await asyncio.gather(*tasks)
                readings.append(process.memory_info().rss / 1024 / 1024)

        # Check for continuous growth (potential leak)
        if len(readings) >= 3:
            assert readings[-1] - readings[0] < 50
