"""Performance tests for APEX-OS Business Platform.

Converted from live-server httpx.AsyncClient tests (http://localhost:8000) to
in-process FastAPI TestClient calls against web/backend/main.py's ``app``.

Conversion mapping (verified against web/backend/main.py + routes/*.py):
- The /api/v1 prefix does not exist on this backend; real prefixed resources
  are /api/users, /api/projects, /api/tasks.
- SPA page routes (/dashboard, /projects, /settings) and static assets
  (/static/js/main.js) are served by the separate web/frontend server, not by
  this FastAPI app — those tests skip with a documented reason.
- Task create payload uses the real TaskCreate model (title, defaults ok);
  project/task query params follow the real list endpoints (page/page_size,
  status — there is no priority filter on tasks).
"""
from __future__ import annotations

import asyncio
import gc
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web" / "backend"))

import main  # noqa: E402  (web/backend FastAPI app)
from main import app  # noqa: E402

API_KEY = os.environ.get("API_KEY", "test-api-key-12345")
AUTH = {"X-API-Key": API_KEY}

CONCURRENCY = 50
MAX_RESPONSE_TIME = 0.5  # seconds
MAX_QUERY_TIME = 0.1  # seconds
MAX_MEMORY_MB = 512

SKIP_SPA = pytest.mark.skip(
    reason="Requires the rendered SPA/static assets served by the frontend server "
           "(web/frontend); the FastAPI backend is API-only and CI has no "
           "frontend server."
)


@pytest.fixture
def client():
    c = TestClient(app)
    yield c


# ── 1. API Response Times ───────────────────────────────────────────────────

class TestAPIResponseTimes:
    """Test API endpoint response times."""

    @pytest.mark.parametrize("endpoint", [
        "/api/health",
        "/api/users/",
        "/api/projects",
        "/api/tasks",
    ])
    def test_endpoint_response_time(self, client, endpoint):
        start = time.perf_counter()
        response = client.get(endpoint, headers=AUTH)
        elapsed = time.perf_counter() - start
        assert response.status_code == 200, f"{endpoint}: {response.status_code}"
        assert elapsed < MAX_RESPONSE_TIME

    def test_p95_response_time(self, client):
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            client.get("/api/health")
            latencies.append(time.perf_counter() - start)
        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)]
        assert p95 < MAX_RESPONSE_TIME


# ── 2. Concurrent Requests ──────────────────────────────────────────────────

class TestConcurrentRequests:
    """Test system under concurrent load."""

    def test_concurrent_reads(self, client):
        def fetch():
            return client.get("/api/health")

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            responses = list(pool.map(lambda _: fetch(), range(CONCURRENCY)))
        elapsed = time.perf_counter() - start
        assert all(r.status_code == 200 for r in responses)
        assert elapsed < MAX_RESPONSE_TIME * 5

    def test_concurrent_writes(self, client):
        created = []

        def post():
            return client.post("/api/tasks", headers=AUTH, json={"title": "perf"})

        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            responses = list(pool.map(lambda _: post(), range(CONCURRENCY)))
        successes = [r for r in responses if r.status_code in (200, 201)]
        assert len(successes) >= CONCURRENCY * 0.95
        for r in successes:
            created.append(r.json()["id"])
        for tid in created:
            client.delete(f"/api/tasks/{tid}", headers=AUTH)


# ── 3. Query Performance ────────────────────────────────────────────────────

class TestDatabaseQueryPerformance:
    """Test query execution times (in-memory stores; no DB on this backend)."""

    def test_simple_query_performance(self, client):
        start = time.perf_counter()
        response = client.get("/api/users/?limit=10", headers=AUTH)
        elapsed = time.perf_counter() - start
        assert response.status_code == 200
        assert elapsed < MAX_QUERY_TIME

    def test_complex_query_performance(self, client):
        # /api/projects has no include= param; a filtered+paginated list is the
        # real complex-query equivalent.
        start = time.perf_counter()
        response = client.get("/api/projects?limit=50", headers=AUTH)
        elapsed = time.perf_counter() - start
        assert response.status_code == 200
        assert elapsed < MAX_QUERY_TIME * 3

    def test_query_with_filters(self, client):
        # /api/tasks supports status= (page_size instead of limit).
        start = time.perf_counter()
        response = client.get("/api/tasks?status=todo&page_size=20", headers=AUTH)
        elapsed = time.perf_counter() - start
        assert response.status_code == 200
        assert elapsed < MAX_QUERY_TIME * 2


# ── 4. Frontend Rendering Performance ───────────────────────────────────────

@SKIP_SPA
async def test_page_load_time():
    """SPA page load timing needs the frontend server."""


@SKIP_SPA
async def test_static_asset_load():
    """Static assets (/static/js/main.js) are served by the frontend server."""


@pytest.mark.parametrize("path", ["/dashboard", "/projects", "/settings"])
def test_spa_route_load(path):
    """SPA route load timing needs the frontend server."""
    pytest.skip(
        reason="Requires the rendered SPA (web/frontend) served by a frontend "
               "server; the FastAPI backend is API-only and CI has no frontend "
               "server."
    )


# ── 5. Memory Usage ─────────────────────────────────────────────────────────

class TestMemoryUsage:
    """Test memory consumption under load."""

    def test_baseline_memory(self):
        import psutil

        process = psutil.Process()
        mem_mb = process.memory_info().rss / 1024 / 1024
        assert mem_mb < MAX_MEMORY_MB

    def test_memory_under_load(self, client):
        import psutil

        process = psutil.Process()
        baseline = process.memory_info().rss / 1024 / 1024

        def fetch():
            return client.get("/api/health")

        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            list(pool.map(lambda _: fetch(), range(CONCURRENCY)))

        # Previous test files left dead request/response objects that get
        # promoted to old-gen only after THIS gc.collect(); a second collect
        # after the requests are released measures the app, not prior noise.
        gc.collect(); gc.collect()   # first collects pre-test garbage, second measures
        current = process.memory_info().rss / 1024 / 1024
        growth = current - baseline
        assert growth < 100  # MB growth under load

    def test_memory_leak_detection(self, client):
        import psutil

        process = psutil.Process()
        readings = []

        def fetch():
            return client.get("/api/health")

        for _ in range(5):
            with ThreadPoolExecutor(max_workers=20) as pool:
                list(pool.map(lambda _: fetch(), range(20)))
            gc.collect()
            readings.append(process.memory_info().rss / 1024 / 1024)

        # Check for continuous growth (potential leak)
        if len(readings) >= 3:
            assert readings[-1] - readings[0] < 50
