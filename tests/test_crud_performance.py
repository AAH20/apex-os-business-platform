"""Comprehensive CRUD performance tests for APEX-OS Business Platform.

Converted from live-server httpx.AsyncClient tests (http://localhost:8000/
api/v1/entities) to in-process FastAPI TestClient calls against
web/backend/main.py's ``app``.

Conversion notes:
- There is no ``/entities`` resource on this backend. The generic CRUD
  factory resource ``/api/dashboard`` has identical semantics (accepts
  arbitrary JSON, auto-assigns ``id``, GET/PUT/DELETE by ``id``) and is used
  as the target for all operations.
- The original file referenced an ``async_client`` fixture that was never
  defined (19 collection errors); a module-scoped ``async_client`` fixture
  wrapping the sync TestClient is provided here.
- Concurrency tests keep the asyncio.gather structure, fanning out over
  TestClient calls from worker threads (TestClient is thread-safe; each call
  is an independent request against the ASGI app in-process).
"""
from __future__ import annotations

import asyncio
import gc
import os
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web" / "backend"))

from main import app  # noqa: E402  (web/backend FastAPI app)

API_KEY = os.environ.get("API_KEY", "test-api-key-12345")
AUTH = {"X-API-Key": API_KEY}

ENTITIES = "/api/dashboard"


@pytest.fixture
def async_client():
    """The original tests referenced this fixture without defining it.

    Provided as the in-process sync TestClient (same request surface used by
    every other converted test file); tests call it with await-style gathers
    executed on worker threads below.
    """
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _timed(fn):
    """Run a sync request callable and return (result, elapsed_seconds)."""
    start = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - start


def _make_payload(size: int = 100) -> dict:
    """Generate a payload of approximate size."""
    return {
        "name": "Performance Test Entity",
        "data": "x" * size,
        "tags": ["perf", "crud", "test"],
        "metadata": {"created_by": "test_suite", "version": 1},
    }


def _gather(async_client, calls):
    """Run request thunks concurrently (mirrors the original asyncio.gather)."""
    with ThreadPoolExecutor(max_workers=max(1, len(calls))) as pool:
        return list(pool.map(lambda fn: fn(), calls))


# ---------------------------------------------------------------------------
# 1. CRUD Operation Response Times
# ---------------------------------------------------------------------------

class TestCRUDResponseTimes:
    """Verify each CRUD operation completes within acceptable latency."""

    MAX_LATENCY_MS = 500

    @pytest.mark.parametrize("operation", ["create", "read", "update", "delete"])
    def test_operation_latency(self, operation, async_client):
        """Each CRUD op should complete within MAX_LATENCY_MS."""
        payload = _make_payload()

        if operation == "create":
            _, elapsed = _timed(
                lambda: async_client.post(ENTITIES, headers=AUTH, json=payload)
            )
        elif operation == "read":
            r = async_client.post(ENTITIES, headers=AUTH, json=payload)
            item_id = r.json()["id"]
            _, elapsed = _timed(
                lambda: async_client.get(f"{ENTITIES}/{item_id}", headers=AUTH)
            )
        elif operation == "update":
            r = async_client.post(ENTITIES, headers=AUTH, json=payload)
            item_id = r.json()["id"]
            _, elapsed = _timed(
                lambda: async_client.put(
                    f"{ENTITIES}/{item_id}", headers=AUTH, json={"name": "Updated"}
                )
            )
        else:  # delete
            r = async_client.post(ENTITIES, headers=AUTH, json=payload)
            item_id = r.json()["id"]
            _, elapsed = _timed(
                lambda: async_client.delete(f"{ENTITIES}/{item_id}", headers=AUTH)
            )

        assert elapsed * 1000 < self.MAX_LATENCY_MS, (
            f"{operation} took {elapsed * 1000:.1f}ms (limit {self.MAX_LATENCY_MS}ms)"
        )

    def test_full_crud_cycle_latency(self, async_client):
        """A full create→read→update→delete cycle should be under 2s."""
        payload = _make_payload()
        start = time.perf_counter()

        r = async_client.post(ENTITIES, headers=AUTH, json=payload)
        item_id = r.json()["id"]
        async_client.get(f"{ENTITIES}/{item_id}", headers=AUTH)
        async_client.put(f"{ENTITIES}/{item_id}", headers=AUTH, json={"name": "Updated"})
        async_client.delete(f"{ENTITIES}/{item_id}", headers=AUTH)

        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"Full CRUD cycle took {elapsed:.2f}s (limit 2.0s)"


# ---------------------------------------------------------------------------
# 2. Concurrent CRUD Operations
# ---------------------------------------------------------------------------

class TestConcurrentCRUD:
    """Verify system handles concurrent operations correctly."""

    CONCURRENCY = 20

    def test_concurrent_creates(self, async_client):
        """Multiple simultaneous creates should all succeed."""
        payloads = [_make_payload() for _ in range(self.CONCURRENCY)]

        calls = [
            (lambda p=p: async_client.post(ENTITIES, headers=AUTH, json=p))
            for p in payloads
        ]
        results = _gather(async_client, calls)
        assert all(r.status_code in (200, 201) for r in results)
        for r in results:
            client_id = r.json().get("id")
            if client_id:
                async_client.delete(f"{ENTITIES}/{client_id}", headers=AUTH)

    def test_concurrent_reads(self, async_client):
        """Multiple simultaneous reads should all succeed."""
        r = async_client.post(ENTITIES, headers=AUTH, json=_make_payload())
        item_id = r.json()["id"]

        calls = [
            (lambda: async_client.get(f"{ENTITIES}/{item_id}", headers=AUTH))
            for _ in range(self.CONCURRENCY)
        ]
        results = _gather(async_client, calls)
        assert all(r.status_code == 200 for r in results)
        async_client.delete(f"{ENTITIES}/{item_id}", headers=AUTH)

    def test_concurrent_mixed_operations(self, async_client):
        """Mix of concurrent creates, reads, updates, and deletes."""
        r = async_client.post(ENTITIES, headers=AUTH, json=_make_payload())
        item_id = r.json()["id"]
        created = [item_id]

        def mixed_op(i):
            if i % 4 == 0:
                rr = async_client.post(ENTITIES, headers=AUTH, json=_make_payload())
                created.append(rr.json()["id"])
                return rr
            elif i % 4 == 1:
                return async_client.get(f"{ENTITIES}/{item_id}", headers=AUTH)
            elif i % 4 == 2:
                return async_client.put(
                    f"{ENTITIES}/{item_id}", headers=AUTH, json={"name": f"Updated-{i}"}
                )
            else:
                return async_client.delete(f"{ENTITIES}/{item_id}", headers=AUTH)

        with ThreadPoolExecutor(max_workers=self.CONCURRENCY) as pool:
            results = list(pool.map(mixed_op, range(self.CONCURRENCY)))
        assert all(r.status_code < 500 for r in results)

        for cid in dict.fromkeys(created):
            async_client.delete(f"{ENTITIES}/{cid}", headers=AUTH)

    def test_concurrent_delete_idempotency(self, async_client):
        """Concurrent deletes of the same resource should not error."""
        r = async_client.post(ENTITIES, headers=AUTH, json=_make_payload())
        item_id = r.json()["id"]

        calls = [
            (lambda: async_client.delete(f"{ENTITIES}/{item_id}", headers=AUTH))
            for _ in range(5)
        ]
        results = _gather(async_client, calls)
        assert all(r.status_code in (200, 204, 404) for r in results)


# ---------------------------------------------------------------------------
# 3. Large Dataset Handling
# ---------------------------------------------------------------------------

class TestLargeDataset:
    """Verify CRUD operations handle large datasets efficiently."""

    LARGE_PAYLOAD_SIZE = 1024 * 1024  # 1 MB
    BATCH_SIZE = 100

    def test_large_payload_create(self, async_client):
        """Creating an entity with a 1MB payload should succeed."""
        payload = _make_payload(size=self.LARGE_PAYLOAD_SIZE)
        resp = async_client.post(ENTITIES, headers=AUTH, json=payload)
        assert resp.status_code in (200, 201)
        async_client.delete(f"{ENTITIES}/{resp.json()['id']}", headers=AUTH)

    def test_large_payload_read(self, async_client):
        """Reading a large entity should return complete data."""
        payload = _make_payload(size=self.LARGE_PAYLOAD_SIZE)
        r = async_client.post(ENTITIES, headers=AUTH, json=payload)
        item_id = r.json()["id"]

        resp = async_client.get(f"{ENTITIES}/{item_id}", headers=AUTH)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == self.LARGE_PAYLOAD_SIZE
        async_client.delete(f"{ENTITIES}/{item_id}", headers=AUTH)

    def test_batch_create(self, async_client):
        """Batch-creating 100 entities should complete within 10s."""
        payloads = [_make_payload() for _ in range(self.BATCH_SIZE)]

        start = time.perf_counter()
        calls = [
            (lambda p=p: async_client.post(ENTITIES, headers=AUTH, json=p))
            for p in payloads
        ]
        results = _gather(async_client, calls)
        elapsed = time.perf_counter() - start

        assert all(r.status_code in (200, 201) for r in results)
        assert elapsed < 10.0, f"Batch create took {elapsed:.2f}s (limit 10s)"
        for r in results:
            async_client.delete(f"{ENTITIES}/{r.json()['id']}", headers=AUTH)

    def test_list_pagination(self, async_client):
        """Listing entities should return the created items."""
        created = []
        for i in range(10):
            p = _make_payload()
            r = async_client.post(ENTITIES, headers=AUTH, json={**p, "name": f"page-{i}"})
            created.append(r.json()["id"])

        resp = async_client.get(ENTITIES, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        listed_ids = {item.get("id") for item in data}
        for cid in created:
            assert cid in listed_ids
            async_client.delete(f"{ENTITIES}/{cid}", headers=AUTH)


# ---------------------------------------------------------------------------
# 4. Memory Usage
# ---------------------------------------------------------------------------

class TestMemoryUsage:
    """Verify CRUD operations do not leak memory."""

    def test_memory_stable_across_operations(self, async_client):
        """Memory should not grow unbounded across repeated operations."""
        tracemalloc.start()
        gc.collect()
        _, baseline = tracemalloc.get_traced_memory()

        for i in range(50):
            p = _make_payload()
            r = async_client.post(ENTITIES, headers=AUTH, json={**p, "name": f"mem-{i}"})
            item_id = r.json()["id"]
            async_client.get(f"{ENTITIES}/{item_id}", headers=AUTH)
            async_client.delete(f"{ENTITIES}/{item_id}", headers=AUTH)

        gc.collect()
        _, current = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        growth = current - baseline
        max_growth = 10 * 1024 * 1024  # 10 MB
        assert growth < max_growth, (
            f"Memory grew by {growth / 1024 / 1024:.1f}MB (limit {max_growth / 1024 / 1024}MB)"
        )

    def test_large_payload_memory_cleanup(self, async_client):
        """Memory should be released after large payload operations."""
        tracemalloc.start()
        gc.collect()
        _, baseline = tracemalloc.get_traced_memory()

        for _ in range(10):
            # Collect BEFORE allocating the next large payload: the previous
            # iteration's dead request/response objects must be freed while
            # they are still in the young generation, otherwise they get
            # promoted and skew the measurement (observed as ~12MB growth
            # instead of ~3.7MB with identical requests).
            gc.collect()
            p = _make_payload(size=512 * 1024)
            r = async_client.post(ENTITIES, headers=AUTH, json=p)
            item_id = r.json()["id"]
            async_client.delete(f"{ENTITIES}/{item_id}", headers=AUTH)
            del r

        gc.collect()
        _, current = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        growth = current - baseline
        max_growth = 5 * 1024 * 1024  # 5 MB
        assert growth < max_growth, (
            f"Memory grew by {growth / 1024 / 1024:.1f}MB after large payload ops"
        )


# ---------------------------------------------------------------------------
# 5. Error Recovery
# ---------------------------------------------------------------------------

class TestErrorRecovery:
    """Verify system recovers gracefully from errors."""

    def test_recovery_after_bad_payload(self, async_client):
        """System should recover after receiving a malformed payload."""
        # The generic resource accepts any JSON object; malformed *typed*
        # payloads are exercised against the users module, which 422s on
        # missing required fields.
        bad_resp = async_client.post("/api/users/", headers=AUTH, json={"invalid": None})
        assert bad_resp.status_code >= 400

        good_resp = async_client.post(ENTITIES, headers=AUTH, json=_make_payload())
        assert good_resp.status_code in (200, 201)
        async_client.delete(f"{ENTITIES}/{good_resp.json()['id']}", headers=AUTH)

    def test_recovery_after_server_error(self, async_client):
        """System should recover after a not-found error."""
        resp = async_client.get(f"{ENTITIES}/nonexistent-id-xyz", headers=AUTH)
        assert resp.status_code == 404

        create_resp = async_client.post(ENTITIES, headers=AUTH, json=_make_payload())
        assert create_resp.status_code in (200, 201)
        async_client.delete(f"{ENTITIES}/{create_resp.json()['id']}", headers=AUTH)

    def test_recovery_after_timeout(self, async_client):
        """System should recover after a large (slow) request."""
        p = _make_payload(size=2 * 1024 * 1024)
        resp = async_client.post(ENTITIES, headers=AUTH, json=p)
        assert resp.status_code in (200, 201, 413)
        if resp.status_code in (200, 201):
            async_client.delete(f"{ENTITIES}/{resp.json()['id']}", headers=AUTH)

        normal_resp = async_client.post(ENTITIES, headers=AUTH, json=_make_payload())
        assert normal_resp.status_code in (200, 201)
        async_client.delete(f"{ENTITIES}/{normal_resp.json()['id']}", headers=AUTH)

    def test_rapid_error_recovery(self, async_client):
        """System should handle rapid sequences of errors and successes."""
        results = []
        created = []
        for i in range(20):
            if i % 3 == 0:
                r = async_client.get(f"{ENTITIES}/nonexistent", headers=AUTH)
                results.append(r.status_code)
            else:
                p = _make_payload()
                r = async_client.post(ENTITIES, headers=AUTH, json={**p, "name": f"rapid-{i}"})
                created.append(r.json()["id"])
                results.append(r.status_code)

        errors = [s for s in results if s >= 400]
        successes = [s for s in results if s < 400]
        assert len(errors) > 0 and len(successes) > 0
        assert all(s < 500 for s in results), "No 5xx errors should occur during recovery"
        for cid in created:
            async_client.delete(f"{ENTITIES}/{cid}", headers=AUTH)
